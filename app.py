"""EthicsNavi - 臨床倫理4分割AI相談 メインアプリ"""

import streamlit as st

from config import QUADRANTS, DISCLAIMER
from claude_client import EthicsNaviClient
from session_manager import (
    init_session,
    get_current_quadrant,
    add_message,
    advance_quadrant,
    reset_session,
)
from pdf_generator import generate_pdf

st.set_page_config(
    page_title="EthicsNavi - 臨床倫理4分割表",
    page_icon="\u2696\ufe0f",
    layout="wide",
)

init_session()


# --- サイドバー ---
with st.sidebar:
    st.title("\u2696\ufe0f EthicsNavi")
    st.caption("臨床倫理4分割AI相談")
    st.divider()

    st.markdown("**進行状況**")
    phases = [
        ("input", "ケース入力"),
        ("quadrant_0", "1. 医学的適応"),
        ("quadrant_1", "2. 患者の意向"),
        ("quadrant_2", "3. QOL"),
        ("quadrant_3", "4. 周囲の状況"),
        ("summary", "まとめ"),
        ("report", "レポート出力"),
    ]

    for phase_key, label in phases:
        if phase_key == "input":
            done = st.session_state.phase != "input"
            current = st.session_state.phase == "input"
        elif phase_key.startswith("quadrant_"):
            idx = int(phase_key.split("_")[1])
            done = (
                st.session_state.phase in ("summary", "report")
                or (
                    st.session_state.phase == "quadrant"
                    and st.session_state.current_quadrant > idx
                )
            )
            current = (
                st.session_state.phase == "quadrant"
                and st.session_state.current_quadrant == idx
            )
        elif phase_key == "summary":
            done = st.session_state.phase == "report"
            current = st.session_state.phase == "summary"
        else:
            done = False
            current = st.session_state.phase == "report"

        if done:
            st.markdown(f"\u2705 ~~{label}~~")
        elif current:
            st.markdown(f"\u25b6\ufe0f **{label}**")
        else:
            st.markdown(f"\u2b1c {label}")

    st.divider()
    if st.button("新しいケースを開始", use_container_width=True):
        reset_session()
        st.rerun()

    st.divider()
    st.warning(f"\u26a0\ufe0f {DISCLAIMER}")


# --- クライアント初期化 ---
@st.cache_resource
def get_client():
    return EthicsNaviClient()


client = get_client()


# --- Phase 1: ケース入力 ---
if st.session_state.phase == "input":
    st.header("ケース概要を入力してください")
    st.markdown("倫理的に検討が必要なケースの概要を自由に記述してください。")

    case_text = st.text_area(
        "ケース概要",
        height=200,
        placeholder="例: 80歳男性、進行性肺癌。本人は積極的治療を望んでいないが、家族は治療継続を強く希望している...",
    )

    if st.button("整理を開始する", type="primary", disabled=not case_text.strip()):
        st.session_state.case_overview = case_text.strip()
        st.session_state.phase = "quadrant"
        st.rerun()


# --- Phase 2: 4象限対話 ---
elif st.session_state.phase == "quadrant":
    quad = get_current_quadrant()
    quad_idx = st.session_state.current_quadrant + 1

    st.header(f"{quad_idx}. {quad['title_ja']}（{quad['title_en']}）")
    st.caption(f"サブトピック: {' / '.join(quad['subtopics'])}")

    conversation = st.session_state.conversations[quad["key"]]

    # 会話履歴を表示
    for msg in conversation:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 初回: AIの最初の質問を生成
    if len(conversation) == 0:
        with st.chat_message("assistant"):
            response = st.write_stream(
                client.ask_quadrant_questions_stream(
                    case_overview=st.session_state.case_overview,
                    quadrant_key=quad["key"],
                    conversation=[],
                )
            )
        add_message(quad["key"], "assistant", response)
        st.rerun()

    # ユーザー入力
    if user_input := st.chat_input("回答を入力してください..."):
        add_message(quad["key"], "user", user_input)

        # 完了チェック
        completion = client.check_quadrant_completion(
            quadrant_key=quad["key"],
            conversation=st.session_state.conversations[quad["key"]],
        )

        if completion["is_complete"]:
            st.session_state.quadrant_summaries[quad["key"]] = completion["summary"]
            st.toast(f"{quad['title_ja']}の整理が完了しました", icon="\u2705")
            advance_quadrant()
            st.rerun()
        else:
            remaining = completion.get("remaining_subtopics", quad["subtopics"])
            with st.chat_message("assistant"):
                response = st.write_stream(
                    client.ask_quadrant_questions_stream(
                        case_overview=st.session_state.case_overview,
                        quadrant_key=quad["key"],
                        conversation=st.session_state.conversations[quad["key"]],
                        remaining_subtopics=remaining,
                    )
                )
            add_message(quad["key"], "assistant", response)
            st.rerun()

    # 手動ナビゲーション
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.current_quadrant > 0:
            if st.button("\u2190 前の象限に戻る"):
                st.session_state.current_quadrant -= 1
                st.rerun()
    with col2:
        if st.button("この象限を完了して次へ \u2192", type="primary"):
            # 強制的に要約して次へ
            conv = st.session_state.conversations[quad["key"]]
            if conv:
                completion = client.check_quadrant_completion(
                    quadrant_key=quad["key"],
                    conversation=conv,
                )
                st.session_state.quadrant_summaries[quad["key"]] = (
                    completion.get("summary", "")
                )
            advance_quadrant()
            st.rerun()


