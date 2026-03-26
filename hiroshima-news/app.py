import streamlit as st
import pandas as pd
import re
from datetime import date, timedelta
from scraper import fetch_all
from analyzer import analyze_articles
from database import init_db, get_known_urls, save_articles, load_all_articles, get_stats, get_uncategorized_articles, update_article_analysis

st.set_page_config(
    page_title="広島県 市町情報ダッシュボード",
    page_icon="📰",
    layout="wide",
)

init_db()

st.markdown("""
<style>
/* ヘッダーバー */
.tss-header {
    background-color: #E60012;
    padding: 16px 24px;
    margin-bottom: 24px;
    border-radius: 4px;
}
.tss-header h1 {
    color: #FFFFFF;
    font-size: 1.8rem;
    font-weight: 900;
    margin: 0;
    letter-spacing: 0.02em;
}
.tss-header span {
    color: #FFB3BA;
    font-size: 0.85rem;
    font-weight: 500;
}
/* カテゴリバッジ */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 4px;
}
</style>
<div class="tss-header">
  <h1>広島県 市町情報 リアルタイムダッシュボード</h1>
  <span>すきゅん TSS ✕ AI &nbsp;|&nbsp; 広島県23市町の最新情報を自動収集・分析</span>
</div>
""", unsafe_allow_html=True)

# サイドバー：フィルター
st.sidebar.header("フィルター")
selected_categories = st.sidebar.multiselect(
    "カテゴリ",
    ["防災・安全", "福祉・医療", "経済・産業", "教育・文化", "インフラ・都市", "その他"],
)
selected_cities = st.sidebar.multiselect(
    "市町",
    [
        "広島市", "福山市", "呉市", "廿日市市", "尾道市", "東広島市",
        "竹原市", "三原市", "府中市", "三次市", "庄原市", "大竹市",
        "安芸高田市", "江田島市",
        "府中町", "海田町", "熊野町", "坂町",
        "安芸太田町", "北広島町", "大崎上島町", "世羅町", "神石高原町",
    ],
)
date_from = st.sidebar.date_input("開始日", value=date.today() - timedelta(days=30))
date_to = st.sidebar.date_input("終了日", value=date.today())
# DB統計
stats = get_stats()
if stats["last_fetch"]:
    st.sidebar.divider()
    st.sidebar.caption(f"📦 DB保存件数: {stats['total']}件")
    st.sidebar.caption(f"🕐 前回取得: {stats['last_fetch']}")

# データ取得ボタン
if st.button("🔄 新着情報を取得・分析する", type="primary"):
    known_urls = get_known_urls()

    with st.spinner("市町村サイトからデータを収集中..."):
        all_articles = fetch_all()

    # 新着のみ抽出（DBに未保存のURL）
    new_articles = [a for a in all_articles if a["url"] not in known_urls]

    if not new_articles:
        st.info("前回取得以降、新しい記事はありませんでした。")
    else:
        try:
            with st.spinner("AIで分析中..."):
                analyzed = analyze_articles(new_articles)
            for a in analyzed:
                a.setdefault("summary", "")
                a.setdefault("category", "その他")
                a.setdefault("score", 1)
            save_articles(analyzed)
            st.success(f"✅ {len(analyzed)}件の新着記事を取得・保存しました")
        except Exception as e:
            st.error(f"分析エラー: {e}")

    # 既存のカテゴリ未設定記事を再分析
    uncategorized = get_uncategorized_articles()
    if uncategorized:
        try:
            with st.spinner(f"既存の未分類記事 {len(uncategorized)}件 を分析中..."):
                analyzed_existing = analyze_articles(uncategorized)
            for a in analyzed_existing:
                update_article_analysis(a["url"], a.get("summary", ""), a.get("category", "その他"), a.get("score", 1))
            st.success(f"✅ 既存記事 {len(analyzed_existing)}件 のカテゴリを更新しました")
        except Exception as e:
            st.error(f"既存記事の分析エラー: {e}")

# DB から全記事を読み込んで表示
articles = load_all_articles()

if articles:
    df = pd.DataFrame(articles)

    # フィルター適用（未選択時はすべて表示）
    if selected_categories:
        df = df[df["category"].isin(selected_categories)]
    if selected_cities:
        df = df[df["city"].isin(selected_cities)]

    # 日付フィルター（published_atがある記事のみ対象）
    def to_date(s):
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", str(s))
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    df["_date"] = df["published_at"].apply(to_date)
    df = df[df["_date"].isna() | ((df["_date"] >= date_from) & (df["_date"] <= date_to))]
    df = df.drop(columns=["_date"])

    # 日付順ソート（新しい順）
    def parse_date(s):
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", str(s))
        return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)
    df["_date_key"] = df["published_at"].apply(parse_date)
    df = df.sort_values("_date_key", ascending=False).drop(columns=["_date_key"])

    # 統計
    col1, col2 = st.columns(2)
    col1.metric("表示件数", len(df))
    col2.metric("対象市町数", df["city"].nunique())

    st.divider()

    # 記事一覧
    for _, row in df.iterrows():
        published = row.get("published_at", "") or ""
        pub_prefix = f"{published} ／ " if published else ""
        url = row.get("url", "")
        label = f"{pub_prefix}[{row['city']}] {row['title']}"
        if url:
            st.markdown(f"- [{label}]({url})")
        else:
            st.markdown(f"- {label}")
else:
    st.info("「新着情報を取得・分析する」ボタンを押してください")
