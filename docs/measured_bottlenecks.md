# Measured Bottlenecks

## Method

Performance is measured with MongoDB `explain("executionStats")` through `scripts/measure_queries.py`.

Compared metrics:

- `executionTimeMillis`
- `totalDocsExamined`
- improvement ratio, calculated as v1 time divided by v2 time

## Dataset-Size Note

Update this after the final run: measured on either 100,000-row sample or full 5,000,000-row dataset.

The current values should be taken from `results/performance_table.md`. If the table still contains sample-run values, label them as a validation run in the presentation.

## Bottleneck Table

| Query | v1 bottleneck | v2 optimization | Evidence from measurement | Defense explanation |
|---|---|---|---|---|
| U6 | `$lookup` to `v1_users` plus runtime focus bucket. | `user_ref.work_mode` plus `computed.focus_sessions_bucket`. | Fill from `results/performance_table.md` after final measurement. | V2 removes the join and repeated bucket calculation for the focus-session access pattern. |
| U7 | `$lookup` plus `$bucket`/runtime grouping over doomscrolling. | `computed.doomscrolling_bucket` plus `user_ref.device_usage_type`. | Fill from `results/performance_table.md` after final measurement. | V2 stores the bucket used by the query and embeds the device type needed for grouping. Buckets are aligned with MongoDB `$bucket`: `[0,1)`, `[1,2)`, `[2,3)`, `3+`. |
| U8 | Filter is moderately selective; many documents still enter grouping. | `computed.workspace_quality_ok` plus compound index. | Fill from `results/performance_table.md` after final measurement. | Improvement may be smaller because v1 also has a useful workspace/remote-days index. |
| U9 | The positive late-night indicator can still leave many documents and then requires occupation lookup. | `computed.late_night_high` plus embedded occupation. | Fill from `results/performance_table.md` after final measurement. | The inspected Kaggle CSV stores `late_night_device_usage` as binary 0/1, so U9 uses `1` as the positive condition. Thresholds are fallback only for other dataset versions. |
| U10 | Computes global physical-activity average at query time and depends on a low-productivity filter. | `computed.activity_level` plus productivity/activity index. | Fill from `results/performance_table.md` after final measurement. | V2 turns a runtime global comparison into a stored category aligned with the query filter. U10 uses `productivity_category = "Low"` if present, otherwise falls back to `productivity_score <= 56` or the configured threshold. |
