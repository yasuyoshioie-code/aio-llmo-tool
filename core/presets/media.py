"""メディア/ブログ向けプリセット — 既存の診断ロジックをラップ"""

from core.scorer import (
    calculate_technical_scores, merge_all_scores,
    calculate_category_totals, calculate_total,
)
from core.content_scorer import (
    analyze_content_python, analyze_eeat_python,
    generate_improvements_python, generate_test_queries_python,
)


PRESET_ID = "media"
PRESET_LABEL = "📰 メディア/ブログ"


def score_page(structure, robots, llms, pagespeed, sitemap):
    """ページを評価して all_scores / categories / total を返す。"""
    technical_scores = calculate_technical_scores(structure, robots, llms, pagespeed, sitemap)
    content_citation = analyze_content_python(structure.get("content_text", ""), structure)
    eeat_scores = analyze_eeat_python(structure.get("content_text", ""), structure)
    all_scores = merge_all_scores(technical_scores, content_citation, eeat_scores)

    faq_count = len(structure.get("faq_items", []))
    if faq_count >= 5: faq_score = 4
    elif faq_count >= 1: faq_score = 2
    else: faq_score = 0
    all_scores["1-3_faq"] = {
        "score": faq_score, "max": 4,
        "reason": f"FAQ {faq_count}件検出",
        "method": "HTML実測", "confidence": "高",
    }

    categories = calculate_category_totals(all_scores)
    total = calculate_total(categories)
    return all_scores, categories, total


def generate_improvements(all_scores, structure, url, competitors=None, comparison=None):
    return generate_improvements_python(
        all_scores, structure, url,
        competitors=competitors, comparison=comparison,
    )


def generate_test_queries(url, keywords, site_title):
    return generate_test_queries_python(url, keywords, site_title)
