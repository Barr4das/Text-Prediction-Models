import argparse
import itertools
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TOKEN = re.compile(r'[A-Za-zÀ-ÿ0-9]*[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*')

@dataclass(frozen=True)
class CorrectionRules:
    confusions: dict
    max_edits: int
    min_reference_count: int
    min_frequency_ratio: int

def load_json(path):
    with Path(path).open(encoding='utf-8') as f:
        return json.load(f)

def candidates(word, edits, confusions):
    positions = [i for i, c in enumerate(word) if c in confusions]
    for chosen in itertools.combinations(positions, edits):
        for replacement in itertools.product(*(confusions[word[i]] for i in chosen)):
            chars = list(word)
            for i, r in zip(chosen, replacement):
                chars[i] = r
            yield ''.join(chars)

def best_correction(word, reference, rules):
    minimum = max(rules.min_reference_count, rules.min_frequency_ratio * reference[word])
    for edits in range(1, rules.max_edits + 1):
        found = []
        for candidate in candidates(word, edits, rules.confusions):
            if reference[candidate] >= minimum:
                found.append(candidate)
        if found:
            return max(found, key=lambda c: reference[c])
    return None

def capital_i_correction(word, reference, rules):
    with_l = 'l' + word[1:]
    if reference[with_l] >= rules.min_reference_count:
        return with_l
    return best_correction(with_l, reference, rules)

def same_letter(a, b):
    def base(c):
        return unicodedata.normalize('NFD', c)[0].lower()
    return base(a) == base(b)

def match_case(original, replacement):
    if not same_letter(original[0], replacement[0]):
        return replacement
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement

def unknown_rate(text, reference, rules):
    tokens = [t.lower() for t in TOKEN.findall(text)]
    unknown = sum(1 for t in tokens if reference[t] < rules.min_reference_count)
    return unknown / max(len(tokens), 1)

def fix_book(text, reference, rules, stats):
    cache = {}

    def replace(match):
        token = match.group(0)
        word = token.lower()
        if reference[word] >= rules.min_reference_count or len(word) < 2:
            return token

        starts_with_capital_i = token[0] == 'I'
        key = (word, starts_with_capital_i)
        if key not in cache:
            correction = best_correction(word, reference, rules)
            if not correction and starts_with_capital_i:
                correction = capital_i_correction(word, reference, rules)
            cache[key] = correction

        correction = cache[key]
        if not correction:
            return token
        stats['corrections'] += 1
        stats['examples'][f'{word} -> {correction}'] += 1
        return match_case(token, correction)

    return TOKEN.sub(replace, text)

def is_ocr_book(relative_path, ocr_subdir):
    return relative_path.parts[0] == ocr_subdir

def ocr_fix(
        input_dir,
        output_dir,
        confusions_path,
        ocr_subdir='ocr',
        max_edits=3,
        min_reference_count=3,
        min_frequency_ratio=10
    ):

    rules = CorrectionRules(load_json(confusions_path), max_edits, min_reference_count, min_frequency_ratio)
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    texts = {}
    for path in sorted(input_dir.rglob('*.txt')):
        texts[path.relative_to(input_dir)] = path.read_text(encoding='utf-8', errors='replace')

    reference = Counter()
    for relative_path, text in texts.items():
        if not is_ocr_book(relative_path, ocr_subdir):
            reference.update(t.lower() for t in TOKEN.findall(text))

    results = {}
    for relative_path, text in texts.items():
        stats = None
        if is_ocr_book(relative_path, ocr_subdir):
            stats = Counter()
            stats['examples'] = Counter()
            stats['unknown_before'] = unknown_rate(text, reference, rules)
            text = fix_book(text, reference, rules, stats)
            stats['unknown_after'] = unknown_rate(text, reference, rules)
        target = output_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        results[relative_path.stem] = stats
    return results

def print_report(results):
    print(f"{'book':<40} {'unknown':>8} {'->':>7} {'fixes':>6}  most frequent")
    for title, stats in results.items():
        if stats is None:
            continue
        top = ', '.join(f'{e} ({n})' for e, n in stats['examples'].most_common(4))
        print(f"{title[:40]:<40} {stats['unknown_before']:>8.1%} {stats['unknown_after']:>7.1%} "
              f"{stats['corrections']:>6}  {top}")
    copied = sum(1 for stats in results.values() if stats is None)
    print(f'\n{copied} books outside the OCR subdirectory copied unchanged')

def main():
    parser = argparse.ArgumentParser(description='Correct OCR errors in scanned books.')
    parser.add_argument('input_dir', help='directory with the .txt files')
    parser.add_argument('output_dir', help='directory where the corrected .txt files are written')
    parser.add_argument('confusions_json', help='JSON with the characters the OCR confuses')
    parser.add_argument('--ocr-subdir', default='ocr',
                        help='subdirectory with the scanned books (default: ocr)')
    parser.add_argument('--max-edits', type=int, default=3,
                        help='maximum characters changed in a word (default: 3)')
    parser.add_argument('--min-reference-count', type=int, default=3,
                        help='occurrences in the reference books for a word to count as known (default: 3)')
    parser.add_argument('--min-frequency-ratio', type=int, default=10,
                        help='how much more frequent the correction must be than the word (default: 10)')
    args = parser.parse_args()

    results = ocr_fix(
        args.input_dir,
        args.output_dir,
        args.confusions_json,
        args.ocr_subdir,
        args.max_edits,
        args.min_reference_count,
        args.min_frequency_ratio
    )
    print_report(results)

if __name__ == '__main__':
    main()
