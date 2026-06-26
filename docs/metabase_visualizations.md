# Metabase Visualizations

The project creates small dashboard-ready result collections in the optimized MongoDB database, `digital_burnout_v2`.

Source collection:

- `v2_wellbeing_assessments`

Generated result collections:

- `metabase_u6_focus_sessions`
- `metabase_u7_doomscrolling`
- `metabase_u8_hybrid_sweet_spot`
- `metabase_u9_late_night_usage`
- `metabase_u10_physical_activity`

Run:

```powershell
docker compose run --rm sbp-app python scripts/create_metabase_collections.py --config config/db_config.docker.json
```

Validate without recreating:

```powershell
docker compose run --rm sbp-app python scripts/create_metabase_collections.py --config config/db_config.docker.json --validate-only
```

## Suggested Charts

| Collection | Chart | X / grouping | Y metrics |
|---|---|---|---|
| `metabase_u6_focus_sessions` | Bar or combo | `focus_bucket` | `avg_task_completion_rate`, `avg_deep_work_hours` |
| `metabase_u7_doomscrolling` | Bar or combo | `doomscrolling_bucket` | `avg_notification_count`, `max_app_switch_frequency` |
| `metabase_u8_hybrid_sweet_spot` | Line | `remote_work_days` | `avg_productivity_score`, `avg_motivation_level` |
| `metabase_u9_late_night_usage` | Horizontal bar | `occupation` | `avg_stress_level` |
| `metabase_u10_physical_activity` | Bar | `activity_level` | `avg_burnout_risk` for low-productivity users |
| `metabase_u10_physical_activity` | Optional stacked/count bar | `activity_level`, stacked by `mental_state` | `user_count` |

## Notes

- These are query-result collections for dashboarding, not a third modeling schema.
- The source dataset is synthetic/simulated behavioral analytics data.
- Interpret results as demo analytics, not real-world medical, HR, or workplace policy conclusions.
- U7 buckets use MongoDB `$bucket` semantics: `[0,1)`, `[1,2)`, `[2,3)`, `3+`.
- U9 uses `late_night_device_usage == 1` because the inspected dataset stores it as a binary indicator.
- U10 visualizes low-productivity users with `productivity_category = "Low"` and compares `computed.activity_level` values: `below_average` and `above_average`.
