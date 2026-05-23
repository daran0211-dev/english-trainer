# 영어 암기 트레이너 — 빌드 에이전트 명세

## 목표

유튜브 영상(자막) 또는 텍스트를 입력하면, 문장의 빈칸을 단계별로 늘려가며
결국 전체 문장·문단을 통으로 암기할 수 있게 만드는 **로컬 Streamlit 웹앱**.
여러 사람이 함께 쓸 수 있도록 닉네임 기반 사용자 구분 및 개인 진도 저장.

---

## 기술 스택

| 역할 | 라이브러리 |
|---|---|
| 웹 프레임워크 | `streamlit` |
| YouTube 자막 추출 | `youtube-transcript-api` |
| 영어 품사 분석 | `nltk` |
| 로컬 DB | `sqlite3` (내장) |
| 한글 폰트 | 시스템 기본 |

```bash
pip install streamlit youtube-transcript-api nltk
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng'); nltk.download('punkt_tab')"
```

---

## 프로젝트 구조

```
english-trainer/
├── app.py                  # 홈 & 닉네임 로그인
├── agents.md
├── requirements.txt
├── 실행.command
├── data/
│   └── trainer.db          # SQLite (자동 생성)
├── pages/
│   ├── 1_콘텐츠.py          # YouTube URL / 텍스트 입력
│   ├── 2_학습.py            # 빈칸 채우기 학습
│   └── 3_진도.py            # 개인 진도 현황
├── core/
│   ├── db.py               # DB 초기화 & CRUD
│   ├── extractor.py        # YouTube 자막 추출
│   ├── blanker.py          # 빈칸 생성 (단계별)
│   └── scorer.py           # 정답 체크
└── .streamlit/
    └── config.toml
```

---

## 핵심 로직: 단계별 점진식 빈칸

### 5단계 구조

| 단계 | 빈칸 비율 | 설명 |
|---|---|---|
| 1단계 | 20% | 핵심 명사·동사 일부만 빈칸 |
| 2단계 | 40% | 형용사·부사 추가 |
| 3단계 | 60% | 절반 이상 빈칸 |
| 4단계 | 80% | 거의 다 빈칸 |
| 5단계 | 100% | 전체 빈칸, 완전 암기 |

### 빈칸 대상 단어 선정 (`core/blanker.py`)

```python
# 품사 우선순위 — 단계가 높을수록 더 많은 품사 포함
BLANK_POS_BY_STAGE = {
    1: {'NN', 'NNS', 'VB', 'VBD', 'VBZ'},           # 명사·기본동사
    2: {'NN', 'NNS', 'VB', 'VBD', 'VBZ', 'VBG',
        'JJ', 'JJR', 'JJS'},                          # + 형용사
    3: {'NN', 'NNS', 'NNP', 'VB', 'VBD', 'VBZ',
        'VBG', 'VBN', 'JJ', 'RB'},                   # + 부사
    4: {'NN', 'NNS', 'NNP', 'NNPS', 'VB', 'VBD',
        'VBZ', 'VBG', 'VBN', 'JJ', 'JJR', 'RB',
        'RBR', 'CD', 'MD'},                           # + 조동사·숫자
    5: None,  # 모든 단어
}

def make_blanks(sentence: str, stage: int) -> list[dict]:
    """
    반환값: [{'word': 'hello', 'blank': True, 'index': 0}, ...]
    단계가 같으면 항상 같은 단어가 빈칸이 되도록 seed 고정.
    """
```

### 힌트 시스템
- 빈칸에 `_` × 단어 글자수 표시 (예: `____` for "love")
- 힌트 버튼 클릭 시 첫 글자 공개 (예: `l___`)

---

## DB 스키마 (`core/db.py`)

```sql
-- 사용자
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    nickname TEXT UNIQUE NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 콘텐츠 (YouTube 또는 텍스트)
CREATE TABLE contents (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL,   -- 'youtube' | 'text'
    source_url TEXT,             -- YouTube URL
    raw_text TEXT NOT NULL,      -- 전체 원문
    sentences TEXT NOT NULL,     -- JSON 배열 (문장 분리된 것)
    created_by INTEGER,          -- users.id
    created_at TEXT DEFAULT (datetime('now'))
);

-- 학습 진도
CREATE TABLE progress (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    content_id INTEGER NOT NULL,
    sentence_index INTEGER NOT NULL,
    stage INTEGER NOT NULL DEFAULT 1,   -- 현재 단계 (1~5)
    attempts INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,        -- 5단계 완료 여부
    last_practiced TEXT,
    UNIQUE(user_id, content_id, sentence_index)
);
```

---

## 각 파일 상세 명세

### `app.py` — 홈 & 로그인

- 닉네임 입력란 → DB에 없으면 자동 생성, 있으면 기존 계정 불러오기
- `st.session_state['user_id']`, `['nickname']` 저장
- 로그인 상태에서 사이드바: 닉네임 + 전체 완료율 표시
- 미로그인 시 다른 페이지 접근 차단

### `pages/1_콘텐츠.py` — 콘텐츠 추가

탭 2개:
1. **YouTube 탭**: URL 입력 → 자막 추출 → 제목 확인 → 저장
2. **텍스트 탭**: 제목 + 본문 직접 붙여넣기 → 저장

- 저장된 콘텐츠 목록 하단에 카드 형태로 표시
- 각 카드에 삭제 버튼

### `pages/2_학습.py` — 학습 화면

레이아웃:
```
[콘텐츠 선택 드롭다운]
[진행 바: 문장 N/전체]

─────────────────────────────
원문 전체 (위에 흐리게 표시 — 컨텍스트 파악용)
─────────────────────────────

현재 문장 (단계 N/5):
"The quick [____] fox [_____] over the lazy dog."

[입력칸들]

[힌트] [제출] [건너뛰기]
─────────────────────────────
```

- 정답 제출 시: 맞은 단어 초록색, 틀린 단어 빨간색 + 정답 표시
- 전부 맞으면 → 다음 단계 자동 이동 (또는 다음 문장)
- 5단계 완료 시 🎉 축하 메시지 + 다음 문장으로

### `pages/3_진도.py` — 진도 현황

- 콘텐츠별 완료 문장 수 / 전체 문장 수 프로그레스 바
- 문장별 현재 단계 테이블 (1~5단계 중 어디인지)
- 정답률 표시

---

## 빌드 순서

```
1. requirements.txt + .streamlit/config.toml
2. core/db.py — DB 초기화 및 CRUD 함수
3. core/extractor.py — YouTube 자막 추출
4. core/blanker.py — 단계별 빈칸 생성
5. core/scorer.py — 정답 체크
6. app.py — 로그인
7. pages/1_콘텐츠.py
8. pages/2_학습.py
9. pages/3_진도.py
10. 실행.command
11. 동작 테스트
```

---

## 테스트 기준

- [ ] 닉네임 입력 → 로그인 유지
- [ ] YouTube URL 입력 → 자막 추출 → 문장 분리 저장
- [ ] 텍스트 붙여넣기 → 문장 분리 저장
- [ ] 1단계: 20% 내외 빈칸 생성 확인
- [ ] 5단계: 모든 내용어 빈칸
- [ ] 정답 입력 → 맞음/틀림 표시
- [ ] 5단계 완료 시 문장 완료 처리
- [ ] 진도 페이지에서 단계 현황 표시
- [ ] 두 명이 같은 앱 접속 시 진도 분리 확인
