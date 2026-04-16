"""採用ページ診断プリセット — Google for Jobs / JobPosting / 求職者UX重視

6カテゴリ × 30項目 = 100点満点

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


# ------------------------------------------------------------------
# 採点ヘルパー
# ------------------------------------------------------------------

def _text_has_any(text: str, keywords: list) -> int:
    return sum(1 for k in keywords if k in text)


def _find_jobposting(jsonld_list: list) -> dict:
    """JSON-LDからJobPostingを抽出。"""
    for item in jsonld_list:
        if isinstance(item, dict):
            t = item.get("@type", "")
            if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                return item
            # @graphの中も探す
            graph = item.get("@graph", [])
            if isinstance(graph, list):
                for g in graph:
                    if isinstance(g, dict) and g.get("@type") == "JobPosting":
                        return g
    return {}


# ------------------------------------------------------------------
# カテゴリ1: Google for Jobs対応（20点）
# ------------------------------------------------------------------

def _score_jobposting(structure: dict) -> dict:
    """Google for Jobs対応を採点。"""
    jsonld_list = structure.get("jsonld", [])
    jp = _find_jobposting(jsonld_list)
    scores: dict = {}

    # 1-1: JobPosting JSON-LDの有無（5点）
    if jp:
        scores["1-1_jobposting_exists"] = {
            "score": 5, "max": 5,
            "reason": "JobPosting JSON-LD検出 — Google for Jobs対応済",
            "method": "JSON-LD解析", "confidence": "高",
        }
    else:
        scores["1-1_jobposting_exists"] = {
            "score": 0, "max": 5,
            "reason": "JobPosting JSON-LD未設置 — Google for Jobsに表示されない",
            "method": "JSON-LD解析", "confidence": "高",
        }

    # 1-2: JobPosting必須項目の完全性（5点）
    required_fields = ["title", "description", "datePosted",
                       "hiringOrganization", "jobLocation"]
    if jp:
        filled = sum(1 for f in required_fields if jp.get(f))
        score = round(filled / len(required_fields) * 5)
        missing = [f for f in required_fields if not jp.get(f)]
        reason = f"必須{filled}/{len(required_fields)}項目" + (
            f"、欠落: {', '.join(missing)}" if missing else " — 完全"
        )
    else:
        score = 0
        reason = "JobPosting未設置のため必須項目判定不可"
    scores["1-2_required_fields"] = {
        "score": score, "max": 5, "reason": reason,
        "method": "JSON-LD解析", "confidence": "高",
    }

    # 1-3: 推奨項目（baseSalary, employmentType, qualifications, validThrough）（4点）
    recommended = ["baseSalary", "employmentType", "qualifications",
                   "validThrough", "skills", "responsibilities"]
    if jp:
        filled = sum(1 for f in recommended if jp.get(f))
        score = min(4, round(filled / len(recommended) * 4))
        reason = f"推奨{filled}/{len(recommended)}項目検出"
    else:
        score = 0
        reason = "JobPosting未設置"
    scores["1-3_recommended_fields"] = {
        "score": score, "max": 4, "reason": reason,
        "method": "JSON-LD解析", "confidence": "高",
    }

    # 1-4: baseSalary（給与情報の構造化）（3点）
    if jp and jp.get("baseSalary"):
        scores["1-4_base_salary"] = {
            "score": 3, "max": 3,
            "reason": "baseSalary定義あり — Googleで給与帯が表示可能",
            "method": "JSON-LD解析", "confidence": "高",
        }
    else:
        scores["1-4_base_salary"] = {
            "score": 0, "max": 3,
            "reason": "baseSalary未定義 — 求職者の離脱要因",
            "method": "JSON-LD解析", "confidence": "高",
        }

    # 1-5: directApply / url（応募導線の構造化）（3点）
    if jp and (jp.get("directApply") is not None or jp.get("url")):
        scores["1-5_direct_apply"] = {
            "score": 3, "max": 3,
            "reason": "directApply/url指定あり — Google経由応募が可能",
            "method": "JSON-LD解析", "confidence": "高",
        }
    else:
        scores["1-5_direct_apply"] = {
            "score": 0, "max": 3,
            "reason": "directApply/url未指定",
            "method": "JSON-LD解析", "confidence": "中",
        }

    return scores


# ------------------------------------------------------------------
# カテゴリ2: 求人情報の具体性（20点）
# ------------------------------------------------------------------

def _score_job_specificity(structure: dict) -> dict:
    text = structure.get("content_text", "")
    scores: dict = {}

    # 2-1: 仕事内容の具体性（5点）— 業務内容/タスク/一日のスケジュール等
    job_detail_kws = ["業務内容", "仕事内容", "担当業務", "1日の流れ", "一日の流れ",
                      "タスク", "プロジェクト", "スケジュール", "役割"]
    job_detail_count = _text_has_any(text, job_detail_kws)
    has_list = structure.get("list_count", 0) >= 2
    if job_detail_count >= 3 and has_list:
        scores["2-1_job_content"] = {"score": 5, "max": 5,
            "reason": f"業務内容キーワード{job_detail_count}件 + 箇条書き構造",
            "method": "テキスト解析", "confidence": "高"}
    elif job_detail_count >= 1:
        scores["2-1_job_content"] = {"score": 2, "max": 5,
            "reason": f"業務内容の記述あり（{job_detail_count}件）がやや抽象的",
            "method": "テキスト解析", "confidence": "中"}
    else:
        scores["2-1_job_content"] = {"score": 0, "max": 5,
            "reason": "仕事内容の具体的記述が見当たらない",
            "method": "テキスト解析", "confidence": "高"}

    # 2-2: 給与情報（4点）
    salary_patterns = [
        r"月給\s*\d+", r"年収\s*\d+", r"時給\s*\d+",
        r"\d+万円", r"\d+,\d{3}円", r"〜\s*\d+万",
    ]
    salary_count = sum(len(re.findall(p, text)) for p in salary_patterns)
    salary_kws = _text_has_any(text, ["月給", "年収", "時給", "賞与", "ボーナス", "昇給"])
    if salary_count >= 2 and salary_kws >= 2:
        scores["2-2_salary"] = {"score": 4, "max": 4,
            "reason": f"給与の具体値{salary_count}箇所 + 関連情報{salary_kws}項目",
            "method": "正規表現", "confidence": "高"}
    elif salary_count >= 1 or salary_kws >= 2:
        scores["2-2_salary"] = {"score": 2, "max": 4,
            "reason": "給与情報はあるが具体性不足",
            "method": "正規表現", "confidence": "中"}
    else:
        scores["2-2_salary"] = {"score": 0, "max": 4,
            "reason": "給与情報が明示されていない — 応募率の大きな阻害要因",
            "method": "正規表現", "confidence": "高"}

    # 2-3: 勤務地（3点）
    location_kws = ["勤務地", "所在地", "本社", "支社", "オフィス",
                    "東京都", "大阪府", "神奈川", "リモート", "在宅"]
    loc_count = _text_has_any(text, location_kws)
    if loc_count >= 3:
        scores["2-3_location"] = {"score": 3, "max": 3,
            "reason": f"勤務地情報{loc_count}件 — 明確",
            "method": "キーワード検出", "confidence": "高"}
    elif loc_count >= 1:
        scores["2-3_location"] = {"score": 1.5, "max": 3,
            "reason": "勤務地の記載はあるが詳細不足",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["2-3_location"] = {"score": 0, "max": 3,
            "reason": "勤務地が明記されていない",
            "method": "キーワード検出", "confidence": "中"}

    # 2-4: スキル要件（4点）— 必須/歓迎スキル
    skill_kws = ["必須スキル", "必須条件", "応募資格", "応募条件",
                 "歓迎スキル", "歓迎条件", "求める人物像", "求めるスキル",
                 "経験者", "未経験"]
    skill_count = _text_has_any(text, skill_kws)
    must_want_separated = ("必須" in text) and ("歓迎" in text)
    if skill_count >= 3 and must_want_separated:
        scores["2-4_skill_requirements"] = {"score": 4, "max": 4,
            "reason": f"必須/歓迎の分離明確 + キーワード{skill_count}件",
            "method": "キーワード検出", "confidence": "高"}
    elif skill_count >= 2:
        scores["2-4_skill_requirements"] = {"score": 2, "max": 4,
            "reason": "応募条件はあるが必須/歓迎の分離が不明確",
            "method": "キーワード検出", "confidence": "中"}
    elif skill_count >= 1:
        scores["2-4_skill_requirements"] = {"score": 1, "max": 4,
            "reason": "応募条件の記述が最小限",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["2-4_skill_requirements"] = {"score": 0, "max": 4,
            "reason": "応募資格・スキル要件の記述なし",
            "method": "キーワード検出", "confidence": "高"}

    # 2-5: キャリアパス（4点）
    career_kws = ["キャリアパス", "キャリアステップ", "昇格", "昇進",
                  "ロールモデル", "成長", "将来像", "次のステージ",
                  "評価制度", "等級"]
    career_count = _text_has_any(text, career_kws)
    if career_count >= 3:
        scores["2-5_career_path"] = {"score": 4, "max": 4,
            "reason": f"キャリア情報{career_count}件 — 成長イメージが描ける",
            "method": "キーワード検出", "confidence": "高"}
    elif career_count >= 1:
        scores["2-5_career_path"] = {"score": 2, "max": 4,
            "reason": "キャリア関連の言及はあるが具体性不足",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["2-5_career_path"] = {"score": 0, "max": 4,
            "reason": "キャリアパスの記述なし — 成長志向の候補者を逃す",
            "method": "キーワード検出", "confidence": "高"}

    return scores


# ------------------------------------------------------------------
# カテゴリ3: 企業カルチャー・魅力（15点）
# ------------------------------------------------------------------

def _score_culture(structure: dict, raw_html: str = "") -> dict:
    text = structure.get("content_text", "")
    scores: dict = {}

    # 3-1: 社員紹介・インタビュー（4点）
    staff_kws = ["社員紹介", "社員インタビュー", "社員の声", "メンバー紹介",
                 "社員メッセージ", "入社ストーリー", "マネージャーインタビュー"]
    staff_count = _text_has_any(text, staff_kws)
    if staff_count >= 2:
        scores["3-1_staff_voices"] = {"score": 4, "max": 4,
            "reason": f"社員紹介要素{staff_count}件検出",
            "method": "キーワード検出", "confidence": "高"}
    elif staff_count >= 1:
        scores["3-1_staff_voices"] = {"score": 2, "max": 4,
            "reason": "社員紹介はあるが最小限",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["3-1_staff_voices"] = {"score": 0, "max": 4,
            "reason": "社員紹介・インタビューなし",
            "method": "キーワード検出", "confidence": "高"}

    # 3-2: 動画コンテンツ（3点）
    video_markers = 0
    if raw_html:
        video_markers += len(re.findall(r'<(?:video|iframe)[^>]*(?:youtube|vimeo)', raw_html, re.IGNORECASE))
        video_markers += len(re.findall(r'<video[\s>]', raw_html, re.IGNORECASE))
    if video_markers >= 2:
        scores["3-2_video_content"] = {"score": 3, "max": 3,
            "reason": f"動画コンテンツ{video_markers}件 — 滞在時間・理解促進",
            "method": "HTML解析", "confidence": "高"}
    elif video_markers >= 1:
        scores["3-2_video_content"] = {"score": 1.5, "max": 3,
            "reason": "動画1件あり、より多くの動画化が望ましい",
            "method": "HTML解析", "confidence": "高"}
    else:
        scores["3-2_video_content"] = {"score": 0, "max": 3,
            "reason": "動画コンテンツなし",
            "method": "HTML解析", "confidence": "高"}

    # 3-3: オフィス・職場環境（2点）— 画像数+キーワード
    office_kws = ["オフィス", "職場", "ワークスペース", "フロア", "会議室", "執務"]
    office_count = _text_has_any(text, office_kws)
    image_count = 0
    if raw_html:
        image_count = len(re.findall(r'<img\s', raw_html, re.IGNORECASE))
    if office_count >= 2 and image_count >= 5:
        scores["3-3_workplace"] = {"score": 2, "max": 2,
            "reason": f"オフィス言及{office_count}件 + 画像{image_count}点",
            "method": "テキスト+HTML", "confidence": "高"}
    elif office_count >= 1 or image_count >= 3:
        scores["3-3_workplace"] = {"score": 1, "max": 2,
            "reason": "職場イメージは部分的",
            "method": "テキスト+HTML", "confidence": "中"}
    else:
        scores["3-3_workplace"] = {"score": 0, "max": 2,
            "reason": "職場環境の可視化なし",
            "method": "テキスト+HTML", "confidence": "中"}

    # 3-4: MVV（ミッション・ビジョン・バリュー）（3点）
    mvv_kws = ["ミッション", "ビジョン", "バリュー", "MVV",
               "企業理念", "経営理念", "私たちの使命", "Vision", "Mission", "Values"]
    mvv_count = _text_has_any(text, mvv_kws)
    if mvv_count >= 3:
        scores["3-4_mvv"] = {"score": 3, "max": 3,
            "reason": f"MVV関連表記{mvv_count}件 — 価値観が明確",
            "method": "キーワード検出", "confidence": "高"}
    elif mvv_count >= 1:
        scores["3-4_mvv"] = {"score": 1.5, "max": 3,
            "reason": "MVVの言及はあるが浅い",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["3-4_mvv"] = {"score": 0, "max": 3,
            "reason": "MVV・企業理念の明示なし",
            "method": "キーワード検出", "confidence": "高"}

    # 3-5: 多様性・DEI（3点）
    dei_kws = ["ダイバーシティ", "多様性", "DEI", "D&I", "インクルージョン",
               "女性活躍", "育児", "育休", "産休", "時短勤務",
               "LGBTQ", "障がい者", "外国籍", "年齢問わず"]
    dei_count = _text_has_any(text, dei_kws)
    if dei_count >= 3:
        scores["3-5_diversity"] = {"score": 3, "max": 3,
            "reason": f"多様性・DEI関連{dei_count}件",
            "method": "キーワード検出", "confidence": "高"}
    elif dei_count >= 1:
        scores["3-5_diversity"] = {"score": 1.5, "max": 3,
            "reason": "多様性への言及はあるが体系的でない",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["3-5_diversity"] = {"score": 0, "max": 3,
            "reason": "多様性・DEIの明示なし",
            "method": "キーワード検出", "confidence": "中"}

    return scores


# ------------------------------------------------------------------
# カテゴリ4: 労働条件・福利厚生（15点）
# ------------------------------------------------------------------

def _score_conditions(structure: dict) -> dict:
    text = structure.get("content_text", "")
    scores: dict = {}

    # 4-1: 勤務時間・休日（3点）
    time_kws = ["勤務時間", "就業時間", "定時", "フレックス", "コアタイム",
                "休日", "休暇", "年間休日", "土日祝"]
    time_count = _text_has_any(text, time_kws)
    if time_count >= 4:
        scores["4-1_working_hours"] = {"score": 3, "max": 3,
            "reason": f"勤務時間・休日情報{time_count}件",
            "method": "キーワード検出", "confidence": "高"}
    elif time_count >= 2:
        scores["4-1_working_hours"] = {"score": 1.5, "max": 3,
            "reason": "勤務時間の記載あり、休日情報が不足",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["4-1_working_hours"] = {"score": 0, "max": 3,
            "reason": "勤務時間・休日の明示なし",
            "method": "キーワード検出", "confidence": "高"}

    # 4-2: リモートワーク / ハイブリッド（3点）
    remote_kws = ["リモート", "テレワーク", "在宅勤務", "フルリモート",
                  "ハイブリッド", "出社"]
    remote_count = _text_has_any(text, remote_kws)
    if remote_count >= 2:
        scores["4-2_remote_work"] = {"score": 3, "max": 3,
            "reason": "リモート/出社条件が明記",
            "method": "キーワード検出", "confidence": "高"}
    elif remote_count >= 1:
        scores["4-2_remote_work"] = {"score": 1.5, "max": 3,
            "reason": "リモート関連の言及はあるが詳細不足",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["4-2_remote_work"] = {"score": 0, "max": 3,
            "reason": "働き方（リモート/出社）の記述なし",
            "method": "キーワード検出", "confidence": "中"}

    # 4-3: 福利厚生（3点）
    benefit_kws = ["福利厚生", "社会保険", "各種保険", "社宅", "家賃補助",
                   "交通費", "退職金", "確定拠出年金", "持株会",
                   "健康診断", "人間ドック", "社員食堂"]
    benefit_count = _text_has_any(text, benefit_kws)
    if benefit_count >= 5:
        scores["4-3_benefits"] = {"score": 3, "max": 3,
            "reason": f"福利厚生{benefit_count}項目 — 充実",
            "method": "キーワード検出", "confidence": "高"}
    elif benefit_count >= 2:
        scores["4-3_benefits"] = {"score": 1.5, "max": 3,
            "reason": f"福利厚生{benefit_count}項目 — 標準的",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["4-3_benefits"] = {"score": 0, "max": 3,
            "reason": "福利厚生の記述が最小限",
            "method": "キーワード検出", "confidence": "高"}

    # 4-4: 研修・スキルアップ制度（3点）
    training_kws = ["研修", "教育制度", "勉強会", "資格取得支援", "書籍購入",
                    "カンファレンス", "社外学習", "Udemy", "オンライン学習",
                    "メンター", "OJT"]
    training_count = _text_has_any(text, training_kws)
    if training_count >= 3:
        scores["4-4_training"] = {"score": 3, "max": 3,
            "reason": f"研修制度{training_count}項目",
            "method": "キーワード検出", "confidence": "高"}
    elif training_count >= 1:
        scores["4-4_training"] = {"score": 1.5, "max": 3,
            "reason": "研修制度の言及はあるが具体性不足",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["4-4_training"] = {"score": 0, "max": 3,
            "reason": "研修・学習支援の記述なし",
            "method": "キーワード検出", "confidence": "高"}

    # 4-5: 数値で語る制度の具体性（3点）
    # 例: 「有給取得率90%」「育休取得率100%」「残業月10時間以内」
    benefit_number_patterns = [
        r"取得率\s*\d+", r"月\s*\d+時間", r"年間\s*\d+日",
        r"\d+時間以内", r"\d+日以上", r"\d+%",
    ]
    num_count = sum(len(re.findall(p, text)) for p in benefit_number_patterns)
    if num_count >= 4:
        scores["4-5_concrete_numbers"] = {"score": 3, "max": 3,
            "reason": f"具体数値{num_count}箇所 — 説得力が高い",
            "method": "正規表現", "confidence": "高"}
    elif num_count >= 1:
        scores["4-5_concrete_numbers"] = {"score": 1, "max": 3,
            "reason": f"数値データ{num_count}箇所 — 補強余地あり",
            "method": "正規表現", "confidence": "中"}
    else:
        scores["4-5_concrete_numbers"] = {"score": 0, "max": 3,
            "reason": "労働条件の具体数値なし — 抽象的で信頼度低",
            "method": "正規表現", "confidence": "高"}

    return scores


# ------------------------------------------------------------------
# カテゴリ5: 応募UX（15点）
# ------------------------------------------------------------------

def _score_apply_ux(structure: dict, raw_html: str = "") -> dict:
    text = structure.get("content_text", "")
    scores: dict = {}

    # 5-1: CTAの明確性（4点）
    cta_kws = ["応募する", "エントリー", "Apply", "応募フォーム",
               "面談を申し込む", "カジュアル面談", "まずは話を聞く"]
    cta_count = _text_has_any(text, cta_kws)
    # ボタン要素数
    button_count = 0
    if raw_html:
        button_count = len(re.findall(r'<(?:button|a)[^>]*(?:btn|button)', raw_html, re.IGNORECASE))
    if cta_count >= 3 and button_count >= 2:
        scores["5-1_cta_clarity"] = {"score": 4, "max": 4,
            "reason": f"CTA文言{cta_count}件 + ボタン要素{button_count}件",
            "method": "テキスト+HTML", "confidence": "高"}
    elif cta_count >= 1:
        scores["5-1_cta_clarity"] = {"score": 2, "max": 4,
            "reason": "CTAはあるが目立つ配置でない可能性",
            "method": "テキスト+HTML", "confidence": "中"}
    else:
        scores["5-1_cta_clarity"] = {"score": 0, "max": 4,
            "reason": "明確なCTAが見当たらない — 応募率が低い",
            "method": "テキスト+HTML", "confidence": "高"}

    # 5-2: 選考フロー（3点）
    flow_kws = ["選考フロー", "選考プロセス", "面接", "書類選考",
                "一次面接", "二次面接", "最終面接", "オファー面談",
                "内定", "STEP"]
    flow_count = _text_has_any(text, flow_kws)
    if flow_count >= 4:
        scores["5-2_selection_flow"] = {"score": 3, "max": 3,
            "reason": f"選考フロー{flow_count}要素 — 透明性高い",
            "method": "キーワード検出", "confidence": "高"}
    elif flow_count >= 2:
        scores["5-2_selection_flow"] = {"score": 1.5, "max": 3,
            "reason": "選考フローはあるが詳細不足",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["5-2_selection_flow"] = {"score": 0, "max": 3,
            "reason": "選考フローが不明瞭",
            "method": "キーワード検出", "confidence": "高"}

    # 5-3: 連絡先・問い合わせ（2点）
    contact_kws = ["問い合わせ", "お問合せ", "連絡先", "採用担当",
                   "人事部", "hr@", "recruit@"]
    contact_count = _text_has_any(text, contact_kws)
    if contact_count >= 2:
        scores["5-3_contact"] = {"score": 2, "max": 2,
            "reason": "連絡先・問い合わせ窓口明確",
            "method": "キーワード検出", "confidence": "高"}
    elif contact_count >= 1:
        scores["5-3_contact"] = {"score": 1, "max": 2,
            "reason": "問い合わせ先は部分的",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["5-3_contact"] = {"score": 0, "max": 2,
            "reason": "問い合わせ先が不明",
            "method": "キーワード検出", "confidence": "中"}

    # 5-4: モバイル対応（3点）
    if structure.get("viewport"):
        scores["5-4_mobile"] = {"score": 3, "max": 3,
            "reason": "viewport meta設定あり — レスポンシブ対応",
            "method": "HTML解析", "confidence": "高"}
    else:
        scores["5-4_mobile"] = {"score": 0, "max": 3,
            "reason": "viewport meta未設定 — スマホ閲覧で崩れ",
            "method": "HTML解析", "confidence": "高"}

    # 5-5: カジュアル面談など低コミット選択肢（3点）
    casual_kws = ["カジュアル面談", "会社説明会", "オフィス見学", "気軽に",
                  "まずは話", "お話しましょう", "オープン社内"]
    casual_count = _text_has_any(text, casual_kws)
    if casual_count >= 2:
        scores["5-5_low_commit_option"] = {"score": 3, "max": 3,
            "reason": f"低コミット選択肢{casual_count}件 — 応募ハードル下げている",
            "method": "キーワード検出", "confidence": "高"}
    elif casual_count >= 1:
        scores["5-5_low_commit_option"] = {"score": 1.5, "max": 3,
            "reason": "カジュアル面談の導線が部分的",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["5-5_low_commit_option"] = {"score": 0, "max": 3,
            "reason": "カジュアル面談など低コミット選択肢なし",
            "method": "キーワード検出", "confidence": "中"}

    return scores


# ------------------------------------------------------------------
# カテゴリ6: 信頼性・E-E-A-T（15点）
# ------------------------------------------------------------------

def _score_credibility(structure: dict) -> dict:
    text = structure.get("content_text", "")
    scores: dict = {}

    # 6-1: 代表メッセージ（3点）
    ceo_kws = ["代表メッセージ", "代表取締役", "CEO", "社長メッセージ",
               "代表挨拶", "創業者"]
    ceo_count = _text_has_any(text, ceo_kws)
    if ceo_count >= 2:
        scores["6-1_ceo_message"] = {"score": 3, "max": 3,
            "reason": "代表メッセージ確認",
            "method": "キーワード検出", "confidence": "高"}
    elif ceo_count >= 1:
        scores["6-1_ceo_message"] = {"score": 1.5, "max": 3,
            "reason": "代表関連の言及はあるが独立セクションなし",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["6-1_ceo_message"] = {"score": 0, "max": 3,
            "reason": "代表メッセージなし",
            "method": "キーワード検出", "confidence": "中"}

    # 6-2: 企業実績・数値（3点）
    num_patterns = [
        r"設立\s*\d{4}", r"創業\s*\d{4}", r"従業員\s*\d+",
        r"社員数\s*\d+", r"売上\s*\d+", r"導入\s*\d+",
        r"顧客\s*\d+", r"実績\s*\d+",
    ]
    num_count = sum(len(re.findall(p, text)) for p in num_patterns)
    if num_count >= 3:
        scores["6-2_company_stats"] = {"score": 3, "max": 3,
            "reason": f"企業の数値実績{num_count}件",
            "method": "正規表現", "confidence": "高"}
    elif num_count >= 1:
        scores["6-2_company_stats"] = {"score": 1.5, "max": 3,
            "reason": "企業実績の数値が一部",
            "method": "正規表現", "confidence": "中"}
    else:
        scores["6-2_company_stats"] = {"score": 0, "max": 3,
            "reason": "企業の数値実績が明示されていない",
            "method": "正規表現", "confidence": "高"}

    # 6-3: 受賞・認定（3点）
    award_kws = ["受賞", "表彰", "認定", "Best Workplaces", "働きがいのある会社",
                 "ホワイト企業", "くるみん", "えるぼし", "プラチナ",
                 "認証", "ISO", "プライバシーマーク"]
    award_count = _text_has_any(text, award_kws)
    if award_count >= 2:
        scores["6-3_awards"] = {"score": 3, "max": 3,
            "reason": f"受賞・認定{award_count}件",
            "method": "キーワード検出", "confidence": "高"}
    elif award_count >= 1:
        scores["6-3_awards"] = {"score": 1.5, "max": 3,
            "reason": "受賞・認定1件",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["6-3_awards"] = {"score": 0, "max": 3,
            "reason": "受賞・認定情報なし",
            "method": "キーワード検出", "confidence": "中"}

    # 6-4: メディア掲載・プレス（3点）
    media_kws = ["メディア掲載", "プレスリリース", "取材", "掲載実績",
                 "日経", "ITmedia", "TechCrunch", "ForbesJapan",
                 "出演", "寄稿"]
    media_count = _text_has_any(text, media_kws)
    if media_count >= 3:
        scores["6-4_media"] = {"score": 3, "max": 3,
            "reason": f"メディア関連{media_count}件",
            "method": "キーワード検出", "confidence": "高"}
    elif media_count >= 1:
        scores["6-4_media"] = {"score": 1.5, "max": 3,
            "reason": "メディア言及は部分的",
            "method": "キーワード検出", "confidence": "中"}
    else:
        scores["6-4_media"] = {"score": 0, "max": 3,
            "reason": "メディア掲載の明示なし",
            "method": "キーワード検出", "confidence": "中"}

    # 6-5: Organization JSON-LD（3点）
    has_org = any(
        (s.get("@type") == "Organization" or
         (isinstance(s.get("@type"), list) and "Organization" in s.get("@type", [])))
        for s in structure.get("jsonld", []) if isinstance(s, dict)
    )
    if has_org:
        scores["6-5_organization_jsonld"] = {"score": 3, "max": 3,
            "reason": "Organization JSON-LD検出",
            "method": "JSON-LD解析", "confidence": "高"}
    else:
        scores["6-5_organization_jsonld"] = {"score": 0, "max": 3,
            "reason": "Organization JSON-LD未設置",
            "method": "JSON-LD解析", "confidence": "高"}

    return scores


# ------------------------------------------------------------------
# メインスコアリング
# ------------------------------------------------------------------

def score_page(structure, robots, llms, pagespeed, sitemap):
    """採用ページとして評価。all_scores / categories / total を返す。"""
    raw_html = structure.get("_raw_html", "") or structure.get("raw_html", "") or ""

    scores: dict = {}
    scores.update(_score_jobposting(structure))
    scores.update(_score_job_specificity(structure))
    scores.update(_score_culture(structure, raw_html))
    scores.update(_score_conditions(structure))
    scores.update(_score_apply_ux(structure, raw_html))
    scores.update(_score_credibility(structure))

    # CV診断を実施し、結果をstructure経由で参照可能にしておく
    try:
        cv = analyze_cv(structure, scores, pagespeed, raw_html)
        structure["_cv_analysis"] = cv
    except Exception:
        pass

    # カテゴリ別集計
    categories: dict = {}
    for cat_key, cat_def in CATEGORY_DEFINITIONS.items():
        prefix = cat_key.split("_")[0] + "-"
        cat_scores = [s for k, s in scores.items() if k.startswith(prefix)]
        total_score = sum(s.get("score", 0) for s in cat_scores)
        categories[cat_key] = {
            "label": cat_def["label"],
            "score": round(total_score, 1),
            "max": cat_def["max"],
            "pct": round(total_score / cat_def["max"] * 100) if cat_def["max"] else 0,
        }

    # 総合
    total_score = sum(c["score"] for c in categories.values())
    grade_result = grade_from_score(round(total_score))

    total = {
        "total": round(total_score),
        "grade": grade_result["grade"],
        "label": grade_result["label"],
    }

    return scores, categories, total


# ------------------------------------------------------------------
# 改善提案
# ------------------------------------------------------------------

def generate_improvements(all_scores, structure, url, competitors=None, comparison=None):
    """採用ページ向け改善提案を生成。"""
    domain = url.split("//")[-1].split("/")[0] if "//" in url else url
    title = structure.get("title", "") or ""
    today = "2026-04-15"
    future_60 = "2026-06-14"

    quick_wins: list = []
    content_strategy: list = []
    technical_debt: list = []
    strategic: list = []

    low = {k for k, v in all_scores.items()
           if v.get("max", 0) > 0 and v.get("score", 0) / v["max"] < 0.5}

    # --- QW1: JobPosting JSON-LD ---
    if any(k.startswith("1-") for k in low):
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
    if "2-2_salary" in low:
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
    if "5-5_low_commit_option" in low:
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
                "日本のIT企業ではカジュアル面談を用意しているだけで、"
                "応募者数が1.5-2倍になる事例が多数あります。"
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
    if "5-2_selection_flow" in low:
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
    if "3-1_staff_voices" in low:
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
    if "4-5_concrete_numbers" in low:
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
    if "3-2_video_content" in low:
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
    if "6-5_organization_jsonld" in low:
        technical_debt.append({
            "priority": "A",
            "title": "Organization JSON-LD の設置（JobPostingの前提）",
            "category": "構造化データ",
            "impact": "Google for Jobs連携の土台",
            "why": "JobPostingのhiringOrganizationから参照されるため、採用ページとして必須",
            "implementation": "全ページ共通の<head>内にOrganization JSON-LDを設置。logo/sameAs/addressを完備",
        })

    # --- llms.txt（採用ページ向け）---
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
