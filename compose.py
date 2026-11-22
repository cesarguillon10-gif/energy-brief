"""Turn brief.json + articles.json into the web page, and rebuild the archive.

Usage: python3 -I compose.py <day-folder> <docs-folder>
Writes docs/<date>.html, docs/index.html (= latest) and docs/archive.html.
"""
import html, json, re, sys, urllib.parse
from datetime import date
from pathlib import Path

day_dir, docs = Path(sys.argv[1]), Path(sys.argv[2])
docs.mkdir(parents=True, exist_ok=True)
D = date.fromisoformat(day_dir.name)
brief = json.loads((day_dir / "brief.json").read_text())
arts = {a["id"]: a for a in json.loads((day_dir / "articles.json").read_text())}
def e(s):
    return html.escape(noemo(s))


ICON = {
 "flex": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
 "markets": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
 "devices": '<path d="M5 17h14M6 17l1.5-6h9L18 17M7 17v2M17 17v2"/><circle cx="8.5" cy="14" r=".6"/><circle cx="15.5" cy="14" r=".6"/>',
 "players": '<path d="M4 21V5l8-3 8 3v16M9 21v-5h6v5M8 8h.01M12 8h.01M16 8h.01M8 12h.01M12 12h.01M16 12h.01"/>',
 "deals": '<path d="M3 17l6-6 4 4 8-8M14 7h7v7"/>',
 "top": '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/>',
 "learn": '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 19V5M8 7h7"/>',
 "interview": '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
 "bolt": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
 "brief": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
 "check": '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9"/>',
 "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
}


def svg(name, size=18):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON[name]}</svg>')


EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\uFE0F\u200D\u2B50\u2B06\u2194-\u21AA]")


def noemo(t):
    return re.sub(r"\s{2,}", " ", EMOJI.sub("", str(t or ""))).strip()

SECTIONS = {
    "flex":    ("flex", "Flexibility & grid", "Markets, rules and grid changes", "#6E9BFF"),
    "markets": ("markets", "New markets", "Countries Axle could enter", "#2DD4BF"),
    "devices": ("devices", "Home devices", "EVs, heat pumps, home batteries", "#FBBF24"),
    "players": ("players", "Axle & competitors", "Who is doing what", "#A78BFA"),
    "deals":   ("deals", "Deals & money", "Funding, M&A and new startups", "#4ADE80"),
}


def sechead(icon, name, desc, colour):
    return (f'<div class="sechead" style="--sc:{colour}"><span class="sicon">{svg(icon)}</span>'
            f'<div><h2>{name}</h2><p>{desc}</p></div></div>')



def link_url(l):
    """Turn the writer's link object into a URL that always works (never a model-written URL)."""
    if not l:
        return "", ""
    k, q = l.get("kind"), (l.get("query") or "").strip()
    if k == "article" and l.get("id") in arts:
        a = arts[l["id"]]
        return a["link"], f"Open article on {a['source']}"
    if k == "linkedin" and q:
        return "https://www.linkedin.com/search/results/companies/?" + urllib.parse.urlencode({"keywords": q}), f"Find {q} on LinkedIn"
    if k == "wikipedia" and q:
        return "https://en.wikipedia.org/wiki/Special:Search?" + urllib.parse.urlencode({"search": q, "go": "Go"}), f"Read: {q}"
    if q:
        return "https://www.google.com/search?" + urllib.parse.urlencode({"q": q}), f"Search: {q}"
    return "", ""


def btn(l):
    url, label = link_url(l)
    if not url:
        return ""
    return f'<a class="btn" href="{html.escape(url)}" target="_blank" rel="noopener">{e(label)} <span>↗</span></a>'


def nice_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%b}"


def pic(s, cls):
    if not s.get("img"):
        return ""
    cap = f'<span class="credit">{e(s["credit"])}</span>' if s.get("credit") else ""
    return f'<figure class="{cls}"><img src="{e(s["img"])}" alt="" loading="lazy">{cap}</figure>'


def src(a, s=None):
    lock = ' <span class="lock">🔒 Subscriber only</span>' if s and s.get("paywall") else ""
    return (f'<a class="src" href="{e(a["link"])}" target="_blank" rel="noopener">'
            f'{e(a["source"])} · {nice_date(a["date"])} ↗{lock}</a>')


