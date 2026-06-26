# Modeling Decisions

## Why Not One Giant Object

The dataset could be imported as one document per CSV row, but that would hide the logical model. It is clearer to distinguish users from wellbeing assessments and to show how analytical access patterns change the schema between v1 and v2.

## Why V1 Has Two Related Entities

V1 contains `v1_users` and `v1_wellbeing_assessments`. User fields such as occupation, work mode, age, and device usage type are separated from behavioral and wellbeing measurements. The relationship is:

```text
v1_users.user_id = v1_wellbeing_assessments.user_id
```

This demonstrates a reference-based design and gives a baseline for measuring the cost of `$lookup` in MongoDB.

## Why V2 Denormalizes Selectively

V2 does not denormalize every possible user field. It embeds only the fields repeatedly needed by U6-U10:

- `occupation`
- `work_mode`
- `age_group`
- `device_usage_type`

This is the Extended Reference pattern: keep a reference identity while embedding the small set of fields needed by frequent reads.

## Why V2 Uses Computed Fields

Several queries repeatedly calculate the same categories:

- focus-session buckets
- doomscrolling buckets
- late-night usage flag
- workspace-quality flag
- physical-activity level

V2 stores these in `computed`, following the Computed pattern. This reduces repeated runtime calculation and allows compound indexes to match the analytical workload.

## Application-Driven Schema

The optimized schema is driven by the U6-U10 analytical questions, not by a generic normalized model. This follows MongoDB's application-driven schema design: model the data according to the queries the application must answer efficiently.
