# Trend Evaluation & Insight Validation
**Sprint:** Week 5–6  
**Status:** In Progress — Two approaches defined and benchmarking IP  
**Sources:** https://www.geeksforgeeks.org/data-science/spearmans-rank-correlation/

---

## 1. Purpose

This document validates the outputs of the trend scoring pipeline developed during Sprint 5–6. It covers two approaches:
- A weighted algorithmic scorer
- A LLM-based scorer  

Both scorers will be benchmarked against the same dataset. Findings will serve as the cross-team reference before backend integration and frontend display.

**File Ownership**

| Approach                   | Owner    | File                        |
|----------------------------|----------|-----------------------------|
| Weighted Scoring Algorithm | Isabella | `trend_scoring_weighted.py` |
| LLM-Based Scoring          | Isabella | `trend_scoring_llm.py`      |
| Benchmarking               | Isabella | `benchmark.py`              |

---

## 2. Approach 1: Weighted Scoring Algorithm

### Formula

`trend_score = (engagement_rate × 0.35) + (recency_score × 0.30) + (mention_score × 0.20) + (views_normalized × 0.15)`

| Component          | Source Fields                               | Description                                                                                                  |
|--------------------|---------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| `engagement_rate`  | `like_count`, `comment_count`, `view_count` | (likes + comments) / views, normalized against 10% ceiling (can be calibrated down to ~5% depending on data) |
| `recency_score`    | `publish_date`                              | Linear decay over 30 days (1.0 today → 0.0 at 30 days)                                                       |
| `mention_score`    | `trends.mention_count`                      | Reflects how much narrative-level buzz is directly traceable to a video's claims, ceiling of 500             |
| `views_normalized` | `view_count`                                | Min-max normalized across dataset                                                                            |

**Trending threshold:** `score >= 0.40` calibrated through manual analysis of the dataset.

**Weight justification:** 
- The engagement rate (0.35) reflects audience quality over raw reach. 
- The recency (0.30) reflects time-sensitivity of trending content. 
- The mention score (0.20) captures narrative resonance through the claim -> narrative pipeline. 
- The views normalization (0.15) adds relative popularity without letting high-view outliers dominate.

---

## 3. Approach 2: LLM-Based Scoring

Instead of computing a score from raw metrics, the LLM receives a video's title, summary, and top comments and assesses trending potential based on semantic understanding, 
match stakes, controversy, narrative momentum, and fan sentiment.

**Model:** `gpt-4o-mini`
 
**Input per video:**
- `title`
- `summary` (if available)
- Top 3 comments by `like_count` (capped for efficiency w/ tokens)
- `league`, `publish_date`

**Output per video:**
- `llm_trend_score` (0.0–1.0)
- `reasoning` (one sentence justification)
- `is_trending` (true/false, threshold >= 0.55 to match weighted scorer)

**Efficiency measures:**
- `gpt-4o-mini` used over `gpt-4o` — sufficient for scoring, significantly cheaper (about 3c/run of ~300 videos w/ token eff. measures)
- System prompt defined once and reused across all video requests
- Comments capped at top 3 by like_count, truncated to 120 characters each
- Response capped at 80 tokens
- `temperature=0` for deterministic, consistent output across benchmark runs

---

## 4. Time Series Approach

The trend scoring formula does not change between runs. Instead, both scorers are re-executed on a weekly schedule by the orchestrator script, and each result is stored 
with a `scored_at` timestamp. This allows the pipeline to track how a video's `trend_score` evolves over time by capturing whether content is gaining, holding, or 
losing momentum week over week.

**How it works:**
- Orchestrator triggers both scoring scripts weekly
- Each run produces a new scored output with `scored_at` appended per record
- Historical scores stored in MongoDB, enabling trend direction (`trending_direction`: up / stable / down) to be derived by comparing current vs. prior week scores
- This feeds directly into the `trends` collection (`mention_count`, `trending_direction`, `time_window`)

**Example:**

| Week | Video                | Algo Score | LLM Score | Direction |
|------|----------------------|------------|-----------|-----------|
| W5   | Arsenal vs Tottenham | 0.27       | —         | —         |
| W6   | Arsenal vs Tottenham | 0.41       | 0.38      | up        |
| W7   | Arsenal vs Tottenham | 0.29       | 0.31      | down      |

---

## 5. Benchmarking Plan

