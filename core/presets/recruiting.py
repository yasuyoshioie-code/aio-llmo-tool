"""採用サイト診断プリセット — ロール別スコアリング

ページの役割（ロール）ごとに異なる基準でスコアリング。
6カテゴリ = 100点満点（CATEGORY_DEFINITIONS は変更なし）。

ロール:
  - recruit_top:   採用トップページ
  - job_listing:   求人詳細ページ
  - culture:       企業カルチャーページ
  - benefits:      福利厚生ページ
  - interview:     社員インタビューページ
  - entry:         エントリー/応募ページ
  - faq:           よくある質問ページ
  - other:         上記に該当しないページ（共通チェックのみ）

カテゴリ:
  1. Google for Jobs対応 (20点)
  2. 求人情報の具体性 (20点)
  3. 企業カルチャー・魅力 (15点)
  4. 労働条件・福利厚生 (15点)
  5. 応募UX (15点)
  6. 信頼性・E-E-A-T (15点)
"""

import re

from core.presets.recruiting_cv import analyze_cv  # noqa: F401
from core.scorer import grade_from_score


PRESET_ID = "recruiting"
PRESET_LABEL = "💼 採用ページ"


CATEGORY_DEFINITIONS = {
    "1_jobposting": {"label": "Google for Jobs対応", "max": 20},
    "2_job_specificity": {"label": "求人情報の具体性", "max": 20},
    "3_culture": {"label": "企業カルチャー・魅力", "max": 15},
    "4_conditions": {"label": "労働条件・福利厚生", "max": 15},
    "5_apply_ux": {"label": "応募UX", "max": 15},
    "6_credibility": {"label": "信頼性・E-E-A-T", "max": 15},
}


# ==================================================================
# ロール別チェック定義
# ==================================================================

ROLE_REQUIREMENTS = {
    "recruit_top": {
        "label": "採用トップページ",
        "checks": [
            {"key": "rt_brand_message", "label": "採用ブランドメッセージ", "max": 3,
             "check_fn": "_check_brand_message"},
            {"key": "rt_job_categories", "label": "職種カテゴリ一覧", "max": 3,
             "check_fn": "_check_job_categories"},
            {"key": "rt_navigation", "label": "各ページへの導線", "max": 2,
             "check_fn": "_check_recruit_navigation"},
            {"key": "rt_cta", "label": "応募CTAボタン", "max": 3,
             "check_fn": "_check_cta"},
            {"key": "rt_company_intro", "label": "会社紹介・数字", "max": 3,
             "check_fn": "_check_company_numbers"},
        ],
    },
    "job_listing": {
        "label": "求人詳細ページ",
        "checks": [
            {"key": "jl_jobposting", "label": "JobPosting JSON-LD", "max": 5,
             "check_fn": "_check_jobposting_jsonld"},
            {"key": "jl_required_fields", "label": "必須項目(title/desc/date/org)", "max": 4,
             "check_fn": "_check_jp_required"},
            {"key": "jl_salary", "label": "給与情報の具体性", "max": 4,
             "check_fn": "_check_salary_detail"},
            {"key": "jl_location", "label": "勤務地情報", "max": 3,
             "check_fn": "_check_location"},
            {"key": "jl_skills", "label": "必須/歓迎スキル分離", "max": 3,
             "check_fn": "_check_skills"},
            {"key": "jl_apply_btn", "label": "応募ボタン/directApply", "max": 3,
             "check_fn": "_check_direct_apply"},
        ],
    },
    "culture": {
        "label": "企業カルチャーページ",
        "checks": [
            {"key": "cl_mvv", "label": "MVV(理念/ミッション/ビジョン)", "max": 4,
             "check_fn": "_check_mvv"},
            {"key": "cl_workplace", "label": "職場環境・オフィス紹介", "max": 3,
             "check_fn": "_check_workplace"},
            {"key": "cl_diversity", "label": "多様性・DEI", "max": 3,
             "check_fn": "_check_diversity"},
            {"key": "cl_video", "label": "動画コンテンツ", "max": 3,
             "check_fn": "_check_video"},
        ],
    },
    "benefits": {
        "label": "福利厚生ページ",
        "checks": [
            {"key": "bf_benefit_list", "label": "福利厚生一覧", "max": 4,
             "check_fn": "_check_benefits_list"},
            {"key": "bf_numbers", "label": "数値の具体性(取得率/時間等)", "max": 3,
             "check_fn": "_check_benefit_numbers"},
            {"key": "bf_work_style", "label": "勤務時間・休日・リモート", "max": 3,
             "check_fn": "_check_work_style"},
            {"key": "bf_training", "label": "研修・教育制度", "max": 3,
             "check_fn": "_check_training"},
        ],
    },
    "interview": {
        "label": "社員インタビューページ",
        "checks": [
            {"key": "iv_staff_voices", "label": "社員の声(具体エピソード)", "max": 4,
             "check_fn": "_check_staff_voices"},
            {"key": "iv_career_path", "label": "キャリアパス紹介", "max": 3,
             "check_fn": "_check_career_path"},
            {"key": "iv_photo_video", "label": "写真/動画の活用", "max": 3,
             "check_fn": "_check_media_content"},
        ],
    },
    "entry": {
        "label": "エントリー/応募ページ",
        "checks": [
            {"key": "en_form", "label": "応募フォーム設置", "max": 4,
             "check_fn": "_check_entry_form"},
            {"key": "en_selection_flow", "label": "選考フロー明記", "max": 3,
             "check_fn": "_check_selection_flow"},
            {"key": "en_low_commit", "label": "低コミット選択肢(カジュアル面談)", "max": 3,
             "check_fn": "_check_low_commit"},
            {"key": "en_contact", "label": "問い合わせ先情報", "max": 2,
             "check_fn": "_check_contact_info"},
        ],
    },
    "faq": {
        "label": "よくある質問ページ",
        "checks": [
            {"key": "fq_count", "label": "FAQ数(7問以上推奨)", "max": 4,
             "check_fn": "_check_faq_count"},
            {"key": "fq_jsonld", "label": "FAQPage JSON-LD", "max": 3,
             "check_fn": "_check_faq_jsonld"},
            {"key": "fq_categories", "label": "カテゴリ分類", "max": 2,
             "check_fn": "_check_faq_categories"},
        ],
    },
}


# ==================================================================
# チェック関数 → カテゴリ マッピング
# ==================================================================

CATEGORY_MAP = {
    "rt_": "5_apply_ux",
    "jl_": "1_jobposting",
    "cl_": "3_culture",
    "bf_": "4_conditions",
    "iv_": "3_culture",
    "en_": "5_apply_ux",
    "fq_": "2_job_specificity",
    "common_cred_": "6_credibility",
    "common_tech_": "6_credibility",
    "common_spec_": "2_job_specificity",
    "common_cult_": "3_culture",
    "common_cond_": "4_conditions",
    "common_ux_": "5_apply_ux",
    "common_jp_": "1_jobposting",
}


# ==================================================================
# テキストヘルパー
# ==================================================================

def _text_has_any(text: str, keywords: list) -> int:
    """テキストにキーワードが何件含まれるか。"""
    return sum(1 for k in keywords if k in text)


def _find_jobposting(jsonld_list: list) -> dict:
    """JSON-LDからJobPostingを抽出。"""
    for item in jsonld_list:
        if isinstance(item, dict):
            t = item.get("@type", "")
            if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                return item
            graph = item.get("@graph", [])
            if isinstance(graph, list):
                for g in graph:
                    if isinstance(g, dict) and g.get("@type") == "JobPosting":
                        return g
    return {}


# ==================================================================
# ロール固有チェック関数  —  recruit_top
# ==================================================================

