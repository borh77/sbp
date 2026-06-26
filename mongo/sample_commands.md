# Sample MongoDB Commands

Run these commands from the repository root after MongoDB is running.

```powershell
mongosh < mongo/indexes_v1.js
mongosh < v1/queries/U6_focus_sessions.js
mongosh < v1/queries/U7_doomscrolling.js
mongosh < v1/queries/U8_hybrid_sweet_spot.js
mongosh < v1/queries/U9_late_night_usage.js
mongosh < v1/queries/U10_physical_activity.js

mongosh < mongo/indexes_v2.js
mongosh < v2/queries/U6_focus_sessions_optimized.js
mongosh < v2/queries/U7_doomscrolling_optimized.js
mongosh < v2/queries/U8_hybrid_sweet_spot_optimized.js
mongosh < v2/queries/U9_late_night_usage_optimized.js
mongosh < v2/queries/U10_physical_activity_optimized.js
```

To inspect one query with execution statistics, open the matching query file and run the commented `explain("executionStats")` version.
