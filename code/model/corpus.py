import json
from pathlib import Path

import nltk

def tokenize(text):
    return nltk.word_tokenize(text, language='portuguese')

def split_sentences(text):
    sentences = []
    for sentence in nltk.sent_tokenize(text, language='portuguese'):
        tokens = tokenize(sentence)
        if tokens:
            sentences.append(tokens)
    return sentences

def available_books(corpus_dir):
    books = {}
    for path in sorted(Path(corpus_dir).rglob('*.txt')):
        books[path.stem] = path
    return books

def select_books(corpus_dir, titles=None, titles_path=None):
    books = available_books(corpus_dir)
    wanted = list(titles or [])
    if titles_path:
        with Path(titles_path).open(encoding='utf-8') as f:
            wanted += json.load(f)
    if not wanted:
        return books
    missing = [t for t in wanted if t not in books]
    if missing:
        raise ValueError(f'books not found in {corpus_dir}: {", ".join(missing)}')
    return {title: books[title] for title in wanted}

def load_sentences(book_paths):
    nltk.download('punkt_tab', quiet=True)
    sentences = []
    for path in book_paths.values():
        sentences += split_sentences(path.read_text(encoding='utf-8'))
    return sentences
