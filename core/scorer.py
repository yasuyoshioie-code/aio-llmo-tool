"""スコア計算 + レポート生成モジュール"""

from datetime import datetime


def calculate_technical_scores(structure: dict, robots: dict, llms: dict,
                                pagespeed: dict, sitemap: dict) -> dict:
    """Python解析データからカテゴリ2,5,6のスコアを計算（LLM不要）。"""
    scores = {}

    # --- カテゴリ2: 構造化データ (20点) ---
    from core.technical import check_structured_data_coverage, validate_jsonld
    sd = check_structured_data_coverage(structure.get("jsonld", []))
    validations = validate_jsonld(structure.get("jsonld", []))

    def _sd_score(exists, validations_list, type_name, full_pts):
        if not exists:
            return 0
        for v in validations_list:
            if v["type"] == type_name:
                if v["status"] == "◎":
                    return full_pts
                elif v["status"] == "○":
                    return full_pts * 0.75
                else:
                    return full_pts * 0.5
        return full_pts * 0.5

    scores["2-1_organization"] = {
        "score": _sd_score(sd["Organization"], validations, "Organization", 4),
        "max": 4, "reason": f"{'実装あり' if sd['Organization'] else '未実装'}",
        "method": "HTMLソースJSON-LD実測", "confidence": "高",
    }
    scores["2-2_article"] = {
        "score": _sd_score(sd["Article"], validations, "Article", 4) or
                 _sd_score(sd["Article"], validations, "BlogPosting", 4),
        "max": 4, "reason": f"{'実装あり' if sd['Article'] else '未実装'}",
        "method": "HTMLソースJSON-LD実測", "confidence": "高",
    }
    scores["2-3_faq"] = {
        "score": _sd_score(sd["FAQPage"], validations, "FAQPage", 4),
        "max": 4, "reason": f"{'実装あり' if sd['FAQPage'] else '未実装'}",
        "method": "HTMLソースJSON-LD実測", "confidence": "高",
    }
    scores["2-4_breadcrumb"] = {
        "score": _sd_score(sd["BreadcrumbList"], validations, "BreadcrumbList", 3),
        "max": 3, "reason": f"{'実装あり' if sd['BreadcrumbList'] else '未実装'}",
        "method": "HTMLソースJSON-LD実測", "confidence": "高",
    }
    scores["2-5_localbusiness"] = {
        "score": _sd_score(sd["LocalBusiness"], validations, "LocalBusiness", 3),
        "max": 3, "reason": f"{'実装あり' if sd['LocalBusiness'] else '未実装'}",
        "method": "HTMLソースJSON-LD実測", "confidence": "高",
        "applicable": True,
    }
    scores["2-6_additional"] = {
        "score": min(2, sum(1 for t in ["HowTo", "Product"] if sd.get(t))),
        "max": 2, "reason": f"追加schema: {', '.join(t for t in ['HowTo','Product'] if sd.get(t)) or 'なし'}",
        "method": "HTMLソースJSON-LD実測", "confidence": "高",
    }

    # --- カテゴリ5: 鮮度 (10点) ---
    dates = structure.get("dates", {})
    scores["5-1_update_display"] = {
        "score": 3 if dates.get("modified") else (1.5 if dates.get("published") else 0),
        "max": 3, "reason": f"更新日: {dates.get('modified', 'なし')}",
        "method": "HTMLソース実測", "confidence": "高",
    }
    scores["5-2_datemodified"] = {
        "score": 3 if dates.get("modified") else 0,
        "max": 3, "reason": f"dateModified: {dates.get('modified', '未実装')}",
        "method": "JSON-LD実測", "confidence": "高",
    }
    # 5-3, 5-4はサンプリングが必要なため推定
    scores["5-3_recent_update"] = {
        "score": 1, "max": 2, "reason": "サンプリング未実施（推定）",
        "method": "推定", "confidence": "低",
    }
    scores["5-4_year_management"] = {
        "score": 1, "max": 2, "reason": "サンプリング未実施（推定）",
        "method": "推定", "confidence": "低",
    }

    # --- カテゴリ6: テクニカル (10点) ---
    crawlers = robots.get("crawlers", {})
    blocked = sum(1 for c in crawlers.values() if "ブロック" in c.get("status", ""))
    total_crawlers = len(crawlers)
    if blocked == 0:
        crawler_score = 3
        crawler_reason = "全AIクローラー許可"
    elif blocked < total_crawlers:
        crawler_score = 1.5
        crawler_reason = f"{blocked}/{total_crawlers}クローラーをブロック"
    else:
        crawler_score = 0
        crawler_reason = "全クローラーブロック"

    scores["6-1_ai_crawlers"] = {
        "score": crawler_score, "max": 3, "reason": crawler_reason,
        "method": "robots.txt実測", "confidence": "高",
    }

    ps = pagespeed
    ps_score_val = ps.get("score")
    if ps_score_val is not None:
        if ps_score_val >= 80:
            ps_pts = 2
        elif ps_score_val >= 50:
            ps_pts = 1
        else:
            ps_pts = 0
        ps_reason = f"Performance Score: {ps_score_val}"
        ps_method = "PageSpeed API実測"
        ps_conf = "高"
    else:
        ps_pts = 1
        ps_reason = "API取得失敗（推定）"
        ps_method = "推定"
        ps_conf = "低"

    scores["6-2_pagespeed"] = {
        "score": ps_pts, "max": 2, "reason": ps_reason,
        "method": ps_method, "confidence": ps_conf,
    }
    scores["6-3_mobile"] = {
        "score": 2 if structure.get("viewport") else 0,
        "max": 2, "reason": f"viewport: {'あり' if structure.get('viewport') else 'なし'}",
        "method": "HTMLソース実測", "confidence": "高",
    }
    scores["6-4_canonical"] = {
        "score": 1.5 if structure.get("canonical") else 0,
        "max": 1.5, "reason": f"canonical: {structure.get('canonical', 'なし')[:50]}",
        "method": "HTMLソース実測", "confidence": "高",
    }
    scores["6-5_sitemap"] = {
        "score": 1.5 if sitemap.get("exists") else 0,
        "max": 1.5, "reason": f"sitemap.xml: {'あり' if sitemap.get('exists') else 'なし'}"
                               f" ({sitemap.get('url_count', 0)}URLs)",
        "method": "sitemap.xml実測", "confidence": "高",
    }

    return scores


