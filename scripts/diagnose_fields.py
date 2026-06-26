from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pymongo import MongoClient


DEFAULT_CONFIG = Path("config/db_config.example.json")


V1_NUMERIC_FIELDS = [
    "focus_productivity.focus_sessions",
    "digital_behavior.doomscrolling_duration",
    "digital_behavior.late_night_device_usage",
    "work_environment.workspace_quality",
    "work_environment.remote_work_days",
    "health_wellness.physical_activity",
    "burnout_result.productivity_score",
    "burnout_result.burnout_risk",
    "focus_productivity.concentration_score",
]


V2_BOOLEAN_FIELDS = [
    "computed.late_night_high",
    "computed.workspace_quality_ok",
]


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def numeric_stats(collection, field: str) -> dict[str, Any] | None:
    result = list(
        collection.aggregate(
            [
                {"$match": {field: {"$type": "number"}}},
                {
                    "$group": {
                        "_id": None,
                        "min": {"$min": f"${field}"},
                        "max": {"$max": f"${field}"},
                        "avg": {"$avg": f"${field}"},
                        "count": {"$sum": 1},
                    }
                },
            ]
        )
    )
    return result[0] if result else None


def value_counts(collection, field: str) -> list[dict[str, Any]]:
    return list(
        collection.aggregate(
            [
                {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1, "_id": 1}},
            ]
        )
    )


def late_night_usage_profile(collection) -> dict[str, Any] | None:
    field = "$digital_behavior.late_night_device_usage"
    result = list(
        collection.aggregate(
            [
                {"$match": {"digital_behavior.late_night_device_usage": {"$type": "number"}}},
                {
                    "$group": {
                        "_id": None,
                        "min": {"$min": field},
                        "max": {"$max": field},
                        "avg": {"$avg": field},
                        "count": {"$sum": 1},
                        "non_binary_count": {
                            "$sum": {
                                "$cond": [
                                    {"$in": [field, [0, 1]]},
                                    0,
                                    1,
                                ]
                            }
                        },
                    }
                },
            ]
        )
    )
    return result[0] if result else None


def late_night_usage_type(profile: dict[str, Any]) -> str:
    min_value = profile.get("min")
    max_value = profile.get("max")
    if min_value is None or max_value is None:
        return "unknown"
    if min_value >= 0 and max_value <= 1 and profile.get("non_binary_count", 0) == 0:
        return "binary_indicator"
    if min_value >= 0 and max_value <= 1:
        return "normalized_0_1"
    return "scale_1_10"


def print_late_night_diagnostics(collection) -> None:
    field = "digital_behavior.late_night_device_usage"
    profile = late_night_usage_profile(collection)
    if not profile:
        print(f"  {field}: no numeric values")
        return

    print(f"  {field}:")
    print(
        "    min={min_value}, max={max_value}, avg={avg_value:.4f}, count={count}".format(
            min_value=profile.get("min"),
            max_value=profile.get("max"),
            avg_value=float(profile.get("avg") or 0),
            count=profile.get("count"),
        )
    )
    print(f"    detected_type={late_night_usage_type(profile)}")

    counts = value_counts(collection, field)
    if len(counts) <= 10:
        print("    value_counts:")
        for item in counts:
            print(f"      {item['_id']}: {item['count']}")


def print_numeric_stats(collection, field: str) -> None:
    stats = numeric_stats(collection, field)
    if not stats:
        print(f"  {field}: no numeric values")
        return
    print(
        "  {field}: min={min_value}, max={max_value}, avg={avg_value:.4f}, count={count}".format(
            field=field,
            min_value=stats.get("min"),
            max_value=stats.get("max"),
            avg_value=float(stats.get("avg") or 0),
            count=stats.get("count"),
        )
    )


def print_counts(collection, field: str) -> None:
    counts = value_counts(collection, field)
    if not counts:
        print(f"  {field}: no values")
        return
    print(f"  {field}:")
    for item in counts:
        print(f"    {item['_id']}: {item['count']}")


def print_threshold_count(collection, field: str, threshold: float) -> None:
    count = collection.count_documents({field: {"$lte": threshold}})
    print(f"  count where {field} <= {threshold:g}: {count}")


def print_common_value_counts(collection, include_user_ref: bool = False) -> None:
    print_counts(collection, "burnout_result.productivity_category")
    print_counts(collection, "burnout_result.mental_state")
    if include_user_ref:
        print_counts(collection, "user_ref.device_usage_type")


def diagnose_v1(db_v1, low_productivity_score_threshold: float) -> None:
    collection = db_v1.v1_wellbeing_assessments
    print("V1 v1_wellbeing_assessments")
    print(f"  documents: {collection.count_documents({})}")
    print_late_night_diagnostics(collection)
    for field in V1_NUMERIC_FIELDS:
        if field != "digital_behavior.late_night_device_usage":
            print_numeric_stats(collection, field)
    print_common_value_counts(collection)
    print_threshold_count(collection, "burnout_result.productivity_score", low_productivity_score_threshold)


def diagnose_v2(db_v2, low_productivity_score_threshold: float) -> None:
    collection = db_v2.v2_wellbeing_assessments
    print("V2 v2_wellbeing_assessments")
    print(f"  documents: {collection.count_documents({})}")
    if collection.count_documents({}) == 0:
        print("  v2 has no documents yet")
        return
    print_late_night_diagnostics(collection)
    for field in V1_NUMERIC_FIELDS:
        if field != "digital_behavior.late_night_device_usage":
            print_numeric_stats(collection, field)
    print_common_value_counts(collection, include_user_ref=True)
    print_threshold_count(collection, "burnout_result.productivity_score", low_productivity_score_threshold)
    for field in V2_BOOLEAN_FIELDS:
        print_counts(collection, field)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose imported field ranges and computed v2 flags.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    client = MongoClient(config["mongo_uri"])
    low_productivity_score_threshold = float(config.get("low_productivity_score_threshold", 56))

    diagnose_v1(client[config["database_v1"]], low_productivity_score_threshold)
    print()
    diagnose_v2(client[config["database_v2"]], low_productivity_score_threshold)


if __name__ == "__main__":
    main()
