import streamlit as st
from core.db import save_content, list_contents, delete_content
from core.extractor import fetch_youtube_transcript, split_sentences, extract_pdf, extract_docx
from core.auth import require_login

st.set_page_config(page_title="콘텐츠", layout="centered", page_icon="📚")
st.title("📚 콘텐츠 추가")

require_login()

# ── 입력 탭 ──────────────────────────────────────────────────────────
tab_yt, tab_file, tab_text = st.tabs(["🎬 유튜브", "📄 파일 (PDF / Word)", "📝 텍스트 붙여넣기"])

# ── 유튜브 탭 ─────────────────────────────────────────────────────────
with tab_yt:
    st.markdown("유튜브 영상의 영어 자막을 자동으로 가져옵니다.")
    yt_url   = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
    yt_title = st.text_input("콘텐츠 제목 (선택)", placeholder="비워두면 영상 ID로 저장됩니다")

    if st.button("자막 가져오기", type='primary', key='fetch_yt'):
        if not yt_url.strip():
            st.warning("URL을 입력해주세요.")
        else:
            with st.spinner("자막을 추출하는 중..."):
                try:
                    vid_id, raw_text = fetch_youtube_transcript(yt_url.strip())
                    sentences = split_sentences(raw_text)
                    title = yt_title.strip() or f"YouTube: {vid_id}"
                    save_content(title=title, source_type='youtube', raw_text=raw_text,
                                 sentences=sentences, created_by=st.session_state['user_id'],
                                 source_url=yt_url.strip())
                    st.success(f"✅ 저장 완료! 총 **{len(sentences)}개** 문장")
                    st.rerun()
                except Exception as e:
                    st.error(f"자막 추출 실패: {e}\n\n영어 자막이 없거나 비공개 영상일 수 있습니다.")

# ── 파일 탭 ───────────────────────────────────────────────────────────
with tab_file:
    st.markdown("PDF 또는 Word 파일을 업로드하면 텍스트를 자동으로 추출합니다.")
    st.caption("지원 형식: `.pdf` `.docx`")

    uploaded_file = st.file_uploader(
        "파일 선택",
        type=['pdf', 'docx'],
        label_visibility='collapsed',
    )

    file_title = st.text_input("콘텐츠 제목", placeholder="예) The Economist — April 2024",
                               key='file_title')

    if uploaded_file:
        # 미리보기
        with st.spinner("텍스트 추출 중..."):
            try:
                file_bytes = uploaded_file.read()
                ext = uploaded_file.name.rsplit('.', 1)[-1].lower()

                if ext == 'pdf':
                    raw_text = extract_pdf(file_bytes)
                elif ext == 'docx':
                    raw_text = extract_docx(file_bytes)
                else:
                    raw_text = ''

                if not raw_text.strip():
                    st.warning("텍스트를 추출하지 못했습니다. 스캔된 이미지 PDF는 지원하지 않습니다.")
                else:
                    sentences = split_sentences(raw_text)
                    st.info(f"**{len(sentences)}개** 문장 추출됨 — 미리보기:")
                    st.text_area("추출된 텍스트 (수정 불가)", raw_text[:1000] + ('...' if len(raw_text) > 1000 else ''),
                                 height=180, disabled=True, key='file_preview')

                    if st.button("저장", type='primary', key='save_file'):
                        if not file_title.strip():
                            st.warning("제목을 입력해주세요.")
                        else:
                            save_content(
                                title=file_title.strip(),
                                source_type=ext,
                                raw_text=raw_text,
                                sentences=sentences,
                                created_by=st.session_state['user_id'],
                                source_url=uploaded_file.name,
                            )
                            st.success(f"✅ 저장 완료! 총 **{len(sentences)}개** 문장")
                            st.rerun()
            except Exception as e:
                st.error(f"파일 처리 실패: {e}")

# ── 텍스트 탭 ─────────────────────────────────────────────────────────
with tab_text:
    st.markdown("에세이, 뉴스, 책 등 영어 텍스트를 직접 붙여넣으세요.")
    text_title = st.text_input("제목", placeholder="예) TED Talk — Do schools kill creativity?")
    text_body  = st.text_area("본문", height=250, placeholder="영어 텍스트를 여기에 붙여넣으세요...")

    if st.button("저장", type='primary', key='save_text'):
        if not text_title.strip():
            st.warning("제목을 입력해주세요.")
        elif not text_body.strip():
            st.warning("본문을 입력해주세요.")
        else:
            sentences = split_sentences(text_body.strip())
            if not sentences:
                st.warning("문장을 인식하지 못했습니다. 영어 텍스트인지 확인해주세요.")
            else:
                save_content(title=text_title.strip(), source_type='text',
                             raw_text=text_body.strip(), sentences=sentences,
                             created_by=st.session_state['user_id'])
                st.success(f"✅ 저장 완료! 총 **{len(sentences)}개** 문장")
                st.rerun()

# ── 저장된 콘텐츠 목록 ────────────────────────────────────────────────
st.markdown("---")
st.subheader("저장된 콘텐츠")

SOURCE_ICONS = {'youtube': '🎬', 'pdf': '📄', 'docx': '📄', 'text': '📝'}

contents = list_contents()
if not contents:
    st.info("아직 추가된 콘텐츠가 없습니다. 위에서 파일이나 유튜브 URL을 추가해보세요.")
else:
    for c in contents:
        with st.container(border=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                icon = SOURCE_ICONS.get(c['source_type'], '📝')
                st.markdown(f"**{icon} {c['title']}**")
                st.caption(f"{len(c['sentences'])}개 문장 · 추가: {c['nickname'] or '알 수 없음'} · {c['created_at'][:10]}")
            with col2:
                if st.button("삭제", key=f"del_{c['id']}", type='secondary'):
                    delete_content(c['id'])
                    st.rerun()
