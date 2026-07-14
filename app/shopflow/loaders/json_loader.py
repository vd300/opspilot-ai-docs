import json
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_json_files(directory: Path) -> list[Any]:
    items: list[Any] = []
    for path in sorted(directory.glob("*.json")):
        data = load_json_file(path)
        if isinstance(data, list):
            items.extend(data)
        else:
            items.append(data)
    return items

