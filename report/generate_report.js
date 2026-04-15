// AIO/LLMO 診断レポート — クライアント提出用スライド生成
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 inches
pres.title = "AIO/LLMO 総合診断レポート";
pres.company = "AIO/LLMO診断ツール";

// ===== カラーパレット（Ocean Gradient） =====
const C = {
  navy: "0A1628",         // 主背景
  deepBlue: "065A82",     // 主テーマ
  teal: "0D9488",         // アクセント
  cyan: "14B8A6",         // ハイライト
  cream: "F8FAFC",        // 明るい背景
  lightBg: "F1F5F9",      // カード背景
  textDark: "1E293B",     // 本文（暗色上）
  textLight: "E2E8F0",    // 本文（明色上）
  muted: "64748B",         // 補助テキスト
  white: "FFFFFF",
  green: "10B981",
  amber: "F59E0B",
  red: "EF4444",
  border: "CBD5E1",
};

const FONT = { header: "Georgia", body: "Calibri" };

// ===== 共通ヘルパー =====
function addHeaderBar(slide, title, subtitle = "") {
  slide.addShape("rect", {
    x: 0, y: 0, w: 13.33, h: 0.7,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  slide.addShape("rect", {
    x: 0, y: 0.7, w: 13.33, h: 0.04,
    fill: { color: C.teal }, line: { color: C.teal },
  });
  slide.addText(title, {
    x: 0.5, y: 0.1, w: 9, h: 0.5,
    fontFace: FONT.header, fontSize: 18, bold: true,
    color: C.white, align: "left", valign: "middle",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 9.5, y: 0.1, w: 3.5, h: 0.5,
      fontFace: FONT.body, fontSize: 11,
      color: C.cyan, align: "right", valign: "middle",
    });
  }
}

function addFooter(slide, pageNum) {
  slide.addText(`AIO/LLMO診断レポート  |  ${pageNum}`, {
    x: 0.5, y: 7.2, w: 12.3, h: 0.25,
    fontFace: FONT.body, fontSize: 9,
    color: C.muted, align: "right",
  });
}

// ====================================================================
// Slide 1: タイトル
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // 左半分の装飾グラデーション風
  s.addShape("rect", {
    x: 0, y: 0, w: 5.5, h: 7.5,
    fill: { color: C.deepBlue }, line: { color: C.deepBlue },
  });
  s.addShape("rect", {
    x: 5.3, y: 0, w: 0.05, h: 7.5,
    fill: { color: C.cyan }, line: { color: C.cyan },
  });

  // ロゴ風サークル
  s.addShape("ellipse", {
    x: 1.2, y: 1.0, w: 1.4, h: 1.4,
    fill: { color: C.cyan }, line: { color: C.cyan },
  });
  s.addText("AIO", {
    x: 1.2, y: 1.0, w: 1.4, h: 1.4,
    fontFace: FONT.header, fontSize: 32, bold: true,
    color: C.navy, align: "center", valign: "middle",
  });

  s.addText("2026", {
    x: 1.0, y: 3.0, w: 4.3, h: 0.3,
    fontFace: FONT.body, fontSize: 12, bold: true,
    color: C.cyan, align: "left", charSpacing: 8,
  });

  s.addText("AIO / LLMO\n総合診断レポート", {
    x: 1.0, y: 3.4, w: 4.3, h: 1.8,
    fontFace: FONT.header, fontSize: 36, bold: true,
    color: C.white, align: "left",
  });

  s.addShape("rect", {
    x: 1.0, y: 5.3, w: 0.6, h: 0.06,
    fill: { color: C.cyan }, line: { color: C.cyan },
  });
  s.addText("AI Overview & LLM Optimization\nAssessment Report", {
    x: 1.0, y: 5.45, w: 4.3, h: 0.8,
    fontFace: FONT.body, fontSize: 13, italic: true,
    color: C.textLight, align: "left",
  });

  // 右サイド
  s.addText("AI検索時代の", {
    x: 6.2, y: 1.5, w: 6.5, h: 0.5,
    fontFace: FONT.body, fontSize: 16,
    color: C.cyan, align: "left",
  });
  s.addText("サイト最適化診断", {
    x: 6.2, y: 2.0, w: 6.5, h: 0.8,
    fontFace: FONT.header, fontSize: 32, bold: true,
    color: C.white, align: "left",
  });

  const bullets = [
    "6カテゴリ × 30項目の実測診断",
    "競合ベンチマーク & ギャップ分析",
    "優先度別の改善アクションプラン",
    "商談・社内共有に使える完全版レポート",
  ];
  bullets.forEach((b, i) => {
    const y = 3.3 + i * 0.5;
    s.addShape("ellipse", {
      x: 6.2, y: y + 0.08, w: 0.2, h: 0.2,
      fill: { color: C.cyan }, line: { color: C.cyan },
    });
    s.addText(b, {
      x: 6.55, y: y, w: 6, h: 0.4,
      fontFace: FONT.body, fontSize: 15,
      color: C.textLight, align: "left", valign: "middle",
    });
  });

  s.addText("診断日: 2026年4月14日", {
    x: 6.2, y: 6.7, w: 6.5, h: 0.3,
    fontFace: FONT.body, fontSize: 11,
    color: C.muted, align: "left",
  });
}

// ====================================================================
// Slide 2: エグゼクティブサマリー
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "エグゼクティブサマリー", "Executive Summary");

  // 左: スコアカード
  s.addShape("roundRect", {
    x: 0.5, y: 1.1, w: 4.3, h: 5.8,
    fill: { color: C.navy }, line: { color: C.navy },
    rectRadius: 0.1,
  });
  s.addText("総合スコア", {
    x: 0.5, y: 1.4, w: 4.3, h: 0.4,
    fontFace: FONT.body, fontSize: 14,
    color: C.cyan, align: "center",
  });
  s.addText("62", {
    x: 0.5, y: 1.85, w: 4.3, h: 2.0,
    fontFace: FONT.header, fontSize: 110, bold: true,
    color: C.white, align: "center",
  });
  s.addText("/ 100", {
    x: 0.5, y: 3.8, w: 4.3, h: 0.4,
    fontFace: FONT.body, fontSize: 18,
    color: C.textLight, align: "center",
  });
  s.addShape("roundRect", {
    x: 1.65, y: 4.4, w: 2.0, h: 0.7,
    fill: { color: C.teal }, line: { color: C.teal },
    rectRadius: 0.08,
  });
  s.addText("グレード B", {
    x: 1.65, y: 4.4, w: 2.0, h: 0.7,
    fontFace: FONT.header, fontSize: 22, bold: true,
    color: C.white, align: "center", valign: "middle",
  });
  s.addText("基本対応あり\n重点改善で大幅効果が見込める", {
    x: 0.7, y: 5.4, w: 3.9, h: 0.9,
    fontFace: FONT.body, fontSize: 12, italic: true,
    color: C.textLight, align: "center",
  });

  // 右: カテゴリ別ハイライト
  const cats = [
    { label: "コンテンツ品質",  score: 13, max: 20, color: C.teal },
    { label: "構造化データ",    score: 10, max: 20, color: C.amber },
    { label: "E-E-A-Tシグナル", score: 11, max: 20, color: C.amber },
    { label: "AI引用可能性",   score: 14, max: 20, color: C.teal },
    { label: "コンテンツ鮮度",  score: 7,  max: 10, color: C.teal },
    { label: "テクニカルAIO/UX", score: 7,  max: 10, color: C.teal },
  ];

  s.addText("カテゴリ別スコア", {
    x: 5.2, y: 1.15, w: 7.5, h: 0.4,
    fontFace: FONT.header, fontSize: 18, bold: true,
    color: C.textDark, align: "left",
  });

  cats.forEach((c, i) => {
    const y = 1.75 + i * 0.82;
    const pct = c.score / c.max;
    s.addText(c.label, {
      x: 5.2, y: y, w: 3.0, h: 0.35,
      fontFace: FONT.body, fontSize: 13, bold: true,
      color: C.textDark, align: "left", valign: "middle",
    });
    // バー背景
    s.addShape("roundRect", {
      x: 8.3, y: y + 0.08, w: 3.5, h: 0.22,
      fill: { color: C.border }, line: { color: C.border },
      rectRadius: 0.03,
    });
    // バー本体
    s.addShape("roundRect", {
      x: 8.3, y: y + 0.08, w: 3.5 * pct, h: 0.22,
      fill: { color: c.color }, line: { color: c.color },
      rectRadius: 0.03,
    });
    s.addText(`${c.score}/${c.max}`, {
      x: 11.9, y: y, w: 0.9, h: 0.35,
      fontFace: FONT.body, fontSize: 12, bold: true,
      color: C.textDark, align: "right", valign: "middle",
    });
  });

  addFooter(s, "02");
}

