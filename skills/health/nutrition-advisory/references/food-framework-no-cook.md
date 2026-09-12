# Food Framework — Build-a-Meal Pattern

*Pattern extracted from 2026-06-30 session. Reusable structure for food recommendations when the user needs SYSTEMS, not single items.*

## When to Use This Pattern

When the user asks "what should I eat?" and has expressed they lack structure (not motivation). This framework gives them a decision system, not a prescription. The user said: "I am not lazy, I am unstructured and you're to help."

## Cooking Capability

The user can **batch-cook 2-3×/week** (quinoa, grains, boiled eggs) and fridge-store portions for 4-5 days. This is NOT daily cooking — it's a Sunday + Wednesday batch session (~20 min each). Recommendations can include:
- Dry quinoa (batch-cooked, not pre-cooked packs — cheaper, larger portions)
- Pre-made grain bowls (quinoa + protein + veg, assembled from fridge at ~20:00)
- Boiled eggs (batch-boiled, stored)

The no-cook constraint applies to DAILY meal prep — the user will not cook on training days after work. The batch-cook window is on rest days or weekends.

## The Framework: 4 Layers

### Layer 1 — Timing Architecture

The structural insight: **when** you eat matters as much as **what** you eat. For a post-workup athlete with a commute:

| Principle | What it means |
|-----------|--------------|
| Eat the recovery meal BEFORE going home | Post-gym café stop at ~18:45, not at 20:00 at home. Protects sleep fast window AND ensures protein timing. |
| At-home eating is optional snacking | If protein is already banked at the café, whatever you eat at home is bonus — not a failed dinner. |
| Pre-gym shake bridges the lunch-to-gym gap | Casein + creatine + banana (on hard days) at 17:30. |

The mental shift: "dinner" happens at the gym-adjacent café. What happens at home is a snack. You're not missing a meal — you're front-loading it where it matters most.

### Layer 2 — Hunger-Tiered Options

Organize food options by hunger level, not by location. Each tier has 3+ options so the user never feels locked in.

| Tier | Hunger Level | Protein Target | Example Options |
|------|-------------|---------------|-----------------|
| 🔴 Very hungry (hard training day) | Post-intervals, post-long-run | 40-55g | Full meal + smoothie combo (sandwich + smoothie, or large salad + protein side) |
| 🟡 Hungry (normal training day) | Post-standard gym session | 25-35g | Single real-food meal (sandwich, salad with protein, or grain bowl) |
| 🟢 Light (low appetite or short session) | Post-easy-day or time-pressed | 20-25g | Light option (yoghurt/kvarg + fruit, or small salad, or a shake as fallback) |
| ⚪ Just a drink (micronutrient focus) | Not training-related hunger | <10g | Fresh juice for vitamins/minerals (iron, vitamin C, magnesium hits) |

**Key preference:** Real food (sandwiches, salads) is the DEFAULT. Shakes are a FALLBACK when the user doesn't want solid food or is rushing — not the primary recommendation. The user explicitly prefers real food and already has a pre-gym shake; stacking another shake creates "three liquid meals in one evening."

### Layer 3 — Category-Based Food Lists

Instead of fixed meals, give the user component categories to mix and match:

**Protein sources (no-cook):**
- Smoked salmon (vacuum packs) — omega-3 + protein + no prep
- Tuna (tinned or pouch) — lean protein, shelf-stable
- Cottage cheese / kvarg / skyr — slow-digesting casein, Swedish staples
- Eggs (pre-boiled if available) — complete protein, choline
- Protein bars (already in user's breakfast rotation)

**Carb sources (training-dependent):**
- Banana — fastest, pre-workout fuel
- Crispbread / sourdough — slow-release, post-workout
- Quinoa — batch-cook dry (1 cup → 3 cups, stores 4-5 days). Triple-hits Mg (197mg/100g), iron (4.6mg), folate (184µg). Physician-prescribed for ApoB.
- Rice (buffet or microwave pouch) — glycogen replenishment
- Oats — weekend base, beta-glucan for ApoB
- Dates — densest natural carb, endurance fuel

**Fat sources (testosterone substrate + satiety):**
- Avocado — monounsaturated, AHEI-aligned
- Olive oil — primary dressing fat
- Walnuts / almonds — omega-3 ALA + magnesium
- Chia / pumpkin seeds — omega-3 + magnesium + fiber
- Dark chocolate 70%+ — magnesium, replaces sugar-heavy raw bars

**The rule:** Pick 1 protein + 1 carb (training days) + 1 fat. Every combination works. Carbs scale UP on hard training days, DOWN on rest days.

### Layer 4 — Day-Type Mapping

| Day Type | Carb Level | Fat Level | Post-Training Tier | Notes |
|----------|-----------|-----------|-------------------|-------|
| Interval day (Zone 5) | HIGH | Moderate | 🔴 Very hungry | Most glycogen-demanding. Extra carbs at lunch + pre-gym banana. |
| Gym day (strength) | Moderate | Moderate | 🟡 Hungry | Standard recovery meal. |
| Easy run (Zone 2) | Low-Moderate | Moderate | 🟡 Hungry | Zone 2 is fat-dominant — low-carb is fine, even optimal (trains fat oxidation). |
| Rest day | Low | Moderate | N/A | No post-gym meal needed. Smallest intake day. |

## Grocery List Pattern (Weekly Staples)

| Category | Items | Why |
|----------|-------|-----|
| Protein (no-cook) | Smoked salmon packs, tuna pouches, cottage cheese, kvarg, protein bars | Post-gym and at-home dinner building blocks |
| Carbs (no-cook) | Crispbread, bananas, dates, microwave rice pouches | Pre-run fuel + post-gym carb replenishment |
| Fats (no-cook) | Avocado, mixed nuts/seeds, olive oil | Testosterone substrate + satiety |
| Veggies (zero prep) | Cherry tomatoes, cucumber, pre-washed spinach | Just open and eat |
| Hydration | Electrolyte tabs (for summer runs) | Sodium replacement |

Everything can be bought in one grocery trip, requires zero cooking, and lasts a week.

## What NOT to Do

- ❌ Do NOT prescribe a single item as "the answer" — provide the framework
- ❌ Do NOT default to shakes/smoothies when the user prefers real food
- ❌ Do NOT recommend daily cooking — batch-cook 2-3×/week is the ceiling, not daily meal prep
- ❌ Do NOT prescribe gram targets for carbs/fat — use qualitative levels (HIGH/MODERATE/LOW) mapped to day type
- ❌ Do NOT separate "post-gym" and "dinner" into two meals when timing makes them the same event (eat at the café before going home)
