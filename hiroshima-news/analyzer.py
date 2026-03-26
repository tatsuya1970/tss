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


def generate_briefing(articles: list[dict]) -> str:
    """記事リストからAIブリーフィングを生成する"""
    if not articles:
        return "対象記事がありません。"

    # 上位30件に絞る（トークン節約）
    targets = sorted(articles, key=lambda a: -(a.get("score") or 1))[:30]
    lines = "\n".join(
        [f"- [{a['city']}]【{a.get('category','その他')}】{a['title']}　{a.get('published_at','')}"
         for a in targets]
    )

    prompt = f"""あなたはテレビ局の優秀なリサーチャーです。
以下は広島県の市町から収集した最新情報の一覧です。
テレビ局のディレクター・報道デスク向けに、朝のブリーフィングを日本語で作成してください。

【形式】
・冒頭に全体の概況を2〜3文でまとめる
・カテゴリ別に注目情報を箇条書きで整理する
・最後に「AIが注目する案件」として取材候補を1〜3件挙げ、その理由も添える
・全体で400字程度にまとめる

【記事一覧】
{lines}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
