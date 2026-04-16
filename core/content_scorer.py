"""Python-onlyコンテンツ分析モジュール — Claude API不要で全30項目をヒューリスティクス採点"""

import re
from datetime import datetime


def analyze_content_python(content_text: str, structure: dict) -> dict:
    """カテゴリ1（コンテンツ品質）+ カテゴリ4（AI引用可能性）をPythonのみで採点。

    Claude APIの代替として、正規表現・テキスト統計ベースのヒューリスティクスで採点。
    """
    scores = {}

    # --- 1-1: Answer-first（冒頭100字に結論/定義があるか）---
    first_200 = content_text[:200]
    first_100 = content_text[:100]
    answer_markers = ["とは", "です。", "である", "結論", "まとめると",
                      "ポイントは", "答えは", "つまり", "要するに", "簡単に言うと"]
    marker_count = sum(1 for m in answer_markers if m in first_200)

    if marker_count >= 2 or any(m in first_100 for m in ["とは", "です。"]):
        af_score = 4
        af_reason = "冒頭に結論/定義文あり"
    elif marker_count >= 1:
        af_score = 2
        af_reason = "冒頭に部分的な結論あり"
    else:
        af_score = 0
        af_reason = "冒頭に結論・定義文なし"

    scores["answer_first"] = {"score": af_score, "reason": af_reason}

    # --- 1-5: 明瞭性（段落長の均一性、リスト使用）---
    paragraphs = structure.get("paragraph_count", 0)
    lists = structure.get("list_count", 0)
    tables = structure.get("table_count", 0)
    word_count = structure.get("word_count", 0)

    avg_para_len = word_count / paragraphs if paragraphs > 0 else word_count
    has_good_structure = lists >= 2 or tables >= 1

    if 80 <= avg_para_len <= 300 and has_good_structure:
        cl_score = 3
        cl_reason = f"段落平均{avg_para_len:.0f}字、リスト/テーブル活用あり"
    elif avg_para_len <= 500 or has_good_structure:
        cl_score = 1.5
        cl_reason = f"段落平均{avg_para_len:.0f}字、構造化は部分的"
    else:
        cl_score = 0
        cl_reason = f"段落平均{avg_para_len:.0f}字、冗長"

    scores["clarity"] = {"score": cl_score, "reason": cl_reason}

    # --- 4-1: 定義文（「〇〇とは△△です」パターン）---
    definition_patterns = [
        r".{2,20}とは.{5,100}です",
        r".{2,20}とは.{5,100}のこと",
        r".{2,20}とは.{5,100}を指す",
        r".{2,20}とは.{5,100}である",
        r".{2,20}は.{5,100}の略",
    ]
    def_count = 0
    for pat in definition_patterns:
        def_count += len(re.findall(pat, content_text[:30000]))

    if def_count >= 1:
        df_score = 4
        df_reason = f"定義文{def_count}件検出"
    else:
        df_score = 0
        df_reason = "定義文パターン未検出"

    scores["definition_sentences"] = {"score": df_score, "reason": df_reason}

    # --- 4-2: 数値データ（具体的な数字の使用）---
    # 金額、期間、スペック等の具体的数値を検出
    number_patterns = [
        r"\d{1,3}(,\d{3})+円",  # 金額（カンマ区切り）
        r"\d+円",                # 金額
        r"\d+万",                # 万単位
        r"\d+%",                 # パーセント
        r"\d+年",                # 年
        r"\d+ヶ月",              # ヶ月
        r"\d+日",                # 日
        r"\d+時間",              # 時間
        r"\d+km",                # 距離
        r"\d+mm",                # ミリ
        r"\d+kg",                # 重量
        r"\d+cc",                # 排気量
        r"\d+馬力",              # 馬力
        r"\d+ps",                # PS
    ]
    num_total = 0
    for pat in number_patterns:
        num_total += len(re.findall(pat, content_text[:30000], re.IGNORECASE))

    # 汎用的な数値も検出
    generic_nums = re.findall(r"\d{2,}", content_text[:3000])
    num_total += len(generic_nums) // 3  # 汎用数値は割引

    if num_total >= 10:
        nd_score = 4
        nd_reason = f"具体的数値{num_total}件以上（豊富）"
    elif num_total >= 4:
        nd_score = 2
        nd_reason = f"具体的数値{num_total}件（一部あり）"
    else:
        nd_score = 0
        nd_reason = f"具体的数値{num_total}件（不足）"

    scores["numeric_data"] = {"score": nd_score, "reason": nd_reason}

    # --- 4-3: 独自データ（一次情報マーカー）---
    original_markers = [
        "独自", "当社調べ", "自社調査", "弊社", "実際に",
        "体験", "レビュー", "使ってみ", "試してみ", "検証",
        "取材", "インタビュー", "アンケート", "調査結果",
        "筆者", "私が", "私は", "実測", "計測",
    ]
    orig_count = sum(1 for m in original_markers if m in content_text[:30000])

    if orig_count >= 3:
        od_score = 4
        od_reason = f"独自情報マーカー{orig_count}件検出"
    elif orig_count >= 1:
        od_score = 2
        od_reason = f"体験談レベル（{orig_count}件）"
    else:
        od_score = 0
        od_reason = "独自情報マーカー未検出"

    scores["original_data"] = {"score": od_score, "reason": od_reason}

    # --- 4-4: エンティティ一貫性（固有名詞の表記ゆれチェック）---
    # タイトルからキーエンティティを抽出して本文との一致を確認
    title = structure.get("title", "")
    # カタカナ固有名詞を抽出
    katakana_entities = re.findall(r"[ァ-ヶー]{3,}", title)
    # 英字固有名詞を抽出
    alpha_entities = re.findall(r"[A-Za-z]{3,}", title)

    entities = katakana_entities + alpha_entities
    if entities:
        consistent = sum(1 for e in entities if e in content_text[:30000])
        ratio = consistent / len(entities) if entities else 0

        if ratio >= 0.8:
            ec_score = 4
            ec_reason = f"エンティティ表記統一（{consistent}/{len(entities)}）"
        elif ratio >= 0.5:
            ec_score = 2
            ec_reason = f"一部表記ゆれ（{consistent}/{len(entities)}）"
        else:
            ec_score = 0
            ec_reason = f"表記不統一（{consistent}/{len(entities)}）"
    else:
        ec_score = 3  # エンティティ検出不能時はやや甘め
        ec_reason = "固有名詞の自動検出不能（推定）"

    scores["entity_consistency"] = {"score": ec_score, "reason": ec_reason}

    return scores


