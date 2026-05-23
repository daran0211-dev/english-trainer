from __future__ import annotations
import re


def extract_youtube_id(url: str) -> str | None:
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def fetch_youtube_transcript(url: str) -> tuple[str, str]:
    """(vid_id, full_text) 반환. 실패 시 예외."""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

    vid_id = extract_youtube_id(url)
    if not vid_id:
        raise ValueError("유효한 YouTube URL이 아닙니다.")

    api = YouTubeTranscriptApi()

    # 영어 자막 우선 시도
    try:
        fetched = api.fetch(vid_id)
    except (NoTranscriptFound, TranscriptsDisabled):
        # 자막 목록에서 영어 찾기
        transcript_list = api.list(vid_id)
        fetched = None
        for lang in ['en', 'en-US', 'en-GB']:
            try:
                fetched = transcript_list.find_transcript([lang]).fetch()
                break
            except Exception:
                continue
        if fetched is None:
            raise ValueError("영어 자막을 찾을 수 없습니다. 영어 자막이 있는 영상인지 확인해주세요.")

    text = ' '.join(s.text for s in fetched)
    text = re.sub(r'\s+', ' ', text).strip()
    return vid_id, text


def extract_pdf(file_bytes: bytes) -> str:
    """PDF에서 텍스트 추출."""
    import pdfplumber, io
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    raw = '\n'.join(text_parts)
    # 줄바꿈/하이픈 이어붙임 정리
    raw = re.sub(r'-\n', '', raw)          # 하이픈 줄바꿈 제거
    raw = re.sub(r'\n+', ' ', raw)         # 나머지 줄바꿈 → 공백
    raw = re.sub(r'\s+', ' ', raw).strip()
    return raw


def extract_docx(file_bytes: bytes) -> str:
    """Word(.docx)에서 텍스트 추출."""
    import docx, io
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    raw = ' '.join(paragraphs)
    raw = re.sub(r'\s+', ' ', raw).strip()
    return raw


def split_sentences(text: str) -> list[str]:
    """문장 분리 — NLTK 우선, 실패 시 정규식 fallback."""
    try:
        import nltk
        sentences = nltk.sent_tokenize(text)
    except Exception:
        sentences = re.split(r'(?<=[.!?])\s+', text)

    cleaned = []
    for s in sentences:
        s = s.strip()
        # 너무 짧거나 단어가 3개 미만인 문장 제외
        if len(s) > 10 and len(s.split()) >= 3:
            cleaned.append(s)
    return cleaned
