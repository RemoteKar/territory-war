# -*- coding: utf-8 -*-
"""Carries the server's battle records into the site and pushes them.

Meant to be run once the server has stopped, from the machine that already holds the
GitHub credentials - which is why it is here rather than inside the plugin. A token
living on the game server would be a second place to lose one, and the plugin does not
need it: it writes JSON to disk and this picks the files up.

    python tools/publish_battles.py            # copy, rebuild, commit, push
    python tools/publish_battles.py --dry-run  # copy and rebuild only

Records already carried over are left alone, so running it twice is not a second copy.
"""
import argparse
import glob
import io
import json
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SOURCE = os.path.join(REPO, "..", "TerritoryWar", "plugins", "TerritoryWar", "battles")
STORE = os.path.join(REPO, "data", "battles")


def run(*args, **kw):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=SOURCE, help="the plugin's battles folder")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    os.makedirs(STORE, exist_ok=True)
    if not os.path.isdir(a.source):
        print("아직 전투 기록이 없습니다: %s" % a.source)
        return 0

    brought = 0
    for src in sorted(glob.glob(os.path.join(a.source, "*.json"))):
        dst = os.path.join(STORE, os.path.basename(src))
        if os.path.exists(dst):
            continue
        # Parsed before it is kept. A half-written file - the server killed mid-flush -
        # would otherwise break every later build, and one bad record is not worth that.
        try:
            json.load(io.open(src, encoding="utf-8"))
        except ValueError as e:
            print("건너뜀 (깨진 JSON): %s - %s" % (os.path.basename(src), e))
            continue
        shutil.copy(src, dst)
        brought += 1

    total = len(glob.glob(os.path.join(STORE, "*.json")))
    print("새 기록 %d건, 누적 %d건" % (brought, total))
    if brought == 0:
        return 0

    build = subprocess.run(["python", "build.py"], cwd=REPO, capture_output=True, text=True)
    print(build.stdout.strip() or build.stderr.strip())
    if build.returncode != 0:
        return build.returncode
    if a.dry_run:
        return 0

    run("git", "add", "-A")
    msg = "전투 기록 %d건" % brought
    c = run("git", "commit", "-q", "-m", msg)
    if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr):
        print(c.stdout, c.stderr)
        return c.returncode
    p = run("git", "push", "-q", "origin", "main")
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        return p.returncode
    print("올렸습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
