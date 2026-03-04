# Trend Evaluation & Insight Validation
**Sprint:** Week 5–6  
**Status:** In Progress — Scoring formula created + outline of this document

---

## 1. Purpose

This document will validate the outputs of the trend scoring algorithm developed by the DS team during sprint weeks 5 and 6. 
It will serve as the reference for understanding how trend scores are computed, what the current outputs mean, and what adjustments are needed before 
backend integration and frontend UI display. Findings will be communicated to the backend and frontend teams via this document and corresponding communication.

---

## 2. Trend Scoring Formula

The algorithm produces a composite trend score per video in the range of 0.0 to 1.0. The formula for `trend_score` is the following:


`trend_score = (engagement_rate  × 0.35) + (recency_score    × 0.30) + (comment_quality  × 0.20) + (views_normalized × 0.15)`


| Component          | Source Fields                               | Description                                                                                                                                                 |
|--------------------|---------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `engagement_rate`  | `like_count`, `comment_count`, `view_count` | (likes + comments) / views                                                                                                                                  |
| `recency_score`    | `publish_date`                              | Natural, linear decay over 30 days (1.0 if published today, 0.0 at 30 days old)                                                                             |
| `comment_quality`  | `comments.like_count`                       | Average like count / comment, normalized against a ceiling of ~100. Using for "narrative popularity" until `trends.mention_count` is populated via pipeline |
| `views_normalized` | `view_count`                                | Min-max normalized view count relative to all videos in the dataset                                                                                         |

### Trending Threshold
Initially, a video is classified as `is_trending = true` when `trend_score >= 0.55`. However, this may change further into the evaluation.

### Justification for Weight and Scoring
- Engagement rate carries the highest weight (0.35) because a video with high likes and comments relative to views signals strong resonance regardless of total reach (i.e. views).
- Recency (0.30) is weighted second because trending content is time-sensitive. 
- Comment quality (0.20) serves as the current narrative popularity signal, replacing `trends.mention_count` until the LLM claims pipeline is fully operational (week 6). 
- Views normalization (0.15) provides another popularity signal, but is kept lower than `comment_quality` as comments typically signify more user engagement than just raw views.

---

## 3. Dataset Overview

**Source files:**  
**Channel:**  
**Videos analyzed:**  
**Comment records scored:**  
**Date range:**  
**Trending videos identified:**  

---

## 4. Trend Output Analysis

### Video 1: (Title)
(Table of calculated scores)  
(Written Analysis)  

---

### Video 2: (Title)
(Table of calculated scores)  
(Written Analysis)  

---

### Video 3: (Title)
(Table of calculated scores)  
(Written Analysis)  

---

### Video 4: (Title)
(Table of calculated scores)  
(Written Analysis)  

---

### Video 5: (Title)
(Table of calculated scores)  
(Written Analysis)  

---

## 5. Raw Data vs. Trend Score Comparison
(Table of calculated scores)  
(Written Analysis)  

---

## 6. LLM Layer Status

The claim extraction pipeline is currently under development by the DS team as a separate sprint task (LLM Integration Layer).
Once operational, each videos transcript chunks and comments will be processed to extract claims, which will then be grouped into narratives.
The `comment_quality` component in the current scoring formula will be replaced by `trends.mention_count` (the count of claims per narrative within a time window) 
which is a more meaningful signal.

---

## 7. Inconsistencies & Cross-Team Feedback

| # | Finding                                                     | Severity | Team    | Action                             |
|---|-------------------------------------------------------------|----------|---------|------------------------------------|
| 1 | `league` and `teams` fields are `null` for all videos in DB | High     | Backend | Populate during ingestion pipeline |

---

## 8. Recommendations

**Recommendation 1:**  

---

## 9. Repo Files Referenced

| File                       | Description                                                   |
|----------------------------|---------------------------------------------------------------|
| `trend_scoring.py`         | Trend scoring algorithm (DS team)                             |
| `filtered_videos.json`     | Source video metadata from ingestion pipeline                 |
| `youtubeComments.json`     | Source comment data from ingestion pipeline                   |
| `trend_scores_output.json` | Scored output from algorithm run used for this evaluation doc |

---