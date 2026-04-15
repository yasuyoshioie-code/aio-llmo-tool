"""設定モジュール — Streamlit Cloud の st.secrets と .env の両対応"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_secret(name: str, default: str = "") -> str:
    """APIキーを st.secrets（Streamlit Cloud）→ 環境変数（ローカル .env）の順で取得。"""
    # Streamlit Cloud では st.secrets、ローカルでは .env から
    try:
        import streamlit as st  # type: ignore
        # secrets.toml が存在しない環境では st.secrets アクセスで例外が出る
        if hasattr(st, "secrets"):
            try:
                val = st.secrets.get(name, "")
                if val:
                    return str(val)
            except Exception:
                pass
    except Exception:
        pass
    return os.getenv(name, default)


TAVILY_API_KEY = _get_secret("TAVILY_API_KEY", "")
PAGESPEED_API_KEY = _get_secret("PAGESPEED_API_KEY", "")

COMPETITOR_COUNT = 3
SAMPLE_ARTICLES = 3
