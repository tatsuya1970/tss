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


def generate_briefing(articles: list[dict]) -> tuple[dict, list[dict]]:
    """記事リストからAIブリーフィングを生成する。(構造化dict, 参照記事リスト) を返す"""
    if not articles:
        return {}, []

    import json as _json

    # 上位30件に絞る（トークン節約）
    targets = sorted(articles, key=lambda a: -(a.get("score") or 1))[:30]
    lines = "\n".join(
        [f"{i+1}. [{a['city']}]【{a.get('category','その他')}】{a['title']}　{a.get('published_at','')}"
         for i, a in enumerate(targets)]
    )

    prompt = f"""あなたはテレビ局の優秀なリサーチャーです。
以下は広島県の市町から収集した最新情報の一覧（番号付き）です。
テレビ局のディレクター・報道デスク向けのブリーフィングを、以下のJSON形式のみで出力してください。

{{
  "overview": "全体の概況（2〜3文）",
  "categories": [
    {{
      "name": "カテゴリ名",
      "items": [
        {{
          "text": "記事の説明文（日付・句点なし）",
          "article_index": 記事番号（1始まり）,
          "date": "YYYY年M月D日"
        }}
      ]
    }}
  ],
  "notable": [
    {{
      "title": "取材候補のキーワード（10字以内）",
      "reason": "取材候補として推薦する理由",
      "article_index": 記事番号
    }}
  ],
  "closing": "締めのテキスト（1文）"
}}

【記事一覧】
{lines}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    content = response.choices[0].message.content.strip()
    return _json.loads(content), targets
