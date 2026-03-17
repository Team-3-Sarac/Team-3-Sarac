"""
Benchmarks weighted algorithmic scorer vs LLM scorer

Input:
    1. weighted_algorithmic_scores.json (output from trend_scoring_weighted.py)
    2. llm_scores.json (output from trend_scoring_llm.py)

Output:
    1. benchmark_report.json written to OUTPUT_PATH
"""

import json
from pathlib import Path
from scipy.stats import spearmanr

BASE_DIR     = Path(__file__).resolve().parent.parent
ALGO_PATH    = BASE_DIR / "data" / "weighted_algorithmic_scores.json"
LLM_PATH     = BASE_DIR / "data" / "llm_scores.json"
OUTPUT_PATH  = BASE_DIR / "data" / "benchmark_report.json"

# Loads both score files and returns dicts keyed by video_id
def load_scores() -> tuple[dict, dict]:
    with open(ALGO_PATH, "r", encoding="utf-8") as f:
        algo_list = json.load(f)
    with open(LLM_PATH, "r", encoding="utf-8") as f:
        llm_list = json.load(f)

    algo_by_id = {r["video_id"]: r for r in algo_list}
    llm_by_id  = {r["video_id"]: r for r in llm_list}
    return algo_by_id, llm_by_id

# Computes Spearman rank correlation between algo and LLM scores on shared videos
def compute_rank_correlation(algo_scores: list, llm_scores: list) -> tuple[float, float]:
    corr, pvalue = spearmanr(algo_scores, llm_scores)
    return round(float(corr), 4), round(float(pvalue), 4)

# Returns list of videos where is_trending classification differs
def find_disagreements(common_ids: list, algo_by_id: dict, llm_by_id: dict) -> list[dict]:
    disagreements = []
    for vid in common_ids:
        a = algo_by_id[vid]
        l = llm_by_id[vid]
        if a["is_trending"] != l["is_trending"]:
            disagreements.append({
                "video_id":        vid,
                "title":           a["title"],
                "algo_score":      a["trend_score"],
                "algo_trending":   a["is_trending"],
                "llm_score":       l["llm_trend_score"],
                "llm_trending":    l["is_trending"],
                "llm_reasoning":   l.get("reasoning", ""),
            })
    return disagreements

# Builds full ranked side-by-side comparison table sorted by algo score to further analyze
def build_comparison_table(common_ids: list, algo_by_id: dict, llm_by_id: dict) -> list[dict]:
    table = []
    for vid in sorted(common_ids, key=lambda v: algo_by_id[v]["trend_score"], reverse=True):
        a = algo_by_id[vid]
        l = llm_by_id[vid]
        table.append({
            "video_id":      vid,
            "title":         a["title"],
            "view_count":    a["view_count"],
            "like_count":    a["like_count"],
            "comment_count": a["comment_count"],
            "algo_score":    a["trend_score"],
            "llm_score":     l["llm_trend_score"],
            "algo_trending": a["is_trending"],
            "llm_trending":  l["is_trending"],
            "agreement":     a["is_trending"] == l["is_trending"],
            "llm_reasoning": l.get("reasoning", ""),
        })
    return table

# Main entry point of script to load data, compute correlation, and write output
def run_benchmark() -> dict:
    print("-- Benchmark: Weighted vs. LLM Trend Scorer --\n")

    algo_by_id, llm_by_id = load_scores()
    common_ids = [vid for vid in algo_by_id if vid in llm_by_id]
    print(f"  Videos in both datasets: {len(common_ids)}")

    algo_scores = [algo_by_id[vid]["trend_score"]    for vid in common_ids]
    llm_scores  = [llm_by_id[vid]["llm_trend_score"] for vid in common_ids]
    algo_trend  = [algo_by_id[vid]["is_trending"]     for vid in common_ids]
    llm_trend   = [llm_by_id[vid]["is_trending"]      for vid in common_ids]

    # Spearman rank correlation
    corr, pvalue = compute_rank_correlation(algo_scores, llm_scores)
    print(f"  Spearman rank correlation: {corr}  (p-value: {pvalue})")

    # Classification agreement
    agreements     = sum(1 for a, l in zip(algo_trend, llm_trend) if a == l)
    agreement_rate = round(agreements / len(common_ids), 4)
    print(f"  is_trending agreement:     {agreements}/{len(common_ids)} ({agreement_rate:.1%})")

    # Disagreements
    disagreements = find_disagreements(common_ids, algo_by_id, llm_by_id)
    print(f"  Disagreements:             {len(disagreements)}")

    # Full comparison table
    comparison_table = build_comparison_table(common_ids, algo_by_id, llm_by_id)

    report = {
        "summary": {
            "videos_compared":      len(common_ids),
            "spearman_correlation":  corr,
            "p_value":               pvalue,
            "agreement_count":       agreements,
            "agreement_rate":        agreement_rate,
            "disagreement_count":    len(disagreements),
            "algo_trending_count":   sum(algo_trend),
            "llm_trending_count":    sum(llm_trend),
        },
        "disagreements":   disagreements,
        "comparison_table": comparison_table,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    print(f"\n  Report written to {OUTPUT_PATH}")

    print("\n-- Disagreements --")
    for d in disagreements:
        print(f"  {d['title'][:60]}")
        print(f"    Algo: {d['algo_score']} trending={d['algo_trending']}")
        print(f"    LLM:  {d['llm_score']} trending={d['llm_trending']}")

    return report

if __name__ == "__main__":
    run_benchmark()