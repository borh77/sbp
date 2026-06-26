# Measured Bottlenecks

## Method

Performance was measured with MongoDB `explain("executionStats")` through `scripts/measure_queries.py`.

Compared metrics:

* `executionTimeMillis`
* `totalDocsExamined`
* improvement ratio, calculated as v1 execution time divided by v2 execution time

## Dataset-Size Note

Final measurement was performed on the full Kaggle dataset:

* 5,000,000 rows imported into v1
* 5,000,000 documents generated in v2
* Final table source: `results/performance_table.md`

The earlier 100,000-row run was used only for validation.

## Bottleneck Table

| Query | v1 bottleneck                                                                                     | v2 optimization                                                    | Evidence from full measurement                                                                        |  explanation                                                                                                                                                                                              |
| ----- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| U6    | `$lookup` to `v1_users` plus runtime focus bucket.                                                | `user_ref.work_mode` plus `computed.focus_sessions_bucket`.        | V1: 470,778 ms, 5,000,000 docs examined. V2: 18,536 ms, 5,000,000 docs examined. Improvement: 25.40x. | V2 removes the join and repeated bucket calculation. Even though both versions examine the same number of documents, v2 does less work per document.                                                             |
| U7    | `$lookup` plus `$bucket` and runtime grouping over doomscrolling.                                 | `computed.doomscrolling_bucket` plus `user_ref.device_usage_type`. | V1: 459,544 ms, 5,000,000 docs examined. V2: 20,228 ms, 5,000,000 docs examined. Improvement: 22.72x. | V2 stores the bucket used by the query and embeds the device type needed for grouping. Buckets are aligned with MongoDB `$bucket`: `[0,1)`, `[1,2)`, `[2,3)`, `3+`.                                              |
| U8    | Filter is moderately selective and v1 already has a useful compound index.                        | `computed.workspace_quality_ok` plus compound index.               | V1: 14,139 ms, 1,998,718 docs examined. V2: 18,878 ms, 1,998,718 docs examined. Improvement: 0.75x.   | U8 is the exception where v2 is slower. Both versions examine the same working set, and v1 already has an effective index on workspace quality and remote days. This shows that optimization is query-dependent. |
| U9    | Binary late-night filter still leaves many documents and then requires occupation lookup.         | `computed.late_night_high` plus embedded occupation.               | V1: 298,031 ms, 3,249,966 docs examined. V2: 20,291 ms, 3,249,966 docs examined. Improvement: 14.69x. | The inspected Kaggle CSV stores `late_night_device_usage` as binary 0/1, so U9 uses `1` as the positive condition. V2 avoids the user lookup by embedding occupation in `user_ref`.                              |
| U10   | Computes global physical-activity average at query time and depends on a low-productivity filter. | `computed.activity_level` plus productivity/activity index.        | V1: 42,434 ms, 5,000,000 docs examined. V2: 11,380 ms, 841,484 docs examined. Improvement: 3.73x.     | V2 turns a runtime global comparison into a stored computed category and examines far fewer documents. U10 uses `productivity_category = "Low"` if present, otherwise falls back to `productivity_score <= 56`.  |

## Summary

The optimized v2 schema significantly improves U6, U7, U9, and U10. The biggest gains come from avoiding repeated `$lookup` operations and storing query-specific computed fields. U8 is slower in v2 because the original v1 query already had a useful index and both schemas examine the same number of documents.
