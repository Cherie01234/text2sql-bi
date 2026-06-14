"""Generate a stylized demo GIF of the Text-to-SQL BI flow using Pillow.

This is an animated *mockup* (not a screen recording), but the chart values are
pulled live from the real DuckDB database, so the numbers are accurate.

    python assets/make_demo_gif.py
    -> writes assets/demo.gif (+ assets/demo_last.png for a quick preview)
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.config import DB_PATH  # noqa: E402

W, H = 920, 520
BG = (255, 255, 255)
INK = (33, 37, 41)
GRAY = (130, 138, 148)
BORDER = (208, 212, 218)
RED = (255, 75, 75)          # Streamlit accent
CODE_BG = (14, 17, 23)
CODE_FG = (220, 224, 230)
BAR = (76, 120, 168)         # Plotly default blue

JP_FONTS = [
    "C:/Windows/Fonts/YuGothM.ttc", "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/msgothic.ttc", "C:/Windows/Fonts/arial.ttf",
]
MONO_FONTS = ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf",
              "C:/Windows/Fonts/arial.ttf"]

SQL_LINES = [
    "SELECT p.product_name,",
    "       SUM(od.quantity * od.unit_price) AS revenue",
    "FROM order_details od",
    "JOIN products p ON p.product_id = od.product_id",
    "GROUP BY p.product_name",
    "ORDER BY revenue DESC",
    "LIMIT 3",
]
QUESTION = "What are the top 3 products by total revenue?"


def font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = font(JP_FONTS, 26)
F_SUB = font(JP_FONTS, 14)
F_BODY = font(JP_FONTS, 16)
F_SMALL = font(JP_FONTS, 13)
F_MONO = font(MONO_FONTS, 14)


def load_chart_data():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    rows = con.execute(
        "SELECT p.product_name, SUM(od.quantity * od.unit_price) AS revenue "
        "FROM order_details od JOIN products p ON p.product_id = od.product_id "
        "GROUP BY p.product_name ORDER BY revenue DESC LIMIT 3"
    ).fetchall()
    con.close()
    return [(name, float(rev)) for name, rev in rows]


CHART = load_chart_data()


def rounded(d, box, radius, **kw):
    d.rounded_rectangle(box, radius=radius, **kw)


def render(typed, pressed, status, sql_n, bar_p):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header
    d.text((40, 22), "Text-to-SQL BI", font=F_TITLE, fill=INK)
    d.text((40, 58), "自然言語 → SQL → 実行 → 自動チャート", font=F_SUB, fill=GRAY)
    d.line((40, 88, W - 40, 88), fill=BORDER, width=1)

    # Input box
    rounded(d, (40, 104, 740, 148), 8, outline=BORDER, width=2, fill=(250, 250, 251))
    cursor = "|" if (len(typed) < len(QUESTION)) else ""
    d.text((54, 116), (typed + cursor) or "質問を入力...", font=F_BODY,
           fill=INK if typed else GRAY)

    # Run button
    btn_fill = (200, 50, 50) if pressed else RED
    rounded(d, (760, 104, 880, 148), 8, fill=btn_fill)
    d.text((792, 117), "実行", font=F_BODY, fill=(255, 255, 255))

    # Status line
    if status == "run":
        d.text((40, 168), "⏳ SQLを生成・検証・実行中...", font=F_SMALL, fill=GRAY)
    elif status == "done":
        d.text((40, 168), "OK  3 rows ・ 参照テーブル: order_details, products  ・ retries=0",
               font=F_SMALL, fill=(34, 139, 84))

    # SQL panel
    rounded(d, (40, 196, 600, 470), 8, fill=CODE_BG)
    for i in range(min(sql_n, len(SQL_LINES))):
        d.text((58, 214 + i * 26), SQL_LINES[i], font=F_MONO, fill=CODE_FG)

    # Chart panel
    if bar_p > 0:
        cx0, cy_base, cy_top = 648, 446, 232
        d.text((640, 206), "revenue by product", font=F_SMALL, fill=GRAY)
        d.line((648, cy_base, 880, cy_base), fill=BORDER, width=1)
        max_rev = max(r for _, r in CHART) or 1
        bw, gap = 56, 20
        for i, (name, rev) in enumerate(CHART):
            full_h = (rev / max_rev) * (cy_base - cy_top)
            h = full_h * bar_p
            x = cx0 + i * (bw + gap)
            d.rectangle((x, cy_base - h, x + bw, cy_base), fill=BAR)
            if bar_p > 0.85:
                d.text((x, cy_base - h - 16), f"{int(rev)}", font=F_SMALL, fill=INK)
            label = name if len(name) <= 8 else name[:7] + "…"
            d.text((x, cy_base + 6), label, font=F_SMALL, fill=GRAY)

    return img


def build():
    frames, durations = [], []

    def add(img, ms):
        frames.append(img)
        durations.append(ms)

    # 1) type the question
    for i in range(0, len(QUESTION) + 1, 3):
        add(render(QUESTION[:i], False, None, 0, 0), 40)
    add(render(QUESTION, False, None, 0, 0), 500)
    # 2) press run
    add(render(QUESTION, True, "run", 0, 0), 250)
    add(render(QUESTION, False, "run", 0, 0), 600)
    # 3) reveal SQL line by line
    for n in range(1, len(SQL_LINES) + 1):
        add(render(QUESTION, False, "run", n, 0), 160)
    # 4) grow the bars
    for t in range(1, 9):
        add(render(QUESTION, False, "done", len(SQL_LINES), t / 8), 110)
    # 5) hold final frame
    add(render(QUESTION, False, "done", len(SQL_LINES), 1.0), 2600)

    out = ROOT / "assets" / "demo.gif"
    frames[0].save(
        out, save_all=True, append_images=frames[1:], duration=durations,
        loop=0, optimize=True, disposal=2,
    )
    frames[-1].save(ROOT / "assets" / "demo_last.png")
    size_kb = out.stat().st_size / 1024
    print(f"Wrote {out} ({len(frames)} frames, {size_kb:.0f} KB)")


if __name__ == "__main__":
    build()
