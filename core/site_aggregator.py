"""ページ単位診断結果をサイト全体で集計するモジュール。

出力:
  - site_scores: サイト全体の平均スコア・Grade
  - page_results: 各ページの詳細結果
  - worst_pages / best_pages: ランキング
  - common_issues: 全ページ共通の問題（= サイト全体施策）
  - score_distribution: スコア分布（ヒストグラム用）
"""

import statistics


def aggregate_site_results(page_results: list[dict]) -> dict:
    """ページ単位の結果リストから、サイト全体集計を生成。

    page_results各要素:
      {
        "url": str, "type": str, "title": str,
        "total": dict (total, grade),
        "categories": dict,
        "all_scores": dict,
        "structure": dict,
      }
    """
    if not page_results:
        return {"error": "no pages analyzed"}

    totals = [p["total"]["total"] for p in page_results]

    # サイト全体スコア
    site_score = round(statistics.mean(totals))
    if site_score >= 80: site_grade = "S"
    elif site_score >= 65: site_grade = "A"
    elif site_score >= 50: site_grade = "B"
    elif site_score >= 35: site_grade = "C"
    else: site_grade = "D"

    # カテゴリ別平均
    cat_aggregates: dict = {}
    for p in page_results:
        for ckey, cval in p.get("categories", {}).items():
            if ckey not in cat_aggregates:
                cat_aggregates[ckey] = {
                    "label": cval.get("label", ckey),
                    "scores": [],
                    "max": cval.get("max", 0),
                }
            cat_aggregates[ckey]["scores"].append(cval.get("score", 0))

    cat_avgs: dict = {}
    for ckey, agg in cat_aggregates.items():
        avg = statistics.mean(agg["scores"]) if agg["scores"] else 0
        cat_avgs[ckey] = {
            "label": agg["label"],
            "score": round(avg, 1),
            "max": agg["max"],
            "pct": round(avg / agg["max"] * 100) if agg["max"] else 0,
            "median": round(statistics.median(agg["scores"]), 1) if agg["scores"] else 0,
            "min": min(agg["scores"]) if agg["scores"] else 0,
            "max_observed": max(agg["scores"]) if agg["scores"] else 0,
        }

    # 項目別実施率（30項目それぞれ、何%のページでフル得点か）
    item_coverage: dict = {}
    for p in page_results:
        for ikey, ival in p.get("all_scores", {}).items():
            if ikey not in item_coverage:
                item_coverage[ikey] = {
                    "scores": [],
                    "max": ival.get("max", 0),
                    "reason_samples": [],
                }
            item_coverage[ikey]["scores"].append(ival.get("score", 0))
            if len(item_coverage[ikey]["reason_samples"]) < 3:
                item_coverage[ikey]["reason_samples"].append(ival.get("reason", ""))

    item_stats: dict = {}
    for ikey, d in item_coverage.items():
        scores = d["scores"]
        max_val = d["max"]
        if not scores or not max_val:
            continue
        avg = statistics.mean(scores)
        full_count = sum(1 for s in scores if s >= max_val * 0.9)
        zero_count = sum(1 for s in scores if s <= max_val * 0.1)
        item_stats[ikey] = {
            "avg_score": round(avg, 1),
            "max": max_val,
            "avg_pct": round(avg / max_val * 100) if max_val else 0,
            "full_coverage_pct": round(full_count / len(scores) * 100),  # フル得点ページ率
            "failure_pct": round(zero_count / len(scores) * 100),  # 未実装ページ率
            "sample_reasons": d["reason_samples"],
        }

    # 共通問題（全ページで80%以上が未実装 or 低得点）
    common_issues = []
    for ikey, stat in item_stats.items():
        if stat["failure_pct"] >= 50:
            common_issues.append({
                "item_key": ikey,
                "failure_pct": stat["failure_pct"],
                "avg_pct": stat["avg_pct"],
                "sample_reasons": stat["sample_reasons"],
            })
    common_issues.sort(key=lambda x: -x["failure_pct"])

    # ワースト/ベストページ
    sorted_pages = sorted(page_results, key=lambda p: p["total"]["total"])
    worst_pages = [{
        "url": p["url"],
        "title": p.get("title", "")[:60],
        "type": p.get("type", ""),
        "score": p["total"]["total"],
        "grade": p["total"].get("grade", "-"),
    } for p in sorted_pages[:10]]

    best_pages = [{
        "url": p["url"],
        "title": p.get("title", "")[:60],
        "type": p.get("type", ""),
        "score": p["total"]["total"],
        "grade": p["total"].get("grade", "-"),
    } for p in sorted_pages[-10:][::-1]]

    # スコア分布
    buckets = {"D(0-34)": 0, "C(35-49)": 0, "B(50-64)": 0, "A(65-79)": 0, "S(80+)": 0}
    for t in totals:
        if t >= 80: buckets["S(80+)"] += 1
        elif t >= 65: buckets["A(65-79)"] += 1
        elif t >= 50: buckets["B(50-64)"] += 1
        elif t >= 35: buckets["C(35-49)"] += 1
        else: buckets["D(0-34)"] += 1

    # タイプ別集計
    type_stats: dict = {}
    for p in page_results:
        ptype = p.get("type", "unknown")
        if ptype not in type_stats:
            type_stats[ptype] = {"count": 0, "scores": []}
        type_stats[ptype]["count"] += 1
        type_stats[ptype]["scores"].append(p["total"]["total"])

    for ptype, d in type_stats.items():
        d["avg_score"] = round(statistics.mean(d["scores"])) if d["scores"] else 0

    return {
        "page_count": len(page_results),
        "site_score": site_score,
        "site_grade": site_grade,
        "score_mean": round(statistics.mean(totals), 1),
        "score_median": round(statistics.median(totals), 1),
        "score_stdev": round(statistics.stdev(totals), 1) if len(totals) > 1 else 0,
        "score_min": min(totals),
        "score_max": max(totals),
        "category_averages": cat_avgs,
        "item_stats": item_stats,
        "common_issues": common_issues,
        "worst_pages": worst_pages,
        "best_pages": best_pages,
        "score_distribution": buckets,
        "type_stats": type_stats,
    }