def why(text):
    return f'<p class="so"><b>→</b>{e(text)}</p>'


def bullets(items):
    return "<ul>" + "".join(f"<li>{e(b)}</li>" for b in items) + "</ul>"


def meta(s, a, num=None):
    n = f'<span class="n">{num}</span>' if num else ""
    lock = f' <span class="lock">{svg("lock", 11)} Paywall</span>' if s.get("paywall") else ""
    return (f'<div class="kicker">{n}<span>{e(s["country"])}</span><span class="dot">·</span>'
            f'<a href="{e(a["link"])}" target="_blank" rel="noopener">{e(a["source"])} ↗</a>{lock}</div>')


def more(s, a):
    return (f'<details><summary>Details</summary>{bullets(s["bullets"])}'
            f'<a class="read" href="{e(a["link"])}" target="_blank" rel="noopener">Read the full article on {e(a["source"])} ↗</a></details>')


def use(text, l=None):
    return f'<div class="use"><span>{svg("brief", 13)} Use it</span>{e(text)}{btn(l)}</div>' if text else ""


def hero(s, i):
    a = arts[s["id"]]
    return f"""<article id="s{s['id']}" class="hero{' first' if i == 1 else ''}">{pic(s, 'wide')}<div class="hbody">
{meta(s, a, i)}<h3><a href="{e(a['link'])}" target="_blank" rel="noopener">{e(s['headline'])}</a></h3>{why(s['why'])}{use(s.get('use'), None if (s.get('use_link') or {}).get('kind') == 'article' and (s.get('use_link') or {}).get('id') == s['id'] else s.get('use_link'))}{more(s, a)}</div></article>"""


def row(s):
    a = arts[s["id"]]
    return f"""<article id="s{s['id']}" class="card">{pic(s, 'cimg')}<div class="cbody">
{meta(s, a)}<h3><a href="{e(a['link'])}" target="_blank" rel="noopener">{e(s['headline'])}</a></h3>{why(s['why'])}{use(s.get('use'), None if (s.get('use_link') or {}).get('kind') == 'article' and (s.get('use_link') or {}).get('id') == s['id'] else s.get('use_link'))}{more(s, a)}</div></article>"""


quick = ""
shown = {s["id"] for s in brief["top3"]} | {s["id"] for sec in brief["sections"] for s in sec["stories"]}
if brief.get("takeaways"):
    quick = ('<section class="quick"><p class="qlabel">In 30 seconds</p><ol>'
             + "".join(f'<li><a href="#s{t["id"] if t["id"] in shown else "top"}"><span class="emo">{k}</span><span>{e(t["text"])}</span></a></li>'
                       for k, t in enumerate(brief["takeaways"], 1)) + "</ol></section>")

count = len(brief["top3"]) + sum(len(s["stories"]) for s in brief["sections"])
minutes = max(2, round(count * 0.5 + 1))

top = "".join(hero(s, i) for i, s in enumerate(brief["top3"], 1))
chips, blocks = ['<a href="#top">Must know</a>'], []
order = {k: i for i, k in enumerate(SECTIONS)}
for sec in sorted(brief["sections"], key=lambda s: order[s["key"]]):
    icon, name, desc, col = SECTIONS[sec["key"]]
    k = len(sec["stories"])
    chips.append(f'<a href="#{sec["key"]}">{name}</a>')
    blocks.append(f'<section class="sec" id="{sec["key"]}">' + sechead(icon, name, f"{desc} · {k} {'story' if k == 1 else 'stories'}", col)
                  + '<div class="grid">' + "".join(row(s) for s in sec["stories"]) + "</div></section>")
if brief.get("moves"):
    chips.append('<a href="#moves">Your move</a>')
chips += ['<a href="#learn">Learn</a>', '<a href="#interview">Interview</a>']
moves = ""
if brief.get("moves"):
    moves = (f'<section class="sec" id="moves">{sechead("check", "Your move today", "Small career actions, under 20 minutes each", "#4ADE80")}'
             '<ol class="moves">' + "".join(f'<li><span class="emo">{k}</span><span>{e(m["text"] if isinstance(m, dict) else m)}'
                                                     f'{btn(m.get("link")) if isinstance(m, dict) else ""}</span></li>'
                                            for k, m in enumerate(brief["moves"], 1)) + "</ol></section>")