Both approaches run against the same dataset and compared on:

| Metric                  | Description                                                                                                      |
|-------------------------|------------------------------------------------------------------------------------------------------------------|
| **Rank correlation**    | Spearman's rank correlation between algorithmic and LLM score rankings                                           |
| **Edge case handling**  | Do both approaches correctly handle outliers (e.g. viral non-soccer clips, high-profile low-engagement matches)? |
| **Threshold agreement** | How often do both approaches agree on `is_trending` classification?                                              |

**Pipeline for Evaluation:**
```
filtered_videos.json + youtubeComments.json
        |
        V
trend_scoring_weighted.py  ->  weighted_algorithmic_scores.json
trend_scoring_llm.py       ->  llm_scores.json
        |
        V
benchmark.py               ->  benchmark_report.json
```

---

## 6. Dataset Overview

**Source files:** `weighted_algorithmic_scores.json`, `llm_scores.json`  
**Videos compared:** 294  
**Date range:** March 4–11 2026  
**Trending videos identified (algorithmic):** 2 / 294  
**Trending videos identified (LLM):** 4 / 294  

---

## 7. Trend Output Analysis

### Video 1: Atlético Madrid vs. Tottenham: Extended Highlights | UCL Round of 16 - Leg 1 | CBS Sports Golazo
| Field              | Algorithmic | LLM                                                                                                                                                               |
|--------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `trend_score`      | 0.6304      | 0.20                                                                                                                                                              |
| `is_trending`      | true        | false                                                                                                                                                             |
| `engagement_rate`  | 0.1195      | —                                                                                                                                                                 |
| `recency_score`    | 0.7952      | —                                                                                                                                                                 |
| `comment_quality`  | 1.0         | —                                                                                                                                                                 |
| `views_normalized` | 1.0         | —                                                                                                                                                                 |
| `reasoning`        | —           | The video is from 2026, making it outdated, and while there are some fan sentiments, the lack of current relevance and context diminishes its trending potential. |
 
**Assessment:** This is the largest disagreement in the dataset because algo scores it trending (0.63) while the LLM rejects it (0.20). The algo rewards its 
maxed-out `comment_quality` and `views_normalized` while the LLM flags it as outdated relative to its training data. This is a known LLM limitation: the model 
penalizes content dated after its knowledge cutoff as "future" content rather than evaluating it on soccer relevance.  
**Ultimately, the weighted algo is correct here because this is a legitimate UCL knockout match and should be trending.**

---

### Video 2: It's never too late for success ⛷️🤩
| Field              | Algorithmic | LLM                                                            |
|--------------------|-------------|----------------------------------------------------------------|
| `trend_score`      | 0.613       | 0.00                                                           |
| `is_trending`      | true        | false                                                          |
| `engagement_rate`  | 1.0         | —                                                              |
| `recency_score`    | 0.7933      | —                                                              |
| `comment_quality`  | 0.118       | —                                                              |
| `views_normalized` | 0.0092      | —                                                              |
| `reasoning`        | —           | The video is not related to soccer and lacks relevant content. |
 
**Assessment:** This is a clear false positive for the weighted algo. A non-soccer short clip scored 2nd overall (0.613) because its `engagement_rate` hit 1.0 from 
1,211 likes on only 11,441 views. The LLM correctly scores it 0.0 and rejects it.  
**Ultimately, this confirms the need for a `duration_seconds` filter and content-type check on the algorithmic approach/in our scraping procedures.**

---

### Video 3: Brighton v. Arsenal | PREMIER LEAGUE HIGHLIGHTS | 3/4/2026 | NBC Sports
| Field              | Algorithmic | LLM                                                                                                                                                 |
|--------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| `trend_score`      | 0.338       | 0.80                                                                                                                                                |
| `is_trending`      | false       | true                                                                                                                                                |
| `engagement_rate`  | 0.12        | —                                                                                                                                                   |
| `recency_score`    | 0.5948      | —                                                                                                                                                   |
| `comment_quality`  | 0.45        | —                                                                                                                                                   |
| `views_normalized` | 0.46        | —                                                                                                                                                   |
| `reasoning`        | —           | The match features significant stakes with Arsenal's title race and Tottenham's relegation battle, generating strong fan sentiment in the comments. |
 
