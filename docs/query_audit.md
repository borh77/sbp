# Query  Audit

| Query | Fields | Observed ranges/values | Query logic
|---|---|---|---|
| U6 | `focus_sessions`, `deep_work_hours`, `task_completion_rate`, `work_mode` | `focus_sessions` is 0-9 | Group focus sessions into `0`, `1-3`, `4+`; compute averages and dominant work mode. |
| U7 | `doomscrolling_duration`, `app_switch_frequency`, `notification_count`, `device_usage_type` | `doomscrolling_duration` is 0.0-7.9; device types include `Work-Centric`, `Entertainment-Centric`, `Balanced` | Use buckets `[0,1)`, `[1,2)`, `[2,3)`, and `3+`; compute max app switching, average notifications, most common device type. |
| U8 | `workspace_quality`, `remote_work_days`, `productivity_score`, `motivation_level` | `workspace_quality` is 1-10; `remote_work_days` is 0-6 | Filter `workspace_quality > 6`, group by remote work days. |
| U9 | `late_night_device_usage`, `occupation`, `stress_level`, `sleep_quality`, `caffeine_intake` | `late_night_device_usage` is binary 0/1 | Filter records where late-night usage equals `1`, group by occupation. |
| U10 | `productivity_category`, `productivity_score`, `physical_activity`, `burnout_risk`, `mental_state` | `physical_activity` is 0-5; `burnout_risk` is 0-100; mental states include `Balanced`, `Burnout`, `Focused` | Use `productivity_category = "Low"` when present; otherwise fall back to `productivity_score <= 56` or configured threshold. |
