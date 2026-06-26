# Measurement Notes

- Current measurement dataset size: 5,000,000 rows
- Command used: docker compose run --rm sbp-app python scripts/measure_queries.py --config config/db_config.full.json

Notes:

- The 100k run was used only for validation.
- The final performance table is based on the full 5,000,000-row dataset.
- `late_night_device_usage` was inspected and found to be binary 0/1.
- U9 uses `1` as the positive late-night usage condition.
- U7 doomscrolling buckets use `[0,1)`, `[1,2)`, `[2,3)`, and `3+`.
- U10 uses `productivity_category = "Low"` when present; otherwise it falls back to `productivity_score <= 56` or the configured threshold.
- U8 is the only query where v2 is slower because v1 already uses a selective index and both versions examine the same number of documents.
- Metabase result collections are generated from v2.