def _check_brand_message(structure: dict) -> dict:
    """採用ブランドメッセージの有無。"""
    text = structure.get("content_text", "")
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""

    brand_kws = ["一緒に", "仲間", "チャレンジ", "未来", "成長", "挑戦",
                 "私たちと", "あなたの力", "共に", "新しい仲間", "ともに",
                 "求む", "Join", "We are hiring", "募集"]
    found = _text_has_any(text, brand_kws)

    # h1/h2 に採用メッセージ系があるか
    h1_h2 = re.findall(r'<h[12][^>]*>(.*?)</h[12]>', raw_html, re.IGNORECASE | re.DOTALL)
    heading_has_brand = any(
        _text_has_any(h, ["採用", "仲間", "募集", "Join", "Career"]) > 0
        for h in h1_h2
    )

    if found >= 3 and heading_has_brand:
        return {"score": 3, "reason": f"採用ブランドメッセージ充実（{found}件＋見出し訴求あり）"}
    if found >= 2 or heading_has_brand:
        return {"score": 2, "reason": f"採用メッセージあり（{found}件）、訴求力強化の余地"}
    if found >= 1:
        return {"score": 1, "reason": "採用メッセージの言及が最小限"}
    return {"score": 0, "reason": "採用ブランドメッセージなし — 求職者の共感を得にくい"}


def _check_job_categories(structure: dict) -> dict:
    """職種カテゴリ一覧の有無。"""
    text = structure.get("content_text", "")
    cat_kws = ["エンジニア", "デザイナー", "マーケ", "営業", "セールス",
               "人事", "経理", "バックオフィス", "事務", "企画",
               "マネージャー", "ディレクター", "インターン", "新卒", "中途",
               "職種一覧", "募集職種", "キャリア採用", "ポジション"]
    found = _text_has_any(text, cat_kws)
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
    link_count = len(re.findall(r'<a[^>]*href=[^>]*(?:job|position|career|recruit)', raw_html, re.IGNORECASE))

    if found >= 4 and link_count >= 2:
        return {"score": 3, "reason": f"職種カテゴリ{found}件 + 個別リンク{link_count}件"}
    if found >= 2:
        return {"score": 2, "reason": f"職種の言及{found}件あり、リンク導線が不足"}
    if found >= 1:
        return {"score": 1, "reason": "職種の言及が最小限"}
    return {"score": 0, "reason": "職種カテゴリ一覧なし"}


def _check_recruit_navigation(structure: dict) -> dict:
    """採用サイト内の各ページへの導線。"""
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
    nav_targets = ["社員", "インタビュー", "福利厚生", "エントリー", "応募",
                   "FAQ", "よくある質問", "選考", "カルチャー", "働き方",
                   "member", "interview", "benefit", "entry", "apply", "faq", "culture"]
    link_texts = re.findall(r'<a[^>]*>(.*?)</a>', raw_html, re.IGNORECASE | re.DOTALL)
    nav_found = sum(1 for lt in link_texts if _text_has_any(lt, nav_targets) > 0)

    if nav_found >= 4:
        return {"score": 2, "reason": f"採用サイト内導線{nav_found}件 — ナビゲーション良好"}
    if nav_found >= 2:
        return {"score": 1, "reason": f"導線{nav_found}件 — 一部ページへのリンクが不足"}
    return {"score": 0, "reason": "採用サイト内のナビゲーション導線が不足"}


def _check_cta(structure: dict) -> dict:
    """応募CTAボタンの有無と品質。"""
    text = structure.get("content_text", "")
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""

    cta_kws = ["応募する", "エントリー", "Apply", "応募フォーム",
               "面談を申し込む", "カジュアル面談", "まずは話を聞く"]
    cta_count = _text_has_any(text, cta_kws)
    button_count = len(re.findall(
        r'<(?:button|a)[^>]*(?:class=["\'][^"\']*(?:btn|button|cta)[^"\']*["\'])',
        raw_html, re.IGNORECASE))

    if cta_count >= 2 and button_count >= 1:
        return {"score": 3, "reason": f"CTA文言{cta_count}件 + ボタン要素{button_count}件"}
    if cta_count >= 1:
        return {"score": 2, "reason": "CTAはあるが目立つ配置でない可能性"}
    return {"score": 0, "reason": "明確なCTAが見当たらない — 応募率が低い"}


def _check_company_numbers(structure: dict) -> dict:
    """会社紹介の数値情報。"""
    text = structure.get("content_text", "")
    num_patterns = [
        r"設立\s*\d{4}", r"創業\s*\d{4}", r"従業員\s*[\d,]+",
        r"社員数\s*[\d,]+", r"売上\s*[\d,]+", r"拠点\s*\d+",
        r"顧客\s*[\d,]+", r"導入\s*[\d,]+", r"平均年齢\s*\d+",
    ]
    found = sum(1 for p in num_patterns if re.search(p, text))

    if found >= 4:
        return {"score": 3, "reason": f"企業の数値情報{found}件 — 信頼性が高い"}
    if found >= 2:
        return {"score": 2, "reason": f"数値情報{found}件 — 補強の余地あり"}
    if found >= 1:
        return {"score": 1, "reason": "数値情報が最小限"}
    return {"score": 0, "reason": "企業の数値データなし — 求職者が規模を判断できない"}


# ==================================================================
# ロール固有チェック関数  —  job_listing
# ==================================================================

def _check_jobposting_jsonld(structure: dict) -> dict:
    """JobPosting JSON-LDの存在と充足度をチェック。"""
    for jsonld in structure.get("jsonld", []):
        if not isinstance(jsonld, dict):
            continue
        t = jsonld.get("@type", "")
        is_jp = t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t)
        if not is_jp:
            graph = jsonld.get("@graph", [])
            if isinstance(graph, list):
                for g in graph:
                    if isinstance(g, dict) and g.get("@type") == "JobPosting":
                        jsonld = g
                        is_jp = True
                        break
        if is_jp:
            required = ["title", "description", "datePosted", "hiringOrganization"]
            has = sum(1 for f in required if jsonld.get(f))
            if has == 4:
                return {"score": 5, "reason": f"JobPosting JSON-LD 完全実装（必須{has}/4項目）"}
            else:
                return {"score": 2, "reason": f"JobPosting JSON-LD 不完全（必須{has}/4項目）"}
    return {"score": 0, "reason": "JobPosting JSON-LD 未実装"}


def _check_jp_required(structure: dict) -> dict:
    """JobPosting必須項目（title/description/datePosted/hiringOrganization/jobLocation）。"""
    jp = _find_jobposting(structure.get("jsonld", []))
    if not jp:
        return {"score": 0, "reason": "JobPosting未設置のため判定不可"}
    required = ["title", "description", "datePosted", "hiringOrganization", "jobLocation"]
    filled = sum(1 for f in required if jp.get(f))
    missing = [f for f in required if not jp.get(f)]
    score = round(filled / len(required) * 4)
    reason = f"必須{filled}/{len(required)}項目"
    if missing:
        reason += f"、欠落: {', '.join(missing)}"
    else:
        reason += " — 完全"
    return {"score": score, "reason": reason}


def _check_salary_detail(structure: dict) -> dict:
    """給与情報の具体性。"""
    content = structure.get("content_text", "")
    salary_patterns = [
        r"月給[\s:：]*[\d,]+", r"年収[\s:：]*[\d,]+", r"時給[\s:：]*[\d,]+",
        r"賞与", r"昇給", r"手当", r"万円",
    ]
    found = sum(1 for p in salary_patterns if re.search(p, content))
    if found >= 4:
        return {"score": 4, "reason": f"給与情報 充実（{found}項目）"}
    if found >= 2:
        return {"score": 2, "reason": f"給与情報 基本記載（{found}項目）"}
    return {"score": 0, "reason": "給与情報の記載なし"}


def _check_location(structure: dict) -> dict:
    """勤務地情報。"""
    text = structure.get("content_text", "")
    location_kws = ["勤務地", "所在地", "本社", "支社", "オフィス",
                    "東京都", "大阪府", "神奈川", "リモート", "在宅",
                    "アクセス", "最寄り駅"]
    found = _text_has_any(text, location_kws)
    if found >= 3:
        return {"score": 3, "reason": f"勤務地情報{found}件 — 明確"}
    if found >= 1:
        return {"score": 1, "reason": "勤務地の記載はあるが詳細不足"}
    return {"score": 0, "reason": "勤務地が明記されていない"}


