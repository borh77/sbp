# Dataset Description

The project uses a Kaggle digital burnout/productivity analytics dataset.

Known facts:

- File name: `digital_burnout_productivity_dataset_5M.csv`
- Rows: 5,000,000
- Columns: 34
- Format: one CSV file
- Size: more than 1 GB

Observed field ranges/values from Kaggle preview and diagnostics:

- `focus_sessions`: 0-9
- `doomscrolling_duration`: 0.0-7.9
- `workspace_quality`: 1-10
- `remote_work_days`: 0-6
- `late_night_device_usage`: binary 0/1
- `physical_activity`: 0-5
- `burnout_risk`: 0-100
- `concentration_score`: 1-10
- `device_usage_type`: values such as `Work-Centric`, `Entertainment-Centric`, `Balanced`
- `mental_state`: values such as `Balanced`, `Burnout`, `Focused`

## Columns

The import script maps common title-case, spaced, and snake-case variants of these logical fields:

- `user_id`
- `age`
- `occupation`
- `work_mode`
- `device_usage_type`
- `daily_screen_time`
- `social_media_hours`
- `doomscrolling_duration`
- `app_switch_frequency`
- `notification_count`
- `smartphone_unlocks`
- `late_night_device_usage`
- `focus_sessions`
- `deep_work_hours`
- `distraction_frequency`
- `task_completion_rate`
- `concentration_score`
- `sleep_hours`
- `sleep_quality`
- `caffeine_intake`
- `physical_activity`
- `stress_level`
- `workspace_quality`
- `meeting_hours`
- `internet_stability`
- `remote_work_days`
- `motivation_level`
- `mental_fatigue`
- `emotional_exhaustion`
- `work_satisfaction`
- `mental_state`
- `burnout_risk`
- `productivity_score`
- `productivity_category`

## Late-Night Device Usage

`late_night_device_usage` is a binary indicator in the inspected Kaggle CSV:

- `1`: late-night device usage happened
- `0`: no late-night device usage

U9 therefore compares users who have late-night device usage (`1`) by occupation. The Python scripts still keep fallback support for other dataset versions where this field might be normalized from 0-1 or stored on a 1-10 scale, but the main project logic treats the inspected CSV as binary.

## U7 Doomscrolling Buckets

U7 uses the same boundary semantics in v1 and v2:

- `0 <= value < 1`: `0-1`
- `1 <= value < 2`: `1-2`
- `2 <= value < 3`: `2-3`
- `value >= 3`: `3+`

## U10 Low-Productivity Definition

Primary definition: use `productivity_category = "Low"` when that category exists in the imported dataset.

Fallback definition: if the dataset version does not contain `Low`, use low-score users with `productivity_score <= low_productivity_score_threshold`. The default threshold is `56` and is configured in `config/*.json`.
