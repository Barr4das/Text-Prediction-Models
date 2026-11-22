import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from domain.SpellingPair import load_spelling_pairs

SILENT_CONSONANTS = 'cp'
BEFORE_SILENT = 'çtc'
VOWELS = 'aeiouáéíóúâêôãõ'
WORD = re.compile(r'[A-Za-zÀ-ÿ]+')
HAVER_DE = re.compile(r'\b(hei|hás|há|havemos|haveis|hão)\s+de\b', re.IGNORECASE)

def load_json(path):
    with Path(path).open(encoding='utf-8') as f:
        return json.load(f)

def follows_agreement(text, pairs):
    text = text.lower()
    pre_agreement = 0
    post_agreement = 0
    for pair in pairs:
        pre_agreement += len(re.findall(rf'\b{pair.pre_agreement}\b', text))
        post_agreement += len(re.findall(rf'\b{pair.post_agreement}\b', text))
    return post_agreement > pre_agreement

def pre_agreement_candidates(word):
    candidates = []
    for i in range(1, len(word)):
        if word[i] in BEFORE_SILENT and word[i - 1] in VOWELS:
            for consonant in SILENT_CONSONANTS:
                candidates.append(word[:i] + consonant + word[i:])
    return candidates

def match_case(original, replacement):
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement

def build_word_map(text, reference, explicit_pairs, min_old_in_reference, max_new_in_reference):
    mapping = {}
    for word in set(w.lower() for w in WORD.findall(text)):
        candidates = pre_agreement_candidates(word)
        if not candidates:
            continue
        best = max(candidates, key=lambda c: reference[c])
        if reference[best] >= min_old_in_reference and reference[word] <= max_new_in_reference:
            mapping[word] = best

    for pair in explicit_pairs:
        if reference[pair.pre_agreement] > 0:
            mapping[pair.post_agreement] = pair.pre_agreement
    return mapping

def convert_book(text, mapping, month_pattern, stats):
    def replace_word(match):
        word = match.group(0)
        pre_agreement = mapping.get(word.lower())
        if not pre_agreement:
            return word
        stats['words'] += 1
        stats['examples'][f'{word.lower()} -> {pre_agreement}'] += 1
        return match_case(word, pre_agreement)

    text = WORD.sub(replace_word, text)
    text, stats['haver_de'] = HAVER_DE.subn(lambda m: f'{m.group(1)}-de', text)
    text, stats['months'] = month_pattern.subn(lambda m: m.group(1) + m.group(2).capitalize(), text)
    return text

def orthography(
        input_dir,
        output_dir,
        pairs_path,
        explicit_path,
        months_path,
        min_old_in_reference=3,
        max_new_in_reference=1
    ):

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    pairs = load_spelling_pairs(pairs_path)
    explicit_pairs = load_spelling_pairs(explicit_path)
    months = load_json(months_path)
    month_pattern = re.compile(rf"\b(\d{{1,2}}\s+de\s+)({'|'.join(months)})\b")

    texts = {}
    for path in sorted(input_dir.rglob('*.txt')):
        texts[path.relative_to(input_dir)] = path.read_text(encoding='utf-8', errors='replace')

    agreement_books = {p for p, text in texts.items() if follows_agreement(text, pairs)}
    reference = Counter()
    for relative_path, text in texts.items():
        if relative_path not in agreement_books:
            reference.update(w.lower() for w in WORD.findall(text))

    results = {}
    for relative_path, text in texts.items():
        stats = None
        if relative_path in agreement_books:
            stats = Counter()
            stats['examples'] = Counter()
            mapping = build_word_map(text, reference, explicit_pairs, min_old_in_reference,
                                     max_new_in_reference)
            text = convert_book(text, mapping, month_pattern, stats)
        target = output_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        results[relative_path.stem] = stats
    return results

def print_report(results):
    print(f"{'book':<40} {'words':>6} {'haver de':>8} {'months':>6}  most frequent")
    for title, stats in results.items():
        if stats is None:
            continue
        top = ', '.join(f'{e} ({n})' for e, n in stats['examples'].most_common(4))
        print(f"{title[:40]:<40} {stats['words']:>6} {stats['haver_de']:>8} {stats['months']:>6}  {top}")
    unchanged = sum(1 for stats in results.values() if stats is None)
    print(f'\n{unchanged} books in pre-1990 spelling copied unchanged')

def main():
    parser = argparse.ArgumentParser(description='Bring books written with the 1990 Agreement back to pre-1990 spelling.')
    parser.add_argument('input_dir', help='directory with the .txt files')
    parser.add_argument('output_dir', help='directory where the converted .txt files are written')
    parser.add_argument('pairs_json', help='JSON with pre-/post-1990 spelling pairs, used to detect the books')
    parser.add_argument('explicit_json', help='JSON with spellings changed by the Agreement beyond silent consonants')
    parser.add_argument('months_json', help='JSON list with the month names')
    parser.add_argument('--min-old-in-reference', type=int, default=3,
                        help='occurrences of the pre-1990 form in the other books needed to use it (default: 3)')
    parser.add_argument('--max-new-in-reference', type=int, default=1,
                        help='maximum occurrences of the post-1990 form in the other books (default: 1)')
    args = parser.parse_args()

    results = orthography(
        args.input_dir,
        args.output_dir,
        args.pairs_json,
        args.explicit_json,
        args.months_json,
        args.min_old_in_reference,
        args.max_new_in_reference
    )
    print_report(results)

if __name__ == '__main__':
    main()
