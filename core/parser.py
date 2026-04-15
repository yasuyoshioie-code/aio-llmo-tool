"""HTML解析モジュール — LLM不要のPython解析"""

import re
import json
from bs4 import BeautifulSoup


def parse_html(raw_html: str) -> dict:
    """HTMLソースから構造情報を抽出。LLM不要。"""
    if not raw_html:
        return _empty_result()

    soup = BeautifulSoup(raw_html, "lxml")
    return {
        "title": _get_title(soup),
        "meta_description": _get_meta(soup, "description"),
        "meta_robots": _get_meta(soup, "robots"),
        "canonical": _get_canonical(soup),
        "ogp": _get_ogp(soup),
        "viewport": bool(soup.find("meta", attrs={"name": "viewport"})),
        "headings": _get_headings(soup),
        "heading_issues": _check_heading_issues(soup),
        "word_count": _count_words(soup),
        "paragraph_count": len(soup.find_all("p")),
        "list_count": len(soup.find_all(["ul", "ol"])),
        "table_count": len(soup.find_all("table")),
        "jsonld": _get_jsonld(soup),
        "faq_items": _detect_faq(soup),
        "dates": _detect_dates(soup),
        "author": _detect_author(soup),
        "images_without_alt": _count_images_without_alt(soup),
        "internal_links": 0,
        "external_links": 0,
        "content_text": _get_body_text(soup),
    }


def parse_from_markdown(content: str, raw_html: str = "") -> dict:
    """Tavilyのmarkdown出力 + raw_htmlから構造情報を抽出。"""
    if raw_html:
        result = parse_html(raw_html)
        result["content_text"] = content or result["content_text"]
        return result

    # markdownのみの場合
    headings = []
    for m in re.finditer(r"^(#{1,4})\s+(.+)$", content, re.MULTILINE):
        headings.append({"level": len(m.group(1)), "text": m.group(2).strip()})

    words = len(content)
    paragraphs = len([p for p in content.split("\n\n") if p.strip()])

    return {
        "title": headings[0]["text"] if headings else "",
        "meta_description": "",
        "meta_robots": "",
        "canonical": "",
        "ogp": {},
        "viewport": True,
        "headings": headings,
        "heading_issues": [],
        "word_count": words,
        "paragraph_count": paragraphs,
        "list_count": content.count("\n- ") + content.count("\n* "),
        "table_count": content.count("| ---"),
        "jsonld": [],
        "faq_items": _detect_faq_from_text(content),
        "dates": {},
        "author": {},
        "images_without_alt": 0,
        "internal_links": 0,
        "external_links": 0,
        "content_text": content,
    }


# --- 内部ヘルパー ---


def _empty_result() -> dict:
    return {
        "title": "", "meta_description": "", "meta_robots": "",
        "canonical": "", "ogp": {}, "viewport": False,
        "headings": [], "heading_issues": [], "word_count": 0,
        "paragraph_count": 0, "list_count": 0, "table_count": 0,
        "jsonld": [], "faq_items": [], "dates": {}, "author": {},
        "images_without_alt": 0, "internal_links": 0,
        "external_links": 0, "content_text": "",
    }


def _get_title(soup: BeautifulSoup) -> str:
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else ""


