from __future__ import annotations
import json
import streamlit as st
from supabase import create_client, Client


def _client() -> Client:
    url = st.secrets['supabase']['url']
    key = st.secrets['supabase']['key']
    return create_client(url, key)


def init_db():
    pass  # Supabase 테이블은 대시보드에서 미리 생성


# ── 사용자 ───────────────────────────────────────────────────────────

def get_or_create_user(nickname: str) -> dict:
    sb = _client()
    res = sb.table('users').select('*').eq('nickname', nickname).execute()
    if res.data:
        return res.data[0]
    res = sb.table('users').insert({'nickname': nickname}).execute()
    return res.data[0]


# ── 콘텐츠 ──────────────────────────────────────────────────────────

def save_content(title: str, source_type: str, raw_text: str,
                 sentences: list[str], created_by: int, source_url: str = '') -> int:
    sb = _client()
    res = sb.table('contents').insert({
        'title': title,
        'source_type': source_type,
        'source_url': source_url,
        'raw_text': raw_text,
        'sentences': json.dumps(sentences, ensure_ascii=False),
        'created_by': created_by,
    }).execute()
    return res.data[0]['id']


def list_contents(user_id: int | None = None) -> list[dict]:
    sb = _client()
    query = sb.table('contents').select('*, users(nickname)').order('id', desc=True)
    if user_id is not None:
        query = query.eq('created_by', user_id)
    res = query.execute()
    result = []
    for r in res.data:
        r['nickname'] = (r.pop('users') or {}).get('nickname', '')
        r['sentences'] = json.loads(r['sentences'])
        result.append(r)
    return result


def get_content(content_id: int) -> dict | None:
    sb = _client()
    res = sb.table('contents').select('*').eq('id', content_id).execute()
    if not res.data:
        return None
    d = res.data[0]
    d['sentences'] = json.loads(d['sentences'])
    return d


def delete_content(content_id: int):
    sb = _client()
    sb.table('translations').delete().eq('content_id', content_id).execute()
    sb.table('progress').delete().eq('content_id', content_id).execute()
    sb.table('contents').delete().eq('id', content_id).execute()


# ── 진도 ─────────────────────────────────────────────────────────────

def get_progress(user_id: int, content_id: int, sentence_index: int) -> dict:
    sb = _client()
    res = sb.table('progress').select('*') \
        .eq('user_id', user_id).eq('content_id', content_id) \
        .eq('sentence_index', sentence_index).execute()
    if res.data:
        return res.data[0]
    return {'user_id': user_id, 'content_id': content_id,
            'sentence_index': sentence_index, 'stage': 1,
            'attempts': 0, 'correct': 0, 'total_blanks': 0, 'completed': 0}


def upsert_progress(user_id: int, content_id: int, sentence_index: int,
                    stage: int, attempts: int, correct: int, total_blanks: int, completed: int):
    sb = _client()
    sb.table('progress').upsert({
        'user_id': user_id,
        'content_id': content_id,
        'sentence_index': sentence_index,
        'stage': stage,
        'attempts': attempts,
        'correct': correct,
        'total_blanks': total_blanks,
        'completed': completed,
    }, on_conflict='user_id,content_id,sentence_index').execute()


def skip_sentence(user_id: int, content_id: int, sentence_index: int):
    """문장을 건너뜀 상태(stage=0)로 저장"""
    sb = _client()
    sb.table('progress').upsert({
        'user_id': user_id,
        'content_id': content_id,
        'sentence_index': sentence_index,
        'stage': 0,
        'attempts': 0,
        'correct': 0,
        'total_blanks': 0,
        'completed': 0,
    }, on_conflict='user_id,content_id,sentence_index').execute()


def get_recent_content_id(user_id: int) -> int | None:
    """가장 최근에 학습한 content_id 반환"""
    sb = _client()
    res = sb.table('progress').select('content_id, updated_at') \
        .eq('user_id', user_id) \
        .order('updated_at', desc=True) \
        .limit(1).execute()
    return res.data[0]['content_id'] if res.data else None


def get_all_progress(user_id: int, content_id: int) -> list[dict]:
    sb = _client()
    res = sb.table('progress').select('*') \
        .eq('user_id', user_id).eq('content_id', content_id) \
        .order('sentence_index').execute()
    return res.data


# ── 번역 캐시 ────────────────────────────────────────────────────────

def get_translation(content_id: int, sentence_index: int) -> str | None:
    sb = _client()
    res = sb.table('translations').select('korean') \
        .eq('content_id', content_id).eq('sentence_index', sentence_index).execute()
    return res.data[0]['korean'] if res.data else None


def save_translation(content_id: int, sentence_index: int, korean: str):
    sb = _client()
    sb.table('translations').upsert({
        'content_id': content_id,
        'sentence_index': sentence_index,
        'korean': korean,
    }, on_conflict='content_id,sentence_index').execute()
