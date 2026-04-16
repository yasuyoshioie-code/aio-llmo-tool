"""コーポレートサイト向けプリセット — ページ役割(ロール)ベースのスコアリング

ページの役割(top / about / business / ir / news / contact / faq / privacy / csr)
ごとに異なる基準でスコアリングし、サイト全体の構造完全性も評価する。
"""

import re
from datetime import datetime
from core.content_scorer import generate_test_queries_python
from core.scorer import grade_from_score


PRESET_ID = "corporate"
PRESET_LABEL = "🏢 コーポレートサイト"


CATEGORY_DEFINITIONS = {
    "1_company_info":   {"label": "企業基本情報",        "max": 20},
    "2_credibility":    {"label": "信頼性・権威性",      "max": 20},
    "3_business":       {"label": "事業内容の明確性",    "max": 15},
    "4_ir_news":        {"label": "IR・ニュース発信",    "max": 15},
    "5_stakeholder":    {"label": "ステークホルダー対応", "max": 15},
    "6_brand_sns":      {"label": "ブランド・SNS",       "max": 15},
}


# チェックキーのプレフィックスからカテゴリへのマッピング
CATEGORY_MAP = {
    "top_": "1_company_info",
    "about_": "1_company_info",
    "biz_": "3_business",
    "ir_": "4_ir_news",
    "news_": "4_ir_news",
    "contact_": "5_stakeholder",
    "faq_": "5_stakeholder",
    "privacy_": "5_stakeholder",
    "csr_": "5_stakeholder",
    "common_credibility_": "2_credibility",
    "common_brand_": "6_brand_sns",
    "common_tech_": "6_brand_sns",
}


# ==========================================================================
# ヘルパー
# ==========================================================================

def _find_organization_jsonld(structure: dict) -> dict | None:
    """Organization / Corporation 系JSON-LDを抽出。"""
    for jsonld in structure.get("jsonld", []):
        node = jsonld
        graph = jsonld.get("@graph") if isinstance(jsonld, dict) else None
        if graph and isinstance(graph, list):
            for g in graph:
                t = g.get("@type", "") if isinstance(g, dict) else ""
                if isinstance(t, list):
                    if any(x in ("Organization", "Corporation", "LocalBusiness") for x in t):
                        return g
                elif t in ("Organization", "Corporation", "LocalBusiness"):
                    return g
        if isinstance(node, dict):
            t = node.get("@type", "")
            if isinstance(t, list):
                if any(x in ("Organization", "Corporation", "LocalBusiness") for x in t):
                    return node
            elif t in ("Organization", "Corporation", "LocalBusiness"):
                return node
    return None


def _has_keywords(text: str, keywords: list[str]) -> int:
    """テキスト中にキーワードが何種類含まれるか。"""
    return sum(1 for k in keywords if k in text)


def _make_result(score: int, reason: str) -> dict:
    """チェック関数の戻り値を生成。"""
    return {"score": score, "reason": reason}


def _find_jsonld_type(structure: dict, target_type: str) -> dict | None:
    """指定@typeのJSON-LDを探す。"""
    for jsonld in structure.get("jsonld", []):
        if not isinstance(jsonld, dict):
            continue
        t = jsonld.get("@type", "")
        if isinstance(t, list):
            if target_type in t:
                return jsonld
        elif t == target_type:
            return jsonld
        graph = jsonld.get("@graph", [])
        if isinstance(graph, list):
            for g in graph:
                if not isinstance(g, dict):
                    continue
                gt = g.get("@type", "")
                if isinstance(gt, list):
                    if target_type in gt:
                        return g
                elif gt == target_type:
                    return g
    return None


# ==========================================================================
# ロール固有チェック関数群
# ==========================================================================

# ---------- トップページ ----------

def _check_top_brand_h1(structure: dict) -> dict:
    """H1にブランド名/ミッションが含まれるか。"""
    headings = structure.get("headings", [])
    h1_list = [h for h in headings if h.get("level") == 1]
    if not h1_list:
        return _make_result(0, "H1タグなし")
    h1_text = h1_list[0].get("text", "")
    title = structure.get("title", "")
    if h1_text and len(h1_text) >= 3:
        if title and any(part in h1_text for part in title.split("|")[:1]):
            return _make_result(3, f"H1にブランド名含む: {h1_text[:40]}")
        return _make_result(2, f"H1あり: {h1_text[:40]}（ブランド名との一致未確認）")
    return _make_result(1, f"H1が短い: {h1_text[:20]}")


def _check_top_website_jsonld(structure: dict) -> dict:
    """WebSite JSON-LDの有無。"""
    ws = _find_jsonld_type(structure, "WebSite")
    if ws:
        has_search = bool(ws.get("potentialAction"))
        has_url = bool(ws.get("url"))
        if has_search and has_url:
            return _make_result(3, "WebSite JSON-LD完全実装（SearchAction付き）")
        elif has_url:
            return _make_result(2, "WebSite JSON-LD実装（SearchAction未設定）")
        return _make_result(1, "WebSite JSON-LD検出（不完全）")
    return _make_result(0, "WebSite JSON-LD未実装")


def _check_top_navigation(structure: dict) -> dict:
    """主要ページへの導線（内部リンク数）。"""
    internal_links = structure.get("internal_links", [])
    link_count = len(internal_links) if isinstance(internal_links, list) else 0
    content = structure.get("content_text", "") or ""
    nav_keywords = ["会社概要", "事業内容", "IR", "ニュース", "お問い合わせ", "採用"]
    nav_found = _has_keywords(content, nav_keywords)
    if nav_found >= 4 or link_count >= 15:
        return _make_result(2, f"ナビゲーション充実（導線キーワード{nav_found}種, リンク{link_count}件）")
    elif nav_found >= 2 or link_count >= 5:
        return _make_result(1, f"ナビゲーション基本あり（導線キーワード{nav_found}種）")
    return _make_result(0, "主要ページへの導線が不十分")


def _check_top_news_section(structure: dict) -> dict:
    """最新ニュース/トピックスセクション。"""
    content = structure.get("content_text", "") or ""
    news_keywords = ["ニュース", "お知らせ", "News", "トピックス", "新着情報", "プレスリリース"]
    news_found = _has_keywords(content, news_keywords)
    current_year = datetime.now().year
    has_recent = any(f"{y}年" in content or f"{y}/" in content or f"{y}-" in content
                     for y in range(current_year - 1, current_year + 1))
    if news_found >= 1 and has_recent:
        return _make_result(2, f"ニュースセクションあり（直近年の更新含む）")
    elif news_found >= 1:
        return _make_result(1, "ニュースセクションあり（鮮度不明）")
    return _make_result(0, "トップページにニュースセクションなし")


# ---------- 会社概要ページ ----------

