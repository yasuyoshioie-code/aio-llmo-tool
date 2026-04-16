"""ページロール自動判定モジュール

クロールしたURLとHTML構造情報(structure辞書)から、
各ページの「役割（ロール）」を自動判定する。

判定ロジック:
  1. URLパターンマッチ（最も信頼性が高い）
  2. コンテンツマッチ（title + H1 + meta_description + 本文先頭500字）
  3. JSON-LD @type マッチ（JobPosting → job_listing）
  4. フォーム要素の有無（entry判定）
  5. どれにもマッチしなければ "other"
"""

from urllib.parse import urlparse, unquote


# ---------------------------------------------------------------------------
# ロール定義: URLパターンとコンテンツキーワード
# ---------------------------------------------------------------------------

# 判定順序が重要: より具体的なロールを先に評価する
# (role, url_patterns, content_keywords)
_ROLE_RULES = [
    # --- 採用系（具体→抽象の順に並べる） ---
    (
        "job_listing",
        ["/job/", "/position/", "/募集/"],
        [],  # JSON-LDで判定するため空
    ),
    (
        "entry",
        ["/entry", "/apply", "/form"],
        [],  # フォーム要素の有無で判定するため空
    ),
    (
        "interview",
        ["/interview", "/voice", "/people", "/staff"],
        ["社員紹介", "インタビュー", "先輩の声", "社員の声"],
    ),
    (
        "culture",
        ["/culture", "/environment", "/workplace"],
        ["社風", "働き方", "職場環境", "カルチャー"],
    ),
    (
        "benefits",
        ["/welfare", "/benefits", "/福利厚生"],
        ["福利厚生", "休暇", "手当", "待遇"],
    ),
    (
        "recruit_top",
        ["/recruit", "/career", "/hiring", "/jobs"],
        ["採用情報", "キャリア", "求人", "新卒採用", "中途採用", "採用トップ"],
    ),
    # --- 企業情報系 ---
    (
        "about",
        ["/about", "/company", "/corporate"],
        ["会社概要", "企業情報", "Corporate", "会社情報"],
    ),
    (
        "ir",
        ["/ir", "/investor", "/finance"],
        ["IR情報", "決算", "有価証券", "株主", "投資家情報"],
    ),
    (
        "csr",
        ["/csr", "/esg", "/sustainability", "/sdgs"],
        ["CSR", "ESG", "サステナビリティ", "SDGs", "社会貢献"],
    ),
    (
        "business",
        ["/service", "/business", "/solution", "/product"],
        ["事業内容", "サービス", "ソリューション", "製品情報"],
    ),
    (
        "news",
        ["/news", "/topics", "/press", "/info", "/blog"],
        ["ニュース", "お知らせ", "プレスリリース", "新着情報", "ブログ"],
    ),
    (
        "faq",
        ["/faq", "/question"],
        ["よくある質問", "FAQ"],
    ),
    (
        "contact",
        ["/contact", "/inquiry"],
        ["お問い合わせ", "Contact"],
    ),
    (
        "privacy",
        ["/privacy", "/policy"],
        ["プライバシーポリシー", "個人情報", "Privacy Policy"],
    ),
]


# ---------------------------------------------------------------------------
# プリセット別の必須/推奨ロール定義
# ---------------------------------------------------------------------------

_PRESETS = {
    "corporate": {
        "required": ["top", "about", "business", "contact", "privacy"],
        "recommended": ["news", "recruit_top", "ir", "csr", "faq"],
    },
    "recruiting": {
        "required": ["recruit_top", "job_listing", "entry"],
        "recommended": ["culture", "benefits", "interview", "faq", "contact"],
    },
}

# ロール別の日本語ラベル
_ROLE_LABELS = {
    "top": "トップページ",
    "about": "会社概要",
    "business": "事業内容",
    "ir": "IR情報",
    "news": "ニュース",
    "contact": "お問い合わせ",
    "privacy": "プライバシーポリシー",
    "recruit_top": "採用トップ",
    "job_listing": "求人詳細",
    "culture": "社風・文化",
    "benefits": "福利厚生",
    "interview": "社員インタビュー",
    "entry": "エントリー/応募",
    "faq": "FAQ",
    "csr": "CSR/ESG",
    "other": "その他",
}

