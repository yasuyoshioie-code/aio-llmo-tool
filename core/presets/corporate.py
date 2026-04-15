"""コーポレートサイト向けプリセット — 企業情報網羅性・信頼性・ステークホルダー対応を評価"""

import re
from core.content_scorer import generate_test_queries_python


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


# ---------- ヘルパー ----------

def _find_organization_jsonld(structure: dict) -> dict | None:
    """Organization / Corporation 系JSON-LDを抽出。"""
    for jsonld in structure.get("jsonld_items", []):
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


def _make_score(score: int, max_score: int, reason: str, method: str = "HTML実測", confidence: str = "高") -> dict:
    return {
        "score": score, "max": max_score,
        "reason": reason,
        "method": method, "confidence": confidence,
    }


# ---------- 1. 企業基本情報 (20点) ----------

def _score_company_info(structure: dict, content: str) -> dict:
    scores = {}
    org = _find_organization_jsonld(structure)

    # 1-1 会社概要ページ存在シグナル / 商号・社名 (4点)
    company_keywords = ["会社概要", "企業情報", "会社案内", "About", "Company", "コーポレート"]
    has_company_section = _has_keywords(content, company_keywords)
    if has_company_section >= 2:
        s = 4
    elif has_company_section >= 1:
        s = 2
    else:
        s = 0
    scores["1-1_company_section"] = _make_score(s, 4, f"会社概要シグナル {has_company_section}種検出")

    # 1-2 NAP情報（名称・住所・電話） (4点)
    has_address = bool(re.search(r"〒?\d{3}-?\d{4}", content)) or "住所" in content or "所在地" in content
    has_phone = bool(re.search(r"0\d{1,4}-?\d{1,4}-?\d{4}", content)) or "TEL" in content or "電話" in content
    has_org_name = bool(structure.get("title")) or "株式会社" in content or "有限会社" in content or "合同会社" in content
    nap_count = sum([has_address, has_phone, has_org_name])
    s = nap_count * 4 // 3 + (1 if nap_count == 3 else 0)  # 3つ揃えば4点
    s = 4 if nap_count == 3 else (2 if nap_count == 2 else (1 if nap_count == 1 else 0))
    scores["1-2_nap"] = _make_score(s, 4, f"NAP情報 {nap_count}/3項目検出（住所:{has_address} 電話:{has_phone} 社名:{has_org_name}）")

    # 1-3 設立日・代表者・資本金 (4点)
    detail_keywords = ["設立", "創業", "代表取締役", "資本金", "従業員数", "事業年度"]
    detail_count = _has_keywords(content, detail_keywords)
    if detail_count >= 4: s = 4
    elif detail_count >= 2: s = 2
    elif detail_count >= 1: s = 1
    else: s = 0
    scores["1-3_company_details"] = _make_score(s, 4, f"会社詳細 {detail_count}/6項目検出")

    # 1-4 沿革・歴史 (4点)
    has_history = ("沿革" in content) or ("歴史" in content) or ("History" in content)
    year_mentions = len(re.findall(r"(19|20)\d{2}年", content))
    if has_history and year_mentions >= 5: s = 4
    elif has_history and year_mentions >= 1: s = 2
    elif year_mentions >= 3: s = 1
    else: s = 0
    scores["1-4_history"] = _make_score(s, 4, f"沿革記述: {has_history} / 年号記述 {year_mentions}件")

    # 1-5 Organization JSON-LD構造化データ (4点)
    if org:
        required = ["name", "url", "logo"]
        recommended = ["address", "telephone", "sameAs", "foundingDate", "numberOfEmployees"]
        req_count = sum(1 for k in required if org.get(k))
        rec_count = sum(1 for k in recommended if org.get(k))
        if req_count == 3 and rec_count >= 3: s = 4
        elif req_count == 3 and rec_count >= 1: s = 3
        elif req_count == 3: s = 2
        elif req_count >= 2: s = 1
        else: s = 0
        scores["1-5_org_jsonld"] = _make_score(s, 4, f"Organization JSON-LD: 必須{req_count}/3 推奨{rec_count}/5")
    else:
        scores["1-5_org_jsonld"] = _make_score(0, 4, "Organization JSON-LD未実装")

    return scores


