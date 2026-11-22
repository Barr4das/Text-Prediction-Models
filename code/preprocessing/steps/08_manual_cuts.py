import argparse
import json
from pathlib import Path

def load_cuts(path):
    with Path(path).open(encoding='utf-8') as f:
        return json.load(f)

def cut_book(lines, cut):
    kept = lines[cut['first_line'] - 1:cut['last_line']]
    prefix = cut.get('removed_prefix')
    if prefix:
        if not kept[0].startswith(prefix):
            raise ValueError('the first kept line does not start with the recorded prefix')
        kept[0] = kept[0][len(prefix):]
    if cut.get('join_first_two_lines'):
        kept[0:2] = [kept[0] + ' ' + kept[1]]
    for edit in reversed(cut.get('edits', [])):
        kept[edit['start']:edit['end']] = edit['replacement']
    return kept

def manual_cuts(input_dir, output_dir, cuts_path, overwrite=False):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    cuts = load_cuts(cuts_path)

    results = {}
    for path in sorted(input_dir.rglob('*.txt')):
        relative_path = path.relative_to(input_dir)
        name = str(relative_path.with_suffix(''))
        lines = path.read_text(encoding='utf-8').rstrip('\n').split('\n')

        cut = cuts.get(name)
        status = 'no cut recorded: copied'
        if cut:
            if len(lines) != cut['lines_before']:
                raise ValueError(f'{name}: expected {cut["lines_before"]} lines, found {len(lines)}; '
                                 f'the cuts were recorded on a different version of the corpus')
            lines = cut_book(lines, cut)
            status = f"{cut['lines_before']} -> {len(lines)} lines"

        text = '\n'.join(lines) + '\n'
        target = output_dir / relative_path
        if target.exists() and not overwrite and target.read_text(encoding='utf-8') != text:
            raise FileExistsError(f'{target} has changes that are not in {cuts_path}; '
                                  f'record them first or use --overwrite')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        results[path.stem] = status
    return results

def print_report(results):
    for title, status in results.items():
        print(f'{title[:40]:<40} {status}')

def main():
    parser = argparse.ArgumentParser(description='Apply the recorded manual cuts (paratext) to each book.')
    parser.add_argument('input_dir', help='directory with the clean .txt files')
    parser.add_argument('output_dir', help='directory where the cut .txt files are written')
    parser.add_argument('cuts_json', help='JSON with the lines kept in each book')
    parser.add_argument('--overwrite', action='store_true',
                        help='overwrite output files with changes that are not recorded')
    args = parser.parse_args()

    print_report(manual_cuts(args.input_dir, args.output_dir, args.cuts_json, args.overwrite))

if __name__ == '__main__':
    main()