def analyze_eeat_python(content_text: str, structure: dict) -> dict:
    """カテゴリ3（E-E-A-T）をPythonのみで採点。"""
    scores = {}

    # --- 3-1: 著者情報 ---
    author = structure.get("author", {})
    if author.get("name") and author.get("url"):
        au_score = 4
        au_reason = f"著者名+プロフィールリンクあり: {author['name']}"
    elif author.get("name"):
        au_score = 2
        au_reason = f"著者名のみ: {author['name']}"
    else:
        au_score = 0
        au_reason = "著者情報未検出"

    scores["author_display"] = {"score": au_score, "reason": au_reason}

    # --- 3-2: 運営者情報 ---
    operator_markers = ["会社概要", "運営者", "代表者", "所在地", "連絡先",
                        "設立", "法人", "株式会社", "合同会社", "事業者"]
    # JSON-LDのOrganizationからも判定
    has_org_jsonld = any(
        s.get("@type") == "Organization" for s in structure.get("jsonld", [])
    )
    op_markers_found = sum(1 for m in operator_markers if m in content_text[:10000])

    if has_org_jsonld and op_markers_found >= 3:
        op_score = 4
        op_reason = f"Organization JSON-LD + 運営者情報{op_markers_found}項目"
    elif has_org_jsonld or op_markers_found >= 2:
        op_score = 2
        op_reason = f"運営者情報一部あり（{op_markers_found}項目）"
    else:
        op_score = 0
        op_reason = "運営者情報未検出"

    scores["operator_info"] = {"score": op_score, "reason": op_reason}

    # --- 3-3: 引用・出典 ---
    # 外部リンク数で近似
    est_external = structure.get("external_links", 0)
    if est_external == 0:
        # structureにexternal_linksがない場合、URLからドメインを抽出して外部リンクを推定
        canonical = structure.get("canonical", "") or ""
        if canonical:
            _canon_domain = canonical.split("//")[-1].split("/")[0].lower() if "//" in canonical else ""
        else:
            _canon_domain = ""
        ext_link_pattern = r'https?://([^\s"<>)/]+)'
        all_domains = re.findall(ext_link_pattern, content_text[:10000])
        if _canon_domain:
            est_external = sum(1 for d in all_domains if d.lower() != _canon_domain)
        else:
            est_external = len(all_domains) // 2

    if est_external >= 5:
        ci_score = 3
        ci_reason = f"外部リンク推定{est_external}件（引用豊富）"
    elif est_external >= 2:
        ci_score = 1.5
        ci_reason = f"外部リンク推定{est_external}件（一部引用あり）"
    else:
        ci_score = 0
        ci_reason = "外部引用リンク少"

    scores["citations"] = {"score": ci_score, "reason": ci_reason}

    # --- 3-5: 経験（一次体験）---
    exp_markers = ["実際に", "体験", "使ってみ", "試してみ", "レビュー",
                   "感想", "正直", "個人的に", "率直に", "実感",
                   "やってみた", "行ってみた", "買ってみた"]
    exp_count = sum(1 for m in exp_markers if m in content_text[:30000])

    if exp_count >= 3:
        ex_score = 3
        ex_reason = f"一次体験マーカー{exp_count}件"
    elif exp_count >= 1:
        ex_score = 1.5
        ex_reason = f"体験マーカー{exp_count}件（一部あり）"
    else:
        ex_score = 0
        ex_reason = "体験・実績の記述なし"

    scores["experience"] = {"score": ex_score, "reason": ex_reason}

    # --- 3-4: 編集ポリシー ---
    policy_markers = ["免責事項", "プライバシーポリシー", "編集方針",
                      "利用規約", "著作権", "監修"]
    pol_count = sum(1 for m in policy_markers if m in content_text[:15000])

    if pol_count >= 2:
        ed_score = 3
        ed_reason = f"編集ポリシー関連{pol_count}件検出"
    elif pol_count >= 1:
        ed_score = 1.5
        ed_reason = f"簡易記載あり（{pol_count}件）"
    else:
        ed_score = 0
        ed_reason = "編集ポリシー記述なし"

    scores["editorial_policy"] = {"score": ed_score, "reason": ed_reason}

    # --- 3-6: 外部一貫性（外部リンク数ベース）---
    ext_link_count = structure.get("external_links", 0)
    if ext_link_count == 0:
        # structureに外部リンク数がない場合、content_text中のURL数から推定
        ext_link_count = len(re.findall(r'https?://', content_text))
    if ext_link_count >= 5:
        ec6_score = 3
        ec6_reason = f"外部リンク{ext_link_count}件（外部参照充実）"
    elif ext_link_count >= 2:
        ec6_score = 1.5
        ec6_reason = f"外部リンク{ext_link_count}件（一部あり）"
    else:
        ec6_score = 0
        ec6_reason = f"外部リンク{ext_link_count}件（不足）"
    scores["external_consistency"] = {
        "score": ec6_score,
        "reason": ec6_reason,
    }

    return scores


