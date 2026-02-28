"""fpdf2によるPDFレポート生成"""

import os
from datetime import datetime
from fpdf import FPDF

from config import DISCLAIMER

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_PATH = os.path.join(FONT_DIR, "NotoSansJP.ttf")


class EthicsNaviPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("NotoSansJP", "", FONT_PATH, uni=True)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("NotoSansJP", "", 16)
        self.cell(0, 10, "EthicsNavi 臨床倫理4分割表レポート", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("NotoSansJP", "", 9)
        self.cell(
            0, 6,
            f"作成日: {datetime.now().strftime('%Y年%m月%d日')}",
            new_x="LMARGIN", new_y="NEXT", align="R",
        )
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("NotoSansJP", "", 7)
        self.cell(0, 10, DISCLAIMER, align="C")


def generate_pdf(case_overview: str, table_data: dict) -> bytes:
    """4分割表のPDFレポートを生成"""
    pdf = EthicsNaviPDF()
    pdf.add_page()

    table = table_data.get("table", {})
    discussion_points = table_data.get("discussion_points", [])
    tensions = table_data.get("tensions", [])

    # --- ケース概要 ---
    pdf.set_font("NotoSansJP", "", 13)
    pdf.cell(0, 8, "ケース概要", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("NotoSansJP", "", 10)
    pdf.multi_cell(0, 6, case_overview)
    pdf.ln(6)

    # --- 4分割表 ---
    pdf.set_font("NotoSansJP", "", 13)
    pdf.cell(0, 8, "Jonsenの臨床倫理4分割表", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_width = page_width / 2

    quadrant_labels = [
        ("1. 医学的適応", "medical_indications"),
        ("2. 患者の意向", "patient_preferences"),
        ("3. QOL", "qol"),
        ("4. 周囲の状況", "contextual_features"),
    ]

    # Row 1
    _render_row(pdf, col_width, [
        (quadrant_labels[0][0], table.get(quadrant_labels[0][1], {})),
        (quadrant_labels[1][0], table.get(quadrant_labels[1][1], {})),
    ])
    pdf.ln(4)

    # Row 2
    _render_row(pdf, col_width, [
        (quadrant_labels[2][0], table.get(quadrant_labels[2][1], {})),
        (quadrant_labels[3][0], table.get(quadrant_labels[3][1], {})),
    ])

    # --- 検討ポイント ---
    pdf.add_page()
    pdf.set_font("NotoSansJP", "", 13)
    pdf.cell(0, 8, "検討すべきポイント", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("NotoSansJP", "", 10)
    for i, point in enumerate(discussion_points, 1):
        pdf.multi_cell(0, 6, f"{i}. {point}")
        pdf.ln(2)

    # --- 緊張関係 ---
    if tensions:
        pdf.ln(4)
        pdf.set_font("NotoSansJP", "", 13)
        pdf.cell(0, 8, "象限間の緊張関係", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("NotoSansJP", "", 10)
        for tension in tensions:
            pdf.multi_cell(0, 6, f"\u30fb{tension}")
            pdf.ln(2)

    return bytes(pdf.output())


def _render_row(pdf: FPDF, col_width: float, quadrants: list[tuple[str, dict]]):
    """2つの象限を横並びで描画"""
    x_start = pdf.l_margin
    y_start = pdf.get_y()

    col_heights = []

    for i, (title, data) in enumerate(quadrants):
        x = x_start + i * col_width
        pdf.set_xy(x, y_start)

        # タイトル
        pdf.set_font("NotoSansJP", "", 11)
        pdf.set_fill_color(230, 240, 250)
        pdf.cell(col_width, 7, f" {title}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        # 内容
        pdf.set_font("NotoSansJP", "", 9)
        content_start_y = pdf.get_y()
        for key, value in data.items():
            pdf.set_x(x)
            pdf.multi_cell(col_width, 5, f"[{key}] {value}", border="LR")

        # 下罫線位置を記録
        col_heights.append(pdf.get_y())

    # 高さを揃える
    max_y = max(col_heights) if col_heights else y_start
    for i in range(len(quadrants)):
        x = x_start + i * col_width
        if col_heights[i] < max_y:
            # 短い方を埋める
            pdf.set_xy(x, col_heights[i])
            pdf.cell(col_width, max_y - col_heights[i], "", border="LR")
        # 下罫線
        pdf.set_xy(x, max_y)
        pdf.cell(col_width, 0, "", border="T")

    pdf.set_y(max_y)
