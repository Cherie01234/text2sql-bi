"""Text-to-SQL BI — Streamlit UI.

Run:
    python data/build_northwind.py   # once
    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from src import insighter
from src.config import DEFAULT_MODEL
from src.executor import connect
from src.self_correct import answer

st.set_page_config(page_title="Text-to-SQL BI", page_icon="🗄️", layout="wide")

EXAMPLES = [
    "What are the top 3 products by total revenue?",
    "How many orders did each country's customers place?",
    "Show monthly order counts over time.",
    "Which employee handled the most orders?",
]


@st.cache_resource
def get_connection():
    return connect()


st.title("🗄️ Text-to-SQL BI — データに話しかける")
st.caption("自然言語 → DuckDB SQL → 実行 → 自動チャート。スキーマRAG＋検証＋自己修正つき。")

with st.sidebar:
    st.header("設定")
    model = st.text_input("Model (OpenRouter)", value=DEFAULT_MODEL)
    st.markdown("**質問の例**")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state["question"] = ex

question = st.text_input(
    "質問を入力", value=st.session_state.get("question", EXAMPLES[0])
)

if st.button("実行", type="primary"):
    try:
        con = get_connection()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    with st.spinner("SQLを生成・検証・実行中..."):
        result = answer(question, con, model=model)

    if not result.ok:
        st.error(f"失敗しました（{len(result.attempts)}回試行）: {result.error}")
    else:
        st.success(insighter.summarize(result.df))
        st.code(result.sql, language="sql")

        fig = insighter.auto_chart(result.df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(result.df, use_container_width=True)

    with st.expander("🔎 実行の内訳（スキーマRAG / リトライ）"):
        st.write("**参照テーブル:**", ", ".join(result.tables_used) or "—")
        for i, att in enumerate(result.attempts, 1):
            status = "✅ OK" if not att.error else f"❌ {att.error}"
            st.markdown(f"**Attempt {i}** — {status}")
            st.code(att.sql or "(no sql)", language="sql")