def _check_skills(structure: dict) -> dict:
    """必須/歓迎スキルの分離。"""
    text = structure.get("content_text", "")
    skill_kws = ["必須スキル", "必須条件", "応募資格", "応募条件",
                 "歓迎スキル", "歓迎条件", "求める人物像", "求めるスキル",
                 "経験者", "未経験"]
    found = _text_has_any(text, skill_kws)
    must_want_separated = ("必須" in text) and ("歓迎" in text)
    if found >= 3 and must_want_separated:
        return {"score": 3, "reason": f"必須/歓迎の分離明確 + キーワード{found}件"}
    if found >= 2:
        return {"score": 2, "reason": "応募条件はあるが必須/歓迎の分離が不明確"}
    if found >= 1:
        return {"score": 1, "reason": "応募条件の記述が最小限"}
    return {"score": 0, "reason": "応募資格・スキル要件の記述なし"}


def _check_direct_apply(structure: dict) -> dict:
    """応募ボタンおよびdirectApply。"""
    jp = _find_jobposting(structure.get("jsonld", []))
    text = structure.get("content_text", "")
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""

    has_direct_apply = bool(jp and (jp.get("directApply") is not None or jp.get("url")))
    cta_kws = ["応募する", "エントリー", "Apply", "応募フォーム"]
    has_button = _text_has_any(text, cta_kws) > 0
    button_el = len(re.findall(
        r'<(?:button|a)[^>]*(?:class=["\'][^"\']*(?:btn|button|cta)[^"\']*["\'])',
        raw_html, re.IGNORECASE))

    if has_direct_apply and has_button:
        return {"score": 3, "reason": "directApply設定 + 応募ボタンあり"}
    if has_direct_apply or (has_button and button_el >= 1):
        return {"score": 2, "reason": "応募導線は部分的"}
    if has_button:
        return {"score": 1, "reason": "応募文言はあるがボタン要素・directApplyなし"}
    return {"score": 0, "reason": "応募ボタン・directApply未設定"}


# ==================================================================
# ロール固有チェック関数  —  culture
# ==================================================================

def _check_mvv(structure: dict) -> dict:
    """MVV（ミッション・ビジョン・バリュー）。"""
    text = structure.get("content_text", "")
    mvv_kws = ["ミッション", "ビジョン", "バリュー", "MVV",
               "企業理念", "経営理念", "私たちの使命", "Vision", "Mission", "Values",
               "パーパス", "Purpose"]
    found = _text_has_any(text, mvv_kws)
    if found >= 4:
        return {"score": 4, "reason": f"MVV関連{found}件 — 価値観が非常に明確"}
    if found >= 2:
        return {"score": 3, "reason": f"MVV関連{found}件 — 基本的に網羅"}
    if found >= 1:
        return {"score": 1, "reason": "MVVの言及はあるが浅い"}
    return {"score": 0, "reason": "MVV・企業理念の明示なし"}


def _check_workplace(structure: dict) -> dict:
    """職場環境・オフィス紹介。"""
    text = structure.get("content_text", "")
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
    office_kws = ["オフィス", "職場", "ワークスペース", "フロア", "会議室",
                  "執務", "社内", "環境"]
    found = _text_has_any(text, office_kws)
    image_count = len(re.findall(r'<img\s', raw_html, re.IGNORECASE))

    if found >= 3 and image_count >= 5:
        return {"score": 3, "reason": f"オフィス言及{found}件 + 画像{image_count}点"}
    if found >= 2 or image_count >= 3:
        return {"score": 2, "reason": "職場イメージは部分的"}
    if found >= 1:
        return {"score": 1, "reason": "職場環境の可視化が最小限"}
    return {"score": 0, "reason": "職場環境の可視化なし"}


def _check_diversity(structure: dict) -> dict:
    """多様性・DEI。"""
    text = structure.get("content_text", "")
    dei_kws = ["ダイバーシティ", "多様性", "DEI", "D&I", "インクルージョン",
               "女性活躍", "育児", "育休", "産休", "時短勤務",
               "LGBTQ", "障がい者", "外国籍", "年齢問わず"]
    found = _text_has_any(text, dei_kws)
    if found >= 3:
        return {"score": 3, "reason": f"多様性・DEI関連{found}件"}
    if found >= 1:
        return {"score": 1, "reason": "多様性への言及はあるが体系的でない"}
    return {"score": 0, "reason": "多様性・DEIの明示なし"}


def _check_video(structure: dict) -> dict:
    """動画コンテンツ。"""
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
    video_markers = 0
    if raw_html:
        video_markers += len(re.findall(
            r'<(?:video|iframe)[^>]*(?:youtube|vimeo)', raw_html, re.IGNORECASE))
        video_markers += len(re.findall(r'<video[\s>]', raw_html, re.IGNORECASE))
    if video_markers >= 2:
        return {"score": 3, "reason": f"動画コンテンツ{video_markers}件 — 滞在時間・理解促進"}
    if video_markers >= 1:
        return {"score": 1, "reason": "動画1件あり、より多くの動画化が望ましい"}
    return {"score": 0, "reason": "動画コンテンツなし"}


# ==================================================================
# ロール固有チェック関数  —  benefits
# ==================================================================

def _check_benefits_list(structure: dict) -> dict:
    """福利厚生一覧。"""
    text = structure.get("content_text", "")
    benefit_kws = ["福利厚生", "社会保険", "各種保険", "社宅", "家賃補助",
                   "交通費", "退職金", "確定拠出年金", "持株会",
                   "健康診断", "人間ドック", "社員食堂",
                   "住宅手当", "扶養手当", "慶弔"]
    found = _text_has_any(text, benefit_kws)
    if found >= 6:
        return {"score": 4, "reason": f"福利厚生{found}項目 — 非常に充実"}
    if found >= 4:
        return {"score": 3, "reason": f"福利厚生{found}項目 — 充実"}
    if found >= 2:
        return {"score": 2, "reason": f"福利厚生{found}項目 — 標準的"}
    return {"score": 0, "reason": "福利厚生の記述が不足"}


def _check_benefit_numbers(structure: dict) -> dict:
    """福利厚生の数値の具体性。"""
    text = structure.get("content_text", "")
    benefit_number_patterns = [
        r"取得率\s*\d+", r"月\s*\d+時間", r"年間\s*\d+日",
        r"\d+時間以内", r"\d+日以上", r"\d+%",
        r"復帰率\s*\d+",
    ]
    found = sum(len(re.findall(p, text)) for p in benefit_number_patterns)
    if found >= 4:
        return {"score": 3, "reason": f"具体数値{found}箇所 — 説得力が高い"}
    if found >= 2:
        return {"score": 2, "reason": f"数値データ{found}箇所 — 補強余地あり"}
    if found >= 1:
        return {"score": 1, "reason": f"数値データ{found}箇所 — 最小限"}
    return {"score": 0, "reason": "労働条件の具体数値なし — 抽象的で信頼度低"}


def _check_work_style(structure: dict) -> dict:
    """勤務時間・休日・リモート。"""
    text = structure.get("content_text", "")
    time_kws = ["勤務時間", "就業時間", "定時", "フレックス", "コアタイム",
                "休日", "休暇", "年間休日", "土日祝"]
    remote_kws = ["リモート", "テレワーク", "在宅勤務", "フルリモート",
                  "ハイブリッド", "出社"]
    time_count = _text_has_any(text, time_kws)
    remote_count = _text_has_any(text, remote_kws)
    total = time_count + remote_count

    if total >= 5:
        return {"score": 3, "reason": f"勤務時間{time_count}件 + 働き方{remote_count}件 — 明確"}
    if total >= 3:
        return {"score": 2, "reason": "勤務条件の記載あり、一部不足"}
    if total >= 1:
        return {"score": 1, "reason": "勤務条件の記載が最小限"}
    return {"score": 0, "reason": "勤務時間・休日・リモートの明示なし"}