def merge_all_scores(technical: dict, content_citation: dict, eeat: dict) -> dict:
    """全カテゴリのスコアを統合して総合スコアを計算。"""
    all_scores = {}

    def _map_scores(source: dict, mapping: dict, method: str = "Pythonヒューリスティクス",
                     confidence: str = "中") -> None:
        for key, (src_key, max_pts) in mapping.items():
            val = source.get(src_key, {})
            if isinstance(val, dict):
                s = val.get("score", 0)
                r = val.get("reason", "")
            else:
                s = 0
                r = "分析データなし"
            all_scores[key] = {
                "score": min(s, max_pts), "max": max_pts, "reason": r,
                "method": method, "confidence": confidence,
            }

    # カテゴリ1: コンテンツ品質 (20点)
    _map_scores(content_citation, {
        "1-1_answer_first": ("answer_first", 4),
        "1-5_clarity": ("clarity", 3),
    })

    # FAQ (1-3) — Python解析（別途統合時に上書き）
    all_scores["1-3_faq"] = {
        "score": 0, "max": 4, "reason": "別途統合時に設定",
        "method": "HTML実測", "confidence": "高",
    }

    # カテゴリ4: AI引用可能性 (20点)
    _map_scores(content_citation, {
        "4-1_definition": ("definition_sentences", 4),
        "4-2_numeric": ("numeric_data", 4),
        "4-3_original": ("original_data", 4),
        "4-4_entity": ("entity_consistency", 4),
    })

    # カテゴリ3: E-E-A-T (20点)
    _map_scores(eeat, {
        "3-1_author": ("author_display", 4),
        "3-2_operator": ("operator_info", 4),
        "3-3_citations": ("citations", 3),
        "3-5_experience": ("experience", 3),
        "3-4_editorial": ("editorial_policy", 3),
        "3-6_external": ("external_consistency", 3),
    })

    # カテゴリ2, 5, 6はtechnicalから
    all_scores.update(technical)

    return all_scores