# ---------- 2. 信頼性・権威性 (20点) ----------

def _score_credibility(structure: dict, content: str) -> dict:
    scores = {}

    # 2-1 上場情報・株式 (4点)
    listing_keywords = ["上場", "証券コード", "東証", "プライム", "スタンダード", "グロース", "JASDAQ"]
    listing_count = _has_keywords(content, listing_keywords)
    if listing_count >= 2: s = 4
    elif listing_count >= 1: s = 2
    else: s = 0
    scores["2-1_listing"] = _make_score(s, 4, f"上場・株式情報 {listing_count}種")

    # 2-2 認証・許認可 (4点)
    cert_keywords = ["ISO", "プライバシーマーク", "Pマーク", "ISMS", "認証", "認定", "ライセンス", "許可番号"]
    cert_count = _has_keywords(content, cert_keywords)
    if cert_count >= 3: s = 4
    elif cert_count >= 2: s = 3
    elif cert_count >= 1: s = 2
    else: s = 0
    scores["2-2_certifications"] = _make_score(s, 4, f"認証・許認可 {cert_count}種検出")

    # 2-3 受賞・実績 (4点)
    award_keywords = ["受賞", "表彰", "ランキング", "選定", "Award", "GOOD DESIGN", "グッドデザイン"]
    award_count = _has_keywords(content, award_keywords)
    if award_count >= 2: s = 4
    elif award_count >= 1: s = 2
    else: s = 0
    scores["2-3_awards"] = _make_score(s, 4, f"受賞・表彰 {award_count}種")

    # 2-4 取引実績・クライアント (4点)
    client_keywords = ["導入企業", "取引先", "クライアント", "実績", "事例", "Case", "お客様の声", "導入事例"]
    client_count = _has_keywords(content, client_keywords)
    if client_count >= 3: s = 4
    elif client_count >= 2: s = 3
    elif client_count >= 1: s = 2
    else: s = 0
    scores["2-4_clients"] = _make_score(s, 4, f"取引実績シグナル {client_count}種")

    # 2-5 メディア掲載・プレス (4点)
    media_keywords = ["メディア掲載", "プレスリリース", "新聞", "テレビ", "雑誌", "PR TIMES", "報道"]
    media_count = _has_keywords(content, media_keywords)
    if media_count >= 2: s = 4
    elif media_count >= 1: s = 2
    else: s = 0
    scores["2-5_media_coverage"] = _make_score(s, 4, f"メディア掲載 {media_count}種")

    return scores


# ---------- 3. 事業内容の明確性 (15点) ----------

def _score_business(structure: dict, content: str) -> dict:
    scores = {}

    # 3-1 事業セグメント・サービス分類 (5点)
    biz_keywords = ["事業内容", "サービス", "事業領域", "事業セグメント", "プロダクト", "製品", "ソリューション"]
    biz_count = _has_keywords(content, biz_keywords)
    if biz_count >= 3: s = 5
    elif biz_count >= 2: s = 3
    elif biz_count >= 1: s = 2
    else: s = 0
    scores["3-1_business_segments"] = _make_score(s, 5, f"事業説明シグナル {biz_count}種")

    # 3-2 強み・差別化 (5点)
    strength_keywords = ["強み", "特長", "特徴", "他社との違い", "選ばれる理由", "Why", "独自"]
    strength_count = _has_keywords(content, strength_keywords)
    if strength_count >= 3: s = 5
    elif strength_count >= 2: s = 3
    elif strength_count >= 1: s = 2
    else: s = 0
    scores["3-2_strengths"] = _make_score(s, 5, f"強み記述 {strength_count}種")

    # 3-3 数値による事業実績 (5点)
    has_numbers = len(re.findall(r"\d+(?:,\d+)*\s*(?:社|件|名|人|台|店舗|拠点|億|万|％|%)", content))
    if has_numbers >= 5: s = 5
    elif has_numbers >= 3: s = 3
    elif has_numbers >= 1: s = 2
    else: s = 0
    scores["3-3_business_numbers"] = _make_score(s, 5, f"事業実績数値 {has_numbers}件検出")

    return scores


