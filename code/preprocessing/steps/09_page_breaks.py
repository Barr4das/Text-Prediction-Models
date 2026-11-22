import argparse
import importlib
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
pdf_fix = importlib.import_module('03_pdf_fix')

LONE_NUMBER = re.compile(r'\d{1,4}')
TRAILING_NUMBER = re.compile(r'\s(\d{1,3})$')
SENTENCE_END = re.compile(r'[.!?…:][)»"”\']*$')

def has_trailing_page_numbers(lines, min_trailing_numbers, min_increasing):
    numbers = []
    for line in lines:
        match = TRAILING_NUMBER.search(line)
        if match:
            numbers.append(int(match.group(1)))
    if len(numbers) < min_trailing_numbers:
        return False
    increasing = sum(b > a for a, b in zip(numbers, numbers[1:])) / (len(numbers) - 1)
    return increasing >= min_increasing

def has_broken_layout(lines, strip_trailing, max_open_lines):
    if strip_trailing or any(LONE_NUMBER.fullmatch(line) for line in lines):
        return True
    open_lines = sum(1 for line in lines if not SENTENCE_END.search(line))
    return open_lines / max(len(lines), 1) > max_open_lines

def continues(current, following, max_title_length):
    if current.endswith('-') and (following[:1].isalpha() or following.startswith('-')):
        return True
    if SENTENCE_END.search(current) or current.isupper():
        return False
    if len(current) <= max_title_length and following[:1].isupper():
        return False
    return True

def fix_page_breaks(
        text,
        stats,
        clitics,
        min_trailing_numbers=10,
        min_increasing=0.9,
        max_open_lines=0.3,
        max_title_length=40
    ):

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    strip_trailing = has_trailing_page_numbers(lines, min_trailing_numbers, min_increasing)
    if not has_broken_layout(lines, strip_trailing, max_open_lines):
        return None
    vocabulary = {w.lower() for w in re.findall(r'\w+-\w+', text)}

    paragraphs = []
    current = ''
    for line in lines:
        if LONE_NUMBER.fullmatch(line):
            stats['page_numbers'] += 1
            continue
        if strip_trailing and TRAILING_NUMBER.search(line):
            line = TRAILING_NUMBER.sub('', line)
            stats['trailing_page_numbers'] += 1
        if current and continues(current, line, max_title_length):
            stats['lines_joined'] += 1
            if current.endswith('-'):
                current = pdf_fix.join_hyphen(current, line, vocabulary, clitics, stats)
            else:
                current = f'{current} {line}'
        else:
            if current:
                paragraphs.append(current)
            current = line
    if current:
        paragraphs.append(current)
    return '\n'.join(paragraphs)

def page_breaks(
        input_dir,
        output_dir,
        clitics_path,
        min_trailing_numbers=10,
        min_increasing=0.9,
        max_open_lines=0.3,
        max_title_length=40
    ):

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    clitics = pdf_fix.load_clitics(clitics_path)

    results = {}
    for path in sorted(input_dir.rglob('*.txt')):
        text = path.read_text(encoding='utf-8', errors='replace')
        stats = Counter()
        fixed = fix_page_breaks(text, stats, clitics, min_trailing_numbers, min_increasing,
                                max_open_lines, max_title_length)
        target = output_dir / path.relative_to(input_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(fixed if fixed is not None else text, encoding='utf-8')
        results[path.stem] = stats if fixed is not None else None
    return results

def print_report(results):
    print(f"{'book':<40} {'pages':>6} {'end of line':>11} {'joined':>7}")
    for title, stats in results.items():
        if stats is None:
            continue
        print(f"{title[:40]:<40} {stats['page_numbers']:>6} {stats['trailing_page_numbers']:>11} "
              f"{stats['lines_joined']:>7}")
    unchanged = sum(1 for stats in results.values() if stats is None)
    print(f'\n{unchanged} books without broken layout copied unchanged')

def main():
    parser = argparse.ArgumentParser(description='Remove page breaks left inside books made from printed layouts.')
    parser.add_argument('input_dir', help='directory with the .txt files')
    parser.add_argument('output_dir', help='directory where the fixed .txt files are written')
    parser.add_argument('clitics_json', help='JSON file with the clitic pronouns kept after a hyphen')
    parser.add_argument('--min-trailing-numbers', type=int, default=10,
                        help='numbers at the end of lines needed to treat them as page numbers (default: 10)')
    parser.add_argument('--min-increasing', type=float, default=0.9,
                        help='share of those numbers that must increase (default: 0.9)')
    parser.add_argument('--max-open-lines', type=float, default=0.3,
                        help='share of lines not ending a sentence above which the layout is broken (default: 0.3)')
    parser.add_argument('--max-title-length', type=int, default=40,
                        help='length up to which a line followed by a capital is a title (default: 40)')
    args = parser.parse_args()

    results = page_breaks(
        args.input_dir,
        args.output_dir,
        args.clitics_json,
        args.min_trailing_numbers,
        args.min_increasing,
        args.max_open_lines,
        args.max_title_length
    )
    print_report(results)

if __name__ == '__main__':
    main()