# 欠落時の優先度と理由テンプレート
_MISSING_REASONS = {
    "top": ("S", "トップページが存在しない。サイトの入口として必須。"),
    "about": ("S", "会社概要ページが存在しない。企業の信頼性・E-E-A-Tに直結する。"),
    "business": ("A", "事業内容ページが存在しない。何をしている企業か不明。"),
    "contact": ("A", "お問い合わせページが存在しない。連絡先の明示は信頼性の基本。"),
    "privacy": ("A", "プライバシーポリシーが存在しない。法的にも必須。"),
    "ir": ("A", "IR情報ページが存在しない。上場企業の場合は必須。"),
    "news": ("B", "ニュース/お知らせページが存在しない。情報発信の鮮度に影響。"),
    "recruit_top": ("B", "採用トップページが存在しない。採用活動を行う場合は設置推奨。"),
    "job_listing": ("S", "求人詳細ページが存在しない。Google for Jobs連携に必須。"),
    "entry": ("S", "エントリーフォームが存在しない。応募導線が不完全。"),
    "culture": ("B", "社風・文化ページが存在しない。求職者の志望度向上に有効。"),
    "benefits": ("B", "福利厚生ページが存在しない。求職者の関心が高い情報。"),
    "interview": ("C", "社員インタビューページが存在しない。リアルな声は応募動機を強化する。"),
    "faq": ("C", "FAQページが存在しない。よくある質問を掲載すると問い合わせ削減に寄与。"),
    "csr": ("C", "CSR/ESGページが存在しない。社会的責任の発信は企業ブランドに好影響。"),
}


# ---------------------------------------------------------------------------
# メイン判定関数
# ---------------------------------------------------------------------------

def classify_page(url: str, structure: dict) -> str:
    """URLパターン + HTML内コンテンツから、ページの役割(ロール)を返す。

    判定優先順位:
      1. トップページ判定（パス）
      2. URLパターンマッチ（部分一致、最も信頼性が高い）
      3. JSON-LD @type マッチ（JobPosting → job_listing）
      4. コンテンツキーワードマッチ（title + H1 + meta + 本文先頭500字）
      5. フォーム要素の簡易検出（entry判定）
      6. どれにもマッチしなければ "other"

    Args:
        url: ページのURL
        structure: parse_html() が返す構造辞書
            キー: title, meta_description, headings, content_text, jsonld, faq_items

    Returns:
        ロール文字列（"top", "about", "business", ... , "other"）
    """
    path = urlparse(url).path.rstrip("/").lower()
    # URLデコード（日本語パス対応）
    path = unquote(path)

    # --- 1. トップページ判定 ---
    if _is_top_page(path):
        return "top"

    # --- 2. URLパターンマッチ ---
    url_role = _match_url_pattern(path)
    if url_role:
        return url_role

    # --- 3. JSON-LD @type マッチ ---
    jsonld_role = _match_jsonld(structure)
    if jsonld_role:
        return jsonld_role

    # --- 4. コンテンツキーワードマッチ ---
    content_role = _match_content(structure)
    if content_role:
        return content_role

    # --- 5. フォーム要素の簡易検出（entry判定） ---
    if _has_form_elements(structure):
        return "entry"

    # --- 6. デフォルト ---
    return "other"


def classify_pages(pages: list[dict]) -> list[dict]:
    """複数ページを一括分類。各dictに "role" キーを追加して返す。

    Args:
        pages: [{"url": "https://...", "structure": {...}}, ...]

    Returns:
        同じリストに "role" キーを追加したもの
    """
    for page in pages:
        page["role"] = classify_page(page["url"], page.get("structure", {}))
    return pages


