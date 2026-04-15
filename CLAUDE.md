# AIO/LLMO 診断ツール

## プロジェクト概要

URLを入力するだけで、AIO（AI Overview）対策とLLMO（Large Language Model Optimization）対策の総合診断レポートを出力するツール。

## エージェント

| エージェント | ファイル | 役割 | モデル |
|------------|---------|------|--------|
| `@aio-diagnostic` | `.claude/agents/aio-diagnostic.md` | AIO/LLMO総合診断 | Opus |

## コマンド

| コマンド | 説明 |
|---------|------|
| `/diagnose <URL>` | 指定URLのAIO/LLMO診断を実行 |

## 基本ルール

- 出力言語: 日本語
- 任意のURLを診断可能（自サイト・他サイト問わず）
- Otterlyデータは登録済みドメインのみ表示
- レポートは会話内に直接出力

## スコアリング

```
総合スコア = AIO最適化(40%) + LLMO最適化(40%) + 競合優位性(20%)
```
