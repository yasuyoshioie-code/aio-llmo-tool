"""競合分析モジュール — 深度分析バージョン

抽出項目（競合1サイトあたり30+項目）:
  【基本】URL、タイトル、meta description、canonical、OGP
  【規模】文字数、段落数、H1〜H4数、画像数、リスト数、テーブル数
  【情報密度】数値データ数、箇条書き密度、テーブル密度、段落平均文字数
  【AIO構造】Answer-first定義文、FAQ数、結論先出しパターン
  【構造化データ】JSON-LD全型リスト、Article/FAQ/HowTo/Organization有無
  【E-E-A-T】著者名/プロフィールリンク、運営者情報、一次情報リンク比率
  【鮮度】公開日、更新日、経過日数
  【リンク構造】内部リンク数、外部リンク数、参考文献数
  【可読性】平均段落文字数、平均文長、漢字比率
  【トピックカバレッジ】使用キーワード、独自語彙
  【総合】スコア、Grade、強み、弱み
"""

import re
from datetime import datetime
from urllib.parse import urlparse, urljoin

from core.fetcher import search_web, fetch_page
from core.parser import parse_html, parse_from_markdown
from core.technical import check_structured_data_coverage


FALLBACK_MAJOR_DOMAINS = [
    "note.com", "qiita.com", "zenn.dev", "hatenablog.com",
    "wikipedia.org", "weblio.jp",
]


def _generate_query_variations(keywords: list[str]) -> list[str]:
    variations = list(keywords)
    for kw in keywords:
        tokens = re.split(r"[\s　]+", kw)
        if len(tokens) >= 2:
            variations.append(tokens[0])
            variations.append(" ".join(tokens[:2]))
        if len(kw) <= 15:
            variations.append(f"{kw} とは")
            variations.append(f"{kw} おすすめ")
            variations.append(f"{kw} 比較")
    seen = set()
    out = []
    for v in variations:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def find_competitors(
    keywords: list[str],
    tavily_key: str,
    self_domain: str,
    max_competitors: int = 3,
) -> list[dict]:
    """キーワード検索で競合サイトを特定。必ずmax_competitors社を返す。"""
    domain_scores: dict[str, dict] = {}

    def _add_result(r: dict, rank: int):
        domain = urlparse(r["url"]).netloc
        if not domain or domain == self_domain:
            return
        if domain not in domain_scores:
            domain_scores[domain] = {
                "domain": domain,
                "urls": [],
                "appearances": 0,
                "best_rank": 99,
                "title": r.get("title", ""),
                "search_query": "",
            }
        domain_scores[domain]["appearances"] += 1
        domain_scores[domain]["best_rank"] = min(
            domain_scores[domain]["best_rank"], rank
        )
        if r["url"] not in domain_scores[domain]["urls"]:
            domain_scores[domain]["urls"].append(r["url"])

    for kw in keywords[:3]:
        results = search_web(kw, tavily_key, max_results=10)
        for i, r in enumerate(results):
            _add_result(r, i + 1)
            if domain_scores.get(urlparse(r["url"]).netloc):
                domain_scores[urlparse(r["url"]).netloc]["search_query"] = kw

    if len(domain_scores) < max_competitors:
        variations = _generate_query_variations(keywords)
        for vq in variations:
            if len(domain_scores) >= max_competitors * 2:
                break
            results = search_web(vq, tavily_key, max_results=8)
            for i, r in enumerate(results):
                _add_result(r, i + 1)

    ranked = sorted(
        domain_scores.values(),
        key=lambda x: (-x["appearances"], x["best_rank"]),
    )

    if len(ranked) < max_competitors:
        existing_domains = {d["domain"] for d in ranked}
        for fallback in FALLBACK_MAJOR_DOMAINS:
            if len(ranked) >= max_competitors:
                break
            if fallback in existing_domains or fallback == self_domain:
                continue
            for kw in keywords[:2]:
                results = search_web(f"site:{fallback} {kw}", tavily_key, max_results=3)
                if results:
                    ranked.append({
                        "domain": fallback,
                        "urls": [results[0]["url"]],
                        "appearances": 1,
                        "best_rank": 99,
                        "title": results[0].get("title", ""),
                        "search_query": kw,
                        "is_fallback": True,
                    })
                    existing_domains.add(fallback)
                    break

    return ranked[:max_competitors]


def _days_since(date_str: str) -> int | None:
    """ISO日付から経過日数を計算。"""
    if not date_str:
        return None
    try:
        # "2024-01-15" or "2024-01-15T..." or "2024/01/15"
        s = date_str.replace("/", "-")[:10]
        dt = datetime.fromisoformat(s)
        return (datetime.now() - dt).days
    except Exception:
        return None


