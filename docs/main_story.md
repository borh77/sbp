## Main Story

The project compares an initial reference-based MongoDB schema with an optimized analytical schema for Product Manager questions U6-U10.

## Query Definitions

- U6 groups by focus-session bucket (`0`, `1-3`, `4+`) and reports average deep-work hours, average task-completion rate, dominant work mode, and count.
- U7 uses doomscrolling buckets `[0,1)`, `[1,2)`, `[2,3)`, and `3+`, then reports maximum app-switch frequency, average notification count, most common device usage type, and count.
- U8 filters to `workspace_quality > 6`, then groups by `remote_work_days` and reports average productivity score, average motivation level, and count.
- U9 filters records where `late_night_device_usage = 1`, because the dataset stores late-night usage as a binary indicator, then groups by occupation and reports average stress level, sleep quality, caffeine intake, and count.
- U10 filters to low-productivity users, splits by physical activity below/above average, and reports average burnout risk plus mental-state distribution. Primary mode is `productivity_category = "Low"` when present; fallback mode is `productivity_score <= 56` or the configured threshold.

For U9, the presentation idea is "high late-night device usage." In the inspected Kaggle CSV this field is binary, so `1` is the positive/high condition. Fallback threshold logic exists only for other dataset versions where the field might be normalized from 0-1 or stored on a 1-10 scale.

## V1 Talking Points

- `v1_users` stores stable user context.
- `v1_wellbeing_assessments` stores behavior, productivity, health, work environment, and burnout results.
- Queries U6, U7, and U9 use `$lookup` to bring user context into the analysis.
- U7 v1 uses MongoDB `$bucket` on `doomscrolling_duration`.
- U9 v1 detects the late-night usage type during measurement and uses `value == 1` for the inspected binary dataset.
- U10 v1 computes the global physical-activity average at query runtime.
- V1 is easier to explain logically but less efficient for repeated analytical reads.

## V2 Talking Points

- `v2_wellbeing_assessments` embeds `user_ref` using the Extended Reference pattern.
- `computed` stores buckets and flags used by U6-U10.
- U6, U7, U8, U9, and U10 read from `computed` and `user_ref` instead of doing repeated runtime bucketing or joins.
- U9 v2 stores `computed.late_night_high` from the binary indicator when values are 0/1.
- Indexes are aligned with the query filters/grouping dimensions.
- The design is intentionally query-driven.

## Expected Performance Argument

V2 should reduce query cost because:

- repeated `$lookup` operations are avoided;
- repeated bucket calculations are avoided;
- compound indexes are built around the U6-U10 access patterns.

## Practical Run Order

1. Import a 100k-row sample into v1.
2. Build v1 indexes.
3. Create v2 from v1.
4. Build v2 indexes.
5. Run `scripts/measure_queries.py`.
6. Use `results/performance_table.md` for the comparison slide.