// ====================================================================
// Slide 3: なぜ今AIO/LLMOなのか
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "なぜ今、AIO/LLMO対策なのか", "The Shift to AI Search");

  s.addText("AI検索の普及で「検索→クリック」の時代は終わった", {
    x: 0.5, y: 1.0, w: 12.3, h: 0.5,
    fontFace: FONT.header, fontSize: 20, bold: true,
    color: C.deepBlue, align: "left",
  });

  // 大きな数字カード x3
  const stats = [
    { num: "58%", label: "Google検索でAI Overviewが表示", sub: "日本では2024年8月〜本格展開" },
    { num: "3.2B", label: "ChatGPT月間アクセス数", sub: "既にGoogle検索の約1/3規模" },
    { num: "-35%", label: "AI Overview表示時のCTR下落", sub: "従来SEOだけでは機会損失" },
  ];
  stats.forEach((st, i) => {
    const x = 0.5 + i * 4.3;
    s.addShape("roundRect", {
      x, y: 1.8, w: 4.0, h: 2.2,
      fill: { color: C.white }, line: { color: C.border, width: 1 },
      rectRadius: 0.08,
    });
    s.addShape("rect", {
      x, y: 1.8, w: 0.1, h: 2.2,
      fill: { color: C.teal }, line: { color: C.teal },
    });
    s.addText(st.num, {
      x: x + 0.2, y: 1.95, w: 3.8, h: 1.0,
      fontFace: FONT.header, fontSize: 48, bold: true,
      color: C.deepBlue, align: "left", valign: "middle",
    });
    s.addText(st.label, {
      x: x + 0.2, y: 2.95, w: 3.8, h: 0.5,
      fontFace: FONT.body, fontSize: 13, bold: true,
      color: C.textDark, align: "left",
    });
    s.addText(st.sub, {
      x: x + 0.2, y: 3.45, w: 3.8, h: 0.4,
      fontFace: FONT.body, fontSize: 10, italic: true,
      color: C.muted, align: "left",
    });
  });

  // 下段: 2カラム問題提起
  s.addShape("roundRect", {
    x: 0.5, y: 4.4, w: 6.1, h: 2.4,
    fill: { color: C.navy }, line: { color: C.navy },
    rectRadius: 0.08,
  });
  s.addText("❌ 何もしない場合", {
    x: 0.7, y: 4.55, w: 5.7, h: 0.4,
    fontFace: FONT.body, fontSize: 14, bold: true,
    color: C.red, align: "left",
  });
  const bad = [
    "AI検索結果に一切表示されず機会損失",
    "競合がAI引用を獲得、相対順位が下落",
    "SEO投資のROIが年々低下",
    "商談・採用での情報露出が減少",
  ];
  bad.forEach((b, i) => {
    s.addText("• " + b, {
      x: 0.8, y: 5.0 + i * 0.4, w: 5.6, h: 0.35,
      fontFace: FONT.body, fontSize: 12,
      color: C.textLight, align: "left",
    });
  });

  s.addShape("roundRect", {
    x: 6.8, y: 4.4, w: 6.0, h: 2.4,
    fill: { color: C.teal }, line: { color: C.teal },
    rectRadius: 0.08,
  });
  s.addText("✅ 早期対策の効果", {
    x: 7.0, y: 4.55, w: 5.6, h: 0.4,
    fontFace: FONT.body, fontSize: 14, bold: true,
    color: C.white, align: "left",
  });
  const good = [
    "AI Overviewでの引用率が平均3〜5倍向上",
    "Perplexity / ChatGPTでの出典表示獲得",
    "ブランド第一想起（エンティティ認識）を確立",
    "SEOとAIOの相乗効果で検索総流入増",
  ];
  good.forEach((b, i) => {
    s.addText("• " + b, {
      x: 7.1, y: 5.0 + i * 0.4, w: 5.5, h: 0.35,
      fontFace: FONT.body, fontSize: 12,
      color: C.white, align: "left",
    });
  });

  addFooter(s, "03");
}

