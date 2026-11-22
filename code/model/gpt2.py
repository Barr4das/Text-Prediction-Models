import argparse
import json
import math
import sys
import time
from pathlib import Path

import nltk
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus import available_books
from domain.Question import load_questions
from experiments import answer_metrics, book_sentences

def load(model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.eval()
    return tokenizer, model

def continue_text(tokenizer, model, prefix, max_new_tokens=30):
    inputs = tokenizer(prefix, return_tensors='pt')
    output = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        top_k=50,
        pad_token_id=tokenizer.eos_token_id,
    )
    return tokenizer.decode(output[0], skip_special_tokens=True)

def perplexity_per_word(
    tokenizer,
    model,
    test_strings,
    test_tokens,
    window=1024,
    stride=512,
):
    ids = tokenizer(' '.join(test_strings), return_tensors='pt').input_ids[0]
    nll = 0.0
    previous_end = 0
    with torch.no_grad():
        for start in range(0, len(ids), stride):
            end = min(start + window, len(ids))
            chunk = ids[start:end].unsqueeze(0)
            targets = chunk.clone()
            targets[:, :previous_end - start] = -100
            loss = model(chunk, labels=targets).loss
            scored = (targets[:, 1:] != -100).sum().item()
            nll += loss.item() * scored
            previous_end = end
            if end == len(ids):
                break
    words = 0
    for sentence in test_tokens:
        words += len(sentence) + 1
    return math.exp(nll / words)

def comparison(
    tokenizer,
    model,
    model_name,
    test_strings,
    test_tokens,
    prefixes,
    seed,
):
    torch.manual_seed(seed)
    perplexity = perplexity_per_word(tokenizer, model, test_strings, test_tokens)
    generated = {}
    for prefix in prefixes:
        generated[prefix] = continue_text(tokenizer, model, prefix)
    parameters = 0
    for p in model.parameters():
        parameters += p.numel()
    return {
        'model': model_name,
        'parameters': parameters,
        'perplexity_per_word': perplexity,
        'generated': generated,
    }

def question_answers(tokenizer, model, prefix, samples, seed):
    texts = []
    for i in range(samples):
        torch.manual_seed(seed + i)
        texts.append(continue_text(tokenizer, model, prefix).replace('\n', ' '))
    return texts

def add_to_question_evaluation(
    tokenizer,
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
        texts = question_answers(tokenizer, model, row['prefix'], samples, seed)
        on_topic = 0
        complete_sentence = 0
        for text in texts:
            metrics = answer_metrics(text, row['prefix'], topics[row['question']])
            on_topic += metrics['on_topic']
            complete_sentence += metrics['complete_sentence']
        row['systems']['gpt2'] = {
            'answers': texts,
            'on_topic': on_topic,
            'complete_sentence': complete_sentence,
        }
        print(f"  {row['question'][:40]:<40} tema {on_topic}/{samples}, "
              f"frase completa {complete_sentence}/{samples}", flush=True)

def main():
    parser = argparse.ArgumentParser(description='Compare a GPT-2 model with the n-gram experiments.')
    parser.add_argument('corpus_dir')
    parser.add_argument('questions_json')
    parser.add_argument('output_json', help='results of experiments.py, updated in place')
    parser.add_argument('--model', default='pierreguillou/gpt2-small-portuguese')
    parser.add_argument('--test-book', default='Caim')
    parser.add_argument('--test-sentences', type=int, default=300,
                        help='sentences of the test book used for evaluation (default: 300)')
    parser.add_argument('--book-prompts-json', default='code/model/resources/book_prompts.json')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--samples', type=int, default=5, help='answers per question (default: 5)')
    args = parser.parse_args()

    nltk.download('punkt_tab', quiet=True)
    start = time.time()
    test_strings, test_tokens = book_sentences(available_books(args.corpus_dir)[args.test_book])
    test_strings = test_strings[:args.test_sentences]
    test_tokens = test_tokens[:args.test_sentences]
    questions = load_questions(args.questions_json)
    prefixes = []
    for q in questions:
        prefixes.append(q.prefix)
    book_prompts = json.loads(Path(args.book_prompts_json).read_text(encoding='utf-8'))
    for item in book_prompts:
        prefixes.append(item['prompt'])

    output = Path(args.output_json)
    results = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    tokenizer, model = load(args.model)

    print(f'Comparison with {args.model}:')
    results['gpt2'] = comparison(tokenizer, model, args.model, test_strings, test_tokens, prefixes, args.seed)
    print(f"  perplexity per word {results['gpt2']['perplexity_per_word']:.1f}")

    if 'question_evaluation' in results:
        print('Measurement questions (topic and complete sentence):')
        add_to_question_evaluation(tokenizer, model, results['question_evaluation'], questions, args.samples, args.seed)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'\nResults in {output} ({time.time() - start:.0f}s)')

if __name__ == '__main__':
    main()
