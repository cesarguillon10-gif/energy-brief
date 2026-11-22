#!/bin/bash
# Paul's Energy Brief: collect news (free) -> one Claude call (subscription) -> web page in docs/.
# Runs on GitHub Actions every morning (or locally: ./generate.sh [force]).
set -u
BASE="${GITHUB_WORKSPACE:-$(cd "$(dirname "$0")" && pwd)}"
cd "$BASE"
export TZ=Europe/London
TODAY=$(date +%F)
[ -z "${GITHUB_ACTIONS:-}" ] && export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
if [ -f "docs/$TODAY.html" ] && [ "${1:-}" != "force" ]; then echo "already built $TODAY"; exit 0; fi
mkdir -p "data/$TODAY"
HOURS=36; [ "$(date +%u)" = 1 ] && HOURS=72        # Monday covers the weekend
python3 -I collect.py "data/$TODAY/articles.json" "$HOURS" | tail -3
for attempt in 1 2; do
  python3 -I write.py "data/$TODAY" && python3 -I links.py "data/$TODAY" && { python3 -I images.py "data/$TODAY" docs || true; } && python3 -I compose.py "data/$TODAY" docs && exit 0
  echo "attempt $attempt failed"; sleep 20
done
exit 1
