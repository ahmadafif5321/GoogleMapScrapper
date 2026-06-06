# Collector Operations — two-lane scraping

## Lanes
- **Lane 1 (priority):** a paid/on-demand customer capture. The Megu app calls
  `scraper.scrape_coord.priority_scrape()`, which raises a flag + takes the
  scrape lock. The collector finishes its current batch then yields, so the
  paying customer is collected and their report delivered first. Served captures
  are counted in `.priority_served` (shown in the admin dashboard).
- **Lane 2 (continuous):** `run_continuous_collector.sh` cycles every query in
  `scraper/queries_all.txt` (refreshed every 12h) and auto-yields to Lane 1.

## Run it manually (dev)
```bash
cd ~/GoogleMapScrapper
nohup ./run_continuous_collector.sh >> storage/collector.log 2>&1 &
tail -f storage/collector.log
pkill -f "main.py collect"        # stop
```

## Run it as a systemd service (production — survives reboots)
Requires sudo (not done automatically).
```bash
sudo cp ~/GoogleMapScrapper/megu-collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now megu-collector
systemctl status megu-collector
journalctl -u megu-collector -f
```
The unit sets `Restart=always`, so the collector self-heals on crash/reboot.

## Health
- Admin dashboard → "Data collection" panel: queries done this cycle, places &
  reviews collected, **priority captures served**, last activity, running state.
- API: `GET /api/admin/scraper` (admin token).

## Safety
- Only ONE collector should run at a time (the script + systemd both guard via
  the OS lock; do not start two).
- A crashed priority capture's flag is auto-cleared once its PID is dead, so the
  collector never yields forever.

## Watchdog (auto-kills stuck containers)

`scraper/watchdog.sh` runs every 10 min via the `megu-watchdog.timer` user
service. It stops any scrape container whose output file has been idle past the
30-min inactivity limit (i.e. hung), without harming a productive scrape. Manual:
```bash
./scraper/watchdog.sh && tail storage/watchdog.log
systemctl --user list-timers megu-watchdog.timer
```