def _check_about_org_jsonld(structure: dict) -> dict:
    """Organization JSON-LDの充足度チェック。"""
    for jsonld in structure.get("jsonld", []):
        if not isinstance(jsonld, dict):
            continue
        # @graph内も検索
        candidates = [jsonld]
        graph = jsonld.get("@graph", [])
        if isinstance(graph, list):
            candidates.extend(g for g in graph if isinstance(g, dict))
        for node in candidates:
            t = node.get("@type", "")
            if isinstance(t, list):
                if not any(x in ("Organization", "Corporation", "LocalBusiness") for x in t):
                    continue
            elif t not in ("Organization", "Corporation", "LocalBusiness"):
                continue
            required = ["name", "url"]
            recommended = ["logo", "contactPoint", "sameAs", "address", "founder", "description"]
            has_required = sum(1 for f in required if node.get(f))
            has_recommended = sum(1 for f in recommended if node.get(f))
            if has_required == 2 and has_recommended >= 4:
                return _make_result(5, f"Organization JSON-LD 完全実装（推奨{has_recommended}/6項目）")
            elif has_required == 2 and has_recommended >= 2:
                return _make_result(4, f"Organization JSON-LD 基本実装（推奨{has_recommended}/6項目 追加推奨）")
            elif has_required == 2:
                return _make_result(3, "Organization JSON-LD 最低限実装（推奨項目を追加すべき）")
            else:
                return _make_result(1, f"Organization JSON-LD 不完全（必須項目 {has_required}/2）")
    return _make_result(0, "Organization JSON-LD 未実装")


def _check_about_nap(structure: dict) -> dict:
    """NAP情報（社名/住所/電話）の有無。"""
    content = structure.get("content_text", "") or ""
    has_address = bool(re.search(r"〒?\d{3}-?\d{4}", content)) or "住所" in content or "所在地" in content
    has_phone = bool(re.search(r"0\d{1,4}-?\d{1,4}-?\d{4}", content)) or "TEL" in content or "電話" in content
    has_org_name = bool(structure.get("title")) or "株式会社" in content or "有限会社" in content or "合同会社" in content
    nap_count = sum([has_address, has_phone, has_org_name])
    if nap_count == 3:
        return _make_result(4, f"NAP情報 3/3項目完備（住所:{has_address} 電話:{has_phone} 社名:{has_org_name}）")
    elif nap_count == 2:
        return _make_result(2, f"NAP情報 2/3項目（住所:{has_address} 電話:{has_phone} 社名:{has_org_name}）")
    elif nap_count == 1:
        return _make_result(1, f"NAP情報 1/3項目のみ")
    return _make_result(0, "NAP情報なし")


def _check_about_details(structure: dict) -> dict:
    """設立/資本金/従業員数の記載。"""
    content = structure.get("content_text", "") or ""
    detail_keywords = ["設立", "創業", "代表取締役", "資本金", "従業員数", "事業年度"]
    detail_count = _has_keywords(content, detail_keywords)
    if detail_count >= 4:
        return _make_result(3, f"会社詳細 {detail_count}/6項目検出")
    elif detail_count >= 2:
        return _make_result(2, f"会社詳細 {detail_count}/6項目検出")
    elif detail_count >= 1:
        return _make_result(1, f"会社詳細 {detail_count}/6項目検出")
    return _make_result(0, "設立・資本金・従業員数の記述なし")


def _check_about_history(structure: dict) -> dict:
    """沿革・歴史ページ。"""
    content = structure.get("content_text", "") or ""
    has_history = ("沿革" in content) or ("歴史" in content) or ("History" in content)
    year_mentions = len(re.findall(r"(19|20)\d{2}年", content))
    if has_history and year_mentions >= 5:
        return _make_result(3, f"沿革記述あり（年号{year_mentions}件）")
    elif has_history and year_mentions >= 1:
        return _make_result(2, f"沿革記述あり（年号{year_mentions}件、もう少し詳細推奨）")
    elif year_mentions >= 3:
        return _make_result(1, f"年号記述{year_mentions}件あるが沿革セクション不明確")
    return _make_result(0, "沿革・歴史の記述なし")


def _check_about_officers(structure: dict) -> dict:
    """役員情報の記載。"""
    content = structure.get("content_text", "") or ""
    officer_keywords = ["代表取締役", "取締役", "監査役", "執行役員", "CEO", "COO", "CTO", "CFO", "役員"]
    officer_count = _has_keywords(content, officer_keywords)
    if officer_count >= 3:
        return _make_result(2, f"役員情報 {officer_count}種検出")
    elif officer_count >= 1:
        return _make_result(1, f"役員情報 {officer_count}種検出（詳細追加推奨）")
    return _make_result(0, "役員情報の記述なし")


# ---------- 事業内容ページ ----------

def _check_biz_segments(structure: dict) -> dict:
    """事業セグメント明記。"""
    content = structure.get("content_text", "") or ""
    biz_keywords = ["事業内容", "サービス", "事業領域", "事業セグメント", "プロダクト", "製品", "ソリューション"]
    biz_count = _has_keywords(content, biz_keywords)
    headings = structure.get("headings", [])
    h2_count = sum(1 for h in headings if h.get("level") == 2)
    if biz_count >= 3 and h2_count >= 3:
        return _make_result(4, f"事業セグメント明確（キーワード{biz_count}種, H2={h2_count}）")
    elif biz_count >= 2:
        return _make_result(3, f"事業説明あり（キーワード{biz_count}種）")
    elif biz_count >= 1:
        return _make_result(2, f"事業説明シグナル {biz_count}種")
    return _make_result(0, "事業セグメントの明記なし")


def _check_biz_numbers(structure: dict) -> dict:
    """数値実績（売上/件数等）。"""
    content = structure.get("content_text", "") or ""
    has_numbers = len(re.findall(r"\d+(?:,\d+)*\s*(?:社|件|名|人|台|店舗|拠点|億|万|％|%)", content))
    if has_numbers >= 5:
        return _make_result(4, f"事業実績数値 {has_numbers}件検出（充実）")
    elif has_numbers >= 3:
        return _make_result(3, f"事業実績数値 {has_numbers}件検出")
    elif has_numbers >= 1:
        return _make_result(2, f"事業実績数値 {has_numbers}件検出（もっと追加推奨）")
    return _make_result(0, "数値実績の記述なし")


def _check_biz_strengths(structure: dict) -> dict:
    """強み/差別化ポイント。"""
    content = structure.get("content_text", "") or ""
    strength_keywords = ["強み", "特長", "特徴", "他社との違い", "選ばれる理由", "Why", "独自"]
    strength_count = _has_keywords(content, strength_keywords)
    if strength_count >= 3:
        return _make_result(3, f"強み記述 {strength_count}種（明確）")
    elif strength_count >= 2:
        return _make_result(2, f"強み記述 {strength_count}種")
    elif strength_count >= 1:
        return _make_result(1, f"強み記述 {strength_count}種（具体化推奨）")
    return _make_result(0, "強み・差別化の記述なし")


def _check_biz_cases(structure: dict) -> dict:
    """導入事例/取引実績。"""
    content = structure.get("content_text", "") or ""
    case_keywords = ["導入企業", "取引先", "クライアント", "実績", "事例", "Case", "お客様の声", "導入事例"]
    case_count = _has_keywords(content, case_keywords)
    if case_count >= 3:
        return _make_result(3, f"事例・実績 {case_count}種検出")
    elif case_count >= 2:
        return _make_result(2, f"事例・実績 {case_count}種検出")
    elif case_count >= 1:
        return _make_result(1, f"事例・実績 {case_count}種検出")
    return _make_result(0, "導入事例・取引実績の記述なし")


# ---------- IR情報ページ ----------

def _check_ir_financial(structure: dict) -> dict:
    """決算情報/財務データ。"""
    content = structure.get("content_text", "") or ""
    ir_keywords = ["決算", "財務", "売上高", "営業利益", "経常利益", "純利益", "有価証券報告書", "決算短信"]
    ir_count = _has_keywords(content, ir_keywords)
    if ir_count >= 4:
        return _make_result(4, f"決算・財務情報 {ir_count}種検出（充実）")
    elif ir_count >= 2:
        return _make_result(3, f"決算・財務情報 {ir_count}種検出")
    elif ir_count >= 1:
        return _make_result(2, f"決算・財務情報 {ir_count}種検出")
    return _make_result(0, "決算情報の記述なし")


