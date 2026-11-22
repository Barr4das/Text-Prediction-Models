import argparse
import re
import unicodedata
from pathlib import Path

SOFT_HYPHEN = '­'

def normalize(text):
    text = unicodedata.normalize('NFC', text)
    text = text.replace(SOFT_HYPHEN, '')
    text = re.sub(r'[ \t ]+', ' ', text)

    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
    return '\n'.join(lines) + '\n'

def normalization(input_dir, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for path in sorted(Path(input_dir).rglob('*.txt')):
        text = path.read_text(encoding='utf-8', errors='replace')
        normalized = normalize(text)
        target = output_dir / path.relative_to(input_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(normalized, encoding='utf-8')
        results[path.stem] = (text.count('\n'), normalized.count('\n'))
    return results

def print_report(results):
    print(f"{'book':<40} {'lines':>8} {'->':>8}")
    for title, (lines_before, lines_after) in results.items():
        print(f"{title[:40]:<40} {lines_before:>8} {lines_after:>8}")

def main():
    parser = argparse.ArgumentParser(description='Normalise Unicode and whitespace, one paragraph per line.')
    parser.add_argument('input_dir', help='directory with the .txt files')
    parser.add_argument('output_dir', help='directory where the normalised .txt files are written')
    args = parser.parse_args()

    results = normalization(args.input_dir, args.output_dir)
    print_report(results)

if __name__ == '__main__':
    main()
