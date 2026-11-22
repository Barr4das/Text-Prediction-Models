import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Question:
    text: str
    prefix: str
    topics: tuple = ()

def load_questions(path):
    with Path(path).open(encoding='utf-8') as f:
        data = json.load(f)
    questions = []
    for item in data:
        question = Question(
            text=item['text'],
            prefix=item['prefix'],
            topics=tuple(item.get('topics', [])),
        )
        questions.append(question)
    return questions