// ====================================================================
// Slide 4: 診断フレームワーク
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "診断フレームワーク", "6 Categories × 30 Items");

  s.addText("AI検索時代に必要な6つの評価軸で、30項目を実測診断", {
    x: 0.5, y: 1.0, w: 12.3, h: 0.4,
    fontFace: FONT.body, fontSize: 14,
    color: C.muted, align: "left",
  });

  const framework = [
    { num: "01", label: "コンテンツ品質・構造", pts: "20点", items: "Answer-first, 見出し階層, FAQ, 明瞭性", color: C.deepBlue },
    { num: "02", label: "構造化データ",         pts: "20点", items: "Organization, Article, FAQPage, Breadcrumb", color: C.teal },
    { num: "03", label: "E-E-A-Tシグナル",      pts: "20点", items: "著者情報, 運営者, 引用, 編集ポリシー",       color: C.cyan },
    { num: "04", label: "AI引用可能性",         pts: "20点", items: "定義文, 数値データ, 独自情報, エンティティ",  color: C.deepBlue },
    { num: "05", label: "コンテンツ鮮度",       pts: "10点", items: "更新日表示, dateModified, 年次管理",         color: C.teal },
    { num: "06", label: "テクニカルAIO/UX",     pts: "10点", items: "AIクローラー, PageSpeed, canonical, sitemap", color: C.cyan },
  ];

  framework.forEach((f, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.5 + col * 4.3;
    const y = 1.6 + row * 2.6;

    s.addShape("roundRect", {
      x, y, w: 4.0, h: 2.4,
      fill: { color: C.white }, line: { color: C.border, width: 1 },
      rectRadius: 0.1,
    });
    // 番号サークル
    s.addShape("ellipse", {
      x: x + 0.2, y: y + 0.2, w: 0.8, h: 0.8,
      fill: { color: f.color }, line: { color: f.color },
    });
    s.addText(f.num, {
      x: x + 0.2, y: y + 0.2, w: 0.8, h: 0.8,
      fontFace: FONT.header, fontSize: 16, bold: true,
      color: C.white, align: "center", valign: "middle",
    });
    // 配点バッジ
    s.addShape("roundRect", {
      x: x + 2.9, y: y + 0.3, w: 1.0, h: 0.4,
      fill: { color: C.lightBg }, line: { color: C.lightBg },
      rectRadius: 0.05,
    });
    s.addText(f.pts, {
      x: x + 2.9, y: y + 0.3, w: 1.0, h: 0.4,
      fontFace: FONT.body, fontSize: 11, bold: true,
      color: C.deepBlue, align: "center", valign: "middle",
    });
    s.addText(f.label, {
      x: x + 0.2, y: y + 1.1, w: 3.7, h: 0.5,
      fontFace: FONT.header, fontSize: 16, bold: true,
      color: C.textDark, align: "left",
    });
    s.addShape("rect", {
      x: x + 0.2, y: y + 1.62, w: 0.5, h: 0.03,
      fill: { color: f.color }, line: { color: f.color },
    });
    s.addText(f.items, {
      x: x + 0.2, y: y + 1.75, w: 3.7, h: 0.6,
      fontFace: FONT.body, fontSize: 10.5,
      color: C.muted, align: "left",
    });
  });

  addFooter(s, "04");
}

// ====================================================================
// Slide 5: カテゴリ別診断結果（詳細）
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "カテゴリ別診断結果", "Category Breakdown");

  const rows = [
    { cat: "コンテンツ品質",    score: "13/20", status: "B", note: "冒頭結論OK・FAQ不足", color: C.amber },
    { cat: "構造化データ",      score: "10/20", status: "C", note: "Organization未実装",    color: C.red },
    { cat: "E-E-A-Tシグナル",   score: "11/20", status: "C", note: "著者情報・引用が弱い",   color: C.red },
    { cat: "AI引用可能性",      score: "14/20", status: "B", note: "定義文OK・数値不足",    color: C.amber },
    { cat: "コンテンツ鮮度",    score: "7/10",  status: "B", note: "更新日あり・年次管理△",  color: C.amber },
    { cat: "テクニカルAIO/UX",  score: "7/10",  status: "B", note: "AIクローラー全許可",    color: C.green },
  ];

  // ヘッダー行
  s.addShape("rect", {
    x: 0.5, y: 1.1, w: 12.3, h: 0.5,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  const hdrs = [
    { t: "カテゴリ",      x: 0.7,  w: 3.5 },
    { t: "スコア",        x: 4.2,  w: 1.5 },
    { t: "判定",          x: 5.7,  w: 1.0 },
    { t: "主な所見",      x: 6.7,  w: 4.0 },
    { t: "優先度",        x: 10.7, w: 2.0 },
  ];
  hdrs.forEach(h => {
    s.addText(h.t, {
      x: h.x, y: 1.1, w: h.w, h: 0.5,
      fontFace: FONT.body, fontSize: 12, bold: true,
      color: C.white, align: "left", valign: "middle",
    });
  });

  rows.forEach((r, i) => {
    const y = 1.6 + i * 0.55;
    if (i % 2 === 0) {
      s.addShape("rect", {
        x: 0.5, y, w: 12.3, h: 0.55,
        fill: { color: C.white }, line: { color: C.white },
      });
    }
    s.addText(r.cat, {
      x: 0.7, y, w: 3.5, h: 0.55,
      fontFace: FONT.body, fontSize: 13, bold: true,
      color: C.textDark, align: "left", valign: "middle",
    });
    s.addText(r.score, {
      x: 4.2, y, w: 1.5, h: 0.55,
      fontFace: FONT.header, fontSize: 15, bold: true,
      color: C.deepBlue, align: "left", valign: "middle",
    });
    s.addShape("roundRect", {
      x: 5.7, y: y + 0.1, w: 0.7, h: 0.35,
      fill: { color: r.color }, line: { color: r.color },
      rectRadius: 0.05,
    });
    s.addText(r.status, {
      x: 5.7, y: y + 0.1, w: 0.7, h: 0.35,
      fontFace: FONT.body, fontSize: 11, bold: true,
      color: C.white, align: "center", valign: "middle",
    });
    s.addText(r.note, {
      x: 6.7, y, w: 4.0, h: 0.55,
      fontFace: FONT.body, fontSize: 11,
      color: C.muted, align: "left", valign: "middle",
    });
    const priority = r.status === "C" ? "🔴 最優先" : r.status === "B" ? "🟡 要改善" : "🟢 維持";
    s.addText(priority, {
      x: 10.7, y, w: 2.0, h: 0.55,
      fontFace: FONT.body, fontSize: 11, bold: true,
      color: C.textDark, align: "left", valign: "middle",
    });
  });

  // 下部インサイト
  s.addShape("roundRect", {
    x: 0.5, y: 5.2, w: 12.3, h: 1.6,
    fill: { color: C.deepBlue }, line: { color: C.deepBlue },
    rectRadius: 0.08,
  });
  s.addText("💡 診断インサイト", {
    x: 0.8, y: 5.35, w: 11.7, h: 0.4,
    fontFace: FONT.body, fontSize: 13, bold: true,
    color: C.cyan, align: "left",
  });
  s.addText(
    "コンテンツの質自体は高水準。一方で「機械可読性（構造化データ）」と「信頼性シグナル（著者・引用）」が大きく欠けています。\n" +
    "この2領域は実装コストが低く、効果が大きい「クイックウィン領域」です。30日以内の改善で +15〜20点の向上が見込めます。",
    {
      x: 0.8, y: 5.75, w: 11.7, h: 1.0,
      fontFace: FONT.body, fontSize: 12,
      color: C.white, align: "left",
    }
  );

  addFooter(s, "05");
}

// ====================================================================
// Slide 6: テクニカル診断（AIクローラー）
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "テクニカル診断 — AIクローラー対応", "robots.txt / llms.txt / Performance");

  // 左: AIクローラー許可状況
  s.addText("🤖 AIクローラーのアクセス状況", {
    x: 0.5, y: 1.1, w: 6.5, h: 0.4,
    fontFace: FONT.header, fontSize: 16, bold: true,
    color: C.textDark, align: "left",
  });

  const crawlers = [
    { name: "GPTBot",         vendor: "OpenAI (ChatGPT)",   status: "許可", color: C.green },
    { name: "Google-Extended", vendor: "Google (Gemini)",    status: "許可", color: C.green },
    { name: "ClaudeBot",      vendor: "Anthropic (Claude)",  status: "許可", color: C.green },
    { name: "PerplexityBot",  vendor: "Perplexity",          status: "許可", color: C.green },
    { name: "CCBot",          vendor: "Common Crawl",        status: "許可", color: C.green },
    { name: "Bytespider",     vendor: "ByteDance (Doubao)",  status: "未設定", color: C.amber },
  ];

  crawlers.forEach((c, i) => {
    const y = 1.6 + i * 0.55;
    s.addShape("roundRect", {
      x: 0.5, y, w: 6.3, h: 0.5,
      fill: { color: C.white }, line: { color: C.border, width: 1 },
      rectRadius: 0.05,
    });
    s.addText(c.name, {
      x: 0.7, y, w: 2.0, h: 0.5,
      fontFace: FONT.body, fontSize: 12, bold: true,
      color: C.textDark, align: "left", valign: "middle",
    });
    s.addText(c.vendor, {
      x: 2.6, y, w: 2.5, h: 0.5,
      fontFace: FONT.body, fontSize: 10,
      color: C.muted, align: "left", valign: "middle",
    });
    s.addShape("roundRect", {
      x: 5.3, y: y + 0.1, w: 1.3, h: 0.3,
      fill: { color: c.color }, line: { color: c.color },
      rectRadius: 0.04,
    });
    s.addText(c.status, {
      x: 5.3, y: y + 0.1, w: 1.3, h: 0.3,
      fontFace: FONT.body, fontSize: 10, bold: true,
      color: C.white, align: "center", valign: "middle",
    });
  });

  // 右: 技術スコアカード
  s.addText("⚙️ テクニカルメトリクス", {
    x: 7.2, y: 1.1, w: 5.6, h: 0.4,
    fontFace: FONT.header, fontSize: 16, bold: true,
    color: C.textDark, align: "left",
  });

  const metrics = [
    { label: "PageSpeed",  value: "78", unit: "/100", note: "Good（80以上で Excellent）", color: C.amber },
    { label: "llms.txt",   value: "×",  unit: "",     note: "未設置 — 改善提案あり",       color: C.red },
    { label: "sitemap.xml", value: "○",  unit: "",     note: "42 URLs 登録済み",            color: C.green },
    { label: "canonical",  value: "○",  unit: "",     note: "全ページ実装",                 color: C.green },
    { label: "viewport",   value: "○",  unit: "",     note: "モバイル対応OK",               color: C.green },
  ];

  metrics.forEach((m, i) => {
    const y = 1.6 + i * 0.95;
    s.addShape("roundRect", {
      x: 7.2, y, w: 5.6, h: 0.85,
      fill: { color: C.white }, line: { color: C.border, width: 1 },
      rectRadius: 0.06,
    });
    s.addShape("rect", {
      x: 7.2, y, w: 0.08, h: 0.85,
      fill: { color: m.color }, line: { color: m.color },
    });
    s.addText(m.label, {
      x: 7.45, y: y + 0.1, w: 3.0, h: 0.35,
      fontFace: FONT.body, fontSize: 12, bold: true,
      color: C.textDark, align: "left",
    });
    s.addText(m.note, {
      x: 7.45, y: y + 0.45, w: 3.5, h: 0.35,
      fontFace: FONT.body, fontSize: 10,
      color: C.muted, align: "left",
    });
    s.addText(m.value + (m.unit || ""), {
      x: 10.8, y, w: 1.9, h: 0.85,
      fontFace: FONT.header, fontSize: 28, bold: true,
      color: m.color, align: "center", valign: "middle",
    });
  });

  addFooter(s, "06");
}