def _check_training(structure: dict) -> dict:
    """研修・教育制度。"""
    text = structure.get("content_text", "")
    training_kws = ["研修", "教育制度", "勉強会", "資格取得支援", "書籍購入",
                    "カンファレンス", "社外学習", "Udemy", "オンライン学習",
                    "メンター", "OJT", "eラーニング"]
    found = _text_has_any(text, training_kws)
    if found >= 3:
        return {"score": 3, "reason": f"研修制度{found}項目 — 充実"}
    if found >= 1:
        return {"score": 1, "reason": "研修制度の言及はあるが具体性不足"}
    return {"score": 0, "reason": "研修・学習支援の記述なし"}


# ==================================================================
# ロール固有チェック関数  —  interview
# ==================================================================

def _check_staff_voices(structure: dict) -> dict:
    """社員の声（具体エピソード）。"""
    text = structure.get("content_text", "")
    staff_kws = ["社員紹介", "社員インタビュー", "社員の声", "メンバー紹介",
                 "社員メッセージ", "入社ストーリー", "マネージャーインタビュー",
                 "入社理由", "やりがい", "1日の流れ"]
    found = _text_has_any(text, staff_kws)

    # 具体的なエピソード性を判定（引用や名前の存在）
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
    blockquote_count = len(re.findall(r'<blockquote', raw_html, re.IGNORECASE))
    person_indicators = len(re.findall(r'さん|氏|部長|課長|マネージャー|リーダー|チーフ',
                                       text))

    if found >= 3 and (blockquote_count >= 1 or person_indicators >= 2):
        return {"score": 4, "reason": f"社員の声{found}件 + 具体エピソード検出"}
    if found >= 2:
        return {"score": 3, "reason": f"社員紹介要素{found}件"}
    if found >= 1:
        return {"score": 1, "reason": "社員紹介はあるが最小限"}
    return {"score": 0, "reason": "社員の声・インタビューなし"}


def _check_career_path(structure: dict) -> dict:
    """キャリアパス紹介。"""
    text = structure.get("content_text", "")
    career_kws = ["キャリアパス", "キャリアステップ", "昇格", "昇進",
                  "ロールモデル", "成長", "将来像", "次のステージ",
                  "評価制度", "等級", "年目"]
    found = _text_has_any(text, career_kws)
    if found >= 3:
        return {"score": 3, "reason": f"キャリア情報{found}件 — 成長イメージが描ける"}
    if found >= 1:
        return {"score": 1, "reason": "キャリア関連の言及はあるが具体性不足"}
    return {"score": 0, "reason": "キャリアパスの記述なし — 成長志向の候補者を逃す"}


def _check_media_content(structure: dict) -> dict:
    """写真/動画の活用。"""
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
    image_count = len(re.findall(r'<img\s', raw_html, re.IGNORECASE))
    video_count = len(re.findall(r'<(?:video|iframe)[^>]*(?:youtube|vimeo)', raw_html, re.IGNORECASE))
    video_count += len(re.findall(r'<video[\s>]', raw_html, re.IGNORECASE))

    if image_count >= 5 and video_count >= 1:
        return {"score": 3, "reason": f"写真{image_count}点 + 動画{video_count}件"}
    if image_count >= 3 or video_count >= 1:
        return {"score": 2, "reason": f"写真{image_count}点 / 動画{video_count}件 — 充実の余地"}
    if image_count >= 1:
        return {"score": 1, "reason": "写真が最小限、動画なし"}
    return {"score": 0, "reason": "写真・動画コンテンツなし"}


# ==================================================================
# ロール固有チェック関数  —  entry
# ==================================================================

def _check_entry_form(structure: dict) -> dict:
    """応募フォーム設置。"""
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
    text = structure.get("content_text", "")

    has_form = bool(re.search(r'<form[\s>]', raw_html, re.IGNORECASE))
    has_input = bool(re.search(r'<input[\s>]', raw_html, re.IGNORECASE))
    has_textarea = bool(re.search(r'<textarea[\s>]', raw_html, re.IGNORECASE))
    form_kws = ["お名前", "氏名", "メールアドレス", "電話番号", "志望動機",
                "履歴書", "職務経歴書", "ファイル添付"]
    form_fields = _text_has_any(text, form_kws)

    if has_form and form_fields >= 3:
        return {"score": 4, "reason": f"応募フォーム設置 + 入力項目{form_fields}件"}
    if has_form or (has_input and has_textarea):
        return {"score": 3, "reason": "フォーム要素検出（入力項目の詳細は不明）"}
    if form_fields >= 1:
        return {"score": 1, "reason": "フォーム関連の文言はあるがフォーム要素なし"}
    return {"score": 0, "reason": "応募フォーム未設置"}


def _check_selection_flow(structure: dict) -> dict:
    """選考フロー明記。"""
    text = structure.get("content_text", "")
    flow_kws = ["選考フロー", "選考プロセス", "面接", "書類選考",
                "一次面接", "二次面接", "最終面接", "オファー面談",
                "内定", "STEP"]
    found = _text_has_any(text, flow_kws)
    if found >= 4:
        return {"score": 3, "reason": f"選考フロー{found}要素 — 透明性高い"}
    if found >= 2:
        return {"score": 2, "reason": "選考フローはあるが詳細不足"}
    if found >= 1:
        return {"score": 1, "reason": "選考関連の言及が最小限"}
    return {"score": 0, "reason": "選考フローが不明瞭"}


def _check_low_commit(structure: dict) -> dict:
    """低コミット選択肢（カジュアル面談等）。"""
    text = structure.get("content_text", "")
    casual_kws = ["カジュアル面談", "会社説明会", "オフィス見学", "気軽に",
                  "まずは話", "お話しましょう", "オープン社内",
                  "相談会", "ミートアップ"]
    found = _text_has_any(text, casual_kws)
    if found >= 2:
        return {"score": 3, "reason": f"低コミット選択肢{found}件 — 応募ハードル下げている"}
    if found >= 1:
        return {"score": 1, "reason": "カジュアル面談の導線が部分的"}
    return {"score": 0, "reason": "カジュアル面談など低コミット選択肢なし"}


def _check_contact_info(structure: dict) -> dict:
    """問い合わせ先情報。"""
    text = structure.get("content_text", "")
    contact_kws = ["問い合わせ", "お問合せ", "連絡先", "採用担当",
                   "人事部", "hr@", "recruit@", "メールアドレス",
                   "電話番号"]
    found = _text_has_any(text, contact_kws)
    if found >= 2:
        return {"score": 2, "reason": "連絡先・問い合わせ窓口明確"}
    if found >= 1:
        return {"score": 1, "reason": "問い合わせ先は部分的"}
    return {"score": 0, "reason": "問い合わせ先が不明"}


# ==================================================================
# ロール固有チェック関数  —  faq
# ==================================================================

def _check_faq_count(structure: dict) -> dict:
    """FAQ数。"""
    faq_items = structure.get("faq_items", [])
    text = structure.get("content_text", "")

    # faq_items がない場合はテキストからQ&Aパターンを推定
    count = len(faq_items)
    if count == 0:
        q_patterns = re.findall(r'(?:Q[\.\s:：]|質問[\s:：]|Ｑ[\.\s:：])', text)
        count = len(q_patterns)
        # dt/dd パターンも探す
        raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
        dt_count = len(re.findall(r'<dt[\s>]', raw_html, re.IGNORECASE))
        if dt_count > count:
            count = dt_count

    if count >= 7:
        return {"score": 4, "reason": f"FAQ {count}問 — 充実（7問以上推奨をクリア）"}
    if count >= 4:
        return {"score": 3, "reason": f"FAQ {count}問 — あと{7 - count}問で推奨水準"}
    if count >= 1:
        return {"score": 1, "reason": f"FAQ {count}問 — 大幅に不足"}
    return {"score": 0, "reason": "FAQコンテンツなし"}


