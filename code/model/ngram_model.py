import math
import pickle
from collections import Counter, defaultdict

START = '<s>'
END = '</s>'
UNKNOWN = '<unk>'
SMOOTHINGS = ('laplace', 'lidstone', 'kneser_ney')

class NgramModel:
    def __init__(self, n=3, smoothing='kneser_ney', lidstone_k=0.01):
        if smoothing not in SMOOTHINGS:
            raise ValueError(f'unknown smoothing: {smoothing}')
        self.n = n
        self.smoothing = smoothing
        self.k = 1.0 if smoothing == 'laplace' else lidstone_k
        self.vocabulary = {END, UNKNOWN}
        self.counts = [None] + [defaultdict(Counter) for _ in range(n)]
        self.ready = False

    # ------------------------------------------------------------------ training

    def train(self, sentences):
        for sentence in sentences:
            self.vocabulary.update(sentence)
            tokens = [START] * (self.n - 1) + list(sentence) + [END]
            for i in range(self.n - 1, len(tokens)):
                word = tokens[i]
                for order in range(1, self.n + 1):
                    context = tuple(tokens[i - order + 1:i])
                    self.counts[order][context][word] += 1
        self.vocabulary.discard(START)
        self.ready = False

    def prepare(self):
        if self.ready:
            return
        kneser_ney = self.smoothing == 'kneser_ney'
        self.base = [None] * (self.n + 1)
        self.totals = [None] * (self.n + 1)
        self.discounts = [None] * (self.n + 1)

        for order in range(1, self.n + 1):
            if kneser_ney and order < self.n:
                base = continuation_counts(self.counts[order + 1])
            else:
                base = self.counts[order]
            self.base[order] = base
            self.totals[order] = {context: sum(c.values()) for context, c in base.items()}
            if kneser_ney:
                self.discounts[order] = ney_discount(base)

        self.uniform = 1 / len(self.vocabulary)
        self.vocabulary_list = sorted(self.vocabulary)
        self.ranking_cache = {}
        self.unigram_ranking = sorted(
            (w for w in self.vocabulary if w != UNKNOWN),
            key=lambda w: (-self.probability_at(1, (), w), w))
        self.ready = True

    # ------------------------------------------------------------------ probability

    def known(self, word):
        return word if word in self.vocabulary else UNKNOWN

    def context_of(self, tokens):
        padded = [START] * (self.n - 1) + [self.known(w) for w in tokens]
        return tuple(padded[len(padded) - (self.n - 1):])

    def probability_at(self, order, context, word):
        if order == 0:
            return self.uniform
        counts = self.base[order].get(context)
        total = self.totals[order].get(context, 0)
        count = counts.get(word, 0) if counts else 0

        if self.smoothing in ('laplace', 'lidstone'):
            return (count + self.k) / (total + self.k * len(self.vocabulary))

        lower = self.probability_at(order - 1, context[1:], word)
        if not total:
            return lower
        types = len(counts)
        discount = self.discounts[order]
        return max(count - discount, 0) / total + discount * types / total * lower

    def probability(self, word, context=()):
        self.prepare()
        return self.probability_at(self.n, self.context_of(context), self.known(word))

    def perplexity(self, sentences):
        self.prepare()
        log_sum = 0.0
        total = 0
        for sentence in sentences:
            tokens = [START] * (self.n - 1) + [self.known(w) for w in sentence] + [END]
            for i in range(self.n - 1, len(tokens)):
                context = tuple(tokens[i - self.n + 1:i])
                log_sum += math.log(self.probability_at(self.n, context, tokens[i]))
                total += 1
        return math.exp(-log_sum / total)

    # ------------------------------------------------------------------ prediction

    def ranking(self, order, context, size):
        if order == 1 and self.smoothing not in ('laplace', 'lidstone'):
            return self.unigram_ranking[:size]
        key = (order, context)
        cached = self.ranking_cache.get(key)
        if cached and cached[0] >= size:
            return cached[1][:size]

        seen = self.base[order].get(context) or {}
        if self.smoothing in ('laplace', 'lidstone'):
            lower = self.unigram_ranking[:size + len(seen)]
        else:
            lower = self.ranking(order - 1, context[1:], size + len(seen))
        candidates = (set(seen) | set(lower)) - {UNKNOWN}
        lower_position = {w: i for i, w in enumerate(lower)}
        ordered = sorted(
            candidates,
            key=lambda w: (-self.probability_at(order, context, w), lower_position.get(w, len(lower)), w))

        cached_size = max(size, 2 * (cached[0] if cached else 0))
        self.ranking_cache[key] = (cached_size, ordered[:cached_size])
        return ordered[:size]

    def predict(self, context, k=5):
        self.prepare()
        ranked = self.ranking(self.n, self.context_of(context), k + 1)
        return [w for w in ranked if w != END][:k]

    # ------------------------------------------------------------------ generation

    def sample(self, order, context, rng):
        if order == 0:
            return rng.choice(self.vocabulary_list)
        counts = self.base[order].get(context)
        total = self.totals[order].get(context, 0)

        if self.smoothing in ('laplace', 'lidstone'):
            seen_mass = total / (total + self.k * len(self.vocabulary))
            if total and rng.random() < seen_mass:
                return rng.choices(list(counts), weights=list(counts.values()))[0]
            return rng.choice(self.vocabulary_list)

        if total:
            types = len(counts)
            discount = self.discounts[order]
            seen_mass = 1 - discount * types / total
            weights = [max(c - discount, 0) for c in counts.values()]
            if rng.random() < seen_mass:
                return rng.choices(list(counts), weights=weights)[0]
        return self.sample(order - 1, context[1:], rng)

    def generate(self, seed, rng, max_tokens=40, min_tokens=0):
        self.prepare()
        tokens = list(self.context_of(seed))
        generated = []
        while len(generated) < max_tokens:
            word = self.sample(self.n, tuple(tokens[-(self.n - 1):]), rng)
            if word == UNKNOWN or (word == END and len(generated) < min_tokens):
                continue
            if word == END:
                return generated, True
            generated.append(word)
            tokens.append(word)
        return generated, False

    # ------------------------------------------------------------------ persistence

    def save(self, path):
        state = {'n': self.n, 'smoothing': self.smoothing, 'k': self.k,
                 'vocabulary': self.vocabulary, 'counts': self.counts}
        with open(path, 'wb') as f:
            pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, path):
        with open(path, 'rb') as f:
            state = pickle.load(f)
        model = cls.__new__(cls)
        model.__dict__.update(state)
        model.ready = False
        return model

def continuation_counts(higher_counts):
    continuation = defaultdict(Counter)
    for context, counts in higher_counts.items():
        lower = continuation[context[1:]]
        for word in counts:
            lower[word] += 1
    return continuation

def ney_discount(base):
    once = 0
    twice = 0
    for counts in base.values():
        for count in counts.values():
            once += count == 1
            twice += count == 2
    return once / (once + 2 * twice) if once else 0.75
