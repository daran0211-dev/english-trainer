"""
쿠키에 닉네임을 저장해 새로고침/페이지 이동 후에도 로그인 상태를 유지합니다.
"""
from __future__ import annotations
import streamlit as st
from streamlit_cookies_controller import CookieController
from core.db import get_or_create_user

COOKIE_NAME = 'et_nickname'  # english-trainer nickname


def require_login(message: str = "먼저 홈 화면에서 닉네임으로 시작해주세요."):
    """
    로그인 상태가 아니면 쿠키에서 복원 시도.
    실패 시 경고 메시지를 표시하고 페이지를 중단.
    """
    if 'user_id' in st.session_state:
        return  # 이미 로그인됨

    # 쿠키에서 복원 시도
    controller = CookieController(key='auth_restore')
    cookies = controller.getAll()

    if cookies is None:
        # 첫 렌더링: 쿠키 아직 로드 안 됨 → 자동 재실행 대기
        st.stop()

    saved = cookies.get(COOKIE_NAME, '').strip()
    if saved:
        try:
            user = get_or_create_user(saved)
            st.session_state['user_id'] = user['id']
            st.session_state['nickname'] = user['nickname']
            st.rerun()
        except Exception:
            pass

    if 'user_id' not in st.session_state:
        st.warning(message)
        st.stop()


def restore_session():
    """홈(app.py)에서 세션 복원용"""
    if 'user_id' in st.session_state:
        return

    controller = CookieController(key='auth_home')
    cookies = controller.getAll()

    if cookies is None:
        return  # 첫 렌더링, 쿠키 아직 없음 — 자동 재실행됨

    saved = cookies.get(COOKIE_NAME, '').strip()
    if saved:
        try:
            user = get_or_create_user(saved)
            st.session_state['user_id'] = user['id']
            st.session_state['nickname'] = user['nickname']
        except Exception:
            pass


def save_login(nickname: str):
    """로그인 시 쿠키에 닉네임 저장 (유효기간 30일)"""
    try:
        controller = CookieController(key='auth_save')
        controller.set(COOKIE_NAME, nickname, max_age=30 * 24 * 60 * 60)
    except Exception:
        pass


def clear_login():
    """로그아웃 시 쿠키 삭제"""
    try:
        controller = CookieController(key='auth_clear')
        controller.remove(COOKIE_NAME)
    except Exception:
        pass
