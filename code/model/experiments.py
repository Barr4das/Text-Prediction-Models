import argparse
import re
import json
import random
import sys
import time
from pathlib import Path

import nltk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus import available_books, tokenize
from domain.Question import load_questions
from ngram_model import SMOOTHINGS, NgramModel
from use import detokenize

def book_sentences(path):
    return text_sentences(path.read_text(encoding='utf-8'))

def text_sentences(text):
    strings, tokens = [], []
    for sentence in nltk.sent_tokenize(text, language='portuguese'):
        words = tokenize(sentence)
        if words:
            strings.append(sentence)
            tokens.append(words)
    return strings, tokens

def train_model(sentences_by_book, titles, n=3, smoothing='kneser_ney'):
    model = NgramModel(n, smoothing)
    for title in titles:
        model.train(sentences_by_book[title])
    return model

def set_smoothing(model, smoothing, lidstone_k=0.01):
    model.smoothing = smoothing
    model.k = 1.0 if smoothing == 'laplace' else lidstone_k
    model.ready = False

def top5_accuracy(model, sentences):
    hits = total = 0
    for sentence in sentences:
        for i in range(len(sentence)):
            hits += sentence[i] in model.predict(sentence[:i], 5)
            total += 1
    return hits / total

def unknown_rate(model, sentences):
    words = [w for s in sentences for w in s]
    return sum(1 for w in words if w not in model.vocabulary) / len(words)

def answers(model, prefixes, seed, max_tokens=25):
    rng = random.Random(seed)
    result = {}
    for prefix in prefixes:
        seed_tokens = tokenize(prefix)
        generated, _ = model.generate(seed_tokens, rng, max_tokens)
        result[prefix] = {'next_words': model.predict(seed_tokens, 5),
                          'generated': detokenize(seed_tokens + generated)}
    return result

def experiment_books(sentences_by_book, order, test, sizes):
    rows = []
    for size in sizes:
        titles = order[:size]
        model = train_model(sentences_by_book, titles)
        rows.append({'books': size,
                     'tokens': sum(len(s) for t in titles for s in sentences_by_book[t]),
                     'vocabulary': len(model.vocabulary),
                     'unknown_in_test': unknown_rate(model, test),
                     'perplexity': model.perplexity(test),
                     'top5': top5_accuracy(model, test)})
        print(f"  {size:>2} books: perplexity {rows[-1]['perplexity']:.1f}, top-5 {rows[-1]['top5']:.1%}", flush=True)
    return rows

def experiment_smoothing(sentences_by_book, titles, test, ns):
    rows = []
    for n in ns:
        model = train_model(sentences_by_book, titles, n)
        for smoothing in SMOOTHINGS:
            set_smoothing(model, smoothing)
            rows.append({'n': n, 'smoothing': smoothing,
                         'perplexity': model.perplexity(test), 'top5': top5_accuracy(model, test)})
            print(f"  n={n} {smoothing:<12} perplexity {rows[-1]['perplexity']:.1f}, top-5 {rows[-1]['top5']:.1%}", flush=True)
        del model
    return rows

def experiment_book_prompts(sentences_by_book, titles, book_prompts, seed):
    rows = []
    for item in book_prompts:
        book = item['book']
        prompt = item['prompt']
        with_book = train_model(sentences_by_book, titles)
        without_book = train_model(sentences_by_book, [t for t in titles if t != book])
        rows.append({'book': book, 'prompt': prompt,
                     'with_book': answers(with_book, [prompt], seed)[prompt],
                     'without_book': answers(without_book, [prompt], seed)[prompt]})
        print(f"  {prompt}: {rows[-1]['with_book']['next_words']} | sem o livro: {rows[-1]['without_book']['next_words']}", flush=True)
    return rows

def answer_metrics(answer, prefix, topic_words):
    continuation = answer[len(prefix):].lower()
    words = set(re.findall(r'[a-zà-ÿ]+', continuation))
    return {'on_topic': bool(words & set(topic_words)),
            'complete_sentence': bool(re.search(r'[.!?…][»")]*\s*$', answer.strip()))}

def ngram_answers(model, prefix, samples, seed, max_tokens=25):
    texts = []
    for i in range(samples):
        rng = random.Random(seed + i)
        seed_tokens = tokenize(prefix)
        generated, _ = model.generate(seed_tokens, rng, max_tokens)
        texts.append(detokenize(seed_tokens + generated))
    return texts

