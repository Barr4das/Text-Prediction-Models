import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class SpellingPair:
    pre_agreement: str
    post_agreement: str

def load_spelling_pairs(path):
    with Path(path).open(encoding='utf-8') as f:
        data = json.load(f)

    pairs = []
    for item in data:
        pair = SpellingPair(**item)
        pairs.append(pair)
    return pairs
