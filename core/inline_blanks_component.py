from __future__ import annotations
import os
import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'components', 'inline_blanks')

_inline_blanks = components.declare_component(
    "inline_blanks",
    path=_COMPONENT_DIR,
)


def inline_blanks_input(tokens: list, hints: list, results: list | None = None, key: str | None = None):
    """
    문장을 인라인 빈칸 입력 형태로 렌더링하는 컴포넌트.
    제출 시 {'type': 'submit', 'answers': [...]} 반환, 그 외엔 None.
    """
    serialized_tokens = [
        {
            'token': t.get('token', ''),
            'blank': bool(t.get('blank', False)),
            'answer': t.get('answer', '') if t.get('blank') else '',
        }
        for t in tokens
    ]
    return _inline_blanks(
        tokens=serialized_tokens,
        hints=hints,
        results=results,
        key=key,
        default=None,
    )
