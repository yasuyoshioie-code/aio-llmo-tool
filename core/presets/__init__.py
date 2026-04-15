"""診断プリセット — サイト種別ごとの評価基準を切り替える"""

from core.presets import media, recruiting, corporate

PRESETS = {
    "media": {
        "id": "media",
        "label": "📰 メディア/ブログ",
        "description": "AI引用・SEO流入を目的としたコンテンツサイト",
        "module": media,
    },
    "recruiting": {
        "id": "recruiting",
        "label": "💼 採用ページ",
        "description": "Google for Jobs対応・求職者への応募転換",
        "module": recruiting,
    },
    "corporate": {
        "id": "corporate",
        "label": "🏢 コーポレートサイト",
        "description": "企業情報網羅性・信頼性・ステークホルダー対応",
        "module": corporate,
    },
}


def get_preset(preset_id: str):
    return PRESETS.get(preset_id, PRESETS["media"])
