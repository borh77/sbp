# V2 Optimized Schema

V2 is optimized for analytical queries U6-U10. The main collection is `v2_wellbeing_assessments`; `v2_users` can remain as a reference/documentation collection, but the query workload should not need repeated `$lookup` operations.

## Optimized Collection

### `v2_wellbeing_assessments`

This collection keeps the v1 assessment structure and adds:

- `user_ref`
- `computed`

## Extended Reference Pattern

`user_ref` embeds the user fields repeatedly needed by U6-U10:

- `user_id`
- `occupation`
- `work_mode`
- `age_group`
- `device_usage_type`

This avoids repeated joins to `v2_users` during analytical queries.

## Computed Pattern

`computed` stores values that v1 calculates at runtime:

- `focus_sessions_bucket`
- `doomscrolling_bucket`
- `activity_level`
- `late_night_high`
- `workspace_quality_ok`

These fields make the query pipelines shorter and allow indexes to match the access patterns more directly.

## Indexes

The optimized indexes are defined in `mongo/indexes_v2.js`:

- `computed.focus_sessions_bucket + user_ref.work_mode`
- `computed.doomscrolling_bucket + user_ref.device_usage_type`
- `computed.workspace_quality_ok + work_environment.remote_work_days`
- `computed.late_night_high + user_ref.occupation`
- `burnout_result.productivity_category + computed.activity_level + burnout_result.mental_state`
- `user_id`

## Why U6-U10 Are Faster in V2

- U6 avoids runtime focus bucket calculation and avoids `$lookup` for `work_mode`.
- U7 avoids runtime doomscrolling bucket calculation and avoids `$lookup` for `device_usage_type`.
- U8 uses the precomputed workspace-quality flag.
- U9 filters directly on `computed.late_night_high`, derived from binary `late_night_device_usage`, and groups by embedded `occupation`.
- U10 avoids recalculating average activity during every query by using `computed.activity_level`.