// ====================================================================
// Slide 7: 構造化データ診断
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "構造化データ（JSON-LD）実装状況", "Schema.org Coverage");

  s.addText("AIが正確に情報を読み取るための「機械可読ラベル」の実装状況", {
    x: 0.5, y: 1.05, w: 12.3, h: 0.4,
    fontFace: FONT.body, fontSize: 13, italic: true,
    color: C.muted, align: "left",
  });

  const schemas = [
    { type: "Organization",   status: "未実装", icon: "×", priority: "必須", impact: "運営者情報をAIに明示",               color: C.red },
    { type: "Article / BlogPosting", status: "実装済み", icon: "○", priority: "必須", impact: "記事メタデータ認識",           color: C.green },
    { type: "FAQPage",        status: "未実装", icon: "×", priority: "必須", impact: "AI Overview引用率が大幅アップ",        color: C.red },
    { type: "BreadcrumbList", status: "実装済み", icon: "○", priority: "推奨", impact: "検索結果パンくず表示",               color: C.green },
    { type: "LocalBusiness",  status: "該当外", icon: "—", priority: "条件", impact: "ローカルビジネスのみ必要",              color: C.muted },
    { type: "HowTo",          status: "未実装", icon: "×", priority: "推奨", impact: "手順コンテンツに有効",                 color: C.amber },
    { type: "Product",        status: "未実装", icon: "×", priority: "推奨", impact: "製品・サービスに有効",                 color: C.amber },
  ];

  // ヘッダー
  s.addShape("rect", {
    x: 0.5, y: 1.55, w: 12.3, h: 0.45,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  [
    { t: "スキーマタイプ", x: 0.8, w: 3.0 },
    { t: "状況",          x: 3.8, w: 1.3 },
    { t: "状態",          x: 5.1, w: 1.8 },
    { t: "優先度",        x: 6.9, w: 1.5 },
    { t: "AIへの効果",    x: 8.4, w: 4.3 },
  ].forEach(h => {
    s.addText(h.t, {
      x: h.x, y: 1.55, w: h.w, h: 0.45,
      fontFace: FONT.body, fontSize: 11, bold: true,
      color: C.white, align: "left", valign: "middle",
    });
  });

  schemas.forEach((sc, i) => {
    const y = 2.0 + i * 0.52;
    if (i % 2 === 0) {
      s.addShape("rect", {
        x: 0.5, y, w: 12.3, h: 0.52,
        fill: { color: C.white }, line: { color: C.white },
      });
    }
    s.addText(sc.type, {
      x: 0.8, y, w: 3.0, h: 0.52,
      fontFace: FONT.body, fontSize: 12, bold: true,
      color: C.textDark, align: "left", valign: "middle",
    });
    s.addText(sc.icon, {
      x: 3.8, y, w: 1.3, h: 0.52,
      fontFace: FONT.header, fontSize: 18, bold: true,
      color: sc.color, align: "center", valign: "middle",
    });
    s.addText(sc.status, {
      x: 5.1, y, w: 1.8, h: 0.52,
      fontFace: FONT.body, fontSize: 11,
      color: C.textDark, align: "left", valign: "middle",
    });
    s.addText(sc.priority, {
      x: 6.9, y, w: 1.5, h: 0.52,
      fontFace: FONT.body, fontSize: 11, bold: true,
      color: sc.priority === "必須" ? C.red : sc.priority === "推奨" ? C.amber : C.muted,
      align: "left", valign: "middle",
    });
    s.addText(sc.impact, {
      x: 8.4, y, w: 4.3, h: 0.52,
      fontFace: FONT.body, fontSize: 10.5,
      color: C.muted, align: "left", valign: "middle",
    });
  });

  // 下部コールアウト
  s.addShape("roundRect", {
    x: 0.5, y: 5.9, w: 12.3, h: 0.9,
    fill: { color: C.teal }, line: { color: C.teal },
    rectRadius: 0.06,
  });
  s.addText(
    "⚡ Organization と FAQPage の2つを追加するだけで +8点。実装所要時間は合計2時間程度です。",
    {
      x: 0.7, y: 5.9, w: 11.9, h: 0.9,
      fontFace: FONT.body, fontSize: 14, bold: true,
      color: C.white, align: "left", valign: "middle",
    }
  );

  addFooter(s, "07");
}

// ====================================================================
// Slide 8: 競合ベンチマーク
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "競合ベンチマーク", "Competitive Analysis");

  s.addText("メインキーワード上位3サイトとの比較", {
    x: 0.5, y: 1.05, w: 12.3, h: 0.4,
    fontFace: FONT.body, fontSize: 13, italic: true,
    color: C.muted, align: "left",
  });

  // 比較テーブル
  const sites = [
    { name: "自サイト",         wc: 2800, h2: 8,  faq: 0, sd: "Article",        score: 62, self: true },
    { name: "競合A",            wc: 4200, h2: 12, faq: 7, sd: "Article, FAQ",   score: 82 },
    { name: "競合B",            wc: 3500, h2: 10, faq: 5, sd: "Article, Org",   score: 75 },
    { name: "競合C",            wc: 3100, h2: 9,  faq: 6, sd: "Article, FAQ, BreadcrumbList", score: 78 },
  ];

  s.addShape("rect", {
    x: 0.5, y: 1.55, w: 12.3, h: 0.5,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  [
    { t: "サイト",          x: 0.7,  w: 2.8 },
    { t: "文字数",          x: 3.5,  w: 1.4 },
    { t: "H2数",            x: 4.9,  w: 1.2 },
    { t: "FAQ数",           x: 6.1,  w: 1.2 },
    { t: "構造化データ",    x: 7.3,  w: 3.5 },
    { t: "総合スコア",      x: 10.8, w: 1.9 },
  ].forEach(h => {
    s.addText(h.t, {
      x: h.x, y: 1.55, w: h.w, h: 0.5,
      fontFace: FONT.body, fontSize: 12, bold: true,
      color: C.white, align: "left", valign: "middle",
    });
  });

  sites.forEach((site, i) => {
    const y = 2.05 + i * 0.6;
    s.addShape("rect", {
      x: 0.5, y, w: 12.3, h: 0.6,
      fill: { color: site.self ? C.lightBg : C.white }, line: { color: C.border, width: 0.5 },
    });
    s.addText(site.name, {
      x: 0.7, y, w: 2.8, h: 0.6,
      fontFace: FONT.body, fontSize: 13, bold: true,
      color: site.self ? C.deepBlue : C.textDark, align: "left", valign: "middle",
    });
    s.addText(site.wc.toLocaleString(), {
      x: 3.5, y, w: 1.4, h: 0.6,
      fontFace: FONT.body, fontSize: 12,
      color: C.textDark, align: "left", valign: "middle",
    });
    s.addText(String(site.h2), {
      x: 4.9, y, w: 1.2, h: 0.6,
      fontFace: FONT.body, fontSize: 12,
      color: C.textDark, align: "left", valign: "middle",
    });
    s.addText(String(site.faq), {
      x: 6.1, y, w: 1.2, h: 0.6,
      fontFace: FONT.body, fontSize: 12, bold: site.faq === 0,
      color: site.faq === 0 ? C.red : C.textDark, align: "left", valign: "middle",
    });
    s.addText(site.sd, {
      x: 7.3, y, w: 3.5, h: 0.6,
      fontFace: FONT.body, fontSize: 10.5,
      color: C.muted, align: "left", valign: "middle",
    });
    const scColor = site.score >= 80 ? C.green : site.score >= 60 ? C.amber : C.red;
    s.addShape("roundRect", {
      x: 10.8, y: y + 0.1, w: 1.5, h: 0.4,
      fill: { color: scColor }, line: { color: scColor },
      rectRadius: 0.04,
    });
    s.addText(`${site.score}点`, {
      x: 10.8, y: y + 0.1, w: 1.5, h: 0.4,
      fontFace: FONT.body, fontSize: 13, bold: true,
      color: C.white, align: "center", valign: "middle",
    });
  });

  // ギャップ分析
  s.addShape("roundRect", {
    x: 0.5, y: 4.7, w: 6.1, h: 2.2,
    fill: { color: C.white }, line: { color: C.red, width: 2 },
    rectRadius: 0.08,
  });
  s.addText("🔴 コンテンツギャップ（負けている項目）", {
    x: 0.7, y: 4.85, w: 5.7, h: 0.4,
    fontFace: FONT.body, fontSize: 13, bold: true,
    color: C.red, align: "left",
  });
  [
    "FAQ数: 自サイト 0 vs 競合平均 6 → 追加で +4点",
    "文字数: 自サイト 2,800 vs 競合平均 3,600 → +800字推奨",
    "Organization構造化データ未実装 → 全競合実装済み",
  ].forEach((g, i) => {
    s.addText("• " + g, {
      x: 0.8, y: 5.3 + i * 0.45, w: 5.6, h: 0.4,
      fontFace: FONT.body, fontSize: 11,
      color: C.textDark, align: "left",
    });
  });

  s.addShape("roundRect", {
    x: 6.8, y: 4.7, w: 6.0, h: 2.2,
    fill: { color: C.white }, line: { color: C.green, width: 2 },
    rectRadius: 0.08,
  });
  s.addText("✅ 独自優位性（勝っている項目）", {
    x: 7.0, y: 4.85, w: 5.6, h: 0.4,
    fontFace: FONT.body, fontSize: 13, bold: true,
    color: C.green, align: "left",
  });
  [
    "Answer-first構造: 冒頭100字で結論提示",
    "独自データ・一次情報の掲載比率が高い",
    "更新日表示あり（競合Aは未表示）",
  ].forEach((g, i) => {
    s.addText("• " + g, {
      x: 7.1, y: 5.3 + i * 0.45, w: 5.5, h: 0.4,
      fontFace: FONT.body, fontSize: 11,
      color: C.textDark, align: "left",
    });
  });

  addFooter(s, "08");
}

// ====================================================================
// Slide 9: 優先改善施策（Quick Win）
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "優先改善施策 — Quick Win", "30日以内で実施可能な高効果施策");

  s.addText("今すぐ着手でき、かつインパクトが大きい5つの施策", {
    x: 0.5, y: 1.05, w: 12.3, h: 0.4,
    fontFace: FONT.body, fontSize: 13, italic: true,
    color: C.muted, align: "left",
  });

  const quickWins = [
    { no: "1", title: "Organization JSON-LDの追加", effort: "30分", impact: "+4点", cat: "構造化データ", detail: "運営者情報をAIに明示。全ページ共通で1度実装すれば完了。" },
    { no: "2", title: "FAQPage JSON-LD + FAQ 7問の追加", effort: "2時間", impact: "+6点", cat: "構造化データ", detail: "Google AI Overview引用率が平均3倍に。即効性が最も高い施策。" },
    { no: "3", title: "著者ボックスの設置", effort: "1時間", impact: "+3点", cat: "E-E-A-T", detail: "著者名・専門分野・プロフィールリンクを全記事に追加。" },
    { no: "4", title: "llms.txt の設置", effort: "30分", impact: "+2点", cat: "テクニカル", detail: "ChatGPTがサイト概要を正確に把握（2025年10月〜対応）。" },
    { no: "5", title: "冒頭「〇〇とは△△です」定義文の追加", effort: "1時間", impact: "+3点", cat: "AI引用可能性", detail: "AIが最も引用しやすいパターン。既存記事の冒頭改修のみで可能。" },
  ];

  quickWins.forEach((q, i) => {
    const y = 1.55 + i * 1.08;
    s.addShape("roundRect", {
      x: 0.5, y, w: 12.3, h: 0.98,
      fill: { color: C.white }, line: { color: C.border, width: 1 },
      rectRadius: 0.08,
    });
    // 番号サークル
    s.addShape("ellipse", {
      x: 0.7, y: y + 0.2, w: 0.6, h: 0.6,
      fill: { color: C.teal }, line: { color: C.teal },
    });
    s.addText(q.no, {
      x: 0.7, y: y + 0.2, w: 0.6, h: 0.6,
      fontFace: FONT.header, fontSize: 20, bold: true,
      color: C.white, align: "center", valign: "middle",
    });
    // タイトル
    s.addText(q.title, {
      x: 1.5, y: y + 0.1, w: 6.5, h: 0.4,
      fontFace: FONT.header, fontSize: 15, bold: true,
      color: C.textDark, align: "left", valign: "middle",
    });
    // カテゴリバッジ
    s.addShape("roundRect", {
      x: 1.5, y: y + 0.55, w: 1.7, h: 0.3,
      fill: { color: C.lightBg }, line: { color: C.lightBg },
      rectRadius: 0.03,
    });
    s.addText(q.cat, {
      x: 1.5, y: y + 0.55, w: 1.7, h: 0.3,
      fontFace: FONT.body, fontSize: 9, bold: true,
      color: C.deepBlue, align: "center", valign: "middle",
    });
    // 詳細
    s.addText(q.detail, {
      x: 3.3, y: y + 0.5, w: 5.0, h: 0.4,
      fontFace: FONT.body, fontSize: 10.5,
      color: C.muted, align: "left", valign: "middle",
    });
    // 工数
    s.addText("工数", {
      x: 8.5, y: y + 0.1, w: 1.5, h: 0.3,
      fontFace: FONT.body, fontSize: 9,
      color: C.muted, align: "center",
    });
    s.addText(q.effort, {
      x: 8.5, y: y + 0.35, w: 1.5, h: 0.5,
      fontFace: FONT.header, fontSize: 18, bold: true,
      color: C.deepBlue, align: "center", valign: "middle",
    });
    // インパクト
    s.addText("インパクト", {
      x: 10.2, y: y + 0.1, w: 2.3, h: 0.3,
      fontFace: FONT.body, fontSize: 9,
      color: C.muted, align: "center",
    });
    s.addShape("roundRect", {
      x: 10.5, y: y + 0.4, w: 1.8, h: 0.45,
      fill: { color: C.teal }, line: { color: C.teal },
      rectRadius: 0.05,
    });
    s.addText(q.impact, {
      x: 10.5, y: y + 0.4, w: 1.8, h: 0.45,
      fontFace: FONT.header, fontSize: 16, bold: true,
      color: C.white, align: "center", valign: "middle",
    });
  });

  addFooter(s, "09");
}

