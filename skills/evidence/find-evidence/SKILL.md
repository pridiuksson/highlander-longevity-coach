---
name: find-evidence
license: MIT
description: "Find and verify evidence on health, nutrition, supplements, athletic performance, injury prevention, or coaching methods. Searches academic sources and reports confidence labels. Use when <USER> needs depth on these topics — not for quick factual lookups or schedule questions."
version: 1.1
---

# Find Evidence — Health & Performance Research

**Trigger:** <USER> asks about supplements, nutrition, training methods,
recovery, injury prevention, dosage, or anything health-related.

**Do NOT trigger for:** schedule questions, product prices, quick factual
lookups, or anything already in memory.

## The protocol

1. **Use the research skill**, not web_search. Run `--scholar` for academic
   papers, `--content` for deep evidence. Built-in web_search returns blogs
   for these topics.

2. **Source hierarchy:** peer-reviewed/meta-analysis > institutional guidelines
   (WHO, EFSA, IOC, Livsmedelsverket, NSCA, ACSM) > sports science journals >
   web results (leads only, never the answer).

3. **2-source minimum.** For any health claim, find at least 2 independent
   sources. If they disagree, present both: "The IOC consensus says X, but a
   2023 trial found Y."

4. **Recency matters.** Prefer research from the last 5-7 years unless it's a
   landmark study. Sports science evolves fast — a 2015 creatine meta-analysis
   may have been superseded.

5. **Clinical boundary.** If <USER> asks about a specific person's injury,
   condition, or treatment, give the evidence but end with: "For [name]'s
   specific case, consult a sports physician." Do not play doctor.

6. **"I don't know" floor.** If you can't find at least 2 peer-reviewed or
   institutional sources after searching, say so: "I couldn't find reliable
   evidence on this." Do not downgrade to blogs and slap a confidence label
   on it.

## How to answer

Lead with the practical answer in 1-2 sentences. Then the evidence: key
findings, what sources agree on, where they don't. Name sources specifically.

End with a confidence label:

- **CONFIRMED** — Multiple peer-reviewed sources agree; guidelines back it
- **LIKELY** — Good evidence but limited (few studies, small samples)
- **MIXED** — Sources disagree; both positions presented
- **UNVERIFIED** — Could not find reliable evidence; said so honestly
