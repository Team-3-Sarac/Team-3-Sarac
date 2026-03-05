# Trend Evaluation & Insight Validation
**Sprint:** Week 5–6  
**Status:** In Progress — Two approaches defined and analysis pending (week 6)  
**Sources:** https://www.geeksforgeeks.org/data-science/spearmans-rank-correlation/

---

## 1. Purpose

This document validates the outputs of the trend scoring pipeline developed during Sprint 5–6. It covers two approaches:
- A weighted algorithmic scorer
- A LLM-based scorer  

Both scorers will be benchmarked against the same dataset. Findings will serve as the cross-team reference before backend integration and frontend display.

**File Ownership**

| Approach                   | Owner    | File                  |
|----------------------------|----------|-----------------------|
| Weighted Scoring Algorithm | Isabella | `trend_scoring.py`    |
| LLM-Based Scoring          | Rudy     | `llm_trend_scorer.py` |

---


## 2. Approach 1: Weighted Scoring Algorithm

### Formula

`trend_score = (engagement_rate × 0.35) + (recency_score × 0.30) + (comment_quality × 0.20) + (views_normalized × 0.15)`

| Component          | Source Fields                               | Description                                                                                                                         |
|--------------------|---------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `engagement_rate`  | `like_count`, `comment_count`, `view_count` | (likes + comments) / views, normalized against 10% ceiling                                                                          |
| `recency_score`    | `publish_date`                              | Linear decay over 30 days (1.0 today → 0.0 at 30 days)                                                                              |
| `comment_quality`  | `comments.like_count`                       | Avg comment like count, normalized against ceiling of 100. Proxy for narrative popularity until `trends.mention_count` is populated |
| `views_normalized` | `view_count`                                | Min-max normalized across dataset                                                                                                   |

**Trending threshold:** `score >= 0.55` can be changed once full dataset is loaded.

**Weight justification:** 
- The engagement rate (0.35) reflects audience quality over raw reach. 
- The recency (0.30) reflects time-sensitivity of trending content. 
- The comment quality (0.20) captures narrative resonance. 
- The views normalization (0.15) adds relative popularity without letting high-view outliers dominate.

---

## 3. Approach 2: LLM-Based Scoring

Instead of computing a score from raw metrics, the LLM receives a video's title, summary, and top comments and assesses trending potential based on semantic understanding, 
match stakes, controversy, narrative momentum, and fan sentiment.

**Input per video:**
- `title`
- `summary` (if available)
- Top 5 comments by `like_count`
- `league`, `publish_date`

**Output per video:**
- `llm_trend_score` (0.0–1.0)
- `reasoning` (1 or 2 sentence justification)
- `is_trending` (true/false, threshold TBD)

---

## 4. Benchmarking Plan (Fully executed during week 6)

Both approaches run against the same dataset and compared on:

| Metric                  | Description                                                                                                      |
|-------------------------|------------------------------------------------------------------------------------------------------------------|
| **Rank correlation**    | Spearman's rank correlation between algorithmic and LLM score rankings                                           |
| **Edge case handling**  | Do both approaches correctly handle outliers (e.g. viral non-soccer clips, high-profile low-engagement matches)? |
| **LLM consistency**     | LLM scorer run 3x on same input and then variance in scores measured                                             |
| **Threshold agreement** | How often do both approaches agree on `is_trending` classification?                                              |

**Pipeline for Evaluation:**
```
filtered_videos.json + youtubeComments.json
        |
        V
trend_scoring.py       ->  algorithmic_scores.json
llm_trend_scorer.py    ->  llm_scores.json
        |
        V
benchmark.py           ->  benchmark_report.json
```

---

## 5. Dataset Overview

**Source files:**  
**Channel:**  
**Videos analyzed:**  
**Comment records scored:**  
**Date range:**  
**Trending videos identified (algorithmic):**  
**Trending videos identified (LLM):**  

---