def _check_ir_reports(structure: dict) -> dict:
    """報告書/開示資料。"""
    content = structure.get("content_text", "") or ""
    report_keywords = ["有価証券報告書", "四半期報告書", "適時開示", "IR資料", "アニュアルレポート", "統合報告書"]
    report_count = _has_keywords(content, report_keywords)
    raw_html = (structure.get("raw_html", "") or "").lower()
    has_pdf = ".pdf" in raw_html
    if report_count >= 2 and has_pdf:
        return _make_result(3, f"開示資料 {report_count}種 + PDF掲載あり")
    elif report_count >= 2:
        return _make_result(2, f"開示資料 {report_count}種検出")
    elif report_count >= 1:
        return _make_result(1, f"開示資料 {report_count}種検出")
    return _make_result(0, "報告書・開示資料の記述なし")


def _check_ir_stock(structure: dict) -> dict:
    """株価/証券情報。"""
    content = structure.get("content_text", "") or ""
    stock_keywords = ["証券コード", "株価", "配当", "株主", "東証", "プライム", "スタンダード", "グロース"]
    stock_count = _has_keywords(content, stock_keywords)
    if stock_count >= 3:
        return _make_result(3, f"証券情報 {stock_count}種検出")
    elif stock_count >= 2:
        return _make_result(2, f"証券情報 {stock_count}種検出")
    elif stock_count >= 1:
        return _make_result(1, f"証券情報 {stock_count}種検出")
    return _make_result(0, "株価・証券情報の記述なし")


# ---------- ニュース/お知らせ ----------

def _check_news_freshness(structure: dict) -> dict:
    """直近6ヶ月以内の更新。"""
    content = structure.get("content_text", "") or ""
    current_year = datetime.now().year
    current_month = datetime.now().month
    has_current_year = str(current_year) in content
    has_recent_dates = len(re.findall(
        rf"{current_year}[/.年-](?:0?[1-9]|1[0-2])[/.月-]", content
    ))
    if has_current_year and has_recent_dates >= 3:
        return _make_result(4, f"直近の更新あり（{current_year}年の日付{has_recent_dates}件）")
    elif has_current_year and has_recent_dates >= 1:
        return _make_result(3, f"今年の更新あり（日付{has_recent_dates}件）")
    elif has_current_year:
        return _make_result(2, f"今年({current_year})の記述はあるが日付不明確")
    elif str(current_year - 1) in content:
        return _make_result(1, f"前年({current_year-1})の記述あり（更新が遅れている可能性）")
    return _make_result(0, "直近の更新が確認できない")


def _check_news_datePublished(structure: dict) -> dict:
    """日付表記の構造化。"""
    content = structure.get("content_text", "") or ""
    raw_html = (structure.get("raw_html", "") or "").lower()
    date_count = len(re.findall(r"\d{4}[/.年-]\d{1,2}[/.月-]\d{1,2}", content))
    has_datetime_attr = "datetime=" in raw_html
    has_time_tag = "<time" in raw_html
    if date_count >= 5 and (has_datetime_attr or has_time_tag):
        return _make_result(3, f"日付{date_count}件 + time/datetime属性あり（構造化済み）")
    elif date_count >= 5:
        return _make_result(2, f"日付{date_count}件あるがdatetime属性なし")
    elif date_count >= 1:
        return _make_result(1, f"日付{date_count}件（構造化・件数追加推奨）")
    return _make_result(0, "日付表記なし")


def _check_news_frequency(structure: dict) -> dict:
    """更新頻度（月1回以上）の推定。"""
    content = structure.get("content_text", "") or ""
    date_matches = re.findall(r"(\d{4})[/.年-](\d{1,2})[/.月-]\d{1,2}", content)
    if len(date_matches) >= 10:
        months = set()
        for y, m in date_matches:
            months.add(f"{y}-{m.zfill(2)}")
        if len(months) >= 6:
            return _make_result(3, f"高頻度更新（{len(months)}ヶ月分の記事検出）")
        elif len(months) >= 3:
            return _make_result(2, f"更新頻度あり（{len(months)}ヶ月分）")
        return _make_result(1, f"記事{len(date_matches)}件あるが月の分散が少ない")
    elif len(date_matches) >= 3:
        return _make_result(1, f"記事{len(date_matches)}件（更新頻度向上推奨）")
    return _make_result(0, "更新頻度を推定できない（日付が少ない）")


# ---------- お問い合わせページ ----------

def _check_contact_form(structure: dict) -> dict:
    """フォーム設置。"""
    raw_html = (structure.get("raw_html", "") or "").lower()
    content = structure.get("content_text", "") or ""
    has_form_tag = "<form" in raw_html
    has_input = "<input" in raw_html
    has_textarea = "<textarea" in raw_html
    form_keywords = ["お問い合わせ", "Contact", "問い合わせ", "送信", "Submit"]
    form_kw_count = _has_keywords(content, form_keywords)
    if has_form_tag and (has_input or has_textarea):
        return _make_result(3, "フォーム設置済み（form+input/textarea検出）")
    elif form_kw_count >= 2:
        return _make_result(2, f"問い合わせ関連キーワード{form_kw_count}種（フォーム要素は未検出）")
    elif form_kw_count >= 1:
        return _make_result(1, "問い合わせの言及あるがフォーム未確認")
    return _make_result(0, "フォームなし")


def _check_contact_info(structure: dict) -> dict:
    """電話/メール/住所。"""
    content = structure.get("content_text", "") or ""
    raw_html = (structure.get("raw_html", "") or "").lower()
    has_phone = bool(re.search(r"0\d{1,4}-?\d{1,4}-?\d{4}", content)) or "TEL" in content
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", content)) or "mailto:" in raw_html
    has_address = bool(re.search(r"〒?\d{3}-?\d{4}", content)) or "所在地" in content or "住所" in content
    info_count = sum([has_phone, has_email, has_address])
    if info_count >= 3:
        return _make_result(3, f"連絡先情報完備（電話:{has_phone} メール:{has_email} 住所:{has_address}）")
    elif info_count >= 2:
        return _make_result(2, f"連絡先情報 {info_count}/3項目")
    elif info_count >= 1:
        return _make_result(1, f"連絡先情報 {info_count}/3項目")
    return _make_result(0, "連絡先情報なし")


# ---------- FAQページ ----------

def _check_faq_count(structure: dict) -> dict:
    """FAQ数（5問以上推奨）。"""
    content = structure.get("content_text", "") or ""
    faq_keywords = ["Q.", "Q:", "質問", "よくあるご質問", "FAQ", "Q&A"]
    faq_signals = _has_keywords(content, faq_keywords)
    # JSON-LDのFAQからカウント
    faq_jsonld = _find_jsonld_type(structure, "FAQPage")
    jsonld_count = 0
    if faq_jsonld:
        main_entity = faq_jsonld.get("mainEntity", [])
        if isinstance(main_entity, list):
            jsonld_count = len(main_entity)
    # テキスト内のQ数推定
    q_pattern_count = len(re.findall(r"(?:Q[\.:：]\s*|質問\d|Q\d)", content))
    total_q = max(jsonld_count, q_pattern_count)
    if total_q >= 5:
        return _make_result(3, f"FAQ {total_q}問検出（5問以上: 推奨水準達成）")
    elif total_q >= 3:
        return _make_result(2, f"FAQ {total_q}問検出（5問以上推奨）")
    elif total_q >= 1 or faq_signals >= 1:
        return _make_result(1, f"FAQ {total_q}問 / シグナル{faq_signals}種（拡充推奨）")
    return _make_result(0, "FAQなし")