def _count_numbers(text: str) -> int:
    """数値データの出現回数。"""
    return len(re.findall(r"\d+[,.]\d+|\d{2,}(?:万|億|円|%|％|年|月|日|時間|分|人|件|位)?", text))


def _count_reference_links(raw_html: str) -> int:
    """出典・参考文献リンク数（rel=nofollow除く外部リンク）。"""
    if not raw_html:
        return 0
    # 出典・参考・source・reference 近傍のaタグ
    pattern = r'(?:出典|参考|参照|ソース|reference|source)[^<]{0,100}<a\s[^>]*href="(https?://[^"]+)"'
    return len(re.findall(pattern, raw_html, re.IGNORECASE))


def _kanji_ratio(text: str) -> float:
    """漢字比率（読みやすさ指標）。"""
    if not text:
        return 0.0
    total = len(text)
    kanji = len(re.findall(r"[\u4e00-\u9fff]", text))
    return round(kanji / total, 3) if total else 0.0


def _avg_sentence_length(text: str) -> int:
    """平均文長（句点で分割）。"""
    sentences = [s for s in re.split(r"[。！？]", text) if s.strip()]
    if not sentences:
        return 0
    return int(sum(len(s) for s in sentences) / len(sentences))


def _avg_paragraph_length(text: str, paragraph_count: int) -> int:
    if not paragraph_count:
        return 0
    return int(len(text) / paragraph_count)


def _detect_primary_entities(text: str, top_n: int = 5) -> list[str]:
    """頻出語彙（3文字以上のカタカナ/漢字連続）。"""
    if not text:
        return []
    candidates = re.findall(r"[ァ-ヴー]{3,}|[一-龥]{3,}", text[:5000])
    freq: dict[str, int] = {}
    for c in candidates:
        freq[c] = freq.get(c, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in ranked[:top_n] if freq[w] >= 2]


def _count_links(raw_html: str, self_domain: str) -> tuple[int, int]:
    """内部リンク数・外部リンク数をカウント。"""
    if not raw_html:
        return 0, 0
    links = re.findall(r'<a\s[^>]*href="([^"]+)"', raw_html)
    internal = 0
    external = 0
    for href in links:
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        if href.startswith("http"):
            domain = urlparse(href).netloc
            if domain == self_domain:
                internal += 1
            else:
                external += 1
        else:
            internal += 1
    return internal, external


def _has_answer_first(text: str) -> tuple[bool, str]:
    """冒頭200字に定義文パターンがあるか。"""
    first_200 = text[:200]
    patterns = [
        (r"[^\s]{1,30}とは[、，]?\s*[^\s]{5,100}[で|だ|です|である]", "定義文"),
        (r"結論[、，:：]?\s*[^\s]{5,100}", "結論先出し"),
        (r"^[^\s]{1,30}は[、，]?\s*[^\s]{5,100}[で|だ|です|である]", "主題説明"),
    ]
    for pat, label in patterns:
        if re.search(pat, first_200):
            return True, label
    return False, ""