// ====================================================================
// Slide 10: 実装ロードマップ
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "実装ロードマップ", "90-Day Action Plan");

  s.addText("90日間で段階的に実装し、スコア +25点を目指す", {
    x: 0.5, y: 1.05, w: 12.3, h: 0.4,
    fontFace: FONT.body, fontSize: 13, italic: true,
    color: C.muted, align: "left",
  });

  // タイムライン
  const phases = [
    {
      period: "Phase 1",
      days: "Day 1–14",
      title: "Quick Win集中実装",
      tasks: ["Organization JSON-LD", "FAQPage JSON-LD", "llms.txt設置", "著者ボックス設置"],
      gain: "+15点",
      color: C.teal,
    },
    {
      period: "Phase 2",
      days: "Day 15–45",
      title: "コンテンツ構造改善",
      tasks: ["冒頭Answer-first化", "定義文パターン追加", "FAQ7問以上追加", "数値データ強化"],
      gain: "+8点",
      color: C.deepBlue,
    },
    {
      period: "Phase 3",
      days: "Day 46–90",
      title: "権威性・鮮度の強化",
      tasks: ["編集ポリシー明記", "外部引用リンク追加", "年次更新運用", "競合差別化コンテンツ"],
      gain: "+7点",
      color: C.navy,
    },
  ];

  phases.forEach((p, i) => {
    const x = 0.5 + i * 4.3;
    // カードコンテナ
    s.addShape("roundRect", {
      x, y: 1.6, w: 4.0, h: 5.0,
      fill: { color: C.white }, line: { color: C.border, width: 1 },
      rectRadius: 0.1,
    });
    // ヘッダー帯
    s.addShape("rect", {
      x, y: 1.6, w: 4.0, h: 1.2,
      fill: { color: p.color }, line: { color: p.color },
    });
    s.addShape("roundRect", {
      x, y: 1.6, w: 4.0, h: 1.2,
      fill: { color: p.color }, line: { color: p.color },
      rectRadius: 0.1,
    });
    s.addShape("rect", {
      x, y: 2.5, w: 4.0, h: 0.3,
      fill: { color: p.color }, line: { color: p.color },
    });
    s.addText(p.period, {
      x: x + 0.2, y: 1.75, w: 3.6, h: 0.35,
      fontFace: FONT.body, fontSize: 11, bold: true,
      color: C.cyan, align: "left", charSpacing: 4,
    });
    s.addText(p.days, {
      x: x + 0.2, y: 2.1, w: 3.6, h: 0.4,
      fontFace: FONT.header, fontSize: 20, bold: true,
      color: C.white, align: "left",
    });
    s.addText(p.title, {
      x: x + 0.2, y: 2.95, w: 3.6, h: 0.4,
      fontFace: FONT.header, fontSize: 14, bold: true,
      color: C.textDark, align: "left",
    });
    s.addShape("rect", {
      x: x + 0.2, y: 3.4, w: 0.5, h: 0.03,
      fill: { color: p.color }, line: { color: p.color },
    });
    // タスクリスト
    p.tasks.forEach((t, j) => {
      const ty = 3.6 + j * 0.35;
      s.addShape("ellipse", {
        x: x + 0.25, y: ty + 0.08, w: 0.12, h: 0.12,
        fill: { color: p.color }, line: { color: p.color },
      });
      s.addText(t, {
        x: x + 0.45, y: ty, w: 3.4, h: 0.3,
        fontFace: FONT.body, fontSize: 11,
        color: C.textDark, align: "left", valign: "middle",
      });
    });
    // 獲得点数
    s.addShape("roundRect", {
      x: x + 1.0, y: 5.8, w: 2.0, h: 0.6,
      fill: { color: C.cream }, line: { color: p.color, width: 2 },
      rectRadius: 0.05,
    });
    s.addText(`想定効果 ${p.gain}`, {
      x: x + 1.0, y: 5.8, w: 2.0, h: 0.6,
      fontFace: FONT.body, fontSize: 12, bold: true,
      color: p.color, align: "center", valign: "middle",
    });
  });

  // 総合効果
  s.addShape("roundRect", {
    x: 0.5, y: 6.75, w: 12.3, h: 0.45,
    fill: { color: C.deepBlue }, line: { color: C.deepBlue },
    rectRadius: 0.05,
  });
  s.addText("💎 90日後の想定総合スコア: 62点 → 87点（グレード A 達成）", {
    x: 0.5, y: 6.75, w: 12.3, h: 0.45,
    fontFace: FONT.body, fontSize: 13, bold: true,
    color: C.white, align: "center", valign: "middle",
  });

  addFooter(s, "10");
}

