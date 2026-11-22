#!/bin/bash
# One-time: put Paul's Energy Brief online (free) and switch on the daily cloud build.
#  1. creates the PUBLIC repo <you>/energy-brief (code + news pages only, no secrets)
#  2. pushes this folder
#  3. stores your Claude subscription login as an ENCRYPTED GitHub secret (for the 5–7am build)
#  4. turns on GitHub Pages from /docs
# Reuses the GitHub token + Claude login already saved for the Cyber Intelligence Brief.
set -euo pipefail
cd "$(dirname "$0")"
SRC="$HOME/ai-cyber-briefing"
T=$(cat "$SRC/.github-token"); U=$(cat "$SRC/.github-user")
api() { curl -sS -o /dev/null -w "%{http_code}" -X "$1" -H "Authorization: Bearer $T" \
          -H "Accept: application/vnd.github+json" "https://api.github.com$2" ${3:+-d "$3"}; }

echo "1/4 create repo:      $(api POST /user/repos '{"name":"energy-brief","description":"A daily 5-minute energy flexibility briefing","private":false,"has_issues":false,"has_wiki":false}') (201 = created, 422 = already exists)"

if [ ! -d .git ]; then
  git init -q -b main
  git add -A
  git -c user.name="energy-brief-bot" -c user.email="actions@users.noreply.github.com" commit -qm "Paul's Energy Brief: first version"
  git remote add origin "https://github.com/$U/energy-brief.git"
fi
git -c http.extraheader="Authorization: Basic $(printf 'x-access-token:%s' "$T" | base64)" push -q -u origin main
echo "2/4 code pushed"

python3 - "$T" "$U" "$SRC/.claude-oauth-token" <<'EOF'
import base64, json, subprocess, sys
from nacl import encoding, public
tok, user, f = sys.argv[1], sys.argv[2], sys.argv[3]
def api(m, path, data=None):
    a = ["curl", "-sS", "-X", m, "-H", "Authorization: Bearer " + tok, "-H", "Accept: application/vnd.github+json",
         "-w", "\n%{http_code}", "https://api.github.com" + path] + (["-d", json.dumps(data)] if data else [])
    body, _, code = subprocess.run(a, capture_output=True, text=True).stdout.rpartition("\n")
    return int(code), (json.loads(body) if body.strip().startswith("{") else {})
c, key = api("GET", f"/repos/{user}/energy-brief/actions/secrets/public-key")
box = public.SealedBox(public.PublicKey(key["key"].encode(), encoding.Base64Encoder()))
enc = base64.b64encode(box.encrypt(open(f).read().strip().encode())).decode()
c, _ = api("PUT", f"/repos/{user}/energy-brief/actions/secrets/CLAUDE_CODE_OAUTH_TOKEN",
           {"encrypted_value": enc, "key_id": key["key_id"]})
print("3/4 Claude login stored as encrypted secret:", "ok" if c in (201, 204) else f"FAILED {c}")
EOF

echo "4/4 GitHub Pages:     $(api POST /repos/$U/energy-brief/pages '{"source":{"branch":"main","path":"/docs"}}') (201 = on, 409 = already on)"
echo
echo "Done. Live in ~1 minute at: https://$U.github.io/energy-brief/"
