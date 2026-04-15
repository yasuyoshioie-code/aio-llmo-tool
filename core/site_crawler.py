"""サイト全体をクロール・サンプリングするモジュール

戦略:
  1. sitemap.xml を解析（index型にも対応、最大3階層）
  2. sitemapが無い/少ない → Tavily crawl でフォールバック
  3. 取得したURL群から戦略的にサンプリング:
     - トップページ必須
     - URLパターン別に分類（記事/カテゴリ/固定ページ）
     - 各カテゴリから均等サンプリング
  4. サンプル数は sample_size（デフォルト20）
"""

import re
import random
import httpx
from urllib.parse import urlparse, urljoin
from xml.etree import ElementTree as ET

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

SITEMAP_CANDIDATES = [
    "sitemap.xml", "sitemap_index.xml", "sitemap1.xml",
    "sitemap-index.xml", "wp-sitemap.xml", "sitemap/sitemap.xml",
]


def _fetch_url(url: str, timeout: int = 20) -> str:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as http:
            resp = http.get(url, headers={"User-Agent": UA})
            if resp.status_code == 200:
                return resp.text
    except Exception:
        pass
    return ""


def _parse_sitemap_xml(xml_text: str, base_url: str, depth: int = 0, max_depth: int = 3) -> list[str]:
    """sitemap.xmlを解析し、全URL（loc）を返す。sitemapindex型は再帰的に展開。"""
    if depth > max_depth:
        return []
    urls = []
    try:
        # XMLネームスペース除去
        xml_clean = re.sub(r'\sxmlns="[^"]+"', '', xml_text, count=1)
        root = ET.fromstring(xml_clean)

        if "sitemapindex" in root.tag.lower() or root.tag.endswith("sitemapindex"):
            # index型 — 子sitemapを再帰取得
            for sm in root.iter("sitemap"):
                loc_elem = sm.find("loc")
                if loc_elem is not None and loc_elem.text:
                    child_xml = _fetch_url(loc_elem.text.strip())
                    if child_xml:
                        urls.extend(_parse_sitemap_xml(child_xml, base_url, depth + 1, max_depth))
        else:
            # urlset型
            for u in root.iter("url"):
                loc_elem = u.find("loc")
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text.strip())
    except Exception:
        # ElementTree失敗 → 正規表現でフォールバック
        urls = re.findall(r"<loc>([^<]+)</loc>", xml_text)

    return urls


def discover_sitemap_urls(base_url: str) -> dict:
    """全sitemap候補を試してURL一覧を取得。"""
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    result = {"urls": [], "source": "", "sitemap_url": "", "total_found": 0}

    # robots.txt から Sitemap: を取得
    robots_txt = _fetch_url(urljoin(origin + "/", "robots.txt"))
    sitemap_urls_from_robots = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_txt)

    candidates = sitemap_urls_from_robots + [
        urljoin(origin + "/", path) for path in SITEMAP_CANDIDATES
    ]

    for sm_url in candidates:
        xml_text = _fetch_url(sm_url)
        if xml_text and ("<urlset" in xml_text or "<sitemapindex" in xml_text):
            urls = _parse_sitemap_xml(xml_text, origin)
            if urls:
                # 同一ドメインのみ
                same_domain = [u for u in urls if parsed.netloc in urlparse(u).netloc]
                if same_domain:
                    result["urls"] = list(dict.fromkeys(same_domain))  # 重複除去
                    result["source"] = "sitemap"
                    result["sitemap_url"] = sm_url
                    result["total_found"] = len(result["urls"])
                    return result

    result["source"] = "not_found"
    return result


def _classify_url(url: str, base_path: str = "") -> str:
    """URLパターン別に分類: home / category / article / tag / page / media"""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    if path == "" or path == "/" or path == base_path.rstrip("/"):
        return "home"
    if re.search(r"/(tag|tags)/", path):
        return "tag"
    if re.search(r"/(category|cat|categories)/", path):
        return "category"
    if re.search(r"\.(jpg|png|gif|pdf|mp4)$", path, re.IGNORECASE):
        return "media"
    # ドット含まず深さ2-4 + 末尾英数・スラッシュ → 記事
    segments = [s for s in path.split("/") if s]
    if 1 <= len(segments) <= 5:
        # 記事っぽいパス（長めのslug or 数字）
        last = segments[-1]
        if len(last) >= 8 or any(c.isdigit() for c in last):
            return "article"
        return "page"
    return "page"


