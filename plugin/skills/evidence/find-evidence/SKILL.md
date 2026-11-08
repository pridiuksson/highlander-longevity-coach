---
name: find-evidence
license: MIT
description: "Find and verify evidence on health, nutrition, supplements, athletic performance, injury prevention, or coaching methods. Searches academic sources and reports confidence labels. Use when the user needs depth on these topics — not for quick factual lookups or schedule questions."
version: 1.2
---

# Find Evidence — Health & Performance Research

**Trigger:** the user asks about supplements, nutrition, training methods,
recovery, injury prevention, dosage, or anything health-related.

**Do NOT trigger for:** schedule questions, product prices, quick factual
lookups, or anything already in memory.

## The protocol

1. **Use the research skill**, not web_search. Run `--scholar` for academic
   papers, `--content` for deep evidence. Built-in web_search returns blogs
   for these topics. Use `--min-if 6.0` (default) and `--min-year 2021` (default).

2. **Scientific literature quality standard:**
   - **Primary Standard:** 2021 onwards, published in scientific peer-reviewed journals with Clarivate JCR Impact Factor higher than six (IF > 6.0).
   - **Fallback Standard:** Earlier papers (< 2021) are permitted **only if they still possess an impact factor higher than six (IF > 6.0)** in a recognized peer-reviewed journal (e.g. *Sports Medicine*, *BJSM*, *JACC*, *Lancet*, *NEJM*, *JAMA*).
   - **Disqualification Rules:** Journals with IF ≤ 6.0 are disqualified from serving as primary evidence (e.g., *Nutrients*, *PLOS ONE*, *Sleep*, *Chronobiology International*, *JISSN*, *Medicine & Science in Sports & Exercise*). Preprints (*arXiv*, *bioRxiv*, *medRxiv*) and non-journal materials (books, conference abstracts, blog posts) do not qualify.
   - For PubMed abstract extraction without CAPTCHA via NCBI E-utilities, Cochrane CD-number disambiguation, and claim verification verdict rules, read `references/scientific-literature-verification.md`.

3. **Source hierarchy:** peer-reviewed meta-analysis / systematic review (IF > 6.0) > institutional guidelines (WHO, EFSA, IOC, Livsmedelsverket, NSCA, ACSM) > qualified randomized controlled trials (IF > 6.0) > web results (leads only, never the answer).

4. **2-source minimum.** For any health claim, find at least 2 independent
   sources. If they disagree, present both: "The IOC consensus says X, but a
   2023 trial found Y."

5. **Recency matters.** Prefer research from 2021 onwards unless citing a landmark protocol or pre-2021 study possessing IF > 6.0. Sports science evolves fast — a 2015 creatine meta-analysis may have been superseded.

6. **Clinical boundary.** If the user asks about a specific person's injury,
   condition, or treatment, give the evidence but end with: "For [name]'s
   specific case, consult a sports physician." Do not play doctor.

7. **"I don't know" floor.** If you can't find at least 2 peer-reviewed or
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
