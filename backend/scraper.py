# backend/scraper.py
# Simple example that generates/updates companies.csv from a seed list.
# You can expand this to pull from public datasets/APIs.
import csv, os

ROOT = os.path.dirname(__file__)
OUT = os.path.join(ROOT, "companies.csv")

seed = [
    # (Company, HQ, Industry, Career URL)
    ("Amazon","Seattle, WA","Tech","https://www.amazon.jobs"),
    ("Microsoft","Redmond, WA","Tech","https://careers.microsoft.com"),
    ("Google (Alphabet)","Mountain View, CA","Tech","https://careers.google.com"),
    # ... add more programmatically or read from public lists.
]

# For demo: duplicate seed to reach 1000 entries quickly (you can replace with real list)
expanded = []
for i in range(1,21):  # tweak multiplier to reach desired size (20*len(seed) ~ 60)
    for c in seed:
        name = f"{c[0]} #{i}" if i>1 else c[0]
        expanded.append([name, c[1], c[2], c[3], "no", "yes"])

# write CSV
with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Company Name","Headquarters","Industry","Career Page URL","Is_Startup","Scrapable"])
    for r in expanded:
        writer.writerow(r)
print(f"Wrote {len(expanded)} rows to {OUT}")
