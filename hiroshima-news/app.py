import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import re
import requests
from datetime import date, timedelta
from scraper import fetch_all
from analyzer import analyze_articles, generate_briefing
from database import init_db, get_known_urls, save_articles, load_all_articles, get_stats, get_uncategorized_articles, update_article_analysis, delete_articles_without_date

st.set_page_config(
    page_title="広島県 市町情報ダッシュボード",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()


def render_briefing(data: dict, sources: list):
    """構造化ブリーフィングデータをMarkdownで表示する"""
    if not data:
        return
    url_map = {i + 1: a.get("url", "") for i, a in enumerate(sources)}

    lines = []
    if data.get("overview"):
        lines.append(data["overview"])
        lines.append("")

    for cat in data.get("categories", []):
        lines.append(f"【{cat['name']}】")
        lines.append("")
        for item in cat.get("items", []):
            idx = item.get("article_index", 0)
            url = url_map.get(idx, "")
            date = item.get("date", "")
            text = item.get("text", "")
            if url and date:
                lines.append(f"- {text}（[{date}]({url})）")
            elif date:
                lines.append(f"- {text}（{date}）")
            else:
                lines.append(f"- {text}")
        lines.append("")

    notables = data.get("notable", [])
    if notables:
        lines.append("**AIが注目する案件**")
        lines.append("")
        for j, n in enumerate(notables, 1):
            idx = n.get("article_index", 0)
            url = url_map.get(idx, "")
            title = n.get("title", "")
            reason = n.get("reason", "")
            link = f" [🔗]({url})" if url else ""
            lines.append(f"{j}. **{title}** - {reason}{link}")
        lines.append("")

    st.info("📋 **AIブリーフィング**\n\n" + "\n".join(lines))
delete_articles_without_date("神石高原町")

st.markdown("""
<style>
/* Streamlitデフォルトのヘッダーを非表示 */
header[data-testid="stHeader"] { display: none; }
/* サイドバーの開閉ボタンを非表示 */
button[data-testid="stSidebarCollapseButton"] { display: none; }
button[data-testid="stSidebarOpenButton"] { display: none; }
</style>
<div style="background-color:#E60012; padding:22px 32px 18px 32px; margin-bottom:24px; position:sticky; top:0; z-index:999;">
  <div style="color:#FFFFFF; font-size:3rem; font-weight:900; margin:0 0 10px 0; letter-spacing:0.02em; line-height:1.1;">広島県 市町情報</div>
  <div style="color:#FFB3BA; font-size:1rem; font-weight:600;">すきゅん TSS ✕ AI &nbsp;|&nbsp; 広島県23市町の最新情報を自動収集・分析</div>
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
# フィルター条件のブリーフィング
st.sidebar.divider()
if st.sidebar.button("📋 選択中の情報をブリーフィング", use_container_width=True):
    st.session_state["run_briefing"] = True

# DB統計
stats = get_stats()
if stats["last_fetch"]:
    st.sidebar.divider()
    st.sidebar.caption(f"📦 DB保存件数: {stats['total']}件")
    st.sidebar.caption(f"🕐 前回取得: {stats['last_fetch']}")

# 上部2カラム：左（取得ボタン＋ブリーフィング）・右（SNSトレンド）
col_left, col_sns = st.columns([3, 2])

with col_left:
    if st.button("🔄 新着情報を取得・分析する", type="primary"):
        known_urls = get_known_urls()

        with st.spinner("市町村サイトからデータを収集中..."):
            all_articles = fetch_all()

        new_articles = [a for a in all_articles if a["url"] not in known_urls]

        analyzed = []
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

        if analyzed:
            try:
                with st.spinner("AIブリーフィングを生成中..."):
                    briefing_data, briefing_sources = generate_briefing(analyzed)
                render_briefing(briefing_data, briefing_sources)
            except Exception as e:
                st.warning(f"ブリーフィング生成エラー: {e}")

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

with col_sns:
    st.markdown("### 📱 SNSトレンド")
    try:
        sns_resp = requests.get("https://sns-analyze.onrender.com/api/events", timeout=10)
        sns_events = sns_resp.json() if sns_resp.status_code == 200 else []
    except Exception:
        sns_events = []

    if sns_events:
        for event in sns_events[:8]:
            st.markdown(f"・{event['name']}")
    else:
        st.caption("データ取得中...")

    st.markdown("[SNSトレンドマップを開く →](https://sns-analyze.onrender.com/)")
    components.iframe("https://sns-analyze.onrender.com/", height=400, scrolling=True)

# DB から全記事を読み込んで表示
articles = load_all_articles()

if articles:
    df = pd.DataFrame(articles)

    if selected_categories:
        df = df[df["category"].isin(selected_categories)]
    if selected_cities:
        df = df[df["city"].isin(selected_cities)]

    def to_date(s):
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", str(s))
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    df["_date"] = df["published_at"].apply(to_date)
    df = df[df["_date"].isna() | ((df["_date"] >= date_from) & (df["_date"] <= date_to))]
    df = df.drop(columns=["_date"])

    def parse_date(s):
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", str(s))
        return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)
    df["_date_key"] = df["published_at"].apply(parse_date)
    df = df.sort_values("_date_key", ascending=False).drop(columns=["_date_key"])

    if st.session_state.pop("run_briefing", False):
        try:
            with st.spinner("AIブリーフィングを生成中..."):
                briefing_data, briefing_sources = generate_briefing(df.to_dict("records"))
            render_briefing(briefing_data, briefing_sources)
        except Exception as e:
            st.warning(f"ブリーフィング生成エラー: {e}")

    c1, c2 = st.columns(2)
    c1.metric("総件数", len(df))
    c2.metric("対象市町数", df["city"].nunique())

    st.divider()

    PAGE_SIZE = 50
    total = len(df)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    if "page" not in st.session_state:
        st.session_state.page = 1
    st.session_state.page = min(st.session_state.page, total_pages)

    start = (st.session_state.page - 1) * PAGE_SIZE
    page_df = df.iloc[start:start + PAGE_SIZE]

    for _, row in page_df.iterrows():
        published = row.get("published_at", "") or ""
        pub_prefix = f"{published} ／ " if published else ""
        url = row.get("url", "")
        label = f"{pub_prefix}[{row['city']}] {row['title']}"
        if url:
            st.markdown(f"- [{label}]({url})")
        else:
            st.markdown(f"- {label}")

    st.divider()
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("◀ 前へ", disabled=st.session_state.page <= 1):
            st.session_state.page -= 1
            st.rerun()
    with col_info:
        st.markdown(
            f"<div style='text-align:center; padding-top:6px;'>{st.session_state.page} / {total_pages} ページ（{total}件）</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("次へ ▶", disabled=st.session_state.page >= total_pages):
            st.session_state.page += 1
            st.rerun()
else:
    st.info("「新着情報を取得・分析する」ボタンを押してください")
