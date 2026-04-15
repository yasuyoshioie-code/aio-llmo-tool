"""Claude API分析モジュール — v2.1の30項目をトークン最適化して実行"""

import json
import anthropic
from config import CLAUDE_MODEL, MAX_CONTENT_CHARS

SYSTEM_PROMPT = """あなたはAIO（AI Overview）とLLMO（LLM最適化）の専門診断士です。
サイトの構造データとコンテンツを受け取り、JSON形式で採点結果を返します。
全項目で根拠を1文で付記してください。推測は「推定」と明記してください。"""


def _call_claude(api_key: str, prompt: str, max_tokens: int = 4000) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def _extract_json(text: str) -> dict:
    """Claude応答からJSONを抽出。"""
    # ```json ... ``` ブロックを探す
    import re
    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 直接JSONを試す
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "JSON解析失敗", "raw": text[:500]}


def analyze_content_and_citation(
    api_key: str,
    content_text: str,
    structure: dict,
) -> dict:
    """カテゴリ1（コンテンツ品質）+ カテゴリ4（AI引用可能性）を一括採点。

    Python解析で得た構造データ + コンテンツ先頭をClaudeに送り、
    定性評価が必要な項目のみLLMで採点する。
    """
    truncated = content_text[:MAX_CONTENT_CHARS]
    headings_str = "\n".join(
        f"  H{h['level']}: {h['text']}" for h in structure.get("headings", [])[:20]
    )
    faq_count = len(structure.get("faq_items", []))

    prompt = f"""以下のサイトデータを分析し、6項目をJSON形式で採点してください。

## サイト構造データ（Python解析済み）
- タイトル: {structure.get('title', 'なし')}
- 見出し構造:
{headings_str}
- 総文字数: {structure.get('word_count', 0)}
- 段落数: {structure.get('paragraph_count', 0)}
- リスト数: {structure.get('list_count', 0)}
- テーブル数: {structure.get('table_count', 0)}
- FAQ数: {faq_count}

## コンテンツ（先頭{MAX_CONTENT_CHARS}字）
{truncated}

## 採点項目（各項目の配点と境界条件に従い厳密に採点）

```json
{{
  "answer_first": {{
    "score": 0-4,
    "reason": "冒頭100字以内に結論・定義文があるか。4=80%以上,2=50-79%,0=50%未満"
  }},
  "clarity": {{
    "score": 0-3,
    "reason": "1段落1トピック、PREP法的構成か。3=明確,1.5=部分的,0=冗長"
  }},
  "definition_sentences": {{
    "score": 0-4,
    "reason": "「○○とは△△です」型の定義文があるか。4=あり(1-2文),2=冗長,0=なし"
  }},
  "numeric_data": {{
    "score": 0-4,
    "reason": "料金/期間/スペック等の具体数値。4=3箇所以上,2=1-2箇所,0=なし"
  }},
  "original_data": {{
    "score": 0-4,
    "reason": "独自調査・一次情報があるか。4=あり,2=体験談レベル,0=なし"
  }},
  "entity_consistency": {{
    "score": 0-4,
    "reason": "企業名/製品名が正式名称で統一されているか。4=統一,2=一部ゆれ,0=不統一"
  }}
}}
```

JSONのみ返してください。"""

    raw = _call_claude(api_key, prompt, max_tokens=1000)
    return _extract_json(raw)


