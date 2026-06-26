# Inside Digital Burnout: Behavioral Analytics & ML

## Team

- Emilija Simic RA3/2022
- Borisa Hrnjez RA95/2022

## Domain and Dataset

This project models behavioral, productivity, and wellbeing signals from a Kaggle digital burnout/productivity analytics dataset. The database is MongoDB, and the repository is organized in two schema versions so the initial logical model can be compared with an access-pattern-driven optimized model.

Dataset facts:

- Source: Kaggle digital burnout/productivity analytics dataset
- File: `digital_burnout_productivity_dataset_5M.csv`
- Size: 5,000,000 rows, 34 columns, one CSV file, more than 1 GB
- Local path expected by config: `data/digital_burnout_productivity_dataset_5M.csv`
- The dataset file is intentionally ignored by Git.

## Repository Structure

```text
sbp/
  config/                  MongoDB and import configuration example
  docs/                    Dataset notes, modeling decisions, defense notes
  mongo/                   Index creation scripts and sample shell commands
  results/                 Performance table and query output placeholders
  scripts/                 Import, transformation, validation, measurement scripts
  v1/                      Initial reference-based schema and U6-U10 queries
  v2/                      Optimized schema and U6-U10 queries
```

## Schema Versions

- [v1 initial schema](v1/README.md): separates users from wellbeing assessments and uses references through `user_id`.
- [v2 optimized schema](v2/README.md): keeps analytical assessment data together with selected user fields in `user_ref`, plus precomputed buckets in `computed`.

## Product Manager Queries U6-U10

- U6: Focus sessions and task completion by work mode
- U7: Doomscrolling buckets and attention disruption by device usage type
- U8: Hybrid work sweet spot using remote work days and workspace quality
- U9: Late-night device usage and health degradation by occupation
- U10: Physical activity vs burnout risk among low-productivity users

## Implementation Steps

1. Import a limited sample of the CSV into v1 collections.
2. Create v1 indexes.
3. Run v1 analytical queries and collect `explain("executionStats")` metrics.
4. Build v2 collections from v1 data using Extended Reference and Computed fields.
5. Create v2 indexes aligned with U6-U10.
6. Run v2 analytical queries and compare performance.

## How to Run

```powershell
pip install -r requirements.txt
Copy-Item config/db_config.example.json config/db_config.json
python scripts/import_v1.py --config config/db_config.json --limit 100000
mongosh < mongo/indexes_v1.js
python scripts/create_v2.py --config config/db_config.json
mongosh < mongo/indexes_v2.js
python scripts/measure_queries.py --config config/db_config.json
```

On Linux/macOS, replace the config copy command with:

```bash
cp config/db_config.example.json config/db_config.json
```

## Docker Run Workflow

Docker is an alternative workflow for Windows when MongoDB is not installed locally. It starts MongoDB in Docker, keeps the large Kaggle CSV mounted from the local `data/` folder, and runs the Python scripts inside the `sbp-app` container.

Place the dataset here before importing:

```text
data/digital_burnout_productivity_dataset_5M.csv
```

The `data/` folder is ignored by Git and is not copied into the Docker image.

Start MongoDB and Mongo Express:

```powershell
docker compose up -d mongo mongo-express
```

Check container status and wait until MongoDB is healthy:

```powershell
docker compose ps
```

Import a 100k-row sample into v1. Use `--drop-existing` when you want to restart the sample import without deleting the Docker MongoDB volume:

```powershell
docker compose run --rm sbp-app python scripts/import_v1.py --config config/db_config.docker.json --limit 100000
```

Restartable sample import:

```powershell
docker compose run --rm sbp-app python scripts/import_v1.py --config config/db_config.docker.json --limit 100000 --drop-existing
```

Validate collection counts:

```powershell
docker compose run --rm sbp-app python scripts/validate_counts.py --config config/db_config.docker.json
```

Diagnose imported field ranges:

```powershell
docker compose run --rm sbp-app python scripts/diagnose_fields.py --config config/db_config.docker.json
```

Run diagnostics before final measurement to verify query assumptions, including U7 bucket ranges, binary late-night usage, `productivity_category` values, and the U10 low-productivity fallback threshold.

Create v1 indexes. The `mongo` container does not mount this project at `/app`, so this command is the PowerShell-safe alternative to running `mongosh` inside the `mongo` container:

```powershell
Get-Content mongo/indexes_v1.js | docker compose run --rm -T mongosh
```

Create v2 from v1:

```powershell
docker compose run --rm sbp-app python scripts/create_v2.py --config config/db_config.docker.json --drop-existing
```

Diagnose v1 ranges and v2 computed flags:

```powershell
docker compose run --rm sbp-app python scripts/diagnose_fields.py --config config/db_config.docker.json
```

Create v2 indexes:

```powershell
Get-Content mongo/indexes_v2.js | docker compose run --rm -T mongosh
```

The same v2 index command can also be run with:

```powershell
docker compose run --rm mongosh --file /app/mongo/indexes_v2.js
```

Measure query performance:

```powershell
docker compose run --rm sbp-app python scripts/measure_queries.py --config config/db_config.docker.json
```

### Full Dataset Workflow

For the full 5,000,000-row dataset, use `config/db_config.full.json`, which sets `limit_rows` to `null`. This imports every CSV row without relying on the sample limit in `config/db_config.docker.json`.

