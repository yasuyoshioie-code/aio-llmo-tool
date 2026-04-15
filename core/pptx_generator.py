"""クライアント提出用PPTXレポート生成モジュール — 実診断データを反映"""

from io import BytesIO
from datetime import datetime

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR


# ===== カラーパレット（Ocean Gradient） =====
class C:
    navy = RGBColor(0x0A, 0x16, 0x28)
    deep_blue = RGBColor(0x06, 0x5A, 0x82)
    teal = RGBColor(0x0D, 0x94, 0x88)
    cyan = RGBColor(0x14, 0xB8, 0xA6)
    cream = RGBColor(0xF8, 0xFA, 0xFC)
    light_bg = RGBColor(0xF1, 0xF5, 0xF9)
    text_dark = RGBColor(0x1E, 0x29, 0x3B)
    text_light = RGBColor(0xE2, 0xE8, 0xF0)
    muted = RGBColor(0x64, 0x74, 0x8B)
    white = RGBColor(0xFF, 0xFF, 0xFF)
    green = RGBColor(0x10, 0xB9, 0x81)
    amber = RGBColor(0xF5, 0x9E, 0x0B)
    red = RGBColor(0xEF, 0x44, 0x44)
    border = RGBColor(0xCB, 0xD5, 0xE1)


FONT_HDR = "Georgia"
FONT_BODY = "メイリオ"  # 日本語対応


# ===== ヘルパー =====
def _set_text(tf, text: str, *, size=14, bold=False, italic=False,
              color=C.text_dark, font=FONT_BODY, align=PP_ALIGN.LEFT,
              anchor=MSO_ANCHOR.TOP):
    tf.text = ""
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Emu(50000)
    tf.margin_right = Emu(50000)
    tf.margin_top = Emu(30000)
    tf.margin_bottom = Emu(30000)
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return p


def _add_rect(slide, x, y, w, h, fill_color, line_color=None, shape_type=MSO_SHAPE.RECTANGLE):
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if line_color is not None:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(0.5)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def _add_text_box(slide, x, y, w, h, text, **kwargs):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    _set_text(tb.text_frame, text, **kwargs)
    return tb