def _check_faq_jsonld(structure: dict) -> dict:
    """FAQPage JSON-LD。"""
    for jsonld in structure.get("jsonld", []):
        if not isinstance(jsonld, dict):
            continue
        t = jsonld.get("@type", "")
        if t == "FAQPage" or (isinstance(t, list) and "FAQPage" in t):
            main_entity = jsonld.get("mainEntity", [])
            q_count = len(main_entity) if isinstance(main_entity, list) else 0
            if q_count >= 5:
                return {"score": 3, "reason": f"FAQPage JSON-LD（{q_count}問）— 完全実装"}
            if q_count >= 1:
                return {"score": 2, "reason": f"FAQPage JSON-LD（{q_count}問）— 項目追加推奨"}
            return {"score": 1, "reason": "FAQPage JSON-LD あり（mainEntity空）"}
    return {"score": 0, "reason": "FAQPage JSON-LD 未実装"}


def _check_faq_categories(structure: dict) -> dict:
    """FAQのカテゴリ分類。"""
    text = structure.get("content_text", "")
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""

    category_kws = ["選考について", "勤務条件", "福利厚生について", "働き方",
                    "キャリアについて", "社風", "入社後", "応募について",
                    "カテゴリ", "ジャンル"]
    found = _text_has_any(text, category_kws)

    # h2/h3 の数で判定（FAQ内のセクション分け）
    headings = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', raw_html, re.IGNORECASE | re.DOTALL)
    faq_headings = [h for h in headings if _text_has_any(h, category_kws) > 0]

    if len(faq_headings) >= 3 or found >= 3:
        return {"score": 2, "reason": f"FAQカテゴリ分類あり（{max(len(faq_headings), found)}セクション）"}
    if found >= 1 or len(faq_headings) >= 1:
        return {"score": 1, "reason": "カテゴリ分類は部分的"}
    return {"score": 0, "reason": "FAQがカテゴリ分類されていない"}


# ==================================================================
# チェック関数辞書（関数名 → 関数オブジェクト）
# ==================================================================

_CHECK_FNS = {
    # recruit_top
    "_check_brand_message": _check_brand_message,
    "_check_job_categories": _check_job_categories,
    "_check_recruit_navigation": _check_recruit_navigation,
    "_check_cta": _check_cta,
    "_check_company_numbers": _check_company_numbers,
    # job_listing
    "_check_jobposting_jsonld": _check_jobposting_jsonld,
    "_check_jp_required": _check_jp_required,
    "_check_salary_detail": _check_salary_detail,
    "_check_location": _check_location,
    "_check_skills": _check_skills,
    "_check_direct_apply": _check_direct_apply,
    # culture
    "_check_mvv": _check_mvv,
    "_check_workplace": _check_workplace,
    "_check_diversity": _check_diversity,
    "_check_video": _check_video,
    # benefits
    "_check_benefits_list": _check_benefits_list,
    "_check_benefit_numbers": _check_benefit_numbers,
    "_check_work_style": _check_work_style,
    "_check_training": _check_training,
    # interview
    "_check_staff_voices": _check_staff_voices,
    "_check_career_path": _check_career_path,
    "_check_media_content": _check_media_content,
    # entry
    "_check_entry_form": _check_entry_form,
    "_check_selection_flow": _check_selection_flow,
    "_check_low_commit": _check_low_commit,
    "_check_contact_info": _check_contact_info,
    # faq
    "_check_faq_count": _check_faq_count,
    "_check_faq_jsonld": _check_faq_jsonld,
    "_check_faq_categories": _check_faq_categories,
}


# ==================================================================
# 共通チェック（全ロール）
# ==================================================================

def _add_common_checks(all_scores: dict, structure: dict,
                       robots: dict, llms: dict,
                       pagespeed: dict, sitemap: dict) -> None:
    """全ロール共通のチェック項目を追加。"""
    text = structure.get("content_text", "")
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""

    # --- 信頼性: Organization JSON-LD ---
    has_org = any(
        (isinstance(s, dict) and (
            s.get("@type") == "Organization" or
            (isinstance(s.get("@type"), list) and "Organization" in s.get("@type", []))
        ))
        for s in structure.get("jsonld", [])
    )
    all_scores["common_cred_org_jsonld"] = {
        "score": 3 if has_org else 0, "max": 3,
        "label": "Organization JSON-LD",
        "reason": "Organization JSON-LD検出" if has_org else "Organization JSON-LD未設置",
        "role": "common",
    }

    # --- 信頼性: 代表メッセージ ---
    ceo_kws = ["代表メッセージ", "代表取締役", "CEO", "社長メッセージ",
               "代表挨拶", "創業者"]
    ceo_count = _text_has_any(text, ceo_kws)
    if ceo_count >= 2:
        s, r = 3, "代表メッセージ確認"
    elif ceo_count >= 1:
        s, r = 1, "代表関連の言及はあるが独立セクションなし"
    else:
        s, r = 0, "代表メッセージなし"
    all_scores["common_cred_ceo"] = {
        "score": s, "max": 3, "label": "代表メッセージ", "reason": r, "role": "common",
    }

    # --- 信頼性: 受賞・認定 ---
    award_kws = ["受賞", "表彰", "認定", "Best Workplaces", "働きがいのある会社",
                 "ホワイト企業", "くるみん", "えるぼし", "プラチナ",
                 "認証", "ISO", "プライバシーマーク"]
    award_count = _text_has_any(text, award_kws)
    if award_count >= 2:
        s, r = 3, f"受賞・認定{award_count}件"
    elif award_count >= 1:
        s, r = 1, "受賞・認定1件"
    else:
        s, r = 0, "受賞・認定情報なし"
    all_scores["common_cred_awards"] = {
        "score": s, "max": 3, "label": "受賞・認定", "reason": r, "role": "common",
    }

    # --- 信頼性: メディア掲載 ---
    media_kws = ["メディア掲載", "プレスリリース", "取材", "掲載実績",
                 "日経", "ITmedia", "TechCrunch", "ForbesJapan",
                 "出演", "寄稿"]
    media_count = _text_has_any(text, media_kws)
    if media_count >= 3:
        s, r = 3, f"メディア関連{media_count}件"
    elif media_count >= 1:
        s, r = 1, "メディア言及は部分的"
    else:
        s, r = 0, "メディア掲載の明示なし"
    all_scores["common_cred_media"] = {
        "score": s, "max": 3, "label": "メディア掲載", "reason": r, "role": "common",
    }

    # --- 応募UX: モバイル対応 ---
    has_viewport = structure.get("viewport")
    all_scores["common_ux_mobile"] = {
        "score": 3 if has_viewport else 0, "max": 3,
        "label": "モバイル対応(viewport)",
        "reason": "viewport meta設定あり — レスポンシブ対応" if has_viewport
                  else "viewport meta未設定 — スマホ閲覧で崩れ",
        "role": "common",
    }


# ==================================================================
# カテゴリ集計
# ==================================================================

def _resolve_category(key: str) -> str:
    """スコアキーからカテゴリを解決。"""
    for prefix, cat in CATEGORY_MAP.items():
        if key.startswith(prefix):
            return cat
    # フォールバック: 旧形式 "1-xxx", "2-xxx" のプレフィックスにも対応
    m = re.match(r'^(\d)-', key)
    if m:
        num = m.group(1)
        for cat_key in CATEGORY_DEFINITIONS:
            if cat_key.startswith(num + "_"):
                return cat_key
    return "6_credibility"  # デフォルト