def analyze_competitor(url: str, tavily_key: str) -> dict:
    """競合1サイトの深度分析。30+項目を抽出。"""
    page = fetch_page(url, tavily_key)
    raw_html = page.get("raw_html", "")

    structure = None
    if raw_html:
        try:
            structure = parse_html(raw_html)
        except Exception:
            structure = None
    if not structure and page.get("content"):
        try:
            structure = parse_from_markdown(page["content"])
        except Exception:
            structure = None
    if not structure:
        structure = {
            "title": urlparse(url).netloc,
            "meta_description": "",
            "canonical": "",
            "ogp": {},
            "content_text": "",
            "word_count": 0,
            "paragraph_count": 0,
            "headings": [],
            "heading_issues": [],
            "faq_items": [],
            "jsonld": [],
            "author": {},
            "dates": {},
            "table_count": 0,
            "list_count": 0,
            "images_without_alt": 0,
        }

    sd_coverage = check_structured_data_coverage(structure.get("jsonld", []))
    content_text = structure.get("content_text", "")
    self_domain = urlparse(url).netloc

    # === 規模指標 ===
    headings = structure.get("headings", [])
    h1_count = sum(1 for h in headings if h.get("level") == 1)
    h2_count = sum(1 for h in headings if h.get("level") == 2)
    h3_count = sum(1 for h in headings if h.get("level") == 3)
    h4_count = sum(1 for h in headings if h.get("level") == 4)

    # === 情報密度 ===
    number_count = _count_numbers(content_text)
    list_count = structure.get("list_count", 0)
    table_count = structure.get("table_count", 0)
    paragraph_count = structure.get("paragraph_count", 0)
    word_count = structure.get("word_count", 0)

    # 1000文字あたりの数値密度
    number_density = round(number_count / word_count * 1000, 1) if word_count else 0
    # 1000文字あたりの箇条書き密度
    list_density = round(list_count / word_count * 1000, 2) if word_count else 0

    # === AIO構造 ===
    af_ok, af_type = _has_answer_first(content_text)
    faq_items = structure.get("faq_items", [])

    # === E-E-A-T ===
    author = structure.get("author", {})
    ref_link_count = _count_reference_links(raw_html)

    # === 鮮度 ===
    dates = structure.get("dates", {})
    days_since_published = _days_since(dates.get("published", ""))
    days_since_modified = _days_since(dates.get("modified", ""))

    # === リンク ===
    internal_links, external_links = _count_links(raw_html, self_domain)

    # === 可読性 ===
    avg_sent = _avg_sentence_length(content_text)
    avg_para = _avg_paragraph_length(content_text, paragraph_count)
    kanji_r = _kanji_ratio(content_text)

    # === トピック ===
    entities = _detect_primary_entities(content_text)

    # === 採点（0-2の3段階×10項目=20点満点） ===
    scores = {}
    scores["answer_first"] = 2 if af_ok else (1 if content_text[:200] else 0)
    scores["heading_structure"] = 2 if headings and not structure.get("heading_issues") else (1 if headings else 0)
    scores["faq"] = 2 if len(faq_items) >= 5 else (1 if faq_items else 0)
    sd_found_count = sum(1 for v in sd_coverage.values() if v is True)
    scores["structured_data"] = 2 if sd_found_count >= 3 else (1 if sd_found_count >= 1 else 0)
    scores["author"] = 2 if author.get("name") and author.get("url") else (1 if author.get("name") else 0)
    scores["freshness"] = 2 if dates.get("modified") else (1 if dates.get("published") else 0)
    scores["numeric_data"] = 2 if number_count >= 10 else (1 if number_count >= 3 else 0)
    scores["lists_tables"] = 2 if table_count >= 1 and list_count >= 3 else (1 if list_count or table_count else 0)
    scores["depth"] = 2 if word_count >= 3000 else (1 if word_count >= 1500 else 0)
    scores["references"] = 2 if ref_link_count >= 3 or external_links >= 5 else (1 if external_links >= 1 else 0)

    total = sum(scores.values())
    max_total = len(scores) * 2
    score_pct = round(total / max_total * 100) if max_total else 0

    # === Grade判定 ===
    if score_pct >= 85:
        grade = "S"
    elif score_pct >= 70:
        grade = "A"
    elif score_pct >= 55:
        grade = "B"
    elif score_pct >= 40:
        grade = "C"
    else:
        grade = "D"

    # === 強み/弱みサマリ ===
    strengths = []
    weaknesses = []
    item_labels = {
        "answer_first": "Answer-first構造",
        "heading_structure": "見出し構造",
        "faq": "FAQ",
        "structured_data": "構造化データ",
        "author": "著者情報",
        "freshness": "鮮度",
        "numeric_data": "数値データ",
        "lists_tables": "リスト/テーブル",
        "depth": "コンテンツ深度",
        "references": "参考文献",
    }
    for k, v in scores.items():
        if v == 2:
            strengths.append(item_labels.get(k, k))
        elif v == 0:
            weaknesses.append(item_labels.get(k, k))

    found_types = sd_coverage.get("found_types", [])

    return {
        # 基本
        "url": url,
        "domain": self_domain,
        "title": structure.get("title", "") or self_domain,
        "meta_description": structure.get("meta_description", ""),
        "canonical": structure.get("canonical", ""),
        "has_ogp": bool(structure.get("ogp", {}).get("title")),
        # 規模
        "word_count": word_count,
        "paragraph_count": paragraph_count,
        "h1_count": h1_count,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "h4_count": h4_count,
        "list_count": list_count,
        "table_count": table_count,
        "images_without_alt": structure.get("images_without_alt", 0),
        # 情報密度
        "number_count": number_count,
        "number_density_per1k": number_density,
        "list_density_per1k": list_density,
        # AIO構造
        "has_answer_first": af_ok,
        "answer_first_type": af_type,
        "faq_count": len(faq_items),
        # 構造化データ
        "sd_types": found_types if found_types else ["未実装"],
        "sd_count": sd_found_count,
        "has_article_schema": sd_coverage.get("Article", False),
        "has_faq_schema": sd_coverage.get("FAQPage", False),
        "has_howto_schema": sd_coverage.get("HowTo", False),
        "has_organization_schema": sd_coverage.get("Organization", False),
        "has_breadcrumb_schema": sd_coverage.get("BreadcrumbList", False),
        # E-E-A-T
        "has_author": bool(author.get("name")),
        "author_name": author.get("name", ""),
        "has_author_profile": bool(author.get("url")),
        "reference_link_count": ref_link_count,
        # 鮮度
        "published_date": dates.get("published", ""),
        "modified_date": dates.get("modified", ""),
        "days_since_published": days_since_published,
        "days_since_modified": days_since_modified,
        # リンク
        "internal_link_count": internal_links,
        "external_link_count": external_links,
        # 可読性
        "avg_sentence_length": avg_sent,
        "avg_paragraph_length": avg_para,
        "kanji_ratio": kanji_r,
        # トピック
        "primary_entities": entities,
        # スコア
        "scores": scores,
        "total_score": total,
        "max_score": max_total,
        "score_pct": score_pct,
        "grade": grade,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        # メタ
        "fetch_source": page.get("source", "unknown"),
    }


