from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError


DEFAULT_CONFIG = Path("config/db_config.example.json")


FIELD_ALIASES = {
    "user_id": ["user_id", "userid", "user id", "id"],
    "age": ["age"],
    "occupation": ["occupation", "job_role", "job role", "profession"],
    "work_mode": ["work_mode", "work mode", "work_arrangement", "work arrangement"],
    "device_usage_type": ["device_usage_type", "device usage type", "primary_device", "primary device"],
    "daily_screen_time": ["daily_screen_time", "daily screen time", "screen_time", "screen time"],
    "social_media_hours": ["social_media_hours", "social media hours"],
    "doomscrolling_duration": ["doomscrolling_duration", "doomscrolling duration", "doomscrolling_hours", "doomscrolling hours"],
    "app_switch_frequency": ["app_switch_frequency", "app switch frequency"],
    "notification_count": ["notification_count", "notification count", "notifications"],
    "smartphone_unlocks": ["smartphone_unlocks", "smartphone unlocks"],
    "late_night_device_usage": ["late_night_device_usage", "late night device usage", "late_night_usage", "late night usage"],
    "focus_sessions": ["focus_sessions", "focus sessions"],
    "deep_work_hours": ["deep_work_hours", "deep work hours"],
    "distraction_frequency": ["distraction_frequency", "distraction frequency"],
    "task_completion_rate": ["task_completion_rate", "task completion rate"],
    "concentration_score": ["concentration_score", "concentration score"],
    "sleep_hours": ["sleep_hours", "sleep hours"],
    "sleep_quality": ["sleep_quality", "sleep quality"],
    "caffeine_intake": ["caffeine_intake", "caffeine intake"],
    "physical_activity": ["physical_activity", "physical activity"],
    "stress_level": ["stress_level", "stress level"],
    "workspace_quality": ["workspace_quality", "workspace quality"],
    "meeting_hours": ["meeting_hours", "meeting hours"],
    "internet_stability": ["internet_stability", "internet stability"],
    "remote_work_days": ["remote_work_days", "remote work days"],
    "motivation_level": ["motivation_level", "motivation level"],
    "mental_fatigue": ["mental_fatigue", "mental fatigue"],
    "emotional_exhaustion": ["emotional_exhaustion", "emotional exhaustion"],
    "work_satisfaction": ["work_satisfaction", "work satisfaction"],
    "mental_state": ["mental_state", "mental state"],
    "burnout_risk": ["burnout_risk", "burnout risk"],
    "productivity_score": ["productivity_score", "productivity score"],
    "productivity_category": ["productivity_category", "productivity category"],
}


NUMERIC_FIELDS = {
    "age",
    "daily_screen_time",
    "social_media_hours",
    "doomscrolling_duration",
    "app_switch_frequency",
    "notification_count",
    "smartphone_unlocks",
    "late_night_device_usage",
    "focus_sessions",
    "deep_work_hours",
    "distraction_frequency",
    "task_completion_rate",
    "concentration_score",
    "sleep_hours",
    "sleep_quality",
    "caffeine_intake",
    "physical_activity",
    "stress_level",
    "workspace_quality",
    "meeting_hours",
    "internet_stability",
    "remote_work_days",
    "motivation_level",
    "mental_fatigue",
    "emotional_exhaustion",
    "work_satisfaction",
    "burnout_risk",
    "productivity_score",
}


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_column_map(columns: list[str]) -> dict[str, str]:
    normalized = {normalize_name(column): column for column in columns}
    column_map = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            key = normalize_name(alias)
            if key in normalized:
                column_map[field] = normalized[key]
                break
    return column_map


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def get_value(row: pd.Series, column_map: dict[str, str], field: str, default: Any = None) -> Any:
    column = column_map.get(field)
    if not column:
        return default
    return clean_value(row.get(column, default))


def to_number(value: Any) -> int | float | None:
    value = clean_value(value)
    if value in ("", None):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def field_value(row: pd.Series, column_map: dict[str, str], field: str, default: Any = None) -> Any:
    value = get_value(row, column_map, field, default)
    if field in NUMERIC_FIELDS:
        return to_number(value)
    return value


