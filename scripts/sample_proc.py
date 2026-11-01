"""Sample CPU% and RSS of a process tree once per second until killed. Usage: PID OUT.csv"""

from __future__ import annotations

import sys
import time

import psutil

root = psutil.Process(int(sys.argv[1]))
with open(sys.argv[2], "w", encoding="utf-8") as fh:
    fh.write("t,cpu_percent,rss_mb\n")
    root.cpu_percent(None)
    t0 = time.time()
    while True:
        time.sleep(1)
        try:
            procs = [root, *root.children(recursive=True)]
            cpu = sum(p.cpu_percent(None) for p in procs)
            rss = sum(p.memory_info().rss for p in procs) / 1e6
        except psutil.Error:
            break
        fh.write(f"{time.time() - t0:.0f},{cpu:.0f},{rss:.0f}\n")
        fh.flush()
