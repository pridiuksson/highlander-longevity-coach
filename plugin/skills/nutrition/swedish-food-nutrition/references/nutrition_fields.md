# Swedish Grocery Nutrition Fields

## Axfood (Hemköp & Willys) — actual verified shape

The research doc describes GS1 codes (`ENER-`, `FAT`, `FASAT`, etc.) but the live API
returns **Swedish field names**. Use these:

### Primary: `nutrientHeaders[0].nutrientDetails[]`

```json
{
  "nutrientBasisQuantity": "100",
  "nutrientBasisQuantityMeasurementUnitCode": "gram",
  "nutrientDetails": [
    {"nutrientTypeCode": "energi",            "quantityContained": "1487", "measurementUnitCode": "kilojoule"},
    {"nutrientTypeCode": "energi",            "quantityContained": "350",  "measurementUnitCode": "kilokalori"},
    {"nutrientTypeCode": "fett",              "quantityContained": "0.6",  "measurementUnitCode": "gram"},
    {"nutrientTypeCode": "varav mättat fett", "quantityContained": "0.5",  "measurementUnitCode": "gram"},
    {"nutrientTypeCode": "kolhydrat",         "quantityContained": "78",   "measurementUnitCode": "gram"},
    {"nutrientTypeCode": "varav sockerarter", "quantityContained": "0.5",  "measurementUnitCode": "gram"},
    {"nutrientTypeCode": "protein",           "quantityContained": "7.4",  "measurementUnitCode": "gram"},
    {"nutrientTypeCode": "salt",              "quantityContained": "0",    "measurementUnitCode": "gram"}
  ]
}
```

### Field name mapping (Swedish → English output)

| Swedish `nutrientTypeCode`         | English key       |
|-------------------------------------|--------------------|
| `energi` (kilojoule unit)           | `energy_kj`        |
| `energi` (kilokalori unit)          | `energy_kcal`      |
| `fett`                              | `fat`              |
| `varav mättat fett`                 | `saturated_fat`    |
| `varav mättade fetter`              | `saturated_fat`    |
| `kolhydrat`                         | `carbohydrates`    |
| `varav sockerarter`                 | `sugars`           |
| `protein`                           | `protein`          |
| `salt`                              | `salt`             |
| `fiber` / `kostfiber`               | `fiber`            |

### Energy disambiguation

`energi` appears **twice** — once in kJ, once in kcal. Disambiguate by `measurementUnitCode`:
- `kilojoule` → `energy_kj`
- `kilokalori` → `energy_kcal`

### Fallback: `nutritionsFactList`

Flat list, usually carries **only energy**. Use only if `nutrientHeaders` is empty:

```json
[{"value": "1487", "typeCode": "energi", "unitCode": "kilojoule"}]
```

### Fresh produce gap

Loose Class 1 produce (onions, potatoes, loose mushrooms sold by weight) may return
**empty nutrition payload** — stores don't attach GS1 data to unpackaged goods.

**Verified 2026-06-20:** Canned/jarred produce (e.g. "Kantareller i Vatten") DOES return
nutrition. Truly loose produce is untested — if you hit an empty payload, fall back to:
1. ICA recipe nutrition (per-serving, from the recipe page)
2. Livsmedelsverket open food database (not yet integrated)

## ICA Recipe Nutrition — per serving, not per 100g

ICA recipe JSON-LD carries aggregate nutrition **per serving**, not per 100g:

```json
{
  "@type": "NutritionInformation",
  "servingSize": "4 Servings",
  "calories": "589 calories",
  "fatContent": "20 g",
  "carbohydrateContent": "75 g",
  "proteinContent": "19 g"
}
```

Parse the numeric value from the string (e.g. "589 calories" → 589).
This is the meal-level nutrition, already portion-adjusted.
