"""Collect recent energy-flexibility articles from RSS/Atom feeds + Google News (free, no AI).

Usage: python3 -I collect.py <out.json> [hours=48]
Stdlib only, so it runs the same on the Mac and on GitHub Actions.
"""
import html, json, re, subprocess, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
out_path = Path(sys.argv[1])
hours = int(sys.argv[2]) if len(sys.argv) > 2 else 48
cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
UA = "EnergyBriefBot/1.0 (personal news digest)"

# Words that make an article relevant to Axle's world. Used to rank before Claude sees them.
KEYWORDS = {
    3: ["flexib", "virtual power plant", "vpp", "demand side response", "demand response", "dsr", "axle energy",
        "aggregator", "balancing mechanism", "balancing market", "smart charg", "vehicle-to-grid", "v2g",
        "kraken", "kaluza", "ohme", "tibber", "enode", "sympower", "voltalis", "flexitricity", "piclo"],
    2: ["ofgem", "neso", "desnz", "grid", "battery", "storage", "heat pump", "ev charg", "electric vehicle",
        "market reform", "rema", "capacity market", "ancillary", "frequency", "tariff", "time-of-use", "octopus",
        "interconnect", "network charg", "distribution", "dso", "tso", "wholesale", "ercot", "entso"],
    1: ["energy", "electricity", "power", "renewable", "solar", "wind", "net zero", "decarbon", "funding",
        "raises", "acquires", "startup", "utility", "regulator", "germany", "netherlands", "france", "nordic",
        "spain", "italy", "ireland", "australia", "california"],
}


def score(text):
    t = text.lower()
    return sum(w * t.count(k) for w, ks in KEYWORDS.items() for k in ks)


def clean(s, n=400):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()[:n]


def when(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def fetch(url):
    # curl uses the system certificate store (python.org Python on macOS has none by default)
    r = subprocess.run(["curl", "-sSL", "--max-time", "25", "--compressed", "-A", UA,
                        "-H", "Accept: application/rss+xml, application/atom+xml, */*", url],
                       capture_output=True)
    if r.returncode or not r.stdout.strip():
        raise RuntimeError(f"curl {r.returncode} {r.stderr.decode()[:60]}")
    return r.stdout


def parse(raw, source):
    root = ET.fromstring(raw)
    items = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        g = {c.tag.split("}")[-1]: c for c in it}
        title = clean(g["title"].text if "title" in g else "", 200)
        link = ""
        if "link" in g:
            link = (g["link"].text or "").strip() or g["link"].get("href", "")
        for c in it:
            if c.tag.split("}")[-1] == "link" and c.get("rel", "alternate") == "alternate" and c.get("href"):
                link = c.get("href")
        date = None
        for k in ("pubDate", "published", "updated", "date"):
            if k in g and g[k].text:
                date = when(g[k].text)
                if date:
                    break
        img = ""
        for c in it:
            t = c.tag.split("}")[-1]
            if t in ("content", "thumbnail") and c.get("url") and (c.get("medium") == "image" or t == "thumbnail"
                                                                or re.search(r"\.(jpe?g|png|webp)", c.get("url"), re.I)):
                img = img or c.get("url")
            if t == "enclosure" and (c.get("type") or "").startswith("image") and c.get("url"):
                img = img or c.get("url")
            if t == "group":
                for cc in c:
                    if cc.get("url") and cc.tag.split("}")[-1] in ("content", "thumbnail"):
                        img = img or cc.get("url")
        if not img:
            for k in ("encoded", "content", "description", "summary"):
                if k in g and g[k].text:
                    m = re.search(r'<img[^>]+src=["\']([^"\']+)', g[k].text)
                    if m and not m.group(1).startswith("data:"):
                        img = html.unescape(m.group(1)); break
        desc = ""
        for k in ("description", "summary", "content", "encoded"):
            if k in g and (g[k].text or "").strip():
                desc = clean(g[k].text)
                break
        src = source
        if "source" in g and (g["source"].text or "").strip():  # Google News gives the real outlet
            src = g["source"].text.strip()
            title = re.sub(r"\s+-\s+" + re.escape(src) + r"$", "", title)
        if title and link and date:
            items.append({"title": title, "link": link, "source": src, "date": date, "summary": desc, "image": img})
    return items


def gnews(q):
    return ("https://news.google.com/rss/search?" +
            urllib.parse.urlencode({"q": q + f" when:{max(1, hours // 24)}d", "hl": "en-GB", "gl": "GB", "ceid": "GB:en"}))


cfg = json.loads((BASE / "feeds.json").read_text())
used_path = BASE / "data" / "used.json"
USED = set(json.loads(used_path.read_text())) if used_path.exists() else set()
jobs = [(f["name"], f["url"]) for f in cfg["feeds"]] + [(f"Google News · {g['name']}", gnews(g["q"])) for g in cfg["google_news"]]


def run(job):
    name, url = job
    try:
        return name, parse(fetch(url), name.replace("Google News · ", "") if name.startswith("Google") else name), None
    except Exception as e:
        return name, [], str(e)[:80]


arts, seen, report = [], set(), []
with ThreadPoolExecutor(8) as ex:
    for name, items, err in ex.map(run, jobs):
        fresh = [i for i in items if i["date"] >= cutoff]
        report.append(f"{'FAIL' if err else 'ok  '} {name}: {len(fresh)} fresh / {len(items)} {err or ''}")
        for i in fresh:
            key = re.sub(r"[^a-z0-9]", "", i["title"].lower())[:70]
            if key in seen or i["link"] in USED or key in USED:
                continue
            seen.add(key)
            i["score"] = score(i["title"] + " " + i["summary"])
            arts.append(i)

BLOCK = re.compile(r"simply wall|kalkine|coin ?gabbar|marketbeat|benzinga|tipranks|zacks|seeking alpha|investing\.com|"
                   r"stocktitan|openpr|ein presswire|newsbreak|msn|yahoo finance|motley|crypto|bitcoin|devdiscourse", re.I)
arts = [a for a in arts if a["score"] > 0 and not BLOCK.search(a["source"])]
arts.sort(key=lambda a: (-a["score"], -a["date"].timestamp()))
arts = arts[:120]
for n, a in enumerate(arts, 1):
    a["id"] = n
    a["date"] = a["date"].strftime("%Y-%m-%d")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(arts, indent=1, ensure_ascii=False))
print("\n".join(report))
print(f"kept {len(arts)} relevant articles from the last {hours}h -> {out_path}")
