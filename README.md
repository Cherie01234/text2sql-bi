# 🗄️ Text-to-SQL BI — データに話しかけるBI

[![CI](https://github.com/Cherie01234/text2sql-bi/actions/workflows/ci.yml/badge.svg)](https://github.com/Cherie01234/text2sql-bi/actions/workflows/ci.yml)

## 概要

| 項目 | 内容 |
|---|---|
| 解く課題 | SQLを書かない利用者でも、自然言語の質問からデータを集計・可視化できるようにする。あわせて、LLMが生成するSQLの誤りや、データを書き換える操作を防ぐ |
| 手法 | テーブル数が上限（既定6）を超えると、質問と語が重なるテーブルの定義だけをLLMに渡すスキーマ検索（サンプルDBは6テーブルのため、現状は全テーブルを渡す）→ OpenRouter経由のLLMでDuckDB用のSQLを生成 → sqlglotで構文を検証しSELECT以外を拒否（読み取り専用接続と二重の防御）→ 実行エラー時はエラー内容をLLMに戻して作り直す（最大2回）→ 結果の表とグラフを表示 |
| 評価方法 | 実行結果の一致率（Execution Accuracy：生成SQLと正解SQLの結果を、行の順序を問わず比較）を、Northwindを模した小さなサンプルデータ（注文7件）で作った6問で計測し、複数のLLMを比較（[`eval/run_eval.py`](eval/run_eval.py)） |
| 結果 | 2026-11-01 に各3回計測：`gpt-4o-mini` と `gemini-2.5-flash-lite` は3回とも 6/6、`deepseek-v4-flash` は3回とも 5/6。deepseek の不一致は q1 で商品IDの列を足したためで、返した商品と売上は正解と同じ（同じ日の先の計測では 6/6 ×3。temperature=0 でも計測ごとに出力が変わる）。作り直しは0回（結果は [`eval/results/`](eval/results/)）。6問（実質5問）と小規模なので、モデルの実力差を測るには問題を増やす必要がある |
| 評価からの知見 | 不一致の原因はモデルではなく、列構成の違いに敏感な指標の性質と、出力列を指定していない質問文にあると切り分けた。正解をモデル出力に合わせず、質問文と正解SQLで出力列を指定して評価データを直した（下記「評価で得られた知見」） |
| 使い方 | `.env` に `OPENROUTER_API_KEY` を設定 → `python data/build_northwind.py` → `streamlit run app.py`。評価は `python eval/run_eval.py --model <モデル名>`、テストは `pytest`（APIキー不要） |
| 開発 | 設計から個人で開発（開発にはAIエージェントを活用）。SQL検証のテスト（更新系SQL・複数文・構文不正の拒否）と GitHub Actions の CI を整備 |

---

自然言語の質問を **DuckDB の SQL に変換 → 実際に実行 → 結果テーブル＋自動チャート** で返す、対話型 BI デモです。
「学習済みモデルをラップしただけ」で終わらせず、**精度を数値で計測**し、**SQL が壊れない仕組み**を備えていることに重点を置いています。

![Text-to-SQL BI demo](assets/demo.gif)

> 質問: *「売上が最も高い商品トップ3を教えて」*
> → スキーマから関連テーブルを検索 → SQL 生成 → 構文検証 → 実行 → 棒グラフを自動描画

---

## ✨ 3つの工夫（このプロジェクトの肝）

| # | 仕組み | 何が嬉しいか | 実装 |
|---|---|---|---|
| 1 | **スキーマ RAG** | 質問に関連するテーブルだけをプロンプトに注入し、大規模スキーマでのトークン増加を抑える。テーブル数が上限（`TEXT2SQL_SCHEMA_TOP_K`、既定6）を超えたときに働く（サンプルDBは6テーブルなので、現状は全テーブルを渡す） | [`src/schema_indexer.py`](src/schema_indexer.py) |
| 2 | **静的バリデーション** | 生成 SQL を実行前に `sqlglot` で構文検証＋ SELECT 以外を機械的に拒否（read-only 接続と二重防御） | [`src/sql_validator.py`](src/sql_validator.py) |
| 3 | **自己修正ループ** | 検証/実行エラーをモデルに戻して自動リトライ（最大2回）。1発で通らない質問の復旧を狙う（下記の評価では作り直しは発生していない） | [`src/self_correct.py`](src/self_correct.py) |

## 📊 Execution Accuracy

結果セット一致（順序非依存）で計測する Text-to-SQL の標準指標です。`python eval/run_eval.py` で再現できます。

| Model | Execution Accuracy（3回の実行） | 平均リトライ |
|---|---|---|
| `openai/gpt-4o-mini` | 100% (6/6 ×3回) | 0.0 |
| `deepseek/deepseek-v4-flash` | 83% (5/6 ×3回) | 0.0 |
| `google/gemini-2.5-flash-lite` | 100% (6/6 ×3回) | 0.0 |

> 2026-11-01 に `--repeat 3` で計測（temperature=0）。各問の生成SQL・リトライ回数・返した列と行数は [`eval/results/`](eval/results/) に保存しています。
>
> `deepseek-v4-flash` が落としたのは3回とも q1（"売上トップ3の商品は？"）で、`product_id` の列を足したため列構成が正解と一致しませんでした。返した商品と売上は正解と同じです。同じ日の先の計測（コミット c8de52a の結果ファイル）では `product_id` を付けず、3回とも 6/6 でした。temperature=0 でも計測ごとに出力が変わり、q1 も出力列を指定していないため、下記の q3 と同じ種類の不一致が起きます。
>
> q6（注文したことのない顧客）は、サンプルデータの顧客5社がすべて注文しているため、正解が0行です。0行を返すSQLなら列構成に関係なく一致と判定されるので、モデル間で差がつきうる問題は実質5問です。
>
> ベンチマークは [`eval/benchmark.jsonl`](eval/benchmark.jsonl)（質問↔正解SQL 6問）。この規模ではモデルの実力差は測れないため、本番では BIRD / Spider のサブセットに差し替えて計測する想定です。

### 評価で得られた知見（指標の限界とベンチ改善）

初回計測（2026-06-14、各モデル1回。当時の結果ファイルは残っておらず、記録はこの README だけ）では全モデルが **5/6 (83%)** で、同一の問題（"最も注文を処理した従業員は？"）だけが落ちました。
FAIL の生成SQLを分析したところ、**3モデルともSQLは意味的に正しく**、原因はモデル側ではなく評価指標にありました:

- Execution Accuracy は**結果セットの完全一致**で判定するため、**列射影（projection）の違いに敏感**。
- 元の質問は出力列を指定しておらず、モデルが気を利かせて `employee_id` を追加したり名前を `CONCAT` したため、中身は正しくても列構成が正解と一致せず誤判定された。

> 2026-11-01 に修正前の q3 を各モデル3回ずつ再実行すると（[`eval/rerun_q3_before_fix.py`](eval/rerun_q3_before_fix.py)）、3モデルとも3回すべて、`employee_id` を足すなどの列構成の違いで不一致になりました。不一致になった生成SQLも、すべて正解と同じ従業員を返しています（[`eval/results/q3_before_fix.json`](eval/results/q3_before_fix.json)）。

対策として、正解SQLをモデル出力に合わせるのではなく、**質問文で出力列を「姓のみ」と指定し、正解SQLもその指定どおりに直して**ベンチを改善し、当時の計測では全モデル **6/6 (100%)** に。
指標の特性を理解し、評価データ側の欠陥を切り分けて修正できることを示す一例です（[`eval/benchmark.jsonl`](eval/benchmark.jsonl) の `q3`）。

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
python data/build_northwind.py   # サンプルDB（Northwind風の小型データ）を生成
streamlit run app.py
```

評価とテスト:

```bash
python eval/run_eval.py --model openai/gpt-4o-mini   # 精度計測（要APIキー）
python eval/run_eval.py --model openai/gpt-4o-mini --repeat 3 --out eval/results/gpt-4o-mini.json   # 3回計測して結果を保存
python eval/rerun_q3_before_fix.py                    # 修正前の q3 を3モデル×3回で再実行（要APIキー）
pytest                                                # 決定的レイヤのテスト（APIキー不要）
```

## 🗂️ データ

定番 **Northwind** を模した小型のサンプルデータ（categories / products / customers / employees / orders / order_details。商品8・顧客5・従業員3・注文7件）を
[`data/build_northwind.py`](data/build_northwind.py) でオフライン生成します（ダウンロード不要。データは決定的に作られるが、LLM の出力は temperature=0 でも回ごとに変わりうる）。

## 🧭 アップグレードの道筋（拡張ポイント）

- **スキーマRAGを埋め込み検索に**: 現在は軽量な語彙オーバーラップ。`sentence-transformers` + FAISS に差し替え可能（インターフェースは同形）。
- **DWHアダプタ**: `executor.py` を BigQuery / Snowflake 接続に差し替え。
- **MLOps化**: `run_eval.py` を CI（GitHub Actions）で回し、プロンプト改善ごとに精度を回帰チェック。
- **マルチモデル比較**: UI でモデルを切替え、精度×コストのトレードオフを可視化。

## 🛠️ 技術スタック

Python / Streamlit / DuckDB / sqlglot / OpenRouter (LLM) / Plotly / pandas