def _check_faq_jsonld(structure: dict) -> dict:
    """FAQPage JSON-LD。"""
    faq_jsonld = _find_jsonld_type(structure, "FAQPage")
    if faq_jsonld:
        main_entity = faq_jsonld.get("mainEntity", [])
        count = len(main_entity) if isinstance(main_entity, list) else 0
        if count >= 5:
            return _make_result(3, f"FAQPage JSON-LD 完全実装（{count}問）")
        elif count >= 1:
            return _make_result(2, f"FAQPage JSON-LD実装（{count}問、5問以上推奨）")
        return _make_result(1, "FAQPage JSON-LDあるがmainEntityが空")
    return _make_result(0, "FAQPage JSON-LD未実装")


# ---------- プライバシーポリシー ----------

def _check_privacy_exists(structure: dict) -> dict:
    """ページ存在。"""
    content = structure.get("content_text", "") or ""
    title = structure.get("title", "") or ""
    privacy_keywords = ["プライバシーポリシー", "個人情報保護方針", "Privacy Policy",
                        "個人情報の取扱", "プライバシー"]
    found = _has_keywords(content + " " + title, privacy_keywords)
    if found >= 2:
        return _make_result(2, f"プライバシーポリシー確認（{found}種のシグナル）")
    elif found >= 1:
        return _make_result(1, "プライバシーポリシーの言及あり（内容の充実推奨）")
    return _make_result(0, "プライバシーポリシーのシグナルなし")


# ---------- CSR/ESGページ ----------

def _check_csr_content(structure: dict) -> dict:
    """CSR/ESG/SDGs取組。"""
    content = structure.get("content_text", "") or ""
    csr_keywords = ["CSR", "サステナビリティ", "Sustainability", "SDGs", "ESG",
                    "社会貢献", "環境", "マテリアリティ", "GHG", "カーボン",
                    "人的資本", "ダイバーシティ", "TCFD"]
    csr_count = _has_keywords(content, csr_keywords)
    if csr_count >= 5:
        return _make_result(3, f"CSR/ESG/SDGs {csr_count}種検出（充実）")
    elif csr_count >= 3:
        return _make_result(2, f"CSR/ESG/SDGs {csr_count}種検出")
    elif csr_count >= 1:
        return _make_result(1, f"CSR/ESG/SDGs {csr_count}種検出（拡充推奨）")
    return _make_result(0, "CSR/ESG/SDGs取組の記述なし")


# ==========================================================================
# ROLE_REQUIREMENTS 定義
# ==========================================================================

ROLE_REQUIREMENTS = {
    "top": {
        "label": "トップページ",
        "checks": [
            {"key": "top_brand_h1", "label": "H1にブランド名/ミッション", "max": 3,
             "check": _check_top_brand_h1},
            {"key": "top_website_jsonld", "label": "WebSite JSON-LD", "max": 3,
             "check": _check_top_website_jsonld},
            {"key": "top_navigation", "label": "主要ページへの導線", "max": 2,
             "check": _check_top_navigation},
            {"key": "top_news_section", "label": "最新ニュース/トピックス", "max": 2,
             "check": _check_top_news_section},
        ],
    },
    "about": {
        "label": "会社概要ページ",
        "checks": [
            {"key": "about_org_jsonld", "label": "Organization JSON-LD", "max": 5,
             "check": _check_about_org_jsonld},
            {"key": "about_nap", "label": "NAP情報（社名/住所/電話）", "max": 4,
             "check": _check_about_nap},
            {"key": "about_details", "label": "設立/資本金/従業員数", "max": 3,
             "check": _check_about_details},
            {"key": "about_history", "label": "沿革・歴史", "max": 3,
             "check": _check_about_history},
            {"key": "about_officers", "label": "役員情報", "max": 2,
             "check": _check_about_officers},
        ],
    },
    "business": {
        "label": "事業内容ページ",
        "checks": [
            {"key": "biz_segments", "label": "事業セグメント明記", "max": 4,
             "check": _check_biz_segments},
            {"key": "biz_numbers", "label": "数値実績（売上/件数等）", "max": 4,
             "check": _check_biz_numbers},
            {"key": "biz_strengths", "label": "強み/差別化ポイント", "max": 3,
             "check": _check_biz_strengths},
            {"key": "biz_cases", "label": "導入事例/取引実績", "max": 3,
             "check": _check_biz_cases},
        ],
    },
    "ir": {
        "label": "IR情報ページ",
        "checks": [
            {"key": "ir_financial", "label": "決算情報/財務データ", "max": 4,
             "check": _check_ir_financial},
            {"key": "ir_reports", "label": "報告書/開示資料", "max": 3,
             "check": _check_ir_reports},
            {"key": "ir_stock", "label": "株価/証券情報", "max": 3,
             "check": _check_ir_stock},
        ],
    },
    "news": {
        "label": "ニュース/お知らせ",
        "checks": [
            {"key": "news_freshness", "label": "直近6ヶ月以内の更新", "max": 4,
             "check": _check_news_freshness},
            {"key": "news_datePublished", "label": "日付表記の構造化", "max": 3,
             "check": _check_news_datePublished},
            {"key": "news_frequency", "label": "更新頻度（月1回以上）", "max": 3,
             "check": _check_news_frequency},
        ],
    },
    "contact": {
        "label": "お問い合わせページ",
        "checks": [
            {"key": "contact_form", "label": "フォーム設置", "max": 3,
             "check": _check_contact_form},
            {"key": "contact_info", "label": "電話/メール/住所", "max": 3,
             "check": _check_contact_info},
        ],
    },
    "faq": {
        "label": "FAQページ",
        "checks": [
            {"key": "faq_count", "label": "FAQ数（5問以上推奨）", "max": 3,
             "check": _check_faq_count},
            {"key": "faq_jsonld", "label": "FAQPage JSON-LD", "max": 3,
             "check": _check_faq_jsonld},
        ],
    },
    "privacy": {
        "label": "プライバシーポリシー",
        "checks": [
            {"key": "privacy_exists", "label": "ページ存在", "max": 2,
             "check": _check_privacy_exists},
        ],
    },
    "csr": {
        "label": "CSR/ESGページ",
        "checks": [
            {"key": "csr_content", "label": "CSR/ESG/SDGs取組", "max": 3,
             "check": _check_csr_content},
        ],
    },
}


# ==========================================================================
# 全ページ共通チェック
# ==========================================================================