**Assessment:** The algo scores it 0.338 (below the trending threshold) while the LLM scores it 0.80. The weighted scorer only sees moderate engagement numbers and an aged 
publish date. The LLM identifies the Arsenal title race and Tottenham relegation narrative as high-interest context. However, when manually analyzing the video, the match 
is not trending in comparison to the other matches in the dataset.  
**Ultimately, this example illustrates the power of the algorithmic approach because it scores content metrics, compared to having an LLM see "Arsenal" and mark it as trending
due to their popularity and relevance.**

---

### Video 4: Galatasaray vs. Liverpool: Extended Highlights | UCL Round of 16 - Leg 1 | CBS Sports Golazo
| Field              | Algorithmic | LLM                                                                                                             |
|--------------------|-------------|-----------------------------------------------------------------------------------------------------------------|
| `trend_score`      | 0.4126      | 0.70                                                                                                            |
| `is_trending`      | false       | true                                                                                                            |
| `engagement_rate`  | 0.108       | —                                                                                                               |
| `recency_score`    | 0.793       | —                                                                                                               |
| `comment_quality`  | 0.38        | —                                                                                                               |
| `views_normalized` | 0.505       | —                                                                                                               |
| `reasoning`        | —           | The match features significant stakes in the UCL knockout stage, a notable rivalry, and positive fan sentiment. |
 
**Assessment:** Strong raw metrics (351K views, 428 comments) but falls short of the 0.55 threshold at 0.41. LLM scores it 0.70 based on UCL knockout context and 
rivalry significance. This is a case where the algo undersells a legitimately high-profile match. Threshold recalibration or a competition-type weight multiplier 
would likely fix this.  
**Ultimately, this will result in a recommendation to reduce the trending threshold to around 0.40.**

---

### Video 5: Lamine Yamal CAN'T BE STOPPED 👏 Takeaways from Barcelona's LALIGA win vs. Athletic Club | ESPN FC
| Field              | Algorithmic | LLM                                                                                                                |
|--------------------|-------------|--------------------------------------------------------------------------------------------------------------------|
| `trend_score`      | 0.3277      | 0.70                                                                                                               |
| `is_trending`      | false       | true                                                                                                               |
| `engagement_rate`  | 0.23        | —                                                                                                                  |
| `recency_score`    | 0.726       | —                                                                                                                  |
| `comment_quality`  | 0.09        | —                                                                                                                  |
| `views_normalized` | 0.065       | —                                                                                                                  |
| `reasoning`        | —           | The video discusses a rising star in a significant league match, generating positive fan sentiment and excitement. |
 
**Assessment:** Analysis content about a rising star has low view count (55K) which keeps `views_normalized` near zero as well as the `comment_quality` of 0.09. 
Algo scores it 0.33 while the LLM scores it 0.70 based on player narrative momentum around Yamal. After manual analysis, the video is not trending in comparison to 
the other matches in the dataset.  
**Ultimately, this example illustrates the power of the algorithmic approach because it scores content metrics, compared to having an LLM see "Yamal" and mark it as trending
due to his popularity and relevance. This result is similar to the video 3 analysis above.**

---

## 8. Raw Data vs. Trend Score Comparison

| Title (shortened)                     | Views   | Likes | Comments | Algo Score | LLM Score | Agreement |
|---------------------------------------|---------|-------|----------|------------|-----------|-----------|
| Atlético Madrid vs. Tottenham UCL     | 690,909 | 7,082 | 1,171    | 0.6304     | 0.20      | NO        |
| It's never too late for success       | 11,441  | 1,211 | 12       | 0.6130     | 0.00      | NO        |
| Tottenham v. Crystal Palace PL        | 363,171 | 4,368 | 652      | 0.4994     | 0.30      | YES       |
| Newcastle vs. Barcelona UCL           | 525,162 | 6,121 | 988      | 0.4942     | 0.20      | YES       |
| Galatasaray vs. Liverpool UCL         | 351,373 | 3,331 | 428      | 0.4126     | 0.70      | NO        |
| Brighton v. Arsenal PL                | 318,526 | 3,570 | 275      | 0.3380     | 0.80      | NO        |
| Lamine Yamal Barcelona vs Athletic    | 55,611  | 1,027 | 253      | 0.3277     | 0.70      | NO        |
| Shaka Hislop on Spurs relegation      | 56,672  | 570   | 172      | 0.2580     | 0.60      | NO        |
 