def generate_improvements_python(
    all_scores: dict, structure: dict, site_url: str,
    competitors: list = None, comparison: dict = None,
) -> dict:
    """プロSEOコンサル水準の網羅的な改善提案を生成。

    出力:
      quick_wins: 1日以内で効果大の施策（詳細な手順 + Before/After + KPI）
      strategic: 中長期の戦略施策
      technical_debt: 技術的負債の解消施策
      content_strategy: コンテンツ戦略施策
      measurement_plan: 計測計画
      competitor_informed: 競合ベースの施策
      llms_txt_template / organization_jsonld / article_jsonld / faq_jsonld: 即コピペ可能なテンプレ
    """
    title = structure.get("title", "") or ""
    meta_desc = structure.get("meta_description", "") or ""
    domain = site_url.split("//")[-1].split("/")[0] if "//" in site_url else site_url
    word_count = structure.get("word_count", 0)
    headings = structure.get("headings", [])
    h2_count = sum(1 for h in headings if h.get("level") == 2)
    faq_items = structure.get("faq_items", [])
    jsonld_list = structure.get("jsonld", [])
    jsonld_types = {s.get("@type") for s in jsonld_list if isinstance(s, dict)}
    author = structure.get("author", {})
    dates = structure.get("dates", {})
    today = datetime.now().strftime("%Y-%m-%d")

    competitors = competitors or []
    comparison = comparison or {}

    # スコア低項目
    low_items = []
    mid_items = []
    for key, item in all_scores.items():
        max_score = item.get("max", 0)
        score = item.get("score", 0)
        if max_score > 0:
            ratio = score / max_score
            if ratio < 0.5:
                low_items.append((key, item, ratio))
            elif ratio < 0.8:
                mid_items.append((key, item, ratio))
    low_keys = {k for k, _, _ in low_items}
    mid_keys = {k for k, _, _ in mid_items}

    quick_wins: list[dict] = []
    strategic: list[dict] = []
    technical_debt: list[dict] = []
    content_strategy: list[dict] = []
    measurement_plan: list[dict] = []
    competitor_informed: list[dict] = []

    # ==========================================
    # Quick Wins（1日以内 / 高インパクト）
    # ==========================================

    # --- QW1: Organization JSON-LD ---
    if "Organization" not in jsonld_types:
        quick_wins.append({
            "priority": "S",
            "title": "Organization JSON-LDの設置",
            "category": "構造化データ",
            "effort": "30分",
            "impact": "高",
            "kpi": "AI Overviewでのブランド認識率 +30%、ナレッジパネル表示の可能性",
            "why": (
                "AIは『どの組織の情報か』を判別できないと引用を避ける傾向があります。"
                "Organization JSON-LDはサイト運営者の公式宣言として機能し、"
                "ChatGPTやPerplexityが参照元を明示する際の信頼度に直結します。"
                "特にlogo/sameAs/contactPointを揃えることで、"
                "Google Knowledge Graphへの取り込み確率が上がります。"
            ),
            "steps": [
                "1. ロゴ画像（正方形/横長）のURLを確定（推奨: 112x112px以上のPNG）",
                "2. SNS公式アカウントURL（X/Facebook/LinkedIn/YouTube等）を列挙",
                "3. 下記JSON-LDを全ページ共通の<head>内に設置",
                "4. Rich Results Testで検証（search.google.com/test/rich-results）",
                "5. 1週間後にGoogle Search Consoleのエンハンスメントで反映確認",
            ],
            "before": "（Organization JSON-LDなし — AIはサイト運営者情報を推測に依存）",
            "after": f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "{domain}",
  "url": "{site_url}",
  "logo": {{
    "@type": "ImageObject",
    "url": "{site_url}/logo.png",
    "width": 600,
    "height": 600
  }},
  "description": "{meta_desc[:160] if meta_desc else '（サイトの要約文160字以内）'}",
  "sameAs": [
    "https://x.com/YOUR_ACCOUNT",
    "https://www.facebook.com/YOUR_PAGE",
    "https://www.linkedin.com/company/YOUR_COMPANY"
  ],
  "contactPoint": {{
    "@type": "ContactPoint",
    "telephone": "+81-XX-XXXX-XXXX",
    "contactType": "customer service",
    "availableLanguage": ["Japanese", "English"]
  }}
}}
</script>''',
            "validation": "https://search.google.com/test/rich-results でOrganization型がDetectedになれば成功",
        })

    # --- QW2: FAQPage JSON-LD ---
    if "FAQPage" not in jsonld_types and len(faq_items) >= 3:
        quick_wins.append({
            "priority": "S",
            "title": "FAQPage JSON-LDの追加（既存FAQを構造化）",
            "category": "構造化データ",
            "effort": "1時間",
            "impact": "高",
            "kpi": "Google AI Overviewでの引用率 +40%、検索結果のFAQリッチリザルト表示",
            "why": (
                f"既にページ内にFAQ相当の箇所が{len(faq_items)}件検出されていますが、"
                "JSON-LD化されていないためAIが『これはFAQだ』と認識できません。"
                "FAQPage JSON-LDは Google AI Overview、ChatGPT、Perplexityすべてが"
                "『Q&A形式のクエリ』に対して最優先で引用する形式です。"
                "既存のFAQをJSON-LD化するだけで実質的な工数は1時間です。"
            ),
            "steps": [
                "1. 既存のFAQ要素（Q&A）を抽出（JavaScriptで自動生成も可）",
                "2. 質問は50字以内、回答は150-300字が推奨",
                "3. 回答には具体的な数値・固有名詞を含める（AIが引用しやすい）",
                "4. FAQ JSON-LDをページ下部の<head>またはFAQセクション直前に設置",
                "5. Rich Results Test で FAQPage 検出を確認",
                "6. Google Search Consoleでクリック率・表示回数をモニタリング",
            ],
            "before": f"（ページ内にFAQ相当の{len(faq_items)}件あるがJSON-LD未実装）",
            "after": '''<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "具体的な質問1（ユーザーの検索クエリを意識）",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "150-300字の具体的で数値を含む回答。定義文＋根拠＋実例の3要素で構成する。"
      }
    },
    {
      "@type": "Question",
      "name": "具体的な質問2",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "回答テキスト。「〇〇の場合は△△です。具体的には□□％、期間は××日程度です」のパターン推奨。"
      }
    }
  ]
}
</script>''',
            "validation": "Rich Results TestでFAQPage型が表示され、Q&Aが全件リストアップされること",
        })
    elif "FAQPage" not in jsonld_types and len(faq_items) < 3:
        content_strategy.append({
            "priority": "A",
            "title": "FAQセクションの新規追加（7問以上）",
            "category": "コンテンツ追加",
            "effort": "2-3時間",
            "impact": "高",
            "kpi": "AI引用率 +40%、ロングテール検索流入 +20%",
            "why": (
                "FAQはAI検索で最も引用されやすいコンテンツ形式の1つです。"
                "ユーザーが実際にAIに投げるクエリ（「〜とは」「〜の違い」「〜いくら」「〜方法」）を"
                "そのままQuestionにし、150-300字で端的に答えるとAIが引用候補として最優先します。"
            ),
            "steps": [
                "1. Google検索の「他の人はこちらも質問」からQ候補を10件抽出",
                "2. ChatGPTに「〇〇について検索ユーザーが知りたい質問10個」と質問して追加候補を得る",
                "3. 7-10問に絞る（少なすぎると効果薄、多すぎると回答品質が落ちる）",
                "4. 各回答は定義文＋具体数値＋実例の3要素で150-300字",
                "5. 同時にFAQPage JSON-LDを設置",
            ],
            "example_questions": [
                f"{title or '対象サービス'}とは何ですか？",
                f"{title or '対象サービス'}の料金はいくらですか？",
                f"{title or '対象サービス'}と他社の違いは？",
                f"{title or '対象サービス'}を利用する流れは？",
                f"{title or '対象サービス'}のメリット・デメリットは？",
            ],
        })

    # --- QW3: Article JSON-LD（記事ページのみ）---
    if "Article" not in jsonld_types and "BlogPosting" not in jsonld_types and "NewsArticle" not in jsonld_types:
        has_dates = bool(dates.get("published") or dates.get("modified"))
        if has_dates or "blog" in site_url.lower() or "article" in site_url.lower() or "news" in site_url.lower():
            quick_wins.append({
                "priority": "A",
                "title": "Article JSON-LDの設置（記事ページ）",
                "category": "構造化データ",
                "effort": "45分",
                "impact": "高",
                "kpi": "記事の引用率 +25%、datePublished/dateModifiedのAI参照",
                "why": (
                    "記事ページに Article / BlogPosting 構造化データがないと、"
                    "AIは『これが記事コンテンツ』『誰が書いたか』『いつの情報か』を判別できません。"
                    "dateModifiedは特に重要で、AIは新しい情報を優先引用します。"
                ),
                "steps": [
                    "1. 公開日・更新日をISO 8601形式（YYYY-MM-DD）で確定",
                    "2. 著者情報（name, url）を確定",
                    "3. アイキャッチ画像（1200x630px推奨）のURLを確定",
                    "4. Article JSON-LDを記事ページテンプレートに動的埋め込み",
                    "5. WordPress等ならプラグイン（Yoast/RankMath等）で自動化も可",
                ],
                "before": "（Article JSON-LDなし）",
                "after": f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title[:110]}",
  "description": "{meta_desc[:160] if meta_desc else '記事の要約160字以内'}",
  "image": ["{site_url}/images/featured.jpg"],
  "datePublished": "{dates.get('published', today)[:10] if dates.get('published') else today}",
  "dateModified": "{dates.get('modified', today)[:10] if dates.get('modified') else today}",
  "author": {{
    "@type": "Person",
    "name": "{author.get('name', '著者名')}",
    "url": "{author.get('url', site_url + '/about')}"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "{domain}",
    "logo": {{
      "@type": "ImageObject",
      "url": "{site_url}/logo.png"
    }}
  }},
  "mainEntityOfPage": "{site_url}"
}}
</script>''',
                "validation": "Rich Results TestでArticle型検出 + datePublished/dateModifiedが正しく表示",
            })

    # --- QW4: Answer-first ---
    if "1-1_answer_first" in low_keys or "answer_first" in low_keys:
        quick_wins.append({
            "priority": "S",
            "title": "冒頭200字にAnswer-first構造を実装",
            "category": "コンテンツ構造",
            "effort": "1-2時間",
            "impact": "最高",
            "kpi": "AI Overview引用率 +50%、直帰率 -10%",
            "why": (
                "Google AI Overview、ChatGPT、Perplexityは、ページを読む際に"
                "『冒頭200字』を最重要セクションとして扱います。"
                "ここに定義文・結論・3つのポイントが揃っていれば、"
                "AIはこの部分をそのまま引用・要約ソースとして採用します。"
                "逆に導入文だけの記事はほぼ引用されません。"
            ),
            "steps": [
                f"1. 『{title or 'タイトル'}とは、〇〇のことです』の1文で開始（50字以内）",
                "2. 続けて『具体的には△△で、□□という特徴があります』（100字以内）",
                "3. 続けて『ポイントは以下の3つ』と3項目の箇条書き（各30字）",
                "4. この冒頭ブロックは目次より前に配置（目次が先だと冒頭と認識されない）",
                "5. この200字内に主要キーワードを2-3回自然に含める",
            ],
            "before": "（冒頭が一般的な導入文 — 定義・結論なし）",
            "after": f'''<p><strong>{title or '〇〇'}とは、【20-50字の1文定義】です。</strong>
具体的には【50-100字の補足】で、【差別化ポイント】という特徴があります。</p>

<p>重要なポイントは以下の3つです：</p>
<ul>
  <li><strong>ポイント1:</strong> 【具体的数値を含む説明 30字】</li>
  <li><strong>ポイント2:</strong> 【独自性のある説明 30字】</li>
  <li><strong>ポイント3:</strong> 【実例/事例を示す説明 30字】</li>
</ul>''',
            "validation": "冒頭200字を音読して『質問→回答』として成立するか確認",
        })

    # --- QW5: AIクローラー許可 ---
    if "6-1_ai_crawlers" in low_keys or any(k for k in low_keys if "crawler" in k):
        quick_wins.append({
            "priority": "S",
            "title": "AIクローラー（GPTBot/ClaudeBot/Google-Extended等）の明示的許可",
            "category": "テクニカル",
            "effort": "15分",
            "impact": "最高",
            "kpi": "AI学習・検索での発見可能性（ブロック中なら0→100）",
            "why": (
                "robots.txtでAIクローラーをブロックしていると、"
                "そのサイトは ChatGPT・Claude・Google AI Overview の情報源から"
                "完全に除外されます。WordPress等の初期設定で意図せずブロックされているケースが多発しています。"
                "許可設定を明示することで、『許可されているサイト』として優先的にクロールされます。"
            ),
            "steps": [
                "1. 現在の robots.txt を確認（https://yoursite.com/robots.txt）",
                "2. Disallow が全体に効いていないか確認",
                "3. 主要AIクローラーを明示的にAllow",
                "4. 保存後、各社のクローラー検証ツールで確認",
            ],
            "before": "# 現状、GPTBot等がブロックされている可能性\nUser-agent: *\nDisallow: /",
            "after": '''User-agent: *
Allow: /

# AI検索・学習クローラーの明示的許可
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: CCBot
Allow: /

User-agent: Bytespider
Allow: /

Sitemap: ''' + site_url.rstrip("/") + '''/sitemap.xml''',
            "validation": "https://yoursite.com/robots.txt でAllowが反映されていること、各クローラーが個別に明示されていること",
        })

    # --- QW6: 更新日表示 ---
    if not dates.get("modified"):
        quick_wins.append({
            "priority": "A",
            "title": "更新日の可視化 + dateModifiedの実装",
            "category": "鮮度シグナル",
            "effort": "30分",
            "impact": "高",
            "kpi": "AIでの引用優先度 +20%、『最新情報』クエリでの引用確率 up",
            "why": (
                "AIは情報の鮮度を厳しく判定します。更新日がないページは"
                "『古い情報の可能性』として引用優先度が下がります。"
                "特に2024年以降、ChatGPTは明示的に最新日付を参照する挙動が確認されています。"
            ),
            "steps": [
                "1. 記事本文上部に『最終更新: YYYY年MM月DD日』を表示",
                "2. HTMLは<time datetime='YYYY-MM-DD'>要素を使用",
                "3. Article JSON-LD の dateModified に同じ日付",
                "4. 実質的な更新（内容の変更）を伴うことが重要（日付だけ更新は評価されない）",
            ],
            "before": "（更新日の表示なし）",
            "after": f'''<p class="updated">
  最終更新: <time datetime="{today}">{today[:4]}年{today[5:7]}月{today[8:10]}日</time>
  <span class="author">by {author.get('name', '編集部')}</span>
</p>

<!-- Article JSON-LDに以下を追加 -->
"dateModified": "{today}"''',
            "validation": "ページ表示で更新日が見え、Rich Results Testでdateが読み取れること",
        })

    # --- QW7: llms.txt設置 ---
    quick_wins.append({
        "priority": "A",
        "title": "llms.txt の設置（LLM最適化の新規格）",
        "category": "LLMO技術",
        "effort": "1時間",
        "impact": "中-高",
        "kpi": "LLMからの構造化された参照、先行者メリット",
        "why": (
            "llms.txt は Anthropic と複数のAI企業が推進している新しい規格で、"
            "サイトの要約・主要コンテンツをLLMに分かりやすく提示する仕様です。"
            "2026年現在、設置サイトはまだ少数のため、設置するだけで競合優位性を得られます。"
            "内容は robots.txt と異なり、『歓迎するLLMへの案内状』として機能します。"
        ),
        "steps": [
            "1. サイトルートに llms.txt を作成（/llms.txt でアクセス可能に）",
            "2. サイト概要、主要ページ、API、ポリシーを構造的に記述",
            "3. 長文版の llms-full.txt も併設（全記事のMarkdown版）推奨",
            "4. 月次で更新、最新の主要記事を反映",
        ],
        "template_file": "llms_txt_template",
    })

    # --- QW8: 著者情報 ---
    if not author.get("name") or not author.get("url"):
        quick_wins.append({
            "priority": "A",
            "title": "著者情報ボックスの実装（E-E-A-T強化）",
            "category": "E-E-A-T",
            "effort": "2-3時間（プロフィールページ含む）",
            "impact": "中-高",
            "kpi": "E-E-A-Tスコア +15%、AIでの専門性認識",
            "why": (
                "2024年のGoogleコアアップデート以降、著者情報の有無は品質評価の"
                "重要シグナルになっています。AIはさらに厳格で、"
                "『著者不明の情報』は医療・金融・法律等のYMYL分野で"
                "実質的に引用対象外になります。"
            ),
            "steps": [
                "1. 著者プロフィールページ（/about/author-name）を作成",
                "2. 経歴・専門分野・資格・実績・SNS・代表著作を記載",
                "3. 記事末尾に著者ボックスを設置（顔写真 + 肩書き + リンク）",
                "4. Person JSON-LD を著者ページに設置",
                "5. Article JSON-LD の author を Person型に",
                "6. 可能ならLinkedIn、X、GitHubとの相互リンクでsameAsを実装",
            ],
            "before": "（著者情報なし — AIは『誰が書いた情報か』判定不能）",
            "after": '''<div class="author-box" itemscope itemtype="https://schema.org/Person">
  <img src="/images/authors/taro.jpg" alt="山田太郎" itemprop="image">
  <div class="author-info">
    <h3 itemprop="name">山田太郎</h3>
    <p itemprop="jobTitle">SEOコンサルタント / 〇〇協会認定講師</p>
    <p itemprop="description">
      2015年より独立系SEOコンサルタント。月間流入10万UU超のメディアを5社以上グロース。
      著書『〇〇』（〇〇社）。
    </p>
    <a href="/about/yamada-taro" itemprop="url">プロフィール詳細</a>
  </div>
</div>

<!-- Person JSON-LD -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Person",
  "name": "山田太郎",
  "jobTitle": "SEOコンサルタント",
  "url": "''' + site_url.rstrip('/') + '''/about/yamada-taro",
  "sameAs": [
    "https://x.com/yamada_taro",
    "https://www.linkedin.com/in/yamada-taro",
    "https://github.com/yamada-taro"
  ],
  "knowsAbout": ["SEO", "コンテンツマーケティング", "AIO"]
}
</script>''',
            "validation": "Rich Results Testで Person型検出、プロフィールページが著者名で検索可能に",
        })

    # ==========================================
    # Strategic（中長期）
    # ==========================================

    # --- 競合ベースの文字数ギャップ ---
    if competitors:
        self_wc = word_count
        comp_wcs = [c.get("word_count", 0) for c in competitors if c.get("word_count")]
        if comp_wcs:
            comp_avg_wc = sum(comp_wcs) / len(comp_wcs)
            comp_max_wc = max(comp_wcs)
            if self_wc < comp_avg_wc * 0.7:
                competitor_informed.append({
                    "priority": "A",
                    "title": f"コンテンツ深度の強化（文字数 {self_wc:,}字 → 目標 {int(comp_avg_wc):,}字）",
                    "category": "コンテンツ戦略",
                    "effort": "1-2週間",
                    "impact": "高",
                    "kpi": "検索順位 +3-5位、滞在時間 +30%、AI引用候補化",
                    "why": (
                        f"競合上位{len(competitors)}サイトの平均文字数は {int(comp_avg_wc):,}字、"
                        f"最大で {comp_max_wc:,}字です。"
                        f"自サイトは {self_wc:,}字で、平均の{int(self_wc/comp_avg_wc*100)}%にとどまります。"
                        "AI・Googleはトピックの網羅性を厳しく見ており、文字数不足 = 情報不足と判定されます。"
                    ),
                    "steps": [
                        "1. 競合上位サイトのH2・H3を抽出し、自サイトにないトピックをリスト化",
                        "2. 『missing_topics』（カバー不足トピック）を優先的に追加",
                        "3. 各H2セクションは最低300字以上、数値・具体例を含める",
                        "4. 独自データ・一次情報セクションを1つ以上追加（差別化）",
                        "5. FAQを7問以上追加で自然に文字数を増やす",
                    ],
                })

            if comparison.get("missing_topics"):
                missing = comparison["missing_topics"][:8]
                content_strategy.append({
                    "priority": "A",
                    "title": f"カバー不足トピックの追加（{len(missing)}件）",
                    "category": "トピックカバレッジ",
                    "effort": "2-3日",
                    "impact": "高",
                    "kpi": "ロングテール流入 +30%、AIでの関連クエリ引用率 up",
                    "why": (
                        "競合上位サイトには存在し、自サイトには存在しないトピックは、"
                        "AI検索・通常検索の両方で『情報の抜け漏れ』として評価を下げます。"
                        "これらのトピックを既存記事に追加するか、関連記事として新規作成することで"
                        "トピッククラスター全体のカバレッジが改善されます。"
                    ),
                    "missing_topics": missing,
                    "steps": [
                        "1. 各トピックについて既存記事に追加可能か判定",
                        "2. 追加可能なら該当H2セクションを作成（300字以上）",
                        "3. 追加不可なら関連記事として新規作成 → 内部リンクで接続",
                        "4. 全トピックを網羅した『まとめページ』（ハブページ）を作成",
                    ],
                })

    # --- コンテンツ密度強化 ---
    if "4-2_numeric_data" in low_keys or "numeric_data" in low_keys:
        content_strategy.append({
            "priority": "A",
            "title": "情報密度の強化（数値・事例・固有名詞の追加）",
            "category": "情報密度",
            "effort": "2-3日",
            "impact": "高",
            "kpi": "AI引用時の選好率 +30%、滞在時間 +20%",
            "why": (
                "AIは抽象的な記述よりも具体的な数値・固有名詞・事例を優先的に引用します。"
                "『多い』『大きい』『高速』等の曖昧表現は引用されませんが、"
                "『月間10万PV』『1.5倍高速』『2024年度No.1』等は引用されます。"
            ),
            "steps": [
                "1. 記事内の抽象表現を全てリストアップ",
                "2. 各抽象表現に具体数値・固有名詞・年月を付与",
                "3. 可能なら独自調査・実測値を1件以上追加（Information Gain）",
                "4. 数値には必ず出典（自社調査/公的データ/論文等）を明記",
                "5. 比較表・データテーブルを1つ以上設置",
            ],
            "example_transform": [
                "Before: 『多くの企業が導入している』",
                "After: 『2024年時点で国内上場企業の38.7%（経産省調査）が導入している』",
                "",
                "Before: 『処理速度が速い』",
                "After: 『従来比1.6倍高速（自社テスト、平均応答時間260ms）』",
            ],
        })

    # --- H2要約ブロック戦略 ---
    if "1-2_layer2" in low_keys or h2_count >= 3:
        strategic.append({
            "priority": "B",
            "title": "AIO第2層：各H2直後に100-150字の要約ブロック配置",
            "category": "AIO構造",
            "effort": "1日",
            "impact": "中-高",
            "kpi": "Perplexity引用率 +25%、セクション単位のAI参照",
            "why": (
                "AI検索の最新研究では、AIはページを『H2単位のチャンク』に分解して"
                "各チャンクの意味を評価します。各H2直後に『このセクションの結論』を"
                "100-150字で置くことで、セクション単位で引用される確率が大幅に上がります。"
            ),
            "steps": [
                "1. 各H2の直後に太字または引用ブロックで要約を配置",
                "2. 要約は『このセクションでは、〇〇について△△を解説します。結論は□□です』の型",
                "3. 目安：H2が5つなら5つの要約ブロック × 125字 = 625字の追加",
            ],
            "before": "<h2>セクションタイトル</h2>\n<p>一般的な導入文...</p>",
            "after": '''<h2>セクションタイトル</h2>
<blockquote class="section-summary">
  <strong>このセクションの結論：</strong>
  〇〇とは△△であり、□□という特徴があります。
  具体的には、××％のケースで効果が確認されており、導入期間は平均○○日です。
</blockquote>
<p>詳細：...</p>''',
        })

    # ==========================================
    # Technical Debt
    # ==========================================

    if "2-4_breadcrumb" in low_keys or "BreadcrumbList" not in jsonld_types:
        technical_debt.append({
            "priority": "B",
            "title": "BreadcrumbList JSON-LDの設置",
            "category": "サイト構造",
            "effort": "2-3時間",
            "impact": "中",
            "kpi": "検索結果でのパンくず表示、サイト構造のAI理解促進",
            "why": "BreadcrumbListはサイトの階層構造をAIに示す基本的な構造化データ。設置していないと、AIはURL構造から推測するしかない。",
            "implementation": "各ページテンプレートに動的に生成するJSON-LDを追加。WordPressならYoast/RankMath等のプラグインで自動化可能。",
        })

    if structure.get("images_without_alt", 0) > 5:
        technical_debt.append({
            "priority": "B",
            "title": f"画像alt属性の整備（現在 {structure['images_without_alt']}件欠落）",
            "category": "アクセシビリティ/SEO",
            "effort": "1-2日",
            "impact": "中",
            "kpi": "画像検索流入、AIのマルチモーダル参照精度",
            "why": "alt属性がないとAIは画像の内容を理解できず、画像を含む文脈全体の理解が弱まる。Google ImagesからのAI検索流入も失う。",
            "steps": [
                "1. 全画像のalt欠落を抽出（HTMLから一括検出）",
                "2. 各画像について10-60字で内容を記述",
                "3. 装飾画像はalt=\"\"で明示（AI・スクリーンリーダー両対応）",
                "4. 記事のメイン画像には記事の主要キーワードを自然に含める",
            ],
        })

    # ==========================================
    # Measurement Plan
    # ==========================================

    measurement_plan.append({
        "title": "週次モニタリング項目",
        "items": [
            "Google Search Console: 表示回数、CTR、平均掲載順位（週次）",
            "Bing Webmaster Tools: Bingチャット（Copilot）経由の流入",
            "Otterly.AI: AI引用率、引用プロンプト、競合シェア（登録推奨）",
            "BrandLens / Profound: ChatGPT・Perplexityでの自ブランド言及率",
            "GA4: Organic Searchの滞在時間、直帰率",
        ],
    })

    measurement_plan.append({
        "title": "月次AIテストクエリ（手動実行）",
        "items": [
            f"ChatGPT で『{title or domain}について教えて』→ 自社引用有無",
            f"ChatGPT で主要KWの質問 → 引用サイトTop5を記録",
            f"Perplexity で同じクエリ → 引用の違いを比較",
            f"Google検索 → AI Overview欄に自社が表示されるか記録",
            "競合3社について同じテスト → 相対ポジション把握",
        ],
    })

    # ==========================================
    # 既存の低スコア項目を網羅的にカバー
    # ==========================================
    covered_titles = {q["title"] for q in quick_wins + strategic + technical_debt + content_strategy}
    for key, item, ratio in low_items + mid_items:
        label = key.split("_", 1)[1] if "_" in key else key
        title_fragment = f"{label}の改善"
        if any(title_fragment in t for t in covered_titles):
            continue
        strategic.append({
            "priority": "B" if ratio < 0.5 else "C",
            "title": f"{label}の改善（現在 {item.get('score',0)}/{item.get('max',0)}）",
            "category": key.split("_")[0] if "_" in key else "その他",
            "effort": "要見積もり",
            "impact": "中",
            "kpi": f"該当項目のスコア {item.get('score',0)} → {item.get('max',0)}",
            "why": item.get("reason", ""),
        })

    # ==========================================
    # テンプレート
    # ==========================================
    llms_txt = f"""# {domain}

> {meta_desc[:200] if meta_desc else title or 'サイトの1-2行要約（160-200字）をここに'}

## About
- サイト名: {title or domain}
- URL: {site_url}
- 提供価値: 【主要サービス・取扱領域を2-3行で】
- 対象読者: 【想定読者プロフィール】
- 著者/運営: {author.get('name') or domain}

## Key Pages
- [トップページ]({site_url})
- [会社概要]({site_url.rstrip('/')}/about)
- [サービス一覧]({site_url.rstrip('/')}/services)
- [お問い合わせ]({site_url.rstrip('/')}/contact)

## Featured Content
- 【主要記事1のタイトル】: {site_url.rstrip('/')}/article-1
- 【主要記事2のタイトル】: {site_url.rstrip('/')}/article-2
- 【主要記事3のタイトル】: {site_url.rstrip('/')}/article-3

## Citation Policy
AIによる引用時は、出典として「{domain}」とURLを明記してください。
商用転載・翻訳には別途許諾が必要です。

## Optional
- [llms-full.txt]({site_url.rstrip('/')}/llms-full.txt) — 全主要コンテンツのMarkdown版
- [sitemap.xml]({site_url.rstrip('/')}/sitemap.xml)
"""

    org_jsonld = f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "{domain}",
  "url": "{site_url}",
  "logo": {{
    "@type": "ImageObject",
    "url": "{site_url.rstrip('/')}/logo.png",
    "width": 600,
    "height": 600
  }},
  "description": "{meta_desc[:200] if meta_desc else '（サイトの要約文 160-200字）'}",
  "sameAs": [
    "https://x.com/YOUR_ACCOUNT",
    "https://www.facebook.com/YOUR_PAGE",
    "https://www.linkedin.com/company/YOUR_COMPANY",
    "https://www.youtube.com/@YOUR_CHANNEL"
  ],
  "contactPoint": {{
    "@type": "ContactPoint",
    "telephone": "+81-XX-XXXX-XXXX",
    "contactType": "customer service",
    "availableLanguage": ["Japanese", "English"],
    "areaServed": "JP"
  }},
  "address": {{
    "@type": "PostalAddress",
    "streetAddress": "【住所】",
    "addressLocality": "【市区町村】",
    "addressRegion": "【都道府県】",
    "postalCode": "【郵便番号】",
    "addressCountry": "JP"
  }}
}}
</script>"""

    article_jsonld = f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title[:110] if title else '記事タイトル'}",
  "description": "{meta_desc[:160] if meta_desc else '記事の要約160字以内'}",
  "image": [
    "{site_url.rstrip('/')}/images/featured-1x1.jpg",
    "{site_url.rstrip('/')}/images/featured-4x3.jpg",
    "{site_url.rstrip('/')}/images/featured-16x9.jpg"
  ],
  "datePublished": "{dates.get('published', today)[:10] if dates.get('published') else today}",
  "dateModified": "{dates.get('modified', today)[:10] if dates.get('modified') else today}",
  "author": {{
    "@type": "Person",
    "name": "{author.get('name', '【著者名】')}",
    "url": "{author.get('url', site_url.rstrip('/') + '/about/author')}"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "{domain}",
    "logo": {{
      "@type": "ImageObject",
      "url": "{site_url.rstrip('/')}/logo.png"
    }}
  }},
  "mainEntityOfPage": {{
    "@type": "WebPage",
    "@id": "{site_url}"
  }}
}}
</script>"""

    faq_jsonld = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "【質問1: ユーザーの検索クエリそのまま、50字以内】",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "【回答1: 定義＋根拠＋実例、150-300字、具体数値を含める】"
      }
    },
    {
      "@type": "Question",
      "name": "【質問2】",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "【回答2】"
      }
    },
    {
      "@type": "Question",
      "name": "【質問3】",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "【回答3】"
      }
    }
  ]
}
</script>"""

    return {
        "quick_wins": quick_wins,
        "strategic": strategic,
        "technical_debt": technical_debt,
        "content_strategy": content_strategy,
        "competitor_informed": competitor_informed,
        "measurement_plan": measurement_plan,
        "llms_txt_template": llms_txt,
        "organization_jsonld": org_jsonld,
        "article_jsonld": article_jsonld,
        "faq_jsonld": faq_jsonld,
    }


def generate_test_queries_python(
    site_url: str, keywords: list[str], site_title: str,
) -> dict:
    """商談用テストクエリをルールベースで生成。"""
    kw = keywords[0] if keywords else site_title or site_url
    domain = site_url.split("//")[-1].split("/")[0] if "//" in site_url else site_url

    queries = [
        {
            "platform": "ChatGPT",
            "query": f"{kw}について教えてください",
            "expected_if_cited": f"{domain}の情報が引用される",
            "reason_if_not": "定義文・Answer-first構造が不足している可能性",
        },
        {
            "platform": "ChatGPT",
            "query": f"{kw} おすすめ 比較",
            "expected_if_cited": f"{domain}の比較情報が引用される",
            "reason_if_not": "比較表・リスト構造が不足、または競合サイトの方が情報密度が高い",
        },
        {
            "platform": "Perplexity",
            "query": f"{kw}の選び方は？",
            "expected_if_cited": f"{domain}の選び方ガイドが引用される",
            "reason_if_not": "FAQ構造やHowTo構造化データが未実装の可能性",
        },
        {
            "platform": "Perplexity",
            "query": f"{kw} メリット デメリット",
            "expected_if_cited": f"{domain}のメリデメ情報が引用される",
            "reason_if_not": "メリット/デメリットの明確なリスト構造がない可能性",
        },
        {
            "platform": "Google AI Overview",
            "query": f"{kw}とは",
            "expected_if_cited": f"{domain}の定義文がAI Overviewに表示される",
            "reason_if_not": "「〇〇とは△△です」型の定義文がページ冒頭にない可能性",
        },
    ]

    return {
        "queries": queries,
        "claude_self_eval": {
            "would_recommend": False,
            "reason": "Python分析のみのため自己評価は省略。Claude Codeの@aio-diagnosticエージェントで詳細な定性評価が可能です。",
        },
    }
