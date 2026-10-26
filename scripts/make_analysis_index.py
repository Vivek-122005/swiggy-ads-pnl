"""Write an index page for the executed WBR notebooks published under /analysis/ on Pages."""
import html
import sys
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else "dashboard/site/analysis")
pages = sorted(out.glob("wbr_week_*.html"))
items = "\n".join(f'<li><a href="{p.name}">Week {int(p.stem.split("_")[-1])}</a></li>' for p in pages)
out.joinpath("index.html").write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>WBR investigations</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;color:#202124;background:#fff}}
a{{color:#1a73e8}}</style></head><body>
<h1>WBR investigation notebooks</h1>
<p>Executed weekly by GitHub Actions against the dbt warehouse. <b>All data is simulated</b> — not Swiggy data.
The one-page memos are in the <a href="https://github.com/Vivek-122005/swiggy-ads-pnl/tree/main/reports">repo</a>;
the dashboard is <a href="../">here</a>.</p>
<ul>{items}</ul></body></html>""")
print(f"indexed {len(pages)} notebooks -> {html.escape(str(out))}/index.html")