def _calculate_categories(all_scores: dict) -> dict:
    """all_scoresからカテゴリ別集計を計算。"""
    categories = {}
    for cat_key, cat_def in CATEGORY_DEFINITIONS.items():
        categories[cat_key] = {
            "label": cat_def["label"],
            "score": 0.0,
            "max": cat_def["max"],
            "pct": 0,
        }

    for key, val in all_scores.items():
        if not isinstance(val, dict):
            continue
        cat = _resolve_category(key)
        if cat in categories:
            categories[cat]["score"] += val.get("score", 0)

    # カテゴリ上限でクリップ + pct計算
    for cat_key, cat_data in categories.items():
        cat_max = CATEGORY_DEFINITIONS[cat_key]["max"]
        cat_data["score"] = round(min(cat_data["score"], cat_max), 1)
        cat_data["pct"] = round(cat_data["score"] / cat_max * 100) if cat_max else 0

    return categories


# ==================================================================
# メインスコアリング
# ==================================================================

def score_page(structure, robots, llms, pagespeed, sitemap,
               role: str = "other"):
    """ページの役割に応じた基準でスコアリング。

    all_scores / categories / total を返す。
    role引数のデフォルトは"other"で後方互換を維持。
    """
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
    # structureに_raw_htmlが含まれていない場合の保険
    if not structure.get("_raw_html") and raw_html:
        structure["_raw_html"] = raw_html

    all_scores: dict = {}

    # 1. ロール固有のチェック
    role_req = ROLE_REQUIREMENTS.get(role, {})
    for check_def in role_req.get("checks", []):
        fn = _CHECK_FNS.get(check_def["check_fn"])
        if fn is None:
            continue
        result = fn(structure)
        all_scores[check_def["key"]] = {
            "score": result.get("score", 0),
            "max": check_def["max"],
            "label": check_def["label"],
            "reason": result.get("reason", ""),
            "role": role,
            "method": result.get("method", "テキスト解析"),
            "confidence": result.get("confidence", "高"),
        }

    # 2. 全ロール共通チェック
    _add_common_checks(all_scores, structure, robots, llms, pagespeed, sitemap)

    # 3. カテゴリ集計
    categories = _calculate_categories(all_scores)

    # 4. CV分析
    try:
        cv = analyze_cv(structure, all_scores, pagespeed, raw_html)
        structure["_cv_analysis"] = cv
    except Exception:
        pass

    # 5. 総合スコア
    total_score = sum(c["score"] for c in categories.values())
    grade_result = grade_from_score(round(total_score))
    total = {
        "total": round(total_score),
        "grade": grade_result["grade"],
        "label": grade_result["label"],
    }

    return all_scores, categories, total


# ==================================================================
# サイト全体の構造完全性スコア
# ==================================================================

def score_site(page_results: list, classified_pages: list) -> dict:
    """採用サイト全体の構造完全性を評価。

    Args:
        page_results: 各ページの診断結果
            [{"url", "role", "structure", "all_scores", "categories", "total"}, ...]
        classified_pages: 分類済みページ一覧
            [{"url", "role"}, ...]

    Returns:
        構造完全性、ロール別スコア、改善提案を含む辞書。
    """
    REQUIRED_ROLES = ["recruit_top", "job_listing", "entry"]
    RECOMMENDED_ROLES = ["culture", "benefits", "interview", "faq"]

    found_roles: dict = {}
    for p in classified_pages:
        role = p.get("role", "other")
        if role not in found_roles:
            found_roles[role] = []
        found_roles[role].append(p.get("url", ""))

    missing_required = [r for r in REQUIRED_ROLES if r not in found_roles]
    missing_recommended = [r for r in RECOMMENDED_ROLES if r not in found_roles]

    completeness = (
        len([r for r in REQUIRED_ROLES if r in found_roles]) / len(REQUIRED_ROLES) * 100
    )

    # 各ロールのベストスコア
    role_scores: dict = {}
    for pr in page_results:
        role = pr.get("role", "other")
        score = pr.get("total", {}).get("total", 0)
        if role not in role_scores or score > role_scores[role].get("score", 0):
            role_scores[role] = {
                "url": pr.get("url", ""),
                "score": score,
                "grade": pr.get("total", {}).get("grade", "D"),
                "issues": [
                    k for k, v in pr.get("all_scores", {}).items()
                    if isinstance(v, dict) and v.get("score", 0) == 0
                ],
            }

    # 構造化データマップ
    schema_map = _build_schema_map(page_results, classified_pages)

    # ページ別改善提案
    recommendations = _generate_page_recommendations(
        found_roles, missing_required, missing_recommended, role_scores)

    return {
        "structure_completeness": {
            "score": int(completeness),
            "required_found": [r for r in REQUIRED_ROLES if r in found_roles],
            "required_missing": missing_required,
            "recommended_found": [r for r in RECOMMENDED_ROLES if r in found_roles],
            "recommended_missing": missing_recommended,
        },
        "role_scores": role_scores,
        "page_recommendations": recommendations,
        "schema_map": schema_map,
    }


def _build_schema_map(page_results: list, classified_pages: list) -> dict:
    """各ページの構造化データ実装状況マップを構築。"""
    schema_map: dict = {}
    for pr in page_results:
        url = pr.get("url", "")
        role = pr.get("role", "other")
        all_scores = pr.get("all_scores", {})

        schemas_found = []
        structure = pr.get("structure", {})
        for jsonld in structure.get("jsonld", []) if isinstance(structure, dict) else []:
            if isinstance(jsonld, dict):
                t = jsonld.get("@type", "")
                if t:
                    schemas_found.append(t if isinstance(t, str) else ", ".join(t))

        schema_map[url] = {
            "role": role,
            "role_label": ROLE_REQUIREMENTS.get(role, {}).get("label", role),
            "schemas": schemas_found,
            "score": pr.get("total", {}).get("total", 0),
            "grade": pr.get("total", {}).get("grade", "D"),
        }

    return schema_map


def _generate_page_recommendations(found_roles: dict,
                                   missing_required: list,
                                   missing_recommended: list,
                                   role_scores: dict) -> list:
    """ページ別改善提案を生成。"""
    recs = []

    # 必須ロールの欠損
    role_labels = {
        "recruit_top": "採用トップページ",
        "job_listing": "求人詳細ページ",
        "entry": "エントリー/応募ページ",
        "culture": "企業カルチャーページ",
        "benefits": "福利厚生ページ",
        "interview": "社員インタビューページ",
        "faq": "よくある質問ページ",
    }

    for role in missing_required:
        recs.append({
            "priority": "S",
            "type": "missing_page",
            "role": role,
            "label": role_labels.get(role, role),
            "message": f"【必須】{role_labels.get(role, role)}が見つかりません。採用サイトに必須のページです。",
        })

    for role in missing_recommended:
        recs.append({
            "priority": "A",
            "type": "missing_page",
            "role": role,
            "label": role_labels.get(role, role),
            "message": f"【推奨】{role_labels.get(role, role)}の追加を検討してください。",
        })

    # 低スコアのロール
    for role, data in role_scores.items():
        if role == "other":
            continue
        if data.get("score", 0) < 40:
            recs.append({
                "priority": "A",
                "type": "low_score",
                "role": role,
                "label": role_labels.get(role, role),
                "url": data.get("url", ""),
                "score": data.get("score", 0),
                "grade": data.get("grade", "D"),
                "issues": data.get("issues", []),
                "message": (
                    f"{role_labels.get(role, role)}のスコアが{data.get('score', 0)}点"
                    f"（{data.get('grade', 'D')}）— 改善が必要です。"
                ),
            })

    return recs


# ==================================================================
# 改善提案
# ==================================================================

