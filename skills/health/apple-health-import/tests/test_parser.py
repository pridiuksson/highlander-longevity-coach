#!/usr/bin/env python3
"""
Unit tests for Apple Health Export Streaming Parser and Gates.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
import zipfile

# Add scripts directory to path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(TEST_DIR), "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from parse_apple_health import parse_apple_health, init_db, normalize_energy, normalize_distance
from test_apple_health_gates import run_gates


class TestAppleHealthImport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_health.db")
        self.fixture_xml = os.path.join(TEST_DIR, "test_export.xml")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_parse_xml_file(self):
        counts = parse_apple_health(
            source_path=self.fixture_xml,
            db_path=self.db_path,
            rebuild=True
        )
        self.assertEqual(counts['resting_hr'], 3)
        self.assertEqual(counts['hrv_sdnn'], 3)
        self.assertEqual(counts['vo2_max'], 2)
        self.assertEqual(counts['workouts'], 2)
        self.assertEqual(counts['sleep_night'], 2)

        # Run gates
        passed = run_gates(self.db_path)
        self.assertTrue(passed)

        # Verify specific data logic
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Check sleep night 2026-08-20:
        # Total sleep = 2.0 (core) + 1.5 (deep) + 1.5 (core) + 1.75 (rem) + 0.5 (core) = 7.25h
        c.execute("SELECT total_h, deep_h, rem_h, core_h FROM sleep_night WHERE night='2026-08-20'")
        row = c.fetchone()
        self.assertIsNotNone(row)
        total, deep, rem, core = row
        self.assertAlmostEqual(total, 7.25, places=2)
        self.assertAlmostEqual(deep, 1.5, places=2)
        self.assertAlmostEqual(rem, 1.75, places=2)
        self.assertAlmostEqual(core, 4.0, places=2)

        # Check workouts
        c.execute("SELECT type, duration_min, distance_km, energy_kcal, avg_hr, max_hr FROM workouts WHERE type='Running'")
        w_run = c.fetchone()
        self.assertIsNotNone(w_run)
        self.assertEqual(w_run[0], "Running")
        self.assertEqual(w_run[1], 45.0)
        self.assertEqual(w_run[2], 6.5)
        self.assertEqual(w_run[3], 420.0)
        self.assertEqual(w_run[4], 148.0)
        self.assertEqual(w_run[5], 172.0)

        conn.close()

    def test_idempotent_reimport_no_duplicates(self):
        # Run import twice without rebuild; counts should remain identical
        parse_apple_health(self.fixture_xml, self.db_path, rebuild=True)
        counts2 = parse_apple_health(self.fixture_xml, self.db_path, rebuild=False)
        self.assertEqual(counts2['resting_hr'], 3)
        self.assertEqual(counts2['hrv_sdnn'], 3)
        self.assertEqual(counts2['workouts'], 2)

    def test_empty_db_fails_gates(self):
        # Verify Gate G2 fails on empty database
        empty_db = os.path.join(self.temp_dir, "empty.db")
        init_db(empty_db, rebuild=True)
        passed = run_gates(empty_db)
        self.assertFalse(passed, "Empty DB must fail Gate G2")

    def test_unit_conversions(self):
        # kJ to kcal conversion
        self.assertAlmostEqual(normalize_energy("1000", "kJ"), 239.0, places=1)
        self.assertEqual(normalize_energy("500", "kcal"), 500.0)

        # Yard to km conversion
        self.assertAlmostEqual(normalize_distance("1000", "yd"), 0.914, places=3)
        self.assertEqual(normalize_distance("5.5", "km"), 5.5)

    def test_parse_zip_archive(self):
        # Create a temporary zip containing apple_health_export/export.xml
        zip_path = os.path.join(self.temp_dir, "export.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(self.fixture_xml, arcname="apple_health_export/export.xml")

        counts = parse_apple_health(
            source_path=zip_path,
            db_path=self.db_path,
            rebuild=True
        )
        self.assertEqual(counts['resting_hr'], 3)
        self.assertEqual(counts['workouts'], 2)
        self.assertTrue(run_gates(self.db_path))


if __name__ == "__main__":
    unittest.main()