# ---------- 4. IR・ニュース発信 (15点) ----------

def _score_ir_news(structure: dict, content: str) -> dict:
    scores = {}

    # 4-1 IR情報セクション存在 (5点)
    ir_keywords = ["IR", "投資家情報", "決算", "有価証券報告書", "適時開示", "株主"]
    ir_count = _has_keywords(content, ir_keywords)
    if ir_count >= 3: s = 5
    elif ir_count >= 2: s = 3
    elif ir_count >= 1: s = 2
    else: s = 0
    scores["4-1_ir_section"] = _make_score(s, 5, f"IR情報シグナル {ir_count}種")

    # 4-2 ニュース・プレスリリースの鮮度 (5点)
    has_news = ("ニュース" in content) or ("お知らせ" in content) or ("News" in content) or ("プレスリリース" in content)
    # 直近1年以内の年号があるか
    recent_year = bool(re.search(r"202[4-6]年", content))
    if has_news and recent_year: s = 5
    elif has_news: s = 3
    elif recent_year: s = 2
    else: s = 0
    scores["4-2_news_freshness"] = _make_score(s, 5, f"ニュースセクション:{has_news} 直近年号:{recent_year}")

    # 4-3 更新頻度シグナル（日付の数） (5点)
    date_count = len(re.findall(r"\d{4}[/.年-]\d{1,2}[/.月-]\d{1,2}", content))
    if date_count >= 10: s = 5
    elif date_count >= 5: s = 3
    elif date_count >= 1: s = 2
    else: s = 0
    scores["4-3_update_frequency"] = _make_score(s, 5, f"日付記述 {date_count}件")

    return scores


# ---------- 5. ステークホルダー対応 (15点) ----------

def _score_stakeholder(structure: dict, content: str) -> dict:
    scores = {}

    # 5-1 採用情報への導線 (3点)
    recruit_keywords = ["採用", "求人", "Recruit", "Career", "募集"]
    recruit_count = _has_keywords(content, recruit_keywords)
    if recruit_count >= 2: s = 3
    elif recruit_count >= 1: s = 2
    else: s = 0
    scores["5-1_recruit_link"] = _make_score(s, 3, f"採用導線 {recruit_count}種")

    # 5-2 お問い合わせフォーム/連絡先 (3点)
    contact_keywords = ["お問い合わせ", "Contact", "問い合わせ", "ご相談"]
    contact_count = _has_keywords(content, contact_keywords)
    has_form = "form" in (structure.get("raw_html", "") or "").lower()
    if contact_count >= 2 or (contact_count >= 1 and has_form): s = 3
    elif contact_count >= 1: s = 2
    else: s = 0
    scores["5-2_contact"] = _make_score(s, 3, f"問合せシグナル {contact_count}種 / フォーム:{has_form}")

    # 5-3 CSR・サステナビリティ・ESG (3点)
    csr_keywords = ["CSR", "サステナビリティ", "Sustainability", "SDGs", "ESG", "社会貢献", "環境"]
    csr_count = _has_keywords(content, csr_keywords)
    if csr_count >= 3: s = 3
    elif csr_count >= 1: s = 2
    else: s = 0
    scores["5-3_csr"] = _make_score(s, 3, f"CSR/ESG {csr_count}種")

    # 5-4 プライバシーポリシー・利用規約 (3点)
    legal_keywords = ["プライバシーポリシー", "個人情報保護方針", "利用規約", "サイトポリシー", "免責事項"]
    legal_count = _has_keywords(content, legal_keywords)
    if legal_count >= 3: s = 3
    elif legal_count >= 2: s = 2
    elif legal_count >= 1: s = 1
    else: s = 0
    scores["5-4_legal"] = _make_score(s, 3, f"法務系ページ {legal_count}種")

    # 5-5 多言語対応 (3点)
    has_en = bool(re.search(r"\b(English|EN)\b", content)) or "/en/" in (structure.get("raw_html", "") or "").lower()
    has_zh = ("中文" in content) or ("简体" in content) or ("/zh/" in (structure.get("raw_html", "") or "").lower())
    lang_count = sum([has_en, has_zh])
    if lang_count >= 2: s = 3
    elif lang_count >= 1: s = 2
    else: s = 0
    scores["5-5_multilingual"] = _make_score(s, 3, f"多言語対応 {lang_count}言語")

    return scores