# --- Phase 3: まとめ ---
elif st.session_state.phase == "summary":
    st.header("Jonsenの臨床倫理4分割表")

    if st.session_state.full_table_data is None:
        with st.spinner("4分割表を生成中..."):
            table_data = client.synthesize_table(
                case_overview=st.session_state.case_overview,
                quadrant_summaries={
                    k: v or "（未整理）"
                    for k, v in st.session_state.quadrant_summaries.items()
                },
            )
            st.session_state.full_table_data = table_data
    else:
        table_data = st.session_state.full_table_data

    # 4分割表を2x2で表示
    table = table_data.get("table", {})

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("1. 医学的適応")
            for k, v in table.get("medical_indications", {}).items():
                st.markdown(f"**{k}**")
                st.markdown(f"{v}")
    with col2:
        with st.container(border=True):
            st.subheader("2. 患者の意向")
            for k, v in table.get("patient_preferences", {}).items():
                st.markdown(f"**{k}**")
                st.markdown(f"{v}")

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.subheader("3. QOL")
            for k, v in table.get("qol", {}).items():
                st.markdown(f"**{k}**")
                st.markdown(f"{v}")
    with col4:
        with st.container(border=True):
            st.subheader("4. 周囲の状況")
            for k, v in table.get("contextual_features", {}).items():
                st.markdown(f"**{k}**")
                st.markdown(f"{v}")

    # 検討ポイント
    st.divider()
    st.subheader("検討すべきポイント")
    for point in table_data.get("discussion_points", []):
        st.markdown(f"- {point}")

    # 緊張関係
    tensions = table_data.get("tensions", [])
    if tensions:
        st.subheader("象限間の緊張関係")
        for tension in tensions:
            st.markdown(f"- {tension}")

    st.divider()
    if st.button("PDFレポートを生成する", type="primary"):
        st.session_state.phase = "report"
        st.rerun()


# --- Phase 4: レポート出力 ---
elif st.session_state.phase == "report":
    st.header("レポート出力")

    table_data = st.session_state.full_table_data

    with st.spinner("PDF を生成中..."):
        pdf_bytes = generate_pdf(
            case_overview=st.session_state.case_overview,
            table_data=table_data,
        )

    st.download_button(
        label="\U0001f4e5 PDFをダウンロード",
        data=pdf_bytes,
        file_name="ethics_navi_report.pdf",
        mime="application/pdf",
        type="primary",
    )

    st.divider()
    st.info(DISCLAIMER)

    # まとめ画面と同じ表を表示
    st.subheader("Jonsenの臨床倫理4分割表")
    table = table_data.get("table", {})

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**1. 医学的適応**")
            for k, v in table.get("medical_indications", {}).items():
                st.markdown(f"- **{k}**: {v}")
    with col2:
        with st.container(border=True):
            st.markdown("**2. 患者の意向**")
            for k, v in table.get("patient_preferences", {}).items():
                st.markdown(f"- **{k}**: {v}")

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown("**3. QOL**")
            for k, v in table.get("qol", {}).items():
                st.markdown(f"- **{k}**: {v}")
    with col4:
        with st.container(border=True):
            st.markdown("**4. 周囲の状況**")
            for k, v in table.get("contextual_features", {}).items():
                st.markdown(f"- **{k}**: {v}")