// ====================================================================
// Slide 11: 想定効果（ROI）
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "想定効果・ROI試算", "Expected Impact");

  // 左: スコア推移グラフ（シェイプで表現）
  s.addText("📊 スコア推移シミュレーション", {
    x: 0.5, y: 1.1, w: 6.5, h: 0.4,
    fontFace: FONT.header, fontSize: 16, bold: true,
    color: C.textDark, align: "left",
  });

  // グラフエリア
  s.addShape("roundRect", {
    x: 0.5, y: 1.6, w: 6.3, h: 3.8,
    fill: { color: C.white }, line: { color: C.border, width: 1 },
    rectRadius: 0.05,
  });

  // Y軸ラベル
  [100, 80, 60, 40, 20, 0].forEach((v, i) => {
    const y = 1.9 + i * 0.55;
    s.addText(String(v), {
      x: 0.6, y, w: 0.35, h: 0.3,
      fontFace: FONT.body, fontSize: 9, color: C.muted, align: "right",
    });
    s.addShape("line", {
      x: 1.0, y: y + 0.15, w: 5.6, h: 0,
      line: { color: C.border, width: 0.5, dashType: "dash" },
    });
  });

  // データポイント（現在62, 14日後77, 45日後85, 90日後92）
  const points = [
    { x: 1.5, label: "現在", score: 62, color: C.red },
    { x: 2.9, label: "14日後", score: 77, color: C.amber },
    { x: 4.3, label: "45日後", score: 85, color: C.teal },
    { x: 5.7, label: "90日後", score: 92, color: C.green },
  ];

  // 折れ線
  for (let i = 0; i < points.length - 1; i++) {
    const p1 = points[i];
    const p2 = points[i + 1];
    const y1 = 4.8 - (p1.score / 100) * 3.3;
    const y2 = 4.8 - (p2.score / 100) * 3.3;
    s.addShape("line", {
      x: p1.x, y: y1, w: p2.x - p1.x, h: y2 - y1,
      line: { color: C.deepBlue, width: 3 },
    });
  }

  // ポイント
  points.forEach(p => {
    const y = 4.8 - (p.score / 100) * 3.3;
    s.addShape("ellipse", {
      x: p.x - 0.12, y: y - 0.12, w: 0.24, h: 0.24,
      fill: { color: p.color }, line: { color: C.white, width: 2 },
    });
    s.addText(String(p.score), {
      x: p.x - 0.4, y: y - 0.5, w: 0.8, h: 0.3,
      fontFace: FONT.body, fontSize: 11, bold: true,
      color: p.color, align: "center",
    });
    s.addText(p.label, {
      x: p.x - 0.6, y: 4.95, w: 1.2, h: 0.3,
      fontFace: FONT.body, fontSize: 10,
      color: C.muted, align: "center",
    });
  });

  // 右: KPI予測
  s.addText("📈 KPI予測", {
    x: 7.2, y: 1.1, w: 5.6, h: 0.4,
    fontFace: FONT.header, fontSize: 16, bold: true,
    color: C.textDark, align: "left",
  });

  const kpis = [
    { label: "AI Overview 引用率",  before: "2%",    after: "12%",    arrow: "×6倍" },
    { label: "ChatGPT 出典表示",    before: "1件/月", after: "8件/月", arrow: "×8倍" },
    { label: "Perplexity 引用",    before: "未計測", after: "15件/月", arrow: "New" },
    { label: "AI経由セッション",    before: "約50/月", after: "約400/月", arrow: "×8倍" },
    { label: "指名検索数",          before: "基準",  after: "+40%",   arrow: "↑40%" },
  ];

  kpis.forEach((k, i) => {
    const y = 1.6 + i * 0.7;
    s.addShape("roundRect", {
      x: 7.2, y, w: 5.6, h: 0.6,
      fill: { color: C.white }, line: { color: C.border, width: 1 },
      rectRadius: 0.05,
    });
    s.addText(k.label, {
      x: 7.35, y, w: 2.5, h: 0.6,
      fontFace: FONT.body, fontSize: 11, bold: true,
      color: C.textDark, align: "left", valign: "middle",
    });
    s.addText(k.before, {
      x: 9.8, y, w: 1.1, h: 0.6,
      fontFace: FONT.body, fontSize: 11,
      color: C.muted, align: "center", valign: "middle",
    });
    s.addText("→", {
      x: 10.9, y, w: 0.4, h: 0.6,
      fontFace: FONT.body, fontSize: 14,
      color: C.teal, align: "center", valign: "middle",
    });
    s.addText(k.after, {
      x: 11.3, y, w: 1.4, h: 0.6,
      fontFace: FONT.body, fontSize: 12, bold: true,
      color: C.teal, align: "center", valign: "middle",
    });
  });

  // 注記
  s.addShape("roundRect", {
    x: 0.5, y: 5.7, w: 12.3, h: 1.1,
    fill: { color: C.navy }, line: { color: C.navy },
    rectRadius: 0.08,
  });
  s.addText("💼 ビジネスインパクト（試算）", {
    x: 0.7, y: 5.8, w: 11.9, h: 0.35,
    fontFace: FONT.body, fontSize: 12, bold: true,
    color: C.cyan, align: "left",
  });
  s.addText(
    "SEO流入に加え、AI経由の新規タッチポイントが加わることで、月間商談機会が推定 +20〜30%。\n" +
    "また、AI引用によるブランド露出はSEO検索結果と異なり「選ばれた1〜3社しか出ない」ため、競合優位を長期に確保できます。",
    {
      x: 0.7, y: 6.15, w: 11.9, h: 0.6,
      fontFace: FONT.body, fontSize: 11,
      color: C.white, align: "left",
    }
  );

  addFooter(s, "11");
}

