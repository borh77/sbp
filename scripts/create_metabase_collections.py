from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pymongo import MongoClient


DEFAULT_CONFIG = Path("config/db_config.example.json")
SOURCE_COLLECTION = "v2_wellbeing_assessments"

METABASE_COLLECTIONS = [
    "metabase_u6_focus_sessions",
    "metabase_u7_doomscrolling",
    "metabase_u8_hybrid_sweet_spot",
    "metabase_u9_late_night_usage",
    "metabase_u10_physical_activity",
]


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def out_stage(collection_name: str) -> dict[str, Any]:
    return {"$out": collection_name}


def u6_pipeline(output_collection: str) -> list[dict[str, Any]]:
    return [
        {
            "$group": {
                "_id": {
                    "focus_bucket": "$computed.focus_sessions_bucket",
                    "work_mode": "$user_ref.work_mode",
                },
                "deep_work_sum": {"$sum": "$focus_productivity.deep_work_hours"},
                "task_completion_sum": {"$sum": "$focus_productivity.task_completion_rate"},
                "mode_count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.focus_bucket": 1, "mode_count": -1, "_id.work_mode": 1}},
        {
            "$group": {
                "_id": "$_id.focus_bucket",
                "deep_work_sum": {"$sum": "$deep_work_sum"},
                "task_completion_sum": {"$sum": "$task_completion_sum"},
                "user_count": {"$sum": "$mode_count"},
                "dominant_work_mode": {"$first": "$_id.work_mode"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "focus_bucket": "$_id",
                "focus_bucket_order": {
                    "$switch": {
                        "branches": [
                            {"case": {"$eq": ["$_id", "0"]}, "then": 0},
                            {"case": {"$eq": ["$_id", "1-3"]}, "then": 1},
                            {"case": {"$eq": ["$_id", "4+"]}, "then": 2},
                        ],
                        "default": 99,
                    }
                },
                "user_count": 1,
                "avg_deep_work_hours": {"$divide": ["$deep_work_sum", "$user_count"]},
                "avg_task_completion_rate": {"$divide": ["$task_completion_sum", "$user_count"]},
                "dominant_work_mode": 1,
            }
        },
        {"$sort": {"focus_bucket_order": 1}},
        out_stage(output_collection),
    ]


def bucket_order(field: str, labels: list[str]) -> dict[str, Any]:
    return {
        "$switch": {
            "branches": [
                {"case": {"$eq": [field, label]}, "then": index}
                for index, label in enumerate(labels)
            ],
            "default": 99,
        }
    }


def u7_pipeline(output_collection: str) -> list[dict[str, Any]]:
    return [
        {"$match": {"computed.doomscrolling_bucket": {"$in": ["0-1", "1-2", "2-3", "3+"]}}},
        {
            "$group": {
                "_id": {
                    "bucket": "$computed.doomscrolling_bucket",
                    "device_usage_type": "$user_ref.device_usage_type",
                },
                "max_app_switch_frequency": {"$max": "$digital_behavior.app_switch_frequency"},
                "notification_sum": {"$sum": "$digital_behavior.notification_count"},
                "device_count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.bucket": 1, "device_count": -1, "_id.device_usage_type": 1}},
        {
            "$group": {
                "_id": "$_id.bucket",
                "max_app_switch_frequency": {"$max": "$max_app_switch_frequency"},
                "notification_sum": {"$sum": "$notification_sum"},
                "user_count": {"$sum": "$device_count"},
                "most_common_device_usage_type": {"$first": "$_id.device_usage_type"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "doomscrolling_bucket": "$_id",
                "doomscrolling_bucket_order": bucket_order("$_id", ["0-1", "1-2", "2-3", "3+"]),
                "user_count": 1,
                "avg_notification_count": {"$divide": ["$notification_sum", "$user_count"]},
                "max_app_switch_frequency": 1,
                "most_common_device_usage_type": 1,
            }
        },
        {"$sort": {"doomscrolling_bucket_order": 1}},
        out_stage(output_collection),
    ]


def u8_pipeline(output_collection: str) -> list[dict[str, Any]]:
    return [
        {
            "$match": {
                "computed.workspace_quality_ok": True,
                "work_environment.remote_work_days": {"$gte": 0, "$lte": 6},
            }
        },
        {
            "$group": {
                "_id": "$work_environment.remote_work_days",
                "user_count": {"$sum": 1},
                "avg_productivity_score": {"$avg": "$burnout_result.productivity_score"},
                "avg_motivation_level": {"$avg": "$burnout_result.motivation_level"},
                "avg_burnout_risk": {"$avg": "$burnout_result.burnout_risk"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "remote_work_days": "$_id",
                "user_count": 1,
                "avg_productivity_score": 1,
                "avg_motivation_level": 1,
                "avg_burnout_risk": 1,
            }
        },
        {"$sort": {"remote_work_days": 1}},
        out_stage(output_collection),
    ]


def u9_pipeline(output_collection: str) -> list[dict[str, Any]]:
    return [
        {"$match": {"digital_behavior.late_night_device_usage": {"$eq": 1}}},
        {
            "$group": {
                "_id": "$user_ref.occupation",
                "user_count": {"$sum": 1},
                "avg_stress_level": {"$avg": "$health_wellness.stress_level"},
                "avg_sleep_quality": {"$avg": "$health_wellness.sleep_quality"},
                "avg_caffeine_intake": {"$avg": "$health_wellness.caffeine_intake"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "occupation": "$_id",
                "user_count": 1,
                "avg_stress_level": 1,
                "avg_sleep_quality": 1,
                "avg_caffeine_intake": 1,
            }
        },
        {"$sort": {"avg_stress_level": -1, "user_count": -1}},
        out_stage(output_collection),
    ]


def u10_pipeline(output_collection: str) -> list[dict[str, Any]]:
    return [
        # TODO: If the dataset version has no productivity_category = "Low",
        # replace this match with:
        # {"$match": {"burnout_result.productivity_score": {"$lte": 56}}}
        {"$match": {"burnout_result.productivity_category": "Low"}},
        {
            "$match": {
                "computed.activity_level": {"$in": ["below_average", "above_average"]},
                "burnout_result.mental_state": {"$exists": True, "$ne": None},
            }
        },
        {
            "$group": {
                "_id": {
                    "activity_level": "$computed.activity_level",
                    "mental_state": "$burnout_result.mental_state",
                },
                "user_count": {"$sum": 1},
                "avg_burnout_risk": {"$avg": "$burnout_result.burnout_risk"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "activity_level": "$_id.activity_level",
                "activity_level_order": {
                    "$switch": {
                        "branches": [
                            {"case": {"$eq": ["$_id.activity_level", "below_average"]}, "then": 0},
                            {"case": {"$eq": ["$_id.activity_level", "above_average"]}, "then": 1},
                        ],
                        "default": 99,
                    }
                },
                "mental_state": "$_id.mental_state",
                "user_count": 1,
                "avg_burnout_risk": 1,
            }
        },
        {"$sort": {"activity_level_order": 1, "mental_state": 1}},
        out_stage(output_collection),
    ]


def pipelines() -> dict[str, list[dict[str, Any]]]:
    return {
        "metabase_u6_focus_sessions": u6_pipeline("metabase_u6_focus_sessions"),
        "metabase_u7_doomscrolling": u7_pipeline("metabase_u7_doomscrolling"),
        "metabase_u8_hybrid_sweet_spot": u8_pipeline("metabase_u8_hybrid_sweet_spot"),
        "metabase_u9_late_night_usage": u9_pipeline("metabase_u9_late_night_usage"),
        "metabase_u10_physical_activity": u10_pipeline("metabase_u10_physical_activity"),
    }


def create_indexes(db) -> None:
    db.metabase_u6_focus_sessions.create_index("focus_bucket_order")
    db.metabase_u7_doomscrolling.create_index("doomscrolling_bucket_order")
    db.metabase_u8_hybrid_sweet_spot.create_index("remote_work_days")
    db.metabase_u9_late_night_usage.create_index("avg_stress_level")
    db.metabase_u10_physical_activity.create_index([("activity_level_order", 1), ("mental_state", 1)])


def validate_collections(db, sample_size: int) -> None:
    print("Metabase collection validation:")
    for collection_name in METABASE_COLLECTIONS:
        collection = db[collection_name]
        count = collection.count_documents({})
        warning = " WARNING: empty collection" if count == 0 else ""
        print(f"  {collection_name}: {count}{warning}")
        for document in collection.find({}, {"_id": 0}).limit(sample_size):
            print(f"    {document}")


def create_metabase_collections(db) -> None:
    source = db[SOURCE_COLLECTION]
    for collection_name, pipeline in pipelines().items():
        print(f"Creating {collection_name} from {SOURCE_COLLECTION}...")
        db[collection_name].drop()
        list(source.aggregate(pipeline, allowDiskUse=True))
        print(f"  wrote {db[collection_name].count_documents({})} documents")
    create_indexes(db)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create small v2 result collections for Metabase dashboards.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--validate-only", action="store_true", help="Only print counts and sample documents.")
    parser.add_argument("--sample-size", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    client = MongoClient(config["mongo_uri"])
    db = client[config["database_v2"]]

    if args.validate_only:
        validate_collections(db, args.sample_size)
        return

    create_metabase_collections(db)
    validate_collections(db, args.sample_size)


if __name__ == "__main__":
    main()