def _add_common_checks(all_scores: dict, structure: dict, robots: dict,
                       llms: dict, pagespeed: dict, sitemap: dict) -> None:
    """全ページ共通のテクニカルチェック項目を追加。"""
    content = structure.get("content_text", "") or ""
    raw_html = (structure.get("raw_html", "") or "").lower()

    # --- 信頼性系 (common_credibility_) ---

    # 認証・許認可
    cert_keywords = ["ISO", "プライバシーマーク", "Pマーク", "ISMS", "認証", "認定", "ライセンス", "許可番号"]
    cert_count = _has_keywords(content, cert_keywords)
    if cert_count >= 3:
        s = 3
    elif cert_count >= 2:
        s = 2
    elif cert_count >= 1:
        s = 1
    else:
        s = 0
    all_scores["common_credibility_cert"] = {
        "score": s, "max": 3, "label": "認証・許認可",
        "reason": f"認証・許認可 {cert_count}種検出",
        "method": "HTML実測", "confidence": "高",
    }

    # 受賞・実績
    award_keywords = ["受賞", "表彰", "ランキング", "選定", "Award", "GOOD DESIGN"]
    award_count = _has_keywords(content, award_keywords)
    if award_count >= 2:
        s = 3
    elif award_count >= 1:
        s = 2
    else:
        s = 0
    all_scores["common_credibility_awards"] = {
        "score": s, "max": 3, "label": "受賞・表彰",
        "reason": f"受賞・表彰 {award_count}種検出",
        "method": "HTML実測", "confidence": "高",
    }

    # メディア掲載
    media_keywords = ["メディア掲載", "プレスリリース", "新聞", "テレビ", "雑誌", "PR TIMES", "報道"]
    media_count = _has_keywords(content, media_keywords)
    if media_count >= 2:
        s = 3
    elif media_count >= 1:
        s = 2
    else:
        s = 0
    all_scores["common_credibility_media"] = {
        "score": s, "max": 3, "label": "メディア掲載",
        "reason": f"メディア掲載 {media_count}種検出",
        "method": "HTML実測", "confidence": "高",
    }

    # 上場情報
    listing_keywords = ["上場", "証券コード", "東証", "プライム", "スタンダード", "グロース"]
    listing_count = _has_keywords(content, listing_keywords)
    if listing_count >= 2:
        s = 3
    elif listing_count >= 1:
        s = 2
    else:
        s = 0
    all_scores["common_credibility_listing"] = {
        "score": s, "max": 3, "label": "上場情報",
        "reason": f"上場・株式情報 {listing_count}種検出",
        "method": "HTML実測", "confidence": "高",
    }

    # --- ブランド系 (common_brand_) ---

    # SNSリンク
    sns_patterns = {
        "x_twitter": ["twitter.com", "x.com"],
        "facebook": ["facebook.com"],
        "instagram": ["instagram.com"],
        "linkedin": ["linkedin.com/company"],
        "youtube": ["youtube.com/@", "youtube.com/channel", "youtube.com/c/"],
        "note": ["note.com"],
    }
    sns_count = sum(1 for patterns in sns_patterns.values() if any(p in raw_html for p in patterns))
    if sns_count >= 4:
        s = 4
    elif sns_count >= 3:
        s = 3
    elif sns_count >= 2:
        s = 2
    elif sns_count >= 1:
        s = 1
    else:
        s = 0
    all_scores["common_brand_sns"] = {
        "score": s, "max": 4, "label": "SNSリンク",
        "reason": f"SNS公式アカウント {sns_count}種検出",
        "method": "HTML実測", "confidence": "高",
    }

    # sameAs構造化データ
    org = _find_organization_jsonld(structure)
    same_as = []
    if org and org.get("sameAs"):
        same_as = org["sameAs"] if isinstance(org["sameAs"], list) else [org["sameAs"]]
    if len(same_as) >= 4:
        s = 3
    elif len(same_as) >= 2:
        s = 2
    elif len(same_as) >= 1:
        s = 1
    else:
        s = 0
    all_scores["common_brand_sameas"] = {
        "score": s, "max": 3, "label": "sameAs構造化データ",
        "reason": f"sameAs {len(same_as)}件",
        "method": "JSON-LD実測", "confidence": "高",
    }

    # --- テクニカル系 (common_tech_) ---

    # ロゴ・OGP・ファビコン
    has_logo = bool(re.search(r'<img[^>]+(?:logo|ロゴ)', raw_html))
    has_og_image = "og:image" in raw_html
    has_favicon = ("rel=\"icon\"" in raw_html) or ("rel='icon'" in raw_html) or ("favicon" in raw_html)
    brand_count = sum([has_logo, has_og_image, has_favicon])
    if brand_count == 3:
        s = 3
    elif brand_count == 2:
        s = 2
    elif brand_count == 1:
        s = 1
    else:
        s = 0
    all_scores["common_tech_brand_assets"] = {
        "score": s, "max": 3, "label": "ブランド素材(ロゴ/OGP/favicon)",
        "reason": f"ロゴ:{has_logo} OG:{has_og_image} favicon:{has_favicon}",
        "method": "HTML実測", "confidence": "高",
    }

    # viewport(モバイル対応)
    has_viewport = bool(structure.get("viewport"))
    all_scores["common_tech_viewport"] = {
        "score": 1 if has_viewport else 0, "max": 1,
        "label": "モバイル対応",
        "reason": f"viewport: {'あり' if has_viewport else 'なし'}",
        "method": "HTML実測", "confidence": "高",
    }

    # canonical
    has_canonical = bool(structure.get("canonical"))
    all_scores["common_tech_canonical"] = {
        "score": 1 if has_canonical else 0, "max": 1,
        "label": "canonical",
        "reason": f"canonical: {structure.get('canonical', 'なし')[:50]}",
        "method": "HTML実測", "confidence": "高",
    }


# ==========================================================================
# カテゴリ集計
# ==========================================================================

def _calculate_categories(all_scores: dict) -> dict:
    """各チェック項目のキーのプレフィックスでカテゴリに振り分け。"""
    categories = {}
    for cat_key, cat_def in CATEGORY_DEFINITIONS.items():
        categories[cat_key] = {
            "label": cat_def["label"],
            "score": 0,
            "max": cat_def["max"],
        }

    for key, val in all_scores.items():
        mapped_cat = None
        for prefix, cat_key in CATEGORY_MAP.items():
            if key.startswith(prefix):
                mapped_cat = cat_key
                break
        if mapped_cat and mapped_cat in categories:
            categories[mapped_cat]["score"] += val.get("score", 0)

    # スコアがmaxを超えないようにキャップ
    for cat_key, cat_data in categories.items():
        cat_data["score"] = min(cat_data["score"], cat_data["max"])

    return categories


# ==========================================================================
# メイン: score_page()
# ==========================================================================

def score_page(structure: dict, robots: dict, llms: dict, pagespeed: dict, sitemap: dict,
               role: str = "other") -> tuple[dict, dict, dict]:
    """ページの役割に応じた基準でスコアリング。

    role: page_classifier.classify_page() で判定されたロール。
          "top", "about", "business", "ir", "news", "contact", "faq",
          "privacy", "csr", "other" のいずれか。
    """
    all_scores = {}

    # 1. ロール固有のチェック実行
    role_req = ROLE_REQUIREMENTS.get(role, {})
    for check_def in role_req.get("checks", []):
        key = check_def["key"]
        result = check_def["check"](structure)
        all_scores[key] = {
            "score": min(result["score"], check_def["max"]),
            "max": check_def["max"],
            "label": check_def["label"],
            "reason": result.get("reason", ""),
            "role": role,
            "page_specific": True,
            "method": "HTML実測",
            "confidence": "高",
        }

    # 2. 全ページ共通のチェック
    _add_common_checks(all_scores, structure, robots, llms, pagespeed, sitemap)

    # 3. カテゴリ集計
    categories = _calculate_categories(all_scores)

    # 4. 総合スコア
    total_score = sum(c["score"] for c in categories.values())
    grade_result = grade_from_score(total_score)
    total = {"total": total_score, "grade": grade_result["grade"], "label": grade_result["label"]}

    return all_scores, categories, total


# ==========================================================================
# score_site() — サイト全体の構造完全性スコア
# ==========================================================================

