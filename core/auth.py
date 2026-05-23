"""
쿠키에 닉네임을 저장해 새로고침/페이지 이동 후에도 로그인 상태를 유지합니다.
"""
from __future__ import annotations
import streamlit as st
from streamlit_cookies_controller import CookieController
from core.db import get_or_create_user

COOKIE_NAME = 'et_nickname'  # english-trainer nickname


def _controller() -> CookieController:
    return CookieController()


def restore_session() -> bool:
    """
    session_state에 user_id가 없으면 쿠키에서 닉네임을 읽어 복원.
    로그인 상태면 True, 비로그인이면 False 반환.
    """
    if 'user_id' not in st.session_state:
        try:
            controller = _controller()
            saved = controller.get(COOKIE_NAME)
            if saved:
                user = get_or_create_user(saved)
                st.session_state['user_id'] = user['id']
                st.session_state['nickname'] = user['nickname']
        except Exception:
            pass

    return 'user_id' in st.session_state


def save_login(nickname: str):
    """로그인 시 쿠키에 닉네임 저장 (유효기간 30일)"""
    try:
        controller = _controller()
        controller.set(COOKIE_NAME, nickname, max_age=30 * 24 * 60 * 60)
    except Exception:
        pass


def clear_login():
    """로그아웃 시 쿠키 삭제"""
    try:
        controller = _controller()
        controller.remove(COOKIE_NAME)
    except Exception:
        pass


def require_login(message: str = "먼저 홈 화면에서 닉네임으로 시작해주세요."):
    """
    로그인 상태가 아니면 경고를 표시하고 페이지를 중단.
    각 페이지 상단에서 호출하세요.
    """
    if not restore_session():
        st.warning(message)
        st.stop()
