import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CATEGORIES = ["防災・安全", "福祉・医療", "経済・産業", "教育・文化", "インフラ・都市", "その他"]

def analyze_articles(articles: list[dict]) -> list[dict]:
    """記事リストをまとめてAIで分析する"""
    if not articles:
        return []

    # タイトル一覧をまとめてAPIに投げる（コスト節約）
    titles_text = "\n".join(
        [f"{i+1}. [{a['city']}] {a['title']}" for i, a in enumerate(articles)]
    )

    prompt = f"""以下は広島県の市町村プレスリリースのタイトル一覧です。
各記事について以下をJSON配列で返してください：
- summary: 15字以内の要約
- category: {CATEGORIES} のいずれか
- score: ニュースバリュー（1〜5の整数、5が最重要）

タイトル一覧：
{titles_text}

必ずJSON配列のみ返してください。例：
[{{"summary":"...","category":"...","score":3}}, ...]
"""

    import json
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    content = response.choices[0].message.content.strip()
    # ```json ... ``` 形式で返ってきた場合に対応
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    results = json.loads(content)
    for i, article in enumerate(articles):
        if i < len(results):
            article["summary"] = results[i].get("summary", "")
            article["category"] = results[i].get("category", "その他")
            article["score"] = results[i].get("score", 1)
        else:
            article["summary"] = ""
            article["category"] = "その他"
            article["score"] = 1
    return articles
