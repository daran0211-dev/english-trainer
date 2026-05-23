from __future__ import annotations


def check_answer(user_input: str, answer: str) -> bool:
    """대소문자·앞뒤공백 무시 비교."""
    return user_input.strip().lower() == answer.strip().lower()


def check_all(user_inputs: list[str], tokens: list[dict]) -> tuple[list[bool], int, int]:
    """
    반환: (결과 리스트, 맞은 수, 전체 빈칸 수)
    """
    blank_tokens = [t for t in tokens if t['blank']]
    results = []
    for inp, tok in zip(user_inputs, blank_tokens):
        results.append(check_answer(inp, tok['answer']))
    correct = sum(results)
    return results, correct, len(blank_tokens)
