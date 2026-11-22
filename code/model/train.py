import argparse
import time
from pathlib import Path

from corpus import load_sentences, select_books
from ngram_model import SMOOTHINGS, NgramModel

def train(
        corpus_dir,
        output_path,
        n=3,
        smoothing='kneser_ney',
        lidstone_k=0.01,
        titles=None,
        titles_path=None
    ):

    books = select_books(corpus_dir, titles, titles_path)
    sentences = load_sentences(books)

    model = NgramModel(n, smoothing, lidstone_k)
    model.train(sentences)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(output_path)
    return model, books, sentences

def main():
    parser = argparse.ArgumentParser(description='Train an n-gram language model on a selection of books.')
    parser.add_argument('corpus_dir', help='directory with the clean .txt files')
    parser.add_argument('output', help='file where the trained model is saved')
    parser.add_argument('-n', type=int, default=3, help='n-gram order (default: 3)')
    parser.add_argument('--smoothing', choices=SMOOTHINGS, default='kneser_ney',
                        help='smoothing technique (default: kneser_ney)')
    parser.add_argument('--lidstone-k', type=float, default=0.01,
                        help='value added to each count with Lidstone smoothing (default: 0.01)')
    parser.add_argument('--books', nargs='+', metavar='TITLE',
                        help='titles of the books to train on (default: all)')
    parser.add_argument('--books-json', help='JSON list with the titles of the books to train on')
    args = parser.parse_args()

    start = time.time()
    model, books, sentences = train(args.corpus_dir, args.output, args.n, args.smoothing,
                                    args.lidstone_k, args.books, args.books_json)

    print(f'books:      {len(books)} ({", ".join(books) if len(books) <= 5 else "…"})')
    print(f'sentences:  {len(sentences)}')
    print(f'tokens:     {sum(len(s) for s in sentences)}')
    print(f'vocabulary: {len(model.vocabulary)}')
    print(f'model:      n={model.n}, smoothing={model.smoothing}')
    print(f'saved in {args.output} ({time.time() - start:.0f}s)')

if __name__ == '__main__':
    main()