**Spearman rank correlation: 0.2733** (p-value: 0.0 which is statistically significant at n=294)  
**is_trending agreement: 288/294 (97.96%)**
 
**Assessment:** The high agreement rate (98%) is misleading because it reflects the fact that both approaches classify most videos as non-trending, so they agree by default.
The Spearman correlation of 0.27 reveals that the two approaches rank content quite differently. The 6 disagreements are the most informative cases. There are quite a few 
false positives from the LLM taking into account certain names like Arsenal and inflating the videos trending score based on that. Additionally, the LLM incorrectly assumes
content is out of date. Overall, the weighted scorer is the most accurate as long as we introduce a content/duration filter and lower the trending threshold from 0.55 to 0.40
before proceeding to score new content. The LLM approach has too much risk of hallucinating trending content, so it is not recommended for production use.

---

## 9. LLM Claims Layer Status

As of week 9, `comment_quality` in the algorithmic scorer has been replaced by `trends.mention_count` which is the claim frequency per narrative within a time window.

---

## 10. Inconsistencies & Cross-Team Feedback

| # | Finding                                                                       | Severity | Team    | Action                                                                      | Complete?       |
|---|-------------------------------------------------------------------------------|----------|---------|-----------------------------------------------------------------------------|-----------------|
| 1 | `league` and `teams` fields are `null` for all videos in DB                   | High     | Backend | Populate during ingestion pipeline                                          | Yes (end of W9) |
| 2 | Non-soccer and short-form clips passing through ingestion inflate algo scores | High     | Backend | Add `duration_seconds >= X` filter and soccer content check during scraping | Yes             |
| 3 | LLM penalizes videos dated after its training cutoff as outdated              | Medium   | DS      | Pass current run date explicitly in system prompt to fix recency evaluation | Yes             |

---

## 11. Recommendations

**Recommendation 1 — Lower trending threshold from 0.55 to 0.40 (COMPLETE):**  
Based on the benchmark results, legitimate high-profile UCL and Premier League matches (Galatasaray vs. Liverpool, 0.41) fall just below the current threshold. 
Lowering to 0.40 captures these without significantly increasing false positives given the current score distribution.
 
**Recommendation 2 — Add duration and content-type filter to the ingestion pipeline (COMPLETE):**  
The "It's never too late for success" false positive demonstrates that non-soccer short clips can top the algo rankings. A `duration_seconds >= X` filter and a soccer 
keyword check during ingestion will address this upstream before scoring runs.
 
**Recommendation 3 — Proceed with weighted algo as primary scorer (COMPLETE):**  
Based on manual analysis of disagreements, the weighted algo produces more accurate trending classifications than the LLM for this dataset. The LLM over-scores content based 
on team/player name recognition rather than actual engagement signals. The LLM approach is not recommended for production use in its current form without prompt 
improvements to address date context and popularity bias.

---

## 12. Repo Files Referenced
| File                               | Description                        |
|------------------------------------|------------------------------------|
| `trend_scoring_weighted.py`        | Weighted scoring algorithm         |
| `trend_scoring_llm.py`             | LLM-based scoring                  |
| `benchmark.py`                     | Benchmarking and comparison script |
| `filtered_videos.json`             | Source video metadata              |
| `youtubeComments.json`             | Source comment data                |
| `weighted_algorithmic_scores.json` | Output from weighted scorer        |
| `llm_scores.json`                  | Output from LLM scorer             |
| `benchmark_report.json`            | Final benchmark comparison output  |
 
---

## 13. Final 0.40 Threshold Validation & Weight Configurations

**Date:** 4/16/2026  
**Scorer Version:** trend_scoring_weighted.py (optimized with batch processing + caching via PR 39)  
**Validation Method:** Manual review of 5 diverse videos with mention_scores  

---

### Manual Video Review Results

