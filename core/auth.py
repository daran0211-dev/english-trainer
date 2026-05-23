"""
새로고침 후 로그인 상태를 복원하는 헬퍼.
URL 쿼리 파라미터 ?u=닉네임 에 로그인 정보를 저장해 두고,
session_state가 비어 있을 때 자동으로 복원합니다.
"""
from __future__ import annotations
import streamlit as st
from core.db import get_or_create_user


def restore_session() -> bool:
    """
    session_state에 user_id가 없으면 URL 파라미터에서 닉네임을 읽어 복원.
    로그인 상태면 True, 비로그인이면 False 반환.
    """
    if 'user_id' not in st.session_state:
        saved = st.query_params.get('u', '').strip()
        if saved:
            user = get_or_create_user(saved)
            st.session_state['user_id'] = user['id']
            st.session_state['nickname'] = user['nickname']

    return 'user_id' in st.session_state


def require_login(message: str = "먼저 홈 화면에서 닉네임으로 시작해주세요."):
    """
    로그인 상태가 아니면 경고를 표시하고 페이지를 중단.
    각 페이지 상단에서 호출하세요.
    """
    if not restore_session():
        st.warning(message)
        st.stop()