def question_evaluation(final_model, questions, samples, seed):
    systems = {'ngram_final': {}}
    for q in questions:
        systems['ngram_final'][q.prefix] = ngram_answers(final_model, q.prefix, samples, seed)

    rows = []
    for q in questions:
        row = {'question': q.text, 'prefix': q.prefix, 'systems': {}}
        for name, answers_by_prefix in systems.items():
            texts = answers_by_prefix[q.prefix]
            metrics = [answer_metrics(t, q.prefix, q.topics) for t in texts]
            row['systems'][name] = {
                'answers': texts,
                'on_topic': sum(m['on_topic'] for m in metrics),
                'complete_sentence': sum(m['complete_sentence'] for m in metrics),
            }
            print(f"  {q.text[:40]:<40} {name:<16} tema {row['systems'][name]['on_topic']}/{samples}, "
                  f"frase completa {row['systems'][name]['complete_sentence']}/{samples}", flush=True)
        rows.append(row)
    return rows

def main():
    parser = argparse.ArgumentParser(description='Experiments for the presentation (test book never used in training).')
    parser.add_argument('corpus_dir')
    parser.add_argument('questions_json')
    parser.add_argument('output_json')
    parser.add_argument('--test-book', default='Caim')
    parser.add_argument('--test-sentences', type=int, default=300,
                        help='sentences of the test book used for evaluation (default: 300)')
    parser.add_argument('--book-prompts-json', default='code/model/resources/book_prompts.json')
    parser.add_argument('--sizes', type=int, nargs='+', default=[1, 3, 6, 12, 18])
    parser.add_argument('--ns', type=int, nargs='+', default=[2, 3, 4])
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--final-n', type=int, default=4, help='n of the final model (default: 4)')
    parser.add_argument('--final-smoothing', choices=SMOOTHINGS, default='kneser_ney',
                        help='smoothing of the final model (default: kneser_ney)')
    parser.add_argument('--samples', type=int, default=5, help='answers per question and system (default: 5)')
    parser.add_argument('--skip', nargs='*', default=[],
                        choices=['books', 'smoothing', 'prompts', 'questions', 'question_eval'])
    args = parser.parse_args()

    nltk.download('punkt_tab', quiet=True)
    start = time.time()
    paths = available_books(args.corpus_dir)
    strings_by_book, sentences_by_book = {}, {}
    for title, path in paths.items():
        strings_by_book[title], sentences_by_book[title] = book_sentences(path)

    train_titles = [t for t in paths if t != args.test_book]
    order = train_titles[:]
    random.Random(args.seed).shuffle(order)
    test = sentences_by_book[args.test_book][:args.test_sentences]
    questions = load_questions(args.questions_json)
    book_prompts = json.loads(Path(args.book_prompts_json).read_text(encoding='utf-8'))
    prefixes = []
    for q in questions:
        prefixes.append(q.prefix)
    for item in book_prompts:
        prefixes.append(item['prompt'])

    output = Path(args.output_json)
    results = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    results.update({'test_book': args.test_book, 'test_sentences': len(test), 'training_order': order})

    if 'books' not in args.skip:
        print('Number of training books (n=3, Kneser-Ney):')
        results['books'] = experiment_books(sentences_by_book, order, test, args.sizes)
    if 'smoothing' not in args.skip:
        print('Smoothing and n (all training books):')
        results['smoothing'] = experiment_smoothing(sentences_by_book, train_titles, test, args.ns)
    if 'prompts' not in args.skip:
        print('Prompts about books in training (with vs. without the book):')
        results['book_prompts'] = experiment_book_prompts(sentences_by_book, train_titles, book_prompts, args.seed)
    final_model = None
    if 'questions' not in args.skip or 'question_eval' not in args.skip:
        print(f'Final model: all {len(paths)} books, n={args.final_n}, {args.final_smoothing}')
        final_model = train_model(sentences_by_book, list(paths), args.final_n, args.final_smoothing)
        results['final_model'] = {'books': len(paths), 'n': args.final_n, 'smoothing': args.final_smoothing}
    if 'questions' not in args.skip:
        results['questions'] = answers(final_model, prefixes, args.seed)
    if 'question_eval' not in args.skip:
        print('Measurement questions (topic and complete sentence):')
        results['question_evaluation'] = question_evaluation(final_model, questions, args.samples, args.seed)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'\nResults in {output} ({time.time() - start:.0f}s)')

if __name__ == '__main__':
    main()