#### Video 1: Colombia vs. France EXTENDED HIGHLIGHTS [March 29, 2026] | Full Game Highlights | ESPN FC
| Metric                | Value      | Analysis                                                                                                     |
|-----------------------|------------|--------------------------------------------------------------------------------------------------------------|
| **Trend Score**       | 0.2691     | Below threshold despite strong mention and recency signals                                                   |
| **League**            | -          | International match content so no league                                                                     |
| **Views**             | 66813      | Solid views but not 100k+                                                                                    |
| **Engagement Rate**   | 0.0504     | Very low engagement rate                                                                                     |
| **Recency Score**     | 0.4572     | Penalized for being a bit older, recency working as intended                                                 |
| **Mention Score**     | 0.458      | Highest observed mention_score                                                                               |
| **Views Normalized**  | 0.1515     | Moderate views                                                                                               |
| **Publish Date**      | 2026-03-30 | Outside peak recency window                                                                                  |
| **Manual Assessment** | -          | High narrative relevance but correctly deemed not trending due to low engagement and moderate recency scores |

**Component Analysis:**
- Engagement rate: Very weak, limits trend potential  
- Recency: Major penalty, but working as intended  
- Mention score: Extremely strong signal (likely narrative-heavy, international match)  
- Views: Moderate support, view normalization is good  

---

#### Video 2: Germany vs. Ghana Reaction: Why is Florian Wirtz playing better with the national team? | ESPN FC
| Metric                | Value      | Analysis                                                                             |
|-----------------------|------------|--------------------------------------------------------------------------------------|
| **Trend Score**       | 0.2645     | Below trending threshold due to low engagement and views                             |
| **League**            | -          | Reaction/discussion surrounding international matches                                |
| **Views**             | 23,686     | Moderate to low view count                                                           |
| **Engagement Rate**   | 0.1853     | Good engagement rate                                                                 |
| **Recency Score**     | 0.4693     | Penalized for being a bit older, recency working as intended                         |
| **Mention Score**     | 0.26       | High mention score, shows component is working as intended and valid                 |
| **Views Normalized**  | 0.0457     | Low view count                                                                       |
| **Publish Date**      | 2026-03-30 | Outside peak recency window                                                          |
| **Manual Assessment** | -          | Strong discussion signal but not broadly trending in regards to engagement and views |

**Component Analysis:**
- Engagement rate: Strong and score accurately reflects that  
- Recency: Holding it back, would increase trend potential if more recent  
- Mention score: Clearly impactful and valid, contributes well to composite score  
- Views: Too low to push over trending threshold  

---

#### Video 3: Ranking 2026 World Cup FAVORITES
| Metric                | Value      | Analysis                                                                                                                       |
|-----------------------|------------|--------------------------------------------------------------------------------------------------------------------------------|
| **Trend Score**       | 0.3143     | Below threshold mostly due to views, but very near-trending                                                                    |
| **League**            | -          | Broad narrative international topic                                                                                            |
| **Views**             | 7,137      | Very low view count but still >5000 as required                                                                                |
| **Engagement Rate**   | 0.3209     | Very strong engagement rate                                                                                                    |
| **Recency Score**     | 0.468      | Penalized for being a bit older, recency working as intended                                                                   |
| **Mention Score**     | 0.304      | High mention score, component is working with the given ceiling, might need to lower to capture top half of range consistently |
| **Views Normalized**  | 0.0051     | Very low normalized view count, main reason it is not classified as trending                                                   |
| **Publish Date**      | 2026-03-30 | Outside peak recency window                                                                                                    |
| **Manual Assessment** | -          | High narrative and engagement but limited by viewership component                                                              |

**Component Analysis:**
- Engagement rate: Excellent engagement rate  
- Recency: Weaker score due to being ~2 weeks old, recency still working great at current calibration  
- Mention score: Strong narrative driver, can reduce ceiling down to capture the top half of the range (consider 300?)  
- Views: Main limiting factor as to why it is not trending  

---

#### Video 4: BOSNIA QUALIFY FOR THE 2026 FIFA WORLD CUP | Italy Misses Third Consecutive World Cup...
| Metric                | Value      | Analysis                                                                                                                   |
|-----------------------|------------|----------------------------------------------------------------------------------------------------------------------------|
| **Trend Score**       | 0.3136     | Below threshold mostly due to views, but very near-trending                                                                |
| **League**            | -          | Broad narrative international topic                                                                                        |
| **Views**             | 20,982     | Moderate view count                                                                                                        |
| **Engagement Rate**   | 0.377      | Very strong engagement rate                                                                                                |
| **Recency Score**     | 0.5033     | Penalized for being a bit older, recency working as intended                                                               |
| **Mention Score**     | 0.124      | Moderate mention score, component is working with the given ceiling, another candidate for benefiting from a lower ceiling |
| **Views Normalized**  | 0.0391     | Very low normalized view count, main reason it is not classified as trending                                               |
| **Publish Date**      | 2026-03-31 | Outside peak recency window                                                                                                |
| **Manual Assessment** | -          | Strong candidate, borderline trending video                                                                                |

