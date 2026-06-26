from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pymongo import MongoClient


DEFAULT_CONFIG = Path("config/db_config.example.json")
OUTPUT_DIR = Path("results/query_outputs")
PERFORMANCE_TABLE = Path("results/performance_table.md")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def focus_bucket_expr(field: str) -> dict[str, Any]:
    return {
        "$switch": {
            "branches": [
                {"case": {"$lte": [field, 0]}, "then": "0"},
                {"case": {"$lte": [field, 3]}, "then": "1-3"},
            ],
            "default": "4+",
        }
    }


def doom_bucket_label_expr(field: str = "$_id") -> dict[str, Any]:
    return {
        "$switch": {
            "branches": [
                {"case": {"$eq": [field, 0]}, "then": "0-1"},
                {"case": {"$eq": [field, 1]}, "then": "1-2"},
                {"case": {"$eq": [field, 2]}, "then": "2-3"},
                {"case": {"$eq": [field, 3]}, "then": "3+"},
            ],
            "default": "other",
        }
    }


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


def apply_late_night_match(mode: str, config: dict[str, Any]) -> None:
    if mode == "binary_indicator":
        positive_value = config.get("late_night_binary_positive_value", 1)
        print(f"Detected late_night_device_usage type: binary_indicator, U9_v1 uses value == {positive_value}")
        match_stage = {"$match": {"digital_behavior.late_night_device_usage": {"$eq": positive_value}}}
    elif mode == "normalized_0_1":
        threshold = float(config.get("late_night_high_threshold_normalized", 0.6))
        print(f"Detected late_night_device_usage type: normalized_0_1, U9_v1 uses threshold > {threshold:g}")
        match_stage = {"$match": {"digital_behavior.late_night_device_usage": {"$gt": threshold}}}
    else:
        threshold = float(config.get("late_night_high_threshold", 6))
        print(f"Detected late_night_device_usage type: scale_1_10, U9_v1 uses threshold > {threshold:g}")
        match_stage = {"$match": {"digital_behavior.late_night_device_usage": {"$gt": threshold}}}
    PIPELINES["U9_v1"]["pipeline"][0] = match_stage


def productivity_category_counts(db_v1) -> dict[Any, int]:
    result = db_v1.v1_wellbeing_assessments.aggregate(
        [
            {"$group": {"_id": "$burnout_result.productivity_category", "count": {"$sum": 1}}},
        ]
    )
    return {item["_id"]: item["count"] for item in result}


def apply_low_productivity_match(db_v1, config: dict[str, Any]) -> None:
    counts = productivity_category_counts(db_v1)
    if counts.get("Low", 0) > 0:
        print("Detected U10 low-productivity mode: category_low")
        match_stage = {"$match": {"burnout_result.productivity_category": "Low"}}
    else:
        threshold = float(config.get("low_productivity_score_threshold", 56))
        print(f"Detected U10 low-productivity mode: score_threshold, using productivity_score <= {threshold:g}")
        match_stage = {"$match": {"burnout_result.productivity_score": {"$lte": threshold}}}

    PIPELINES["U10_v1"]["pipeline"][1] = match_stage
    PIPELINES["U10_v2"]["pipeline"][0] = match_stage


