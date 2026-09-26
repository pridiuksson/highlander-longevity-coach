#!/usr/bin/env python3
"""
Apple Health Export Streaming Parser.

Extracts resting heart rate, HRV (SDNN), VO2 max, sleep architecture,
and workouts from an Apple Health export.xml (or .zip) directly into
a normalized SQLite database.

Memory-safe: uses streaming iterparse with proper ancestor-safe element clearing,
enabling parsing of 1GB to 20GB+ XML exports under 100MB RAM.
"""

import argparse
import os
import re
import sqlite3
import sys
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET


SCHEMA = """
CREATE TABLE IF NOT EXISTS resting_hr (
    date TEXT PRIMARY KEY,
    value REAL
);

CREATE TABLE IF NOT EXISTS hrv_sdnn (
    ts TEXT PRIMARY KEY,
    value REAL
);
CREATE INDEX IF NOT EXISTS idx_hrv_ts ON hrv_sdnn(ts);

CREATE TABLE IF NOT EXISTS sleep_night (
    night TEXT PRIMARY KEY,
    total_h REAL,
    deep_h REAL,
    rem_h REAL,
    core_h REAL
);

CREATE TABLE IF NOT EXISTS vo2_max (
    ts TEXT PRIMARY KEY,
    value REAL
);

CREATE TABLE IF NOT EXISTS workouts (
    type TEXT,
    start TEXT,
    end TEXT,
    duration_min REAL,
    distance_km REAL,
    energy_kcal REAL,
    avg_hr REAL,
    max_hr REAL,
    PRIMARY KEY (type, start)
);
CREATE INDEX IF NOT EXISTS idx_workouts_start ON workouts(start);

CREATE TABLE IF NOT EXISTS import_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def init_db(db_path, rebuild=False):
    """Initialize or recreate the SQLite database schema."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    if rebuild:
        tables = ['resting_hr', 'hrv_sdnn', 'sleep_night', 'vo2_max', 'workouts', 'import_meta']
        for t in tables:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def get_xml_stream(source_path):
    """
    Open an XML stream from either a raw .xml file or a .zip archive
    containing export.xml.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Export source not found: {source_path}")

    if zipfile.is_zipfile(source_path):
        zf = zipfile.ZipFile(source_path, 'r')
        xml_names = [n for n in zf.namelist() if n.endswith('export.xml')]
        if not xml_names:
            raise ValueError(f"No export.xml found in zip archive: {source_path}")
        return zf.open(xml_names[0]), zf
    else:
        return open(source_path, 'rb'), None


def normalize_duration(duration_str, unit_str):
    """Normalize duration to minutes."""
    try:
        val = float(duration_str)
    except (ValueError, TypeError):
        return None
    unit = (unit_str or 'min').lower()
    if unit in ('min', 'm', 'minute', 'minutes'):
        return round(val, 2)
    elif unit in ('s', 'sec', 'second', 'seconds'):
        return round(val / 60.0, 2)
    elif unit in ('hr', 'h', 'hour', 'hours'):
        return round(val * 60.0, 2)
    return round(val, 2)


def normalize_distance(dist_str, unit_str):
    """Normalize distance to kilometers."""
    try:
        val = float(dist_str)
    except (ValueError, TypeError):
        return None
    unit = (unit_str or 'km').lower()
    if unit in ('km', 'kilometer', 'kilometers'):
        return round(val, 3)
    elif unit in ('m', 'meter', 'meters'):
        return round(val / 1000.0, 3)
    elif unit in ('mi', 'mile', 'miles'):
        return round(val * 1.60934, 3)
    elif unit in ('yd', 'yard', 'yards'):
        return round(val * 0.0009144, 3)
    return round(val, 3)


def normalize_energy(energy_str, unit_str):
    """Normalize energy to kilocalories (kcal)."""
    try:
        val = float(energy_str)
    except (ValueError, TypeError):
        return None
    unit = (unit_str or 'kcal').lower()
    if unit in ('kj', 'kilojoule', 'kilojoules'):
        return round(val / 4.184, 1)
    elif unit in ('cal', 'calorie', 'calories'):
        return round(val / 1000.0, 1)
    return round(val, 1)


def parse_apple_health(source_path, db_path, source_filter=None, rebuild=False, batch_size=5000):
    """
    Parse Apple Health export into SQLite with memory-safe streaming iterparse.
    """
    conn = init_db(db_path, rebuild=rebuild)
    stream, archive = get_xml_stream(source_path)

    t0 = time.time()

    # Staging buffers
    resting_hr_batch = {}      # date -> value
    hrv_batch = []             # (ts, value)
    vo2_batch = {}             # ts -> value
    workout_batch = []         # (type, start, end, dur, dist, kcal, avg_hr, max_hr)

    # Sleep aggregation buffer: night_key -> {'total': s, 'deep': s, 'rem': s, 'core': s}
    sleep_nights = defaultdict(lambda: {'total': 0.0, 'deep': 0.0, 'rem': 0.0, 'core': 0.0})

    def flush_batches():
        staged = len(resting_hr_batch) + len(hrv_batch) + len(vo2_batch) + len(workout_batch)
        if staged == 0:
            return

        if resting_hr_batch:
            conn.executemany("INSERT OR REPLACE INTO resting_hr VALUES (?,?)", resting_hr_batch.items())
            resting_hr_batch.clear()
        if hrv_batch:
            conn.executemany("INSERT OR REPLACE INTO hrv_sdnn VALUES (?,?)", hrv_batch)
            hrv_batch.clear()
        if vo2_batch:
            conn.executemany("INSERT OR REPLACE INTO vo2_max VALUES (?,?)", vo2_batch.items())
            vo2_batch.clear()
        if workout_batch:
            conn.executemany("INSERT OR REPLACE INTO workouts VALUES (?,?,?,?,?,?,?,?)", workout_batch)
            workout_batch.clear()
        conn.commit()

    root = None

    try:
        context = ET.iterparse(stream, events=('start', 'end'))
        for event, elem in context:
            if root is None and event == 'start':
                root = elem
                continue

            if event != 'end':
                continue

            tag = elem.tag

            if tag == 'Record':
                attr = elem.attrib
                rec_type = attr.get('type', '')
                source = attr.get('sourceName', '')

                # Filter source if specified
                if source_filter and source_filter.lower() not in source.lower():
                    elem.clear()
                    if root is not None:
                        root.clear()
                    continue

                val_str = attr.get('value')
                start_str = attr.get('startDate')

                if rec_type == 'HKQuantityTypeIdentifierRestingHeartRate':
                    if start_str and val_str:
                        date_key = start_str[:10]
                        try:
                            resting_hr_batch[date_key] = float(val_str)
                        except ValueError:
                            pass

                elif rec_type == 'HKQuantityTypeIdentifierHeartRateVariabilitySDNN':
                    if start_str and val_str:
                        try:
                            hrv_batch.append((start_str, float(val_str)))
                        except ValueError:
                            pass

                elif rec_type == 'HKQuantityTypeIdentifierVO2Max':
                    if start_str and val_str:
                        try:
                            vo2_batch[start_str] = float(val_str)
                        except ValueError:
                            pass

                elif rec_type == 'HKCategoryTypeIdentifierSleepAnalysis':
                    end_str = attr.get('endDate')
                    cat_val = val_str or ''

                    # Exclude InBed and Awake; count asleep records
                    if start_str and end_str and 'Asleep' in cat_val and 'Awake' not in cat_val:
                        try:
                            s_dt = datetime.fromisoformat(start_str)
                            e_dt = datetime.fromisoformat(end_str)
                            dur_h = (e_dt - s_dt).total_seconds() / 3600.0

                            # 18:00 night key: (start - 18h).date()
                            night_key = (s_dt - timedelta(hours=18)).date().isoformat()

                            # Categorize stage
                            if 'Deep' in cat_val:
                                sleep_nights[night_key]['deep'] += dur_h
                                sleep_nights[night_key]['total'] += dur_h
                            elif 'REM' in cat_val:
                                sleep_nights[night_key]['rem'] += dur_h
                                sleep_nights[night_key]['total'] += dur_h
                            elif 'Core' in cat_val:
                                sleep_nights[night_key]['core'] += dur_h
                                sleep_nights[night_key]['total'] += dur_h
                            else:
                                # Asleep or AsleepUnspecified
                                sleep_nights[night_key]['total'] += dur_h

                        except (ValueError, TypeError):
                            pass

                if len(resting_hr_batch) + len(hrv_batch) + len(vo2_batch) >= batch_size:
                    flush_batches()

                elem.clear()
                if root is not None:
                    root.clear()

            elif tag == 'Workout':
                attr = elem.attrib
                atype = attr.get('workoutActivityType', '').replace('HKWorkoutActivityType', '')
                dur_raw = attr.get('duration')
                dunit = attr.get('durationUnit', 'min')
                start_str = attr.get('startDate')
                end_str = attr.get('endDate')

                dur_min = normalize_duration(dur_raw, dunit)
                distance_km = None
                energy_kcal = None
                avg_hr = None
                max_hr = None

                # Fallback to direct attributes if present (e.g. legacy iOS or third-party exports)
                if attr.get('totalDistance'):
                    distance_km = normalize_distance(attr.get('totalDistance'), attr.get('totalDistanceUnit'))
                if attr.get('totalEnergyBurned'):
                    energy_kcal = normalize_energy(attr.get('totalEnergyBurned'), attr.get('totalEnergyBurnedUnit'))

                # Inspect nested WorkoutStatistics (overrides attributes with child totals)
                for stat in elem.findall('WorkoutStatistics'):
                    s_type = stat.attrib.get('type', '')
                    s_sum = stat.attrib.get('sum')
                    s_unit = stat.attrib.get('unit', '')
                    s_avg = stat.attrib.get('average')
                    s_max = stat.attrib.get('maximum')

                    if 'ActiveEnergyBurned' in s_type and s_sum:
                        parsed_energy = normalize_energy(s_sum, s_unit)
                        if parsed_energy is not None:
                            energy_kcal = parsed_energy
                    elif 'Distance' in s_type and s_sum:
                        parsed_dist = normalize_distance(s_sum, s_unit)
                        if parsed_dist is not None:
                            distance_km = parsed_dist
                    elif 'HeartRate' in s_type:
                        if s_avg:
                            try:
                                avg_hr = round(float(s_avg), 1)
                            except ValueError:
                                pass
                        if s_max:
                            try:
                                max_hr = round(float(s_max), 1)
                            except ValueError:
                                pass

                workout_batch.append((atype, start_str, end_str, dur_min, distance_km, energy_kcal, avg_hr, max_hr))

                if len(workout_batch) >= batch_size:
                    flush_batches()

                elem.clear()
                if root is not None:
                    root.clear()

            elif tag in ('Correlation', 'ExportDate', 'Me'):
                # Top-level non-data tags can be safely cleared along with root
                elem.clear()
                if root is not None:
                    root.clear()

            else:
                # Child tags (WorkoutStatistics, MetadataEntry, etc.) must not be cleared here;
                # they are read by their parent container (e.g. Workout) and cleared when the parent ends.
                pass

    finally:
        # Flush any remaining records safely inside finally
        flush_batches()

        if sleep_nights:
            sleep_rows = [
                (
                    k,
                    round(v['total'], 2),
                    round(v['deep'], 2),
                    round(v['rem'], 2),
                    round(v['core'], 2),
                )
                for k, v in sleep_nights.items()
            ]
            conn.executemany("INSERT OR REPLACE INTO sleep_night VALUES (?,?,?,?,?)", sleep_rows)
            conn.commit()

        # Query exact row counts directly from database
        cursor = conn.cursor()
        counts = {}
        for t in ('resting_hr', 'hrv_sdnn', 'sleep_night', 'vo2_max', 'workouts'):
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = cursor.fetchone()[0]

        # Write import metadata
        meta = [
            ('imported_at', datetime.now().isoformat()),
            ('source_file', os.path.basename(source_path)),
            ('resting_hr_rows', str(counts['resting_hr'])),
            ('hrv_sdnn_rows', str(counts['hrv_sdnn'])),
            ('sleep_night_rows', str(counts['sleep_night'])),
            ('vo2_max_rows', str(counts['vo2_max'])),
            ('workouts_rows', str(counts['workouts'])),
        ]
        conn.executemany("INSERT OR REPLACE INTO import_meta VALUES (?,?)", meta)
        conn.commit()

        stream.close()
        if archive:
            archive.close()
        conn.close()

    elapsed = time.time() - t0
    print(f"=== Apple Health Import Complete in {elapsed:.2f}s ===")
    print(f"  Resting HR : {counts['resting_hr']} rows")
    print(f"  HRV (SDNN) : {counts['hrv_sdnn']} rows")
    print(f"  Sleep      : {counts['sleep_night']} nights")
    print(f"  VO2 max    : {counts['vo2_max']} rows")
    print(f"  Workouts   : {counts['workouts']} rows")
    print(f"  Database   : {db_path}")

    return counts


def main():
    parser = argparse.ArgumentParser(description="Memory-safe streaming parser for Apple Health export.xml")
    parser.add_argument("--export", "-e", required=True, help="Path to export.xml or export .zip archive")
    parser.add_argument("--db", "-d", required=True, help="Target SQLite database path")
    parser.add_argument("--source-filter", "-s", default=None, help="Filter records by sourceName substring")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild database from scratch")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size for SQL commits")

    args = parser.parse_args()
    parse_apple_health(
        source_path=args.export,
        db_path=args.db,
        source_filter=args.source_filter,
        rebuild=args.rebuild,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
