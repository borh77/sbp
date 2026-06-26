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


def number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def age_group(age: Any) -> str | None:
    if age is None:
        return None
    age_value = number(age, -1)
    if age_value < 0:
        return None
    if age_value < 25:
        return "under_25"
    if age_value < 35:
        return "25_34"
    if age_value < 45:
        return "35_44"
    return "45_plus"


def focus_bucket(value: Any) -> str:
    sessions = number(value)
    if sessions <= 0:
        return "0"
    if sessions <= 3:
        return "1-3"
    return "4+"


def doomscrolling_bucket(value: Any) -> str:
    duration = number(value)
    if duration < 1:
        return "0-1"
    if duration < 2:
        return "1-2"
    if duration < 3:
        return "2-3"
    return "3+"


def create_indexes(db) -> None:
    collection = db.v2_wellbeing_assessments
    collection.create_index([("computed.focus_sessions_bucket", 1), ("user_ref.work_mode", 1)])
    collection.create_index([("computed.doomscrolling_bucket", 1), ("user_ref.device_usage_type", 1)])
    old_u8_key = [("work_environment.remote_work_days", 1), ("computed.workspace_quality_ok", 1)]
    new_u8_key = [("computed.workspace_quality_ok", 1), ("work_environment.remote_work_days", 1)]
    for index in list(collection.list_indexes()):
        index_key = list(index["key"].items())
        if index_key == old_u8_key or (index_key == new_u8_key and index["name"] != "idx_v2_u8_workspace_ok_remote_days"):
            collection.drop_index(index["name"])
    collection.create_index(
        new_u8_key,
        name="idx_v2_u8_workspace_ok_remote_days",
    )
    collection.create_index([("computed.late_night_high", 1), ("user_ref.occupation", 1)])
    collection.create_index(
        [
            ("burnout_result.productivity_category", 1),
            ("computed.activity_level", 1),
            ("burnout_result.mental_state", 1),
        ]
    )
    collection.create_index("user_id")


def physical_activity_average(db_v1) -> float:
    result = list(
        db_v1.v1_wellbeing_assessments.aggregate(
            [
                {"$match": {"health_wellness.physical_activity": {"$type": "number"}}},
                {"$group": {"_id": None, "avg_activity": {"$avg": "$health_wellness.physical_activity"}}},
            ]
        )
    )
    if not result:
        return 0.0
    return float(result[0].get("avg_activity") or 0.0)