def analyze_eeat(
    api_key: str,
    content_text: str,
    author_info: dict,
    about_page_text: str,
) -> dict:
    """カテゴリ3（E-E-A-T）を採点。"""
    truncated = content_text[:3000]
    author_str = json.dumps(author_info, ensure_ascii=False) if author_info else "なし"

    prompt = f"""以下のサイト情報からE-E-A-Tシグナルを採点してください。

## 著者情報（Python検出結果）
{author_str}

## 運営者ページ内容（先頭2000字）
{about_page_text[:2000] if about_page_text else '取得できず'}

## 記事コンテンツ（先頭3000字）
{truncated}

## 採点項目

```json
{{
  "author_display": {{
    "score": 0-4,
    "reason": "著者名+専門領域+プロフィールリンク=4, 名前のみ=2, なし=0"
  }},
  "operator_info": {{
    "score": 0-4,
    "reason": "会社名/代表者/所在地/連絡先/設立年=4, 簡易的=2, なし=0"
  }},
  "citations": {{
    "score": 0-3,
    "reason": "一次情報源へのリンク。50%以上=3, 一部=1.5, なし=0"
  }},
  "experience": {{
    "score": 0-3,
    "reason": "一次体験/実績/事例あり=3, 一部あり=1.5, なし=0"
  }},
  "editorial_policy": {{
    "score": 0-3,
    "reason": "編集ポリシー/免責事項ページあり=3, 簡易記載=1.5, なし=0"
  }},
  "external_consistency": {{
    "score": 0-3,
    "reason": "外部プロフィールとの一致。一致=3, 一部不一致=1.5, なし=0（推定）"
  }}
}}
```

JSONのみ返してください。"""

    raw = _call_claude(api_key, prompt, max_tokens=800)
    return _extract_json(raw)


def generate_improvements(
    api_key: str,
    scores: dict,
    content_text: str,
    structure: dict,
    site_url: str,
) -> dict:
    """低スコア項目に対する具体的改善提案を生成。"""
    truncated = content_text[:4000]
    scores_str = json.dumps(scores, ensure_ascii=False, indent=2)

    prompt = f"""以下の診断結果に基づき、改善施策をJSON形式で返してください。

## 対象サイト
URL: {site_url}
タイトル: {structure.get('title', '')}

## 現在のスコア
{scores_str}

## コンテンツ（先頭4000字）
{truncated}

## 出力形式

低スコア項目を中心に、優先度別に改善施策を5つ提案してください。
各施策にはBefore/After（対象サイトの実際のコンテンツを使用）を含めてください。

```json
{{
  "quick_wins": [
    {{
      "title": "施策名",
      "category": "構造化データ/コンテンツ構造/E-E-A-T/テクニカル",
      "target": "対象ページや要素",
      "effort": "想定工数（時間）",
      "impact": "高/中/低",
      "before": "現在の実際のコード/テキスト",
      "after": "改善後のコード/テキスト",
      "reason": "なぜこの改善が効果的か"
    }}
  ],
  "strategic": [
    {{
      "title": "施策名",
      "category": "カテゴリ",
      "description": "詳細説明",
      "effort": "想定工数",
      "impact": "高/中/低",
      "reason": "根拠"
    }}
  ],
  "llms_txt_template": "対象サイト用のllms.txtテンプレート（Markdown形式）",
  "organization_jsonld": "対象サイト用のOrganization JSON-LDコード"
}}
```

JSONのみ返してください。"""

    raw = _call_claude(api_key, prompt, max_tokens=3000)
    return _extract_json(raw)


def generate_test_queries(
    api_key: str,
    site_url: str,
    keywords: list[str],
    site_title: str,
) -> dict:
    """商談実演用テストクエリを生成。"""
    kw_str = ", ".join(keywords) if keywords else "（キーワード未指定）"

    prompt = f"""以下のサイト情報から、商談デモ用のAI検索テストクエリを設計してください。

サイト: {site_url}
サイト名: {site_title}
メインキーワード: {kw_str}

## 出力形式

```json
{{
  "queries": [
    {{
      "platform": "ChatGPT/Perplexity/Google AI Overview",
      "query": "テストクエリ文",
      "expected_if_cited": "引用される場合の期待表示",
      "reason_if_not": "引用されない場合の原因仮説"
    }}
  ],
  "claude_self_eval": {{
    "would_recommend": true/false,
    "reason": "理由"
  }}
}}
```

5つのクエリ（ChatGPT×2, Perplexity×2, Google×1）を設計してください。
JSONのみ返してください。"""

    raw = _call_claude(api_key, prompt, max_tokens=1200)
    return _extract_json(raw)
