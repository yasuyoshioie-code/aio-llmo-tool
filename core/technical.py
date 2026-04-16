"""テクニカルチェックモジュール — robots.txt, llms.txt, JSON-LD検証（LLM不要）"""

import re

# AIクローラー一覧
AI_CRAWLERS = {
    "GPTBot": {"vendor": "OpenAI", "agent": "GPTBot"},
    "Google-Extended": {"vendor": "Google (Gemini)", "agent": "Google-Extended"},
    "ClaudeBot": {"vendor": "Anthropic", "agent": "ClaudeBot"},
    "PerplexityBot": {"vendor": "Perplexity", "agent": "PerplexityBot"},
    "CCBot": {"vendor": "Common Crawl", "agent": "CCBot"},
    "Bytespider": {"vendor": "ByteDance", "agent": "Bytespider"},
}


def analyze_robots_txt(content: str) -> dict:
    """robots.txtの内容を解析し、AIクローラーの許可状況を返す。"""
    result = {"crawlers": {}, "raw": content}

    if not content:
        for name, info in AI_CRAWLERS.items():
            result["crawlers"][name] = {
                "vendor": info["vendor"],
                "status": "未設定（デフォルト許可）",
                "matched_line": "",
            }
        return result

    lines = content.strip().split("\n")

    # User-agentブロックをパース
    blocks: list[dict] = []
    current_agents: list[str] = []
    current_rules: list[str] = []

    for line in lines:
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if line.lower().startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            if current_rules:
                blocks.append({"agents": current_agents[:], "rules": current_rules[:]})
                current_agents = []
                current_rules = []
            current_agents.append(agent)
        else:
            current_rules.append(line)

    if current_agents:
        blocks.append({"agents": current_agents, "rules": current_rules})

    # 各AIクローラーの状態を判定
    for name, info in AI_CRAWLERS.items():
        status = "未設定（デフォルト許可）"
        matched = ""

        for block in blocks:
            agents_lower = [a.lower() for a in block["agents"]]
            if info["agent"].lower() in agents_lower or "*" in agents_lower:
                specific = info["agent"].lower() in agents_lower
                for rule in block["rules"]:
                    if rule.lower().startswith("disallow:"):
                        path = rule.split(":", 1)[1].strip()
                        if path == "/" or path == "":
                            if path == "/":
                                status = "ブロック" if specific else "ブロック（*で）"
                                matched = f"User-agent: {info['agent'] if specific else '*'}\n{rule}"
                            # Disallow: (空) は許可の意味
                        elif path:
                            status = f"一部ブロック（{path}）"
                            matched = rule
                    elif rule.lower().startswith("allow:"):
                        if specific:
                            status = "明示的許可"
                            matched = f"User-agent: {info['agent']}\n{rule}"

        result["crawlers"][name] = {
            "vendor": info["vendor"],
            "status": status,
            "matched_line": matched,
        }

    return result


def analyze_llms_txt(content: str, exists: bool) -> dict:
    """llms.txtの内容を分析。"""
    result = {
        "exists": exists,
        "format": "N/A",
        "has_site_info": False,
        "has_urls": False,
        "has_services": False,
        "summary": "",
    }

    if not exists or not content:
        result["summary"] = "未設置"
        return result

    # Markdown形式チェック
    if re.search(r"^#\s+", content, re.MULTILINE):
        result["format"] = "Markdown形式"
    else:
        result["format"] = "プレーンテキスト"

    # 内容チェック
    result["has_site_info"] = bool(
        re.search(r"(about|概要|会社|サイト)", content, re.IGNORECASE)
    )
    result["has_urls"] = bool(re.search(r"https?://", content))
    result["has_services"] = bool(
        re.search(r"(service|サービス|製品|product)", content, re.IGNORECASE)
    )

    quality_items = [result["has_site_info"], result["has_urls"], result["has_services"]]
    filled = sum(quality_items)
    if filled >= 3:
        result["summary"] = "充実（サイト情報・URL・サービス情報あり）"
    elif filled >= 1:
        result["summary"] = f"基本情報あり（{filled}/3項目）"
    else:
        result["summary"] = "内容不十分"

    return result


