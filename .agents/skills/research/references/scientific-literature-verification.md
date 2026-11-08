# Scientific Literature Verification

Load this reference when verifying claims that cite scientific papers — PubMed
IDs (PMIDs), Cochrane reviews, DOI links, or specific study findings. Distinct
from general web fact-checking because the source artifacts (abstracts, review
numbers) are structured, exact, and must be quoted rather than paraphrased.

## Scientific Literature Quality Thresholds

When searching for, citing, or relying on scientific papers, enforce the following criteria:

### 1. Primary Standard (Default Target)
- **Publication Year:** 2021 onwards (≥ 2021)
- **Publication Type:** Published in a scientific peer-reviewed journal
- **Impact Factor:** Clarivate JCR Impact Factor **higher than six (IF > 6.0)**

### 2. Fallback Standard (Conditional)
- Papers published **earlier than 2021** are acceptable **only if they still possess an impact factor higher than six (IF > 6.0)** in a recognized peer-reviewed journal.
- Examples of valid fallback journals: *Nature* (50.5), *Cell* (45.5), *The Lancet* (98.4), *NEJM* (96.2), *JAMA* (63.1), *JACC* (24.0), *Circulation* (35.5), *European Heart Journal* (37.6), *Sports Medicine* (11.1), *British Journal of Sports Medicine* (11.6), *PNAS* (9.4), *JAMA Network Open* (10.5), *Cochrane Database of Systematic Reviews* (8.4), *American Journal of Clinical Nutrition* (6.5), *Clinical Nutrition* (6.3).

### 3. Disqualification Criteria
- **Journals with IF ≤ 6.0:** Disqualified from serving as primary evidence. Examples:
  - *Nutrients* (IF ~4.8)
  - *PLOS ONE* (IF ~2.9)
  - *Sleep* (IF ~5.6)
  - *Sleep and Breathing* (IF ~2.1)
  - *Chronobiology International* (IF ~2.5)
  - *Journal of Biological Rhythms* (IF ~2.9)
  - *Clocks & Sleep* (IF ~2.1)
  - *Medical Journal Armed Forces India* (IF ~1.1)
  - *Journal of Nutrition* (IF ~4.2)
  - *Journal of the American College of Nutrition* (IF ~3.4)
  - *Journal of Strength and Conditioning Research* (IF ~3.2)
  - *Journal of the International Society of Sports Nutrition* (IF ~4.9)
  - *Medicine & Science in Sports & Exercise* (IF ~4.1)
  - *Journal of Applied Physiology* (IF ~3.3)
  - *European Journal of Applied Physiology* (IF ~3.0)
  - *BMC Nephrology* (IF ~2.2)
  - *Frontiers in Human Neuroscience* (IF ~2.9) / *Frontiers in Physiology* (IF ~4.0)
- **Preprints:** *arXiv*, *bioRxiv*, *medRxiv*, *SSRN*, *Research Square* are unreviewed preprints and do not qualify.
- **Non-Journal Materials:** Book chapters, conference proceedings without journal status, StatPearls entries, and vendor whitepapers do not qualify.

## Fetching PubMed Abstracts

PubMed's HTML pages (`pubmed.ncbi.nlm.nih.gov/<PMID>/`) are protected by
reCAPTCHA and will block `curl`, `web_extract`, and other automated fetchers.

**Use the NCBI E-utilities API instead — it is a plain-text endpoint with no
CAPTCHA:**

```bash
curl -sL "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=<PMID>&rettype=abstract&retmode=text"
```

This returns the full structured abstract (Purpose, Methods, Results,
Conclusions) plus author list, DOI, and citation. No API key required for
low-volume use.

For structured XML metadata (authors, MeSH terms, publication type):

```bash
curl -sL "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=<PMID>&rettype=xml&retmode=text"
```

## Common Verification Error Modes

### 1. Cochrane CD-number confusion

Cochrane reviews have unique identifiers like `CD010405`. These get confused or
misattributed in secondary sources. **Always resolve the CD number to the exact
review title and author** before accepting a claim about what a review found.

Example from practice: A document cited "Cochrane CD010405" for a claim about
CoQ10 in heart failure. But CD010405 is Flowers et al. 2014 — *primary
prevention of CVD*. The heart failure review is Madmani et al. 2014 — a
different CD number (CD008684). The claim was about the wrong review.

Check CD numbers against the Cochrane Library directly:

```
https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.<CD-NUMBER>.pub2/full
```

Or search: `site:cochranelibrary.com <CD-NUMBER>`

### 2. Abstract numbers must be quoted exactly

When a claim makes a quantitative assertion (e.g., "cardiorespiratory endurance increased 10-15%"),
the abstract contains the actual reported numbers. **Quote them directly from
the E-utilities fetch** — do not paraphrase, round, or approximate. Report the
exact figures and the exact group they belong to.

Common mismatches:
- Claim cites a range that doesn't appear in the abstract
- Claim attributes a finding to the wrong study arm
- Claim rounds a directionally-correct but quantitatively-different result

### 3. Study population ≠ claim population

A review of "primary prevention in healthy adults" may actually include only
high-risk or statin-treated patients. Check the Methods/eligibility section in
the abstract, not just the title. Flag when the studied population differs from
the population the claim describes.

### 4. Comparator arm confusion

When a claim says "X outperformed Y," verify which arms were actually compared.
Studies with multiple arms (e.g., Helgerud 2007 had 4 groups: LSD, lactate
threshold, 15/15 intervals, 4×4 intervals) allow several pairwise comparisons.
The claim may name the wrong comparator or omit that multiple comparators
existed.

## Verdict Labels for Literature Claims

| Label | When to use |
|-------|-------------|
| **TRUE** | Citation is correct AND the finding as described matches the primary source abstract |
| **FALSE** | The cited source does not support the claim (wrong paper, wrong CD number, inverted finding, fabricated data) |
| **PARTIALLY TRUE** | Directionally correct but quantitatively off, or right paper but wrong detail, or studied population differs from claimed population |

Report each claim with:
- Verdict label
- The exact primary source URL (PubMed or Cochrane)
- A one-line evidence summary citing the specific finding from the abstract

Do NOT paraphrase generically. If the abstract says "7.2%" and the claim says
"10-15%", report "7.2%" — the reader can see the discrepancy.