def _get_meta(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": name})
    if not tag:
        tag = soup.find("meta", attrs={"property": f"og:{name}"})
    return tag.get("content", "") if tag else ""


def _get_canonical(soup: BeautifulSoup) -> str:
    tag = soup.find("link", attrs={"rel": "canonical"})
    return tag.get("href", "") if tag else ""


def _get_ogp(soup: BeautifulSoup) -> dict:
    ogp = {}
    for tag in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
        key = tag.get("property", "").replace("og:", "")
        ogp[key] = tag.get("content", "")
    return ogp


def _get_headings(soup: BeautifulSoup) -> list[dict]:
    headings = []
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        level = int(tag.name[1])
        headings.append({"level": level, "text": tag.get_text(strip=True)})
    return headings


def _check_heading_issues(soup: BeautifulSoup) -> list[str]:
    issues = []
    h1_tags = soup.find_all("h1")
    if len(h1_tags) == 0:
        issues.append("H1タグなし")
    elif len(h1_tags) > 1:
        issues.append(f"H1タグが{len(h1_tags)}個（1個推奨）")

    headings = _get_headings(soup)
    for i in range(1, len(headings)):
        if headings[i]["level"] - headings[i - 1]["level"] > 1:
            issues.append(
                f"見出し階層飛ばし: H{headings[i-1]['level']}→H{headings[i]['level']}"
                f"（{headings[i]['text'][:20]}）"
            )
    return issues


def _count_words(soup: BeautifulSoup) -> int:
    text = soup.get_text(separator=" ", strip=True)
    return len(text)


def _get_body_text(soup: BeautifulSoup) -> str:
    body = soup.find("body")
    if not body:
        return ""
    for tag in body.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return body.get_text(separator="\n", strip=True)


def _get_jsonld(soup: BeautifulSoup) -> list[dict]:
    schemas = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                schemas.extend(data)
            else:
                schemas.append(data)
        except (json.JSONDecodeError, TypeError):
            pass
    return schemas


def _detect_faq(soup: BeautifulSoup) -> list[dict]:
    """FAQ Q&Aペアを検出（JSON-LD + HTML構造）"""
    items = []

    # JSON-LDからFAQ検出
    for schema in _get_jsonld(soup):
        if schema.get("@type") == "FAQPage":
            for q in schema.get("mainEntity", []):
                items.append({
                    "question": q.get("name", ""),
                    "answer": q.get("acceptedAnswer", {}).get("text", ""),
                    "source": "jsonld",
                })

    # HTML構造からFAQ検出（dt/dd, details/summary等）
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            items.append({
                "question": dt.get_text(strip=True),
                "answer": dd.get_text(strip=True)[:200],
                "source": "html_dl",
            })

    for details in soup.find_all("details"):
        summary = details.find("summary")
        if summary:
            items.append({
                "question": summary.get_text(strip=True),
                "answer": details.get_text(strip=True)[:200],
                "source": "html_details",
            })

    return items


def _detect_faq_from_text(text: str) -> list[dict]:
    """マークダウンテキストからFAQパターンを検出。"""
    items = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^#{2,3}\s*.*(よくある質問|FAQ|Q\s*[.:]|質問)", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 30, len(lines))):
                if re.match(r"^#{2,3}\s*Q[.:\s]", lines[j]):
                    items.append({"question": lines[j], "answer": "", "source": "text"})
    return items


def _detect_dates(soup: BeautifulSoup) -> dict:
    dates = {}

    # JSON-LDから
    for schema in _get_jsonld(soup):
        if schema.get("datePublished"):
            dates["published"] = schema["datePublished"]
        if schema.get("dateModified"):
            dates["modified"] = schema["dateModified"]

    # HTML time要素から
    for time_tag in soup.find_all("time"):
        dt = time_tag.get("datetime", "")
        cls = " ".join(time_tag.get("class", []))
        text = time_tag.parent.get_text(strip=True) if time_tag.parent else ""
        if "publish" in cls or "post" in cls or "公開" in text:
            dates.setdefault("published", dt)
        elif "modif" in cls or "update" in cls or "更新" in text:
            dates.setdefault("modified", dt)
        elif dt and "published" not in dates:
            dates.setdefault("published", dt)

    return dates


def _detect_author(soup: BeautifulSoup) -> dict:
    author = {}

    # JSON-LDから
    for schema in _get_jsonld(soup):
        a = schema.get("author")
        if isinstance(a, dict):
            author["name"] = a.get("name", "")
            author["url"] = a.get("url", "")
            author["source"] = "jsonld"
        elif isinstance(a, str):
            author["name"] = a
            author["source"] = "jsonld"

    # rel=authorから
    if not author.get("name"):
        link = soup.find("a", attrs={"rel": "author"})
        if link:
            author["name"] = link.get_text(strip=True)
            author["url"] = link.get("href", "")
            author["source"] = "html_rel"

    # meta authorから
    if not author.get("name"):
        meta = soup.find("meta", attrs={"name": "author"})
        if meta:
            author["name"] = meta.get("content", "")
            author["source"] = "meta"

    return author


def _count_images_without_alt(soup: BeautifulSoup) -> int:
    count = 0
    for img in soup.find_all("img"):
        alt = img.get("alt", "").strip()
        if not alt:
            count += 1
    return count