PIPELINES: dict[str, dict[str, Any]] = {
    "U6_v1": {
        "version": "v1",
        "collection": "v1_wellbeing_assessments",
        "pipeline": [
            {"$lookup": {"from": "v1_users", "localField": "user_id", "foreignField": "user_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$addFields": {"focus_sessions_bucket": focus_bucket_expr("$focus_productivity.focus_sessions")}},
            {
                "$group": {
                    "_id": {"bucket": "$focus_sessions_bucket", "work_mode": "$user.work_mode"},
                    "deep_work_sum": {"$sum": "$focus_productivity.deep_work_hours"},
                    "task_completion_sum": {"$sum": "$focus_productivity.task_completion_rate"},
                    "mode_count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.bucket": 1, "mode_count": -1, "_id.work_mode": 1}},
            {
                "$group": {
                    "_id": "$_id.bucket",
                    "deep_work_sum": {"$sum": "$deep_work_sum"},
                    "task_completion_sum": {"$sum": "$task_completion_sum"},
                    "count": {"$sum": "$mode_count"},
                    "dominant_work_mode": {"$first": "$_id.work_mode"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "focus_sessions_bucket": "$_id",
                    "avg_deep_work_hours": {"$divide": ["$deep_work_sum", "$count"]},
                    "avg_task_completion_rate": {"$divide": ["$task_completion_sum", "$count"]},
                    "dominant_work_mode": 1,
                    "count": 1,
                }
            },
            {"$sort": {"focus_sessions_bucket": 1}},
        ],
    },
    "U6_v2": {
        "version": "v2",
        "collection": "v2_wellbeing_assessments",
        "pipeline": [
            {
                "$group": {
                    "_id": {"bucket": "$computed.focus_sessions_bucket", "work_mode": "$user_ref.work_mode"},
                    "deep_work_sum": {"$sum": "$focus_productivity.deep_work_hours"},
                    "task_completion_sum": {"$sum": "$focus_productivity.task_completion_rate"},
                    "mode_count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.bucket": 1, "mode_count": -1, "_id.work_mode": 1}},
            {
                "$group": {
                    "_id": "$_id.bucket",
                    "deep_work_sum": {"$sum": "$deep_work_sum"},
                    "task_completion_sum": {"$sum": "$task_completion_sum"},
                    "count": {"$sum": "$mode_count"},
                    "dominant_work_mode": {"$first": "$_id.work_mode"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "focus_sessions_bucket": "$_id",
                    "avg_deep_work_hours": {"$divide": ["$deep_work_sum", "$count"]},
                    "avg_task_completion_rate": {"$divide": ["$task_completion_sum", "$count"]},
                    "dominant_work_mode": 1,
                    "count": 1,
                }
            },
            {"$sort": {"focus_sessions_bucket": 1}},
        ],
    },
    "U7_v1": {
        "version": "v1",
        "collection": "v1_wellbeing_assessments",
        "pipeline": [
            {"$lookup": {"from": "v1_users", "localField": "user_id", "foreignField": "user_id", "as": "user"}},
            {"$unwind": "$user"},
            {
                "$bucket": {
                    "groupBy": "$digital_behavior.doomscrolling_duration",
                    "boundaries": [0, 1, 2, 3, 1000000000],
                    "default": "other",
                    "output": {
                        "max_app_switch_frequency": {"$max": "$digital_behavior.app_switch_frequency"},
                        "notification_sum": {"$sum": "$digital_behavior.notification_count"},
                        "count": {"$sum": 1},
                        "device_usage_types": {"$push": "$user.device_usage_type"},
                    },
                }
            },
            {"$match": {"_id": {"$ne": "other"}}},
            {"$unwind": "$device_usage_types"},
            {
                "$group": {
                    "_id": {"bucket": "$_id", "device_usage_type": "$device_usage_types"},
                    "device_count": {"$sum": 1},
                    "max_app_switch_frequency": {"$first": "$max_app_switch_frequency"},
                    "notification_sum": {"$first": "$notification_sum"},
                    "count": {"$first": "$count"},
                }
            },
            {"$sort": {"_id.bucket": 1, "device_count": -1, "_id.device_usage_type": 1}},
            {
                "$group": {
                    "_id": "$_id.bucket",
                    "max_app_switch_frequency": {"$first": "$max_app_switch_frequency"},
                    "notification_sum": {"$first": "$notification_sum"},
                    "count": {"$first": "$count"},
                    "most_common_device_usage_type": {"$first": "$_id.device_usage_type"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "doomscrolling_bucket": doom_bucket_label_expr("$_id"),
                    "max_app_switch_frequency": 1,
                    "avg_notification_count": {"$divide": ["$notification_sum", "$count"]},
                    "most_common_device_usage_type": 1,
                    "count": 1,
                }
            },
            {"$sort": {"doomscrolling_bucket": 1}},
        ],
    },
    "U7_v2": {
        "version": "v2",
        "collection": "v2_wellbeing_assessments",
        "pipeline": [
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
                    "count": {"$sum": "$device_count"},
                    "most_common_device_usage_type": {"$first": "$_id.device_usage_type"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "doomscrolling_bucket": "$_id",
                    "max_app_switch_frequency": 1,
                    "avg_notification_count": {"$divide": ["$notification_sum", "$count"]},
                    "most_common_device_usage_type": 1,
                    "count": 1,
                }
            },
            {"$sort": {"doomscrolling_bucket": 1}},
        ],
    },
    "U8_v1": {
        "version": "v1",
        "collection": "v1_wellbeing_assessments",
        "pipeline": [
            {"$match": {"work_environment.workspace_quality": {"$gt": 6}}},
            {
                "$group": {
                    "_id": "$work_environment.remote_work_days",
                    "avg_productivity_score": {"$avg": "$burnout_result.productivity_score"},
                    "avg_motivation_level": {"$avg": "$burnout_result.motivation_level"},
                    "count": {"$sum": 1},
                }
            },
            {"$project": {"_id": 0, "remote_work_days": "$_id", "avg_productivity_score": 1, "avg_motivation_level": 1, "count": 1}},
            {"$sort": {"remote_work_days": 1}},
        ],
    },
    "U8_v2": {
        "version": "v2",
        "collection": "v2_wellbeing_assessments",
        "pipeline": [
            {"$match": {"computed.workspace_quality_ok": True}},
            {
                "$group": {
                    "_id": "$work_environment.remote_work_days",
                    "avg_productivity_score": {"$avg": "$burnout_result.productivity_score"},
                    "avg_motivation_level": {"$avg": "$burnout_result.motivation_level"},
                    "count": {"$sum": 1},
                }
            },
            {"$project": {"_id": 0, "remote_work_days": "$_id", "avg_productivity_score": 1, "avg_motivation_level": 1, "count": 1}},
            {"$sort": {"remote_work_days": 1}},
        ],
    },
    "U9_v1": {
        "version": "v1",
        "collection": "v1_wellbeing_assessments",
        "pipeline": [
            {"$match": {"digital_behavior.late_night_device_usage": {"$eq": 1}}},
            {"$lookup": {"from": "v1_users", "localField": "user_id", "foreignField": "user_id", "as": "user"}},
            {"$unwind": "$user"},
            {
                "$group": {
                    "_id": "$user.occupation",
                    "avg_stress_level": {"$avg": "$health_wellness.stress_level"},
                    "avg_sleep_quality": {"$avg": "$health_wellness.sleep_quality"},
                    "avg_caffeine_intake": {"$avg": "$health_wellness.caffeine_intake"},
                    "count": {"$sum": 1},
                }
            },
            {"$project": {"_id": 0, "occupation": "$_id", "avg_stress_level": 1, "avg_sleep_quality": 1, "avg_caffeine_intake": 1, "count": 1}},
            {"$sort": {"avg_stress_level": -1}},
        ],
    },
    "U9_v2": {
        "version": "v2",
        "collection": "v2_wellbeing_assessments",
        "pipeline": [
            {"$match": {"computed.late_night_high": True}},
            {
                "$group": {
                    "_id": "$user_ref.occupation",
                    "avg_stress_level": {"$avg": "$health_wellness.stress_level"},
                    "avg_sleep_quality": {"$avg": "$health_wellness.sleep_quality"},
                    "avg_caffeine_intake": {"$avg": "$health_wellness.caffeine_intake"},
                    "count": {"$sum": 1},
                }
            },
            {"$project": {"_id": 0, "occupation": "$_id", "avg_stress_level": 1, "avg_sleep_quality": 1, "avg_caffeine_intake": 1, "count": 1}},
            {"$sort": {"avg_stress_level": -1}},
        ],
    },
    "U10_v1": {
        "version": "v1",
        "collection": "v1_wellbeing_assessments",
        "pipeline": [
            {
                "$setWindowFields": {
                    "output": {
                        "avg_physical_activity": {
                            "$avg": "$health_wellness.physical_activity",
                            "window": {"documents": ["unbounded", "unbounded"]},
                        }
                    }
                }
            },
            {"$match": {"burnout_result.productivity_category": "Low"}},
            {
                "$project": {
                    "activity_level": {
                        "$cond": [
                            {"$lt": ["$health_wellness.physical_activity", "$avg_physical_activity"]},
                            "below_average",
                            "above_average",
                        ]
                    },
                    "burnout_risk": "$burnout_result.burnout_risk",
                    "mental_state": "$burnout_result.mental_state",
                }
            },
            {
                "$group": {
                    "_id": {"activity_level": "$activity_level", "mental_state": "$mental_state"},
                    "burnout_risk_sum": {"$sum": "$burnout_risk"},
                    "mental_state_count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.activity_level": 1, "mental_state_count": -1, "_id.mental_state": 1}},
            {
                "$group": {
                    "_id": "$_id.activity_level",
                    "burnout_risk_sum": {"$sum": "$burnout_risk_sum"},
                    "count": {"$sum": "$mental_state_count"},
                    "mental_state_distribution": {
                        "$push": {
                            "mental_state": "$_id.mental_state",
                            "count": "$mental_state_count",
                        }
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "activity_level": "$_id",
                    "avg_burnout_risk": {"$divide": ["$burnout_risk_sum", "$count"]},
                    "mental_state_distribution": 1,
                    "count": 1,
                }
            },
            {"$sort": {"activity_level": 1}},
        ],
    },
    "U10_v2": {
        "version": "v2",
        "collection": "v2_wellbeing_assessments",
        "pipeline": [
            {"$match": {"burnout_result.productivity_category": "Low"}},
            {
                "$group": {
                    "_id": {"activity_level": "$computed.activity_level", "mental_state": "$burnout_result.mental_state"},
                    "burnout_risk_sum": {"$sum": "$burnout_result.burnout_risk"},
                    "mental_state_count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.activity_level": 1, "mental_state_count": -1, "_id.mental_state": 1}},
            {
                "$group": {
                    "_id": "$_id.activity_level",
                    "burnout_risk_sum": {"$sum": "$burnout_risk_sum"},
                    "count": {"$sum": "$mental_state_count"},
                    "mental_state_distribution": {
                        "$push": {
                            "mental_state": "$_id.mental_state",
                            "count": "$mental_state_count",
                        }
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "activity_level": "$_id",
                    "avg_burnout_risk": {"$divide": ["$burnout_risk_sum", "$count"]},
                    "mental_state_distribution": 1,
                    "count": 1,
                }
            },
            {"$sort": {"activity_level": 1}},
        ],
    },
}


def find_key_recursive(document: Any, key: str) -> Any:
    if isinstance(document, dict):
        if key in document:
            return document[key]
        for value in document.values():
            found = find_key_recursive(value, key)
            if found is not None:
                return found
    elif isinstance(document, list):
        for item in document:
            found = find_key_recursive(item, key)
            if found is not None:
                return found
    return None


def extract_metrics(explain: dict[str, Any]) -> dict[str, Any]:
    execution_stats = explain.get("executionStats", {})
    winning_plan = find_key_recursive(explain, "winningPlan") or {}
    return {
        "executionTimeMillis": execution_stats.get("executionTimeMillis") or find_key_recursive(explain, "executionTimeMillis"),
        "totalDocsExamined": execution_stats.get("totalDocsExamined") or find_key_recursive(explain, "totalDocsExamined"),
        "totalKeysExamined": execution_stats.get("totalKeysExamined") or find_key_recursive(explain, "totalKeysExamined"),
        "nReturned": execution_stats.get("nReturned") or find_key_recursive(explain, "nReturned"),
        "winningStage": winning_plan.get("stage") or find_key_recursive(winning_plan, "stage"),
    }


def run_explain(db, collection_name: str, pipeline: list[dict[str, Any]]) -> dict[str, Any]:
    return db.command(
        "explain",
        {"aggregate": collection_name, "pipeline": pipeline, "cursor": {}},
        verbosity="executionStats",
    )


def render_performance_table(results: list[dict[str, Any]]) -> str:
    rows_by_query: dict[str, dict[str, Any]] = {}
    for result in results:
        query, version = result["name"].split("_")
        rows_by_query.setdefault(query, {})[version] = result["metrics"]

    optimizations = {
        "U6": "Computed focus bucket + no lookup",
        "U7": "Computed doomscrolling bucket + no lookup",
        "U8": "workspace_quality_ok filter + compound index",
        "U9": "binary late_night_high + occupation in user_ref",
        "U10": "activity_level + productivity index",
    }

    lines = [
        "| Query | V1 time ms | V1 docs examined | V2 time ms | V2 docs examined | Improvement | Main optimization |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for query in ["U6", "U7", "U8", "U9", "U10"]:
        v1 = rows_by_query.get(query, {}).get("v1", {})
        v2 = rows_by_query.get(query, {}).get("v2", {})
        v1_time = v1.get("executionTimeMillis")
        v2_time = v2.get("executionTimeMillis")
        improvement = "TBD"
        if isinstance(v1_time, (int, float)) and isinstance(v2_time, (int, float)) and v2_time:
            improvement = f"{v1_time / v2_time:.2f}x"
        lines.append(
            "| {query} | {v1_time} | {v1_docs} | {v2_time} | {v2_docs} | {improvement} | {optimization} |".format(
                query=query,
                v1_time=v1_time if v1_time is not None else "TBD",
                v1_docs=v1.get("totalDocsExamined", "TBD"),
                v2_time=v2_time if v2_time is not None else "TBD",
                v2_docs=v2.get("totalDocsExamined", "TBD"),
                improvement=improvement,
                optimization=optimizations[query],
            )
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure v1/v2 MongoDB query performance with explain executionStats.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--query", choices=sorted(PIPELINES), default=None, help="Run one query only, for example U6_v1.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    client = MongoClient(config["mongo_uri"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    db_v1 = client[config["database_v1"]]
    late_night_profile = late_night_usage_profile(db_v1)
    late_night_mode = late_night_usage_mode(late_night_profile)
    apply_late_night_match(late_night_mode, config)
    apply_low_productivity_match(db_v1, config)

    selected = {args.query: PIPELINES[args.query]} if args.query else PIPELINES
    results = []

    for name, spec in selected.items():
        db_name = config[f"database_{spec['version']}"]
        db = client[db_name]
        print(f"Measuring {name} on {db_name}.{spec['collection']}")
        explain = run_explain(db, spec["collection"], spec["pipeline"])
        metrics = extract_metrics(explain)
        result = {"name": name, "version": spec["version"], "collection": spec["collection"], "metrics": metrics}
        results.append(result)
        output_path = OUTPUT_DIR / f"{name}.json"
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(result, file, indent=2, default=str)
        print(f"  {metrics}")

    if not args.query:
        PERFORMANCE_TABLE.write_text(render_performance_table(results), encoding="utf-8")
        print(f"Updated {PERFORMANCE_TABLE}")


if __name__ == "__main__":
    main()