def build_comparison_table(
    self_analysis: dict, competitor_analyses: list[dict]
) -> dict:
    """自サイトと競合の多次元比較 + ギャップ分析 + 統計サマリ。"""
    gaps = []
    advantages = []

    items_to_compare = [
        ("answer_first", "Answer-first構造"),
        ("heading_structure", "見出し構造"),
        ("faq", "FAQ/Q&A"),
        ("structured_data", "構造化データ"),
        ("author", "著者情報"),
        ("freshness", "更新日表示"),
        ("numeric_data", "数値データ"),
        ("lists_tables", "リスト/テーブル"),
        ("depth", "コンテンツ深度"),
        ("references", "参考文献"),
    ]

    for item, label in items_to_compare:
        self_score = self_analysis.get("scores", {}).get(item, 0)
        comp_scores = [c.get("scores", {}).get(item, 0) for c in competitor_analyses]
        comp_avg = sum(comp_scores) / len(comp_scores) if comp_scores else 0

        if self_score < comp_avg:
            gaps.append({
                "item": label,
                "key": item,
                "self_score": self_score,
                "competitor_avg": round(comp_avg, 1),
                "competitor_scores": comp_scores,
                "impact": "高" if comp_avg - self_score >= 1.5 else "中",
            })
        elif self_score > comp_avg:
            advantages.append({
                "item": label,
                "key": item,
                "self_score": self_score,
                "competitor_avg": round(comp_avg, 1),
            })

    # === 数値指標の統計サマリ ===
    numeric_fields = [
        ("word_count", "文字数"),
        ("h2_count", "H2数"),
        ("h3_count", "H3数"),
        ("faq_count", "FAQ数"),
        ("number_count", "数値データ数"),
        ("list_count", "リスト数"),
        ("table_count", "テーブル数"),
        ("external_link_count", "外部リンク数"),
        ("internal_link_count", "内部リンク数"),
        ("reference_link_count", "参考文献数"),
        ("sd_count", "構造化データ型数"),
        ("avg_sentence_length", "平均文長"),
        ("avg_paragraph_length", "平均段落文字数"),
    ]
    stats = []
    for field, label in numeric_fields:
        self_val = self_analysis.get(field, 0) or 0
        comp_vals = [c.get(field, 0) or 0 for c in competitor_analyses]
        comp_avg = sum(comp_vals) / len(comp_vals) if comp_vals else 0
        comp_max = max(comp_vals) if comp_vals else 0
        diff = self_val - comp_avg
        stats.append({
            "field": field,
            "label": label,
            "self": self_val,
            "competitor_avg": round(comp_avg, 1),
            "competitor_max": comp_max,
            "diff_vs_avg": round(diff, 1),
            "verdict": "優位" if diff > 0 else ("劣位" if diff < -0.01 else "同等"),
        })

    # === トピック共通/独自 ===
    self_entities = set(self_analysis.get("primary_entities", []))
    comp_entity_union: set = set()
    for c in competitor_analyses:
        comp_entity_union.update(c.get("primary_entities", []))
    shared_topics = sorted(self_entities & comp_entity_union)
    self_unique_topics = sorted(self_entities - comp_entity_union)
    missing_topics = sorted(comp_entity_union - self_entities)[:10]  # カバー不足

    # === 鮮度比較 ===
    self_days = self_analysis.get("days_since_modified")
    comp_days = [c.get("days_since_modified") for c in competitor_analyses if c.get("days_since_modified") is not None]
    freshness_gap = None
    if self_days is not None and comp_days:
        freshness_gap = {
            "self_days": self_days,
            "competitor_median_days": sorted(comp_days)[len(comp_days) // 2],
            "is_stale": self_days > (sum(comp_days) / len(comp_days)) + 90,
        }

    return {
        "gaps": sorted(gaps, key=lambda x: 0 if x["impact"] == "高" else 1),
        "advantages": advantages,
        "statistics": stats,
        "shared_topics": shared_topics,
        "self_unique_topics": self_unique_topics,
        "missing_topics": missing_topics,
        "freshness_gap": freshness_gap,
    }
