"""Keep only the columns the simulator needs from the 570 MB Zomato Bangalore file (drops review text)."""
import csv
import sys

csv.field_size_limit(sys.maxsize)
KEEP = ["name", "location", "rate", "approx_cost(for two people)", "cuisines", "rest_type", "votes", "listed_in(city)"]

src, dst = sys.argv[1], sys.argv[2]
n = 0
with open(src, newline="", encoding="utf-8", errors="replace") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    w = csv.writer(g)
    w.writerow(KEEP)
    for row in csv.DictReader(f):
        w.writerow([row.get(k, "") for k in KEEP])
        n += 1
print(f"{dst}: {n:,} rows")
