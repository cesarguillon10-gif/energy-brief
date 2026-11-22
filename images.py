"""Find, download and resize one picture per story (and for 'Learn one thing').

Order: the article's own feed image -> the article page's og:image -> the Wikipedia photo Claude suggested.
Saves docs/img/<date>-<n>.jpg and records "img" (+ "credit") in brief.json. Logos/tiny images are skipped.
Usage: python3 -I images.py <day-folder> <docs-folder>
"""
import json, re, shutil, subprocess, sys, time, urllib.parse
from pathlib import Path

day_dir, docs = Path(sys.argv[1]), Path(sys.argv[2])
D = day_dir.name
out_dir = docs / "img"
out_dir.mkdir(parents=True, exist_ok=True)
tmp = day_dir / "_img"
tmp.mkdir(exist_ok=True)
brief = json.loads((day_dir / "brief.json").read_text())
arts = {a["id"]: a for a in json.loads((day_dir / "articles.json").read_text())}
UA = "PaulsEnergyBrief/1.0 (https://github.com/cesarguillon10-gif/energy-brief; daily personal digest)"

CACHE_PATH = day_dir.parent / "wiki-cache.json"
CACHE = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}

try:
    from PIL import Image
except Exception:
    Image = None


def curl(url, dest=None, limit=None):
    args = ["curl", "-sSL", "--max-time", "20", "-A", UA, url]
    if dest:
        args += ["-o", str(dest)]
    if limit:
        args += ["-r", f"0-{limit}"]
    r = subprocess.run(args, capture_output=True)
    return r.returncode == 0, r.stdout


def og_image(link):
    if "news.google.com" in link:
        return ""
    ok, body = curl(link, limit=400000)
    if not ok:
        return ""
    t = body.decode("utf-8", "ignore")
    for pat in (r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)'):
        m = re.search(pat, t, re.I)
        if m:
            return urllib.parse.urljoin(link, m.group(1).replace("&amp;", "&"))
    return ""


def wiki_image(title):
    """1000px lead photo of an English Wikipedia article (free images only, so usually not a logo)."""
    if not title:
        return ""
    if title in CACHE:
        return CACHE[title]
    q = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "pageimages", "pithumbsize": 1000,
                                "format": "json", "redirects": 1})
    src = ""
    for attempt in range(3):
        time.sleep(1.5 * (attempt + 1))                # be gentle: Wikimedia rate-limits bursts
        ok, body = curl("https://en.wikipedia.org/w/api.php?" + q)
        try:
            for p in json.loads(body)["query"]["pages"].values():
                s = (p.get("thumbnail") or {}).get("source", "")
                if s and not re.search(r"logo|\.svg", s, re.I):
                    src = s
            break
        except Exception:
            continue                                   # rate-limited or bad reply: wait and retry
    CACHE[title] = src
    return src


FALLBACK = {"flex": ["Transmission tower", "Electrical substation", "Smart grid", "Overhead power line"],
            "markets": ["Electrical grid", "Wind farm", "Solar farm", "Power station"],
            "devices": ["Charging station", "Heat pump", "Electric car", "Home battery"],
            "players": ["Smart meter", "Control room", "Data center", "Electric vehicle"],
            "deals": ["Wind farm", "Solar panel", "Battery storage power station", "Offshore wind power"],
            "learn": ["Control room", "Electrical substation", "Load profile", "Electricity meter"]}
USED = set()


def save(url, name, width):
    if not url:
        return False
    raw = tmp / (name + ".raw")
    ok, _ = curl(url, dest=raw)
    if not ok or not raw.exists() or raw.stat().st_size < 4000:
        return False
    out = out_dir / (name + ".jpg")
    try:
        if Image:
            im = Image.open(raw)
            if im.width < 320 or im.height < 180 or im.width / max(im.height, 1) > 3.2:
                return False                       # logos, banners, icons
            im = im.convert("RGB")
            if im.width > width:
                im = im.resize((width, round(im.height * width / im.width)))
            im.save(out, "JPEG", quality=72, optimize=True, progressive=True)
        else:                                      # macOS fallback
            p = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(raw)], capture_output=True, text=True).stdout
            w, h = (int(x) for x in re.findall(r"pixel(?:Width|Height): (\d+)", p)[:2])
            if w < 320 or h < 180 or w / h > 3.2:
                return False
            r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "72", "--resampleWidth",
                                str(min(width, w)), str(raw), "--out", str(out)], capture_output=True)
            if r.returncode:
                return False
        return out.exists() and out.stat().st_size > 3000
    except Exception:
        return False


n = 0
def picture(obj, link="", feed_img="", width=760, kind="flex"):
    global n
    n += 1
    name = f"{D}-{n}"
    tries = [(lambda: feed_img, ""), (lambda: og_image(link) if link else "", ""),
             (lambda: wiki_image(obj.get("wiki")), "Photo: Wikipedia")]
    tries += [(lambda t=t: wiki_image(t), "Photo: Wikipedia") for t in FALLBACK.get(kind, FALLBACK["markets"])]
    for get, credit in tries:
        url = get()
        if url and url not in USED and save(url, name, width):
            USED.add(url)
            obj["img"] = f"img/{name}.jpg"
            obj["credit"] = credit
            return True
    obj.pop("img", None)
    return False


got = total = 0
for i, s in enumerate(brief["top3"]):
    a = arts[s["id"]]
    total += 1; got += picture(s, a["link"], a.get("image", ""), 1100 if i == 0 else 760)
for sec in brief["sections"]:
    for s in sec["stories"]:
        a = arts[s["id"]]
        total += 1; got += picture(s, a["link"], a.get("image", ""), 480, sec["key"])
total += 1; got += picture(brief["learn"], width=760, kind="learn")

shutil.rmtree(tmp, ignore_errors=True)
CACHE_PATH.write_text(json.dumps({k: v for k, v in CACHE.items() if v}, indent=1))
(day_dir / "brief.json").write_text(json.dumps(brief, indent=1, ensure_ascii=False))
print(f"pictures: {got}/{total}")
