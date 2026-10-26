"""The anomaly answer key must never feed the warehouse or the dashboard."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_answer_key_not_referenced_downstream():
    offenders = []
    for folder in ("dbt/models", "dbt/macros", "dbt/tests", "dashboard"):
        for p in (ROOT / folder).rglob("*"):
            if p.is_file() and p.suffix in {".sql", ".yml", ".py", ".js", ".html"} and "mock_data" not in p.name:
                if "answer_key" in p.read_text(errors="ignore") or "anomalies.csv" in p.read_text(errors="ignore"):
                    offenders.append(str(p.relative_to(ROOT)))
    assert not offenders, f"answer key referenced in: {offenders}"