**Component Analysis:**
- Engagement rate: Excellent engagement rate  
- Recency: Weaker score due to being ~2 weeks old, recency still working great at current calibration  
- Mention score: Meaningful mention score but not dominant, would benefit from lower ceiling as well  
- Views: Not high enough to be considered trending  

---

#### Video 5: Scotland vs. Ivory Coast | Full Game Highlights | ESPN FC
| Metric                | Value      | Analysis                                                                                                                   |
|-----------------------|------------|----------------------------------------------------------------------------------------------------------------------------|
| **Trend Score**       | 0.2743     | Below threshold mostly due to engagement rate and moderate narrative buzz, but very near-trending due to views             |
| **League**            | -          | Broad narrative international topic                                                                                        |
| **Views**             | 152,437    | High view count                                                                                                            |
| **Engagement Rate**   | 0.1299     | Moderate engagement rate, reflects appropriately                                                                           |
| **Recency Score**     | 0.5008     | Penalized for being a bit older, recency working as intended                                                               |
| **Mention Score**     | 0.122      | Moderate mention score, component is working with the given ceiling, another candidate for benefiting from a lower ceiling |
| **Views Normalized**  | 0.3615     | Strong view count, primary trending driver                                                                                 |
| **Publish Date**      | 2026-03-31 | Outside peak recency window                                                                                                |
| **Manual Assessment** | -          | Strong reach, but has a weaker narrative signal and engagement rate lowering composite score                               |

**Component Analysis:**
- Engagement rate: Decent rate but could be better, score is accurate and reflects well in pipeline  
- Recency: Weaker score due to being ~2 weeks old, recency still working great at current calibration  
- Mention score: Meaningful mention score but not dominant, would benefit from lower ceiling as well  
- Views: Primary driver behind videos push to be classified as trending  

---

### Key Takeaways
- Mention score clearly differentiates narrative-heavy content (rankings, reactions, previews) from pure highlights  
- However, mention score alone is not sufficient to push videos above 0.40  
  - The system is behaving correctly:  
      - Narrative videos = high mention, lower views → near-trending but not trending unless views/engagement tick up  
      - Match highlights = high views, low mention → trending  

--- 
### Final Production Weight Configuration

#### Approved Parameters

| Parameter                 | Value     | Justification                                                                                                            |
|---------------------------|-----------|--------------------------------------------------------------------------------------------------------------------------|
| **TRENDING_THRESHOLD**    | 0.40      | Captures high-profile matches and excludes niche narrative content unless high view count and engagement rate is present |
| **ENGAGEMENT_CEILING**    | 0.08 (8%) | Typical soccer engagement is 0.5-5% so we lowered it from 10% -> 8% to prevent viral outliers from dominating            |
| **RECENCY_WINDOW_DAYS**   | 30        | Balances fresh content priority with long-tail video discovery, still appropriate based on observed decay                |
| **MENTION_COUNT_CEILING** | 250       | Based on observed max (~230), this provides headroom without compressing distribution                                    |
| **BATCH_SIZE**            | 1000      | Optimal for memory efficiency on 10K+ video datasets, can be considered for future calibrations when dataset grows       |

#### Approved Component Weights

| Component            | Weight | Justification                                             |
|----------------------|--------|-----------------------------------------------------------|
| **engagement_rate**  | 0.35   | Primary signal of audience interest quality               |
| **recency_score**    | 0.30   | Time-sensitivity critical for trending classification     |
| **mention_score**    | 0.20   | Captures narrative resonance through claim pipeline       |
| **views_normalized** | 0.15   | Relative popularity without over-weighting viral outliers |

---

### Recommended Recalibration Schedule

| Frequency     | Trigger                     | Actions                                                   |
|---------------|-----------------------------|-----------------------------------------------------------|
| **Weekly**    | After orchestrator runs     | Review top 10 trending videos for obvious false positives |
| **Monthly**   | Dataset grows significantly | Re-run sensitivity analysis on thresholds/ceilings        |
| **Quarterly** | Major pipeline changes      | Full manual review of 20+ boundary videos                 |

---