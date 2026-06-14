# 🗄️ Text-to-SQL BI — データに話しかけるBI

自然言語の質問を **DuckDB の SQL に変換 → 実際に実行 → 結果テーブル＋自動チャート** で返す、対話型 BI デモです。
「学習済みモデルをラップしただけ」で終わらせず、**精度を数値で計測**し、**SQL が壊れない仕組み**を備えていることに重点を置いています。

> 質問: *"What are the top 3 products by total revenue?"*
> → スキーマから関連テーブルを検索 → SQL 生成 → 構文検証 → 実行 → 棒グラフを自動描画

---

## ✨ 3つの工夫（このプロジェクトの肝）

| # | 仕組み | 何が嬉しいか | 実装 |
|---|---|---|---|
| 1 | **スキーマ RAG** | 質問に関連するテーブルだけをプロンプトに注入。大規模スキーマでもトークンが爆発しない | [`src/schema_indexer.py`](src/schema_indexer.py) |
| 2 | **静的バリデーション** | 生成 SQL を実行前に `sqlglot` で構文検証＋ SELECT 以外を機械的に拒否（read-only 接続と二重防御） | [`src/sql_validator.py`](src/sql_validator.py) |
| 3 | **自己修正ループ** | 検証/実行エラーをモデルに戻して自動リトライ。1発で通らない質問も復旧する | [`src/self_correct.py`](src/self_correct.py) |

## 📊 Execution Accuracy

結果セット一致（順序非依存）で計測する Text-to-SQL の標準指標です。`python eval/run_eval.py` で再現できます。

| Model | Execution Accuracy | 平均リトライ |
|---|---|---|
| `openai/gpt-4o-mini` | _（`run_eval.py` を実行して記入）_ | — |
| `anthropic/claude-3.5-sonnet` | _（同上）_ | — |

> ベンチマークは [`eval/benchmark.jsonl`](eval/benchmark.jsonl)（質問↔正解SQL 6問）。本番では BIRD / Spider のサブセットに差し替え可能。

## 🏗️ アーキテクチャ

```
質問
  │
  ▼
schema_indexer ──(関連テーブルのDDL)──► sql_generator (OpenRouter LLM)
                                              │  生成SQL
                                              ▼
                                       sql_validator (sqlglot, SELECT限定)
                                              │  OK
                                              ▼
                                         executor (DuckDB, read-only)
                                              │  ┌── エラー ──► self_correct がフィードバックして再生成
                                              ▼  │
                                         insighter (自動チャート＋要約)
                                              ▼
                                         Streamlit UI
```

## 🚀 ローカル起動

```bash
pip install -r requirements.txt
cp .env.example .env          # OPENROUTER_API_KEY を設定
python data/build_northwind.py   # サンプルDB（Northwindサブセット）を生成
streamlit run app.py
```

評価とテスト:

```bash
python eval/run_eval.py --model openai/gpt-4o-mini   # 精度計測（要APIキー）
pytest                                                # 決定的レイヤのテスト（APIキー不要）
```

## 🗂️ データ

定番 **Northwind** の小型サブセット（categories / products / customers / employees / orders / order_details）を
[`data/build_northwind.py`](data/build_northwind.py) でオフライン生成します（ダウンロード不要・決定的なので評価が安定）。

## 🧭 アップグレードの道筋（拡張ポイント）

- **スキーマRAGを埋め込み検索に**: 現在は軽量な語彙オーバーラップ。`sentence-transformers` + FAISS に差し替え可能（インターフェースは同形）。
- **DWHアダプタ**: `executor.py` を BigQuery / Snowflake 接続に差し替え。
- **MLOps化**: `run_eval.py` を CI（GitHub Actions）で回し、プロンプト改善ごとに精度を回帰チェック。
- **マルチモデル比較**: UI でモデルを切替え、精度×コストのトレードオフを可視化。

## 🛠️ 技術スタック

Python / Streamlit / DuckDB / sqlglot / OpenRouter (LLM) / Plotly / pandas
