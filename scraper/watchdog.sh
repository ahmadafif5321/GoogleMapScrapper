#!/usr/bin/env bash
# Scrape watchdog — self-kills STUCK scrape containers.
#
# A healthy scrape keeps writing to its batch_*.json and exits ~30 min after the
# last new data (-exit-on-inactivity 30m). A STUCK one keeps running but its
# output file stops growing. This watchdog stops any container whose output has
# been idle past the inactivity limit + buffer, or that has produced no output
# for too long. It NEVER kills a productive scrape (file still growing).
#
# Run via the systemd timer (every ~10 min) or: ./scraper/watchdog.sh

cd "$(dirname "$0")/.." || exit 1
MAX_IDLE_MIN=40      # output file untouched this long -> stuck (limit is 30m)
MAX_NOOUT_MIN=45     # running this long with no output file -> stuck
now=$(date +%s)
LOG="storage/watchdog.log"
mkdir -p storage

log(){ echo "[$(date '+%F %T')] $*" >> "$LOG"; }

for c in $(docker ps -q --filter ancestor=gosom/google-maps-scraper:latest 2>/dev/null); do
  name=$(docker inspect "$c" --format '{{.Name}}' 2>/dev/null | sed 's#^/##')
  batch=$(docker inspect "$c" --format '{{range .Args}}{{.}} {{end}}' 2>/dev/null | grep -oE 'batch_[0-9]+\.json' | head -1)
  f="data/raw/${batch}"
  if [ -n "$batch" ] && [ -f "$f" ]; then
    idle_min=$(( (now - $(stat -c %Y "$f")) / 60 ))
    if [ "$idle_min" -gt "$MAX_IDLE_MIN" ]; then
      log "stopping $name — output ${batch} idle ${idle_min}m (>$MAX_IDLE_MIN)"
      docker stop -t 10 "$c" >/dev/null 2>&1
    fi
  else
    started=$(docker inspect "$c" --format '{{.State.StartedAt}}' 2>/dev/null)
    [ -z "$started" ] && continue
    age_min=$(( (now - $(date -d "$started" +%s 2>/dev/null || echo "$now")) / 60 ))
    if [ "$age_min" -gt "$MAX_NOOUT_MIN" ]; then
      log "stopping $name — no output, age ${age_min}m (>$MAX_NOOUT_MIN)"
      docker stop -t 10 "$c" >/dev/null 2>&1
    fi
  fi
done