# 必須ロールと推奨ロール
_REQUIRED_ROLES = ["top", "about", "contact"]
_RECOMMENDED_ROLES = ["business", "ir", "news", "faq", "privacy", "csr"]

# 構造化データのあるべき配置
_SCHEMA_EXPECTATIONS = {
    "Organization": {"should_be_on": "about", "importance": "S"},
    "WebSite": {"should_be_on": "top", "importance": "S"},
    "FAQPage": {"should_be_on": "faq", "importance": "A"},
}


def score_site(page_results: list[dict], classified_pages: list[dict]) -> dict:
    """サイト全体の構造完全性を評価。

    page_results: 各ページの分析結果リスト。各要素は以下のキーを想定:
        - url: str
        - role: str
        - all_scores: dict
        - categories: dict
        - total: dict
        - structure: dict (オプション)

    classified_pages: classify_pages() でロール付けされたリスト。各要素は:
        - url: str
        - role: str

    戻り値: サイト全体の診断結果dict。
    """
    # ロールごとのページを集計
    role_to_pages = {}
    for cp in classified_pages:
        r = cp.get("role", "other")
        if r not in role_to_pages:
            role_to_pages[r] = []
        role_to_pages[r].append(cp.get("url", ""))

    # 必須ロールの存在チェック
    required_found = [r for r in _REQUIRED_ROLES if r in role_to_pages]
    required_missing = [r for r in _REQUIRED_ROLES if r not in role_to_pages]

    # 推奨ロールの存在チェック
    recommended_found = [r for r in _RECOMMENDED_ROLES if r in role_to_pages]
    recommended_missing = [r for r in _RECOMMENDED_ROLES if r not in role_to_pages]

    # 構造完全性スコア (100点満点)
    # 必須: 各20点 = 60点
    # 推奨: 各 ~6.67点 = 40点
    required_score = len(required_found) * 20
    recommended_score = round(len(recommended_found) * (40 / max(len(_RECOMMENDED_ROLES), 1)))
    completeness_score = min(required_score + recommended_score, 100)

    # ロール別スコア集計
    role_scores = {}
    for pr in page_results:
        r = pr.get("role", "other")
        total_info = pr.get("total", {})
        all_sc = pr.get("all_scores", {})
        # 未達項目を抽出
        issues = []
        for k, v in all_sc.items():
            if v.get("page_specific") and v.get("score", 0) < v.get("max", 1):
                issues.append({
                    "key": k,
                    "label": v.get("label", k),
                    "score": v.get("score", 0),
                    "max": v.get("max", 0),
                    "reason": v.get("reason", ""),
                })
        role_scores[r] = {
            "url": pr.get("url", ""),
            "score": total_info.get("total", 0),
            "grade": total_info.get("grade", "D"),
            "issues": issues,
        }

    # ページ別改善提案
    page_recommendations = []
    # 不足ロールに対する「新規作成」提案
    for r in required_missing:
        role_def = ROLE_REQUIREMENTS.get(r, {})
        page_recommendations.append({
            "role": r,
            "role_label": role_def.get("label", r),
            "action": "新規作成",
            "priority": "S",
            "reason": f"必須ページ（{role_def.get('label', r)}）が見つかりません",
        })
    for r in recommended_missing:
        role_def = ROLE_REQUIREMENTS.get(r, {})
        page_recommendations.append({
            "role": r,
            "role_label": role_def.get("label", r),
            "action": "新規作成",
            "priority": "A" if r in ("business", "news") else "B",
            "reason": f"推奨ページ（{role_def.get('label', r)}）が見つかりません",
        })

    # 既存ページのスコアが低い場合の改善提案
    for r, rs in role_scores.items():
        for issue in rs.get("issues", []):
            if issue["score"] == 0:
                page_recommendations.append({
                    "role": r,
                    "role_label": ROLE_REQUIREMENTS.get(r, {}).get("label", r),
                    "action": f"{issue['label']}を追加",
                    "priority": "S" if issue["max"] >= 4 else "A",
                    "url": rs.get("url", ""),
                    "reason": issue.get("reason", ""),
                })

    # スキーマ配置マップ
    schema_map = {}
    for schema_type, expectation in _SCHEMA_EXPECTATIONS.items():
        found_on = []
        for pr in page_results:
            st = pr.get("structure", {})
            if st and _find_jsonld_type(st, schema_type):
                found_on.append(pr.get("url", ""))
        expected_role = expectation["should_be_on"]
        if found_on:
            status = "ok"
        elif expected_role in required_missing + recommended_missing:
            status = "page_missing"
        else:
            status = "missing"
        schema_map[schema_type] = {
            "should_be_on": expected_role,
            "found_on": found_on,
            "status": status,
            "importance": expectation["importance"],
        }

    # サイト全体スコア — 各ロールのスコア加重平均 + 構造完全性
    if role_scores:
        page_avg = sum(rs["score"] for rs in role_scores.values()) / len(role_scores)
    else:
        page_avg = 0
    site_total_score = round(page_avg * 0.6 + completeness_score * 0.4)
    site_grade = grade_from_score(site_total_score)

    return {
        "structure_completeness": {
            "score": completeness_score,
            "max": 100,
            "required_found": required_found,
            "required_missing": required_missing,
            "recommended_found": recommended_found,
            "recommended_missing": recommended_missing,
        },
        "role_scores": role_scores,
        "page_recommendations": page_recommendations,
        "schema_map": schema_map,
        "site_total": {
            "total": site_total_score,
            "grade": site_grade["grade"],
            "label": site_grade["label"],
        },
    }


# ==========================================================================
# 改善提案
# ==========================================================================