def sample_site_pages(
    urls: list[str],
    base_url: str,
    sample_size: int = 20,
) -> list[dict]:
    """URL一覧から戦略的にサンプリング。

    戦略:
      - トップページは必ず含める
      - 記事 / カテゴリ / 固定ページから比例配分
      - 同一カテゴリに偏らないよう分散
    """
    parsed_base = urlparse(base_url)
    base_path = parsed_base.path

    classified: dict[str, list[str]] = {
        "home": [], "article": [], "category": [], "page": [], "tag": [], "media": [],
    }
    for u in urls:
        t = _classify_url(u, base_path)
        classified.setdefault(t, []).append(u)

    # 配分（articleを最優先、次にpage、category、home）
    target_distribution = {
        "home": 1,
        "article": max(1, int(sample_size * 0.6)),   # 60%
        "page": max(1, int(sample_size * 0.2)),       # 20%
        "category": max(1, int(sample_size * 0.15)),  # 15%
        "tag": 0,
        "media": 0,
    }
    # 余剰
    used = sum(target_distribution.values())
    if used < sample_size:
        target_distribution["article"] += (sample_size - used)

    sampled: list[dict] = []

    # トップページ（または指定URL）
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    if classified["home"]:
        sampled.append({"url": classified["home"][0], "type": "home"})
    else:
        sampled.append({"url": origin + "/", "type": "home"})

    # 各カテゴリから均等サンプリング
    for cat, target_n in target_distribution.items():
        if cat == "home" or target_n == 0:
            continue
        pool = classified.get(cat, [])
        if not pool:
            continue
        random.seed(42)  # 再現性
        chunk_size = max(1, len(pool) // max(target_n, 1))
        # 等間隔サンプリング（均等に散らす）
        step = max(1, len(pool) // target_n)
        picked = pool[::step][:target_n]
        for u in picked:
            if u not in [s["url"] for s in sampled]:
                sampled.append({"url": u, "type": cat})

    # 足りなければarticleから追加
    if len(sampled) < sample_size:
        for u in classified.get("article", []):
            if u not in [s["url"] for s in sampled]:
                sampled.append({"url": u, "type": "article"})
                if len(sampled) >= sample_size:
                    break
    # それでも足りなければ他カテゴリ
    if len(sampled) < sample_size:
        for cat in ["page", "category", "tag"]:
            for u in classified.get(cat, []):
                if u not in [s["url"] for s in sampled]:
                    sampled.append({"url": u, "type": cat})
                    if len(sampled) >= sample_size:
                        break
            if len(sampled) >= sample_size:
                break

    return sampled[:sample_size]


def discover_links_from_page(base_url: str, max_pages: int = 5) -> list[str]:
    """sitemap.xmlがない場合のフォールバック: 入力URLとそのリンク先を辿って同一ドメインのリンクを収集。

    入力URLパス配下を優先（例: /career/ なら /career/* を優先収集）。
    最大 max_pages ページまで再帰してリンク収集（広がりすぎ防止）。
    """
    parsed_base = urlparse(base_url)
    base_path = parsed_base.path or "/"
    same_domain = parsed_base.netloc

    visited: set[str] = set()
    queue: list[str] = [base_url]
    found_urls: set[str] = set()

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        html = _fetch_url(url)
        if not html:
            continue

        # href抽出
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        for href in hrefs:
            # 絶対URL化
            if href.startswith("//"):
                full = parsed_base.scheme + ":" + href
            elif href.startswith("/"):
                full = f"{parsed_base.scheme}://{same_domain}{href}"
            elif href.startswith("http"):
                full = href
            else:
                full = urljoin(url, href)

            p = urlparse(full)
            # 同一ドメインのみ
            if p.netloc != same_domain:
                continue
            # 拡張子で除外（画像/CSS/JS/PDF等）
            if re.search(r"\.(jpg|jpeg|png|gif|webp|svg|ico|css|js|pdf|mp4|webm|woff|woff2|ttf|xml|json|php)(\?|$)", p.path, re.IGNORECASE):
                continue
            # WordPress系API/RSS等を除外
            if re.search(r"/(wp-json|wp-admin|wp-login|xmlrpc|feed|trackback|comments)(/|$)", p.path, re.IGNORECASE):
                continue
            # クエリ・フラグメント除去
            clean = f"{p.scheme}://{p.netloc}{p.path}"
            if clean.endswith("/") is False and "." not in p.path.rsplit("/", 1)[-1]:
                pass  # 末尾スラッシュ無くてもOK

            found_urls.add(clean)

            # 同一path配下を優先的に追加クロール対象に
            if base_path != "/" and base_path in p.path and clean not in visited and clean not in queue:
                if len(queue) < max_pages * 3:
                    queue.append(clean)

    return list(found_urls)


def get_site_urls(base_url: str, tavily_key: str = "", sample_size: int = 20) -> dict:
    """サイト全体のURL取得 → サンプリング。失敗時もtop pageは必ず含む。

    フォールバックチェーン:
      1. sitemap.xml探索（標準6パターン + robots.txt）
      2. 入力URLからHTMLリンク辿り（同一ドメイン・同一パス配下優先）
      3. それでも0件 → 入力URLのみ
    """
    discovered = discover_sitemap_urls(base_url)
    urls = discovered.get("urls", [])
    source = discovered.get("source", "")

    # sitemapが取れなかった場合 → ページのリンク辿りでフォールバック
    if not urls:
        crawled = discover_links_from_page(base_url, max_pages=8)
        if crawled:
            urls = crawled
            source = "html_crawl"

    # それでも空 → 入力URLのみ
    if not urls:
        urls = [base_url]
        source = "input_only"

    # 入力URLのパス配下を優先サンプリング（例: /career/ なら /career/* を優先）
    parsed_base = urlparse(base_url)
    base_path = parsed_base.path.rstrip("/")
    if base_path and base_path != "":
        path_filtered = [u for u in urls if base_path in urlparse(u).path]
        if len(path_filtered) >= 3:
            # path配下が十分あれば、それを優先（入力URL自体も先頭に）
            if base_url not in path_filtered:
                path_filtered.insert(0, base_url)
            urls = path_filtered + [u for u in urls if u not in path_filtered]

    samples = sample_site_pages(urls, base_url, sample_size=sample_size)

    return {
        "total_urls_discovered": discovered.get("total_found", len(urls)),
        "sitemap_url": discovered.get("sitemap_url", ""),
        "source": source or discovered.get("source", "fallback"),
        "sampled_pages": samples,
        "all_urls": urls[:500],
    }
