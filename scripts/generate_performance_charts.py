from __future__ import annotations

from pathlib import Path


PERFORMANCE_TABLE = Path("results/performance_table.md")
CHARTS_DIR = Path("results/charts")


def parse_number(value: str) -> float | None:
    value = value.strip().replace(",", "")
    if not value or value.upper() == "TBD":
        return None
    if value.endswith("x"):
        value = value[:-1]
    try:
        return float(value)
    except ValueError:
        return None


def parse_markdown_table(path: Path) -> list[dict[str, str]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]
    if len(table_lines) < 3:
        return []

    header = [column.strip() for column in table_lines[0].strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        values = [value.strip() for value in line.strip("|").split("|")]
        if len(values) != len(header):
            continue
        rows.append(dict(zip(header, values)))
    return rows


def chart_rows(rows: list[dict[str, str]]) -> list[dict[str, float | str]]:
    parsed = []
    for row in rows:
        v1_time = parse_number(row.get("V1 time ms", ""))
        v2_time = parse_number(row.get("V2 time ms", ""))
        v1_docs = parse_number(row.get("V1 docs examined", ""))
        v2_docs = parse_number(row.get("V2 docs examined", ""))
        if None in (v1_time, v2_time, v1_docs, v2_docs):
            continue
        parsed.append(
            {
                "query": row["Query"],
                "v1_time": v1_time,
                "v2_time": v2_time,
                "v1_docs": v1_docs,
                "v2_docs": v2_docs,
            }
        )
    return parsed


def save_grouped_bar_chart(
    labels: list[str],
    v1_values: list[float],
    v2_values: list[float],
    title: str,
    ylabel: str,
    output_path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    positions = range(len(labels))
    width = 0.36

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar([position - width / 2 for position in positions], v1_values, width, label="V1")
    ax.bar([position + width / 2 for position in positions], v2_values, width, label="V2")
    ax.set_title(title)
    ax.set_xlabel("Query")
    ax.set_ylabel(ylabel)
    ax.set_xticks(list(positions))
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> None:
    rows = chart_rows(parse_markdown_table(PERFORMANCE_TABLE))
    if not rows:
        print(f"No complete numeric rows found in {PERFORMANCE_TABLE}")
        return

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    labels = [str(row["query"]) for row in rows]

    time_chart = CHARTS_DIR / "query_execution_time.png"
    docs_chart = CHARTS_DIR / "docs_examined.png"

    save_grouped_bar_chart(
        labels,
        [float(row["v1_time"]) for row in rows],
        [float(row["v2_time"]) for row in rows],
        "MongoDB Query Execution Time",
        "Execution time (ms)",
        time_chart,
    )
    save_grouped_bar_chart(
        labels,
        [float(row["v1_docs"]) for row in rows],
        [float(row["v2_docs"]) for row in rows],
        "MongoDB Documents Examined",
        "Documents examined",
        docs_chart,
    )

    print(f"Wrote {time_chart}")
    print(f"Wrote {docs_chart}")


if __name__ == "__main__":
    main()
