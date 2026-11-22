"""One Claude call: pick + write today's stories as strict JSON (subscription login, no API bill).

Usage: python3 -I write.py <day-folder>   (reads articles.json, writes brief.json)
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
day = Path(sys.argv[1])
MODEL = "claude-sonnet-5-5"

link = {"type": "object", "additionalProperties": False, "required": ["kind", "id", "query"],
        "properties": {"kind": {"type": "string", "enum": ["article", "linkedin", "wikipedia", "google"]},
                       "id": {"type": "integer"}, "query": {"type": "string"}}}
story = {"type": "object", "additionalProperties": False,
         "required": ["id", "headline", "bullets", "why", "use", "use_link", "country", "wiki"],
         "properties": {"id": {"type": "integer"}, "headline": {"type": "string"},
                        "bullets": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2},
                        "why": {"type": "string"}, "use": {"type": "string"}, "use_link": link, "country": {"type": "string"}, "wiki": {"type": "string"}}}
schema = {
    "type": "object", "additionalProperties": False,
    "required": ["takeaways", "top3", "moves", "learn", "interview"],
    "properties": {
        "takeaways": {"type": "array", "minItems": 3, "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False, "required": ["emoji", "text", "id"],
            "properties": {"emoji": {"type": "string"}, "text": {"type": "string"}, "id": {"type": "integer"}}}},
        "top3": {"type": "array", "items": story, "minItems": 3, "maxItems": 5},
        "moves": {"type": "array", "minItems": 2, "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False, "required": ["text", "link"],
            "properties": {"text": {"type": "string"}, "link": link}}},
        "learn": {"type": "object", "additionalProperties": False,
                  "required": ["title", "bullets", "so_what", "topic", "wiki", "link"],
                  "properties": {"title": {"type": "string"}, "wiki": {"type": "string"}, "link": link, "so_what": {"type": "string"}, "topic": {"type": "string"},
                                 "bullets": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 4}}},
        "interview": {"type": "object", "additionalProperties": False, "required": ["question", "answer"],
                      "properties": {"question": {"type": "string"},
                                     "answer": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 3}}},
    }}

arts = json.loads((day / "articles.json").read_text())
learned_path = BASE / "data" / "learned.json"
learned = json.loads(learned_path.read_text()) if learned_path.exists() else []
lines = [f'[{a["id"]}]{" [img]" if a.get("image") else ""} {a["date"]} · {a["source"]} · {a["title"]} — {a["summary"][:280]}' for a in arts]
user = ("Already taught (do not repeat): " + (", ".join(learned[-60:]) or "nothing yet") +
        f"\n\nToday's articles ({len(arts)}):\n" + "\n".join(lines))

env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
claude = shutil.which("claude", path=env.get("PATH", "") + ":" + os.path.expanduser("~/.local/bin")) or "claude"
p = subprocess.run([claude, "-p", "--model", MODEL, "--tools", "", "--system-prompt-file", str(BASE / "rules.md"),
                    "--json-schema", json.dumps(schema), "--output-format", "json", "--no-session-persistence"],
                   input=user, capture_output=True, text=True, timeout=1200, env=env)
if p.returncode:
    sys.exit(f"claude failed rc={p.returncode}: {p.stdout[-600:]} {p.stderr[-600:]}")
d = json.loads(p.stdout)
out = d.get("structured_output")
if d.get("is_error") or not out:
    sys.exit(f"no structured output: {p.stdout[-600:]}")

# keep only stories whose id is a real collected article; drop duplicates
ids, used = {a["id"] for a in arts}, set()
def keep(s):
    if s["id"] in ids and s["id"] not in used:
        used.add(s["id"]); return True
    return False
out["top3"] = [s for s in out["top3"] if keep(s)]
out["sections"] = []          # condensed format: must-know stories only
# keep all takeaways; the page links one only if its story is shown
if not out["top3"]:
    sys.exit("no valid stories")

(day / "brief.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
learned.append(out["learn"]["topic"])
import re
used_path = BASE / "data" / "used.json"
used_list = json.loads(used_path.read_text()) if used_path.exists() else []
by_id = {a["id"]: a for a in arts}
for i in used:
    used_list += [by_id[i]["link"], re.sub(r"[^a-z0-9]", "", by_id[i]["title"].lower())[:70]]
used_path.write_text(json.dumps(used_list[-3000:], indent=0, ensure_ascii=False))
learned_path.write_text(json.dumps(learned, indent=1, ensure_ascii=False))
n = len(out["top3"]) + sum(len(s["stories"]) for s in out["sections"])
print(f"brief written: {n} stories, learn = {out['learn']['topic']}, cost ${d.get('total_cost_usd', 0):.2f} (subscription)")
