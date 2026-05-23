import streamlit as st
from core.db import list_contents, get_progress, upsert_progress, get_translation, save_translation
from core.blanker import make_blanks, hint_char, blank_display
from core.scorer import check_all
from core.translator import translate_to_korean
from core.auth import require_login
from core.inline_blanks_component import inline_blanks_input

st.set_page_config(page_title="학습", layout="centered", page_icon="✏️")
st.title("✏️ 학습")

require_login()

try:
    contents = list_contents(user_id=st.session_state['user_id'])
except Exception:
    contents = []

if not contents:
    st.info("콘텐츠가 없습니다. 먼저 **콘텐츠** 페이지에서 추가해주세요.")
    st.stop()

user_id = st.session_state['user_id']

# ── 콘텐츠 선택 ──────────────────────────────────────────────────────
content_map = {c['title']: c for c in contents}
selected_title = st.selectbox("콘텐츠 선택", list(content_map.keys()))
content = content_map[selected_title]
sentences = content['sentences']
content_id = content['id']

# ── 문장 선택 ─────────────────────────────────────────────────────────
prog_list = [get_progress(user_id, content_id, i) for i in range(len(sentences))]
completed_count = sum(1 for p in prog_list if p['completed'])

st.progress(completed_count / len(sentences), text=f"완료: {completed_count} / {len(sentences)} 문장")

incomplete = [i for i, p in enumerate(prog_list) if not p['completed']]
default_idx = incomplete[0] if incomplete else 0

sentence_labels = []
for i, p in enumerate(prog_list):
    status = "✅" if p['completed'] else f"▶ {p['stage']}단계"
    sentence_labels.append(f"[{i+1}] {status} — {sentences[i][:40]}...")

sent_idx = st.selectbox("문장 선택", range(len(sentences)),
                         index=default_idx,
                         format_func=lambda i: sentence_labels[i])

sentence = sentences[sent_idx]
prog = get_progress(user_id, content_id, sent_idx)
stage = prog['stage']

st.markdown("---")

# ── 원문 컨텍스트 ─────────────────────────────────────────────────────
with st.expander("📖 전체 원문 보기", expanded=False):
    st.markdown(
        f"<p style='color:#aaa;font-size:0.9em'>{content['raw_text'][:800]}"
        f"{'...' if len(content['raw_text'])>800 else ''}</p>",
        unsafe_allow_html=True
    )

# ── 단계 표시 ─────────────────────────────────────────────────────────
stage_labels = {1:'🟢 1단계 (20%)', 2:'🟡 2단계 (40%)', 3:'🟠 3단계 (60%)',
                4:'🔴 4단계 (80%)', 5:'⚫ 5단계 (100%)'}
st.markdown(f"### {stage_labels.get(stage, f'{stage}단계')}")

if prog['completed']:
    st.success("🎉 이 문장은 이미 완료했습니다! 다른 문장을 선택하거나 다시 연습하세요.")

# ── 빈칸 생성 ─────────────────────────────────────────────────────────
tokens = make_blanks(sentence, stage)
blank_tokens = [t for t in tokens if t['blank']]
n_blanks = len(blank_tokens)

state_key  = f"hints_{content_id}_{sent_idx}_{stage}"
result_key = f"results_{content_id}_{sent_idx}_{stage}"
if state_key not in st.session_state:
    st.session_state[state_key] = [False] * n_blanks
if result_key not in st.session_state:
    st.session_state[result_key] = None

hints   = st.session_state[state_key]
results = st.session_state[result_key]

# ── 한국어 번역 토글 ──────────────────────────────────────────────────
show_kr_key = f"show_kr_{content_id}_{sent_idx}"
if show_kr_key not in st.session_state:
    st.session_state[show_kr_key] = False

col_kr, _ = st.columns([1, 4])
with col_kr:
    if st.button(
        "🇰🇷 한국어 숨기기" if st.session_state[show_kr_key] else "🇰🇷 한국어 보기",
        use_container_width=True
    ):
        st.session_state[show_kr_key] = not st.session_state[show_kr_key]
        st.rerun()

if st.session_state[show_kr_key]:
    korean = get_translation(content_id, sent_idx)
    if not korean:
        with st.spinner("번역 중..."):
            korean = translate_to_korean(sentence)
            if korean:
                save_translation(content_id, sent_idx, korean)
    if korean:
        st.markdown(
            f"<div style='background:#f0f4ff;border-left:3px solid #4F8EF7;"
            f"padding:10px 16px;border-radius:6px;color:#333;font-size:1em'>"
            f"🇰🇷 {korean}</div>",
            unsafe_allow_html=True
        )
    else:
        st.caption("번역을 가져오지 못했습니다. 인터넷 연결을 확인해주세요.")

st.markdown("")

# ── 인라인 빈칸 입력 컴포넌트 ─────────────────────────────────────────
result_list_display = results[0] if results else None

component_value = inline_blanks_input(
    tokens=tokens,
    hints=hints,
    results=result_list_display,
    key=f"blanks_{content_id}_{sent_idx}_{stage}",
)

# 제출 처리
if component_value and component_value.get('type') == 'submit' and results is None:
    user_inputs = component_value['answers']
    result_list, correct, total = check_all(user_inputs, tokens)
    st.session_state[result_key] = (result_list, correct, total)
    new_attempts     = prog['attempts'] + 1
    new_correct      = prog['correct'] + correct
    new_total_blanks = prog.get('total_blanks', 0) + total
    all_correct      = correct == total
    next_stage       = min(stage + 1, 5) if all_correct else stage
    completed        = 1 if all_correct and stage == 5 else prog['completed']
    upsert_progress(user_id, content_id, sent_idx,
                    next_stage, new_attempts, new_correct, new_total_blanks, completed)
    st.rerun()

# ── 결과 표시 & 버튼 ──────────────────────────────────────────────────
if results is None:
    col_hint, col_skip = st.columns(2)
    with col_hint:
        if st.button("💡 힌트", use_container_width=True):
            for i in range(n_blanks):
                if not hints[i]:
                    st.session_state[state_key][i] = True
                    break
            st.rerun()
    with col_skip:
        if st.button("⏭ 건너뛰기", use_container_width=True):
            st.info("건너뛰었습니다. 다음 문장을 선택해주세요.")
else:
    result_list, correct, total = results
    if correct == total:
        if stage == 5:
            st.success(f"🎉 완벽합니다! {total}/{total} 정답 — **이 문장을 완전히 외웠습니다!**")
        else:
            st.success(f"✅ 모두 정답! {total}/{total} — 다음 단계로 올라갑니다 🚀")
    else:
        wrong = total - correct
        st.warning(f"아쉽네요. {correct}/{total} 정답 ({wrong}개 틀림). 다시 도전해보세요!")

    if st.button("🔄 다시 풀기", type='primary'):
        del st.session_state[result_key]
        del st.session_state[state_key]
        st.rerun()
