import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Clue:
    variety: str
    category: str
    pattern: str
    strength: str
    scope: str

def load_clues(path):
    with Path(path).open(encoding='utf-8') as f:
        data = json.load(f)

    clues = []
    for item in data:
        clue = Clue(**item)
        clues.append(clue)
    return clues