// ====================================================================
// Slide 12: 商談実演用テストクエリ
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeaderBar(s, "商談・社内共有用テストクエリ", "AI Search Demo Queries");

  s.addText("実際にAIに質問して「御社が引用されるか」を体感確認するクエリ集", {
    x: 0.5, y: 1.05, w: 12.3, h: 0.4,
    fontFace: FONT.body, fontSize: 13, italic: true,
    color: C.muted, align: "left",
  });

  const queries = [
    { platform: "ChatGPT",           color: "10A37F", icon: "🤖", query: "〔メインKW〕について教えてください",         note: "定義文＋Answer-first構造の評価" },
    { platform: "ChatGPT",           color: "10A37F", icon: "🤖", query: "〔メインKW〕 おすすめ 比較",               note: "比較構造・リスト化レベルの評価" },
    { platform: "Perplexity",        color: "20B8CD", icon: "🔮", query: "〔メインKW〕の選び方は？",                   note: "FAQ・HowTo構造の評価" },
    { platform: "Perplexity",        color: "20B8CD", icon: "🔮", query: "〔メインKW〕 メリット デメリット",           note: "網羅性・両論併記の評価" },
    { platform: "Google AI Overview", color: "4285F4", icon: "🔍", query: "〔メインKW〕とは",                          note: "定義文パターンの評価（最重要）" },
  ];

  queries.forEach((q, i) => {
    const y = 1.55 + i * 1.05;
    s.addShape("roundRect", {
      x: 0.5, y, w: 12.3, h: 0.95,
      fill: { color: C.white }, line: { color: C.border, width: 1 },
      rectRadius: 0.08,
    });
    // プラットフォームアイコン
    s.addShape("roundRect", {
      x: 0.7, y: y + 0.15, w: 2.0, h: 0.65,
      fill: { color: q.color }, line: { color: q.color },
      rectRadius: 0.05,
    });
    s.addText(`${q.icon}  ${q.platform}`, {
      x: 0.7, y: y + 0.15, w: 2.0, h: 0.65,
      fontFace: FONT.body, fontSize: 11, bold: true,
      color: C.white, align: "center", valign: "middle",
    });
    // クエリ本文
    s.addText("検索クエリ例", {
      x: 2.9, y: y + 0.1, w: 9.7, h: 0.25,
      fontFace: FONT.body, fontSize: 9,
      color: C.muted, align: "left",
    });
    s.addText(`"${q.query}"`, {
      x: 2.9, y: y + 0.35, w: 9.7, h: 0.35,
      fontFace: FONT.header, fontSize: 14, bold: true, italic: true,
      color: C.textDark, align: "left", valign: "middle",
    });
    s.addText("▶ " + q.note, {
      x: 2.9, y: y + 0.65, w: 9.7, h: 0.25,
      fontFace: FONT.body, fontSize: 10,
      color: C.teal, align: "left",
    });
  });

  // 下部ティップ
  s.addShape("roundRect", {
    x: 0.5, y: 6.8, w: 12.3, h: 0.45,
    fill: { color: C.lightBg }, line: { color: C.lightBg },
    rectRadius: 0.05,
  });
  s.addText("💡 商談現場で上記クエリを実行 → 「御社サイトが出ない/出る」を体感してもらうと改善ニーズが明確化されます", {
    x: 0.5, y: 6.8, w: 12.3, h: 0.45,
    fontFace: FONT.body, fontSize: 11, italic: true,
    color: C.deepBlue, align: "center", valign: "middle",
  });

  addFooter(s, "12");
}

