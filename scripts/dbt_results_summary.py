"""Turn dbt's run_results.json into a short Markdown summary (used in the GitHub Actions job summary)."""
import json
import sys
from collections import Counter

res = json.load(open(sys.argv[1]))["results"]
c = Counter(r["status"] for r in res)
print("## dbt build\n")
print(" | ".join(f"**{k}**: {v}" for k, v in sorted(c.items())))
warn = [r for r in res if r["status"] in ("warn", "fail", "error")]
if warn:
    print("\n| status | node | failures | message |\n|---|---|---|---|")
    for r in warn:
        msg = (r.get("message") or "").replace("\n", " ")[:120]
        print(f"| {r['status']} | `{r['unique_id'].split('.')[-1]}` | {r.get('failures')} | {msg} |")
