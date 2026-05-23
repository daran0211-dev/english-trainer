from __future__ import annotations


def translate_to_korean(text: str) -> str:
    """영어 텍스트를 한국어로 번역. 실패 시 빈 문자열 반환."""
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source='en', target='ko').translate(text)
    except Exception:
        return ''