# ---------- 6. ブランド・SNS (15点) ----------

def _score_brand_sns(structure: dict, content: str) -> dict:
    scores = {}
    raw_html = (structure.get("raw_html", "") or "").lower()

    # 6-1 SNSリンク（公式アカウント） (5点)
    sns_patterns = {
        "x_twitter": ["twitter.com", "x.com"],
        "facebook": ["facebook.com"],
        "instagram": ["instagram.com"],
        "linkedin": ["linkedin.com/company"],
        "youtube": ["youtube.com/@", "youtube.com/channel", "youtube.com/c/"],
        "note": ["note.com"],
    }
    sns_count = sum(1 for patterns in sns_patterns.values() if any(p in raw_html for p in patterns))
    if sns_count >= 4: s = 5
    elif sns_count >= 3: s = 4
    elif sns_count >= 2: s = 3
    elif sns_count >= 1: s = 2
    else: s = 0
    scores["6-1_sns_links"] = _make_score(s, 5, f"SNS公式アカウント {sns_count}種検出")

    # 6-2 sameAs構造化データ (5点)
    org = _find_organization_jsonld(structure)
    same_as = []
    if org and org.get("sameAs"):
        same_as = org["sameAs"] if isinstance(org["sameAs"], list) else [org["sameAs"]]
    if len(same_as) >= 4: s = 5
    elif len(same_as) >= 2: s = 3
    elif len(same_as) >= 1: s = 2
    else: s = 0
    scores["6-2_sameas"] = _make_score(s, 5, f"sameAs {len(same_as)}件")

    # 6-3 ロゴ・OGP・ファビコン (5点)
    has_logo = bool(re.search(r'<img[^>]+(?:logo|ロゴ)', raw_html))
    has_og_image = ("og:image" in raw_html)
    has_favicon = ("rel=\"icon\"" in raw_html) or ("rel='icon'" in raw_html) or ("favicon" in raw_html)
    brand_count = sum([has_logo, has_og_image, has_favicon])
    if brand_count == 3: s = 5
    elif brand_count == 2: s = 3
    elif brand_count == 1: s = 2
    else: s = 0
    scores["6-3_brand_assets"] = _make_score(s, 5, f"ブランド素材 ロゴ:{has_logo} OG:{has_og_image} favicon:{has_favicon}")

    return scores


# ---------- メイン ----------

