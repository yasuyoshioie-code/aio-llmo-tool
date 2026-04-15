# デプロイガイド

このアプリを世界に公開する方法を、**最も簡単な順**に解説。

---

## ⭐ プランA: Streamlit Community Cloud（無料・10分で完了）

**こんな人向け**: とにかく早く公開したい・無料で済ませたい・内部デモ／ポートフォリオ用

### 手順

#### 1. GitHubアカウントを作る（持ってなければ）
https://github.com/signup

#### 2. GitHubリポジトリを作成
https://github.com/new
- Repository name: `aio-llmo-tool`（任意）
- Public / Private どちらでもOK（Privateは無料枠で1個まで）
- README・.gitignoreは作らない（既にある）
- 「Create repository」を押す

#### 3. ローカルからpush

```bash
cd C:\Users\oievi\AIOツール

git init
git add .
git commit -m "初回コミット"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/aio-llmo-tool.git
git push -u origin main
```

※ 初回pushで GitHub のログインを求められたら、ブラウザ認証で通せます。

#### 4. Streamlit Community Cloud でデプロイ

1. https://share.streamlit.io にアクセス
2. 「Continue with GitHub」でログイン
3. 「**New app**」を押す
4. 以下を入力：
   - Repository: `YOUR_NAME/aio-llmo-tool`
   - Branch: `main`
   - Main file path: `app.py`
5. 「**Advanced settings**」を開く → **Secrets** 欄に以下を貼り付け：

   ```toml
   TAVILY_API_KEY = "tvly-xxxxxxxxxxxxxxxx"
   PAGESPEED_API_KEY = "AIzaSyxxxxxxxxxxxxxxxx"
   ```

6. 「**Deploy!**」を押す
7. 2〜5分待つと https://xxxxxxxx.streamlit.app の形式でURLが発行される ✅

### 制限事項
- 無料枠: 1GB RAM、7日間アクセス無しでスリープ（初回起動時に数十秒待ち）
- Public repoは無制限、Private repoは1つまで
- コード更新 → `git push` で自動再デプロイ

---

## プランB: Render.com（無料・常時起動向き）

**こんな人向け**: スリープなしで快適に使いたい・クライアントに常時URLを提供したい

### 手順

1. https://render.com でサインアップ（GitHub連携）
2. 「**New +**」→「**Web Service**」
3. リポジトリ選択（プランAと同じGitHubリポジトリ）
4. 設定：
   - Name: `aio-llmo-tool`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true`
   - Plan: **Free** （または Starter $7/月で常時起動）
5. **Environment Variables** に追加：
   - `TAVILY_API_KEY`: 値を貼り付け
   - `PAGESPEED_API_KEY`: 値を貼り付け
6. 「Create Web Service」

発行URL: `https://aio-llmo-tool.onrender.com`

### 制限
- 無料プラン: 15分アクセス無しでスリープ（起動に30〜60秒）
- Starter($7/月): スリープなし・独自ドメイン可

---

## プランC: Hugging Face Spaces（無料）

1. https://huggingface.co/new-space
2. Space name入力、SDK = **Streamlit**、**Public**
3. 発行されたgit URLに push
4. **Settings → Repository secrets** で `TAVILY_API_KEY` 追加

発行URL: `https://huggingface.co/spaces/YOUR_NAME/aio-llmo-tool`

---

## プランD: VPS（AWS Lightsail / さくらVPS / DigitalOcean）

**月$5〜**、独自ドメイン・認証・24時間稼働可能。本格運用向け。

### AWS Lightsail 例

1. Lightsailインスタンス作成（Ubuntu 22.04, $5プラン）
2. SSH接続
3. セットアップ：

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv nginx
git clone https://github.com/YOUR_NAME/aio-llmo-tool.git
cd aio-llmo-tool
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# .env 作成
echo "TAVILY_API_KEY=tvly-xxx" > .env

# systemd サービス化（再起動耐性）
sudo nano /etc/systemd/system/aio-tool.service
```

サービスファイル内容：
```ini
[Unit]
Description=AIO/LLMO Tool
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/aio-llmo-tool
ExecStart=/home/ubuntu/aio-llmo-tool/venv/bin/streamlit run app.py --server.port=8501 --server.headless=true
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable aio-tool && sudo systemctl start aio-tool
# Nginx リバースプロキシ + SSL (certbot) 設定
```

---

## 🔐 公開前チェックリスト

- [ ] `.env` が `.gitignore` に含まれている（APIキー漏洩防止）
- [ ] APIキーは全てデプロイ先の Secrets に登録
- [ ] **レート制限の検討**: Tavily無料枠は月1,000回。公開した場合は上限到達リスク
  - 対策1: Streamlitの `@st.cache_data(ttl=3600)` で診断結果をキャッシュ
  - 対策2: Basic認証追加（`streamlit-authenticator`）
  - 対策3: APIキーを訪問者自身に入力してもらう方式に変更
- [ ] 利用規約・プライバシーポリシーページ（任意）

---

## 💰 コスト目安

| プラン | 月額 | 制限 |
|-------|------|------|
| Streamlit Cloud 無料 | ¥0 | 1GB/スリープあり |
| Render 無料 | ¥0 | スリープ15分 |
| Render Starter | ≈ ¥1,100 | 常時起動 |
| AWS Lightsail | ≈ ¥750 | 月3.5TB転送 |
| Hugging Face 無料 | ¥0 | CPU Basic |

---

## 🆘 トラブルシューティング

**Q: `ModuleNotFoundError` が出る**
→ `requirements.txt` に漏れがないか確認。該当パッケージを追記して再push。

**Q: APIキーが読み込まれない**
→ Streamlit Cloud では Secrets（`st.secrets`）、Render/VPSでは環境変数経由。`config.py` は両対応済み。

**Q: Tavily無料枠が枯渇した**
→ アプリのサイドバーにAPIキー入力欄あり — ユーザー自身のキーを使ってもらう設計に。

**Q: アプリが重い/メモリ不足**
→ Streamlit Cloud無料は1GBまで。重い診断時は Render Starter（$7/月）推奨。
