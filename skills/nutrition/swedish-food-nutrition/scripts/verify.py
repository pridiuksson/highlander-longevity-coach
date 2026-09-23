#!/usr/bin/env python3
"""
Smoke test for the Swedish grocery APIs.

Runs the minimum checks to confirm the API tier is healthy:
1. Hemköp search returns real products with prices
2. Hemköp product detail returns nutrition data
3. Willys search returns real products (shared Axfood backend)
4. ICA recipe page returns ingredients via JSON-LD

Usage:
    python verify.py           # all checks
    python verify.py --quiet   # exit code only (0=pass, 1=fail)
"""

import json
import sys
import os

# Add scripts dir to path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from axfood import search, get_product
from ica_recipe import get_recipe


def run_checks(quiet=False):
    results = []

    # Check 1: Hemköp search
    try:
        r = search("arborioris", "hemkop", size=1)
        ok = len(r) > 0 and r[0].get("price") is not None
        results.append(("hemkop_search", ok, f"{r[0]['name']} — {r[0]['price']} kr" if ok else "No results"))
    except Exception as e:
        results.append(("hemkop_search", False, str(e)))

    # Check 2: Hemköp product detail + nutrition
    try:
        r = search("arborioris", "hemkop", size=1)
        if r:
            p = get_product(r[0]["code"], "hemkop")
            ok = p.get("nutrition_available", False)
            results.append(("hemkop_nutrition", ok, f"nutrition fields: {list(p.get('nutrition', {}).keys())}" if ok else "No nutrition"))
        else:
            results.append(("hemkop_nutrition", False, "No search results to test"))
    except Exception as e:
        results.append(("hemkop_nutrition", False, str(e)))

    # Check 3: Willys search
    try:
        r = search("arborioris", "willys", size=1)
        ok = len(r) > 0 and r[0].get("price") is not None
        results.append(("willys_search", ok, f"{r[0]['name']} — {r[0]['price']} kr" if ok else "No results"))
    except Exception as e:
        results.append(("willys_search", False, str(e)))

    # Check 4: ICA recipe
    try:
        recipe = get_recipe("https://www.ica.se/recept/svamprisotto-1205/")
        ok = len(recipe.get("ingredients", [])) > 0
        results.append(("ica_recipe", ok, f"{len(recipe['ingredients'])} ingredients found" if ok else "No ingredients"))
    except Exception as e:
        results.append(("ica_recipe", False, str(e)))

    # Report
    if not quiet:
        print("=" * 55)
        print("SWEDISH GROCERY API — SMOKE TEST")
        print("=" * 55)
        all_ok = True
        for name, ok, detail in results:
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {name:20s} {detail}")
            if not ok:
                all_ok = False
        print("=" * 55)
        print(f"  Result: {'ALL PASS' if all_ok else 'FAILURES DETECTED'}")
        print("=" * 55)
    else:
        all_ok = all(ok for _, ok, _ in results)

    return 0 if all_ok else 1


if __name__ == "__main__":
    quiet = "--quiet" in sys.argv
    sys.exit(run_checks(quiet))
