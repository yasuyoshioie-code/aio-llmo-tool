# AIO / LLMO 診断ツール

**URLを入れるだけ**で、AI検索時代における最適化状況を100点満点で診断するWebアプリ。
メディア / 採用ページ / コーポレートサイトの3プリセット対応、クライアント提出用PPTXレポート出力機能付き。

## 🎯 主な機能

- **3プリセット診断**
  - 📰 メディアサイト（コンテンツ品質・E-E-A-T・AI引用可能性）
  - 💼 採用ページ（Google for Jobs対応・CV率診断）
  - 🏢 コーポレートサイト（企業情報網羅性・信頼性）
- **3モード**
  - 単一URL診断
  - サイト全体診断（sitemap.xml 自動探索 + HTMLリンク辿りフォールバック）
  - 複数URL貼り付け診断
- **クライアント提出用 PPTX レポート**（13〜30スライド、改善案サンプルコード付き）
- **競合比較**（上位3サイト自動分析）
- **改善ロードマップ**（優先度S/A/B + 期待効果 + 実装コスト）

## 🚀 セットアップ

### 必要なもの

- Python 3.10+
- [Tavily API Key](https://tavily.com/)（無料枠あり・必須）
- [PageSpeed Insights API Key](https://developers.google.com/speed/docs/insights/v5/get-started)（無料・任意）

### ローカル実行

```bash
# 1. リポジトリをクローン
git clone https://github.com/YOUR_NAME/aio-llmo-tool.git
cd aio-llmo-tool

# 2. 仮想環境作成（任意）
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux

# 3. 依存パッケージインストール
pip install -r requirements.txt

# 4. APIキーを設定
cp .env.example .env
# .env を編集して TAVILY_API_KEY を設定

# 5. 起動
streamlit run app.py
```

ブラウザで http://localhost:8501 を開く。

## ☁️ 公開デプロイ

詳細は [DEPLOY.md](./DEPLOY.md) を参照。

- **Streamlit Community Cloud**（無料・10分で公開）
- **Render.com**（無料〜・常時起動向け）
- **Hugging Face Spaces**（無料）
- **VPS**（月$5〜・本格運用）

## 📁 プロジェクト構成

```
.
├── app.py                      # Streamlit メインアプリ
├── config.py                   # API キー管理
├── requirements.txt            # 依存パッケージ
├── .streamlit/
│   └── config.toml             # テーマ設定
├── core/
│   ├── fetcher.py              # ページ取得（httpx + Tavily）
│   ├── parser.py               # HTML解析
│   ├── technical.py            # robots/llms.txt/JSON-LD検証
│   ├── content_scorer.py       # コンテンツスコアリング
│   ├── competitor.py           # 競合分析
│   ├── scorer.py               # 統合スコアリング
│   ├── site_crawler.py         # サイト全体URL収集
│   ├── site_aggregator.py      # 複数ページ集計
│   ├── pptx_generator.py       # PPTX生成
│   └── presets/
│       ├── media.py            # メディア診断
│       ├── recruiting.py       # 採用診断
│       ├── recruiting_cv.py    # CV率分析
│       └── corporate.py        # コーポレート診断
└── .claude/agents/
    └── aio-diagnostic.md       # Claude Code診断エージェント定義
```

## 🔐 セキュリティ

- `.env` / `secrets.toml` は必ず `.gitignore` で除外
- 外部ユーザに公開する場合は、APIキー消費を防ぐためレート制限・認証を検討

## 📄 ライセンス

MIT（※ 必要に応じて調整してください）
