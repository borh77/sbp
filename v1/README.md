# V1 Initial Schema

V1 is the initial logical schema. It separates stable user attributes from behavioral and wellbeing assessment data, then joins them through `user_id` when analytical queries need user context.

## Collections

### `v1_users`

Stores user-level fields:

- `user_id`
- `age`
- `occupation`
- `work_mode`
- `device_usage_type`

### `v1_wellbeing_assessments`

Stores behavioral, productivity, health, work-environment, and burnout-result fields:

- `digital_behavior`
- `focus_productivity`
- `health_wellness`
- `work_environment`
- `burnout_result`

## Relationship

```text
v1_users.user_id = v1_wellbeing_assessments.user_id
```

This relationship is used with `$lookup` in analytical queries that need user attributes:

- U6 needs `work_mode`
- U7 needs `device_usage_type`
- U9 needs `occupation`

## Why This Is the Initial Schema

This version keeps at least two related entities instead of storing the entire row as one flat document. It makes the logical distinction between user identity/profile data and repeated wellbeing assessment data visible for the database design discussion.

## Expected Bottlenecks

- `$lookup` is needed for queries that combine assessment metrics with user attributes.
- Buckets such as focus-session ranges and doomscrolling ranges are calculated at runtime.
- Grouping over a large collection is expensive, especially on the full 5M-row dataset.
- U10 needs the global average `physical_activity`, so v1 either uses a more expensive aggregation or a two-step query.
