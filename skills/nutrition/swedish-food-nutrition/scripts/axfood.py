#!/usr/bin/env python3
"""
Axfood product API client — Hemköp & Willys.

No auth needed. Both chains share the same backend; only the domain differs.
Returns clean, compact dicts — not raw API responses.

Usage from execute_code:
    import sys; sys.path.insert(0, "<skill_dir>/scripts")
    from axfood import search, get_product, compare_prices, search_with_details

CLI usage:
    python axfood.py search "arborioris" --store hemkop
    python axfood.py product 101599140_ST --store hemkop
    python axfood.py compare "arborioris"
"""

import json
import sys
import urllib.request
import urllib.parse

STORES = {
    "hemkop": "https://www.hemkop.se",
    "willys": "https://www.willys.se",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
}

# Swedish nutrition field names → English keys for the output
NUTRITION_MAP = {
    "energi": "energy",
    "fett": "fat",
    "varav mättat fett": "saturated_fat",
    "varav mättade fetter": "saturated_fat",
    "kolhydrat": "carbohydrates",
    "varav sockerarter": "sugars",
    "protein": "protein",
    "salt": "salt",
    "fiber": "fiber",
    "kostfiber": "fiber",
}


def _store_domain(store="hemkop"):
    store = store.lower()
    if store not in STORES:
        raise ValueError(f"Unknown store '{store}'. Use: {', '.join(STORES)}")
    return STORES[store]


def _fetch(url, store="hemkop"):
    headers = dict(HEADERS)
    headers["Referer"] = _store_domain(store) + "/"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def search(query, store="hemkop", size=5):
    """Search products. Returns list of compact product dicts.

    Each dict: name, price (float), price_display, compare_price, compare_unit,
    code, brand, image_url, out_of_stock
    """
    domain = _store_domain(store)
    url = f"{domain}/search?q={urllib.parse.quote(query)}&page=0&size={size}"
    data = _fetch(url, store)
    results = data.get("results", [])
    return [_compact_search_result(r) for r in results]


def _compact_search_result(r):
    return {
        "name": r.get("name", ""),
        "brand": r.get("manufacturer", ""),
        "price": r.get("priceValue"),
        "price_display": r.get("price", ""),
        "compare_price": r.get("comparePrice", ""),
        "compare_unit": r.get("comparePriceUnit", ""),
        "code": r.get("code", ""),
        "image_url": (r.get("image") or {}).get("url", ""),
        "out_of_stock": r.get("outOfStock", False),
        "store": None,  # filled by caller
    }


def get_product(code, store="hemkop"):
    """Get full product details including nutrition and ingredients.

    Returns dict with: name, brand, price, compare_price, ingredients,
    nutrition (per 100g dict), origin_country, ean, out_of_stock
    """
    domain = _store_domain(store)
    url = f"{domain}/axfood/rest/p/{code}?include=BREADCRUMB,NUTRIENTS"
    p = _fetch(url, store)
    return _compact_product(p, store)


def _compact_product(p, store):
    nutrition = _parse_nutrition(p)
    return {
        "name": p.get("name", ""),
        "brand": p.get("manufacturer", ""),
        "price": p.get("priceValue"),
        "price_display": p.get("price", ""),
        "compare_price": p.get("comparePrice", ""),
        "compare_unit": p.get("comparePriceUnit", ""),
        "code": p.get("code", ""),
        "ean": p.get("ean", ""),
        "ingredients": p.get("ingredients", ""),
        "nutrition": nutrition,
        "nutrition_available": bool(nutrition),
        "origin_country": p.get("originCountry", p.get("tradeItemCountryOfOrigin", "")),
        "out_of_stock": p.get("outOfStock", False),
        "storage": _parse_storage(p),
        "store": store,
    }


def _parse_nutrition(p):
    """Parse nutrition from nutrientHeaders (primary) or nutritionsFactList (fallback).

    Returns dict with energy_kj, energy_kcal, fat, saturated_fat, carbs,
    sugars, protein, salt — all per 100g. Empty dict if no data.
    """
    result = {}

    # Primary: nutrientHeaders[].nutrientDetails[]
    headers = p.get("nutrientHeaders", [])
    if headers:
        details = headers[0].get("nutrientDetails", [])
        for d in details:
            ntype = (d.get("nutrientTypeCode") or "").lower().strip()
            val = d.get("quantityContained")
            unit = (d.get("measurementUnitCode") or "").lower().strip()
            if val is None:
                continue
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue

            # Energy has two units (kJ + kcal) — disambiguate
            if ntype == "energi":
                if unit.startswith("kilojoule") or unit == "kj":
                    result["energy_kj"] = val
                elif unit.startswith("kilokalori") or unit == "kcal":
                    result["energy_kcal"] = val
                continue

            # Map Swedish names to English keys
            mapped = NUTRITION_MAP.get(ntype)
            if mapped:
                result[mapped] = val

    # Fallback: nutritionsFactList (usually only energy)
    if not result:
        nfl = p.get("nutritionsFactList", [])
        for item in nfl:
            ntype = (item.get("typeCode") or "").lower().strip()
            val = item.get("value")
            unit = (item.get("unitCode") or "").lower().strip()
            if val is None:
                continue
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue
            if ntype == "energi":
                if unit.startswith("kilojoule") or unit == "kj":
                    result["energy_kj"] = val
                elif unit.startswith("kilokalori") or unit == "kcal":
                    result["energy_kcal"] = val

    return result


def _parse_storage(p):
    parts = []
    for key in ("consumerStorageInstructions", "minStorageTemperature", "maxStorageTemperature"):
        v = p.get(key)
        if v:
            parts.append(str(v))
    return " ".join(parts) if parts else ""


def search_with_details(query, store="hemkop", size=3):
    """Search then fetch full details (nutrition + ingredients) for top results."""
    results = search(query, store, size)
    detailed = []
    for r in results:
        try:
            full = get_product(r["code"], store)
            detailed.append(full)
        except Exception:
            # If detail fails, keep the search-level data
            r["store"] = store
            detailed.append(r)
    return detailed


def compare_prices(query, size=3):
    """Search the same query across both Hemköp and Willys, return side-by-side.

    Returns dict: {query, hemkop: [...], willys: [...]}
    """
    return {
        "query": query,
        "hemkop": search(query, "hemkop", size),
        "willys": search(query, "willys", size),
    }


# --- CLI ---

def _cli():
    if len(sys.argv) < 2:
        print("Usage: axfood.py <command> [args]")
        print("Commands: search <query> [--store hemkop|willys] [--size N]")
        print("          product <code> [--store hemkop|willys]")
        print("          compare <query> [--size N]")
        print("          details <query> [--store hemkop|willys] [--size N]")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Parse flags
    store = "hemkop"
    size = 3
    positional = []
    i = 0
    while i < len(args):
        if args[i] == "--store":
            store = args[i + 1]
            i += 2
        elif args[i] == "--size":
            size = int(args[i + 1])
            i += 2
        else:
            positional.append(args[i])
            i += 1

    if cmd == "search":
        query = " ".join(positional)
        print(json.dumps(search(query, store, size), indent=2, ensure_ascii=False))
    elif cmd == "product":
        code = positional[0]
        print(json.dumps(get_product(code, store), indent=2, ensure_ascii=False))
    elif cmd == "compare":
        query = " ".join(positional)
        print(json.dumps(compare_prices(query, size), indent=2, ensure_ascii=False))
    elif cmd == "details":
        query = " ".join(positional)
        print(json.dumps(search_with_details(query, store, size), indent=2, ensure_ascii=False))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    _cli()