## 6. Trend Output Analysis

### Video 1: (Title)
| Field              | Algorithmic | LLM |
|--------------------|-------------|-----|
| `trend_score`      |             |     |
| `is_trending`      |             |     |
| `engagement_rate`  |             | —   |
| `recency_score`    |             | —   |
| `comment_quality`  |             | —   |
| `views_normalized` |             | —   |
| `reasoning`        | —           |     |

**Assessment:**

---

### Video 2: (Title)
| Field              | Algorithmic | LLM |
|--------------------|-------------|-----|
| `trend_score`      |             |     |
| `is_trending`      |             |     |
| `engagement_rate`  |             | —   |
| `recency_score`    |             | —   |
| `comment_quality`  |             | —   |
| `views_normalized` |             | —   |
| `reasoning`        | —           |     |

**Assessment:**

---

### Video 3: (Title)
| Field              | Algorithmic | LLM |
|--------------------|-------------|-----|
| `trend_score`      |             |     |
| `is_trending`      |             |     |
| `engagement_rate`  |             | —   |
| `recency_score`    |             | —   |
| `comment_quality`  |             | —   |
| `views_normalized` |             | —   |
| `reasoning`        | —           |     |

**Assessment:**

---

### Video 4: (Title)
| Field              | Algorithmic | LLM |
|--------------------|-------------|-----|
| `trend_score`      |             |     |
| `is_trending`      |             |     |
| `engagement_rate`  |             | —   |
| `recency_score`    |             | —   |
| `comment_quality`  |             | —   |
| `views_normalized` |             | —   |
| `reasoning`        | —           |     |

**Assessment:**

---

### Video 5: (Title)
| Field              | Algorithmic | LLM |
|--------------------|-------------|-----|
| `trend_score`      |             |     |
| `is_trending`      |             |     |
| `engagement_rate`  |             | —   |
| `recency_score`    |             | —   |
| `comment_quality`  |             | —   |
| `views_normalized` |             | —   |
| `reasoning`        | —           |     |

**Assessment:**

---

## 7. Raw Data vs. Trend Score Comparison

| Title | Views | Likes | Comments | Eng. Rate | Algo Score | LLM Score | Agreement |
|-------|-------|-------|----------|-----------|------------|-----------|-----------|
|       |       |       |          |           |            |           |           |
|       |       |       |          |           |            |           |           |
|       |       |       |          |           |            |           |           |
|       |       |       |          |           |            |           |           |
|       |       |       |          |           |            |           |           |

**Rank correlation (Spearman's):**  
**Assessment:**

---

## 8. LLM Claims Layer Status

Claim extraction pipeline is under development (LLM Integration Layer task). Once operational, `comment_quality` in the algorithmic scorer will be replaced by 
`trends.mention_count` which is the claim frequency per narrative within a time window.

---

## 9. Inconsistencies & Cross-Team Feedback

| # | Finding                                                     | Severity | Team    | Action                             |
|---|-------------------------------------------------------------|----------|---------|------------------------------------|
| 1 | `league` and `teams` fields are `null` for all videos in DB | High     | Backend | Populate during ingestion pipeline |
| 2 |                                                             |          |         |                                    |
| 3 |                                                             |          |         |                                    |

---

## 10. Recommendations

**Recommendation 1:**

---

## 11. Repo Files Referenced

| File                      | Description                        |
|---------------------------|------------------------------------|
| `trend_scoring.py`        | Weighted scoring algorithm (Bella) |
| `llm_trend_scorer.py`     | LLM-based scoring (Rudy)           |
| `benchmark.py`            | Benchmarking and comparison script |
| `filtered_videos.json`    | Source video metadata              |
| `youtubeComments.json`    | Source comment data                |
| `algorithmic_scores.json` | Output from weighted scorer        |
| `llm_scores.json`         | Output from LLM scorer             |
| `benchmark_report.json`   | Final benchmark comparison output  |

---