"""
로컬 실행 → SQLite (core/db_sqlite.py)
클라우드 배포 → Supabase (core/db_supabase.py)
secrets.toml에 [supabase] 섹션이 있으면 자동으로 Supabase를 사용합니다.
"""
from __future__ import annotations


def _use_cloud() -> bool:
    try:
        import streamlit as st
        return 'supabase' in st.secrets
    except Exception:
        return False


if _use_cloud():
    from core.db_supabase import (
        init_db,
        get_or_create_user,
        save_content,
        list_contents,
        get_content,
        delete_content,
        get_progress,
        upsert_progress,
        get_all_progress,
        get_translation,
        save_translation,
    )
else:
    from core.db_sqlite import (
        init_db,
        get_or_create_user,
        save_content,
        list_contents,
        get_content,
        delete_content,
        get_progress,
        upsert_progress,
        get_all_progress,
        get_translation,
        save_translation,
    )
