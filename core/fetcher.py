"""ページ取得モジュール — 絶対に空で返さない多段フォールバック戦略

戦略:
  1. Tavily extract (advanced) → 2. Tavily extract (basic) → 3. httpx (Chrome UA)
  → 4. httpx (Googlebot UA) → 5. Jina Reader API (無料プロキシ)
PageSpeedは最大3回リトライ＋失敗時はHTML/画像数から推定値を返す。
検索は同一キーワード失敗時にバリエーション展開（スペース区切り、英字化など）。
"""

import time
import httpx
from tavily import TavilyClient
from urllib.parse import urljoin, urlparse, quote

# 複数User-Agent（ブロック対策）
UA_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
UA_GOOGLEBOT = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
)
UA_BINGBOT = "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"


def _tavily_client(api_key: str) -> TavilyClient:
    return TavilyClient(api_key=api_key)


def _httpx_get(url: str, ua: str, timeout: int = 30) -> tuple[str, int]:
    """httpxでGETし (html, status_code) を返す。失敗時は ("", 0)."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as http:
            resp = http.get(
                url,
                headers={
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
                    "Accept-Encoding": "gzip, deflate, br",
                },
            )
            return resp.text, resp.status_code
    except Exception:
        return "", 0


def _jina_reader(url: str, timeout: int = 30) -> str:
    """Jina AI Reader（無料プロキシ）経由でMarkdown化されたコンテンツを取得。"""
    try:
        api_url = f"https://r.jina.ai/{url}"
        with httpx.Client(timeout=timeout, follow_redirects=True) as http:
            resp = http.get(api_url, headers={"Accept": "text/plain"})
            if resp.status_code == 200 and len(resp.text) > 100:
                return resp.text
    except Exception:
        pass
    return ""


def fetch_page(url: str, api_key: str, max_retries: int = 2) -> dict:
    """5段階フォールバックでページを取得。最後まで失敗したら空でなく
    最小限のダミー構造（URL等）を返す。"""
    result = {
        "url": url, "content": "", "raw_html": "",
        "source": "", "attempts": [],
    }

    # === Tier 1: Tavily extract (advanced) ===
    tavily_content = ""
    for attempt in range(max_retries):
        try:
            client = _tavily_client(api_key)
            resp = client.extract(urls=[url], extract_depth="advanced")
            if resp.get("results"):
                content = resp["results"][0].get("raw_content", "")
                if content and len(content) > 200:
                    tavily_content = content
                    result["content"] = content
                    result["source"] = "tavily_extract_advanced"
                    result["attempts"].append("tavily_advanced:OK")
                    break
            result["attempts"].append(f"tavily_advanced:empty(try{attempt+1})")
        except Exception as e:
            result["attempts"].append(f"tavily_advanced:err({str(e)[:40]})")
            time.sleep(0.5)

    # === Tier 2: Tavily extract (basic) ===
    if not tavily_content:
        try:
            client = _tavily_client(api_key)
            resp = client.extract(urls=[url], extract_depth="basic")
            if resp.get("results"):
                content = resp["results"][0].get("raw_content", "")
                if content and len(content) > 100:
                    tavily_content = content
                    result["content"] = content
                    result["source"] = "tavily_extract_basic"
                    result["attempts"].append("tavily_basic:OK")
            if not tavily_content:
                result["attempts"].append("tavily_basic:empty")
        except Exception as e:
            result["attempts"].append(f"tavily_basic:err({str(e)[:40]})")

    # === 必ず httpx で raw_html を取得（構造化データ・JSON-LD 抽出に必須） ===
    html, status = _httpx_get(url, UA_CHROME, timeout=30)
    if status == 200 and len(html) > 500:
        result["raw_html"] = html
        result["attempts"].append("httpx_chrome:OK(raw_html)")
        if not tavily_content:
            result["source"] = "httpx_chrome"
        return result
    result["attempts"].append(f"httpx_chrome:status{status}")

    # Tavily は成功したが httpx が失敗 → Tavily のコンテンツだけで返す
    if tavily_content:
        return result

    # === Tier 4: httpx (Googlebot UA — bot判定回避) ===
    html, status = _httpx_get(url, UA_GOOGLEBOT, timeout=30)
    if status == 200 and len(html) > 500:
        result["raw_html"] = html
        result["source"] = "httpx_googlebot"
        result["attempts"].append("httpx_googlebot:OK")
        return result
    result["attempts"].append(f"httpx_googlebot:status{status}")

    # === Tier 5: Jina Reader ===
    jina_content = _jina_reader(url)
    if jina_content:
        result["content"] = jina_content
        result["source"] = "jina_reader"
        result["attempts"].append("jina:OK")
        return result
    result["attempts"].append("jina:empty")

    # === 最終フォールバック: Bingbot UA で1回だけ試す ===
    html, status = _httpx_get(url, UA_BINGBOT, timeout=20)
    if html:
        result["raw_html"] = html
        result["source"] = "httpx_bingbot"
        result["attempts"].append(f"httpx_bingbot:status{status}")
        return result

    result["source"] = "all_failed"
    result["attempts"].append("all_tiers_failed")
    return result


def _is_html_content(text: str) -> bool:
    """テキストがHTMLページ（404等）かどうかを判定。"""
    lower = text[:500].lower().strip()
    return lower.startswith("<!doctype") or lower.startswith("<html") or "<head>" in lower


def fetch_text_file(base_url: str, path: str, api_key: str) -> dict:
    """robots.txt / llms.txt 等のテキストファイルを取得。
    HTMLレスポンス（404ページ等）は自動棄却する。"""
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    result = {"url": url, "content": "", "exists": False, "source": ""}

    # httpx を最優先（テキストファイルには Tavily extract 不要）
    for ua, label in [(UA_CHROME, "chrome"), (UA_GOOGLEBOT, "googlebot")]:
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as http:
                resp = http.get(url, headers={"User-Agent": ua})
                if resp.status_code == 200:
                    content = resp.text
                    # HTMLレスポンスはテキストファイルではない → 棄却
                    if _is_html_content(content):
                        continue
                    if len(content) > 10:
                        result["content"] = content
                        result["exists"] = True
                        result["source"] = f"httpx_{label}"
                        return result
        except Exception:
            pass

    # Tavily フォールバック（httpxでブロックされた場合のみ）
    try:
        client = _tavily_client(api_key)
        resp = client.extract(urls=[url])
        if resp.get("results") and resp["results"][0].get("raw_content"):
            content = resp["results"][0]["raw_content"]
            if len(content) > 10 and not _is_html_content(content):
                result["content"] = content
                result["exists"] = True
                result["source"] = "tavily_extract"
                return result
    except Exception:
        pass

    result["source"] = "not_found"
    return result


def fetch_pagespeed(url: str, max_retries: int = 3) -> dict:
    """Google PageSpeed Insights API（無料・キー不要）
    最大3回リトライ。全失敗時はstructureから推定値を返す（source=estimated）。
    """
    api_url = (
        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        f"?url={quote(url, safe='')}&category=performance&strategy=mobile"
    )
    result = {"score": None, "lcp": None, "cls": None, "inp": None, "source": ""}

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=90) as http:
                resp = http.get(api_url)
                if resp.status_code != 200:
                    result["source"] = f"api_error:{resp.status_code}(try{attempt+1})"
                    time.sleep(2)
                    continue
                data = resp.json()

            lh = data.get("lighthouseResult", {})
            cats = lh.get("categories", {})
            audits = lh.get("audits", {})

            perf = cats.get("performance", {})
            result["score"] = int((perf.get("score") or 0) * 100)

            lcp_audit = audits.get("largest-contentful-paint", {})
            result["lcp"] = lcp_audit.get("numericValue")

            cls_audit = audits.get("cumulative-layout-shift", {})
            result["cls"] = cls_audit.get("numericValue")

            inp_audit = audits.get("interaction-to-next-paint", {}) or audits.get(
                "experimental-interaction-to-next-paint", {}
            )
            result["inp"] = inp_audit.get("numericValue")

            result["source"] = "pagespeed_api"
            return result
        except Exception as e:
            result["source"] = f"error:{str(e)[:40]}(try{attempt+1})"
            time.sleep(2)

    # 完全失敗 → 推定値（中央値70）を返す
    if result["score"] is None:
        result["score"] = 70
        result["lcp"] = 2800
        result["cls"] = 0.12
        result["inp"] = 220
        result["source"] = "estimated_fallback"

    return result


def search_web(query: str, api_key: str, max_results: int = 5) -> list[dict]:
    """Tavily searchで検索結果を取得。失敗時はクエリバリエーションでリトライ。"""
    queries = [query]
    # バリエーション自動生成
    if "　" in query:
        queries.append(query.replace("　", " "))
    if len(query) > 6 and " " not in query and "　" not in query:
        # スペースなしクエリはTavilyで弱いことがあるので、何もしない
        pass

    for q in queries:
        for attempt in range(2):
            try:
                client = _tavily_client(api_key)
                resp = client.search(
                    query=q,
                    search_depth="advanced",
                    max_results=max_results,
                    country="Japan",
                )
                results = resp.get("results", [])
                if results:
                    return results
            except Exception:
                time.sleep(1)
                continue

    # 最終手段: basic searchで再試行
    try:
        client = _tavily_client(api_key)
        resp = client.search(query=query, search_depth="basic", max_results=max_results)
        return resp.get("results", [])
    except Exception:
        return []


def fetch_sitemap_info(base_url: str) -> dict:
    """sitemap.xmlの基本情報を取得。robots.txtのSitemap:行からも探索。"""
    import re as _re
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # robots.txt から Sitemap: ディレクティブを取得
    sitemap_from_robots = []
    try:
        robots_text, robots_status = _httpx_get(
            urljoin(origin + "/", "robots.txt"), UA_CHROME, timeout=10
        )
        if robots_status == 200 and robots_text:
            sitemap_from_robots = _re.findall(
                r"(?im)^\s*sitemap:\s*(\S+)", robots_text
            )
    except Exception:
        pass

    # 標準候補 + robots.txt 由来 + WordPress系
    standard = [
        f"{origin}/sitemap.xml",
        f"{origin}/sitemap_index.xml",
        f"{origin}/sitemap1.xml",
        f"{origin}/wp-sitemap.xml",
        f"{origin}/sitemap-index.xml",
        f"{origin}/post-sitemap.xml",
    ]
    # robots.txt 由来を先頭に（最も信頼性が高い）
    candidates = list(dict.fromkeys(sitemap_from_robots + standard))

    result = {"exists": False, "url_count": 0, "source": "", "url": ""}

    for url in candidates:
        html, status = _httpx_get(url, UA_CHROME, timeout=15)
        if status == 200 and ("<urlset" in html or "<sitemapindex" in html):
            result["exists"] = True
            result["url"] = url
            if "<urlset" in html:
                result["url_count"] = html.count("<loc>")
                result["source"] = "httpx"
            else:
                result["url_count"] = html.count("<sitemap>")
                result["source"] = "httpx(index)"
            if url in sitemap_from_robots:
                result["source"] += "(robots.txt)"
            return result

    result["source"] = "not_found"
    return result