def make_documents(row: pd.Series, column_map: dict[str, str], fallback_user_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    user_id = field_value(row, column_map, "user_id", fallback_user_id)
    if user_id in ("", None):
        user_id = fallback_user_id

    user_doc = {
        "user_id": user_id,
        "age": field_value(row, column_map, "age"),
        "occupation": field_value(row, column_map, "occupation"),
        "work_mode": field_value(row, column_map, "work_mode"),
        "device_usage_type": field_value(row, column_map, "device_usage_type"),
    }

    assessment_doc = {
        "user_id": user_id,
        "digital_behavior": {
            "daily_screen_time": field_value(row, column_map, "daily_screen_time"),
            "social_media_hours": field_value(row, column_map, "social_media_hours"),
            "doomscrolling_duration": field_value(row, column_map, "doomscrolling_duration"),
            "app_switch_frequency": field_value(row, column_map, "app_switch_frequency"),
            "notification_count": field_value(row, column_map, "notification_count"),
            "smartphone_unlocks": field_value(row, column_map, "smartphone_unlocks"),
            "late_night_device_usage": field_value(row, column_map, "late_night_device_usage"),
        },
        "focus_productivity": {
            "focus_sessions": field_value(row, column_map, "focus_sessions"),
            "deep_work_hours": field_value(row, column_map, "deep_work_hours"),
            "distraction_frequency": field_value(row, column_map, "distraction_frequency"),
            "task_completion_rate": field_value(row, column_map, "task_completion_rate"),
            "concentration_score": field_value(row, column_map, "concentration_score"),
        },
        "health_wellness": {
            "sleep_hours": field_value(row, column_map, "sleep_hours"),
            "sleep_quality": field_value(row, column_map, "sleep_quality"),
            "caffeine_intake": field_value(row, column_map, "caffeine_intake"),
            "physical_activity": field_value(row, column_map, "physical_activity"),
            "stress_level": field_value(row, column_map, "stress_level"),
        },
        "work_environment": {
            "workspace_quality": field_value(row, column_map, "workspace_quality"),
            "meeting_hours": field_value(row, column_map, "meeting_hours"),
            "internet_stability": field_value(row, column_map, "internet_stability"),
            "remote_work_days": field_value(row, column_map, "remote_work_days"),
        },
        "burnout_result": {
            "motivation_level": field_value(row, column_map, "motivation_level"),
            "mental_fatigue": field_value(row, column_map, "mental_fatigue"),
            "emotional_exhaustion": field_value(row, column_map, "emotional_exhaustion"),
            "work_satisfaction": field_value(row, column_map, "work_satisfaction"),
            "mental_state": field_value(row, column_map, "mental_state"),
            "burnout_risk": field_value(row, column_map, "burnout_risk"),
            "productivity_score": field_value(row, column_map, "productivity_score"),
            "productivity_category": field_value(row, column_map, "productivity_category"),
        },
    }
    return user_doc, assessment_doc


def create_indexes(db) -> None:
    db.v1_users.create_index("user_id", unique=True)
    db.v1_wellbeing_assessments.create_index("user_id")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import CSV rows into the v1 MongoDB schema.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of CSV rows to import.")
    parser.add_argument("--drop-existing", action="store_true", help="Drop v1 collections before importing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    limit = args.limit if args.limit is not None else config.get("limit_rows")
    batch_size = int(config.get("batch_size", 5000))
    csv_path = Path(config["csv_path"])

    client = MongoClient(config["mongo_uri"])
    db = client[config["database_v1"]]

    if args.drop_existing:
        print("Dropping existing v1 collections before import.")
        db.v1_users.drop()
        db.v1_wellbeing_assessments.drop()

    create_indexes(db)

    imported = 0
    processed = 0
    skipped = 0
    column_map: dict[str, str] | None = None

    for chunk in pd.read_csv(csv_path, chunksize=batch_size):
        if column_map is None:
            column_map = build_column_map(list(chunk.columns))
            print(f"Detected {len(column_map)} mapped columns: {sorted(column_map)}")

        if limit is not None:
            remaining = limit - processed
            if remaining <= 0:
                break
            chunk = chunk.head(remaining)

        user_ops = []
        assessment_docs = []
        processed_before_chunk = processed
        processed += len(chunk)
        for offset, (_, row) in enumerate(chunk.iterrows(), start=1):
            fallback_user_id = processed_before_chunk + offset
            try:
                user_doc, assessment_doc = make_documents(row, column_map, fallback_user_id)
                user_ops.append(
                    UpdateOne(
                        {"user_id": user_doc["user_id"]},
                        {"$setOnInsert": user_doc},
                        upsert=True,
                    )
                )
                assessment_docs.append(assessment_doc)
            except Exception as exc:
                skipped += 1
                print(f"Skipping row {fallback_user_id}: {exc}")

        if user_ops:
            try:
                db.v1_users.bulk_write(user_ops, ordered=False)
            except BulkWriteError as exc:
                skipped += len(exc.details.get("writeErrors", []))
                print(f"User upsert batch completed with write errors: {exc.details.get('writeErrors', [])[:3]}")
        if assessment_docs:
            try:
                result = db.v1_wellbeing_assessments.insert_many(assessment_docs, ordered=False)
                imported += len(result.inserted_ids)
            except BulkWriteError as exc:
                inserted = exc.details.get("nInserted", 0)
                imported += inserted
                skipped += len(exc.details.get("writeErrors", []))
                print(f"Assessment insert batch completed with write errors: {exc.details.get('writeErrors', [])[:3]}")

        print(f"Processed {processed} CSV rows; imported {imported} assessment rows; skipped {skipped}.")

    create_indexes(db)
    print("Final counts:")
    print(f"  v1_users: {db.v1_users.count_documents({})}")
    print(f"  v1_wellbeing_assessments: {db.v1_wellbeing_assessments.count_documents({})}")
    print(f"  skipped_rows: {skipped}")


if __name__ == "__main__":
    main()
