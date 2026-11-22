import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from domain.Clue import load_clues

PAGE_BREAK = '\f'

def credits_sample(text, sample_size, credits_pages):
    pages = text.split(PAGE_BREAK)
    if len(pages) > 1:
        first, last = credits_pages
        credits = PAGE_BREAK.join(pages[first - 1:last])
        if credits.strip():
            return credits[:sample_size]
    return text[:sample_size]

def text_samples(text, sample_size, text_positions):
    samples = []
    for position in text_positions:
        start = len(text) * position // 100
        samples.append(text[start:start + sample_size])
    return samples

def find_clues(clues, credits, texts):
    found = []
    for clue in clues:
        samples = [credits] if clue.scope == 'credits' else texts
        matches = []
        for sample in samples:
            for match in re.finditer(clue.pattern, sample, re.IGNORECASE):
                matches.append(match.group(0))
        if matches:
            found.append((clue, matches))
    return found

def summarize(found):
    totals = {(v, s): 0 for v in ('PE', 'PB') for s in ('credits', 'text')}
    for clue, matches in found:
        totals[(clue.variety, clue.scope)] += len(matches)
    return totals

def variety_clues(
        txt_dir, 
        clues_path, 
        sample_size=3000, 
        text_positions=(25, 50, 75),
        credits_pages=(2, 6)
    ):

    clues = load_clues(clues_path)

    results = {}
    for txt_path in sorted(Path(txt_dir).rglob('*.txt')):
        text = txt_path.read_text(encoding='utf-8', errors='replace')
        credits = credits_sample(text, sample_size, credits_pages)
        texts = text_samples(text, sample_size, text_positions)
        found = find_clues(clues, credits, texts)
        results[txt_path.stem] = (summarize(found), found)
    return results

def print_report(results):
    print(f"{'book':<40} {'text PE':>7} {'text PB':>7} {'ed. PE':>6} {'ed. PB':>6}")
    for title, (totals, found) in results.items():
        print(f"{title[:40]:<40} {totals[('PE', 'text')]:>7} {totals[('PB', 'text')]:>7} "
              f"{totals[('PE', 'credits')]:>6} {totals[('PB', 'credits')]:>6}")
        for clue, matches in found:
            print(f"{'':<4}{clue.variety} {clue.category:<10} ({clue.strength}): {', '.join(matches[:3])}")

def main():
    parser = argparse.ArgumentParser(description='Collect PE vs. PB clues in each book.')
    parser.add_argument('txt_dir', help='directory with the converted .txt files')
    parser.add_argument('clues_json', help='JSON file with the clues')
    parser.add_argument('--sample-size', type=int, default=3000,
                        help='characters in each sample (default: 3000)')
    parser.add_argument('--text-positions', type=int, nargs='+', default=[25, 50, 75],
                        help='positions of the text samples, in %% of the book (default: 25 50 75)')
    parser.add_argument('--credits-pages', type=int, nargs=2, default=[2, 6], metavar=('FIRST', 'LAST'),
                        help='pages read as credits in books that came from PDF (default: 2 6)')
    args = parser.parse_args()

    results = variety_clues(
        args.txt_dir, 
        args.clues_json, 
        args.sample_size,
        args.text_positions, 
        args.credits_pages
    )
    print_report(results)

if __name__ == '__main__':
    main()
