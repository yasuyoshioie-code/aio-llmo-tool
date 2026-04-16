"""設定モジュール — Streamlit Cloud の st.secrets と .env の両対応"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Streamlit Cloud には dotenv 不要


def _get_secret(name: str, default: str = "") -> str:
    """APIキーを st.secrets（Streamlit Cloud）→ 環境変数（ローカル .env）の順で取得。"""
    # 1. Streamlit Cloud の st.secrets
    try:
        import streamlit as st
        val = st.secrets[name]
        if val:
            return str(val)
    except Exception:
        pass
    # 2. ローカル .env / 環境変数
    return os.getenv(name, default)


TAVILY_API_KEY = _get_secret("TAVILY_API_KEY", "")
PAGESPEED_API_KEY = _get_secret("PAGESPEED_API_KEY", "")

# Claude API モデル設定（analyzer.py 互換）
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
MAX_CONTENT_CHARS = int(os.getenv("MAX_CONTENT_CHARS", "50000"))

COMPETITOR_COUNT = 3
SAMPLE_ARTICLES = 3
