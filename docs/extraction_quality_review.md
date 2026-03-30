## Overview

This document reviews the quality of narrative cluster groupings and LLM-extracted claims against real database data. The goal is to validate semantic coherence of narrative clusters, identify hallucinated or degraded claims, and confirm that `mention_count` per narrative is correctly written to the `trends` collection.

---

## Narrative Cluster Review

Three narrative clusters were manually reviewed for semantic coherence by inspecting grouped claims against their source content.

---

### Cluster 1 — Maldini Assist
**Narrative ID:** `69b0fb4b306b3162c14c06bf`  
**mention_count:** 2  

| # | Claim |
|---|-------|
| 1 | "Maldini provided the assist." |
| 2 | "Daniel Maldini made an assist." |

**Coherence Assessment:** Pass — both claims refer to the same real event and are correctly grouped.  
**Quality Issue:** Claim 1 is a vague restatement of Claim 2. The LLM dropped the subject's first name, producing a redundant near-duplicate instead of a single canonical claim.  
**Hallucination:** None detected.

---

### Cluster 2 — Defensive Openness
**Narrative ID:** `69b35c3ee85a628aa02ddf81`  
**mention_count:** 2  

| # | Claim |
|---|-------|
| 1 | "The defense was too open sometimes at the back." |
| 2 | "The defense is sometimes far too open at the back." |

**Coherence Assessment:** Pass — both claims express the same observation and are correctly grouped.  
**Quality Issue:** Near-duplicate phrasing suggests the LLM extracted the same claim twice from slightly different parts of the transcript rather than deduplicating.  
**Hallucination:** None detected.

---

### Cluster 3 — Goal Count Narratives
**Narrative IDs:** `69b35c3fe85a628aa02ddf82`, `69b35c40e85a628aa02ddf83`, `69b35c40e85a628aa02ddf84`  
**mention_counts:** 2, 2, 2  

| # | Claim |
|---|-------|
| 1 | "Players scored four goals." / "A player or team scored four goals." |
| 2 | "Players scored five goals." / "A player or team scored five goals." |
| 3 | "Players scored six goals." / "A player or team scored six goals." |

**Coherence Assessment:** Pass — goal count claims are correctly grouped by count value.  
**Quality Issue:** Claims are stripped of all specificity. No player names, team names, or match context are preserved. This is a medium-severity extraction quality issue — the LLM is over-generalizing source content rather than retaining factual detail.  
**Hallucination:** None detected, but loss of specificity reduces claim usefulness significantly.

---

## Issues Summary

| Issue | Type | Severity | Affected Clusters |
|-------|------|----------|-------------------|
| Redundant near-duplicate claims | Extraction quality | Low | Clusters 1, 2 |
| Loss of specificity (no names/context) | Extraction quality | Medium | Cluster 3 |
| All leagues stored as `"unknown"` | Data pipeline | Medium | All |

---

## Trends Collection Validation

The `mention_count` per narrative has been successfully written to the `trends` collection via `trends_service.py`.

**Sample document:**
```
{
  "narrative_id": ObjectId("69b0fb4b306b3162c14c06bf"),
  "league": "unknown",
  "time_window": "1d",
  "mention_count": 2,
  "trending_direction": "stable",
  "score": 0.0,
  "created_at": 2026-03-29T19:17:20
}
```

- Total trend documents written: **222**
- `mention_count` source: total number of claims grouped under each narrative
- `score` is currently a placeholder (`curr_count * 1.5`) — pending integration with composite scoring algorithm

---

## Video Audit
*In progress — Step 2.*