L, I, J = brief["learn"], brief["interview"], brief.get("jargon")
learn = f"""<div class="duo">
<section class="sec" id="learn">{sechead("learn", "Learn one thing", "A key idea for the role", "#F472B6")}
<article class="panel">{pic(L, 'wide')}<h3>{e(L['title'])}</h3>{bullets(L['bullets'])}
<p class="so"><b>→</b>{e(L['so_what'])}</p>{btn(L.get('link'))}</article></section>
<section class="sec" id="interview">{sechead("interview", "Interview angle", "Be ready if Axle asks", "#FB923C")}
<article class="panel"><p class="q">“{e(I['question'])}”</p><p class="label">You could say</p>{bullets(I['answer'])}</article></section>
</div>"""

CSS = """
:root{--bg:#0A0B10;--surface:rgba(255,255,255,.035);--surface2:rgba(255,255,255,.06);--ink:#D9DBE3;--head:#FFFFFF;--soft:#8D90A0;
--line:rgba(255,255,255,.08);--accent:#6E9BFF;--accent2:#A78BFA;--accent-bg:rgba(110,155,255,.10);--fs:16px;
--hf:"Space Grotesk",Inter,sans-serif;--bf:Inter,system-ui,sans-serif;
--glow:radial-gradient(800px 420px at 90% -10%,rgba(110,155,255,.18),transparent 60%),radial-gradient(600px 400px at -10% 6%,rgba(167,139,250,.13),transparent 60%)}
:root[data-theme="light"]{--bg:#F5F6FA;--surface:#FFFFFF;--surface2:#F0F2F8;--ink:#2A2E3D;--head:#0B0D18;--soft:#666B7E;
--line:#E3E6EF;--accent:#2F5BEA;--accent2:#7C5CE0;--accent-bg:#EEF2FF;
--glow:radial-gradient(800px 420px at 90% -10%,rgba(47,91,234,.09),transparent 60%),radial-gradient(600px 400px at -10% 6%,rgba(124,92,224,.07),transparent 60%)}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:60px;background:var(--bg)}
body{margin:0;background:var(--glow),var(--bg);background-repeat:no-repeat;color:var(--ink);font-family:var(--bf);
font-size:var(--fs);line-height:1.6;-webkit-font-smoothing:antialiased;min-height:100vh;font-feature-settings:"cv11","ss01"}
.wrap{max-width:860px;margin:0 auto;padding:0 20px 70px}
header{padding:22px 0 0}
.top{display:flex;align-items:center;justify-content:space-between}
.brand{display:flex;align-items:center;gap:9px;font:600 13px var(--hf);color:var(--soft);letter-spacing:.01em}
.logo{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;font-size:13px;color:#fff;
background:linear-gradient(135deg,var(--accent),var(--accent2));box-shadow:0 4px 14px rgba(110,155,255,.3)}
.tools{display:flex;gap:6px}
.tools button{font:500 12px var(--bf);color:var(--soft);background:var(--surface);border:1px solid var(--line);border-radius:8px;
height:30px;min-width:34px;padding:0 10px;cursor:pointer}
.tools button:hover{color:var(--head)}
.eyebrow{font:600 11px var(--hf);color:var(--accent);margin:24px 0 2px;letter-spacing:.06em;text-transform:uppercase}
h1{font-family:var(--hf);font-size:2.1em;line-height:1.1;margin:0 0 6px;font-weight:700;letter-spacing:-.025em;color:var(--head)}
.sub{color:var(--soft);margin:0;font-size:.82em}
nav{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 85%,transparent);backdrop-filter:blur(14px);
display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;padding:8px 0;margin:18px 0 0;border-bottom:1px solid var(--line)}
nav::-webkit-scrollbar{display:none}
nav a{flex:none;color:var(--soft);text-decoration:none;font:500 12.5px var(--bf);padding:6px 10px;border-radius:7px}
nav a:hover{color:var(--head);background:var(--surface2)}
h2{font:600 12px var(--hf);color:var(--soft);margin:38px 0 4px;letter-spacing:.06em;text-transform:uppercase;display:flex;align-items:center;gap:10px}
h2::after{content:"";flex:1;height:1px;background:var(--line)}
figure{margin:0;position:relative;overflow:hidden;background:var(--surface2)}
figure img{display:block;width:100%;height:100%;object-fit:cover}
.credit{position:absolute;right:6px;bottom:5px;font-size:9px;color:#fff;background:rgba(0,0,0,.5);padding:0 5px;border-radius:4px}
.thumb .credit{display:none}

.hero{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:10px 10px 14px;display:flex;flex-direction:column}
.hero.first{grid-column:1/-1;display:grid;grid-template-columns:1.15fr 1fr;gap:18px;padding:10px}
.hero.first figure{grid-row:1/8;margin:0;aspect-ratio:auto;min-height:0}
.hero.first figure img{position:absolute;inset:0}
.hero.first > *:not(figure){margin-left:0;margin-right:6px}
.hero.first .kicker{margin-top:8px}
.hero > *:not(figure){margin-left:6px;margin-right:6px}
.wide{aspect-ratio:2/1;border-radius:10px;margin:0 0 12px}
.hero.first h3{font-size:1.45em}
.kicker{display:flex;align-items:center;gap:8px;font:500 11.5px var(--bf);color:var(--soft);margin:0 0 4px}
.n{width:19px;height:19px;border-radius:5px;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;
display:grid;place-items:center;font:700 11px var(--hf)}
.lock{display:inline-flex;align-items:center;gap:3px;color:var(--soft);border:1px solid var(--line);border-radius:5px;padding:0 6px;font-size:10.5px}
h3{font-family:var(--hf);font-size:1.12em;line-height:1.3;font-weight:600;margin:0 0 8px;letter-spacing:-.01em;color:var(--head)}
ul{margin:0 0 10px;padding-left:1em;font-size:.94em}li{margin:0 0 4px}li::marker{color:var(--accent)}
.why{margin:0 0 10px;padding:8px 11px;border-radius:9px;background:var(--accent-bg);font-size:.9em}
.why span{display:block;font:600 10.5px var(--hf);color:var(--accent);margin-bottom:1px;letter-spacing:.05em;text-transform:uppercase}
.src{font:500 11.5px var(--bf);color:var(--soft);text-decoration:none;margin-top:auto}
.src:hover{color:var(--accent)}
.row{display:flex;gap:16px;padding:18px 0;border-bottom:1px solid var(--line)}
.row .body{flex:1;min-width:0}.row h3{font-size:1.05em}
.thumb{flex:none;width:96px;height:96px;border-radius:10px;border:1px solid var(--line)}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:14px}.duo .sec{margin-top:46px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 16px 6px}
.panel .wide{margin:-16px -16px 14px;border-radius:14px 14px 0 0;width:auto;aspect-ratio:21/9}
.q{font:600 1.08em/1.35 var(--hf);color:var(--head);margin:0 0 10px;letter-spacing:-.01em}
.label{font:600 10.5px var(--hf);color:var(--accent);margin:0 0 4px;letter-spacing:.05em;text-transform:uppercase}
.jargon{margin:14px 0 0;padding:12px 16px;border:1px solid var(--line);border-radius:12px;font-size:.9em;background:var(--surface)}
.jargon span{display:block;font:600 10.5px var(--hf);color:var(--accent2);margin-bottom:1px;letter-spacing:.05em;text-transform:uppercase}
.quick{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 16px 4px;margin:20px 0 0;overflow:hidden}
.quick::before{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.qlabel{margin:0 0 2px;font:600 10.5px var(--hf);color:var(--accent);letter-spacing:.06em;text-transform:uppercase}
.quick ol{list-style:none;margin:0;padding:0}
.quick li{border-top:1px solid var(--line)}.quick li:first-child{border-top:0}
.quick a{display:flex;gap:12px;align-items:center;padding:9px 0;color:var(--head);text-decoration:none;font-size:.95em;font-weight:500;line-height:1.4}
.quick a:hover span:last-child{color:var(--accent)}
.emo{flex:none;width:24px;height:24px;border-radius:7px;background:var(--accent-bg);color:var(--accent);display:grid;place-items:center;font:700 12px var(--hf)}
.sec{margin-top:46px}
.sechead{display:flex;align-items:center;gap:12px;margin:0 0 14px;padding-bottom:12px;border-bottom:1px solid var(--line)}
.sicon{flex:none;width:36px;height:36px;border-radius:10px;display:grid;place-items:center;color:var(--sc);
background:color-mix(in srgb,var(--sc) 16%,transparent);border:1px solid color-mix(in srgb,var(--sc) 35%,transparent)}
.sechead h2{font:700 1.15em/1.2 var(--hf);color:var(--head);margin:0;letter-spacing:-.01em;text-transform:none;display:block}
.sechead h2::after{display:none}
.sechead p{margin:2px 0 0;font-size:.78em;color:var(--soft)}
.tops{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;
transition:border-color .15s}
.card:hover,.hero:hover{border-color:color-mix(in srgb,var(--accent) 45%,transparent)}
.cimg{aspect-ratio:12/5;border-radius:0}
.cbody{padding:14px 16px 14px;display:flex;flex-direction:column;flex:1}
.card h3{font-size:1.05em}
.grid > .card:last-child:nth-child(odd){grid-column:1/-1;flex-direction:row}
.grid > .card:last-child:nth-child(odd) .cimg{flex:0 0 38%;aspect-ratio:auto;min-height:0}
.grid > .card:last-child:nth-child(odd) .cimg img{position:absolute;inset:0}
@media (max-width:700px){.tops,.grid{grid-template-columns:1fr}.sec{margin-top:36px}
.grid > .card:last-child:nth-child(odd){flex-direction:column}.grid > .card:last-child:nth-child(odd) .cimg{flex:none;aspect-ratio:2/1;min-height:0}.grid > .card:last-child:nth-child(odd) .cimg img{position:static}}
.hbody{display:flex;flex-direction:column;flex:1}
.kicker a{color:var(--soft);text-decoration:none}.kicker a:hover{color:var(--accent)}
.kicker .dot{opacity:.5}
.so{display:flex;gap:8px;margin:0 0 6px;font-size:.92em;line-height:1.5;color:var(--ink)}
.so b{color:var(--accent);flex:none}
details{margin-top:auto;padding-top:6px}
summary{list-style:none;cursor:pointer;font:500 12px var(--bf);color:var(--soft);display:inline-flex;align-items:center;gap:4px;
padding:4px 0;user-select:none}
summary::-webkit-details-marker{display:none}
summary::after{content:"▾";font-size:10px;transition:transform .15s}
details[open] summary::after{transform:rotate(180deg)}
summary:hover{color:var(--head)}
details ul{margin:6px 0 8px}
.read{font:500 12px var(--bf);color:var(--accent);text-decoration:none}
.hero h3,.card h3{margin-bottom:6px}
.tops > .hero:last-child:nth-child(even):not(.first){grid-column:1/-1}
.tops > .hero:last-child:nth-child(even):not(.first) .wide{aspect-ratio:3/1}
.use{display:flex;flex-direction:column;margin:2px 0 6px;font-size:.9em;line-height:1.5;color:var(--ink);
padding:8px 11px;border-radius:9px;background:color-mix(in srgb,var(--accent2) 10%,transparent)}
.use span{display:inline-flex;align-items:center;gap:5px;font:600 10.5px var(--hf);color:var(--accent2);letter-spacing:.05em;text-transform:uppercase;margin-bottom:1px}
.moves{list-style:none;margin:0;padding:6px 16px;background:var(--surface);border:1px solid var(--line);border-radius:14px}
.moves li{display:flex;gap:12px;align-items:flex-start;padding:11px 0;border-top:1px solid var(--line);font-size:.95em;color:var(--head);line-height:1.45}
.moves li:first-child{border-top:0}
.moves .emo{background:color-mix(in srgb,#4ADE80 14%,transparent);color:#4ADE80}
h3 a{color:inherit;text-decoration:none;background-image:linear-gradient(currentColor,currentColor);background-size:0 1px;
background-repeat:no-repeat;background-position:0 100%;transition:background-size .2s,color .15s}
h3 a:hover{color:var(--accent);background-size:100% 1px}
.btn{display:inline-flex;align-items:center;gap:5px;margin-top:7px;padding:5px 10px;border-radius:8px;font:500 12px var(--bf);
color:var(--head);background:var(--surface2);border:1px solid var(--line);text-decoration:none;width:fit-content;max-width:100%}
.btn span{color:var(--accent)}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.moves li > span:last-child{display:flex;flex-direction:column}
.panel .btn{margin:0 0 14px}
footer{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);color:var(--soft);font:500 12px var(--bf);display:flex;justify-content:space-between}
footer a{color:var(--head);text-decoration:none}
.list a{display:flex;justify-content:space-between;padding:14px 0;border-bottom:1px solid var(--line);color:var(--head);text-decoration:none;font-size:.95em}
.list a span{color:var(--soft)}
@media (max-width:700px){.duo{grid-template-columns:1fr}.hero.first{display:flex;flex-direction:column;gap:0}.hero.first figure{aspect-ratio:16/9;min-height:0;max-height:none;width:100%;margin:0 0 12px}.hero.first figure img{position:static}
.hero.first > *:not(figure){margin-left:6px}h1{font-size:1.75em}.hero.first h3{font-size:1.25em}.thumb{width:76px;height:76px}}
"""
JS = """
<script>
(function(){var r=document.documentElement;
try{var t=localStorage.getItem('peb-theme');if(t)r.dataset.theme=t;var f=localStorage.getItem('peb-fs');if(f)r.style.setProperty('--fs',f+'px')}catch(e){}
function dark(){return r.dataset.theme!=='light'}
function label(){var b=document.getElementById('theme');if(b)b.innerHTML=dark()?'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>':'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>'}
document.addEventListener('DOMContentLoaded',function(){label();
document.getElementById('theme').onclick=function(){r.dataset.theme=dark()?'light':'dark';try{localStorage.setItem('peb-theme',r.dataset.theme)}catch(e){}label()};
document.getElementById('size').onclick=function(){var c=parseInt(getComputedStyle(r).getPropertyValue('--fs'))||16;
var n=c>=20?15:c+1;r.style.setProperty('--fs',n+'px');try{localStorage.setItem('peb-fs',n)}catch(e){}}})})();
</script>"""


