"""
Cross-process scrape coordinator.

Shared by the background collector AND Megu ReviewScore's on-demand capture
(separate processes/venvs) so they never run the Google scraper at the same
time, and so LIVE customer captures take PRIORITY over the bulk collector.

Mechanism (file-based, same paths for both processes):
  - PRIORITY flag: an on-demand capture creates it to ask the collector to
    yield. The collector will not start a new batch while it exists.
  - LOCK file (fcntl exclusive): whoever holds it is scraping; the other
    blocks. Guarantees the two never run docker simultaneously.

On-demand side calls priority_scrape(fn). Collector calls
wait_if_yield() before each batch and collector_scrape(fn) around its run.
"""
from __future__ import annotations

import fcntl
import os
import time
from pathlib import Path

COORD_DIR = Path(__file__).resolve().parent
PRIORITY_FLAG = COORD_DIR / ".ondemand_priority"
LOCK_FILE = COORD_DIR / ".scrape.lock"


def _open_lock():
    LOCK_FILE.touch(exist_ok=True)
    return open(LOCK_FILE, "w")


def request_priority():
    """On-demand: ask the collector to yield."""
    try:
        PRIORITY_FLAG.write_text(str(os.getpid()))
    except OSError:
        pass


def release_priority():
    try:
        PRIORITY_FLAG.unlink(missing_ok=True)
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
    except PermissionError:
        return True


def _clear_if_stale() -> None:
    """Remove a priority flag whose owning process has died — otherwise a
    crashed capture would make the collector yield forever."""
    if not PRIORITY_FLAG.exists():
        return
    try:
        pid = int(PRIORITY_FLAG.read_text().strip() or "0")
    except (ValueError, OSError):
        pid = 0
    if pid <= 0 or not _pid_alive(pid):
        try:
            PRIORITY_FLAG.unlink(missing_ok=True)
        except OSError:
            pass


def priority_pending() -> bool:
    _clear_if_stale()
    return PRIORITY_FLAG.exists()


def wait_if_yield(poll: float = 3.0, log=print):
    """Collector: block here while a live capture wants the scraper."""
    waited = False
    while priority_pending():            # priority_pending() clears stale flags
        if not waited and log:
            log("[coord] yielding to a live customer capture…")
        waited = True
        time.sleep(poll)
    if waited and log:
        log("[coord] live capture done, resuming collection.")


def priority_scrape(fn, *args, **kwargs):
    """
    On-demand: run `fn` holding the exclusive scrape lock, after signalling
    priority so the collector won't grab a new batch. Returns fn's result.
    """
    request_priority()
    lock = _open_lock()
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)   # waits for collector's current batch
        return fn(*args, **kwargs)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        release_priority()


def collector_scrape(fn, *args, **kwargs):
    """Collector: run a batch holding the exclusive scrape lock."""
    lock = _open_lock()
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return fn(*args, **kwargs)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