def late_night_usage_profile(db_v1) -> dict[str, Any]:
    field = "$digital_behavior.late_night_device_usage"
    result = list(
        db_v1.v1_wellbeing_assessments.aggregate(
            [
                {"$match": {"digital_behavior.late_night_device_usage": {"$type": "number"}}},
                {
                    "$group": {
                        "_id": None,
                        "min": {"$min": field},
                        "max": {"$max": field},
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
    if not result:
        return {"count": 0, "min": None, "max": None, "non_binary_count": 0}
    return result[0]


def late_night_usage_mode(profile: dict[str, Any]) -> str:
    min_value = profile.get("min")
    max_value = profile.get("max")
    if min_value is None or max_value is None:
        return "scale_1_10"
    if min_value >= 0 and max_value <= 1 and profile.get("non_binary_count", 0) == 0:
        return "binary_indicator"
    if min_value >= 0 and max_value <= 1:
        return "normalized_0_1"
    return "scale_1_10"


def print_late_night_detection(mode: str, config: dict[str, Any]) -> None:
    if mode == "binary_indicator":
        positive_value = config.get("late_night_binary_positive_value", 1)
        print(f"Detected late_night_device_usage type: binary_indicator, using value == {positive_value}")
    elif mode == "normalized_0_1":
        threshold = float(config.get("late_night_high_threshold_normalized", 0.6))
        print(f"Detected late_night_device_usage type: normalized_0_1, using threshold > {threshold:g}")
    else:
        threshold = float(config.get("late_night_high_threshold", 6))
        print(f"Detected late_night_device_usage type: scale_1_10, using threshold > {threshold:g}")


def is_late_night_high(value: Any, mode: str, config: dict[str, Any]) -> bool:
    numeric_value = number(value)
    if mode == "binary_indicator":
        return numeric_value == number(config.get("late_night_binary_positive_value", 1))
    if mode == "normalized_0_1":
        return numeric_value > float(config.get("late_night_high_threshold_normalized", 0.6))
    return numeric_value > float(config.get("late_night_high_threshold", 6))


def build_v2_document(
    assessment: dict[str, Any],
    user: dict[str, Any] | None,
    avg_activity: float,
    late_night_mode: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    user = user or {}
    focus_productivity = assessment.get("focus_productivity", {})
    digital_behavior = assessment.get("digital_behavior", {})
    health_wellness = assessment.get("health_wellness", {})
    work_environment = assessment.get("work_environment", {})

    activity = number(health_wellness.get("physical_activity"))

    return {
        "user_id": assessment.get("user_id"),
        "user_ref": {
            "user_id": user.get("user_id", assessment.get("user_id")),
            "occupation": user.get("occupation"),
            "work_mode": user.get("work_mode"),
            "age_group": age_group(user.get("age")),
            "device_usage_type": user.get("device_usage_type"),
        },
        "digital_behavior": digital_behavior,
        "focus_productivity": focus_productivity,
        "health_wellness": health_wellness,
        "work_environment": work_environment,
        "burnout_result": assessment.get("burnout_result", {}),
        "computed": {
            "focus_sessions_bucket": focus_bucket(focus_productivity.get("focus_sessions")),
            "doomscrolling_bucket": doomscrolling_bucket(digital_behavior.get("doomscrolling_duration")),
            "activity_level": "above_average" if activity >= avg_activity else "below_average",
            "late_night_high": is_late_night_high(
                digital_behavior.get("late_night_device_usage"),
                late_night_mode,
                config,
            ),
            "workspace_quality_ok": number(work_environment.get("workspace_quality")) > 6,
        },
    }


def iter_batches(cursor, batch_size: int):
    batch = []
    for document in cursor:
        batch.append(document)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def fetch_users_for_assessments(db_v1, assessments: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    user_ids = list({assessment.get("user_id") for assessment in assessments if assessment.get("user_id") is not None})
    if not user_ids:
        return {}
    users = db_v1.v1_users.find({"user_id": {"$in": user_ids}}, {"_id": 0})
    return {user.get("user_id"): user for user in users}


def build_v2_batch(
    assessments: list[dict[str, Any]],
    users_by_id: dict[Any, dict[str, Any]],
    avg_activity: float,
    late_night_mode: str,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        build_v2_document(
            assessment,
            users_by_id.get(assessment.get("user_id")),
            avg_activity,
            late_night_mode,
            config,
        )
        for assessment in assessments
    ]


def copy_users_streaming(db_v1, db_v2, batch_size: int) -> int:
    db_v2.v2_users.delete_many({})
    copied = 0
    cursor = db_v1.v1_users.find({}, {"_id": 0}, no_cursor_timeout=True).batch_size(batch_size)
    try:
        for users_batch in iter_batches(cursor, batch_size):
            db_v2.v2_users.insert_many(users_batch, ordered=False)
            copied += len(users_batch)
            print(f"Copied {copied} v2 users.")
    finally:
        cursor.close()
    if copied:
        db_v2.v2_users.create_index("user_id", unique=True)
    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build v2 optimized MongoDB schema from v1 collections.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--drop-existing", action="store_true", help="Drop v2 collections before transformation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    batch_size = args.batch_size or int(config.get("batch_size", 5000))

    client = MongoClient(config["mongo_uri"])
    db_v1 = client[config["database_v1"]]
    db_v2 = client[config["database_v2"]]

    if args.drop_existing:
        db_v2.v2_users.drop()
        db_v2.v2_wellbeing_assessments.drop()

    avg_activity = physical_activity_average(db_v1)
    print(f"Global average physical_activity: {avg_activity:.4f}")
    late_night_profile = late_night_usage_profile(db_v1)
    late_night_mode = late_night_usage_mode(late_night_profile)
    print_late_night_detection(late_night_mode, config)

    inserted = 0

    cursor = db_v1.v1_wellbeing_assessments.find({}, no_cursor_timeout=True).batch_size(batch_size)
    try:
        for assessments_batch in iter_batches(cursor, batch_size):
            users_by_id = fetch_users_for_assessments(db_v1, assessments_batch)
            v2_batch = build_v2_batch(assessments_batch, users_by_id, avg_activity, late_night_mode, config)
            db_v2.v2_wellbeing_assessments.insert_many(v2_batch, ordered=False)
            inserted += len(v2_batch)
            print(f"Inserted {inserted} v2 assessments.")
    finally:
        cursor.close()

    copied_users = copy_users_streaming(db_v1, db_v2, batch_size)

    create_indexes(db_v2)
    print("Final counts:")
    print(f"  v2_users: {copied_users}")
    print(f"  v2_wellbeing_assessments: {db_v2.v2_wellbeing_assessments.count_documents({})}")


if __name__ == "__main__":
    main()