def calculate_category_totals(all_scores: dict) -> dict:
    """カテゴリ別の合計スコアを計算。"""
    categories = {
        "1_content": {"label": "コンテンツ品質・構造", "max": 20, "items": []},
        "2_structured": {"label": "構造化データ", "max": 20, "items": []},
        "3_eeat": {"label": "E-E-A-Tシグナル", "max": 20, "items": []},
        "4_citation": {"label": "AI引用可能性", "max": 20, "items": []},
        "5_freshness": {"label": "コンテンツ鮮度", "max": 10, "items": []},
        "6_technical": {"label": "テクニカルAIO/UX", "max": 10, "items": []},
    }

    for key, item in all_scores.items():
        cat_num = key.split("-")[0].split("_")[0]
        for cat_key in categories:
            if cat_key.startswith(cat_num):
                categories[cat_key]["items"].append(item)
                break

    for cat in categories.values():
        raw = sum(i.get("score", 0) for i in cat["items"])
        raw_max = sum(i.get("max", 0) for i in cat["items"])
        # 正規化
        if raw_max > 0:
            cat["score"] = round(raw / raw_max * cat["max"], 1)
        else:
            cat["score"] = 0
        cat["raw"] = round(raw, 1)
        cat["raw_max"] = round(raw_max, 1)

    return categories


def calculate_total(categories: dict) -> dict:
    """総合スコアとグレードを計算。"""
    total = sum(c["score"] for c in categories.values())
    total = round(total, 1)

    if total >= 80:
        grade = "A"
        label = "AIO/LLMO対応が高水準"
    elif total >= 60:
        grade = "B"
        label = "基本対応あり。重点改善で大幅効果"
    elif total >= 40:
        grade = "C"
        label = "対応不足。優先施策の実行が急務"
    elif total >= 20:
        grade = "D"
        label = "ほぼ未対応。基盤構築から着手"
    else:
        grade = "E"
        label = "全面的な対策が必要"

    return {"total": total, "grade": grade, "label": label}