def generate_improvements(all_scores, structure, url, competitors=None, comparison=None,
                          role: str = "other", site_diagnosis: dict = None) -> dict:
    """コーポレートサイト特化の改善提案。

    site_diagnosis が渡された場合 = サイト全体の改善提案を生成
    site_diagnosis が None = 個別ページの改善提案を生成
    """
    quick_wins = []
    strategic = []
    technical_debt = []
    content_strategy = []

    role_label = ROLE_REQUIREMENTS.get(role, {}).get("label", "ページ")

    # ---------- サイト全体モード ----------
    if site_diagnosis is not None:
        # 欠落ページの作成提案
        for rec in site_diagnosis.get("page_recommendations", []):
            if rec.get("action") == "新規作成":
                quick_wins.append({
                    "priority": rec.get("priority", "A"),
                    "title": f"{rec.get('role_label', rec.get('role'))}ページの新規作成",
                    "target_role": rec.get("role"),
                    "category": "サイト構造",
                    "impact": "大",
                    "kpi": "サイト構造完全性スコア",
                    "why": rec.get("reason", ""),
                    "steps": [
                        f"1. {rec.get('role_label', '')}ページを作成",
                        "2. 適切な構造化データ（JSON-LD）を実装",
                        "3. グローバルナビゲーションからリンク",
                        "4. sitemap.xmlに追加",
                    ],
                })

        # スキーマ未実装の提案
        for schema_type, sm in site_diagnosis.get("schema_map", {}).items():
            if sm["status"] in ("missing", "page_missing"):
                quick_wins.append({
                    "priority": sm.get("importance", "A"),
                    "title": f"{schema_type} JSON-LD を{ROLE_REQUIREMENTS.get(sm['should_be_on'], {}).get('label', sm['should_be_on'])}ページに追加",
                    "target_role": sm["should_be_on"],
                    "category": "構造化データ",
                    "impact": "大",
                    "kpi": "AI検索でのナレッジパネル表示・企業情報引用率",
                    "why": f"{schema_type} JSON-LDはAI検索で企業情報を正しく認識させるために重要です",
                    "steps": [
                        f"1. {sm['should_be_on']}ページに{schema_type} JSON-LDを追加",
                        "2. Schema Markup Validatorで検証",
                    ],
                })

        # 既存ページの個別改善提案
        for rec in site_diagnosis.get("page_recommendations", []):
            if rec.get("action") != "新規作成" and rec.get("priority") == "S":
                quick_wins.append({
                    "priority": "S",
                    "title": f"{rec.get('role_label', '')}ページ: {rec.get('action', '')}",
                    "target_page": rec.get("url", ""),
                    "target_role": rec.get("role"),
                    "category": "コンテンツ改善",
                    "impact": "大",
                    "kpi": "該当ロールスコア向上",
                    "why": rec.get("reason", ""),
                    "steps": [
                        f"1. {rec.get('url', '')} を改修",
                        f"2. {rec.get('action', '')}",
                        "3. 変更後にスコア再測定",
                    ],
                })

        return {
            "quick_wins": quick_wins,
            "strategic": strategic,
            "technical_debt": technical_debt,
            "content_strategy": content_strategy,
            "competitor_informed": [],
            "measurement_plan": [
                {"metric": "サイト構造完全性スコア", "target": "80点以上", "tool": "AIO診断ツール"},
                {"metric": "Organization JSON-LD validation", "target": "エラー0件", "tool": "Rich Results Test"},
                {"metric": "ナレッジパネル表示", "target": "企業名検索でパネル出現", "tool": "Google検索"},
                {"metric": "AI検索引用率", "target": "競合比+30%", "tool": "Otterly / Perplexity手動確認"},
            ],
        }

    # ---------- 個別ページモード ----------

    # Quick Win 1: Organization JSON-LD (aboutロール向け)
    about_org = all_scores.get("about_org_jsonld", {})
    if about_org and about_org.get("score", 999) < about_org.get("max", 5):
        quick_wins.append({
            "priority": "S",
            "title": "会社概要ページに Organization JSON-LD 完全実装",
            "target_page": url,
            "target_role": role,
            "category": "構造化データ",
            "impact": "大",
            "kpi": "AI検索でのナレッジパネル表示・企業情報引用率",
            "why": "Organization JSON-LDはGoogle・ChatGPT・Perplexityが企業情報を理解する最重要シグナル。これがないとAI検索で企業概要が正しく引用されず、ナレッジパネルにも表示されません。",
            "steps": [
                "1. 必須項目（@type, name, url, logo, address, telephone）を準備",
                "2. 推奨項目（sameAs[SNS全URL], foundingDate, numberOfEmployees, founder, taxID）を追加",
                "3. <head>内に<script type=\"application/ld+json\">で配置",
                "4. Schema Markup Validatorで検証",
                "5. Google Search Consoleでカバレッジ確認",
            ],
            "before": "<!-- Organization構造化データなし -->",
            "after": '''<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Corporation",
  "name": "株式会社○○",
  "alternateName": "○○",
  "url": "https://example.com",
  "logo": "https://example.com/logo.png",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "○○1-2-3",
    "addressLocality": "千代田区",
    "addressRegion": "東京都",
    "postalCode": "100-0001",
    "addressCountry": "JP"
  },
  "telephone": "+81-3-1234-5678",
  "foundingDate": "2010-04-01",
  "numberOfEmployees": {"@type": "QuantitativeValue", "value": 150},
  "founder": {"@type": "Person", "name": "代表者名"},
  "sameAs": [
    "https://twitter.com/example",
    "https://www.facebook.com/example",
    "https://www.linkedin.com/company/example",
    "https://www.youtube.com/@example"
  ]
}
</script>''',
            "validation": "Schema.org Validator・Rich Results Test・Google Search Console「拡張」レポート",
        })

    # Quick Win 2: NAP情報 (aboutロール向け)
    about_nap = all_scores.get("about_nap", {})
    if about_nap and about_nap.get("score", 999) < about_nap.get("max", 4):
        quick_wins.append({
            "priority": "S",
            "title": f"{role_label}: NAP情報（社名・住所・電話）を全ページフッターに統一掲載",
            "target_page": url,
            "target_role": role,
            "category": "基本情報",
            "impact": "大",
            "kpi": "ローカルSEO・Googleビジネスプロフィール連携",
            "why": "NAP情報の一貫性はローカル検索順位に直結。複数ページ・GBP・SNSでの記載揺れがあると評価が分散します。",
            "steps": [
                "1. 正式社名（株式会社の前後を含む）を1パターンに統一",
                "2. 住所表記（番地のハイフン、ビル名）を全媒体で揃える",
                "3. 電話番号フォーマット統一（03-1234-5678 形式）",
                "4. フッターコンポーネント化して全ページに配置",
                "5. Googleビジネスプロフィール・SNSプロフィールも同形式に修正",
            ],
            "before": "ページごとにNAP表記がバラバラ／フッターに住所なし",
            "after": '''<footer>
  <address>
    <strong>株式会社サンプル</strong><br>
    〒100-0001 東京都千代田区○○1-2-3 ○○ビル5F<br>
    TEL: 03-1234-5678 / FAX: 03-1234-5679
  </address>
</footer>''',
            "validation": "全ページ共通フッター表示確認・GBP情報との完全一致",
        })

    # Quick Win 3: WebSite JSON-LD (topロール向け)
    top_ws = all_scores.get("top_website_jsonld", {})
    if top_ws and top_ws.get("score", 999) < top_ws.get("max", 3):
        quick_wins.append({
            "priority": "S",
            "title": "トップページに WebSite JSON-LD + SearchAction を追加",
            "target_page": url,
            "target_role": "top",
            "category": "構造化データ",
            "impact": "大",
            "kpi": "サイトリンク検索ボックス表示・ブランド検索CTR",
            "why": "WebSite JSON-LDはGoogleのサイトリンク検索ボックス表示に必要。ブランド検索でリッチなSERPを獲得できます。",
            "steps": [
                "1. WebSite JSON-LDをトップページに配置",
                "2. SearchActionで内部検索URLを指定",
                "3. Rich Results Testで検証",
            ],
            "after": '''<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "サイト名",
  "url": "https://example.com",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://example.com/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>''',
            "validation": "Rich Results Test",
        })

    # Quick Win 4: 沿革 (aboutロール向け)
    about_hist = all_scores.get("about_history", {})
    if about_hist and about_hist.get("score", 999) < 2:
        quick_wins.append({
            "priority": "A",
            "title": f"{role_label}: 沿革ページの充実（年表＋写真＋エピソード）",
            "target_page": url,
            "target_role": role,
            "category": "信頼性",
            "impact": "中",
            "kpi": "滞在時間・直帰率・「会社名 沿革」検索流入",
            "why": "創業からの歩みは信頼性の最重要シグナル。AI検索でも「○○社の歴史」「○○社の創業」クエリで引用されやすくなります。",
            "steps": [
                "1. 創業年から現在までの主要マイルストーンを抽出（最低10件）",
                "2. 年・月・出来事・写真の4列で年表化",
                "3. 各時代の代表者コメントや裏話を1-2個追加",
                "4. dl/dt/dd または table で構造化マークアップ",
            ],
        })

    # Quick Win 5: SNS統合
    sns_score = all_scores.get("common_brand_sns", {}).get("score", 999)
    sameas_score = all_scores.get("common_brand_sameas", {}).get("score", 999)
    if sns_score < 3 or sameas_score < 2:
        quick_wins.append({
            "priority": "A",
            "title": f"{role_label}: 公式SNSリンク統合＋sameAs構造化データ",
            "target_page": url,
            "target_role": role,
            "category": "ブランド",
            "impact": "中",
            "kpi": "ナレッジパネルでのSNSアイコン表示・SNSフォロワー流入",
            "why": "sameAsは企業の公式SNS識別シグナル。Googleナレッジパネルで公式アカウントを正しく表示するために必須です。",
            "steps": [
                "1. 自社の全公式SNSアカウントURLを棚卸し（X / Facebook / Instagram / LinkedIn / YouTube / note）",
                "2. フッターにSVGアイコン＋rel=\"me\"でリンク設置",
                "3. Organization JSON-LDのsameAs配列に全URL追加",
                "4. 各SNSプロフィールから自社サイトへ相互リンク",
            ],
        })

    # Quick Win 6: ニュース更新 (newsロール向け)
    news_fresh = all_scores.get("news_freshness", {})
    if news_fresh and news_fresh.get("score", 999) < 3:
        quick_wins.append({
            "priority": "A",
            "title": f"{role_label}: ニュース/お知らせの定期更新運用化（最低月2本）",
            "target_page": url,
            "target_role": role,
            "category": "鮮度",
            "impact": "大",
            "kpi": "クロール頻度・「企業名 ニュース」流入・AI検索引用",
            "why": "更新が止まったコーポレートサイトはGoogleからもAI検索からも「鮮度なし」と判断されます。月2本のプレスリリースでクロール頻度が3倍に。",
            "steps": [
                "1. ニュースカテゴリを5つに整理（プレスリリース/メディア掲載/イベント/採用/その他）",
                "2. 各記事に発行日・更新日（date_published / date_modified）をdatetime属性で明示",
                "3. NewsArticle JSON-LDを各記事に実装",
                "4. RSSフィード配信で外部認知拡大",
            ],
        })

    # Quick Win 7: 事業実績の数値化 (businessロール向け)
    biz_nums = all_scores.get("biz_numbers", {})
    if biz_nums and biz_nums.get("score", 999) < 3:
        quick_wins.append({
            "priority": "A",
            "title": f"{role_label}: 事業実績の数値ファクト集約セクション",
            "target_page": url,
            "target_role": role,
            "category": "信頼性",
            "impact": "大",
            "kpi": "AI検索引用率・コンバージョン率",
            "why": "ChatGPT・Perplexityは具体的な数値ファクトを優先的に引用します。「導入企業3,500社」「シェア国内No.1」のような数字がないと埋もれます。",
            "steps": [
                "1. 主要KPI（取引社数・累計実績・シェア・年間取扱量・顧客満足度）を抽出",
                "2. ファーストビュー直下に「数字で見る○○」セクション配置",
                "3. 各数字に出典・調査年月を併記（信頼性確保）",
                "4. 半年に1回数値更新（鮮度維持）",
            ],
        })

    # FAQPage JSON-LD (faqロール向け)
    faq_jl = all_scores.get("faq_jsonld", {})
    if faq_jl and faq_jl.get("score", 999) < faq_jl.get("max", 3):
        quick_wins.append({
            "priority": "A",
            "title": f"{role_label}: FAQPage JSON-LD を実装",
            "target_page": url,
            "target_role": role,
            "category": "構造化データ",
            "impact": "中",
            "kpi": "FAQ系クエリでのリッチリザルト・AI検索引用",
            "why": "FAQPage JSON-LDは検索結果でのリッチリザルト表示とAI検索での直接引用に効果的です。",
            "steps": [
                "1. FAQを5問以上にまとめる",
                "2. FAQPage JSON-LDを実装",
                "3. Rich Results Testで検証",
            ],
        })

    # 戦略施策
    strategic.extend([
        {
            "priority": "A",
            "title": "代表メッセージ動画＋ロングインタビューの設置",
            "category": "ブランド・E-E-A-T",
            "why": "AI検索時代、企業の「人」と「想い」が引用差別化要因に。代表者の顔・声・哲学を発信する企業ほどAI回答内で名指し引用されやすい。",
            "steps": [
                "代表メッセージ（3分動画＋全文テキスト3,000字）を制作",
                "VideoObject JSON-LD実装でリッチリザルト対応",
                "代表のPerson schema作成（jobTitle・worksFor・sameAs）",
                "経歴・著書・受賞歴を構造化",
            ],
            "impact": "大", "effort": "中",
        },
        {
            "priority": "A",
            "title": "IR情報・適時開示ページの構築（上場企業の場合）",
            "category": "IR",
            "why": "投資家・アナリスト・AI検索ボットが最も探す情報。決算短信・有報・適時開示の構造化は必須。",
            "steps": [
                "決算短信PDFをHTML化（テキスト検索可能に）",
                "Report JSON-LDで構造化",
                "5期分のサマリ表（売上・利益・EPS）を可視化",
                "アナリストカバレッジ・アナリストレポートも掲載",
            ],
            "impact": "大", "effort": "大",
        },
        {
            "priority": "B",
            "title": "サステナビリティ・ESGページ大幅拡充",
            "category": "CSR",
            "why": "AI検索でESG関連クエリが急増中。マテリアリティ・GHG排出量・人的資本情報の開示が引用されやすい。",
            "steps": [
                "マテリアリティマトリクス公開",
                "GHG排出量Scope1/2/3の年次推移",
                "人的資本（女性管理職比率・育休取得率・離職率）の数値開示",
                "TCFDレポートPDFと要約ページ",
            ],
            "impact": "中", "effort": "大",
        },
    ])

    return {
        "quick_wins": quick_wins,
        "strategic": strategic,
        "technical_debt": technical_debt,
        "content_strategy": content_strategy,
        "competitor_informed": [],
        "measurement_plan": [
            {"metric": "Organization JSON-LD validation", "target": "エラー0件", "tool": "Rich Results Test"},
            {"metric": "ナレッジパネル表示", "target": "企業名検索でパネル出現", "tool": "Google検索"},
            {"metric": "ニュース更新頻度", "target": "月2本以上", "tool": "CMS管理画面"},
            {"metric": "AI検索引用率", "target": "競合比+30%", "tool": "Otterly / Perplexity手動確認"},
        ],
    }


# ==========================================================================
# テストクエリ生成（既存のまま維持）
# ==========================================================================

def generate_test_queries(url, keywords, site_title):
    """コーポレートサイト向け商談テストクエリ。"""
    domain = url.split("//")[-1].split("/")[0] if "//" in url else url
    company_name = (site_title.split("｜")[0].split("|")[0].split("-")[0].strip() if site_title else domain)

    return {
        "google_knowledge_panel": [
            f"{company_name}",
            f"{company_name} 会社概要",
            f"{company_name} 代表",
            f"{company_name} 本社",
        ],
        "chatgpt_corporate": [
            f"{company_name}という会社について教えて",
            f"{company_name}の事業内容と強みは？",
            f"{company_name}の沿革と創業ストーリー",
            f"{company_name}と同業の主要競合5社を比較して",
        ],
        "perplexity_factcheck": [
            f"{company_name} 売上 従業員数",
            f"{company_name} 上場 証券コード",
            f"{company_name} 受賞 認証",
        ],
        "google_for_business": [
            f"{keywords[0] if keywords else '業界'} 企業 おすすめ",
            f"{keywords[0] if keywords else '業界'} 大手 一覧",
            f"{company_name} 評判 口コミ",
        ],
    }
