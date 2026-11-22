import argparse
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus import load_sentences, select_books, tokenize
from domain.Question import load_questions
from ngram_model import NgramModel

def detokenize(tokens):
    text = ' '.join(tokens)
    text = re.sub(r' ([,.;:!?»)\]…])', r'\1', text)
    text = re.sub(r'([«(\[]) ', r'\1', text)
    return text

def predict(model, text, k):
    return model.predict(tokenize(text), k)

def generate(model, text, rng, max_tokens):
    seed = tokenize(text)
    generated, _ = model.generate(seed, rng, max_tokens)
    return detokenize(seed + generated)

def answer_questions(model, questions_path, rng, answers, max_tokens):
    results = []
    for question in load_questions(questions_path):
        texts = []
        for _ in range(answers):
            texts.append(generate(model, question.prefix, rng, max_tokens))
        results.append((question.text, texts))
    return results

def evaluate(model, corpus_dir, titles):
    sentences = load_sentences(select_books(corpus_dir, titles))
    return model.perplexity(sentences)

def main():
    parser = argparse.ArgumentParser(description='Use a trained n-gram model.')
    parser.add_argument('model', help='file with the trained model')
    subparsers = parser.add_subparsers(dest='command', required=True)

    p = subparsers.add_parser('predict', help='most likely next words')
    p.add_argument('text')
    p.add_argument('-k', type=int, default=5, help='number of words (default: 5)')

    p = subparsers.add_parser('generate', help='continue a text')
    p.add_argument('text')
    p.add_argument('--max-tokens', type=int, default=40)
    p.add_argument('--seed', type=int, help='random seed, for reproducible output')

    p = subparsers.add_parser('questions', help='answer the questions of a JSON file')
    p.add_argument('questions_json')
    p.add_argument('--answers', type=int, default=3, help='answers per question (default: 3)')
    p.add_argument('--max-tokens', type=int, default=40)
    p.add_argument('--seed', type=int, help='random seed, for reproducible output')

    p = subparsers.add_parser('perplexity', help='perplexity of the model on some books')
    p.add_argument('corpus_dir')
    p.add_argument('--books', nargs='+', metavar='TITLE', help='titles of the books (default: all)')

    args = parser.parse_args()
    model = NgramModel.load(args.model)

    if args.command == 'predict':
        print(', '.join(predict(model, args.text, args.k)))
    elif args.command == 'generate':
        print(generate(model, args.text, random.Random(args.seed), args.max_tokens))
    elif args.command == 'questions':
        rng = random.Random(args.seed)
        for question, texts in answer_questions(model, args.questions_json, rng, args.answers, args.max_tokens):
            print(f'\n# {question}')
            for text in texts:
                print(f'   {text}')
    elif args.command == 'perplexity':
        print(f'{evaluate(model, args.corpus_dir, args.books):.1f}')

if __name__ == '__main__':
    main()
