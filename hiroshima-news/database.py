import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "articles.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """テーブルが存在しない場合のみ作成"""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                url       TEXT PRIMARY KEY,
                city      TEXT NOT NULL,
                title     TEXT NOT NULL,
                published_at TEXT,
                fetched_at   TEXT,
                summary   TEXT,
                category  TEXT,
                score     INTEGER
            )
        """)


def get_known_urls() -> set[str]:
    """DB に保存済みの URL 一覧を返す"""
    with get_conn() as conn:
        rows = conn.execute("SELECT url FROM articles").fetchall()
    return {row["url"] for row in rows}


def save_articles(articles: list[dict]):
    """新規記事をDBに保存（既存URLはスキップ）"""
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO articles
                (url, city, title, published_at, fetched_at, summary, category, score)
            VALUES
                (:url, :city, :title, :published_at, :fetched_at, :summary, :category, :score)
            """,
            articles,
        )


def load_all_articles() -> list[dict]:
    """DB の全記事を published_at 降順で返す"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM articles
            ORDER BY published_at DESC, fetched_at DESC
        """).fetchall()
    return [dict(row) for row in rows]


def get_uncategorized_articles() -> list[dict]:
    """カテゴリが未設定（その他）または空の記事を返す"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM articles
            WHERE category IS NULL OR category = '' OR category = 'その他'
        """).fetchall()
    return [dict(row) for row in rows]


def update_article_analysis(url: str, summary: str, category: str, score: int):
    """記事の要約・カテゴリ・スコアを更新する"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE articles SET summary=?, category=?, score=? WHERE url=?",
            (summary, category, score, url),
        )


def get_stats() -> dict:
    """統計情報を返す"""
    with get_conn() as conn:
        total      = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        cities     = conn.execute("SELECT COUNT(DISTINCT city) FROM articles").fetchone()[0]
        last_fetch = conn.execute("SELECT MAX(fetched_at) FROM articles").fetchone()[0]
    return {"total": total, "cities": cities, "last_fetch": last_fetch}
