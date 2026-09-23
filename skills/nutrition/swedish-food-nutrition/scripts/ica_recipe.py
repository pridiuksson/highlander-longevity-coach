#!/usr/bin/env python3
"""
ICA recipe fetcher — extracts structured data from ica.se recipe pages.

ICA recipe pages are static server-rendered HTML with embedded JSON-LD.
No API, no auth, no JS rendering needed. Works with curl.

Usage from execute_code:
    import sys; sys.path.insert(0, "<skill_dir>/scripts")
    from ica_recipe import get_recipe, extract_ingredients

CLI usage:
    python ica_recipe.py "https://www.ica.se/recept/svamprisotto-1205/"
    python ica_recipe.py --ingredients-only "https://www.ica.se/recept/svamprisotto-1205/"
"""

import json
import re
import subprocess
import sys


def _fetch_html(url):
    """Fetch raw HTML via curl. web_extract is broken in some envs (search-only backend)."""
    result = subprocess.run(
        ["curl", "-sL", "-H", "User-Agent: Mozilla/5.0", url],
        capture_output=True, text=True, timeout=20,
    )
    if not result.stdout or len(result.stdout) < 500:
        raise RuntimeError(f"Empty response from {url} (got {len(result.stdout)} chars)")
    return result.stdout


def _extract_jsonld(html):
    """Extract and parse JSON-LD blocks from HTML. Returns the Recipe object or None."""
    blocks = re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL,
    )
    for block in blocks:
        try:
            data = json.loads(block)
            # Could be a single object or a list
            candidates = data if isinstance(data, list) else [data]
            for obj in candidates:
                if isinstance(obj, dict) and obj.get("@type", "").lower() == "recipe":
                    return obj
        except json.JSONDecodeError:
            continue
    return None


def get_recipe(url):
    """Fetch an ICA recipe page and return structured data.

    Returns dict:
        name, url, portions, total_time, rating, category, cuisine,
        ingredients (list of strings with quantities),
        instructions (list of strings),
        nutrition (dict: energy_kcal, fat_g, carbs_g, protein_g per serving)
    """
    html = _fetch_html(url)
    recipe = _extract_jsonld(html)
    if not recipe:
        raise RuntimeError(f"No recipe JSON-LD found at {url}")

    # Parse nutrition
    nutrition = {}
    n = recipe.get("nutrition", {})
    if n:
        # "589 calories" → 589
        kcal = n.get("calories", "")
        kcal_match = re.search(r"(\d+)", kcal)
        if kcal_match:
            nutrition["energy_kcal_per_serving"] = int(kcal_match.group(1))

        for key, suffix in [("fatContent", "fat_g"), ("carbohydrateContent", "carbs_g"),
                            ("proteinContent", "protein_g"), ("saturatedFatContent", "saturated_fat_g"),
                            ("fiberContent", "fiber_g"), ("sugarContent", "sugars_g"),
                            ("sodiumContent", "sodium_g")]:
            val = n.get(key, "")
            val_match = re.search(r"([\d.]+)", val)
            if val_match:
                nutrition[suffix] = float(val_match.group(1))

    # Parse time (ISO 8601 duration → minutes)
    total_time = recipe.get("totalTime", "")
    time_match = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?", total_time)
    total_minutes = None
    if time_match:
        hours = int(time_match.group(1) or 0)
        mins = int(time_match.group(2) or 0)
        total_minutes = hours * 60 + mins

    return {
        "name": recipe.get("name", ""),
        "url": url,
        "portions": recipe.get("recipeYield", ""),
        "total_time_minutes": total_minutes,
        "rating": (recipe.get("aggregateRating") or {}).get("ratingValue"),
        "category": recipe.get("recipeCategory", ""),
        "cuisine": recipe.get("recipeCuisine", ""),
        "ingredients": recipe.get("recipeIngredient", []),
        "instructions": [
            step.get("text", str(step)) if isinstance(step, dict) else str(step)
            for step in recipe.get("recipeInstructions", [])
        ],
        "nutrition_per_serving": nutrition,
        "nutrition_available": bool(nutrition),
        "description": recipe.get("description", ""),
    }


def extract_ingredients(url):
    """Convenience: return just the ingredient list from a recipe URL."""
    return get_recipe(url)["ingredients"]


def _cli():
    if len(sys.argv) < 2:
        print("Usage: ica_recipe.py [--ingredients-only] <url>")
        sys.exit(1)

    ingredients_only = "--ingredients-only" in sys.argv
    url = sys.argv[-1]

    if ingredients_only:
        for item in extract_ingredients(url):
            print(f"  - {item}")
    else:
        print(json.dumps(get_recipe(url), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
