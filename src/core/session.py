"""会话存储 —— SQLite 持久化会话（Hermes 风格）"""

import os
import json
import sqlite3
import time


# 数据库路径
_db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sessions.db")


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接，自动初始化表结构"""
    os.makedirs(os.path.dirname(_db_path), exist_ok=True)
    conn = sqlite3.connect(_db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,              -- 会话标题
            messages TEXT,           -- JSON 序列化的消息列表
            created_at REAL,         -- Unix 时间戳
            tool_calls INTEGER DEFAULT 0  -- 工具调用次数
        )
    """)
    # FTS5 全文搜索虚拟表（Hermes 风格：跨会话内容搜索）
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
            id, title, content, tokenize='unicode61'
        )
    """)
    conn.commit()
    return conn


def save_session(session_id: str, title: str, messages: list[dict], tool_calls: int = 0):
    """保存会话到 SQLite 并建立 FTS5 索引"""
    conn = _get_conn()
    conn.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?)",
                 (session_id, title, json.dumps(messages, ensure_ascii=False), time.time(), tool_calls))
    # 同步 FTS5 索引
    content_text = " ".join(str(m.get("content", "")) for m in messages)
    conn.execute("INSERT OR REPLACE INTO sessions_fts VALUES (?, ?, ?)",
                 (session_id, title, content_text))
    conn.commit()
    conn.close()

def search_sessions(query: str, limit: int = 10) -> list[dict]:
    """FTS5 全文搜索会话内容"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT s.id, s.title, s.created_at, s.tool_calls "
        "FROM sessions s JOIN sessions_fts f ON s.id = f.id "
        "WHERE sessions_fts MATCH ? LIMIT ?",
        (query, limit)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "created_at": r[2], "tool_calls": r[3]} for r in rows]


def load_session(session_id: str) -> dict | None:
    """加载指定会话，返回 {title, messages, tool_calls} 或 None"""
    conn = _get_conn()
    row = conn.execute("SELECT title, messages, tool_calls FROM sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    return {"title": row[0], "messages": json.loads(row[1]), "tool_calls": row[2]} if row else None


def list_sessions(limit: int = 10) -> list[dict]:
    """列出最近会话"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, title, created_at, tool_calls FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "created_at": r[2], "tool_calls": r[3]} for r in rows]


def delete_session(session_id: str):
    """删除指定会话"""
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()
