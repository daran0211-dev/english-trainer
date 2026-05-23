"""
URL 쿼리 파라미터(?u=닉네임)로 로그인 상태를 유지합니다.
- 페이지 이동 시: session_state가 유지되므로 자동으로 쿼리 파라미터 갱신
- 새로고침 시: URL의 ?u= 값으로 세션 복원
"""
from __future__ import annotations
import streamlit as st
from core.db import get_or_create_user


def restore_session():
    """홈(app.py)에서 호출. 쿼리 파라미터로 세션 복원."""
    if 'user_id' in st.session_state:
        # 이미 로그인 상태 → 쿼리 파라미터 유지
        if 'u' not in st.query_params:
            st.query_params['u'] = st.session_state['nickname']
        return

    saved = st.query_params.get('u', '').strip()
    if saved:
        try:
            user = get_or_create_user(saved)
            st.session_state['user_id'] = user['id']
            st.session_state['nickname'] = user['nickname']
        except Exception:
            pass


def save_login(nickname: str):
    """로그인 시 쿼리 파라미터에 닉네임 저장."""
    st.query_params['u'] = nickname


def clear_login():
    """로그아웃 시 쿼리 파라미터 삭제."""
    st.query_params.clear()


def require_login(message: str = "먼저 홈 화면에서 닉네임으로 시작해주세요."):
    """
    각 페이지 상단에서 호출.
    1) session_state에 user_id 있으면 → 쿼리 파라미터 갱신 후 통과
    2) 쿼리 파라미터 ?u= 있으면 → 세션 복원 후 통과
    3) 둘 다 없으면 → 경고 후 중단
    """
    if 'user_id' in st.session_state:
        # 페이지 이동 후 첫 렌더 → 이 페이지 URL에도 ?u= 추가
        if 'u' not in st.query_params:
            st.query_params['u'] = st.session_state['nickname']
        return

    saved = st.query_params.get('u', '').strip()
    if saved:
        try:
            user = get_or_create_user(saved)
            st.session_state['user_id'] = user['id']
            st.session_state['nickname'] = user['nickname']
            return
        except Exception:
            pass

    st.warning(message)
    st.stop()