def score_page(structure, robots, llms, pagespeed, sitemap):
    """コーポレートサイト評価。100点満点。"""
    content = structure.get("content_text", "") or ""

    all_scores = {}
    all_scores.update(_score_company_info(structure, content))
    all_scores.update(_score_credibility(structure, content))
    all_scores.update(_score_business(structure, content))
    all_scores.update(_score_ir_news(structure, content))
    all_scores.update(_score_stakeholder(structure, content))
    all_scores.update(_score_brand_sns(structure, content))

    # カテゴリ集計
    categories = {}
    cat_mapping = {
        "1": "1_company_info",
        "2": "2_credibility",
        "3": "3_business",
        "4": "4_ir_news",
        "5": "5_stakeholder",
        "6": "6_brand_sns",
    }
    for key, val in all_scores.items():
        prefix = key.split("-")[0]
        cat_key = cat_mapping.get(prefix)
        if not cat_key:
            continue
        if cat_key not in categories:
            categories[cat_key] = {
                "label": CATEGORY_DEFINITIONS[cat_key]["label"],
                "score": 0,
                "max": CATEGORY_DEFINITIONS[cat_key]["max"],
            }
        categories[cat_key]["score"] += val["score"]

    total_score = sum(c["score"] for c in categories.values())

    if total_score >= 85: grade = "S"
    elif total_score >= 70: grade = "A"
    elif total_score >= 55: grade = "B"
    elif total_score >= 40: grade = "C"
    else: grade = "D"

    grade_labels = {
        "S": "卓越: 業界トップクラスの企業情報網羅性・信頼性",
        "A": "優良: ステークホルダーへの情報開示が充実",
        "B": "標準: 基本情報は揃うが、IR/CSR等の発信が不足",
        "C": "要改善: 企業情報の網羅性・構造化が不十分",
        "D": "危険: コーポレートサイトとして必要情報が大幅不足",
    }

    total = {"total": total_score, "grade": grade, "label": grade_labels[grade]}
    return all_scores, categories, total


