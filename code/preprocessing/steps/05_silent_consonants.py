import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from domain.SpellingPair import load_spelling_pairs

CONSONANT_CLUSTER = re.compile(r'\b\w*(?:cç|pç|ct|pt|ec[tç]|ap[tç])\w*\b')

def count_clusters(text):
    return Counter(CONSONANT_CLUSTER.findall(text))

def count_pairs(text, pairs):
    pre_agreement = 0
    post_agreement = Counter()
    for pair in pairs:
        pre_agreement += len(re.findall(rf'\b{pair.pre_agreement}\b', text))
        found = len(re.findall(rf'\b{pair.post_agreement}\b', text))
        if found:
            post_agreement[pair.post_agreement] = found
    return pre_agreement, post_agreement

def silent_consonants(input_dir, pairs_path):
    pairs = load_spelling_pairs(pairs_path)

    results = {}
    for path in sorted(Path(input_dir).rglob('*.txt')):
        text = path.read_text(encoding='utf-8', errors='replace').lower()
        clusters = count_clusters(text)
        pre_agreement, post_agreement = count_pairs(text, pairs)
        results[path.stem] = {
            'words': len(text.split()),
            'clusters': clusters,
            'pre_agreement': pre_agreement,
            'post_agreement': post_agreement,
        }
    return results

def print_report(results, top):
    print(f"{'book':<40} {'words':>8} {'clusters':>8} {'/1000':>6} {'pre-AO':>6} {'AO90':>5}  AO90 forms")
    total = Counter()
    for title, r in results.items():
        n_clusters = sum(r['clusters'].values())
        n_post = sum(r['post_agreement'].values())
        forms = ', '.join(f'{w} {n}' for w, n in r['post_agreement'].most_common(4))
        print(f"{title[:40]:<40} {r['words']:>8} {n_clusters:>8} {1000 * n_clusters / r['words']:>6.1f} "
              f"{r['pre_agreement']:>6} {n_post:>5}  {forms}")
        total.update(r['clusters'])

    print(f'\nMost frequent words with consonant clusters ({len(total)} forms, {sum(total.values())} occurrences):')
    print(', '.join(f'{w} {n}' for w, n in total.most_common(top)))

def main():
    parser = argparse.ArgumentParser(description='Find which books follow the 1990 Orthographic Agreement.')
    parser.add_argument('input_dir', help='directory with the .txt files')
    parser.add_argument('pairs_json', help='JSON file with pre-/post-1990 spelling pairs')
    parser.add_argument('--top', type=int, default=20,
                        help='number of most frequent cluster words to show (default: 20)')
    args = parser.parse_args()

    results = silent_consonants(args.input_dir, args.pairs_json)
    print_report(results, args.top)

if __name__ == '__main__':
    main()