def generate_report_md(
    url: str, structure: dict, categories: dict, total: dict,
    robots: dict, llms: dict, pagespeed: dict, all_scores: dict,
    competitors: list = None, comparison: dict = None,
    improvements: dict = None, test_queries: dict = None,
) -> str:
    """Markdown形式の診断レポートを生成。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# AIO/LLMO 総合診断レポート",
        f"",
        f"| 項目 | 内容 |",
        f"|------|------|",
        f"| 対象URL | {url} |",
        f"| 診断日時 | {now} |",
        f"| サイト名 | {structure.get('title', '')} |",
        f"| 総文字数 | {structure.get('word_count', 0):,} |",
        f"",
        f"---",
        f"",
        f"## 総合スコア: {total['total']} / 100（グレード: {total['grade']}）",
        f"",
        f"> {total['label']}",
        f"",
        f"| カテゴリ | スコア | 配点 |",
        f"|---------|-------|------|",
    ]

    for key in sorted(categories.keys()):
        cat = categories[key]
        bar_filled = int(cat['score'] / cat['max'] * 10)
        bar = "■" * bar_filled + "□" * (10 - bar_filled)
        lines.append(f"| {cat['label']} | {cat['score']}/{cat['max']} [{bar}] | {cat['max']} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # 詳細スコア
    lines.append("## 30項目診断詳細")
    lines.append("")
    lines.append("| # | 項目 | 得点 | 根拠 | 確認方法 | 信頼度 |")
    lines.append("|---|------|------|------|---------|--------|")

    for key in sorted(all_scores.keys()):
        item = all_scores[key]
        label = key.replace("_", " ")
        lines.append(
            f"| {key} | {label} | {item.get('score',0)}/{item.get('max',0)} "
            f"| {item.get('reason','')} | {item.get('method','')} | {item.get('confidence','')} |"
        )

    # 競合分析
    if competitors:
        lines.extend(["", "---", "", "## 競合分析", ""])
        lines.append("| サイト | 文字数 | H2数 | FAQ数 | 構造化データ | スコア |")
        lines.append("|--------|--------|------|-------|-------------|--------|")
        for c in competitors:
            sd_str = ", ".join(c.get("sd_types", [])[:3]) or "なし"
            lines.append(
                f"| [{c.get('title',c['url'])[:30]}]({c['url']}) "
                f"| {c.get('word_count',0):,} | {c.get('h2_count',0)} "
                f"| {c.get('faq_count',0)} | {sd_str} | {c.get('score_pct',0)}% |"
            )

    if comparison:
        if comparison.get("gaps"):
            lines.extend(["", "### コンテンツギャップ（競合に負けている項目）", ""])
            for g in comparison["gaps"]:
                emoji = "🔴" if g["impact"] == "高" else "🟡"
                lines.append(f"- {emoji} **{g['item']}**: 自サイト {g['self_score']} vs 競合平均 {g['competitor_avg']}")

        if comparison.get("advantages"):
            lines.extend(["", "### 独自優位性", ""])
            for a in comparison["advantages"]:
                lines.append(f"- ✅ **{a['item']}**: 自サイト {a['self_score']} vs 競合平均 {a['competitor_avg']}")

    # 改善提案
    if improvements and not improvements.get("error"):
        lines.extend(["", "---", "", "## 改善アクションプラン", ""])

        qw = improvements.get("quick_wins", [])
        if qw:
            lines.append("### Quick Win（今すぐ・効果大）")
            lines.append("")
            for i, item in enumerate(qw, 1):
                lines.append(f"#### {i}. {item.get('title', '')}")
                lines.append(f"- **カテゴリ:** {item.get('category', '')}")
                lines.append(f"- **工数:** {item.get('effort', '')}")
                lines.append(f"- **インパクト:** {item.get('impact', '')}")
                if item.get("before"):
                    lines.append(f"- **Before:**")
                    lines.append(f"```\n{item['before']}\n```")
                if item.get("after"):
                    lines.append(f"- **After:**")
                    lines.append(f"```\n{item['after']}\n```")
                lines.append("")

        strat = improvements.get("strategic", [])
        if strat:
            lines.append("### 戦略施策（中長期）")
            lines.append("")
            for i, item in enumerate(strat, 1):
                lines.append(f"{i}. **{item.get('title', '')}** — {item.get('description', '')}")
            lines.append("")

        if improvements.get("organization_jsonld"):
            lines.extend([
                "### Organization JSON-LD（コピペ用）",
                "",
                "```json",
                improvements["organization_jsonld"],
                "```",
                "",
            ])

        if improvements.get("llms_txt_template"):
            lines.extend([
                "### llms.txt テンプレート",
                "",
                "```markdown",
                improvements["llms_txt_template"],
                "```",
                "",
            ])

    # テストクエリ
    if test_queries and not test_queries.get("error"):
        lines.extend(["", "---", "", "## 商談実演用テストクエリ", ""])
        lines.append("| # | プラットフォーム | テストクエリ | 引用されない場合の原因 |")
        lines.append("|---|----------------|------------|---------------------|")
        for i, q in enumerate(test_queries.get("queries", []), 1):
            lines.append(
                f"| {i} | {q.get('platform','')} | {q.get('query','')} | {q.get('reason_if_not','')} |"
            )

        ce = test_queries.get("claude_self_eval", {})
        if ce:
            lines.extend([
                "",
                f"**Claude参考評価（内省的評価・実測ではない）:** "
                f"{'推薦する' if ce.get('would_recommend') else '推薦しない'} — {ce.get('reason', '')}",
            ])

    lines.extend(["", "---", f"", f"*生成日時: {now} | AIO/LLMO診断ツール v2.1*"])

    return "\n".join(lines)
