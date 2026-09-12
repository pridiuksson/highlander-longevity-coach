#!/usr/bin/env python3
"""Extract the inner UploadedFiles zip(s) from the Garmin account export zip
into fit-cache, so parse_garmin_fit.py can walk loose .fit files.
Re-runnable: skips files already present."""
import io
import sys
from pathlib import Path

import zipfile

ZIP = '$HOME/highlander-longevity-coach/<YOUR_HEALTH_DIR>/garmin-exports/garmin_connect_export.zip'
CACHE = Path('$HOME/highlander-longevity-coach/<YOUR_HEALTH_DIR>/garmin-exports/fit-cache')


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    outer = zipfile.ZipFile(ZIP)
    inner_names = [n for n in outer.namelist()
                   if 'Uploaded' in n and n.endswith('.zip')]
    if not inner_names:
        print('ERROR: no UploadedFiles zip found'); return 1
    total_new = 0
    for inner_name in inner_names:
        inner = zipfile.ZipFile(io.BytesIO(outer.read(inner_name)))
        for info in inner.infolist():
            if not info.filename.endswith('.fit'):
                continue
            out = CACHE / info.filename.rsplit('/', 1)[-1]
            if out.exists():
                continue
            with inner.open(info) as src, open(out, 'wb') as dst:
                dst.write(src.read())
            total_new += 1
    print(f'extracted {total_new} new .fit files into {CACHE}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
