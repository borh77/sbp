from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pymongo import MongoClient


DEFAULT_CONFIG = Path("config/db_config.example.json")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print basic collection counts for v1 and v2 databases.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> None:
    config = load_config(parse_args().config)
    client = MongoClient(config["mongo_uri"])
    for database, collections in {
        config["database_v1"]: ["v1_users", "v1_wellbeing_assessments"],
        config["database_v2"]: ["v2_users", "v2_wellbeing_assessments"],
    }.items():
        db = client[database]
        print(database)
        for collection in collections:
            print(f"  {collection}: {db[collection].count_documents({})}")


if __name__ == "__main__":
    main()