def generate_improvements(all_scores, structure, url,
                          competitors=None, comparison=None,
                          target_page=None, target_role=None):
    """採用ページ向け改善提案を生成。

    target_page / target_role が指定された場合はロール特化提案を追加。
    """
    domain = url.split("//")[-1].split("/")[0] if "//" in url else url
    title = structure.get("title", "") or ""
    today = "2026-04-16"
    future_60 = "2026-06-15"

    quick_wins: list = []
    content_strategy: list = []
    technical_debt: list = []
    strategic: list = []

    low = {k for k, v in all_scores.items()
           if isinstance(v, dict) and v.get("max", 0) > 0
           and v.get("score", 0) / v["max"] < 0.5}

    # --- QW1: JobPosting JSON-LD ---
    jp_low = any(k.startswith("jl_jobposting") or k.startswith("1-") for k in low)
    if jp_low:
        quick_wins.append({
            "priority": "S",
            "title": "JobPosting JSON-LD の完全実装（Google for Jobs対応）",
            "category": "構造化データ",
            "impact": "応募数 +30〜50%",
            "kpi": "Google for Jobsでの掲載、Indeed連携",
            "why": (
                "Google for Jobs は JobPosting JSON-LD なしには絶対に掲載されません。"
                "日本企業の採用ページの約65%がこの対応をしておらず、"
                "実装するだけで大きな先行者メリットが得られます。"
                "Indeedへの自動連携にも寄与し、求人広告費を大幅削減できる可能性があります。"
            ),
            "steps": [
                "1. 募集要項（タイトル、業務内容、給与、勤務地）を構造化",
                "2. hiringOrganizationにOrganization JSON-LDを参照",
                "3. baseSalary は必ずminValue/maxValueで範囲指定",
                "4. validThrough は募集終了日、未定なら3ヶ月後を入れて運用更新",
                "5. Rich Results Testで検証 → Search Console登録",
                "6. Indexing APIでJobPostingをGoogleに即時通知（推奨）",
            ],
            "after": f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "【職種名を具体的に】例: バックエンドエンジニア（Go/Python）",
  "description": "<p>【HTMLタグ込みで業務内容・応募条件・歓迎条件・福利厚生を全て含む】</p>",
  "datePosted": "{today}",
  "validThrough": "{future_60}",
  "employmentType": "FULL_TIME",
  "hiringOrganization": {{
    "@type": "Organization",
    "name": "{domain}",
    "sameAs": "{url.rstrip('/')}",
    "logo": "{url.rstrip('/')}/logo.png"
  }},
  "jobLocation": {{
    "@type": "Place",
    "address": {{
      "@type": "PostalAddress",
      "streetAddress": "【番地】",
      "addressLocality": "【市区町村】",
      "addressRegion": "【都道府県】",
      "postalCode": "【郵便番号】",
      "addressCountry": "JP"
    }}
  }},
  "jobLocationType": "TELECOMMUTE",
  "baseSalary": {{
    "@type": "MonetaryAmount",
    "currency": "JPY",
    "value": {{
      "@type": "QuantitativeValue",
      "minValue": 5000000,
      "maxValue": 9000000,
      "unitText": "YEAR"
    }}
  }},
  "qualifications": "【必須スキル・経験を箇条書き】",
  "responsibilities": "【担当業務を箇条書き】",
  "skills": "Go, Python, AWS, Kubernetes",
  "directApply": true,
  "url": "{url}"
}}
</script>''',
            "validation": "https://search.google.com/test/rich-results で JobPosting が検出されること",
        })

    # --- QW2: 給与の明示 ---
    salary_low = any(k in ("jl_salary", "2-2_salary") for k in low)
    if salary_low:
        quick_wins.append({
            "priority": "S",
            "title": "給与情報の具体的明示（年収レンジ＋賞与条件）",
            "category": "求人情報",
            "impact": "応募率 +20〜40%",
            "kpi": "求職者の事前検討完了率、面談前離脱率 -30%",
            "why": (
                "「応相談」「当社規定による」だけの記載は、応募の最大の障壁です。"
                "Indeed調査では、給与が不明確な求人は給与明示の求人に比べ応募率が"
                "約40%低いというデータがあります。"
                "レンジ（下限〜上限）と賞与条件を明示することで、本気度の高い候補者が集まります。"
            ),
            "steps": [
                "1. モデル年収をレンジで明示（例: 500万〜900万円）",
                "2. 下限=未経験〜1年、上限=スーパーパフォーマー想定",
                "3. 固定残業代の有無、賞与、昇給条件を必ず記載",
                "4. JobPosting JSON-LD の baseSalary にも同じ値を設定",
                "5. モデルケース（X年目: ○○万円、リーダー層: ○○万円）を追加",
            ],
            "after": '''<section>
<h3>給与</h3>
<ul>
  <li><strong>年収:</strong> 500万〜900万円（経験・スキルに応じて決定）</li>
  <li><strong>月給:</strong> 35万〜65万円 ＋ 賞与年2回（業績連動）</li>
  <li><strong>固定残業代:</strong> 月45時間分を含む（超過分は別途支給）</li>
  <li><strong>昇給:</strong> 年1回（4月）、業績連動型</li>
</ul>
<h4>モデル年収</h4>
<ul>
  <li>メンバー (入社1-2年): 500〜650万円</li>
  <li>シニア (入社3-5年): 650〜850万円</li>
  <li>テックリード: 850万円〜</li>
</ul>
</section>''',
        })

    # --- QW3: カジュアル面談の導線 ---
    casual_low = any(k in ("en_low_commit", "5-5_low_commit_option") for k in low)
    if casual_low:
        quick_wins.append({
            "priority": "A",
            "title": "カジュアル面談の導線を追加",
            "category": "応募UX",
            "impact": "総エントリー数 +50〜100%",
            "kpi": "母集団形成数、カジュアル面談→本選考コンバージョン率",
            "why": (
                "『応募』のみのCTAは強いコミットメントを求めるため、"
                "検討段階の候補者を取り逃します。"
                "カジュアル面談は『応募ではなく話を聞くだけ』の低コミット選択肢として、"
                "採用広報的にも候補者ファネルの上流を太くします。"
            ),
            "steps": [
                "1. ヘッダーとページ下部に『まずはカジュアル面談』ボタン設置",
                "2. カジュアル面談の説明ページ or FAQを作成",
                "3. YoutrustやMeety、Pitta等の低コミットツール活用も検討",
                "4. Google Calendar の予約リンクを直接埋め込み",
                "5. 『選考とは無関係』『服装自由』など心理的ハードルを下げる文言",
            ],
            "after": '''<div class="cta-section">
  <a href="/recruit/casual" class="btn btn-primary">
    まずはカジュアル面談（30分・選考とは無関係）
  </a>
  <a href="/recruit/apply" class="btn btn-secondary">
    本選考に応募する
  </a>
</div>''',
        })

    # --- QW4: 選考フロー ---
    flow_low = any(k in ("en_selection_flow", "5-2_selection_flow") for k in low)
    if flow_low:
        quick_wins.append({
            "priority": "A",
            "title": "選考フローの可視化（所要期間付き）",
            "category": "応募UX",
            "impact": "応募完了率 +15%",
            "kpi": "応募フォーム開始→完了率",
            "why": (
                "候補者は『どれだけ時間がかかるか』を強く気にします。"
                "選考フロー（ステップ数、各ステップの期間、合計所要日数）を明示することで、"
                "心理的不安を取り除き、応募完了率が上がります。"
            ),
            "steps": [
                "1. 全ステップをフローチャート形式で掲載",
                "2. 各ステップの目安期間（「1週間以内に連絡」等）を記載",
                "3. 内定までの最短・最長日数を明示",
                "4. 各ステップの評価ポイントも添える（何を見るか）",
            ],
            "after": '''<section>
<h3>選考フロー（最短 2〜3週間）</h3>
<ol>
  <li><strong>エントリー</strong> → 24時間以内に担当から連絡</li>
  <li><strong>書類選考</strong> → 3営業日以内に結果通知</li>
  <li><strong>一次面接</strong>（60分・オンライン）— エンジニアリングマネージャー</li>
  <li><strong>技術課題</strong>（1週間・任意）</li>
  <li><strong>最終面接</strong>（60分・対面orオンライン）— CTO / CEO</li>
  <li><strong>オファー面談</strong>（条件調整）</li>