def check_site_completeness(classified_pages: list[dict], preset_id: str) -> dict:
    """分類済みページから、サイト構造の完全性をチェック。

    Args:
        classified_pages: classify_pages() の出力
        preset_id: "corporate" or "recruiting"

    Returns:
        {
            "found_roles": {"top": ["https://..."], ...},
            "missing_required": ["ir"],
            "missing_recommended": ["csr", "faq"],
            "completeness_score": 80,
            "recommendations": [
                {"role": "ir", "priority": "S", "reason": "..."},
            ]
        }
    """
    preset = _PRESETS.get(preset_id, _PRESETS["corporate"])
    required_roles = preset["required"]
    recommended_roles = preset["recommended"]

    # ロール別にURLを集約
    found_roles: dict[str, list[str]] = {}
    for page in classified_pages:
        role = page.get("role", "other")
        url = page.get("url", "")
        if role not in found_roles:
            found_roles[role] = []
        found_roles[role].append(url)

    # 必須ロールの欠落
    missing_required = [r for r in required_roles if r not in found_roles]

    # 推奨ロールの欠落
    missing_recommended = [r for r in recommended_roles if r not in found_roles]

    # 充足率（必須ページベース）
    if required_roles:
        fulfilled = len(required_roles) - len(missing_required)
        completeness_score = round(fulfilled / len(required_roles) * 100)
    else:
        completeness_score = 100

    # 改善提案の生成
    recommendations = []
    for role in missing_required:
        priority, reason = _MISSING_REASONS.get(role, ("B", f"{_ROLE_LABELS.get(role, role)}ページが存在しない。"))
        recommendations.append({
            "role": role,
            "label": _ROLE_LABELS.get(role, role),
            "priority": priority,
            "type": "required",
            "reason": reason,
        })
    for role in missing_recommended:
        priority, reason = _MISSING_REASONS.get(role, ("C", f"{_ROLE_LABELS.get(role, role)}ページが存在しない。"))
        recommendations.append({
            "role": role,
            "label": _ROLE_LABELS.get(role, role),
            "priority": priority,
            "type": "recommended",
            "reason": reason,
        })

    # 優先度順にソート（S > A > B > C）
    priority_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    recommendations.sort(key=lambda r: priority_order.get(r["priority"], 99))

    return {
        "found_roles": found_roles,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "completeness_score": completeness_score,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 内部ヘルパー
# ---------------------------------------------------------------------------

def _is_top_page(path: str) -> bool:
    """トップページ判定。"""
    # パスなし、"/"、"/index.html"、"/index.php" 等
    if not path or path == "/":
        return True
    # /index.xxx パターン
    if path in ("/index.html", "/index.htm", "/index.php"):
        return True
    return False


def _match_url_pattern(path: str) -> str | None:
    """URLパスのパターンマッチでロールを判定。

    部分一致で判定する。具体的なパスが先にマッチするよう
    _ROLE_RULES の定義順に評価する。

    例:
      "/company/about"           → about（"/about" が部分一致）
      "/recruit/interview/tanaka" → interview（"/interview" が部分一致）
      "/career/"                  → recruit_top（"/career" が部分一致）
      "/service/cloud"            → business（"/service" が部分一致）
    """
    for role, url_patterns, _ in _ROLE_RULES:
        for pattern in url_patterns:
            if pattern in path:
                return role
    return None


def _match_jsonld(structure: dict) -> str | None:
    """JSON-LD の @type からロールを判定。"""
    jsonld_list = structure.get("jsonld", [])
    if not jsonld_list:
        return None

    for item in jsonld_list:
        if not isinstance(item, dict):
            continue
        schema_type = item.get("@type", "")
        types = schema_type if isinstance(schema_type, list) else [schema_type]

        if "JobPosting" in types:
            return "job_listing"
        if "FAQPage" in types:
            return "faq"
        # ContactPage は稀だがサポート
        if "ContactPage" in types:
            return "contact"

    return None


def _build_content_text(structure: dict) -> str:
    """判定用テキストを構築。title + H1 + meta_description + 本文先頭500字。"""
    parts = []

    title = structure.get("title", "")
    if title:
        parts.append(title)

    # H1見出しを追加
    headings = structure.get("headings", [])
    for h in headings:
        if h.get("level") == 1:
            parts.append(h.get("text", ""))

    meta_desc = structure.get("meta_description", "")
    if meta_desc:
        parts.append(meta_desc)

    content = structure.get("content_text", "")
    if content:
        parts.append(content[:500])

    return " ".join(parts)


def _match_content(structure: dict) -> str | None:
    """コンテンツキーワードからロールを判定。"""
    if not structure:
        return None

    text = _build_content_text(structure)
    if not text:
        return None

    # 各ロールのキーワードをチェック（先にマッチしたものが優先）
    for role, _, keywords in _ROLE_RULES:
        if not keywords:
            continue
        for kw in keywords:
            if kw.lower() in text.lower():
                return role

    return None


def _has_form_elements(structure: dict) -> bool:
    """フォーム要素の簡易検出。

    structure["content_text"] 中に form/input 系のテキストが
    多数出現する場合にエントリーフォームと判定。
    """
    content = structure.get("content_text", "")
    if not content:
        return False

    # 応募フォームを示すキーワードの出現をチェック
    form_indicators = ["応募", "エントリー", "氏名", "メールアドレス",
                       "電話番号", "履歴書", "職務経歴書", "送信"]
    hit_count = sum(1 for kw in form_indicators if kw in content)

    # 3つ以上のフォーム関連キーワードがあればentry判定
    return hit_count >= 3
