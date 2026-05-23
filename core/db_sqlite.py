from __future__ import annotations
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'trainer.db')


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            nickname TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_url TEXT,
            raw_text TEXT NOT NULL,
            sentences TEXT NOT NULL,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            sentence_index INTEGER NOT NULL,
            stage INTEGER NOT NULL DEFAULT 1,
            attempts INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            total_blanks INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            last_practiced TEXT,
            UNIQUE(user_id, content_id, sentence_index)
        );
        CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY,
            content_id INTEGER NOT NULL,
            sentence_index INTEGER NOT NULL,
            korean TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(content_id, sentence_index)
        );
        """)


# ── 사용자 ───────────────────────────────────────────────────────────

def get_or_create_user(nickname: str) -> dict:
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE nickname=?", (nickname,)).fetchone()
        if row:
            return dict(row)
        con.execute("INSERT INTO users(nickname) VALUES(?)", (nickname,))
        row = con.execute("SELECT * FROM users WHERE nickname=?", (nickname,)).fetchone()
        return dict(row)


# ── 콘텐츠 ──────────────────────────────────────────────────────────

def save_content(title: str, source_type: str, raw_text: str,
                 sentences: list[str], created_by: int, source_url: str = '') -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO contents(title,source_type,source_url,raw_text,sentences,created_by) VALUES(?,?,?,?,?,?)",
            (title, source_type, source_url, raw_text, json.dumps(sentences, ensure_ascii=False), created_by)
        )
        return cur.lastrowid


def list_contents() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT c.*, u.nickname FROM contents c LEFT JOIN users u ON c.created_by=u.id ORDER BY c.id DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['sentences'] = json.loads(d['sentences'])
            result.append(d)
        return result


def get_content(content_id: int) -> dict | None:
    with _conn() as con:
        row = con.execute("SELECT * FROM contents WHERE id=?", (content_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d['sentences'] = json.loads(d['sentences'])
        return d


def delete_content(content_id: int):
    with _conn() as con:
        con.execute("DELETE FROM contents WHERE id=?", (content_id,))
        con.execute("DELETE FROM progress WHERE content_id=?", (content_id,))


# ── 진도 ─────────────────────────────────────────────────────────────

def get_progress(user_id: int, content_id: int, sentence_index: int) -> dict:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM progress WHERE user_id=? AND content_id=? AND sentence_index=?",
            (user_id, content_id, sentence_index)
        ).fetchone()
        if row:
            return dict(row)
        return {'user_id': user_id, 'content_id': content_id,
                'sentence_index': sentence_index, 'stage': 1,
                'attempts': 0, 'correct': 0, 'total_blanks': 0, 'completed': 0}


def upsert_progress(user_id: int, content_id: int, sentence_index: int,
                    stage: int, attempts: int, correct: int, total_blanks: int, completed: int):
    with _conn() as con:
        con.execute("""
        INSERT INTO progress(user_id,content_id,sentence_index,stage,attempts,correct,total_blanks,completed,last_practiced)
        VALUES(?,?,?,?,?,?,?,?,datetime('now'))
        ON CONFLICT(user_id,content_id,sentence_index) DO UPDATE SET
            stage=excluded.stage,
            attempts=excluded.attempts,
            correct=excluded.correct,
            total_blanks=excluded.total_blanks,
            completed=excluded.completed,
            last_practiced=excluded.last_practiced
        """, (user_id, content_id, sentence_index, stage, attempts, correct, total_blanks, completed))


# ── 번역 캐시 ────────────────────────────────────────────────────────

def get_translation(content_id: int, sentence_index: int) -> str | None:
    with _conn() as con:
        row = con.execute(
            "SELECT korean FROM translations WHERE content_id=? AND sentence_index=?",
            (content_id, sentence_index)
        ).fetchone()
        return row['korean'] if row else None


def save_translation(content_id: int, sentence_index: int, korean: str):
    with _conn() as con:
        con.execute("""
        INSERT INTO translations(content_id, sentence_index, korean)
        VALUES(?,?,?)
        ON CONFLICT(content_id, sentence_index) DO UPDATE SET korean=excluded.korean
        """, (content_id, sentence_index, korean))


def get_all_progress(user_id: int, content_id: int) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM progress WHERE user_id=? AND content_id=? ORDER BY sentence_index",
            (user_id, content_id)
        ).fetchall()
        return [dict(r) for r in rows]