// ====================================================================
// Slide 13: 次のステップ・お問い合わせ
// ====================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // 上部装飾
  s.addShape("rect", {
    x: 0, y: 0, w: 13.33, h: 0.08,
    fill: { color: C.cyan }, line: { color: C.cyan },
  });

  s.addText("NEXT STEP", {
    x: 0.5, y: 0.6, w: 12.3, h: 0.4,
    fontFace: FONT.body, fontSize: 14, bold: true,
    color: C.cyan, align: "center", charSpacing: 12,
  });
  s.addText("次のアクションについて", {
    x: 0.5, y: 1.1, w: 12.3, h: 0.8,
    fontFace: FONT.header, fontSize: 36, bold: true,
    color: C.white, align: "center",
  });

  // 3カラム
  const steps = [
    {
      num: "STEP 1",
      title: "診断レポートの読み合わせ",
      desc: "社内で優先度・工数感の共有。疑問点の洗い出し（約60分）",
      icon: "📋",
    },
    {
      num: "STEP 2",
      title: "Quick Win実装キックオフ",
      desc: "Phase 1施策（Day 1–14）の担当・期日確定。テンプレートコード提供",
      icon: "🚀",
    },
    {
      num: "STEP 3",
      title: "30日後の再診断",
      desc: "同じツールで再測定。改善効果の定量確認と次フェーズ計画",
      icon: "📊",
    },
  ];

  steps.forEach((st, i) => {
    const x = 0.7 + i * 4.1;
    s.addShape("roundRect", {
      x, y: 2.5, w: 3.8, h: 3.2,
      fill: { color: C.deepBlue }, line: { color: C.cyan, width: 1 },
      rectRadius: 0.12,
    });
    s.addText(st.icon, {
      x, y: 2.75, w: 3.8, h: 0.8,
      fontFace: FONT.body, fontSize: 40,
      align: "center", valign: "middle",
    });
    s.addShape("roundRect", {
      x: x + 1.3, y: 3.75, w: 1.2, h: 0.35,
      fill: { color: C.cyan }, line: { color: C.cyan },
      rectRadius: 0.04,
    });
    s.addText(st.num, {
      x: x + 1.3, y: 3.75, w: 1.2, h: 0.35,
      fontFace: FONT.body, fontSize: 10, bold: true,
      color: C.navy, align: "center", valign: "middle",
    });
    s.addText(st.title, {
      x: x + 0.2, y: 4.2, w: 3.4, h: 0.7,
      fontFace: FONT.header, fontSize: 16, bold: true,
      color: C.white, align: "center", valign: "middle",
    });
    s.addText(st.desc, {
      x: x + 0.25, y: 4.95, w: 3.3, h: 0.7,
      fontFace: FONT.body, fontSize: 11,
      color: C.textLight, align: "center",
    });
  });

  // CTA
  s.addShape("roundRect", {
    x: 2.5, y: 6.1, w: 8.3, h: 0.8,
    fill: { color: C.teal }, line: { color: C.teal },
    rectRadius: 0.1,
  });
  s.addText("▶ 詳細な実装支援・カスタム診断のご相談を承ります", {
    x: 2.5, y: 6.1, w: 8.3, h: 0.8,
    fontFace: FONT.header, fontSize: 16, bold: true,
    color: C.white, align: "center", valign: "middle",
  });

  s.addText("Thank you  |  AIO/LLMO診断ツール v2.1", {
    x: 0.5, y: 7.1, w: 12.3, h: 0.3,
    fontFace: FONT.body, fontSize: 10,
    color: C.muted, align: "center",
  });
}

// ===== 保存 =====
pres.writeFile({ fileName: "AIO_LLMO_診断レポート.pptx" })
  .then(fn => console.log("✅ Generated:", fn));