</ol>
</section>''',
        })

    # --- QW5: 社員紹介 ---
    staff_low = any(k in ("iv_staff_voices", "3-1_staff_voices") for k in low)
    if staff_low:
        content_strategy.append({
            "priority": "A",
            "title": "社員インタビュー記事を5名分以上追加",
            "category": "企業カルチャー",
            "impact": "滞在時間 +40%、応募率 +15%",
            "kpi": "平均セッション時間、/recruit 配下の PV",
            "why": (
                "社員の生の声は候補者が最も知りたい情報です。"
                "『どんな人が働いているか』『入社してどう変わったか』を具体的に伝えることで、"
                "候補者は自分の姿を投影できます。動画＋テキストの組み合わせが最も効果的です。"
            ),
            "steps": [
                "1. 異なる職種・年次・性別・バックグラウンドから5名を選定",
                "2. 1記事あたり: 経歴／入社理由／現在の仕事／印象的なエピソード／今後の目標",
                "3. 全記事に顔写真必須（笑顔）、可能なら5分以内の動画",
                "4. 職場の様子の写真を3-5枚ずつ",
                "5. Organization JSON-LDにemployeeとしてPerson JSON-LDを追加",
            ],
        })

    # --- QW6: 具体数値で語る ---
    numbers_low = any(k in ("bf_numbers", "4-5_concrete_numbers") for k in low)
    if numbers_low:
        content_strategy.append({
            "priority": "A",
            "title": "労働条件・文化を数値で語る",
            "category": "信頼性",
            "impact": "信頼度 +30%、応募者の質向上",
            "kpi": "面談承諾率、内定辞退率 -10%",
            "why": (
                "『働きやすい』『成長できる』等の抽象表現は信頼されません。"
                "『有給取得率89%』『平均残業時間 月12時間』『育休復帰率100%』のような"
                "数値で語ることで、主張の裏付けが生まれます。"
            ),
            "steps": [
                "1. 有給取得率、平均残業時間、育休取得/復帰率、女性管理職比率を集計",
                "2. 平均年齢、平均勤続年数、離職率も公開",
                "3. 最新版を年1回更新（『2025年度実績』と明示）",
                "4. グラフ/数値カードで視覚的に表示",
            ],
            "example_transform": [
                "Before: 「風通しの良い社風です」",
                "After: 「Slack全チャンネルオープン率100%、月1回の全社Q&Aセッション開催、CEO直通チャンネルあり」",
                "",
                "Before: 「ワークライフバランス重視」",
                "After: 「平均残業時間 月12時間、有給取得率 89.3%、育休取得率 男性78%/女性100%」",
            ],
        })

    # --- Strategic: 動画コンテンツ ---
    video_low = any(k in ("cl_video", "3-2_video_content") for k in low)
    if video_low:
        strategic.append({
            "priority": "B",
            "title": "採用動画コンテンツの制作（社員インタビュー / オフィスツアー）",
            "category": "企業カルチャー",
            "impact": "応募率 +25%、ブランド認知",
            "kpi": "動画再生完了率、採用ページ滞在時間",
            "why": (
                "テキストの10倍の情報量を伝えられる動画は、"
                "『雰囲気』『人柄』『オフィスの空気感』など言語化しにくい要素を伝える最強の手段です。"
                "YouTubeチャンネル運営は採用ブランディングの土台になります。"
            ),
            "steps": [
                "1. 社員インタビュー（5分×5本）",
                "2. オフィスツアー（3分×1本）",
                "3. CEOメッセージ（3分×1本）",
                "4. 1日の密着動画（7分×1-2本）",
                "5. YouTube + ページ内埋め込み、VideoObject JSON-LDも設置",
            ],
        })

    # --- Technical Debt ---
    org_low = "common_cred_org_jsonld" in low or "6-5_organization_jsonld" in low
    if org_low:
        technical_debt.append({
            "priority": "A",
            "title": "Organization JSON-LD の設置（JobPostingの前提）",
            "category": "構造化データ",
            "impact": "Google for Jobs連携の土台",
            "why": "JobPostingのhiringOrganizationから参照されるため、採用ページとして必須",
            "implementation": "全ページ共通の<head>内にOrganization JSON-LDを設置。logo/sameAs/addressを完備",
        })

    # --- ロール特化提案 ---
    if target_role and target_role in ROLE_REQUIREMENTS:
        role_req = ROLE_REQUIREMENTS[target_role]
        role_checks = role_req.get("checks", [])
        for check_def in role_checks:
            key = check_def["key"]
            if key in low:
                content_strategy.append({
                    "priority": "A",
                    "title": f"[{role_req['label']}] {check_def['label']}の改善",
                    "category": role_req["label"],
                    "impact": "ページ別スコア向上",
                    "why": f"{check_def['label']}のスコアが低い状態です。{role_req['label']}として重要な項目です。",
                    "steps": [f"対象ページ: {target_page or url}"],
                })

    # --- llms.txt ---
    llms_txt = f"""# {domain} — 採用情報

> {title or domain}の採用ページ。求人情報、企業カルチャー、応募方法をご案内します。

## About Hiring
- 採用ポジション一覧: {url.rstrip('/')}/positions
- カジュアル面談: {url.rstrip('/')}/casual
- 選考フロー: {url.rstrip('/')}/process

## Open Roles
- 【職種1】例: バックエンドエンジニア
- 【職種2】例: プロダクトマネージャー
- 【職種3】

## Company Culture
- ミッション / ビジョン / バリュー
- 社員インタビュー: {url.rstrip('/')}/members
- オフィス紹介: {url.rstrip('/')}/office

## Contact
- 採用担当: recruit@{domain}
"""

    # 計測計画
    measurement_plan = [
        {
            "title": "週次KPI",
            "items": [
                "Google for Jobs 表示回数（Search Console）",
                "採用ページ PV / UU",
                "エントリーフォーム送信数",
                "カジュアル面談申込数",
                "Indeed / Wantedly / Green の応募数",
            ],
        },
        {
            "title": "月次KPI",
            "items": [
                "応募→面談コンバージョン率",
                "面談→内定コンバージョン率",
                "内定承諾率",
                "チャネル別 CPA（コストパーハイヤー）",
                "社員紹介記事の平均滞在時間",
            ],
        },
    ]

    return {
        "quick_wins": quick_wins,
        "content_strategy": content_strategy,
        "technical_debt": technical_debt,
        "strategic": strategic,
        "competitor_informed": [],
        "measurement_plan": measurement_plan,
        "llms_txt_template": llms_txt,
        "organization_jsonld": "",
        "article_jsonld": "",
        "faq_jsonld": "",
    }


# ==================================================================
# テストクエリ
# ==================================================================

def generate_test_queries(url, keywords, site_title):
    """採用ページ向けテストクエリ。"""
    domain = url.split("//")[-1].split("/")[0] if "//" in url else url
    kw = keywords[0] if keywords else site_title or domain

    queries = [
        {
            "platform": "Google for Jobs",
            "query": f"{kw} 採用",
            "reason_if_not": "JobPosting JSON-LDが未設置または必須項目不足",
        },
        {
            "platform": "ChatGPT",
            "query": f"{domain}の採用情報について教えて",
            "reason_if_not": "Organization JSON-LD不足、求人情報のAI可読性不足",
        },
        {
            "platform": "ChatGPT",
            "query": f"{kw} 年収 求人",
            "reason_if_not": "給与レンジが明示されていない、JobPosting.baseSalary未設定",
        },
        {
            "platform": "Perplexity",
            "query": f"{domain} 社風 働き方",
            "reason_if_not": "社員の声・カルチャー情報が少ない、数値データ不足",
        },
        {
            "platform": "Indeed検索",
            "query": f"{kw}",
            "reason_if_not": "JobPosting構造化データがIndeedクローラーに検出されていない",
        },
    ]

    return {
        "queries": queries,
        "claude_self_eval": {
            "would_recommend": False,
            "reason": "採用プリセットによる構造化データ・求人情報の実測ベース診断。",
        },
    }
