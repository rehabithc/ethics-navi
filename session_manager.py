"""Streamlitセッション状態管理"""

import streamlit as st
from config import QUADRANTS


def init_session():
    """セッション状態を初期化"""
    if "phase" not in st.session_state:
        st.session_state.phase = "input"
        st.session_state.current_quadrant = 0
        st.session_state.case_overview = ""
        st.session_state.conversations = {q["key"]: [] for q in QUADRANTS}
        st.session_state.quadrant_summaries = {q["key"]: None for q in QUADRANTS}
        st.session_state.full_table_data = None


def get_current_quadrant() -> dict:
    """現在の象限の設定を取得"""
    return QUADRANTS[st.session_state.current_quadrant]


def add_message(quadrant_key: str, role: str, content: str):
    """会話履歴にメッセージを追加"""
    st.session_state.conversations[quadrant_key].append(
        {"role": role, "content": content}
    )


def advance_quadrant():
    """次の象限へ進む。全象限完了ならまとめフェーズへ"""
    if st.session_state.current_quadrant < len(QUADRANTS) - 1:
        st.session_state.current_quadrant += 1
    else:
        st.session_state.phase = "summary"


def reset_session():
    """セッションをリセット"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