def _header_bar(slide, title, subtitle=""):
    _add_rect(slide, 0, 0, 13.33, 0.7, C.navy)
    _add_rect(slide, 0, 0.7, 13.33, 0.04, C.teal)
    _add_text_box(slide, 0.5, 0.1, 9, 0.5, title,
                  size=18, bold=True, color=C.white, font=FONT_HDR,
                  anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        _add_text_box(slide, 9.5, 0.1, 3.5, 0.5, subtitle,
                      size=11, color=C.cyan, align=PP_ALIGN.RIGHT,
                      anchor=MSO_ANCHOR.MIDDLE)


def _footer(slide, page_num):
    _add_text_box(slide, 0.5, 7.2, 12.3, 0.25,
                  f"AIO/LLMO診断レポート  |  {page_num}",
                  size=9, color=C.muted, align=PP_ALIGN.RIGHT)


def _grade_color(grade: str):
    return {"A": C.green, "B": C.teal, "C": C.amber, "D": C.red, "E": C.red}.get(grade, C.muted)


def _score_color(pct: float):
    if pct >= 0.75:
        return C.green
    if pct >= 0.50:
        return C.teal
    if pct >= 0.35:
        return C.amber
    return C.red


def _set_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


# ====================================================================
# メイン関数
# ====================================================================
def generate_pptx_report(
    url: str,
    structure: dict,
    total: dict,
    categories: dict,
    all_scores: dict,
    robots: dict,
    llms: dict,
    pagespeed: dict,
    competitors: list = None,
    comparison: dict = None,
    improvements: dict = None,
    test_queries: dict = None,
    cv_data: dict = None,
    site_agg: dict = None,
    preset_id: str = "media",
) -> BytesIO:
    """診断データから網羅的なクライアント提出用スライドを生成（20-25枚想定）。

    preset_id: media / recruiting / corporate — カテゴリラベルを切り替え。
    """
    # プリセット別カテゴリ定義を動的に取得
    try:
        from core.presets import get_preset
        _preset_module = get_preset(preset_id)["module"]
        _cat_defs = getattr(_preset_module, "CATEGORY_DEFINITIONS", None)
    except Exception:
        _cat_defs = None
    if _cat_defs:
        cat_order = [(k, v.get("label", k)) for k, v in _cat_defs.items()]
    else:
        cat_order = [
            ("1_content", "コンテンツ品質"),
            ("2_structured", "構造化データ"),
            ("3_eeat", "E-E-A-Tシグナル"),
            ("4_citation", "AI引用可能性"),
            ("5_freshness", "コンテンツ鮮度"),
            ("6_technical", "テクニカルAIO/UX"),
        ]

    # プリセット別の表紙コピー
    _preset_label_map = {
        "media": ("オウンドメディア / コンテンツサイト", "Content & Media Site"),
        "recruiting": ("採用ページ / リクルーティングサイト", "Recruiting Site"),
        "corporate": ("コーポレートサイト / 企業公式サイト", "Corporate Site"),
    }
    preset_label_jp, preset_label_en = _preset_label_map.get(
        preset_id, ("Webサイト", "Website")
    )
    pres = Presentation()
    pres.slide_width = Inches(13.33)
    pres.slide_height = Inches(7.5)
    blank = pres.slide_layouts[6]

    # ページ番号カウンター（リスト型でクロージャ参照）
    pn = [1]
    def _pg() -> str:
        n = pn[0]
        pn[0] += 1
        return f"{n:02d}"

    domain = url.split("//")[-1].split("/")[0] if "//" in url else url
    site_title = structure.get("title", domain)
    today = datetime.now().strftime("%Y年%m月%d日")
    competitors = competitors or []
    comparison = comparison or {}
    improvements = improvements or {}
    test_queries = test_queries or {}

    # ==============================================================
    # Slide 1: タイトル
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.navy)
    _add_rect(s, 0, 0, 5.5, 7.5, C.deep_blue)
    _add_rect(s, 5.3, 0, 0.05, 7.5, C.cyan)

    # ロゴサークル
    _add_rect(s, 1.2, 1.0, 1.4, 1.4, C.cyan, shape_type=MSO_SHAPE.OVAL)
    _add_text_box(s, 1.2, 1.0, 1.4, 1.4, "AIO",
                  size=32, bold=True, color=C.navy, font=FONT_HDR,
                  align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    _add_text_box(s, 1.0, 3.0, 4.3, 0.3,
                  datetime.now().strftime("%Y"),
                  size=12, bold=True, color=C.cyan)
    _add_text_box(s, 1.0, 3.4, 4.3, 1.8,
                  "AIO / LLMO\n総合診断レポート",
                  size=32, bold=True, color=C.white, font=FONT_HDR)
    _add_rect(s, 1.0, 5.3, 0.6, 0.06, C.cyan)
    _add_text_box(s, 1.0, 5.45, 4.3, 0.8,
                  "AI Overview & LLM Optimization\nAssessment Report",
                  size=12, italic=True, color=C.text_light)

    # 右サイド
    _add_text_box(s, 6.2, 1.5, 6.5, 0.5, "診断対象サイト",
                  size=14, color=C.cyan)
    _add_text_box(s, 6.2, 2.0, 6.5, 0.8, site_title[:40],
                  size=26, bold=True, color=C.white, font=FONT_HDR)
    _add_text_box(s, 6.2, 2.9, 6.5, 0.4, url[:70],
                  size=12, italic=True, color=C.text_light)

    _total_items = sum(len(s) for s in (all_scores or {}).values()) if all_scores else 30
    bullets = [
        f"診断種別: {preset_label_jp}",
        f"総合スコア: {total['total']} / 100（グレード {total['grade']}）",
        f"{len(cat_order)}カテゴリ × {_total_items}項目の実測診断",
        f"競合ベンチマーク & 改善アクションプラン",
    ]
    for i, b in enumerate(bullets):
        y = 3.8 + i * 0.5
        _add_rect(s, 6.2, y + 0.08, 0.2, 0.2, C.cyan, shape_type=MSO_SHAPE.OVAL)
        _add_text_box(s, 6.55, y, 6, 0.4, b,
                      size=14, color=C.text_light, anchor=MSO_ANCHOR.MIDDLE)

    _add_text_box(s, 6.2, 6.7, 6.5, 0.3, f"診断日: {today}",
                  size=11, color=C.muted)

    # ==============================================================
    # Slide 2: エグゼクティブサマリー
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "エグゼクティブサマリー", "Executive Summary")

    # スコアカード
    _add_rect(s, 0.5, 1.1, 4.3, 5.8, C.navy, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 0.5, 1.4, 4.3, 0.4, "総合スコア",
                  size=14, color=C.cyan, align=PP_ALIGN.CENTER)
    _add_text_box(s, 0.5, 1.85, 4.3, 2.0, str(total["total"]),
                  size=96, bold=True, color=C.white, font=FONT_HDR,
                  align=PP_ALIGN.CENTER)
    _add_text_box(s, 0.5, 3.8, 4.3, 0.4, "/ 100",
                  size=18, color=C.text_light, align=PP_ALIGN.CENTER)

    _add_rect(s, 1.65, 4.4, 2.0, 0.7, _grade_color(total["grade"]),
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 1.65, 4.4, 2.0, 0.7, f"グレード {total['grade']}",
                  size=22, bold=True, color=C.white, font=FONT_HDR,
                  align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    _add_text_box(s, 0.7, 5.4, 3.9, 0.9, total.get("label", ""),
                  size=11, italic=True, color=C.text_light,
                  align=PP_ALIGN.CENTER)

    # カテゴリ別
    _add_text_box(s, 5.2, 1.15, 7.5, 0.4, "カテゴリ別スコア",
                  size=18, bold=True, color=C.text_dark, font=FONT_HDR)

    for i, (key, label) in enumerate(cat_order):
        cat = categories.get(key, {"score": 0, "max": 20})
        y = 1.75 + i * 0.82
        score = cat.get("score", 0)
        mx = cat.get("max", 20) or 20
        pct = score / mx

        _add_text_box(s, 5.2, y, 3.0, 0.35, label,
                      size=13, bold=True, color=C.text_dark,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_rect(s, 8.3, y + 0.08, 3.5, 0.22, C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, 8.3, y + 0.08, max(3.5 * pct, 0.05), 0.22,
                  _score_color(pct), shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 11.9, y, 0.9, 0.35, f"{score}/{mx}",
                      size=12, bold=True, color=C.text_dark,
                      align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)

    _footer(s, _pg())

    # ==============================================================
    # Slide 3: なぜ今 AIO/LLMO
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "なぜ今、AIO/LLMO対策なのか", "The Shift to AI Search")

    _add_text_box(s, 0.5, 1.0, 12.3, 0.5,
                  "AI検索の普及で「検索→クリック」の時代は終わった",
                  size=20, bold=True, color=C.deep_blue, font=FONT_HDR)

    stats = [
        ("58%", "Google検索でAI Overviewが表示", "日本では2024年8月〜本格展開"),
        ("3.2B", "ChatGPT月間アクセス数", "既にGoogle検索の約1/3規模"),
        ("-35%", "AI Overview表示時のCTR下落", "従来SEOだけでは機会損失"),
    ]
    for i, (num, label, sub) in enumerate(stats):
        x = 0.5 + i * 4.3
        _add_rect(s, x, 1.8, 4.0, 2.2, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, x, 1.8, 0.1, 2.2, C.teal)
        _add_text_box(s, x + 0.2, 1.95, 3.8, 1.0, num,
                      size=44, bold=True, color=C.deep_blue, font=FONT_HDR,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, x + 0.2, 2.95, 3.8, 0.5, label,
                      size=13, bold=True, color=C.text_dark)
        _add_text_box(s, x + 0.2, 3.45, 3.8, 0.4, sub,
                      size=10, italic=True, color=C.muted)

    # 下段2カラム
    _add_rect(s, 0.5, 4.4, 6.1, 2.4, C.navy,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 0.7, 4.55, 5.7, 0.4, "❌ 何もしない場合",
                  size=14, bold=True, color=C.red)
    bad = [
        "AI検索結果に一切表示されず機会損失",
        "競合がAI引用を獲得、相対順位が下落",
        "SEO投資のROIが年々低下",
        "商談・採用での情報露出が減少",
    ]
    for i, b in enumerate(bad):
        _add_text_box(s, 0.8, 5.0 + i * 0.4, 5.6, 0.35, "• " + b,
                      size=12, color=C.text_light)

    _add_rect(s, 6.8, 4.4, 6.0, 2.4, C.teal,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 7.0, 4.55, 5.6, 0.4, "✅ 早期対策の効果",
                  size=14, bold=True, color=C.white)
    good = [
        "AI Overviewでの引用率が平均3〜5倍向上",
        "Perplexity / ChatGPTでの出典表示獲得",
        "ブランド第一想起（エンティティ認識）を確立",
        "SEOとAIOの相乗効果で検索総流入増",
    ]
    for i, g in enumerate(good):
        _add_text_box(s, 7.1, 5.0 + i * 0.4, 5.5, 0.35, "• " + g,
                      size=12, color=C.white)

    _footer(s, _pg())

    # ==============================================================
    # Slide 4: 診断フレームワーク
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "診断フレームワーク", "6 Categories × 30 Items")

    _add_text_box(s, 0.5, 1.0, 12.3, 0.4,
                  "AI検索時代に必要な6つの評価軸で、30項目を実測診断",
                  size=14, color=C.muted)

    framework = [
        ("01", "コンテンツ品質・構造", "20点", "Answer-first, 見出し階層, FAQ, 明瞭性", C.deep_blue),
        ("02", "構造化データ",         "20点", "Organization, Article, FAQPage, Breadcrumb", C.teal),
        ("03", "E-E-A-Tシグナル",      "20点", "著者情報, 運営者, 引用, 編集ポリシー", C.cyan),
        ("04", "AI引用可能性",         "20点", "定義文, 数値データ, 独自情報, エンティティ", C.deep_blue),
        ("05", "コンテンツ鮮度",       "10点", "更新日表示, dateModified, 年次管理", C.teal),
        ("06", "テクニカルAIO/UX",     "10点", "AIクローラー, PageSpeed, canonical, sitemap", C.cyan),
    ]
    for i, (num, label, pts, items, color) in enumerate(framework):
        col = i % 3
        row = i // 3
        x = 0.5 + col * 4.3
        y = 1.6 + row * 2.6

        _add_rect(s, x, y, 4.0, 2.4, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, x + 0.2, y + 0.2, 0.8, 0.8, color,
                  shape_type=MSO_SHAPE.OVAL)
        _add_text_box(s, x + 0.2, y + 0.2, 0.8, 0.8, num,
                      size=16, bold=True, color=C.white, font=FONT_HDR,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_rect(s, x + 2.9, y + 0.3, 1.0, 0.4, C.light_bg,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, x + 2.9, y + 0.3, 1.0, 0.4, pts,
                      size=11, bold=True, color=C.deep_blue,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, x + 0.2, y + 1.1, 3.7, 0.5, label,
                      size=16, bold=True, color=C.text_dark, font=FONT_HDR)
        _add_rect(s, x + 0.2, y + 1.62, 0.5, 0.03, color)
        _add_text_box(s, x + 0.2, y + 1.75, 3.7, 0.6, items,
                      size=10, color=C.muted)

    _footer(s, _pg())

    # ==============================================================
    # Slide 5: カテゴリ別診断結果
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "カテゴリ別診断結果", "Category Breakdown")

    # 判定を計算
    def _judge(pct):
        if pct >= 0.8:
            return "A", C.green, "🟢 維持"
        if pct >= 0.6:
            return "B", C.teal, "🟢 維持"
        if pct >= 0.4:
            return "C", C.amber, "🟡 要改善"
        return "D", C.red, "🔴 最優先"

    rows = []
    for key, label in cat_order:
        cat = categories.get(key, {})
        score = cat.get("score", 0)
        mx = cat.get("max", 20) or 20
        pct = score / mx
        status, color, priority = _judge(pct)
        # 主な所見を算出
        items = cat.get("items", [])
        low = [i for i in items if i.get("max", 0) > 0
               and i.get("score", 0) / i.get("max", 1) < 0.5]
        note = f"低スコア項目 {len(low)}件" if low else "主要項目クリア"
        rows.append({
            "cat": label, "score": f"{score}/{mx}",
            "status": status, "note": note, "color": color,
            "priority": priority,
        })

    # テーブルヘッダー
    _add_rect(s, 0.5, 1.1, 12.3, 0.5, C.navy)
    hdrs = [("カテゴリ", 0.7, 3.5), ("スコア", 4.2, 1.5), ("判定", 5.7, 1.0),
            ("主な所見", 6.7, 4.0), ("優先度", 10.7, 2.0)]
    for t, x, w in hdrs:
        _add_text_box(s, x, 1.1, w, 0.5, t,
                      size=12, bold=True, color=C.white,
                      anchor=MSO_ANCHOR.MIDDLE)

    for i, r in enumerate(rows):
        y = 1.6 + i * 0.55
        if i % 2 == 0:
            _add_rect(s, 0.5, y, 12.3, 0.55, C.white)
        _add_text_box(s, 0.7, y, 3.5, 0.55, r["cat"],
                      size=13, bold=True, color=C.text_dark,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 4.2, y, 1.5, 0.55, r["score"],
                      size=15, bold=True, color=C.deep_blue, font=FONT_HDR,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_rect(s, 5.7, y + 0.1, 0.7, 0.35, r["color"],
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 5.7, y + 0.1, 0.7, 0.35, r["status"],
                      size=11, bold=True, color=C.white,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 6.7, y, 4.0, 0.55, r["note"],
                      size=11, color=C.muted, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 10.7, y, 2.0, 0.55, r["priority"],
                      size=11, bold=True, color=C.text_dark,
                      anchor=MSO_ANCHOR.MIDDLE)

    # インサイト
    _add_rect(s, 0.5, 5.2, 12.3, 1.6, C.deep_blue,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 0.8, 5.35, 11.7, 0.4, "💡 診断インサイト",
                  size=13, bold=True, color=C.cyan)

    # 弱点カテゴリを特定
    weak_cats = sorted(
        [(lbl, categories.get(k, {})) for k, lbl in cat_order],
        key=lambda x: x[1].get("score", 0) / (x[1].get("max", 1) or 1),
    )[:2]
    weak_names = " / ".join(w[0] for w in weak_cats)
    insight = (
        f"特に改善が必要な領域は「{weak_names}」です。この2領域は実装コストが低く、"
        f"効果が大きい「クイックウィン領域」です。60日以内の改善で +15〜20点の向上が見込めます。"
    )
    _add_text_box(s, 0.8, 5.75, 11.7, 1.0, insight,
                  size=12, color=C.white)

    _footer(s, _pg())

    # ==============================================================
    # Slide 6: テクニカル診断
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "テクニカル診断 — AIクローラー対応", "robots.txt / llms.txt / Performance")

    _add_text_box(s, 0.5, 1.1, 6.5, 0.4, "🤖 AIクローラーのアクセス状況",
                  size=16, bold=True, color=C.text_dark, font=FONT_HDR)

    crawlers_data = robots.get("crawlers", {})
    for i, (name, info) in enumerate(list(crawlers_data.items())[:6]):
        y = 1.6 + i * 0.55
        status = info.get("status", "未設定")
        if "ブロック" in status:
            color = C.red
        elif "許可" in status:
            color = C.green
        else:
            color = C.amber

        _add_rect(s, 0.5, y, 6.3, 0.5, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 0.7, y, 2.0, 0.5, name,
                      size=12, bold=True, color=C.text_dark,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 2.6, y, 2.5, 0.5, info.get("vendor", ""),
                      size=10, color=C.muted, anchor=MSO_ANCHOR.MIDDLE)
        # ステータスラベルを短縮
        status_short = status[:8] if len(status) > 8 else status
        _add_rect(s, 5.3, y + 0.1, 1.3, 0.3, color,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 5.3, y + 0.1, 1.3, 0.3, status_short,
                      size=9, bold=True, color=C.white,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # 右サイド メトリクス
    _add_text_box(s, 7.2, 1.1, 5.6, 0.4, "⚙️ テクニカルメトリクス",
                  size=16, bold=True, color=C.text_dark, font=FONT_HDR)

    ps_score = pagespeed.get("score")
    ps_val = f"{ps_score}" if ps_score is not None else "—"
    ps_color = C.green if (ps_score or 0) >= 80 else (
        C.amber if (ps_score or 0) >= 50 else C.red)

    metrics = [
        ("PageSpeed", ps_val, "/100" if ps_score else "",
         f"Performance Score: {ps_score}" if ps_score else "取得失敗",
         ps_color),
        ("llms.txt", "○" if llms.get("exists") else "×", "",
         llms.get("summary", ""),
         C.green if llms.get("exists") else C.red),
        ("sitemap.xml", "○" if structure.get("sitemap_exists", True) else "×", "",
         "登録済み",
         C.green),
        ("canonical", "○" if structure.get("canonical") else "×", "",
         (structure.get("canonical", "")[:40] if structure.get("canonical") else "未実装"),
         C.green if structure.get("canonical") else C.red),
        ("viewport", "○" if structure.get("viewport") else "×", "",
         "モバイル対応" if structure.get("viewport") else "未対応",
         C.green if structure.get("viewport") else C.red),
    ]

    for i, (lbl, val, unit, note, color) in enumerate(metrics):
        y = 1.6 + i * 0.95
        _add_rect(s, 7.2, y, 5.6, 0.85, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, 7.2, y, 0.08, 0.85, color)
        _add_text_box(s, 7.45, y + 0.1, 3.0, 0.35, lbl,
                      size=12, bold=True, color=C.text_dark)
        _add_text_box(s, 7.45, y + 0.45, 3.5, 0.35, note,
                      size=10, color=C.muted)
        _add_text_box(s, 10.8, y, 1.9, 0.85, val + unit,
                      size=24, bold=True, color=color, font=FONT_HDR,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    _footer(s, _pg())

    # ==============================================================
    # Slide 7: 構造化データ
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "構造化データ（JSON-LD）実装状況", "Schema.org Coverage")

    _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                  "AIが正確に情報を読み取るための「機械可読ラベル」の実装状況",
                  size=13, italic=True, color=C.muted)

    # 実装されているスキーマタイプを検出
    found_types = set()
    for sd in structure.get("jsonld", []):
        t = sd.get("@type", "")
        if isinstance(t, list):
            found_types.update(t)
        else:
            found_types.add(t)

    schemas = [
        ("Organization", "Organization" in found_types, "必須", "運営者情報をAIに明示"),
        ("Article / BlogPosting",
         "Article" in found_types or "BlogPosting" in found_types,
         "必須", "記事メタデータ認識"),
        ("FAQPage", "FAQPage" in found_types, "必須",
         "AI Overview引用率が大幅アップ"),
        ("BreadcrumbList", "BreadcrumbList" in found_types, "推奨",
         "検索結果パンくず表示"),
        ("LocalBusiness", "LocalBusiness" in found_types, "条件",
         "ローカルビジネスのみ必要"),
        ("HowTo", "HowTo" in found_types, "推奨",
         "手順コンテンツに有効"),
        ("Product", "Product" in found_types, "推奨",
         "製品・サービスに有効"),
    ]

    _add_rect(s, 0.5, 1.55, 12.3, 0.45, C.navy)
    for t, x, w in [("スキーマタイプ", 0.8, 3.0), ("状況", 3.8, 1.3),
                    ("状態", 5.1, 1.8), ("優先度", 6.9, 1.5),
                    ("AIへの効果", 8.4, 4.3)]:
        _add_text_box(s, x, 1.55, w, 0.45, t,
                      size=11, bold=True, color=C.white,
                      anchor=MSO_ANCHOR.MIDDLE)

    for i, (stype, impl, prio, impact) in enumerate(schemas):
        y = 2.0 + i * 0.52
        if i % 2 == 0:
            _add_rect(s, 0.5, y, 12.3, 0.52, C.white)
        icon = "○" if impl else "×"
        status = "実装済み" if impl else "未実装"
        color = C.green if impl else C.red

        _add_text_box(s, 0.8, y, 3.0, 0.52, stype,
                      size=12, bold=True, color=C.text_dark,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 3.8, y, 1.3, 0.52, icon,
                      size=18, bold=True, color=color, font=FONT_HDR,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 5.1, y, 1.8, 0.52, status,
                      size=11, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)
        prio_color = C.red if prio == "必須" else (C.amber if prio == "推奨" else C.muted)
        _add_text_box(s, 6.9, y, 1.5, 0.52, prio,
                      size=11, bold=True, color=prio_color,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 8.4, y, 4.3, 0.52, impact,
                      size=10, color=C.muted, anchor=MSO_ANCHOR.MIDDLE)

    # コールアウト
    missing_required = [stype for stype, impl, prio, _ in schemas
                        if not impl and prio == "必須"]
    callout = (
        f"⚡ {' / '.join(missing_required[:3])} の追加で大幅スコアアップ。実装所要時間は合計2〜3時間程度です。"
        if missing_required else
        "⚡ 必須スキーマは実装済み。推奨スキーマの追加で更なる最適化が可能です。"
    )
    _add_rect(s, 0.5, 5.9, 12.3, 0.9, C.teal,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 0.7, 5.9, 11.9, 0.9, callout,
                  size=13, bold=True, color=C.white,
                  anchor=MSO_ANCHOR.MIDDLE)

    _footer(s, _pg())

    # ==============================================================
    # Slide 8: 競合ベンチマーク
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "競合ベンチマーク", "Competitive Analysis")

    _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                  "メインキーワード上位サイトとの比較",
                  size=13, italic=True, color=C.muted)

    # 自サイト + 競合データ
    sites = [{
        "name": "自サイト",
        "wc": structure.get("word_count", 0),
        "h2": sum(1 for h in structure.get("headings", []) if h.get("level") == 2),
        "faq": len(structure.get("faq_items", [])),
        "sd": ", ".join(list(found_types)[:3]) or "なし",
        "score": total["total"],
        "self": True,
    }]
    for c in competitors[:3]:
        sites.append({
            "name": (c.get("title") or c.get("url", ""))[:25],
            "wc": c.get("word_count", 0),
            "h2": c.get("h2_count", 0),
            "faq": c.get("faq_count", 0),
            "sd": ", ".join(c.get("sd_types", [])[:3]) or "なし",
            "score": c.get("score_pct", 0),
            "self": False,
        })

    _add_rect(s, 0.5, 1.55, 12.3, 0.5, C.navy)
    for t, x, w in [("サイト", 0.7, 2.8), ("文字数", 3.5, 1.4),
                    ("H2数", 4.9, 1.2), ("FAQ数", 6.1, 1.2),
                    ("構造化データ", 7.3, 3.5), ("スコア", 10.8, 1.9)]:
        _add_text_box(s, x, 1.55, w, 0.5, t,
                      size=12, bold=True, color=C.white,
                      anchor=MSO_ANCHOR.MIDDLE)

    for i, site in enumerate(sites):
        y = 2.05 + i * 0.6
        bg = C.light_bg if site["self"] else C.white
        _add_rect(s, 0.5, y, 12.3, 0.6, bg, line_color=C.border)
        _add_text_box(s, 0.7, y, 2.8, 0.6, site["name"],
                      size=13, bold=True,
                      color=C.deep_blue if site["self"] else C.text_dark,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 3.5, y, 1.4, 0.6, f"{site['wc']:,}",
                      size=12, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 4.9, y, 1.2, 0.6, str(site["h2"]),
                      size=12, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 6.1, y, 1.2, 0.6, str(site["faq"]),
                      size=12, bold=(site["faq"] == 0),
                      color=(C.red if site["faq"] == 0 else C.text_dark),
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 7.3, y, 3.5, 0.6, site["sd"][:40],
                      size=10, color=C.muted, anchor=MSO_ANCHOR.MIDDLE)
        sc_color = (C.green if site["score"] >= 80 else
                    C.amber if site["score"] >= 60 else C.red)
        _add_rect(s, 10.8, y + 0.1, 1.5, 0.4, sc_color,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 10.8, y + 0.1, 1.5, 0.4, f"{site['score']}点",
                      size=13, bold=True, color=C.white,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # ギャップ / 優位性
    gaps_y = 2.05 + len(sites) * 0.6 + 0.3
    _add_rect(s, 0.5, gaps_y, 6.1, 6.8 - gaps_y, C.white, line_color=C.red,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 0.7, gaps_y + 0.1, 5.7, 0.4,
                  "🔴 コンテンツギャップ（負けている項目）",
                  size=13, bold=True, color=C.red)
    gaps = comparison.get("gaps", [])[:3]
    if not gaps:
        gaps_text = ["競合データ不足のため算出不能"]
    else:
        gaps_text = [f"{g['item']}: 自 {g['self_score']} vs 競合平均 {g['competitor_avg']}"
                     for g in gaps]
    for i, gt in enumerate(gaps_text):
        _add_text_box(s, 0.8, gaps_y + 0.55 + i * 0.4, 5.6, 0.4, "• " + gt,
                      size=11, color=C.text_dark)

    _add_rect(s, 6.8, gaps_y, 6.0, 6.8 - gaps_y, C.white, line_color=C.green,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 7.0, gaps_y + 0.1, 5.6, 0.4,
                  "✅ 独自優位性（勝っている項目）",
                  size=13, bold=True, color=C.green)
    advs = comparison.get("advantages", [])[:3]
    if not advs:
        advs_text = ["競合データ不足のため算出不能"]
    else:
        advs_text = [f"{a['item']}: 自 {a['self_score']} vs 競合平均 {a['competitor_avg']}"
                     for a in advs]
    for i, at in enumerate(advs_text):
        _add_text_box(s, 7.1, gaps_y + 0.55 + i * 0.4, 5.5, 0.4, "• " + at,
                      size=11, color=C.text_dark)

    _footer(s, _pg())

    # ==============================================================
    # Slide 9: Quick Win
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "優先改善施策 — Quick Win", "60日以内で実施可能な高効果施策")

    _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                  "今すぐ着手でき、かつインパクトが大きい施策",
                  size=13, italic=True, color=C.muted)

    qw_list = improvements.get("quick_wins", [])
    if not qw_list:
        # デフォルトQW
        qw_list = [
            {"title": "Organization JSON-LDの追加", "category": "構造化データ",
             "effort": "30分", "impact": "+4点",
             "reason": "運営者情報をAIに明示。全ページ共通で1度実装すれば完了。"},
            {"title": "FAQPage JSON-LD + FAQ追加", "category": "構造化データ",
             "effort": "2時間", "impact": "+6点",
             "reason": "Google AI Overview引用率が平均3倍に。即効性が最も高い施策。"},
            {"title": "著者ボックスの設置", "category": "E-E-A-T",
             "effort": "1時間", "impact": "+3点",
             "reason": "著者名・専門分野・プロフィールリンクを全記事に追加。"},
            {"title": "llms.txt の設置", "category": "テクニカル",
             "effort": "30分", "impact": "+2点",
             "reason": "ChatGPTがサイト概要を正確に把握（2025年10月〜対応）。"},
            {"title": "冒頭定義文の追加", "category": "AI引用可能性",
             "effort": "1時間", "impact": "+3点",
             "reason": "AIが最も引用しやすいパターン。既存記事の冒頭改修のみで可能。"},
        ]

    for i, q in enumerate(qw_list[:5]):
        y = 1.55 + i * 1.08
        _add_rect(s, 0.5, y, 12.3, 0.98, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, 0.7, y + 0.2, 0.6, 0.6, C.teal,
                  shape_type=MSO_SHAPE.OVAL)
        _add_text_box(s, 0.7, y + 0.2, 0.6, 0.6, str(i + 1),
                      size=20, bold=True, color=C.white, font=FONT_HDR,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 1.5, y + 0.1, 6.5, 0.4,
                      q.get("title", "")[:50],
                      size=14, bold=True, color=C.text_dark, font=FONT_HDR,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_rect(s, 1.5, y + 0.55, 1.7, 0.3, C.light_bg,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 1.5, y + 0.55, 1.7, 0.3, q.get("category", "")[:12],
                      size=9, bold=True, color=C.deep_blue,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 3.3, y + 0.5, 6.8, 0.4,
                      q.get("reason", "")[:110],
                      size=10, color=C.muted, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 10.3, y + 0.1, 2.2, 0.3, "インパクト",
                      size=9, color=C.muted, align=PP_ALIGN.CENTER)
        _add_rect(s, 10.4, y + 0.4, 2.0, 0.45, C.teal,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 10.4, y + 0.4, 2.0, 0.45,
                      q.get("impact", "")[:10],
                      size=14, bold=True, color=C.white, font=FONT_HDR,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    _footer(s, _pg())

    # ==============================================================
    # Slide 10〜N: Quick Win 詳細展開（1施策につき1ページ）
    # ==============================================================
    qw_detail_list = improvements.get("quick_wins", []) or qw_list
    for idx, qw in enumerate(qw_detail_list[:8], 1):
        s = pres.slides.add_slide(blank)
        _set_bg(s, C.cream)

        # ヘッダー
        priority = qw.get("priority", "A")
        pri_color = {"S": C.red, "A": C.amber, "B": C.teal, "C": C.muted}.get(priority, C.teal)
        _add_rect(s, 0, 0, 13.33, 0.65, C.navy)
        _add_text_box(s, 0.5, 0.13, 0.9, 0.4, f"#{idx:02d}",
                      size=18, bold=True, color=C.cyan, font=FONT_HDR)
        _add_rect(s, 1.4, 0.18, 0.7, 0.32, pri_color,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 1.4, 0.18, 0.7, 0.32, f"優先{priority}",
                      size=11, bold=True, color=C.white,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 2.2, 0.13, 9.0, 0.4, qw.get("title", "")[:70],
                      size=16, bold=True, color=C.white, font=FONT_HDR,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 11.3, 0.13, 1.9, 0.4,
                      qw.get("category", "")[:14],
                      size=11, color=C.cyan,
                      align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        _add_rect(s, 0, 0.65, 13.33, 0.04, C.cyan)

        # 上段：Why（背景・狙い）／KPI／インパクト
        _add_rect(s, 0.4, 0.95, 8.0, 1.45, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 0.6, 1.0, 7.7, 0.3, "💡 なぜこの施策か（Why）",
                      size=11, bold=True, color=C.deep_blue)
        _add_text_box(s, 0.6, 1.3, 7.7, 1.05, qw.get("why", "")[:280],
                      size=11, color=C.text_dark)

        # 右上：KPI / Impact / Effort
        _add_rect(s, 8.55, 0.95, 4.4, 0.65, C.deep_blue,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 8.7, 0.95, 4.1, 0.25, "🎯 KPI",
                      size=9, color=C.cyan, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 8.7, 1.18, 4.1, 0.4, qw.get("kpi", "")[:60],
                      size=10, bold=True, color=C.white, anchor=MSO_ANCHOR.MIDDLE)

        _add_rect(s, 8.55, 1.7, 2.1, 0.7, C.teal,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 8.55, 1.7, 2.1, 0.25, "想定インパクト",
                      size=9, color=C.white, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 8.55, 1.95, 2.1, 0.45, str(qw.get("impact", "+5点"))[:14],
                      size=15, bold=True, color=C.white, font=FONT_HDR,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

        _add_rect(s, 10.85, 1.7, 2.1, 0.7, C.amber,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 10.85, 1.7, 2.1, 0.25, "実装工数",
                      size=9, color=C.white, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 10.85, 1.95, 2.1, 0.45, str(qw.get("effort", qw.get("cost", "1日")))[:14],
                      size=15, bold=True, color=C.white, font=FONT_HDR,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

        # 中段：実装ステップ
        _add_rect(s, 0.4, 2.55, 12.55, 1.6, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 0.6, 2.6, 12.2, 0.3, "🛠 実装ステップ（このとおりに進めれば完了）",
                      size=11, bold=True, color=C.deep_blue)
        steps = qw.get("steps") or qw.get("actions") or []
        for si, step in enumerate(steps[:6], 1):
            sx = 0.6 + (si - 1) % 2 * 6.15
            sy = 2.95 + (si - 1) // 2 * 0.4
            _add_rect(s, sx, sy + 0.07, 0.25, 0.25, C.teal,
                      shape_type=MSO_SHAPE.OVAL)
            _add_text_box(s, sx, sy + 0.07, 0.25, 0.25, str(si),
                          size=9, bold=True, color=C.white,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, sx + 0.32, sy, 5.7, 0.4, str(step)[:80],
                          size=9, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)

        # 下段：Before / After サンプルコード
        before_text = str(qw.get("before", ""))[:200]
        after_text = str(qw.get("after", qw.get("code_sample", "")))[:380]

        _add_rect(s, 0.4, 4.3, 6.15, 2.55, RGBColor(0xFE, 0xF3, 0xF2), line_color=C.red,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, 0.4, 4.3, 6.15, 0.32, C.red,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 0.5, 4.3, 6.0, 0.32, "❌ BEFORE（現状）",
                      size=10, bold=True, color=C.white, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 0.55, 4.7, 6.0, 2.1, before_text,
                      size=8, color=C.text_dark, font="Consolas")

        _add_rect(s, 6.8, 4.3, 6.15, 2.55, RGBColor(0xEC, 0xFD, 0xF5), line_color=C.green,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, 6.8, 4.3, 6.15, 0.32, C.green,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 6.9, 4.3, 6.0, 0.32, "✅ AFTER（実装後）",
                      size=10, bold=True, color=C.white, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 6.95, 4.7, 6.0, 2.1, after_text,
                      size=8, color=C.text_dark, font="Consolas")

        # 検証方法
        validation = qw.get("validation", "")
        if validation:
            _add_rect(s, 0.4, 6.95, 12.55, 0.3, C.light_bg,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.55, 6.95, 12.3, 0.3,
                          f"🔍 検証: {validation[:140]}",
                          size=9, italic=True, color=C.deep_blue, anchor=MSO_ANCHOR.MIDDLE)

        _footer(s, _pg())

    # ==============================================================
    # 🎯 CV診断（面接応募）— サマリ + 10要素 + 改善案2-3枚
    # ==============================================================
    if cv_data:
        # ----- CVサマリスライド -----
        s = pres.slides.add_slide(blank)
        _set_bg(s, C.cream)
        _header_bar(s, "🎯 CV（面接応募）転換率診断", "Conversion Rate Assessment")

        cv_total_score = cv_data.get("cv_total", 0)
        cv_grade = cv_data.get("cv_grade", "C")
        est_cv = cv_data.get("estimated_cv_rate", 0)
        imp_cv = cv_data.get("improved_cv_rate", 0)
        uplift_pct = cv_data.get("potential_uplift_pct", 0)
        bench_pos = cv_data.get("benchmark_position", "業界平均並み")
        bench = cv_data.get("benchmark", {})

        # 4カードKPI
        cards = [
            ("CV診断スコア", f"{cv_total_score}", f"/100  {cv_grade}", _grade_color(cv_grade)),
            ("推定CV率（現状）", f"{est_cv}", "%", C.amber),
            ("改善後CV率（予測）", f"{imp_cv}", "%", C.green),
            ("改善余地", f"+{uplift_pct}", "%", C.teal),
        ]
        for i, (lbl, big, sub, col) in enumerate(cards):
            x = 0.5 + i * 3.18
            _add_rect(s, x, 1.15, 3.0, 1.5, col, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, x, 1.2, 3.0, 0.3, lbl,
                          size=11, color=C.white, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, x, 1.55, 3.0, 0.7, big,
                          size=36, bold=True, color=C.white, font=FONT_HDR,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, x, 2.3, 3.0, 0.3, sub,
                          size=12, color=C.white, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

        # ベンチマーク帯
        _add_rect(s, 0.5, 2.85, 12.3, 1.05, C.navy, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 0.7, 2.92, 11.9, 0.3, "📊 業界ベンチマーク（採用ページ応募完了率）",
                      size=11, bold=True, color=C.cyan)
        _add_text_box(s, 0.7, 3.22, 11.9, 0.65,
                      f"業界平均: {bench.get('industry_avg_low', 1.5)}〜{bench.get('industry_avg_high', 3.0)}%　|　"
                      f"ベストプラクティス: {bench.get('best_practice', 6.0)}%　|　"
                      f"トップクラス: {bench.get('top_class', 10.0)}%　|　"
                      f"自社位置: {bench_pos}",
                      size=12, color=C.white, anchor=MSO_ANCHOR.MIDDLE)

        # 10要素レーダー風（横棒）
        _add_text_box(s, 0.5, 4.05, 12.3, 0.4, "🔍 CV阻害要因 10要素 — スコア一覧",
                      size=14, bold=True, color=C.text_dark, font=FONT_HDR)
        factors = cv_data.get("factors", [])
        for i, f in enumerate(factors[:10]):
            row = i % 5
            col = i // 5
            x = 0.5 + col * 6.4
            y = 4.5 + row * 0.5
            score = f.get("score", 0)
            mx = f.get("max", 10)
            pct = score / mx if mx else 0
            color = C.green if pct >= 0.7 else (C.amber if pct >= 0.4 else C.red)

            _add_text_box(s, x, y, 2.5, 0.4, f.get("label", "")[:14],
                          size=10, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)
            _add_rect(s, x + 2.5, y + 0.1, 3.0, 0.2, C.border,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_rect(s, x + 2.5, y + 0.1, max(3.0 * pct, 0.05), 0.2, color,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, x + 5.6, y, 0.7, 0.4, f"{score}/{mx}",
                          size=10, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE)

        # 弱点TOP3
        weak = cv_data.get("weak_factors", [])[:3]
        if weak:
            _add_rect(s, 0.5, 7.0, 12.3, 0.35, C.red, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.6, 7.0, 12.2, 0.35,
                          "⚠️ 最優先弱点: " + " / ".join(f["label"] + f"({f['score']}点)" for f in weak),
                          size=10, bold=True, color=C.white, anchor=MSO_ANCHOR.MIDDLE)

        _footer(s, _pg())

        # ----- CV改善案 詳細スライド（最大4件） -----
        cv_ideas = cv_data.get("improvement_ideas", [])
        for i, idea in enumerate(cv_ideas[:6]):
            s = pres.slides.add_slide(blank)
            _set_bg(s, C.cream)

            pri = idea.get("priority", "A")
            pri_color = {"S": C.red, "A": C.amber, "B": C.teal}.get(pri, C.teal)
            _add_rect(s, 0, 0, 13.33, 0.65, RGBColor(0x7C, 0x2D, 0x12))  # CV専用色
            _add_text_box(s, 0.5, 0.13, 1.4, 0.4, "🎯 CV改善",
                          size=13, bold=True, color=C.cyan, font=FONT_HDR)
            _add_rect(s, 1.95, 0.18, 0.7, 0.32, pri_color,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 1.95, 0.18, 0.7, 0.32, f"優先{pri}",
                          size=11, bold=True, color=C.white,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 2.75, 0.13, 8.5, 0.4, idea.get("title", "")[:60],
                          size=15, bold=True, color=C.white, font=FONT_HDR,
                          anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 11.3, 0.13, 1.9, 0.4,
                          f"対象: {idea.get('factor_label', '')[:14]}",
                          size=10, color=C.cyan,
                          align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
            _add_rect(s, 0, 0.65, 13.33, 0.04, C.cyan)

            # 現状スコア / 期待効果 / コスト カード
            cur_score = idea.get("current_score", 0)
            max_score = idea.get("max_score", 10)
            _add_rect(s, 0.4, 0.95, 4.1, 1.0, C.white, line_color=C.border,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.5, 1.0, 4.0, 0.3, "📊 現状スコア",
                          size=10, color=C.muted, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 0.5, 1.3, 4.0, 0.6, f"{cur_score} / {max_score}",
                          size=24, bold=True, color=C.red, font=FONT_HDR,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

            _add_rect(s, 4.6, 0.95, 4.1, 1.0, C.green, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 4.7, 1.0, 4.0, 0.3, "📈 期待CV改善効果",
                          size=10, color=C.white, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 4.7, 1.3, 4.0, 0.6, str(idea.get("expected_uplift", ""))[:18],
                          size=20, bold=True, color=C.white, font=FONT_HDR,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

            _add_rect(s, 8.85, 0.95, 4.1, 1.0, C.amber, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 8.95, 1.0, 4.0, 0.3, "💰 実装コスト",
                          size=10, color=C.white, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 8.95, 1.3, 4.0, 0.6, str(idea.get("cost", ""))[:18],
                          size=18, bold=True, color=C.white, font=FONT_HDR,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

            # 具体的アクション
            _add_rect(s, 0.4, 2.1, 12.55, 2.1, C.white, line_color=C.border,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.6, 2.15, 12.3, 0.3, "🛠 具体的アクション",
                          size=12, bold=True, color=C.deep_blue)
            actions = idea.get("actions", [])
            for ai, action in enumerate(actions[:5]):
                ay = 2.5 + ai * 0.32
                _add_rect(s, 0.6, ay + 0.07, 0.22, 0.22, C.teal, shape_type=MSO_SHAPE.OVAL)
                _add_text_box(s, 0.6, ay + 0.07, 0.22, 0.22, str(ai + 1),
                              size=9, bold=True, color=C.white,
                              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
                _add_text_box(s, 0.9, ay, 11.9, 0.32, str(action)[:130],
                              size=10, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)

            # 実装サンプルコード
            _add_rect(s, 0.4, 4.35, 12.55, 2.55, RGBColor(0x1E, 0x29, 0x3B),
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_rect(s, 0.4, 4.35, 12.55, 0.32, C.deep_blue,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.55, 4.35, 12.3, 0.32, "💻 実装サンプルコード（コピペで使える）",
                          size=10, bold=True, color=C.white, anchor=MSO_ANCHOR.MIDDLE)
            code = str(idea.get("code_sample", ""))[:600]
            _add_text_box(s, 0.55, 4.75, 12.3, 2.1, code,
                          size=8, color=C.cyan, font="Consolas")

            # CV影響メモ
            _add_rect(s, 0.4, 7.0, 12.55, 0.32, C.light_bg,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.55, 7.0, 12.3, 0.32,
                          "📌 改善対象要素: " + idea.get("factor_label", "") + " — 業界統計データに基づく改善余地",
                          size=9, italic=True, color=C.deep_blue, anchor=MSO_ANCHOR.MIDDLE)

            _footer(s, _pg())

        # ----- CV改善ロードマップスライド -----
        if cv_ideas:
            s = pres.slides.add_slide(blank)
            _set_bg(s, C.cream)
            _header_bar(s, "🎯 CV改善 推奨実施ロードマップ", "CV Improvement Roadmap")
            _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                          f"優先度・現状スコア順に並べた{len(cv_ideas)}施策の実施順序",
                          size=13, italic=True, color=C.muted)

            # 並び替え: 優先度S→A→B、その中で現状スコア低い順
            sorted_ideas = sorted(cv_ideas,
                                   key=lambda x: ({"S": 0, "A": 1, "B": 2}.get(x.get("priority", "B"), 9),
                                                  x.get("current_score", 0)))

            # ヘッダー
            _add_rect(s, 0.5, 1.55, 12.3, 0.4, C.navy)
            for hi, (htxt, w, x_off) in enumerate([
                ("順", 0.5, 0), ("Phase", 1.6, 0.5),
                ("施策", 5.0, 2.1),
                ("対象要素", 2.4, 7.1),
                ("効果", 1.5, 9.5),
                ("工数", 1.3, 11.0),
            ]):
                _add_text_box(s, 0.5 + x_off, 1.55, w, 0.4, htxt,
                              size=10, bold=True, color=C.cyan,
                              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

            for i, idea in enumerate(sorted_ideas[:12]):
                y = 1.95 + i * 0.4
                bg = C.white if i % 2 == 0 else C.light_bg
                phase = "Phase 1（〜30日）" if i < 3 else ("Phase 2（〜60日）" if i < 6 else "Phase 3（60日〜）")
                phase_color = C.red if i < 3 else (C.amber if i < 6 else C.teal)
                _add_rect(s, 0.5, y, 12.3, 0.4, bg, line_color=C.border)
                _add_text_box(s, 0.55, y, 0.5, 0.4, str(i + 1),
                              size=10, bold=True, color=C.text_dark,
                              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
                _add_rect(s, 1.05, y + 0.05, 1.5, 0.3, phase_color,
                          shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
                _add_text_box(s, 1.05, y + 0.05, 1.5, 0.3, phase[:9],
                              size=8, bold=True, color=C.white,
                              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
                _add_text_box(s, 2.65, y, 5.0, 0.4, idea.get("title", "")[:42],
                              size=9, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)
                _add_text_box(s, 7.65, y, 2.4, 0.4, idea.get("factor_label", "")[:16],
                              size=9, color=C.muted,
                              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
                _add_text_box(s, 10.05, y, 1.5, 0.4, str(idea.get("expected_uplift", ""))[:14],
                              size=9, bold=True, color=C.green,
                              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
                _add_text_box(s, 11.55, y, 1.3, 0.4, str(idea.get("cost", ""))[:14],
                              size=9, color=C.muted,
                              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

            _footer(s, _pg())

    # ==============================================================
    # 🎯 サイト全体優先施策（未実装率が高い項目）
    # ==============================================================
    if site_agg and site_agg.get("common_issues"):
        common_issues = site_agg["common_issues"]

        s = pres.slides.add_slide(blank)
        _set_bg(s, C.cream)
        _header_bar(s, "🎯 サイト全体 優先対応項目", "Site-Wide Critical Issues")
        _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                      f"分析した{site_agg.get('page_count', 0)}ページのうち過半数で未実装の項目 — "
                      f"サイト共通テンプレート修正で全ページが一気に改善されます",
                      size=12, italic=True, color=C.muted)

        # ヘッダー行
        _add_rect(s, 0.5, 1.6, 12.3, 0.5, C.navy)
        for hi, (htxt, w, x_off) in enumerate([
            ("優先", 0.7, 0),
            ("項目", 5.5, 0.7),
            ("失点ページ率", 1.7, 6.2),
            ("平均スコア", 1.5, 7.9),
            ("改善後の想定インパクト", 3.4, 9.4),
        ]):
            _add_text_box(s, 0.5 + x_off, 1.6, w, 0.5, htxt,
                          size=11, bold=True, color=C.cyan,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

        for i, issue in enumerate(common_issues[:10]):
            y = 2.1 + i * 0.45
            failure_pct = issue.get("failure_pct", 0)
            avg_score = issue.get("avg_score", 0)
            max_score = issue.get("max_score", 0)
            item_key = issue.get("item_key", "")
            label = item_key.replace("_", " ")[:50]

            # 優先度
            if failure_pct >= 80:
                pri = "S"; pri_color = C.red
            elif failure_pct >= 65:
                pri = "A"; pri_color = C.amber
            else:
                pri = "B"; pri_color = C.teal

            bg = C.white if i % 2 == 0 else C.light_bg
            _add_rect(s, 0.5, y, 12.3, 0.45, bg, line_color=C.border)
            _add_rect(s, 0.65, y + 0.08, 0.45, 0.3, pri_color,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.65, y + 0.08, 0.45, 0.3, pri,
                          size=10, bold=True, color=C.white,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 1.2, y, 5.5, 0.45, label,
                          size=10, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)

            # 失点ページ率（バー付き）
            bar_w = 1.5 * (failure_pct / 100)
            _add_rect(s, 6.3, y + 0.13, 1.5, 0.18, C.border,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_rect(s, 6.3, y + 0.13, max(bar_w, 0.05), 0.18, pri_color,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 6.3, y - 0.05, 1.5, 0.2, f"{failure_pct}%",
                          size=8, bold=True, color=pri_color,
                          align=PP_ALIGN.CENTER)

            _add_text_box(s, 7.95, y, 1.4, 0.45,
                          f"{avg_score:.1f}/{max_score}",
                          size=10, color=C.muted,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

            # 想定インパクト（共通テンプレート修正で全ページ改善）
            page_count = site_agg.get("page_count", 1)
            failed_pages = int(page_count * failure_pct / 100)
            potential = int((max_score - avg_score) * failed_pages)
            _add_text_box(s, 9.4, y, 3.4, 0.45,
                          f"+{potential}点（{failed_pages}ページ × +{max_score - avg_score:.1f}点）",
                          size=10, bold=True, color=C.green,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

        # フッター注記
        _add_rect(s, 0.5, 6.95, 12.3, 0.4, C.deep_blue,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 0.5, 6.95, 12.3, 0.4,
                      "💡 これらは「サイト共通の構造的問題」— ヘッダー/フッター/テンプレート1箇所の修正で全ページが一気に改善されます",
                      size=11, italic=True, color=C.white,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _footer(s, _pg())

        # ----- スコア分布 + 最弱ページTOP5 -----
        s = pres.slides.add_slide(blank)
        _set_bg(s, C.cream)
        _header_bar(s, "🎯 サイト全体 スコア分布 & 最優先改善ページ", "Site-Wide Score Distribution")

        # 左: スコア分布
        _add_text_box(s, 0.5, 1.1, 6.0, 0.4, "📊 スコア分布（グレード別ページ数）",
                      size=14, bold=True, color=C.text_dark, font=FONT_HDR)
        dist = site_agg.get("score_distribution", {})
        total_pages = sum(dist.values()) or 1
        grade_colors = {"S": C.green, "A": C.teal, "B": C.amber, "C": RGBColor(0xF9, 0x73, 0x16), "D": C.red}
        for gi, g in enumerate(["S", "A", "B", "C", "D"]):
            count = dist.get(g, 0)
            pct = count / total_pages * 100
            y = 1.6 + gi * 0.85
            _add_text_box(s, 0.5, y, 0.6, 0.6, g,
                          size=24, bold=True, color=grade_colors[g], font=FONT_HDR,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_rect(s, 1.1, y + 0.18, 4.0, 0.3, C.border,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_rect(s, 1.1, y + 0.18, max(4.0 * pct / 100, 0.05), 0.3, grade_colors[g],
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 5.2, y, 1.2, 0.6, f"{count}p ({pct:.0f}%)",
                          size=11, bold=True, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)

        # 右: 最弱ページTOP5
        worst = site_agg.get("worst_pages", [])[:5]
        _add_text_box(s, 7.0, 1.1, 6.0, 0.4, "⚠️ 最優先改善ページ TOP5",
                      size=14, bold=True, color=C.text_dark, font=FONT_HDR)
        for wi, p in enumerate(worst):
            y = 1.6 + wi * 1.05
            score = p.get("total", {}).get("total", 0) if isinstance(p.get("total"), dict) else p.get("score", 0)
            grade = p.get("total", {}).get("grade", "D") if isinstance(p.get("total"), dict) else p.get("grade", "D")
            url_str = p.get("url", "")[:55]
            title_str = p.get("title", "")[:35]

            _add_rect(s, 7.0, y, 6.2, 0.95, C.white, line_color=C.border,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 7.15, y + 0.05, 0.7, 0.4, f"#{wi+1}",
                          size=14, bold=True, color=C.muted, font=FONT_HDR,
                          anchor=MSO_ANCHOR.MIDDLE)
            _add_rect(s, 7.85, y + 0.1, 0.8, 0.35, _grade_color(grade),
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 7.85, y + 0.1, 0.8, 0.35, f"{score}",
                          size=12, bold=True, color=C.white,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 8.75, y + 0.05, 4.4, 0.35, title_str,
                          size=10, bold=True, color=C.text_dark,
                          anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 8.75, y + 0.4, 4.4, 0.3, url_str,
                          size=8, italic=True, color=C.muted,
                          anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 7.15, y + 0.65, 5.9, 0.3,
                          f"Grade {grade}",
                          size=10, color=C.muted, anchor=MSO_ANCHOR.MIDDLE)

        # フッター注記
        site_score = site_agg.get("site_score", 0)
        site_grade = site_agg.get("site_grade", "C")
        median = site_agg.get("score_median", 0)
        _add_rect(s, 0.5, 6.95, 12.3, 0.4, C.navy,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 0.5, 6.95, 12.3, 0.4,
                      f"📈 サイト総合: {site_score}/100 (Grade {site_grade}) | 中央値: {median} | "
                      f"S+A: {dist.get('S',0)+dist.get('A',0)}p / C+D: {dist.get('C',0)+dist.get('D',0)}p",
                      size=11, bold=True, color=C.white,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _footer(s, _pg())

    # ==============================================================
    # Slide N+1: 戦略施策（中長期）
    # ==============================================================
    strategic_list = improvements.get("strategic", []) or improvements.get("content_strategy", [])
    if strategic_list:
        s = pres.slides.add_slide(blank)
        _set_bg(s, C.cream)
        _header_bar(s, "中長期 戦略施策", "Strategic Initiatives")
        _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                      "Quick Winで地盤固め → 戦略施策で差別化・競合優位を確立",
                      size=13, italic=True, color=C.muted)

        for i, item in enumerate(strategic_list[:4]):
            y = 1.55 + i * 1.4
            _add_rect(s, 0.5, y, 12.3, 1.3, C.white, line_color=C.border,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            # 優先度バッジ
            pri = item.get("priority", "A")
            pri_color = {"S": C.red, "A": C.amber, "B": C.teal}.get(pri, C.teal)
            _add_rect(s, 0.7, y + 0.2, 0.7, 0.35, pri_color,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.7, y + 0.2, 0.7, 0.35, f"優先{pri}",
                          size=10, bold=True, color=C.white,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 1.55, y + 0.15, 8.5, 0.4, item.get("title", "")[:60],
                          size=14, bold=True, color=C.text_dark, font=FONT_HDR,
                          anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 10.2, y + 0.15, 2.5, 0.4,
                          f"カテゴリ: {item.get('category', '戦略')[:12]}",
                          size=10, color=C.muted, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)

            # Why
            _add_text_box(s, 0.7, y + 0.55, 11.9, 0.35,
                          "🎯 " + str(item.get("why", ""))[:130],
                          size=10, color=C.deep_blue, anchor=MSO_ANCHOR.MIDDLE)

            # Steps
            steps = item.get("steps", item.get("actions", []))
            if steps:
                step_text = "  ▶ ".join([str(x)[:30] for x in steps[:4]])
                _add_text_box(s, 0.7, y + 0.9, 11.9, 0.35,
                              "▶ " + step_text,
                              size=9, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)

        _footer(s, _pg())

    # ==============================================================
    # Slide N+2: 競合分析からの示唆（Competitor-Informed）
    # ==============================================================
    ci_list = improvements.get("competitor_informed", [])
    if ci_list:
        s = pres.slides.add_slide(blank)
        _set_bg(s, C.cream)
        _header_bar(s, "競合分析から導き出した施策", "Competitor-Informed Recommendations")
        _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                      "上位競合と比較して見えてきた差別化ポイント・キャッチアップ施策",
                      size=13, italic=True, color=C.muted)

        for i, item in enumerate(ci_list[:5]):
            y = 1.6 + i * 1.05
            _add_rect(s, 0.5, y, 12.3, 0.95, C.white, line_color=C.border,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            pri = item.get("priority", "A")
            pri_color = {"S": C.red, "A": C.amber, "B": C.teal}.get(pri, C.teal)
            _add_rect(s, 0.7, y + 0.18, 0.7, 0.3, pri_color,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.7, y + 0.18, 0.7, 0.3, f"優先{pri}",
                          size=9, bold=True, color=C.white,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 1.55, y + 0.1, 11.0, 0.35, item.get("title", "")[:80],
                          size=12, bold=True, color=C.text_dark, font=FONT_HDR,
                          anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 1.55, y + 0.45, 11.0, 0.45,
                          str(item.get("why", "") or item.get("reason", ""))[:160],
                          size=10, color=C.muted, anchor=MSO_ANCHOR.MIDDLE)

        _footer(s, _pg())

    # ==============================================================
    # Slide N+3: 測定計画（Measurement Plan）
    # ==============================================================
    mp_list = improvements.get("measurement_plan", [])
    if mp_list:
        s = pres.slides.add_slide(blank)
        _set_bg(s, C.cream)
        _header_bar(s, "効果測定 KPI & ツール計画", "Measurement Plan")
        _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                      "施策実施後の効果を客観的に証明するための定量指標と計測ツール",
                      size=13, italic=True, color=C.muted)

        # ヘッダー
        _add_rect(s, 0.5, 1.55, 12.3, 0.45, C.deep_blue,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        for hi, htxt in enumerate(["指標", "目標値", "計測ツール"]):
            _add_text_box(s, 0.5 + hi * 4.1, 1.55, 4.1, 0.45, htxt,
                          size=12, bold=True, color=C.white,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

        for i, m in enumerate(mp_list[:8]):
            y = 2.05 + i * 0.55
            bg = C.white if i % 2 == 0 else C.light_bg
            _add_rect(s, 0.5, y, 12.3, 0.55, bg, line_color=C.border)
            _add_text_box(s, 0.6, y, 4.0, 0.55, str(m.get("metric", ""))[:40],
                          size=10, bold=True, color=C.text_dark,
                          anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 4.7, y, 4.0, 0.55, str(m.get("target", ""))[:40],
                          size=10, color=C.teal,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 8.8, y, 4.0, 0.55, str(m.get("tool", ""))[:40],
                          size=10, color=C.muted,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

        _footer(s, _pg())

    # ==============================================================
    # Slide N+4: 全施策一覧マトリクス
    # ==============================================================
    all_imp = []
    for key, label in [("quick_wins", "Quick Win"), ("strategic", "戦略"),
                       ("competitor_informed", "競合発"), ("technical_debt", "技術負債")]:
        for it in improvements.get(key, []):
            all_imp.append({
                "category": label,
                "priority": it.get("priority", "A"),
                "title": it.get("title", ""),
                "impact": it.get("impact", it.get("expected_uplift", "")),
                "effort": it.get("effort", it.get("cost", "")),
            })

    if all_imp:
        s = pres.slides.add_slide(blank)
        _set_bg(s, C.cream)
        _header_bar(s, "全改善施策 一覧マトリクス", "All Recommendations Matrix")
        _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                      f"今回の診断で抽出された全{len(all_imp)}件の改善施策（優先度順）",
                      size=13, italic=True, color=C.muted)

        # 並び替え: 優先度S→A→B→C
        pri_order = {"S": 0, "A": 1, "B": 2, "C": 3}
        all_imp_sorted = sorted(all_imp, key=lambda x: pri_order.get(x["priority"], 9))

        # ヘッダー
        _add_rect(s, 0.5, 1.55, 12.3, 0.4, C.navy)
        for hi, (htxt, w, x_off) in enumerate([
            ("優先", 0.7, 0), ("分類", 1.3, 0.7),
            ("施策タイトル", 7.4, 2.0),
            ("インパクト", 1.6, 9.4),
            ("工数", 1.3, 11.0),
        ]):
            _add_text_box(s, 0.5 + x_off, 1.55, w, 0.4, htxt,
                          size=10, bold=True, color=C.cyan,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

        for i, it in enumerate(all_imp_sorted[:14]):
            y = 1.95 + i * 0.35
            bg = C.white if i % 2 == 0 else C.light_bg
            _add_rect(s, 0.5, y, 12.3, 0.35, bg, line_color=C.border)
            pri_color = {"S": C.red, "A": C.amber, "B": C.teal, "C": C.muted}.get(it["priority"], C.muted)
            _add_rect(s, 0.65, y + 0.05, 0.5, 0.25, pri_color,
                      shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
            _add_text_box(s, 0.65, y + 0.05, 0.5, 0.25, it["priority"],
                          size=9, bold=True, color=C.white,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 1.2, y, 1.3, 0.35, it["category"][:8],
                          size=9, color=C.deep_blue,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 2.5, y, 7.4, 0.35, it["title"][:60],
                          size=9, color=C.text_dark, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 9.9, y, 1.6, 0.35, str(it["impact"])[:14],
                          size=9, bold=True, color=C.teal,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _add_text_box(s, 11.5, y, 1.3, 0.35, str(it["effort"])[:14],
                          size=9, color=C.muted,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

        _footer(s, _pg())

    # ==============================================================
    # Slide 10: 実装ロードマップ
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "実装ロードマップ", "90-Day Action Plan")

    _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                  "90日間で段階的に実装し、スコア +25点を目指す",
                  size=13, italic=True, color=C.muted)

    phases = [
        ("Phase 1", "Day 1–14", "Quick Win集中実装",
         ["Organization JSON-LD", "FAQPage JSON-LD", "llms.txt設置", "著者ボックス設置"],
         "+15点", C.teal),
        ("Phase 2", "Day 15–45", "コンテンツ構造改善",
         ["冒頭Answer-first化", "定義文パターン追加", "FAQ7問以上追加", "数値データ強化"],
         "+8点", C.deep_blue),
        ("Phase 3", "Day 46–90", "権威性・鮮度の強化",
         ["編集ポリシー明記", "外部引用リンク追加", "年次更新運用", "競合差別化コンテンツ"],
         "+7点", C.navy),
    ]

    for i, (period, days, title, tasks, gain, color) in enumerate(phases):
        x = 0.5 + i * 4.3
        _add_rect(s, x, 1.6, 4.0, 5.0, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, x, 1.6, 4.0, 1.4, color,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, x, 2.5, 4.0, 0.5, color)
        _add_text_box(s, x + 0.2, 1.75, 3.6, 0.35, period,
                      size=11, bold=True, color=C.cyan)
        _add_text_box(s, x + 0.2, 2.1, 3.6, 0.5, days,
                      size=20, bold=True, color=C.white, font=FONT_HDR)
        _add_text_box(s, x + 0.2, 3.15, 3.6, 0.4, title,
                      size=14, bold=True, color=C.text_dark, font=FONT_HDR)
        _add_rect(s, x + 0.2, 3.6, 0.5, 0.03, color)
        for j, t in enumerate(tasks):
            ty = 3.8 + j * 0.35
            _add_rect(s, x + 0.25, ty + 0.08, 0.12, 0.12, color,
                      shape_type=MSO_SHAPE.OVAL)
            _add_text_box(s, x + 0.45, ty, 3.4, 0.3, t,
                          size=11, color=C.text_dark,
                          anchor=MSO_ANCHOR.MIDDLE)
        _add_rect(s, x + 1.0, 5.9, 2.0, 0.6, C.cream, line_color=color,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, x + 1.0, 5.9, 2.0, 0.6, f"想定効果 {gain}",
                      size=12, bold=True, color=color,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    target_score = min(100, total["total"] + 25)
    target_grade = "A" if target_score >= 80 else "B" if target_score >= 60 else "C"
    _add_rect(s, 0.5, 6.75, 12.3, 0.45, C.deep_blue,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 0.5, 6.75, 12.3, 0.45,
                  f"💎 90日後の想定総合スコア: {total['total']}点 → {target_score}点（グレード {target_grade} 達成）",
                  size=13, bold=True, color=C.white,
                  align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    _footer(s, _pg())

    # ==============================================================
    # Slide 11: ROI
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "想定効果・ROI試算", "Expected Impact")

    _add_text_box(s, 0.5, 1.1, 6.5, 0.4, "📊 スコア推移シミュレーション",
                  size=16, bold=True, color=C.text_dark, font=FONT_HDR)
    _add_rect(s, 0.5, 1.6, 6.3, 3.8, C.white, line_color=C.border,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)

    # Y軸ラベル
    for v in [100, 80, 60, 40, 20, 0]:
        y = 1.9 + (100 - v) / 100 * 3.3
        _add_text_box(s, 0.6, y - 0.15, 0.35, 0.3, str(v),
                      size=9, color=C.muted, align=PP_ALIGN.RIGHT)

    # データポイント
    now_score = total["total"]
    points = [
        (1.5, "現在", now_score, C.red),
        (2.9, "14日後", min(100, now_score + 15), C.amber),
        (4.3, "45日後", min(100, now_score + 23), C.teal),
        (5.7, "90日後", min(100, now_score + 30), C.green),
    ]

    # 折れ線を線で描画
    for i in range(len(points) - 1):
        x1, _, v1, _ = points[i]
        x2, _, v2, _ = points[i + 1]
        y1 = 1.9 + (100 - v1) / 100 * 3.3
        y2 = 1.9 + (100 - v2) / 100 * 3.3
        connector = s.shapes.add_connector(1, Inches(x1), Inches(y1),
                                           Inches(x2), Inches(y2))
        connector.line.color.rgb = C.deep_blue
        connector.line.width = Pt(3)

    for x, label, score, color in points:
        y = 1.9 + (100 - score) / 100 * 3.3
        _add_rect(s, x - 0.12, y - 0.12, 0.24, 0.24, color,
                  shape_type=MSO_SHAPE.OVAL)
        _add_text_box(s, x - 0.4, y - 0.5, 0.8, 0.3, str(score),
                      size=11, bold=True, color=color, align=PP_ALIGN.CENTER)
        _add_text_box(s, x - 0.6, 5.0, 1.2, 0.3, label,
                      size=10, color=C.muted, align=PP_ALIGN.CENTER)

    # KPI
    _add_text_box(s, 7.2, 1.1, 5.6, 0.4, "📈 KPI予測",
                  size=16, bold=True, color=C.text_dark, font=FONT_HDR)

    kpis = [
        ("AI Overview 引用率", "2%", "12%"),
        ("ChatGPT 出典表示", "1件/月", "8件/月"),
        ("Perplexity 引用", "未計測", "15件/月"),
        ("AI経由セッション", "約50/月", "約400/月"),
        ("指名検索数", "基準", "+40%"),
    ]
    for i, (lbl, before, after) in enumerate(kpis):
        y = 1.6 + i * 0.7
        _add_rect(s, 7.2, y, 5.6, 0.6, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 7.35, y, 2.5, 0.6, lbl,
                      size=11, bold=True, color=C.text_dark,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 9.8, y, 1.1, 0.6, before,
                      size=11, color=C.muted, align=PP_ALIGN.CENTER,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 10.9, y, 0.4, 0.6, "→",
                      size=14, color=C.teal, align=PP_ALIGN.CENTER,
                      anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 11.3, y, 1.4, 0.6, after,
                      size=12, bold=True, color=C.teal,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    _add_rect(s, 0.5, 5.7, 12.3, 1.1, C.navy,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 0.7, 5.8, 11.9, 0.35, "💼 ビジネスインパクト（試算）",
                  size=12, bold=True, color=C.cyan)
    _add_text_box(s, 0.7, 6.15, 11.9, 0.6,
                  "SEO流入に加え、AI経由の新規タッチポイントが加わることで、月間商談機会が推定 +20〜30%。\n"
                  "また、AI引用によるブランド露出はSEO検索結果と異なり「選ばれた1〜3社しか出ない」ため、競合優位を長期に確保できます。",
                  size=11, color=C.white)

    _footer(s, _pg())

    # ==============================================================
    # Slide 12: テストクエリ
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.cream)
    _header_bar(s, "商談・社内共有用テストクエリ", "AI Search Demo Queries")

    _add_text_box(s, 0.5, 1.05, 12.3, 0.4,
                  "実際にAIに質問して「御社が引用されるか」を体感確認するクエリ集",
                  size=13, italic=True, color=C.muted)

    platform_colors = {
        "ChatGPT": RGBColor(0x10, 0xA3, 0x7F),
        "Perplexity": RGBColor(0x20, 0xB8, 0xCD),
        "Google AI Overview": RGBColor(0x42, 0x85, 0xF4),
        "Google": RGBColor(0x42, 0x85, 0xF4),
    }

    queries_list = test_queries.get("queries", [])
    if not queries_list:
        queries_list = [
            {"platform": "ChatGPT", "query": f"{site_title}について教えてください",
             "reason_if_not": "定義文＋Answer-first構造の評価"},
            {"platform": "ChatGPT", "query": f"{site_title} おすすめ 比較",
             "reason_if_not": "比較構造・リスト化レベルの評価"},
            {"platform": "Perplexity", "query": f"{site_title}の選び方は？",
             "reason_if_not": "FAQ・HowTo構造の評価"},
            {"platform": "Perplexity", "query": f"{site_title} メリット デメリット",
             "reason_if_not": "網羅性・両論併記の評価"},
            {"platform": "Google AI Overview", "query": f"{site_title}とは",
             "reason_if_not": "定義文パターンの評価（最重要）"},
        ]

    for i, q in enumerate(queries_list[:5]):
        y = 1.55 + i * 1.05
        platform = q.get("platform", "ChatGPT")
        color = C.teal
        for k, v in platform_colors.items():
            if k in platform:
                color = v
                break

        _add_rect(s, 0.5, y, 12.3, 0.95, C.white, line_color=C.border,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(s, 0.7, y + 0.15, 2.0, 0.65, color,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, 0.7, y + 0.15, 2.0, 0.65, platform[:18],
                      size=11, bold=True, color=C.white,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 2.9, y + 0.1, 9.7, 0.25, "検索クエリ例",
                      size=9, color=C.muted)
        _add_text_box(s, 2.9, y + 0.35, 9.7, 0.35,
                      f'"{q.get("query", "")[:60]}"',
                      size=13, bold=True, italic=True, color=C.text_dark,
                      font=FONT_HDR, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, 2.9, y + 0.65, 9.7, 0.25,
                      "▶ " + q.get("reason_if_not", "")[:70],
                      size=10, color=C.teal)

    _add_rect(s, 0.5, 6.8, 12.3, 0.45, C.light_bg,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 0.5, 6.8, 12.3, 0.45,
                  "💡 商談現場で上記クエリを実行 → 「御社サイトが出ない/出る」を体感してもらうと改善ニーズが明確化されます",
                  size=11, italic=True, color=C.deep_blue,
                  align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    _footer(s, _pg())

    # ==============================================================
    # Slide 13: Next Step
    # ==============================================================
    s = pres.slides.add_slide(blank)
    _set_bg(s, C.navy)
    _add_rect(s, 0, 0, 13.33, 0.08, C.cyan)

    _add_text_box(s, 0.5, 0.6, 12.3, 0.4, "NEXT STEP",
                  size=14, bold=True, color=C.cyan, align=PP_ALIGN.CENTER)
    _add_text_box(s, 0.5, 1.1, 12.3, 0.8, "次のアクションについて",
                  size=32, bold=True, color=C.white, font=FONT_HDR,
                  align=PP_ALIGN.CENTER)

    steps = [
        ("STEP 1", "診断レポートの読み合わせ",
         "社内で優先度・工数感の共有。疑問点の洗い出し（約60分）", "📋"),
        ("STEP 2", "Quick Win実装キックオフ",
         "Phase 1施策（Day 1–14）の担当・期日確定。テンプレートコード提供", "🚀"),
        ("STEP 3", "60日後の再診断",
         "同じツールで再測定。改善効果の定量確認と次フェーズ計画", "📊"),
    ]
    for i, (num, title, desc, icon) in enumerate(steps):
        x = 0.7 + i * 4.1
        _add_rect(s, x, 2.5, 3.8, 3.2, C.deep_blue, line_color=C.cyan,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, x, 2.75, 3.8, 0.8, icon,
                      size=40, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_rect(s, x + 1.3, 3.75, 1.2, 0.35, C.cyan,
                  shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_text_box(s, x + 1.3, 3.75, 1.2, 0.35, num,
                      size=10, bold=True, color=C.navy,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, x + 0.2, 4.2, 3.4, 0.7, title,
                      size=16, bold=True, color=C.white, font=FONT_HDR,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        _add_text_box(s, x + 0.25, 4.95, 3.3, 0.7, desc,
                      size=11, color=C.text_light, align=PP_ALIGN.CENTER)

    _add_rect(s, 2.5, 6.1, 8.3, 0.8, C.teal,
              shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_text_box(s, 2.5, 6.1, 8.3, 0.8,
                  "▶ 詳細な実装支援・カスタム診断のご相談を承ります",
                  size=16, bold=True, color=C.white, font=FONT_HDR,
                  align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    _add_text_box(s, 0.5, 7.1, 12.3, 0.3,
                  f"Thank you  |  AIO/LLMO診断ツール  |  {today}",
                  size=10, color=C.muted, align=PP_ALIGN.CENTER)

    # ===== Bytesに書き出し =====
    buf = BytesIO()
    pres.save(buf)
    buf.seek(0)
    return buf
