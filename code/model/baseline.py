import argparse
import json
import sys
import time
from pathlib import Path

import nltk
from nltk.corpus import machado

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus import available_books
from domain.Question import load_questions
from experiments import (
    answer_metrics,
    book_sentences,
    ngram_answers,
    text_sentences,
    top5_accuracy,
    train_model,
    unknown_rate,
)
from ngram_model import SMOOTHINGS, NgramModel

def machado_sentences(held_out):
    train = []
    for fileid in machado.fileids():
        if fileid != held_out:
            _, tokens = text_sentences(machado.raw(fileid))
            train += tokens
    _, test = text_sentences(machado.raw(held_out))
    return train, test

def corpus_size(sentences):
    tokens = 0
    vocabulary = set()
    for sentence in sentences:
        tokens += len(sentence)
        vocabulary.update(sentence)
    return {'sentences': len(sentences), 'tokens': tokens, 'vocabulary': len(vocabulary)}

def evaluate(model, test):
    return {
        'perplexity': model.perplexity(test),
        'top5': top5_accuracy(model, test),
        'unknown_in_test': unknown_rate(model, test),
    }

def add_to_question_evaluation(
    model,
    rows,
    questions,
    samples,
    seed,
):
    topics = {}
    for q in questions:
        topics[q.text] = q.topics
    for row in rows:
        texts = ngram_answers(model, row['prefix'], samples, seed)
        on_topic = 0
        complete_sentence = 0
        for text in texts:
            metrics = answer_metrics(text, row['prefix'], topics[row['question']])
            on_topic += metrics['on_topic']
            complete_sentence += metrics['complete_sentence']
        row['systems']['machado'] = {
            'answers': texts,
            'on_topic': on_topic,
            'complete_sentence': complete_sentence,
        }
        print(f"  {row['question'][:40]:<40} tema {on_topic}/{samples}, "
              f"frase completa {complete_sentence}/{samples}", flush=True)

def main():
    parser = argparse.ArgumentParser(description='Baseline: the same n-gram model trained on the NLTK machado corpus.')
    parser.add_argument('corpus_dir')
    parser.add_argument('questions_json')
    parser.add_argument('output_json', help='results of experiments.py, updated in place')
    parser.add_argument('--test-book', default='Caim')
    parser.add_argument('--test-sentences', type=int, default=300,
                        help='sentences of each test text used for evaluation (default: 300)')
    parser.add_argument('--machado-test', default='romance/marm08.txt',
                        help='machado file left out of training and used for testing (default: Dom Casmurro)')
    parser.add_argument('-n', type=int, default=4)
    parser.add_argument('--smoothing', choices=SMOOTHINGS, default='kneser_ney')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--samples', type=int, default=5, help='answers per question (default: 5)')
    args = parser.parse_args()

    nltk.download('punkt_tab', quiet=True)
    nltk.download('machado', quiet=True)
    start = time.time()

    paths = available_books(args.corpus_dir)
    saramago_by_book = {}
    for title, path in paths.items():
        _, saramago_by_book[title] = book_sentences(path)
    saramago_titles = [t for t in paths if t != args.test_book]
    saramago_train = []
    for title in saramago_titles:
        saramago_train += saramago_by_book[title]
    machado_train, machado_test = machado_sentences(args.machado_test)

    tests = {
        'saramago': saramago_by_book[args.test_book][:args.test_sentences],
        'machado': machado_test[:args.test_sentences],
    }
    models = {
        'saramago': train_model(saramago_by_book, saramago_titles, args.n, args.smoothing),
        'machado': NgramModel(args.n, args.smoothing),
    }
    models['machado'].train(machado_train)

    result = {
        'n': args.n,
        'smoothing': args.smoothing,
        'test_texts': {'saramago': args.test_book, 'machado': args.machado_test},
        'corpus': {'saramago': corpus_size(saramago_train), 'machado': corpus_size(machado_train)},
        'evaluation': {},
    }
    print('Corpus size (training):')
    for name, size in result['corpus'].items():
        print(f"  {name:<9} {size['tokens']:>9} tokens, vocabulary {size['vocabulary']}, {size['sentences']} sentences")

    print('Model trained on X, tested on Y:')
    for model_name, model in models.items():
        result['evaluation'][model_name] = {}
        for test_name, test in tests.items():
            row = evaluate(model, test)
            result['evaluation'][model_name][test_name] = row
            print(f"  {model_name:<9} -> {test_name:<9} perplexity {row['perplexity']:.1f}, "
                  f"top-5 {row['top5']:.1%}, unknown {row['unknown_in_test']:.1%}", flush=True)

    output = Path(args.output_json)
    results = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    results['machado'] = result

    if 'question_evaluation' in results:
        print('Measurement questions with the machado model (topic and complete sentence):')
        questions = load_questions(args.questions_json)
        add_to_question_evaluation(models['machado'], results['question_evaluation'], questions, args.samples, args.seed)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'\nResults in {output} ({time.time() - start:.0f}s)')

if __name__ == '__main__':
    main()
