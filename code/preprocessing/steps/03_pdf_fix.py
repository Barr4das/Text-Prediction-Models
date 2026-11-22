import argparse
import json
import re
from collections import Counter
from pathlib import Path

PAGE_BREAK = '\f'
SENTENCE_END = tuple('.!?…:»"”')

def load_clitics(path):
    with Path(path).open(encoding='utf-8') as f:
        return set(json.load(f))

def came_from_pdf(text):
    return PAGE_BREAK in text

def header_key(line):
    return re.sub(r'\d+', '#', line.strip().lower())

def page_margins(lines, margin_lines):
    filled = [i for i, line in enumerate(lines) if line.strip()]
    return set(filled[:margin_lines] + filled[-margin_lines:])

def find_headers(pages, min_header_repeats, margin_lines, max_header_length):
    repeats = Counter()
    for lines in pages:
        for i in page_margins(lines, margin_lines):
            line = lines[i].strip()
            if len(line) <= max_header_length:
                repeats[header_key(line)] += 1

    headers = set()
    for key, count in repeats.items():
        letters = sum(c.isalpha() for c in key)
        if count >= min_header_repeats and not key.endswith(SENTENCE_END) and letters >= 4:
            headers.add(key)
    return headers

def remove_page_numbers_and_headers(
        text,
        stats,
        min_header_repeats,
        margin_lines,
        max_header_length
    ):

    pages = [page.split('\n') for page in text.split(PAGE_BREAK)]
    headers = find_headers(pages, min_header_repeats, margin_lines, max_header_length)

    result = []
    for lines in pages:
        margins = page_margins(lines, margin_lines)
        for i, line in enumerate(lines):
            line = line.strip()
            if i in margins and re.fullmatch(r'\d{1,4}', line):
                stats['page_numbers'] += 1
            elif i in margins and header_key(line) in headers:
                stats['headers'] += 1
            else:
                result.append(line)
    return result

def join_hyphen(before, after, vocabulary, clitics, stats):
    if after.startswith('-'):
        stats['hyphens_kept'] += 1
        return before + after[1:]

    fragment = re.match(r'\w*', after).group(0)
    start = re.search(r'(\w*)-$', before).group(1)
    if fragment.lower() in clitics or f'{start}-{fragment}'.lower() in vocabulary:
        stats['hyphens_kept'] += 1
        return before + after

    stats['hyphens_removed'] += 1
    return before[:-1] + after

def continues_paragraph(current, following):
    if current.endswith('-') and (following[:1].isalpha() or following.startswith('-')):
        return True
    if current.endswith(SENTENCE_END):
        return False
    if current.isupper():
        return False
    return current[-1:].isalnum() or current.endswith((',', ';', '—', '–'))

def fix_pdf_text(
        text,
        stats,
        clitics,
        min_header_repeats=8,
        margin_lines=2,
        max_header_length=60
    ):

    lines = remove_page_numbers_and_headers(
        text,
        stats,
        min_header_repeats,
        margin_lines,
        max_header_length
    )
    vocabulary = {w.lower() for w in re.findall(r'\w+-\w+', text)}

    paragraphs = []
    current = ''
    for line in lines:
        if not line:
            continue
        if current and continues_paragraph(current, line):
            stats['lines_joined'] += 1
            if current.endswith('-'):
                current = join_hyphen(current, line, vocabulary, clitics, stats)
            else:
                current = f'{current} {line}'
        else:
            if current:
                paragraphs.append(current)
            current = line
    if current:
        paragraphs.append(current)
    return '\n'.join(paragraphs) + '\n'

def pdf_fix(
        input_dir,
        output_dir,
        clitics_path,
        min_header_repeats=8,
        margin_lines=2,
        max_header_length=60
    ):

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    clitics = load_clitics(clitics_path)

    results = {}
    for path in sorted(Path(input_dir).rglob('*.txt')):
        text = path.read_text(encoding='utf-8', errors='replace')
        stats = None
        if came_from_pdf(text):
            stats = Counter()
            text = fix_pdf_text(text, stats, clitics, min_header_repeats, margin_lines, max_header_length)
        target = output_dir / path.relative_to(input_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        results[path.stem] = stats
    return results

def print_report(results):
    print(f"{'book':<40} {'pages':>6} {'headers':>7} {'hyph. -':>7} {'hyph. =':>7} {'joined':>7}")
    for title, stats in results.items():
        if stats is None:
            print(f"{title[:40]:<40} {'not from PDF: copied':>38}")
            continue
        print(f"{title[:40]:<40} {stats['page_numbers']:>6} {stats['headers']:>7} "
              f"{stats['hyphens_removed']:>7} {stats['hyphens_kept']:>7} {stats['lines_joined']:>7}")

def main():
    parser = argparse.ArgumentParser(description='Fix the defects left by converting PDFs to text.')
    parser.add_argument('input_dir', help='directory with the converted .txt files')
    parser.add_argument('output_dir', help='directory where the fixed .txt files are written')
    parser.add_argument('clitics_json', help='JSON file with the clitic pronouns kept after a hyphen')
    parser.add_argument('--min-header-repeats', type=int, default=8,
                        help='times a line must repeat at the page margins to be a header (default: 8)')
    parser.add_argument('--margin-lines', type=int, default=2,
                        help='lines at the top and bottom of each page searched for headers (default: 2)')
    parser.add_argument('--max-header-length', type=int, default=60,
                        help='maximum length of a header line (default: 60)')
    args = parser.parse_args()

    results = pdf_fix(
        args.input_dir,
        args.output_dir,
        args.clitics_json,
        args.min_header_repeats,
        args.margin_lines,
        args.max_header_length
    )
    print_report(results)

if __name__ == '__main__':
    main()
