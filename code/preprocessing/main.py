import argparse
import importlib
import re
import subprocess
import sys
from pathlib import Path

import nltk

PREPROCESSING_DIR = Path(__file__).resolve().parent
STEPS_DIR = PREPROCESSING_DIR / 'steps'
RESOURCES_DIR = PREPROCESSING_DIR / 'resources'

WORD = re.compile(r'[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)*')

sys.path.insert(0, str(STEPS_DIR))

def step(name):
    return importlib.import_module(name)

def title(text):
    print(f'\n=== {text}')

def corpus_stats(directory):
    words = 0
    vocabulary = set()
    sentences = 0
    books = 0
    for path in Path(directory).rglob('*.txt'):
        text = path.read_text(encoding='utf-8', errors='replace')
        tokens = [w.lower() for w in WORD.findall(text)]
        words += len(tokens)
        vocabulary.update(tokens)
        sentences += len(nltk.sent_tokenize(text, language='portuguese'))
        books += 1
    return {'books': books, 'words': words, 'vocabulary': len(vocabulary), 'sentences': sentences}

def print_stats(stages):
    print(f"{'stage':<20} {'books':>5} {'words':>10} {'vocabulary':>11} {'change':>8} {'sentences':>10} {'change':>8}")
    previous = None
    for name, stats in stages:
        vocabulary_change = sentences_change = ''
        if previous:
            vocabulary_change = f"{stats['vocabulary'] - previous['vocabulary']:+d}"
            sentences_change = f"{stats['sentences'] - previous['sentences']:+d}"
        print(f"{name:<20} {stats['books']:>5} {stats['words']:>10} {stats['vocabulary']:>11} "
              f"{vocabulary_change:>8} {stats['sentences']:>10} {sentences_change:>8}")
        previous = stats

def run(raw_dir, work_dir, clean_dir, manual_cuts=None, final_dir=None):
    work_dir = Path(work_dir)
    txt_dir = work_dir / '01_txt'
    pdf_fix_dir = work_dir / '03_pdf_fix'
    page_breaks_dir = work_dir / '09_page_breaks'
    normalized_dir = work_dir / '04_normalization'
    orthography_dir = work_dir / '06_orthography'
    nltk.download('punkt_tab', quiet=True)
    stages = []

    title('01 File conversion')
    subprocess.run(['bash', str(STEPS_DIR / '01_file_conversion.sh'), str(raw_dir), str(txt_dir)], check=True)
    stages.append(('01 conversion', corpus_stats(txt_dir)))

    title('02 Variety clues')
    variety = step('02_variety_clues')
    variety.print_report(variety.variety_clues(txt_dir, RESOURCES_DIR / '02_variety_clues.json'))

    title('03 PDF fix')
    pdf_fix = step('03_pdf_fix')
    pdf_fix.print_report(pdf_fix.pdf_fix(txt_dir, pdf_fix_dir, RESOURCES_DIR / '03_clitics.json'))
    stages.append(('03 PDF fix', corpus_stats(pdf_fix_dir)))

    title('09 Page breaks')
    page_breaks = step('09_page_breaks')
    page_breaks.print_report(
        page_breaks.page_breaks(pdf_fix_dir, page_breaks_dir, RESOURCES_DIR / '03_clitics.json'))
    stages.append(('09 page breaks', corpus_stats(page_breaks_dir)))

    title('04 Normalization')
    normalization = step('04_normalization')
    normalization.print_report(normalization.normalization(page_breaks_dir, normalized_dir))
    stages.append(('04 normalization', corpus_stats(normalized_dir)))

    title('05 Silent consonants')
    silent = step('05_silent_consonants')
    silent.print_report(silent.silent_consonants(normalized_dir, RESOURCES_DIR / '05_spelling_pairs.json'), top=20)

    title('06 Orthography')
    orthography = step('06_orthography')
    orthography.print_report(orthography.orthography(
        normalized_dir,
        orthography_dir,
        RESOURCES_DIR / '05_spelling_pairs.json',
        RESOURCES_DIR / '06_explicit_spellings.json',
        RESOURCES_DIR / '06_months.json'
    ))
    stages.append(('06 orthography', corpus_stats(orthography_dir)))

    title('07 OCR fix')
    ocr = step('07_ocr_fix')
    ocr.print_report(ocr.ocr_fix(orthography_dir, clean_dir, RESOURCES_DIR / '07_ocr_confusions.json'))
    stages.append(('07 OCR fix', corpus_stats(clean_dir)))

    if manual_cuts and final_dir:
        title('08 Manual cuts')
        cuts = step('08_manual_cuts')
        cuts.print_report(cuts.manual_cuts(clean_dir, final_dir, manual_cuts))
        stages.append(('08 manual cuts', corpus_stats(final_dir)))

    title('Corpus after each step')
    print_stats(stages)
    print(f'\nClean corpus in {clean_dir}')
    if manual_cuts and final_dir:
        print(f'Final corpus (with manual cuts) in {final_dir}')

def main():
    parser = argparse.ArgumentParser(description='Run all preprocessing steps, from the original books to the clean corpus.')
    parser.add_argument('raw_dir', help='directory with the original books (scanned ones in the ocr/ subdirectory)')
    parser.add_argument('work_dir', help='directory for the intermediate results of each step')
    parser.add_argument('clean_dir', help='directory where the clean corpus is written')
    parser.add_argument('--manual-cuts', help='JSON with the manual cuts to apply after the automatic steps')
    parser.add_argument('--final-dir', help='directory where the corpus with the manual cuts is written')
    args = parser.parse_args()

    run(args.raw_dir, args.work_dir, args.clean_dir, args.manual_cuts, args.final_dir)

if __name__ == '__main__':
    main()
