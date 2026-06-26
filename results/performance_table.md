| Query | V1 time ms | V1 docs examined | V2 time ms | V2 docs examined | Improvement | Main optimization |
|---|---:|---:|---:|---:|---:|---|
| U6 | 470778 | 5000000 | 18536 | 5000000 | 25.40x | Computed focus bucket + no lookup |
| U7 | 459544 | 5000000 | 20228 | 5000000 | 22.72x | Computed doomscrolling bucket + no lookup |
| U8 | 14139 | 1998718 | 18878 | 1998718 | 0.75x | workspace_quality_ok filter + compound index |
| U9 | 298031 | 3249966 | 20291 | 3249966 | 14.69x | binary late_night_high + occupation in user_ref |
| U10 | 42434 | 5000000 | 11380 | 841484 | 3.73x | activity_level + productivity index |
