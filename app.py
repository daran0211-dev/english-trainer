import streamlit as st
from core.db import init_db, get_or_create_user

init_db()

st.set_page_config(page_title="영어 암기 트레이너", layout="centered", page_icon="🧠")

# ── 새로고침 후 자동 로그인 복원 ──────────────────────────────────────
# URL 쿼리 파라미터 ?u=닉네임 에 저장 → 새로고침/페이지 이동 후 복원
if 'user_id' not in st.session_state:
    saved = st.query_params.get('u', '').strip()
    if saved:
        user = get_or_create_user(saved)
        st.session_state['user_id'] = user['id']
        st.session_state['nickname'] = user['nickname']

# ── 사이드바 ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧠 영어 암기 트레이너")
    if 'nickname' in st.session_state:
        st.success(f"👤 {st.session_state['nickname']}")
        if st.button("로그아웃"):
            del st.session_state['nickname']
            del st.session_state['user_id']
            st.query_params.clear()
            st.rerun()
    else:
        st.info("로그인 후 이용하세요")

# ── 메인 ──────────────────────────────────────────────────────────────
st.title("🧠 영어 암기 트레이너")
st.caption("유튜브·에세이 문장을 단계별 빈칸으로 통째로 외워보세요")

if 'user_id' not in st.session_state:
    st.markdown("---")
    st.subheader("시작하기")
    st.markdown("닉네임을 입력하면 바로 시작됩니다. 다음에 같은 닉네임으로 오면 진도가 이어집니다.")

    col1, col2 = st.columns([3, 1])
    with col1:
        nickname = st.text_input("닉네임", placeholder="예) randakim", label_visibility='collapsed')
    with col2:
        start = st.button("시작", use_container_width=True, type='primary')

    if start:
        if not nickname.strip():
            st.warning("닉네임을 입력해주세요.")
        else:
            user = get_or_create_user(nickname.strip())
            st.session_state['user_id'] = user['id']
            st.session_state['nickname'] = user['nickname']
            st.query_params['u'] = user['nickname']   # URL에 저장
            st.rerun()
else:
    # 로그인 상태 진입 시 URL 파라미터 유지
    if 'u' not in st.query_params:
        st.query_params['u'] = st.session_state['nickname']
    st.success(f"안녕하세요, **{st.session_state['nickname']}** 님! 👋")
    st.markdown("---")
    st.markdown("""
    ### 사용 방법
    왼쪽 메뉴에서 페이지를 선택하세요:

    - **1 콘텐츠** — 유튜브 URL 또는 텍스트를 추가합니다
    - **2 학습** — 빈칸을 채우며 문장을 단계별로 암기합니다
    - **3 진도** — 나의 학습 현황을 확인합니다

    ### 학습 단계
    | 단계 | 빈칸 비율 | 내용 |
    |---|---|---|
    | 1단계 | 20% | 핵심 명사·동사 일부 |
    | 2단계 | 40% | 형용사 추가 |
    | 3단계 | 60% | 부사 추가 |
    | 4단계 | 80% | 거의 모든 단어 |
    | 5단계 | 100% | 완전 암기 🎉 |
    """)
