#!/usr/bin/env python3
"""Extract the inner UploadedFiles zip(s) from the Garmin account export zip
into fit-cache, so parse_garmin_fit.py can walk loose .fit files.
Re-runnable: skips files already present.

No path is hardcoded. The health data root resolves from, in order:
  1. --health-dir
  2. $HEALTH_DIR, if YOU export it — Hermes injects `metadata.hermes.config` values into the
     skill message, not into the environment, so nothing sets this for you. An agent should
     pass the resolved `health.health_dir` via --health-dir.
Pass --export / --cache to override either path directly.
"""
import argparse
import io
import os
import sys
import zipfile
from pathlib import Path


def _resolve(value: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(value)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--health-dir", default=os.environ.get("HEALTH_DIR", ""),
                    help="health data root (default: $HEALTH_DIR)")
    ap.add_argument("--export", help="path to garmin_connect_export.zip")
    ap.add_argument("--cache", help="output dir for loose .fit files")
    args = ap.parse_args()

    if not args.health_dir and not (args.export and args.cache):
        ap.error("set --health-dir (or $HEALTH_DIR), or pass both --export and --cache")

    root = _resolve(args.health_dir) if args.health_dir else None
    zip_path = _resolve(args.export) if args.export else \
        root / "garmin-exports" / "garmin_connect_export.zip"
    cache = _resolve(args.cache) if args.cache else \
        root / "garmin-exports" / "fit-cache"

    if not zip_path.is_file():
        print(f"ERROR: export zip not found: {zip_path}", file=sys.stderr)
        return 1

    cache.mkdir(parents=True, exist_ok=True)
    outer = zipfile.ZipFile(zip_path)
    inner_names = [n for n in outer.namelist()
                   if "Uploaded" in n and n.endswith(".zip")]
    if not inner_names:
        print("ERROR: no UploadedFiles zip found", file=sys.stderr)
        return 1

    total_new = 0
    for inner_name in inner_names:
        inner = zipfile.ZipFile(io.BytesIO(outer.read(inner_name)))
        for info in inner.infolist():
            if not info.filename.endswith(".fit"):
                continue
            out = cache / info.filename.rsplit("/", 1)[-1]
            if out.exists():
                continue
            with inner.open(info) as src, open(out, "wb") as dst:
                dst.write(src.read())
            total_new += 1
    print(f"extracted {total_new} new .fit files into {cache}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
