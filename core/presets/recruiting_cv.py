"""採用ページのCV（面接応募）転換診断モジュール

10要素 × 10点 = 100点満点で応募率を阻害する要因を診断し、
クライアント提出用の具体的改善案を生成する。
"""

import re
from core.scorer import grade_from_score


# 業界ベンチマーク（採用ページの応募完了率 %）
CV_BENCHMARK = {
    "industry_avg_low": 1.5,
    "industry_avg_high": 3.0,
    "best_practice": 6.0,
    "top_class": 10.0,
}


def analyze_cv(structure: dict, all_scores: dict, pagespeed: dict, raw_html: str = "") -> dict:
    """採用ページのCV阻害要因を10軸で診断。"""
    content = structure.get("content_text", "") or ""
    raw_html = raw_html or structure.get("_raw_html", "") or structure.get("raw_html", "") or ""
    raw_lower = raw_html.lower()

    factors: list[dict] = []

    # 1: CTA可視性
    apply_kws = ["応募する", "エントリー", "今すぐ応募", "応募はこちら", "応募フォーム"]
    casual_kws = ["カジュアル面談", "話を聞く", "気軽に相談"]
    apply_count = sum(content.count(k) for k in apply_kws)
    casual_count = sum(content.count(k) for k in casual_kws)
    has_sticky = ("position:fixed" in raw_lower or "position: fixed" in raw_lower)

    s = 0
    if apply_count >= 3: s += 4
    elif apply_count >= 2: s += 3
    elif apply_count >= 1: s += 2
    if has_sticky and apply_count > 0: s += 3
    if casual_count >= 1: s += 2
    if apply_count >= 1: s += 1
    factors.append({
        "id": "cv1_cta_visibility", "label": "CTA可視性・配置",
        "score": min(s, 10), "max": 10,
        "current": "応募CTA" + str(apply_count) + "箇所 / カジュアル" + str(casual_count) + "箇所 / 固定CTA:" + ("有" if has_sticky else "無"),
        "ideal": "FV内＋本文末＋固定追従の3箇所以上＋カジュアル面談動線併設",
        "cv_impact": "CTA1→3箇所で応募率+25〜40%（HubSpot）",
        "issue": "応募ボタンが見つけにくく、離脱時に追従しない" if s < 6 else "良好",
    })

    # 2: CTAコピー
    low_friction = ["30秒で", "1分で", "簡単", "履歴書不要", "選考なし", "面談から", "オンライン面談", "服装自由"]
    fc = sum(1 for p in low_friction if p in content)
    has_apply_link = bool(re.search(r'href="[^"]*(apply|entry|form|recruit)', raw_lower))
    s = 0
    if fc >= 4: s += 6
    elif fc >= 2: s += 4
    elif fc >= 1: s += 2
    if has_apply_link: s += 4
    factors.append({
        "id": "cv2_cta_copy", "label": "CTAコピーの具体性",
        "score": min(s, 10), "max": 10,
        "current": "摩擦低減フレーズ " + str(fc) + "/8種 / 応募リンク:" + ("有" if has_apply_link else "無"),
        "ideal": "「30秒で完了」「履歴書不要」など心理的負担を下げる文言",
        "cv_impact": "「応募する」→「30秒で応募完了」でCTR+90%（VWO）",
        "issue": "「応募する」のみで具体性に欠ける" if s < 6 else "効果的",
    })

    # 3: フォーム摩擦
    inputs = len(re.findall(r"<input[^>]+type=\"(?!hidden|submit|button)", raw_lower))
    selects = raw_lower.count("<select")
    textareas = raw_lower.count("<textarea")
    fields = inputs + selects + textareas
    has_step = ("ステップ" in content) or ("step" in raw_lower and "1/" in content)
    has_oauth = ("linkedin" in raw_lower or "google" in raw_lower) and ("login" in raw_lower or "sign" in raw_lower)
    if fields == 0: s = 4
    elif fields <= 5: s = 8
    elif fields <= 8: s = 6
    elif fields <= 12: s = 4
    else: s = 2
    if has_step: s += 1
    if has_oauth: s += 1
    factors.append({
        "id": "cv3_form_friction", "label": "応募フォーム摩擦",
        "score": min(s, 10), "max": 10,
        "current": "フォーム項目 " + str(fields) + "個 / ステップ表示:" + ("有" if has_step else "無") + " / SNS認証:" + ("有" if has_oauth else "無"),
        "ideal": "必須5項目以下＋ステップ表示＋LinkedIn/Google認証",
        "cv_impact": "11→4項目でCV+120%（HubSpot）",
        "issue": "フォーム項目が多すぎる" if s < 6 else "許容範囲",
    })

    # 4: カジュアル面談
    casual_phr = ["カジュアル面談", "情報交換", "話を聞きに", "選考なし", "選考前面談", "1on1", "オフィス見学"]
    cd = sum(1 for p in casual_phr if p in content)
    has_cal = bool(re.search(r"(calendly|timerex|spir|youcanbookme|saleshub)", raw_lower))
    s = 0
    if cd >= 3: s += 6
    elif cd >= 2: s += 4
    elif cd >= 1: s += 2
    if has_cal: s += 4
    factors.append({
        "id": "cv4_low_commit", "label": "カジュアル面談導線",
        "score": min(s, 10), "max": 10,
        "current": "カジュアル面談シグナル " + str(cd) + "/7種 / 予約リンク:" + ("有" if has_cal else "無"),
        "ideal": "選考前カジュアル面談明示＋Calendly等で即予約可",
        "cv_impact": "母集団形成数2-3倍（Wantedly事例）",
        "issue": "本応募しかなく検討層を取りこぼし" if s < 5 else "良好",
    })

    # 5: 給与透明性
    has_range = bool(re.search(r"\d{2,4}\s*万円?\s*[-〜~‐–]\s*\d{2,4}\s*万", content))
    has_min = bool(re.search(r"(月給|年収|想定年収|基本給)\s*\d{2,4}\s*万", content))
    has_overtime = "残業" in content
    has_bonus = ("賞与" in content) or ("ボーナス" in content) or ("インセンティブ" in content)
    s = 0
    if has_range: s += 5
    elif has_min: s += 3
    if has_overtime: s += 2
    if has_bonus: s += 3
    factors.append({
        "id": "cv5_salary", "label": "給与・条件の透明性",
        "score": min(s, 10), "max": 10,
        "current": "レンジ:" + ("有" if has_range else "無") + " / 残業:" + ("有" if has_overtime else "無") + " / 賞与:" + ("有" if has_bonus else "無"),
        "ideal": "年収レンジ＋モデル年収＋賞与＋残業実績を明示",
        "cv_impact": "給与開示で応募率+30%、ミスマッチ-40%（LinkedIn）",
        "issue": "「応相談」のみで判断材料不足" if s < 6 else "確保",
    })

    # 6: 社員ボイス
    voice_kws = ["社員の声", "社員インタビュー", "メンバー紹介", "1日のスケジュール", "活躍するメンバー", "先輩社員"]
    vc = sum(1 for k in voice_kws if k in content)
    img_count = raw_lower.count("<img")
    has_video = ("youtube.com/embed" in raw_lower) or ("<video" in raw_lower)
    s = 0
    if vc >= 3: s += 5
    elif vc >= 1: s += 3
    if img_count >= 10: s += 3
    elif img_count >= 5: s += 2
    if has_video: s += 2
    factors.append({
        "id": "cv6_voice", "label": "社員リアルボイス",
        "score": min(s, 10), "max": 10,
        "current": "社員紹介 " + str(vc) + "種 / 画像 " + str(img_count) + "枚 / 動画:" + ("有" if has_video else "無"),
        "ideal": "顔写真付きインタビュー3名以上＋オフィス写真10枚＋動画",
        "cv_impact": "社員写真+インタビューで応募率+45%（Glassdoor）",
        "issue": "社員の顔・声が見えず入社後イメージが湧かない" if s < 6 else "十分",
    })

    # 7: 選考フロー
    flow_kws = ["選考フロー", "選考プロセス", "選考の流れ", "STEP", "面接回数", "内定までの流れ"]
    fs = sum(1 for k in flow_kws if k in content)
    has_dur = bool(re.search(r"(\d+\s*週間|\d+\s*日|\d+\s*ヶ月)", content))
    has_step_count = bool(re.search(r"(一次|二次|最終|1次|2次|3次)\s*面接", content))
    s = 0
    if fs >= 2: s += 5
    elif fs >= 1: s += 3
    if has_dur: s += 3
    if has_step_count: s += 2
    factors.append({
        "id": "cv7_flow", "label": "選考フロー可視化",
        "score": min(s, 10), "max": 10,
        "current": "選考フロー " + str(fs) + "種 / 期間明記:" + ("有" if has_dur else "無") + " / 面接回数:" + ("有" if has_step_count else "無"),
        "ideal": "STEP1-5図解＋各STEP所要時間＋内定までの平均日数明記",
        "cv_impact": "選考フロー可視化で応募率+22%（DODA）",
        "issue": "選考プロセス不透明で求職者が躊躇" if s < 6 else "可視化済み",
    })

    # 8: モバイル
    has_viewport = "viewport" in raw_lower and "device-width" in raw_lower
    has_resp = ("@media" in raw_lower) or ("responsive" in raw_lower) or ("flex" in raw_lower)
    has_touch = bool(re.search(r"min-height:\s*4[4-9]px|height:\s*[5-9]\dpx", raw_lower))
    mps = pagespeed.get("mobile", {}).get("score", 0) if isinstance(pagespeed, dict) else 0
    s = 0
    if has_viewport: s += 2
    if has_resp: s += 2
    if has_touch: s += 2
    if mps >= 80: s += 4
    elif mps >= 60: s += 3
    elif mps >= 40: s += 2
    factors.append({
        "id": "cv8_mobile", "label": "モバイル最適化",
        "score": min(s, 10), "max": 10,
        "current": "viewport:" + ("有" if has_viewport else "無") + " / レスポンシブ:" + ("有" if has_resp else "無") + " / モバイルPS:" + str(mps),
        "ideal": "viewport設定＋レスポンシブ＋タップ領域44px以上＋PS80点以上",
        "cv_impact": "採用流入の60-70%がモバイル。最適化遅れで応募率-50%",
        "issue": "モバイル操作性が悪く過半数が離脱" if s < 7 else "良好",
    })

    # 9: 速度
    dps = pagespeed.get("desktop", {}).get("score", 0) if isinstance(pagespeed, dict) else 0
    lcp = pagespeed.get("mobile", {}).get("lcp", 0) if isinstance(pagespeed, dict) else 0
    s = 0
    if dps >= 90: s += 5
    elif dps >= 70: s += 4
    elif dps >= 50: s += 2
    if lcp and lcp <= 2.5: s += 5
    elif lcp and lcp <= 4.0: s += 3
    elif lcp and lcp <= 6.0: s += 1
    if s == 0: s = 4
    factors.append({
        "id": "cv9_speed", "label": "ページ表示速度",
        "score": min(s, 10), "max": 10,
        "current": "DesktopPS:" + str(dps) + " / LCP:" + str(lcp) + "秒",
        "ideal": "PageSpeed90点以上＋LCP2.5秒以下",
        "cv_impact": "3秒で53%離脱（Google）／1秒短縮で応募率+7%",
        "issue": "表示が遅く応募意欲のあるユーザーが離脱" if s < 6 else "問題なし",
    })

    # 10: 信頼シグナル
    trust_kws = ["受賞", "認証", "Great Place to Work", "ベストカンパニー", "メディア掲載", "口コミ", "OpenWork"]
    tc = sum(1 for k in trust_kws if k in content)
    has_logo_grid = ("client" in raw_lower or "partner" in raw_lower or "導入" in content) and "img" in raw_lower
    cred_score = sum(all_scores.get(k, {}).get("score", 0) for k in ["6-2_company_stats", "6-3_awards", "6-4_media"])
    s = 0
    if tc >= 3: s += 4
    elif tc >= 1: s += 2
    if has_logo_grid: s += 2
    s += min(cred_score, 4)
    factors.append({
        "id": "cv10_trust", "label": "信頼シグナル",
        "score": min(s, 10), "max": 10,
        "current": "信頼KW " + str(tc) + "/7種 / クライアントロゴ:" + ("有" if has_logo_grid else "無") + " / 信頼カテゴリ加算:" + str(cred_score),
        "ideal": "Great Place to Work等の認証＋メディア掲載＋OpenWork口コミ",
        "cv_impact": "第三者評価で応募意向+38%（マイナビ）",
        "issue": "客観評価が見えず信用判断材料不足" if s < 6 else "あり",
    })

    # 集計
    cv_total = sum(f["score"] for f in factors)
    cv_max = sum(f["max"] for f in factors)

    base_rate = (CV_BENCHMARK["industry_avg_low"] + CV_BENCHMARK["industry_avg_high"]) / 2
    multiplier = cv_total / 50
    estimated = round(max(0.3, min(base_rate * multiplier, 12.0)), 2)

    weak = sorted(factors, key=lambda x: x["score"])[:5]
    uplift_pts = sum(f["max"] - f["score"] for f in weak)
    improved_total = min(cv_total + uplift_pts, 100)
    improved = round(max(0.5, min(base_rate * (improved_total / 50), 12.0)), 2)

    grade_result = grade_from_score(cv_total)
    grade = grade_result["grade"]

    if estimated >= CV_BENCHMARK["best_practice"]:
        bench_pos = "ベストプラクティス水準"
    elif estimated >= CV_BENCHMARK["industry_avg_high"]:
        bench_pos = "業界平均上位"
    elif estimated >= CV_BENCHMARK["industry_avg_low"]:
        bench_pos = "業界平均並み"
    else:
        bench_pos = "業界平均以下"

    return {
        "cv_total": cv_total,
        "cv_max": cv_max,
        "cv_grade": grade,
        "factors": factors,
        "weak_factors": weak,
        "estimated_cv_rate": estimated,
        "improved_cv_rate": improved,
        "potential_uplift_pct": round((improved - estimated) / max(estimated, 0.1) * 100, 0),
        "benchmark": CV_BENCHMARK,
        "benchmark_position": bench_pos,
        "improvement_ideas": _generate_ideas(factors),
    }