Restart v1 and import the full dataset:

```powershell
docker compose run --rm sbp-app python scripts/import_v1.py --config config/db_config.full.json --drop-existing
```

An equivalent explicit-limit run is:

```powershell
docker compose run --rm sbp-app python scripts/import_v1.py --config config/db_config.docker.json --limit 5000000 --drop-existing
```

Create v1 indexes after the full import:

```powershell
Get-Content mongo/indexes_v1.js | docker compose run --rm -T mongosh
```

Build v2 using the streaming/batched transformation:

```powershell
docker compose run --rm sbp-app python scripts/create_v2.py --config config/db_config.full.json --drop-existing
```

Create v2 indexes and measure the full run:

```powershell
docker compose run --rm mongosh --file /app/mongo/indexes_v2.js
docker compose run --rm sbp-app python scripts/measure_queries.py --config config/db_config.full.json
```

Access points:

- MongoDB is available from Windows at `localhost:27017`.
- Mongo Express is available at `http://localhost:8081`.
- Inside Docker, scripts use `mongodb://mongo:27017` from `config/db_config.docker.json`.

If you already created v2 before changing the late-night binary-indicator logic, rebuild v2 and remeasure:

```powershell
docker compose run --rm sbp-app python scripts/create_v2.py --config config/db_config.docker.json --drop-existing
docker compose run --rm mongosh --file /app/mongo/indexes_v2.js
docker compose run --rm sbp-app python scripts/measure_queries.py --config config/db_config.docker.json
```

Cleanup:

```powershell
docker compose down
```

This stops containers but keeps the MongoDB data volume.

```powershell
docker compose down -v
```

This stops containers and deletes the MongoDB data volume. Use it only when starting fresh.

## Results and Statistics

The starter comparison table is in [results/performance_table.md](results/performance_table.md). After running the measurement script, raw JSON summaries are written to `results/query_outputs/`.

## Performance Evidence

`scripts/measure_queries.py` reads the v1/v2 analytical pipelines, runs MongoDB `explain("executionStats")`, writes per-query metrics to `results/query_outputs/`, and updates `results/performance_table.md`.

`scripts/generate_performance_charts.py` creates chart PNGs from the current `results/performance_table.md`:

```powershell
python scripts/generate_performance_charts.py
```

Docker equivalent:

```powershell
docker compose run --rm sbp-app python scripts/generate_performance_charts.py
```

The table and generated charts must state whether they come from the 100k validation sample or the full 5,000,000-row run. Full dataset performance should be regenerated after full import, v2 build, and index creation.

U7 doomscrolling buckets are `[0,1)`, `[1,2)`, `[2,3)`, and `3+`. U10 uses `productivity_category = "Low"` if that category exists; if not, `scripts/measure_queries.py` falls back to `productivity_score <= low_productivity_score_threshold` from config, default `56`.

## Metabase Dashboard Setup

Metabase runs in Docker with the existing MongoDB stack and is available at [http://localhost:3000](http://localhost:3000/).

Start only MongoDB and Metabase:

```powershell
docker compose up -d metabase
```

Start the full stack:

```powershell
docker compose up -d
```

When adding MongoDB as a Metabase database, use:

- Host: `mongo`
- Port: `27017`
- Database: `digital_burnout_v2`
- Authentication: none

Inside Docker, Metabase must connect to MongoDB using host `mongo`, not `localhost`, because `mongo` is the Docker Compose service name.

Expected dashboard workflow:

1. Import/load data.
2. Create the v2 optimized schema.
3. Create the Metabase result collections.
4. Start Metabase.
5. Connect Metabase to MongoDB database `digital_burnout_v2`.

Create or refresh the Metabase collections:

```powershell
python scripts/create_metabase_collections.py --config config/db_config.json
```

Docker equivalent:

```powershell
docker compose run --rm sbp-app python scripts/create_metabase_collections.py --config config/db_config.docker.json
```

Validate existing Metabase collections without recreating them:

```powershell
docker compose run --rm sbp-app python scripts/create_metabase_collections.py --config config/db_config.docker.json --validate-only
```

Use Metabase on the small aggregated collections, not directly on the full 5,000,000-row raw dataset.

Visualization collections and suggested charts:

- `metabase_u6_focus_sessions`: bar chart, x = `focus_bucket`, y = `avg_task_completion_rate` and `avg_deep_work_hours`.
- `metabase_u7_doomscrolling`: bar chart, x = `doomscrolling_bucket`, y = `avg_notification_count` and `max_app_switch_frequency`.
- `metabase_u8_hybrid_sweet_spot`: line chart, x = `remote_work_days`, y = `avg_productivity_score` and `avg_motivation_level`.
- `metabase_u9_late_night_usage`: horizontal bar chart, y = `occupation`, x = `avg_stress_level`.
- `metabase_u10_physical_activity`: bar chart, x = `activity_level`, y = `avg_burnout_risk`.

The Kaggle dataset is synthetic/simulated behavioral analytics data. Dashboard conclusions should be presented as analytical/demo conclusions, not real-world medical, HR, or workplace policy claims.

## Notes

The Python scripts use configurable CSV column aliases because Kaggle exports often vary between title case, snake case, and spaced column names. The expected logical field names are documented in [docs/dataset_description.md](docs/dataset_description.md).