def generate_improvements(all_scores, structure, url, competitors=None, comparison=None):
    """コーポレートサイト特化の改善提案。"""
    quick_wins = []
    strategic = []

    # Quick Win 1: Organization JSON-LD
    if all_scores.get("1-5_org_jsonld", {}).get("score", 0) < 4:
        quick_wins.append({
            "priority": "S",
            "title": "Organization JSON-LD完全実装（必須5項目+推奨5項目）",
            "category": "構造化データ",
            "impact": "大",
            "kpi": "AI検索でのナレッジパネル表示・企業情報引用率",
            "why": "Organization JSON-LDはGoogle・ChatGPt・Perplexityが企業情報を理解する最重要シグナル。これがないとAI検索で企業概要が正しく引用されず、ナレッジパネルにも表示されません。",
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

    # Quick Win 2: NAP情報
    if all_scores.get("1-2_nap", {}).get("score", 0) < 4:
        quick_wins.append({
            "priority": "S",
            "title": "NAP情報（社名・住所・電話）を全ページフッターに統一掲載",
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

    # Quick Win 3: 沿革
    if all_scores.get("1-4_history", {}).get("score", 0) < 3:
        quick_wins.append({
            "priority": "A",
            "title": "沿革ページの新設（年表＋写真＋エピソード）",
            "category": "信頼性",
            "impact": "中",
            "kpi": "滞在時間・直帰率・「会社名 沿革」検索流入",
            "why": "創業からの歩みは信頼性の最重要シグナル。AI検索でも「○○社の歴史」「○○社の創業」クエリで引用されやすくなります。",
            "steps": [
                "1. 創業年から現在までの主要マイルストーンを抽出（最低10件）",
                "2. 年・月・出来事・写真の4列で年表化",
                "3. 各時代の代表者コメントや裏話を1-2個追加",
                "4. dl/dt/dd または table で構造化マークアップ",
                "5. 上場・受賞・新規事業立ち上げは特に詳しく",
            ],
            "before": "沿革ページなし、または年と一行説明のみ",
            "after": "年表形式＋各エポックの写真＋エピソード（300字×10エポック以上）",
            "validation": "/company/history ページ新設・グローバルナビから2クリック以内",
        })

    # Quick Win 4: SNS統合
    if all_scores.get("6-1_sns_links", {}).get("score", 0) < 4 or all_scores.get("6-2_sameas", {}).get("score", 0) < 3:
        quick_wins.append({
            "priority": "A",
            "title": "公式SNSリンク統合＋sameAs構造化データ",
            "category": "ブランド",
            "impact": "中",
            "kpi": "ナレッジパネルでのSNSアイコン表示・SNSフォロワー流入",
            "why": "sameAsは企業の公式SNS識別シグナル。Googleナレッジパネルで公式アカウントを正しく表示するために必須です。",
            "steps": [
                "1. 自社の全公式SNSアカウントURLを棚卸し（X / Facebook / Instagram / LinkedIn / YouTube / note）",
                "2. フッターにSVGアイコン＋rel=\"me\"でリンク設置",
                "3. Organization JSON-LDのsameAs配列に全URL追加",
                "4. 各SNSプロフィールから自社サイトへ相互リンク",
                "5. SNSアイコンはaria-label付与でアクセシビリティ確保",
            ],
            "before": "SNSリンクなし、またはトップページにバナーのみ",
            "after": "全ページフッターにSNSアイコン＋sameAs構造化データ統合",
            "validation": "Rich Results Test・ナレッジパネル表示確認",
        })

    # Quick Win 5: ニュース・更新シグナル
    if all_scores.get("4-2_news_freshness", {}).get("score", 0) < 4:
        quick_wins.append({
            "priority": "A",
            "title": "ニュース/お知らせの定期更新運用化（最低月2本）",
            "category": "鮮度",
            "impact": "大",
            "kpi": "クロール頻度・「企業名 ニュース」流入・AI検索引用",
            "why": "更新が止まったコーポレートサイトはGoogleからもAI検索からも「鮮度なし」と判断されます。月2本のプレスリリースでクロール頻度が3倍に。",
            "steps": [
                "1. ニュースカテゴリを5つに整理（プレスリリース/メディア掲載/イベント/採用/その他）",
                "2. 各記事に発行日・更新日（date_published / date_modified）をdatetime属性で明示",
                "3. NewsArticle JSON-LDを各記事に実装",
                "4. RSSフィード配信で外部認知拡大",
                "5. 月次でPR TIMES・@Pressへの同時配信",
            ],
            "before": "ニュース最新が半年以上前、日付タグなし",
            "after": "月2本以上の更新＋NewsArticle構造化データ＋RSSフィード",
            "validation": "Search Console「クロール統計」で月次クロール数の上昇確認",
        })

    # Quick Win 6: 事業実績の数値化
    if all_scores.get("3-3_business_numbers", {}).get("score", 0) < 4:
        quick_wins.append({
            "priority": "A",
            "title": "事業実績の数値ファクト集約セクション",
            "category": "信頼性",
            "impact": "大",
            "kpi": "AI検索引用率・コンバージョン率",
            "why": "ChatGPt・Perplexityは具体的な数値ファクトを優先的に引用します。「導入企業3,500社」「シェア国内No.1」のような数字がないと埋もれます。",
            "steps": [
                "1. 主要KPI（取引社数・累計実績・シェア・年間取扱量・顧客満足度）を抽出",
                "2. ファーストビュー直下に「数字で見る○○」セクション配置",
                "3. 各数字に出典・調査年月を併記（信頼性確保）",
                "4. アニメーションで数字をカウントアップ（離脱防止）",
                "5. 半年に1回数値更新（鮮度維持）",
            ],
            "before": "「業界トップクラス」「多数の実績」など曖昧表現",
            "after": "「導入3,500社（2026年4月時点）」「業界シェア28.5%（自社調べ）」など具体数値",
            "validation": "ファーストビュー直下に数値セクション設置、最低5項目",
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
        "technical_debt": [],
        "content_strategy": [],
        "competitor_informed": [],
        "measurement_plan": [
            {"metric": "Organization JSON-LD validation", "target": "エラー0件", "tool": "Rich Results Test"},
            {"metric": "ナレッジパネル表示", "target": "企業名検索でパネル出現", "tool": "Google検索"},
            {"metric": "ニュース更新頻度", "target": "月2本以上", "tool": "CMS管理画面"},
            {"metric": "AI検索引用率", "target": "競合比+30%", "tool": "Otterly / Perplexity手動確認"},
        ],
    }


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