_IDEAS = {
    "cv1_cta_visibility": {
        "title": "CTA 3点配置＋スクロール追従ボタン実装",
        "actions": [
            "FV内に「応募する」ボタン配置（高彩度カラー #FF5722 等）",
            "各セクション末尾（仕事内容・給与・社員紹介後）にCTA再配置",
            "PC右下追従ボタン / SP画面下部固定バー（高さ56px）実装",
            "「応募する」と「カジュアル面談」を並列表示で選択肢提供",
        ],
        "code_sample": '<div style="position:fixed;bottom:0;left:0;right:0;background:#fff;padding:12px;display:flex;gap:8px;z-index:9999"><a href="/casual" style="flex:1;padding:14px;border:2px solid #FF5722;color:#FF5722;text-align:center;border-radius:8px">まず話を聞く</a><a href="/apply" style="flex:1;padding:14px;background:#FF5722;color:#fff;text-align:center;border-radius:8px">30秒で応募</a></div>',
        "expected_uplift": "+25〜40%",
        "cost": "工数3-5日",
    },
    "cv2_cta_copy": {
        "title": "CTAコピーの心理的ハードル低減",
        "actions": [
            "「応募する」→「30秒で応募完了」「履歴書不要で応募」",
            "サブコピー追加: 「平均5名/月が応募・カジュアル面談OK」",
            "緊急性訴求: 「今月の選考枠 残り3名」（実態に応じて）",
            "ベネフィット明示: 「応募から最短3日で内定」",
        ],
        "code_sample": '<a href="/apply"><span class="main">30秒で応募完了</span><span class="sub">📝 履歴書アップロードのみ・即日返信</span></a>',
        "expected_uplift": "+15〜90%",
        "cost": "工数0.5日 + ABテスト",
    },
    "cv3_form_friction": {
        "title": "応募フォームの徹底的な摩擦削減",
        "actions": [
            "必須項目を5個以下に削減（氏名/メール/電話/希望/自己PR）",
            "選考前ヒアリング項目はカジュアル面談時に移行",
            "ステップインジケーター表示（1/3 → 2/3 → 完了）",
            "LinkedIn/Google認証で氏名・メール自動入力",
            "履歴書PDFアップロード方式（手入力強制を排除）",
        ],
        "code_sample": '<form><div>STEP 1/2</div><input name="name" required placeholder="お名前"><input name="email" type="email" required><input name="phone" type="tel" required><input name="resume" type="file" accept=".pdf,.doc"><button>次へ</button></form>',
        "expected_uplift": "+50〜120%",
        "cost": "工数5-7日",
    },
    "cv4_low_commit": {
        "title": "カジュアル面談ファネル構築",
        "actions": [
            "「カジュアル面談」専用ページを新設",
            "Calendly/TimeRex等で即予約フォーマット導入",
            "面談内容を明示: 「会社説明30分＋質疑応答15分＋雑談15分」",
            "オンライン/オフィス来社/カフェ等の選択肢を提供",
            "事前提出書類なしを明記",
        ],
        "code_sample": '<a href="https://calendly.com/your-company/casual">☕ カジュアル面談を予約（30分・履歴書不要）</a>',
        "expected_uplift": "母集団2〜3倍 / 最終CV+30%",
        "cost": "工数2-3日 + Calendly有料月2,000円",
    },
    "cv5_salary": {
        "title": "給与・条件の完全透明化",
        "actions": [
            "想定年収レンジ記載: 「年収450万円〜800万円」",
            "モデル年収を経験別提示（3年目600万、5年目750万）",
            "賞与実績（前年度: 基本給4ヶ月分）明記",
            "残業実績（月平均15時間）を数値開示",
            "JobPosting JSON-LDのbaseSalary実装",
        ],
        "code_sample": '<dl><dt>想定年収</dt><dd>450万円〜800万円</dd><dt>モデル年収</dt><dd>3年目580万円 / 5年目720万円</dd><dt>賞与</dt><dd>年2回（前年度実績: 基本給4.2ヶ月分）</dd><dt>残業</dt><dd>月平均15時間</dd></dl>',
        "expected_uplift": "+30%応募率 / -40%ミスマッチ",
        "cost": "工数1-2日 + 経営判断",
    },
    "cv6_voice": {
        "title": "社員リアルボイスコンテンツ強化",
        "actions": [
            "社員インタビュー記事を3名以上追加（職種・年代・性別バランス）",
            "1日のスケジュール記事（タイムライン形式）",
            "オフィス写真ギャラリー10枚以上（執務/休憩/イベント）",
            "3分以内の社員紹介動画（YouTube埋め込み）",
            "VideoObject JSON-LDで構造化",
        ],
        "code_sample": '<article><img src="/staff/yamada.jpg"><h3>「3年で年収200万円アップ。挑戦を後押しする文化」</h3><p>エンジニア / 入社3年目 / 山田太郎</p><a href="/interview/yamada">全文を読む →</a></article>',
        "expected_uplift": "+45%応募率 / 滞在時間2倍",
        "cost": "工数10-15日 / 撮影+取材+編集",
    },
    "cv7_flow": {
        "title": "選考フローの完全可視化",
        "actions": [
            "選考ステップを図解（応募→書類→1次→2次→最終→内定）",
            "各STEPの所要日数を明記（書類選考3日／面接1週間以内）",
            "応募から内定までの平均日数を表示（21日）",
            "面接官の役職・顔写真・質問例を事前公開",
            "オンライン面接/対面どちらか選択可能",
        ],
        "code_sample": '<ol><li>STEP 1 応募 / 24時間以内に返信</li><li>STEP 2 書類選考 / 3営業日</li><li>STEP 3 1次面接（オンライン60分）</li><li>STEP 4 2次面接（対面90分）</li><li>STEP 5 最終面接（役員60分）</li><li>内定 平均21日</li></ol>',
        "expected_uplift": "+22%応募率",
        "cost": "工数1-2日",
    },
    "cv8_mobile": {
        "title": "モバイルUXの徹底改善",
        "actions": [
            "viewport設定確認（width=device-width, initial-scale=1）",
            "全CTAボタンのタップ領域を44px以上に拡大",
            "フォントサイズ16px以上（iOSズーム抑制）",
            "画像WebP化＋遅延読み込み",
            "モバイル専用の固定CTAバー実装",
        ],
        "code_sample": '<meta name="viewport" content="width=device-width,initial-scale=1"><style>.cta{min-height:48px;font-size:16px}@media(max-width:768px){body{padding-bottom:80px}.mobile-cta-bar{position:fixed;bottom:0}}</style>',
        "expected_uplift": "モバイルCV +50%",
        "cost": "工数5-7日",
    },
    "cv9_speed": {
        "title": "ページ表示速度の最適化",
        "actions": [
            "画像WebP/AVIF変換＋遅延読み込み（loading=\"lazy\"）",
            "LCP対象画像のpreload",
            "サードパーティJS（広告/解析）の遅延読み込み",
            "CDN導入（Cloudflare等）",
            "Critical CSSのインライン化",
        ],
        "code_sample": '<link rel="preload" as="image" href="/hero.webp"><img src="/hero.webp" fetchpriority="high"><img src="/staff.webp" loading="lazy"><script src="/analytics.js" defer></script>',
        "expected_uplift": "1秒短縮で+7%応募率",
        "cost": "工数3-5日 + CDN月額",
    },
    "cv10_trust": {
        "title": "第三者信頼シグナル集約セクション",
        "actions": [
            "受賞・認証ロゴをFV直下に集約（Great Place to Work等）",
            "OpenWork/Lighthouse等の口コミスコアを引用",
            "メディア掲載一覧（ロゴグリッド）",
            "従業員数・平均年齢・男女比・離職率などの数値開示",
            "クライアント企業ロゴグリッド（許諾済み）",
        ],
        "code_sample": '<section><h2>客観評価で見る当社</h2><div class="badges"><img src="/gptw-2025.png" alt="GPTW 2025"><img src="/openwork-4.2.png"><img src="/iso27001.png"></div><dl><dt>従業員数</dt><dd>248名</dd><dt>離職率</dt><dd>4.2%（業界平均15%）</dd><dt>平均勤続年数</dt><dd>7.8年</dd></dl></section>',
        "expected_uplift": "+38%応募意向",
        "cost": "工数2-3日（認証取得別途）",
    },
}


def _generate_ideas(factors: list) -> list:
    ideas = []
    for f in factors:
        if f["score"] >= 7:
            continue
        base = _IDEAS.get(f["id"])
        if not base:
            continue
        priority = "S" if f["score"] < 4 else ("A" if f["score"] < 6 else "B")
        ideas.append({
            "factor_id": f["id"],
            "factor_label": f["label"],
            "current_score": f["score"],
            "max_score": f["max"],
            "priority": priority,
            **base,
        })
    return ideas
