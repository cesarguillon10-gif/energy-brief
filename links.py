"""Check that every chosen story's source link can be opened.

- Direct publisher links are checked; stories with dead links (404/410/no such site) are dropped.
- Google News links are kept (they open the publisher's page in a normal browser).
- Paywalled outlets get "paywall": true so the page shows a 🔒 "Subscriber only" tag.
Usage: python3 -I links.py <day-folder>
"""
import json, re, subprocess, sys
from pathlib import Path

day_dir = Path(sys.argv[1])
UA = "PaulsEnergyBrief/1.0 (daily personal news digest; link check)"
PAYWALL = re.compile(r"utility ?week|montel|financial times|\bft\.com|the times|bloomberg|wall street journal|wsj|"
                     r"economist|recharge|telegraph|s&p global|spglobal|argus|icis|businessgreen|handelsblatt|"
                     r"les echos|new york times|nytimes|washington post|energy voice premium|new energy update", re.I)


def status(url):
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "20", "-A", UA, "-o", "/dev/null", "-w", "%{http_code}", url],
                       capture_output=True, text=True)
    return int(r.stdout or 0) if r.returncode == 0 else 0


brief = json.loads((day_dir / "brief.json").read_text())
arts = {a["id"]: a for a in json.loads((day_dir / "articles.json").read_text())}
chosen = list(brief["top3"]) + [s for sec in brief["sections"] for s in sec["stories"]]
dead = set()
for s in chosen:
    a = arts[s["id"]]
    s["paywall"] = bool(PAYWALL.search(a["source"] + " " + a["link"]))
    if "news.google.com" in a["link"]:
        continue
    code = status(a["link"])
    if code in (404, 410) or code == 0:
        print("dead link", code, a["link"][:90]); dead.add(s["id"])

brief["top3"] = [s for s in brief["top3"] if s["id"] not in dead]
for sec in brief["sections"]:
    sec["stories"] = [s for s in sec["stories"] if s["id"] not in dead]
brief["sections"] = [s for s in brief["sections"] if s["stories"]]
# takeaways are kept; the page only links those whose story is still shown
(day_dir / "brief.json").write_text(json.dumps(brief, indent=1, ensure_ascii=False))
print(f"links checked: {len(chosen)}, dropped {len(dead)}, paywalled {sum(s['paywall'] for s in chosen)}")
