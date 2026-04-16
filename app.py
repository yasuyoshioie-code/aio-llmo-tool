"""AIO/LLMO 診断ツール — Streamlit Web App（サイト全体診断版）"""

import os
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from config import TAVILY_API_KEY
from core.fetcher import (
    fetch_page, fetch_text_file, fetch_pagespeed, search_web, fetch_sitemap_info,
)
from core.parser import parse_html, parse_from_markdown
from core.technical import analyze_robots_txt, analyze_llms_txt, validate_jsonld
from core.content_scorer import (
    analyze_content_python, analyze_eeat_python,
    generate_improvements_python, generate_test_queries_python,
)
from core.competitor import find_competitors, analyze_competitor, build_comparison_table
from core.scorer import (
    calculate_technical_scores, merge_all_scores,
    calculate_category_totals, calculate_total, generate_report_md,
)
from core.site_crawler import get_site_urls
from core.site_aggregator import aggregate_site_results
from core.pptx_generator import generate_pptx_report
from core.presets import get_preset, PRESETS


def _save_env_key(key_name: str, key_value: str) -> bool:
    env_path = Path(__file__).parent / ".env"
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key_name}="):
            lines[i] = f"{key_name}={key_value}"
            found = True
            break
    if not found:
        lines.append(f"{key_name}={key_value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key_name] = key_value
    return True


def analyze_single_page(
    page_url: str,
    tavily_key: str,
    robots: dict,
    llms: dict,
    pagespeed: dict,
    sitemap: dict,
    preset=None,
) -> dict:
    """1ページのPython解析とスコアリングを実行。プリセットでスコアリング方式を切替。"""
    page_data = fetch_page(page_url, tavily_key)

    if page_data.get("raw_html"):
        structure = parse_html(page_data["raw_html"])
    else:
        structure = parse_from_markdown(page_data.get("content", ""), page_data.get("raw_html", ""))

    if not structure.get("content_text") and page_data.get("content"):
        structure["content_text"] = page_data["content"]

    if preset is not None:
        all_scores, categories, total = preset.score_page(structure, robots, llms, pagespeed, sitemap)
    else:
        technical_scores = calculate_technical_scores(structure, robots, llms, pagespeed, sitemap)
        content_citation = analyze_content_python(structure["content_text"], structure)
        eeat_scores = analyze_eeat_python(structure["content_text"], structure)
        all_scores = merge_all_scores(technical_scores, content_citation, eeat_scores)

        faq_count = len(structure.get("faq_items", []))
        if faq_count >= 5: faq_score = 4
        elif faq_count >= 1: faq_score = 2
        else: faq_score = 0
        all_scores["1-3_faq"] = {
            "score": faq_score, "max": 4,
            "reason": f"FAQ {faq_count}件検出",
            "method": "HTML実測", "confidence": "高",
        }

        categories = calculate_category_totals(all_scores)
        total = calculate_total(categories)

    return {
        "url": page_url,
        "title": structure.get("title", ""),
        "structure": structure,
        "all_scores": all_scores,
        "categories": categories,
        "total": total,
        "fetch_source": page_data.get("source", ""),
    }


# ================================================================
# --- Page Config ---
st.set_page_config(
    page_title="AIO/LLMO サイト診断ツール",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ================================================================
# 🔐 パスワード認証ゲート（限定公開用）
# ================================================================
def _check_password() -> bool:
    """APP_PASSWORD が設定されていれば認証ゲートを表示。未設定なら素通し。"""
    # secrets / env var から取得
    app_pw = ""
    try:
        app_pw = st.secrets["APP_PASSWORD"]
    except Exception:
        pass
    if not app_pw:
        app_pw = os.getenv("APP_PASSWORD", "")

    # パスワード未設定 → 認証スキップ（ローカル開発用）
    if not app_pw:
        return True

    # 認証済みセッション → そのまま通す
    if st.session_state.get("_authed"):
        return True

    # ログイン画面
    st.markdown("<div style='max-width:420px;margin:15vh auto 0;'>", unsafe_allow_html=True)
    st.markdown("## 🔐 AIO/LLMO 診断ツール")
    st.caption("このツールは限定公開です。アクセスパスワードを入力してください。")

    with st.form("login", clear_on_submit=False):
        pw = st.text_input("パスワード", type="password")
        submit = st.form_submit_button("ログイン", type="primary", use_container_width=True)

    if submit:
        if pw == app_pw:
            st.session_state["_authed"] = True
            st.rerun()
        else:
            st.error("❌ パスワードが違います")

    st.markdown("</div>", unsafe_allow_html=True)
    return False


if not _check_password():
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ 設定")

    tavily_key = st.text_input(
        "Tavily API Key",
        value=TAVILY_API_KEY,
        type="password",
        help="Tavily APIキー（tavily.com）",
    )

    if st.button("💾 APIキーを保存", use_container_width=True):
        if tavily_key and tavily_key.strip():
            try:
                _save_env_key("TAVILY_API_KEY", tavily_key.strip())
                st.success("✅ .envに保存しました")
            except Exception as e:
                st.error(f"保存失敗: {e}")
        else:
            st.warning("APIキーを入力してください")

    st.divider()
    st.subheader("診断タイプ")
    preset_id = st.selectbox(
        "サイト種別を選択",
        options=list(PRESETS.keys()),
        format_func=lambda x: PRESETS[x]["label"],
        index=0,
        help="サイト種別ごとに評価基準・改善提案・テストクエリが切り替わります",
    )
    st.caption(PRESETS[preset_id]["description"])
    preset = get_preset(preset_id)["module"]

    st.divider()
    st.subheader("診断モード")
    diagnostic_mode = st.radio(
        "モード",
        [
            "🌐 サイト全体診断（推奨）",
            "📋 URL貼り付け診断（複数ページ指定）",
            "📄 単一ページ診断",
        ],
        index=0,
        help="複数のリクルートページ等を指定して診断する場合は「URL貼り付け」を選択",
    )
    is_site_mode = diagnostic_mode.startswith("🌐")
    is_paste_mode = diagnostic_mode.startswith("📋")

    sample_size = st.slider(
        "サンプル分析ページ数", 5, 50, 20, step=5,
        help="サイト全体モード時、sitemap.xmlから戦略的サンプリングするページ数",
        disabled=not is_site_mode,
    )

    pasted_urls_input = st.text_area(
        "診断するURL（1行1URL・最大30件）",
        placeholder="https://example.com/recruit/job-001\nhttps://example.com/recruit/job-002\nhttps://example.com/recruit/engineer",
        height=140,
        disabled=not is_paste_mode,
        help="リクルート下層ページや特定のLPなど、診断したいURLを改行区切りで貼り付け",
    )

    st.divider()
    st.subheader("オプション")

    keywords_input = st.text_input(
        "メインキーワード（カンマ区切り・最大3つ）",
        placeholder="例: 金沢 SEO, Webコンサル 石川",
    )
    run_competitor = st.checkbox("競合分析を実行", value=True)
    run_improvements = st.checkbox("改善提案を生成", value=True)

    st.divider()
    st.caption("💡 定性分析はClaude Codeの")
    st.caption("@aio-diagnostic で実行可能")
    st.divider()
    st.caption("v3.0 — サイト全体診断モード")

# --- Main ---
st.title("🔍 AIO/LLMO サイト全体診断ツール")
st.caption("サイトURLを入力するだけで、サイト全体を網羅的に診断します")

url = st.text_input(
    "診断するサイトURLを入力（URL貼り付けモード時は代表URLを入力）",
    placeholder="https://example.com",
    label_visibility="collapsed",
)

# URL貼り付けモード時のリスト
pasted_urls: list[str] = []
if is_paste_mode and pasted_urls_input:
    pasted_urls = [
        u.strip() for u in pasted_urls_input.splitlines()
        if u.strip().startswith("http")
    ][:30]

col_run, col_info = st.columns([1, 3])
with col_run:
    run_btn = st.button("🚀 診断開始", type="primary", use_container_width=True)
with col_info:
    if is_site_mode:
        info_msg = f"{sample_size}ページを分析します（3〜5分）"
    elif is_paste_mode:
        info_msg = f"{len(pasted_urls)}件のURLを分析します（{max(1, len(pasted_urls)//4)}〜{max(2, len(pasted_urls)//2)}分）"
    else:
        info_msg = "単一ページ分析（1〜2分）"
    st.caption(f"診断モード: **{diagnostic_mode}** — {info_msg}")


# URL貼り付けモードで代表URL未入力なら、貼り付け1件目を採用
if is_paste_mode and not url and pasted_urls:
    url = pasted_urls[0]

if run_btn and url:
    if is_paste_mode and not pasted_urls:
        st.error("URL貼り付けモードでは、診断するURLを1つ以上入力してください")
        st.stop()
    if not tavily_key:
        st.error("Tavily APIキーを設定してください（サイドバー）")
        st.stop()

    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()] if keywords_input else []
    parsed_url = urlparse(url)
    self_domain = parsed_url.netloc
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

    progress = st.progress(0, text="Phase 1: サイト情報取得中...")

    # ===== Phase 1: サイト共通情報 =====
    with st.status("📥 Phase 1: サイト共通情報の取得（robots.txt / llms.txt / PageSpeed / sitemap）", expanded=True) as status1:
        st.write("robots.txt 取得中...")
        robots_raw = fetch_text_file(origin, "robots.txt", tavily_key)
        robots = analyze_robots_txt(robots_raw["content"] if robots_raw["exists"] else "")

        st.write("llms.txt 取得中...")
        llms_raw = fetch_text_file(origin, "llms.txt", tavily_key)
        llms = analyze_llms_txt(llms_raw["content"], llms_raw["exists"])

        st.write("PageSpeed測定中（トップページ）...")
        pagespeed = fetch_pagespeed(origin)

        st.write("sitemap.xml 取得中...")
        sitemap = fetch_sitemap_info(origin)

        status1.update(label="📥 Phase 1: サイト共通情報 取得完了", state="complete")

    # ===== Phase 1.5: サイト全体URL収集 =====
    sampled_pages: list[dict] = []
    site_info = {}
    if is_site_mode:
        with st.status(f"🗺️ Phase 1.5: サイトマップ解析とページサンプリング（目標 {sample_size}件）", expanded=True) as status15:
            site_info = get_site_urls(origin, tavily_key, sample_size=sample_size)
            total_discovered = site_info.get("total_urls_discovered", 0)
            sampled_pages = site_info.get("sampled_pages", [])
            st.write(f"✅ sitemapから **{total_discovered}件** のURLを発見 → **{len(sampled_pages)}件** をサンプリング")
            if site_info.get("source") == "not_found":
                st.warning("sitemap.xml が見つかりませんでした — 入力URLのみを診断します")
                sampled_pages = [{"url": url, "type": "input"}]
            status15.update(label=f"🗺️ Phase 1.5: {len(sampled_pages)}ページ抽出", state="complete")
    elif is_paste_mode:
        sampled_pages = [{"url": u, "type": "pasted"} for u in pasted_urls]
        st.success(f"📋 貼り付けられた **{len(sampled_pages)}件** のURLを診断します")
    else:
        sampled_pages = [{"url": url, "type": "input"}]

    progress.progress(20, text=f"Phase 2: {len(sampled_pages)}ページを個別分析中...")

    # ===== Phase 2: 各ページの解析 =====
    page_results: list[dict] = []
    with st.status(f"🧠 Phase 2: ページ単位AIO/LLMO分析（{len(sampled_pages)}ページ）", expanded=True) as status2:
        prog_bar = st.progress(0)
        for i, p in enumerate(sampled_pages):
            p_url = p["url"]
            try:
                result = analyze_single_page(p_url, tavily_key, robots, llms, pagespeed, sitemap, preset=preset)
                result["type"] = p.get("type", "page")
                page_results.append(result)
                st.write(f"✅ [{i+1}/{len(sampled_pages)}] {p.get('type','page')}: {p_url[:80]} — {result['total']['total']}/100 ({result['total']['grade']})")
            except Exception as e:
                st.write(f"⚠️ [{i+1}/{len(sampled_pages)}] 分析失敗: {p_url[:60]} ({str(e)[:40]})")
            prog_bar.progress((i + 1) / len(sampled_pages))

        status2.update(label=f"🧠 Phase 2: {len(page_results)}ページ分析完了", state="complete")

    if not page_results:
        st.error("すべてのページで分析失敗。URLを確認してください。")
        st.stop()

    progress.progress(55, text="Phase 2.5: サイト全体集計中...")

    # ===== Phase 2.5: サイト全体集計 =====
    site_agg = aggregate_site_results(page_results)

    # 入力URLのページ結果 or 代表ページ（最高スコア or ホーム）を「代表ページ」として選ぶ
    representative = next(
        (p for p in page_results if p["url"].rstrip("/") == url.rstrip("/")),
        None,
    )
    if not representative:
        representative = max(page_results, key=lambda p: p["total"]["total"])

    structure = representative["structure"]
    all_scores = representative["all_scores"]
    categories = representative["categories"]
    total = representative["total"]

    # サイト全体・URL貼り付けの場合はサイト平均で上書き
    if is_site_mode or (is_paste_mode and len(page_results) > 1):
        site_score_val = site_agg["site_score"]
        site_grade_val = site_agg["site_grade"]
        grade_labels = {
            "S": "卓越: AI検索時代で優位に立てるトップクラスのサイト",
            "A": "優良: AI検索でも高評価、継続的な改善でトップ層へ",
            "B": "標準: 一般的なレベル、競合と差をつけるには施策が必要",
            "C": "要改善: AI検索で引用されにくい、抜本的な対策が必要",
            "D": "危険: AI検索時代で取り残されるリスク大、即時対応が必須",
        }
        total = {
            "total": site_score_val,
            "grade": site_grade_val,
            "label": grade_labels.get(site_grade_val, ""),
        }

    # キーワード自動推定
    if not keywords:
        title = structure.get("title", "")
        keywords = [title.split("–")[0].split("|")[0].strip()] if title else [self_domain]

    # ===== Phase 3: 検索出現テスト =====
    progress.progress(65, text="Phase 3: 検索出現テスト中...")
    search_results_data = {}
    with st.status("🔎 Phase 3: 検索出現テスト", expanded=False) as status3:
        for kw in keywords[:3]:
            st.write(f"検索中: 「{kw}」")
            results = search_web(kw, tavily_key, max_results=10)
            found_rank = None
            for i, r in enumerate(results):
                if self_domain in r.get("url", ""):
                    found_rank = i + 1
                    break
            search_results_data[kw] = {
                "results": results,
                "self_rank": found_rank,
                "status": f"第{found_rank}位" if found_rank else "圏外",
            }
        status3.update(label="🔎 Phase 3: 完了", state="complete")

    # ===== Phase 4: 競合分析 =====
    progress.progress(75, text="Phase 4: 競合分析中...")
    competitor_analyses = []
    comparison = {}
    if run_competitor:
        with st.status("📊 Phase 4: 競合ベンチマーク", expanded=False) as status4:
            st.write("競合サイトを特定中...")
            competitors_info = find_competitors(keywords, tavily_key, self_domain)

            for comp in competitors_info[:3]:
                comp_url = comp["urls"][0] if comp["urls"] else ""
                if comp_url:
                    st.write(f"分析中: {comp['domain']}")
                    analysis = analyze_competitor(comp_url, tavily_key)
                    competitor_analyses.append(analysis)

            self_as_competitor = analyze_competitor(representative["url"], tavily_key)
            comparison = build_comparison_table(self_as_competitor, competitor_analyses)
            status4.update(label="📊 Phase 4: 完了", state="complete")

    # ===== Phase 5: 改善提案 =====
    progress.progress(90, text="Phase 5: 改善提案生成中...")
    improvements = {}
    test_queries = {}
    if run_improvements:
        with st.status("💡 Phase 5: 改善提案", expanded=False) as status5:
            st.write("サイト全体向けの改善施策を生成中...")
            improvements = preset.generate_improvements(
                all_scores, structure, url,
                competitors=competitor_analyses, comparison=comparison,
            )
            test_queries = preset.generate_test_queries(
                url, keywords, structure.get("title", ""),
            )
            status5.update(label="💡 Phase 5: 完了", state="complete")

    progress.progress(100, text="レポート生成完了！")

    # ================================================================
    # 結果表示
    # ================================================================
    st.divider()

    # --- サイトヘッダー ---
    is_aggregated = is_site_mode or (is_paste_mode and len(page_results) > 1)
    if is_aggregated:
        if is_paste_mode:
            st.subheader(f"📋 複数ページ集計診断結果: `{self_domain}` ({len(page_results)}ページ)")
        else:
            st.subheader(f"🌐 サイト全体診断結果: `{self_domain}`")
        h1, h2, h3, h4, h5 = st.columns(5)
        with h1:
            st.metric("サイト総合", f"{site_agg['site_score']}/100", delta=f"Grade {site_agg['site_grade']}")
        with h2:
            st.metric("分析ページ数", site_agg["page_count"])
        with h3:
            st.metric("スコア中央値", site_agg["score_median"])
        with h4:
            st.metric("最高スコア", site_agg["score_max"])
        with h5:
            st.metric("最低スコア", site_agg["score_min"])

        st.caption(f"📊 標準偏差: {site_agg['score_stdev']} （値が小さいほどサイト全体で品質が均一）")
    else:
        cat_items = list(categories.items())
        cols = st.columns(min(4, 1 + len(cat_items)))
        with cols[0]:
            st.metric("総合スコア", f"{total['total']}/100", delta=f"Grade {total['grade']}")
        for i, (cat_key, cat_val) in enumerate(cat_items[:3], start=1):
            if i >= len(cols):
                break
            with cols[i]:
                label = cat_val.get("label") or cat_key
                st.metric(label, f"{cat_val.get('score', 0)}/{cat_val.get('max', 0)}")

    st.divider()

    # --- タブ ---
    # CV診断データ（リクルーティングプリセット時のみ）
    cv_data = structure.get("_cv_analysis") if isinstance(structure, dict) else None

    tab_labels = [
        "🌐 サイト全体サマリ",
        "📋 ページ別スコア",
        "🔧 テクニカル",
        "📈 競合分析",
        "💡 改善提案",
        "🎯 商談テストクエリ",
        "📄 レポートDL",
    ]
    cv_tab_index = None
    if cv_data:
        cv_tab_index = len(tab_labels)
        tab_labels.append("🎯 CV診断（応募率）")
    tabs = st.tabs(tab_labels)

    # Tab 0: サイト全体サマリ
    with tabs[0]:
        if is_aggregated:
            st.subheader("📊 スコア分布")
            dist = site_agg["score_distribution"]
            st.bar_chart(dist)

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.subheader("ページタイプ別平均")
                tstat_rows = []
                for ptype, s in site_agg["type_stats"].items():
                    tstat_rows.append({
                        "タイプ": ptype,
                        "ページ数": s["count"],
                        "平均スコア": s["avg_score"],
                    })
                st.dataframe(tstat_rows, use_container_width=True)

            with col_d2:
                st.subheader("カテゴリ別平均（30項目→6カテゴリ）")
                cat_rows = []
                for ckey, cavg in sorted(site_agg["category_averages"].items()):
                    cat_rows.append({
                        "カテゴリ": cavg["label"],
                        "平均": f"{cavg['score']}/{cavg['max']}",
                        "達成率": f"{cavg['pct']}%",
                        "中央値": cavg["median"],
                        "最低": cavg["min"],
                        "最高": cavg["max_observed"],
                    })
                st.dataframe(cat_rows, use_container_width=True)

            st.subheader("🔴 サイト共通の問題（50%以上のページで未実装）")
            if site_agg["common_issues"]:
                issue_rows = []
                for iss in site_agg["common_issues"][:15]:
                    issue_rows.append({
                        "項目": iss["item_key"],
                        "未実装ページ率": f"{iss['failure_pct']}%",
                        "平均達成率": f"{iss['avg_pct']}%",
                        "サンプル根拠": (iss["sample_reasons"][0] if iss["sample_reasons"] else "")[:60],
                    })
                st.dataframe(issue_rows, use_container_width=True)
                st.caption("👉 これらを全ページ横断で修正することで、サイト全体のスコアが大幅改善します")
            else:
                st.success("サイト全体で一貫して実装されており、共通の未実装項目はありません")

            col_w, col_b = st.columns(2)
            with col_w:
                st.subheader("🔴 ワースト10ページ")
                for i, p in enumerate(site_agg["worst_pages"], 1):
                    st.write(f"{i}. [{p['grade']}] **{p['score']}** — {p['title'] or p['url'][:60]}")
                    st.caption(f"   {p['url']}")
            with col_b:
                st.subheader("✅ ベスト10ページ")
                for i, p in enumerate(site_agg["best_pages"], 1):
                    st.write(f"{i}. [{p['grade']}] **{p['score']}** — {p['title'] or p['url'][:60]}")
                    st.caption(f"   {p['url']}")
        else:
            st.info("単一ページ診断モードです。サイト全体診断はサイドバーで選択してください。")
            st.subheader("カテゴリ別スコア（このページ）")
            for key in sorted(categories.keys()):
                cat = categories[key]
                pct = cat["score"] / cat["max"] if cat["max"] else 0
                st.progress(pct, text=f"{cat['label']}: {cat['score']}/{cat['max']}")

    # Tab 1: ページ別スコア
    with tabs[1]:
        st.subheader(f"全 {len(page_results)} ページのスコア")
        page_rows = []
        for p in sorted(page_results, key=lambda x: -x["total"]["total"]):
            page_rows.append({
                "URL": p["url"],
                "タイプ": p.get("type", "-"),
                "タイトル": (p.get("title", "") or "")[:50],
                "文字数": p["structure"].get("word_count", 0),
                "H2数": sum(1 for h in p["structure"].get("headings", []) if h.get("level") == 2),
                "FAQ": len(p["structure"].get("faq_items", [])),
                "構造化": len(p["structure"].get("jsonld", [])),
                "スコア": p["total"]["total"],
                "Grade": p["total"]["grade"],
            })
        st.dataframe(
            page_rows,
            use_container_width=True,
            column_config={
                "URL": st.column_config.LinkColumn("URL", width="medium"),
            },
        )

        st.subheader("30項目の実施率（全ページ平均）")
        if is_aggregated:
            item_rows = []
            for ikey in sorted(site_agg["item_stats"].keys()):
                s = site_agg["item_stats"][ikey]
                item_rows.append({
                    "項目": ikey,
                    "平均得点": f"{s['avg_score']}/{s['max']}",
                    "達成率": f"{s['avg_pct']}%",
                    "完全実装率": f"{s['full_coverage_pct']}%",
                    "未実装率": f"{s['failure_pct']}%",
                })
            st.dataframe(item_rows, use_container_width=True)

    # Tab 2: テクニカル
    with tabs[2]:
        st.subheader("AIクローラーアクセス状況")
        crawler_rows = []
        for name, info in robots.get("crawlers", {}).items():
            status_emoji = "✅" if "許可" in info["status"] else ("⚠️" if "一部" in info["status"] else "🔴")
            crawler_rows.append({
                "クローラー": name,
                "ベンダー": info["vendor"],
                "状態": f"{status_emoji} {info['status']}",
            })
        st.dataframe(crawler_rows, use_container_width=True)

        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("llms.txt")
            if llms["exists"]:
                st.success(f"設置済み — {llms['summary']}")
            else:
                st.warning("未設置 — 改善提案にテンプレートを含めています")
            st.subheader("sitemap.xml")
            if sitemap.get("exists"):
                st.success(f"検出 ({sitemap.get('url_count',0)}URL)")
            else:
                st.warning("未検出")

        with col_r:
            st.subheader("PageSpeed (トップページ)")
            st.metric("Performance Score", pagespeed.get("score", 70))
            if pagespeed.get("lcp"):
                st.caption(f"LCP: {pagespeed['lcp']:.0f}ms")
            if pagespeed.get("cls") is not None:
                st.caption(f"CLS: {pagespeed['cls']:.4f}")
            if pagespeed.get("source") == "estimated_fallback":
                st.caption("※推定値")

        st.subheader("代表ページの構造化データ")
        jsonld_validations = validate_jsonld(structure.get("jsonld", []))
        if jsonld_validations:
            for v in jsonld_validations:
                status_icon = {"◎": "🟢", "○": "🟡", "△": "🔴"}.get(v["status"], "⚪")
                st.write(f"{status_icon} **{v['type']}** ({v['status']})")
                if v["missing_required"]:
                    st.caption(f"  欠落（必須）: {', '.join(v['missing_required'])}")
                if v["missing_recommended"]:
                    st.caption(f"  欠落（推奨）: {', '.join(v['missing_recommended'][:5])}")
        else:
            st.warning("構造化データ（JSON-LD）未検出")

    # Tab 3: 競合分析
    with tabs[3]:
        if competitor_analyses:
            st.subheader("📋 競合サマリ")
            summary_rows = []
            for i, c in enumerate(competitor_analyses, 1):
                summary_rows.append({
                    "#": f"競合{i}",
                    "ドメイン": c.get("domain", ""),
                    "サイト名": (c.get("title", "") or c.get("domain", ""))[:40],
                    "URL": c.get("url", ""),
                    "文字数": f"{c.get('word_count',0):,}",
                    "H2/H3": f"{c.get('h2_count',0)}/{c.get('h3_count',0)}",
                    "FAQ": c.get("faq_count", 0),
                    "構造化": c.get("sd_count", 0),
                    "著者": "○" if c.get("has_author") else "—",
                    "更新": f"{c.get('days_since_modified','—')}日前" if c.get('days_since_modified') is not None else "—",
                    "スコア": f"{c.get('score_pct', 0)}% ({c.get('grade','-')})",
                })
            st.dataframe(
                summary_rows, use_container_width=True,
                column_config={"URL": st.column_config.LinkColumn("URL", width="medium")},
            )

            if comparison.get("statistics"):
                st.subheader("📊 数値指標比較（代表ページ vs 競合）")
                stat_rows = []
                for s in comparison["statistics"]:
                    emoji = {"優位": "🟢", "同等": "🟡", "劣位": "🔴"}.get(s["verdict"], "")
                    stat_rows.append({
                        "指標": s["label"], "自サイト": s["self"],
                        "競合平均": s["competitor_avg"], "競合最大": s["competitor_max"],
                        "差分": f"{s['diff_vs_avg']:+.1f}",
                        "判定": f"{emoji} {s['verdict']}",
                    })
                st.dataframe(stat_rows, use_container_width=True)

            col_gap, col_adv = st.columns(2)
            with col_gap:
                if comparison.get("gaps"):
                    st.subheader("🔴 コンテンツギャップ")
                    for g in comparison["gaps"]:
                        e = "🔥" if g["impact"] == "高" else "⚡"
                        st.write(f"{e} **{g['item']}**")
                        st.caption(f"自: {g['self_score']} / 競合平均: {g['competitor_avg']}")
            with col_adv:
                if comparison.get("advantages"):
                    st.subheader("✅ 独自優位性")
                    for a in comparison["advantages"]:
                        st.write(f"🏆 **{a['item']}**")
                        st.caption(f"自: {a['self_score']} / 競合平均: {a['competitor_avg']}")

            st.subheader("🎯 トピックカバレッジ")
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                st.markdown("**🔄 共通トピック**")
                for t in comparison.get("shared_topics", [])[:10]:
                    st.write(f"- {t}")
            with col_t2:
                st.markdown("**🎖️ 自サイト独自**")
                uni = comparison.get("self_unique_topics", [])
                if uni:
                    for t in uni[:10]:
                        st.write(f"- {t}")
                else:
                    st.caption("独自語彙なし")
            with col_t3:
                st.markdown("**⚠️ カバー不足**")
                miss = comparison.get("missing_topics", [])
                if miss:
                    for t in miss[:10]:
                        st.write(f"- {t}")
                else:
                    st.caption("カバー率良好")

            fg = comparison.get("freshness_gap")
            if fg:
                st.subheader("⏰ 鮮度比較")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("代表ページ更新", f"{fg['self_days']}日前")
                with c2:
                    st.metric("競合中央値", f"{fg['competitor_median_days']}日前")
                if fg.get("is_stale"):
                    st.warning("⚠️ 競合より90日以上古い")

            st.subheader("🔍 競合サイト詳細プロフィール")
            for i, c in enumerate(competitor_analyses, 1):
                with st.expander(f"#{i} {c.get('domain','')} — {c.get('title','')[:50]} (スコア {c.get('score_pct',0)}% Grade {c.get('grade','-')})"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**基本情報**")
                        st.write(f"URL: {c.get('url','')}")
                        st.write(f"文字数: **{c.get('word_count',0):,}**")
                        st.write(f"段落数: {c.get('paragraph_count',0)}")
                        st.write(f"見出し: H1={c.get('h1_count',0)} / H2={c.get('h2_count',0)} / H3={c.get('h3_count',0)} / H4={c.get('h4_count',0)}")
                        st.write(f"リスト: {c.get('list_count',0)} / テーブル: {c.get('table_count',0)}")
                        st.markdown("**情報密度**")
                        st.write(f"数値データ: {c.get('number_count',0)}個（1000字あたり {c.get('number_density_per1k',0)}個）")
                        st.write(f"平均文長: {c.get('avg_sentence_length',0)}字 / 平均段落: {c.get('avg_paragraph_length',0)}字")
                    with col_b:
                        st.markdown("**AIO/LLMO対応**")
                        af_e = "✅" if c.get("has_answer_first") else "❌"
                        st.write(f"{af_e} Answer-first: {c.get('answer_first_type','なし')}")
                        st.write(f"FAQ: {c.get('faq_count',0)}件")
                        st.write(f"構造化: {', '.join(c.get('sd_types',[]))}")
                        st.markdown("**E-E-A-T**")
                        ae = "✅" if c.get("has_author") else "❌"
                        st.write(f"{ae} 著者: {c.get('author_name','') or 'なし'}")
                        st.write(f"参考文献リンク: {c.get('reference_link_count',0)}件")
                        st.write(f"外部/内部リンク: {c.get('external_link_count',0)}/{c.get('internal_link_count',0)}")
                        if c.get("modified_date"):
                            st.write(f"更新: {c['modified_date'][:10]}（{c.get('days_since_modified','-')}日前）")
                    if c.get("strengths"):
                        st.markdown("**💪 強み**: " + "、".join(c["strengths"]))
                    if c.get("weaknesses"):
                        st.markdown("**🕳️ 弱み**: " + "、".join(c["weaknesses"]))
                    if c.get("primary_entities"):
                        st.caption("主要語彙: " + "、".join(c["primary_entities"]))

            st.subheader("🔎 検索出現テスト")
            for kw, data in search_results_data.items():
                emoji = "🟢" if data["self_rank"] and data["self_rank"] <= 5 else ("🟡" if data["self_rank"] else "🔴")
                st.write(f"{emoji} 「{kw}」: **{data['status']}**")
                if data.get("results"):
                    with st.expander(f"  上位10サイト（{kw}）"):
                        for i, r in enumerate(data["results"][:10], 1):
                            st.caption(f"{i}. {r.get('title','')[:60]} — {urlparse(r.get('url','')).netloc}")
        else:
            st.info("競合分析は実行されていません")

    # Tab 4: 改善提案
    with tabs[4]:
        if improvements and not improvements.get("error"):
            total_count = (
                len(improvements.get("quick_wins", []))
                + len(improvements.get("strategic", []))
                + len(improvements.get("technical_debt", []))
                + len(improvements.get("content_strategy", []))
                + len(improvements.get("competitor_informed", []))
            )
            st.caption(f"計 {total_count} 件の改善施策を提案しています")

            if is_site_mode and site_agg.get("common_issues"):
                st.subheader("🎯 サイト全体優先施策（未実装率が高い項目）")
                for iss in site_agg["common_issues"][:8]:
                    st.error(f"**{iss['item_key']}** — {iss['failure_pct']}%のページで未実装 / 平均達成率 {iss['avg_pct']}%")
                st.caption("👆 これらは全ページに共通して修正が必要です")
                st.divider()

            qw = improvements.get("quick_wins", [])
            if qw:
                st.subheader(f"🚀 Quick Win — {len(qw)}件")
                for i, item in enumerate(qw, 1):
                    priority = item.get("priority", "A")
                    pe = {"S": "🔥", "A": "⚡", "B": "📌", "C": "💡"}.get(priority, "📌")
                    with st.expander(f"{pe} [優先度{priority}] {i}. {item.get('title', '')} （{item.get('effort', '—')} / {item.get('impact', '—')}）"):
                        if item.get("kpi"):
                            st.info(f"🎯 **期待KPI:** {item['kpi']}")
                        if item.get("why"):
                            st.markdown("#### なぜ重要か"); st.write(item["why"])
                        if item.get("steps"):
                            st.markdown("#### 実装ステップ")
                            for s in item["steps"]: st.write(s)
                        if item.get("before"):
                            st.markdown("#### Before"); st.code(item["before"], language="html")
                        if item.get("after"):
                            st.markdown("#### After（コピペ可）"); st.code(item["after"], language="html")
                        if item.get("validation"):
                            st.success(f"✅ 検証: {item['validation']}")
                        if item.get("template_file") == "llms_txt_template":
                            st.code(improvements.get("llms_txt_template", ""), language="markdown")

            for section_key, section_label in [
                ("competitor_informed", "🎯 競合ベース施策"),
                ("content_strategy", "📝 コンテンツ戦略"),
                ("technical_debt", "🔧 技術的負債の解消"),
                ("strategic", "📋 戦略施策（中長期）"),
            ]:
                items = improvements.get(section_key, [])
                if not items:
                    continue
                st.subheader(f"{section_label} — {len(items)}件")
                for i, item in enumerate(items, 1):
                    with st.expander(f"[優先度{item.get('priority','B')}] {i}. {item.get('title','')}"):
                        st.write(f"**工数:** {item.get('effort','—')} / **インパクト:** {item.get('impact','—')}")
                        if item.get("kpi"): st.info(f"🎯 {item['kpi']}")
                        if item.get("why"): st.write(item["why"])
                        if item.get("steps"):
                            for s in item["steps"]: st.write(s)
                        if item.get("missing_topics"):
                            for t in item["missing_topics"]: st.write(f"- {t}")

            mp = improvements.get("measurement_plan", [])
            if mp:
                st.subheader("📊 計測計画")
                for block in mp:
                    st.markdown(f"**{block.get('title','')}**")
                    for it in block.get("items", []): st.write(f"- {it}")

            st.divider()
            st.subheader("🧰 コピペ可能テンプレート")
            t1, t2, t3, t4 = st.tabs(["Organization", "Article", "FAQPage", "llms.txt"])
            with t1: st.code(improvements.get("organization_jsonld", ""), language="html")
            with t2: st.code(improvements.get("article_jsonld", ""), language="html")
            with t3: st.code(improvements.get("faq_jsonld", ""), language="html")
            with t4: st.code(improvements.get("llms_txt_template", ""), language="markdown")
        else:
            st.info("改善提案は実行されていません")

    # Tab 5: テストクエリ
    with tabs[5]:
        if test_queries and not test_queries.get("error"):
            st.subheader("商談実演用テストクエリ")
            for i, q in enumerate(test_queries.get("queries", []), 1):
                st.write(f"**{i}. {q.get('platform', '')}:** {q.get('query', '')}")
                st.caption(f"引用されない場合: {q.get('reason_if_not', '')}")
        else:
            st.info("テストクエリは生成されていません")

    # Tab 6: レポートDL
    with tabs[6]:
        report_md = generate_report_md(
            url=url, structure=structure, categories=categories,
            total=total, robots=robots, llms=llms, pagespeed=pagespeed,
            all_scores=all_scores, competitors=competitor_analyses,
            comparison=comparison, improvements=improvements,
            test_queries=test_queries,
        )

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="📥 Markdownレポート", data=report_md,
                file_name=f"aio-llmo-report-{self_domain}.md",
                mime="text/markdown", use_container_width=True,
            )
        with col_dl2:
            try:
                pptx_buf = generate_pptx_report(
                    url=url, structure=structure, total=total, categories=categories,
                    all_scores=all_scores, robots=robots, llms=llms, pagespeed=pagespeed,
                    competitors=competitor_analyses, comparison=comparison,
                    improvements=improvements, test_queries=test_queries,
                    cv_data=cv_data,
                    site_agg=site_agg if (is_site_mode or (is_paste_mode and len(page_results) > 1)) else None,
                    preset_id=preset_id,
                )
                st.download_button(
                    label="📊 クライアント提出用PPTX", data=pptx_buf,
                    file_name=f"AIO-LLMO-診断レポート-{self_domain}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True, type="primary",
                )
            except Exception as e:
                st.error(f"PPTX生成エラー: {e}")

        st.caption("💡 PPTXは13スライドの網羅的クライアント提出レポートです")

        with st.expander("レポートプレビュー（Markdown）"):
            st.markdown(report_md)

    # ============================================================
    # CV診断タブ（リクルーティングプリセット時のみ）
    # ============================================================
    if cv_data and cv_tab_index is not None:
        with tabs[cv_tab_index]:
            st.subheader("🎯 CV（面接応募）転換率診断")
            st.caption("採用ページの応募率を阻害する10要素を診断し、クライアント提出用の改善案を提示します")

            # サマリ
            cv_c1, cv_c2, cv_c3, cv_c4 = st.columns(4)
            with cv_c1:
                st.metric(
                    "CV診断スコア",
                    f"{cv_data['cv_total']}/100",
                    delta=f"Grade {cv_data['cv_grade']}",
                )
            with cv_c2:
                st.metric(
                    "推定CV率（現状）",
                    f"{cv_data['estimated_cv_rate']}%",
                    help="業界平均1.5〜3.0%・ベストプラクティス6%以上",
                )
            with cv_c3:
                st.metric(
                    "改善後CV率（予測）",
                    f"{cv_data['improved_cv_rate']}%",
                    delta=f"+{cv_data['potential_uplift_pct']}%",
                )
            with cv_c4:
                st.metric("ベンチマーク位置", cv_data["benchmark_position"])

            st.info(
                f"📊 **業界ベンチマーク**　業界平均: {cv_data['benchmark']['industry_avg_low']}〜{cv_data['benchmark']['industry_avg_high']}% / "
                f"ベストプラクティス: {cv_data['benchmark']['best_practice']}% / トップクラス: {cv_data['benchmark']['top_class']}%"
            )

            # 10要素レーダー
            st.subheader("🔍 CV阻害要因 10要素診断")
            factor_rows = []
            for f in cv_data["factors"]:
                pct = round(f["score"] / f["max"] * 100)
                emoji = "🟢" if pct >= 70 else ("🟡" if pct >= 40 else "🔴")
                factor_rows.append({
                    "判定": emoji,
                    "要素": f["label"],
                    "スコア": f"{f['score']}/{f['max']}",
                    "現状": f["current"],
                    "理想": f["ideal"],
                    "CV影響": f["cv_impact"],
                })
            st.dataframe(factor_rows, use_container_width=True, hide_index=True)

            # 改善案（クライアント提出用）
            st.subheader("💼 クライアント提出用 改善アイデア")
            ideas = cv_data.get("improvement_ideas", [])
            if not ideas:
                st.success("🎉 全要素で7点以上を獲得。大きな改善余地はありません。")
            else:
                st.caption(f"7点未満の要素について、優先順位S/A/B別の具体的改善案を{len(ideas)}件提示します")
                for i, idea in enumerate(ideas, 1):
                    pri_color = {"S": "🔴", "A": "🟠", "B": "🟡"}.get(idea["priority"], "⚪")
                    with st.expander(
                        f"{pri_color} 優先度{idea['priority']} 【{idea['factor_label']}】 {idea['title']}（現状{idea['current_score']}/{idea['max_score']}点）",
                        expanded=(i <= 2),
                    ):
                        ic1, ic2 = st.columns(2)
                        with ic1:
                            st.markdown(f"**期待CV改善効果:** {idea['expected_uplift']}")
                        with ic2:
                            st.markdown(f"**実装コスト:** {idea['cost']}")

                        st.markdown("**🛠 具体的アクション:**")
                        for action in idea["actions"]:
                            st.markdown(f"- {action}")

                        st.markdown("**💻 実装サンプルコード:**")
                        st.code(idea["code_sample"], language="html")

            # 改善ロードマップ
            st.subheader("📅 推奨実施ロードマップ")
            sorted_ideas = sorted(
                cv_data.get("improvement_ideas", []),
                key=lambda x: (
                    {"S": 0, "A": 1, "B": 2}.get(x["priority"], 3),
                    x["current_score"],
                ),
            )
            roadmap_rows = []
            for i, idea in enumerate(sorted_ideas, 1):
                phase = "Phase 1（〜30日）" if i <= 3 else ("Phase 2（〜60日）" if i <= 6 else "Phase 3（60日〜）")
                roadmap_rows.append({
                    "順位": i,
                    "実施フェーズ": phase,
                    "施策": idea["title"],
                    "対象要素": idea["factor_label"],
                    "優先度": idea["priority"],
                    "効果": idea["expected_uplift"],
                    "工数": idea["cost"],
                })
            if roadmap_rows:
                st.dataframe(roadmap_rows, use_container_width=True, hide_index=True)

            # 弱点トップ5
            st.subheader("⚠️ 最優先で取り組むべき弱点 TOP5")
            for i, w in enumerate(cv_data["weak_factors"], 1):
                st.markdown(f"**{i}. {w['label']}** — {w['score']}/{w['max']}点　{w['issue']}")

elif run_btn and not url:
    st.warning("URLを入力してください")
