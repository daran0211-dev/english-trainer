from __future__ import annotations
import re
import hashlib

# 단계별로 빈칸을 만들 품사 집합
_STAGE_POS: dict[int, set[str] | None] = {
    1: {'NN', 'NNS', 'VB', 'VBD', 'VBZ', 'VBP'},
    2: {'NN', 'NNS', 'NNP', 'VB', 'VBD', 'VBZ', 'VBG', 'VBP', 'JJ', 'JJR', 'JJS'},
    3: {'NN', 'NNS', 'NNP', 'NNPS', 'VB', 'VBD', 'VBZ', 'VBG', 'VBN', 'VBP',
        'JJ', 'JJR', 'JJS', 'RB', 'RBR', 'RBS'},
    4: {'NN', 'NNS', 'NNP', 'NNPS', 'VB', 'VBD', 'VBZ', 'VBG', 'VBN', 'VBP',
        'JJ', 'JJR', 'JJS', 'RB', 'RBR', 'RBS', 'CD', 'MD', 'IN', 'DT'},
    5: None,  # 전체
}

# 단계별 빈칸 비율
_STAGE_RATIO = {1: 0.20, 2: 0.40, 3: 0.60, 4: 0.80, 5: 1.0}


def _tokenize(sentence: str) -> list[str]:
    """단어와 비단어(공백·구두점)를 순서 유지한 채 분리."""
    return re.findall(r"[A-Za-z']+|[^A-Za-z']+", sentence)


def _pos_tag(words: list[str]) -> list[tuple[str, str]]:
    """품사 태깅. NLTK 실패 시 모두 'NN'으로 처리."""
    try:
        import nltk
        return nltk.pos_tag(words)
    except Exception:
        return [(w, 'NN') for w in words]


def _stable_indices(candidates: list[int], ratio: float, seed: str) -> set[int]:
    """동일 seed면 항상 같은 인덱스를 선택 (재현성 보장)."""
    n = max(1, round(len(candidates) * ratio))
    # seed 기반 결정론적 셔플
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    shuffled = sorted(candidates, key=lambda i: (h * (i + 1)) % (10 ** 9))
    return set(shuffled[:n])


def make_blanks(sentence: str, stage: int) -> list[dict]:
    """
    반환값 예시:
    [
      {'token': 'The',   'is_word': True,  'blank': False, 'answer': 'The'},
      {'token': ' ',     'is_word': False, 'blank': False, 'answer': ' '},
      {'token': 'quick', 'is_word': True,  'blank': True,  'answer': 'quick'},
      ...
    ]
    """
    tokens = _tokenize(sentence)
    word_tokens = [(i, t) for i, t in enumerate(tokens) if re.match(r"[A-Za-z']", t)]

    # 품사 태깅
    words_only = [t for _, t in word_tokens]
    tagged = _pos_tag(words_only)

    target_pos = _STAGE_POS[stage]
    ratio = _STAGE_RATIO[stage]

    # 빈칸 후보: 해당 단계 품사에 해당하는 단어
    if target_pos is None:
        candidates = [i for i, _ in enumerate(word_tokens)]
    else:
        candidates = [
            i for i, (_, pos) in enumerate(tagged)
            if pos in target_pos
        ]

    # 후보가 없으면 전체 단어 사용
    if not candidates:
        candidates = list(range(len(word_tokens)))

    seed = f"{sentence}|{stage}"
    blank_word_indices = _stable_indices(candidates, ratio, seed)

    # 결과 조립
    result = []
    word_cursor = 0
    for i, token in enumerate(tokens):
        is_word = bool(re.match(r"[A-Za-z']", token))
        if is_word:
            blank = word_cursor in blank_word_indices
            result.append({
                'token': token,
                'is_word': True,
                'blank': blank,
                'answer': token,
            })
            word_cursor += 1
        else:
            result.append({
                'token': token,
                'is_word': False,
                'blank': False,
                'answer': token,
            })
    return result


def hint_char(answer: str) -> str:
    """첫 글자만 공개한 힌트 문자열."""
    if not answer:
        return ''
    return answer[0] + '_' * (len(answer) - 1)


def blank_display(answer: str) -> str:
    """빈칸 표시: 글자 수만큼 언더스코어."""
    return '_' * len(answer)