def validate_jsonld(schemas: list[dict]) -> list[dict]:
    """JSON-LDの必須プロパティをチェック。"""
    results = []

    # 期待するスキーマと必須/推奨プロパティ
    schema_specs = {
        "Organization": {
            "required": ["name", "url"],
            "recommended": ["logo", "contactPoint", "sameAs", "address"],
        },
        "Article": {
            "required": ["headline", "author", "datePublished"],
            "recommended": ["dateModified", "image", "publisher", "description"],
        },
        "BlogPosting": {
            "required": ["headline", "author", "datePublished"],
            "recommended": ["dateModified", "image", "publisher", "description"],
        },
        "FAQPage": {
            "required": ["mainEntity"],
            "recommended": [],
        },
        "BreadcrumbList": {
            "required": ["itemListElement"],
            "recommended": [],
        },
        "LocalBusiness": {
            "required": ["name", "address"],
            "recommended": ["telephone", "openingHours", "geo", "priceRange"],
        },
        "HowTo": {
            "required": ["name", "step"],
            "recommended": ["description", "totalTime", "image"],
        },
        "Product": {
            "required": ["name"],
            "recommended": ["description", "image", "offers", "review"],
        },
        "JobPosting": {
            "required": ["title", "description", "datePosted", "hiringOrganization"],
            "recommended": ["validThrough", "employmentType", "jobLocation", "baseSalary"],
        },
        "WebSite": {
            "required": ["name", "url"],
            "recommended": ["potentialAction", "publisher"],
        },
        "WebPage": {
            "required": ["name"],
            "recommended": ["description", "url", "datePublished"],
        },
        "Corporation": {
            "required": ["name", "url"],
            "recommended": ["logo", "contactPoint", "sameAs", "address", "founder"],
        },
        "NewsArticle": {
            "required": ["headline", "author", "datePublished"],
            "recommended": ["dateModified", "image", "publisher"],
        },
    }

    for schema in schemas:
        if not isinstance(schema, dict):
            continue
        schema_type = schema.get("@type", "Unknown")
        if isinstance(schema_type, list):
            schema_type = schema_type[0] if schema_type else "Unknown"

        spec = schema_specs.get(schema_type)
        if not spec:
            results.append({
                "type": schema_type,
                "status": "○",
                "missing_required": [],
                "missing_recommended": [],
                "note": "検証仕様外のスキーマ",
            })
            continue

        missing_req = [p for p in spec["required"] if p not in schema]
        missing_rec = [p for p in spec["recommended"] if p not in schema]

        if not missing_req and len(missing_rec) <= len(spec["recommended"]) * 0.2:
            status = "◎"
        elif not missing_req:
            status = "○"
        else:
            status = "△"

        results.append({
            "type": schema_type,
            "status": status,
            "missing_required": missing_req,
            "missing_recommended": missing_rec,
            "note": "",
        })

    return results


def check_structured_data_coverage(schemas: list[dict]) -> dict:
    """構造化データの実装カバレッジを確認。"""
    found_types = set()
    for s in schemas:
        t = s.get("@type", "")
        if isinstance(t, list):
            found_types.update(t)
        else:
            found_types.add(t)

    return {
        "Organization": "Organization" in found_types or "Corporation" in found_types,
        "Article": "Article" in found_types or "BlogPosting" in found_types or "NewsArticle" in found_types,
        "FAQPage": "FAQPage" in found_types,
        "BreadcrumbList": "BreadcrumbList" in found_types,
        "LocalBusiness": "LocalBusiness" in found_types,
        "HowTo": "HowTo" in found_types,
        "Product": "Product" in found_types,
        "JobPosting": "JobPosting" in found_types,
        "WebSite": "WebSite" in found_types,
        "WebPage": "WebPage" in found_types,
        "found_types": list(found_types),
    }
