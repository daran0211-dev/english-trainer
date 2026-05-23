import streamlit as st
from core.db import list_contents, get_all_progress
from core.auth import require_login

st.set_page_config(page_title="진도", layout="centered", page_icon="📊")
st.title("📊 나의 진도")

require_login()

user_id = st.session_state['user_id']
nickname = st.session_state['nickname']
try:
    contents = list_contents(user_id=user_id)
except Exception:
    contents = []

if not contents:
    st.info("아직 콘텐츠가 없습니다.")
    st.stop()

st.markdown(f"**👤 {nickname}** 님의 학습 현황")
st.markdown("---")

for c in contents:
    sentences = c['sentences']
    total = len(sentences)
    prog_list = get_all_progress(user_id, c['id'])
    prog_map = {p['sentence_index']: p for p in prog_list}

    completed = sum(1 for p in prog_list if p['completed'])
    total_attempts = sum(p['attempts'] for p in prog_list)
    total_correct = sum(p['correct'] for p in prog_list)
    total_blanks = sum(p.get('total_blanks', 0) for p in prog_list)
    accuracy = (total_correct / total_blanks * 100) if total_blanks > 0 else 0

    icon = "🎬" if c['source_type'] == 'youtube' else "📝"
    with st.container(border=True):
        st.markdown(f"**{icon} {c['title']}**")

        col1, col2, col3 = st.columns(3)
        col1.metric("완료 문장", f"{completed}/{total}")
        col2.metric("총 시도", total_attempts)
        col3.metric("정답률", f"{accuracy:.1f}%" if total_attempts > 0 else "-")

        st.progress(completed / total if total > 0 else 0)

        # 문장별 단계 현황
        with st.expander("문장별 상세 현황"):
            stage_icons = {1: '🟢', 2: '🟡', 3: '🟠', 4: '🔴', 5: '⚫'}
            rows = []
            for i, sent in enumerate(sentences):
                p = prog_map.get(i)
                if p and p['completed']:
                    status = "✅ 완료"
                    stage_disp = "5/5"
                elif p:
                    s = p['stage']
                    status = f"{stage_icons.get(s,'▶')} 진행 중"
                    stage_disp = f"{s}/5"
                else:
                    status = "⬜ 미시작"
                    stage_disp = "0/5"

                acc_str = ""
                if p and p.get('total_blanks', 0) > 0:
                    a = p['correct'] / p['total_blanks'] * 100
                    acc_str = f"{a:.0f}%"

                rows.append({
                    '번호': i + 1,
                    '문장': sent[:50] + ('...' if len(sent) > 50 else ''),
                    '상태': status,
                    '단계': stage_disp,
                    '정답률': acc_str,
                })

            import pandas as pd
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
