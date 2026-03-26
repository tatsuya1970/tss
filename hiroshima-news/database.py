import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    url          TEXT PRIMARY KEY,
                    city         TEXT NOT NULL,
                    title        TEXT NOT NULL,
                    published_at TEXT,
                    fetched_at   TEXT,
                    summary      TEXT,
                    category     TEXT,
                    score        INTEGER
                )
            """)


def get_known_urls() -> set:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT url FROM articles")
            return {row[0] for row in cur.fetchall()}


def save_articles(articles: list):
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, """
                INSERT INTO articles
                    (url, city, title, published_at, fetched_at, summary, category, score)
                VALUES
                    (%(url)s, %(city)s, %(title)s, %(published_at)s, %(fetched_at)s,
                     %(summary)s, %(category)s, %(score)s)
                ON CONFLICT (url) DO NOTHING
            """, articles)


def load_all_articles() -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM articles
                ORDER BY published_at DESC, fetched_at DESC
            """)
            return [dict(row) for row in cur.fetchall()]


def get_uncategorized_articles() -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM articles
                WHERE category IS NULL OR category = '' OR category = 'その他'
            """)
            return [dict(row) for row in cur.fetchall()]


def update_article_analysis(url: str, summary: str, category: str, score: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE articles SET summary=%s, category=%s, score=%s WHERE url=%s",
                (summary, category, score, url),
            )


def get_stats() -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM articles")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT city) FROM articles")
            cities = cur.fetchone()[0]
            cur.execute("SELECT MAX(fetched_at) FROM articles")
            last_fetch = cur.fetchone()[0]
    return {"total": total, "cities": cities, "last_fetch": last_fetch}