def page(title, body):
    return f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Energy Brief">
<meta name="theme-color" content="#0A0B10"><link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22><rect width=%2224%22 height=%2224%22 rx=%226%22 fill=%22%236E9BFF%22/><path d=%22M13 3 5 13h6l-1 8 8-10h-6z%22 fill=%22white%22/></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>{JS}</head><body><div class="wrap">{body}</div></body></html>"""


def head(h1, sub):
    return f"""<header><div class="top"><div class="brand"><span class="logo">{svg("bolt", 15)}</span>Paul's Energy Brief</div>
<div class="tools"><button id="size" title="Text size" aria-label="Change text size">Aa</button>
<button id="theme" title="Dark or light" aria-label="Switch dark or light"></button></div></div>
<p class="eyebrow">Daily briefing · Energy flexibility</p><h1>{h1}</h1><p class="sub">{sub}</p></header>"""


body = (head(f"{D:%A} {D.day} {D:%B}", f"{count} must-know stories · {minutes} min read · for the Axle Energy job")
        + quick + f'<nav>{"".join(chips)}</nav><section class="sec" id="top">{sechead("top", "Must know", "Only what matters for you today", "#6E9BFF")}<div class="tops">{top}</div></section>'
        + moves + "".join(blocks) + learn
        + '<footer><span>Updated every morning</span><a href="archive.html">Past briefs →</a></footer>')
html_out = page(f"Paul's Energy Brief · {D.day} {D:%b}", body)
(docs / f"{D.isoformat()}.html").write_text(html_out)
(docs / "index.html").write_text(html_out)

days = sorted((p.stem for p in docs.glob("20??-??-??.html")), reverse=True)
rows = "".join(f'<a href="{d}.html">{date.fromisoformat(d):%A %-d %B}<span>→</span></a>' for d in days)
(docs / "archive.html").write_text(page("Past briefs", head("Past briefs", "Every brief, newest first.")
                                   + f'<div class="list">{rows}</div><footer><a href="index.html">← Today</a></footer>'))
print(f"page: {docs / (D.isoformat() + '.html')} ({count} stories)")
