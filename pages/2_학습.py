import streamlit as st
from core.db import list_contents, get_progress, upsert_progress, get_translation, save_translation, get_recent_content_id, skip_sentence
from core.blanker import make_blanks, hint_char, blank_display
from core.scorer import check_all
from core.translator import translate_to_korean
from core.auth import require_login

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
titles = list(content_map.keys())

# 가장 최근 학습한 콘텐츠를 기본값으로
recent_id = get_recent_content_id(user_id)
recent_title = next((c['title'] for c in contents if c['id'] == recent_id), None)
default_content_idx = titles.index(recent_title) if recent_title in titles else 0

selected_title = st.selectbox("콘텐츠 선택", titles, index=default_content_idx)
content = content_map[selected_title]
sentences = content['sentences']
content_id = content['id']

# ── 문장 선택 ─────────────────────────────────────────────────────────
prog_list = [get_progress(user_id, content_id, i) for i in range(len(sentences))]
completed_count = sum(1 for p in prog_list if p['completed'])

st.progress(completed_count / len(sentences), text=f"완료: {completed_count} / {len(sentences)} 문장")

# stage=0 → 건너뜀 (DB에 영구 저장)
skipped_set = {i for i, p in enumerate(prog_list) if p.get('stage') == 0}
incomplete   = [i for i, p in enumerate(prog_list) if not p['completed'] and p.get('stage') != 0]
not_skipped  = incomplete  # 건너뜀 제외한 미완료

# 마지막으로 풀던 문장 기억 (session_state)
current_key = f"current_{content_id}"
if current_key not in st.session_state:
    st.session_state[current_key] = not_skipped[0] if not_skipped else 0

preferred = st.session_state[current_key]
if preferred in not_skipped:
    default_idx = preferred
else:
    default_idx = not_skipped[0] if not_skipped else 0

sentence_labels = []
for i, p in enumerate(prog_list):
    if p['completed']:
        status = "✅"
    elif p.get('stage') == 0:
        status = "⏭ 건너뜀"
    else:
        status = f"▶ {p['stage']}단계"
    sentence_labels.append(f"[{i+1}] {status} — {sentences[i][:40]}...")

sent_idx = st.selectbox("문장 선택", range(len(sentences)),
                         index=default_idx,
                         format_func=lambda i: sentence_labels[i])

# 사용자가 직접 문장을 바꾸면 현재 문장 업데이트
st.session_state[current_key] = sent_idx

# 건너뛴 문장을 직접 선택하면 건너뛰기 해제 (stage=1로 복원)
if sent_idx in skipped_set:
    upsert_progress(user_id, content_id, sent_idx, 1, 0, 0, 0, 0)
    st.rerun()

sentence = sentences[sent_idx]
prog = get_progress(user_id, content_id, sent_idx)
stage = prog['stage'] if prog['stage'] > 0 else 1  # 건너뜀 상태면 1단계로 표시

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

# ── 문장 표시 (번호 붙인 빈칸) ────────────────────────────────────────
NUMS = ['①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩',
        '⑪','⑫','⑬','⑭','⑮','⑯','⑰','⑱','⑲','⑳']

display_parts = []
blank_cursor = 0
for t in tokens:
    if t['blank']:
        if results is not None:
            color = 'green' if results[0][blank_cursor] else 'red'
            display_parts.append(
                f"<span style='color:{color};font-weight:bold'>[{t['answer']}]</span>"
            )
        else:
            num = NUMS[blank_cursor] if blank_cursor < len(NUMS) else f"({blank_cursor+1})"
            display_parts.append(
                f"<span style='background:#e8f0fe;padding:1px 6px;"
                f"border-radius:4px;font-family:monospace;border-bottom:2px solid #4F8EF7'>"
                f"{num}</span>"
            )
        blank_cursor += 1
    else:
        display_parts.append(t['token'])

st.markdown(
    f"<p style='font-size:1.1em;line-height:2.2'>{''.join(display_parts)}</p>",
    unsafe_allow_html=True
)

# ── 한국어 번역 토글 ──────────────────────────────────────────────────
show_kr_key = f"show_kr_{content_id}_{sent_idx}"
if show_kr_key not in st.session_state:
    st.session_state[show_kr_key] = False

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
            f"padding:10px 16px;border-radius:6px;color:#333;font-size:1em;margin-bottom:8px'>"
            f"🇰🇷 {korean}</div>",
            unsafe_allow_html=True
        )
    else:
        st.caption("번역을 가져오지 못했습니다.")

# ── 입력 폼 ───────────────────────────────────────────────────────────
if results is None:
    with st.form(key=f"form_{content_id}_{sent_idx}_{stage}"):
        user_inputs = []
        for idx, tok in enumerate(blank_tokens):
            num = NUMS[idx] if idx < len(NUMS) else f"({idx+1})"
            hint_text = hint_char(tok['answer']) if hints[idx] else '_' * len(tok['answer'])
            val = st.text_input(
                f"{num}",
                placeholder=hint_text,
                key=f"inp_{content_id}_{sent_idx}_{stage}_{idx}",
            )
            user_inputs.append(val)

        col_hint, col_submit, col_skip = st.columns(3)
        with col_hint:
            hint_btn = st.form_submit_button("💡 힌트", use_container_width=True)
        with col_submit:
            submit_btn = st.form_submit_button("✅ 제출", type='primary', use_container_width=True)
        with col_skip:
            skip_btn = st.form_submit_button("⏭ 건너뛰기", use_container_width=True)

    if hint_btn:
        for i in range(n_blanks):
            if not hints[i]:
                st.session_state[state_key][i] = True
                break
        st.rerun()

    if submit_btn:
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

    if skip_btn:
        # stage=0 으로 DB에 저장 (건너뜀 영구 기록)
        upsert_progress(user_id, content_id, sent_idx,
                        0, prog['attempts'], prog['correct'],
                        prog.get('total_blanks', 0), 0)
        # 다음 문장으로 이동
        remaining = [i for i in not_skipped if i != sent_idx]
        if remaining:
            st.session_state[current_key] = remaining[0]
        st.rerun()

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
