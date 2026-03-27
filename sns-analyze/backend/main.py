import tweepy
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import datetime
import os
from dotenv import load_dotenv
import re
import asyncio

load_dotenv()

app = FastAPI(title="GeoTrend Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_JST = datetime.timezone(datetime.timedelta(hours=9))
_cached_events: List = []
_last_updated: Optional[str] = None
_CACHE_FILE = os.path.join(os.path.dirname(__file__), "events_cache.json")
print(f"キャッシュファイルパス: {_CACHE_FILE}")

def save_cache_to_file():
    import json
    try:
        data = {"events": [e.model_dump() for e in _cached_events], "last_updated": _last_updated}
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"キャッシュをファイルに保存: {len(_cached_events)}件")
    except Exception as e:
        print(f"キャッシュ保存エラー: {e}")

def load_cache_from_file():
    global _cached_events, _last_updated
    import json
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            _cached_events = [EventModel(**e) for e in data.get("events", [])]
            _last_updated = data.get("last_updated")
            print(f"キャッシュをファイルから読み込み: {len(_cached_events)}件 ({_last_updated})")
        else:
            print("キャッシュファイルなし（次の定時更新まで待機）")
    except Exception as e:
        print(f"キャッシュ読み込みエラー: {e}")

class EventsResponse(BaseModel):
    events: List
    last_updated: Optional[str] = None

class TweetModel(BaseModel):
    id: str
    text: str
    url: str
    created_at: str
    author_name: str = "Anonymous"
    author_username: str = "user"
    platform: str = "X"

class EventModel(BaseModel):
    id: str
    name: str
    category: str
    lat: float
    lng: float
    heatScore: int
    description: str
    keywords: List[str]
    trendingTime: str
    tweetUrl: str = ""
    tweets: List[TweetModel] = []
    platform: str = "X"

LOCAL_MAP = {
    # 基本スポット
    "広島駅": {"lat": 34.3976, "lng": 132.4754, "category": "other"},
    "原爆ドーム": {"lat": 34.3955, "lng": 132.4536, "category": "event"},
    "宮島": {"lat": 34.2952, "lng": 132.3204, "category": "event"},
    "厳島神社": {"lat": 34.2959, "lng": 132.3198, "category": "event"},
    "本通": {"lat": 34.3932, "lng": 132.4589, "category": "gourmet"},
    "マツダスタジアム": {"lat": 34.3917, "lng": 132.4846, "category": "event"},
    "グリーンアリーナ": {"lat": 34.3986, "lng": 132.4547, "category": "event"},
    "エディオンスタジアム": {"lat": 34.4398, "lng": 132.3953, "category": "event"},
    "エディオンピースウイング": {"lat": 34.4015, "lng": 132.4534, "category": "event"},
    # 広島県 23市町
    "広島市": {"lat": 34.3853, "lng": 132.4553, "category": "other"},
    "呉市": {"lat": 34.2488, "lng": 132.5654, "category": "other"},
    "竹原市": {"lat": 34.3418, "lng": 132.9080, "category": "event"},
    "三原市": {"lat": 34.4011, "lng": 133.0850, "category": "other"},
    "尾道市": {"lat": 34.4103, "lng": 133.2046, "category": "event"},
    "福山市": {"lat": 34.4859, "lng": 133.3615, "category": "other"},
    "府中市": {"lat": 34.5694, "lng": 133.2383, "category": "other"},
    "三次市": {"lat": 34.8052, "lng": 132.8533, "category": "event"},
    "庄原市": {"lat": 34.8584, "lng": 133.0163, "category": "other"},
    "大竹市": {"lat": 34.2238, "lng": 132.2212, "category": "other"},
    "東広島市": {"lat": 34.4262, "lng": 132.7441, "category": "event"},
    "廿日市市": {"lat": 34.3499, "lng": 132.3305, "category": "event"},
    "安芸高田市": {"lat": 34.6644, "lng": 132.7058, "category": "other"},
    "江田島市": {"lat": 34.2046, "lng": 132.4594, "category": "other"},
    "府中町": {"lat": 34.3968, "lng": 132.5029, "category": "other"},
    "海田町": {"lat": 34.3734, "lng": 132.5311, "category": "other"},
    "熊野町": {"lat": 34.3408, "lng": 132.5683, "category": "other"},
    "坂町": {"lat": 34.3298, "lng": 132.5050, "category": "other"},
    "安芸太田町": {"lat": 34.6063, "lng": 132.3168, "category": "other"},
    "北広島町": {"lat": 34.6723, "lng": 132.5323, "category": "other"},
    "大崎上島町": {"lat": 34.2541, "lng": 132.8988, "category": "other"},
    "世羅町": {"lat": 34.5804, "lng": 133.0489, "category": "event"},
    "神石高原町": {"lat": 34.7214, "lng": 133.2662, "category": "other"},
}

async def get_real_trends_from_x() -> List[EventModel]:
    twitter_bearer_token = (os.getenv("TWITTER_BEARER_TOKEN") or "").strip()
    if not twitter_bearer_token or "your_bearer_token_here" in twitter_bearer_token:
        print("X API Key is missing or invalid. Returning empty list.")
        return []
    
    events = []
    try:
        client = tweepy.Client(bearer_token=twitter_bearer_token)
        
        # 北海道の「北広島」、東京の「府中」などをAPIの段階で除外するマイナス検索
        exclude_keywords = "-北海道 -北広島駅 -北広島市 -千歳線 -エスコン -東京 -府中競馬場 -東京競馬場 -京王線 -山手線 -府中市美術館 -府中市美 -首都高 -大阪 -道頓堀 -難波 -なんば -ミナミ"

        # イベント系キーワード制限を外し、地名だけで広く収集（重要度はAIフィルタで判定）
        places_list = list(LOCAL_MAP.keys())
        places_str = "(" + " OR ".join(places_list) + ")"
        query = f"{places_str} {exclude_keywords} -is:retweet -is:reply"
        
        # We need expansions="author_id" and user_fields to get real user profile details.
        # But to keep it simple and within basic quota, we just take standard metrics.
        # 過去6時間前からのツイートのみを取得するように設定
        two_hours_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6)

        x_request_params = {
            "query": query,
            "tweet_fields": ["created_at", "public_metrics", "author_id"],
            "expansions": ["author_id"],
            "user_fields": ["name", "username"],
            "start_time": two_hours_ago.isoformat(),
            "max_results": 100,
        }
        print("Sending request to X API:")
        print(x_request_params)
        
        response = client.search_recent_tweets(
            query=x_request_params["query"], 
            tweet_fields=x_request_params["tweet_fields"],
            expansions=x_request_params["expansions"],
            user_fields=x_request_params["user_fields"],
            start_time=two_hours_ago,
            max_results=x_request_params["max_results"]
        )
        
        if not response.data:
            print("No event-like tweets found. Returning empty list.")
            return []

        # Build user dictionary
        users = {u.id: u for u in response.includes.get('users', [])} if response.includes else {}
        
        # --- 🚀 先端的な「推論フィルター (LLM)」をここで挟む ---
        filtered_tweets = response.data
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and len(filtered_tweets) > 0:
            print("Passing tweets through AI Inference Filter...")
            try:
                import json
                from openai import AsyncOpenAI
                ai_client = AsyncOpenAI(api_key=openai_key)
                
                # GPTへ渡すためにツイートのリストをJSON化する
                input_data = {str(i): t.text for i, t in enumerate(filtered_tweets)}
                
                prompt = f"""
以下のJSONデータのツイート本文を深く読み込み、それぞれが「テレビ局のリサーチャーにとって価値ある広島県の情報」かどうかを判定して True / False で返してください。

【必ず False にするもの】
1. 他県の同名地名：「北広島（北海道）」「府中（東京）」など広島県以外の話題
2. 他県ワードを含む：「大阪」「東京」「難波」「新宿」など県外地名が含まれるもの
3. 地名の誤検知：「呉服屋」の『呉』、「本通販」の『本通』など地名として使われていないもの
4. 単なる日常・感想：「広島に行きたい」「宮島きれい」「広島出身です」など、現地で何かが起きているわけではないもの
5. 宣伝・スパム：商品告知、アフィリエイト、無関係な広告

【True にするもの（以下のいずれかに該当）】
- イベント・お祭り・ライブ・スポーツの開催・混雑・盛り上がり情報
- 新店舗オープン・閉店・リニューアル情報
- 交通渋滞・事故・遅延など地域の異変
- 災害・気象・緊急情報
- 地域の話題になっている出来事・炎上・論争
- 観光地・グルメスポットのリアルな混雑・評判

出力はJSON書式のみ。例: {{"0": true, "1": false, "2": true}}

入力データ:
{json.dumps(input_data, ensure_ascii=False)}
"""
                ai_resp = await ai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_format={ "type": "json_object" },
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                )
                
                # AIの判定結果をパースして、本当に広島県関連のツイートだけを抽出
                result_json = json.loads(ai_resp.choices[0].message.content)
                new_filtered = []
                for i, t in enumerate(filtered_tweets):
                    if result_json.get(str(i), True):  # GPTからTrueと判定されたものだけ許可
                        new_filtered.append(t)
                
                print(f"AI Filter Result: {len(filtered_tweets)} -> {len(new_filtered)} tweets.")
                filtered_tweets = new_filtered
            except Exception as e:
                print(f"AI Filter Failed (Fallback to raw data): {e}")
        # -----------------------------------------------------

        grouped_trends = {}
        
        # さらに念の為、Python側での取りこぼしを防ぐためのNGワードリスト
        ng_words = ["北広島駅", "北広島市", "北海道", "千歳線", "エスコン", "東京都府中市", "府中競馬", "京王線", "新宿", "渋谷", "府中市美術館", "府中市美", "首都高", "長沢芦雪", "大阪", "道頓堀", "難波", "なんば", "ミナミ", "宮島南"]
        
        for tweet in filtered_tweets:
            text = tweet.text
            metrics = tweet.public_metrics
            
            # NGワードが含まれていればスキップ
            if any(ng in text for ng in ng_words):
                continue
            
            # 地名判定 (完全一致による誤判定「広島市」が「東広島市」を食うのを防ぐため、一番長い地名を採用する)
            found_places = [p_name for p_name in LOCAL_MAP.keys() if p_name in text]
            if not found_places:
                continue
            
            # 例: ["広島市", "東広島市"] が見つかった場合は、具体的な方である "東広島市" を優先する
            found_place_name = max(found_places, key=len)
                
            if found_place_name not in grouped_trends:
                grouped_trends[found_place_name] = {
                    "tweets_list": [],
                    "tweets_count": 0,
                    "total_likes": 0,
                    "total_retweets": 0,
                    "latest_time": tweet.created_at,
                    "sample_text": text,
                    "hashtags": set(),
                    "primary_tweet_id": tweet.id
                }
            
            tags = re.findall(r'#\w+', text)
            for t in tags:
                grouped_trends[found_place_name]["hashtags"].add(t)
                
            grouped_trends[found_place_name]["tweets_count"] += 1
            grouped_trends[found_place_name]["total_likes"] += metrics.get("like_count", 0)
            grouped_trends[found_place_name]["total_retweets"] += metrics.get("retweet_count", 0)
            
            if tweet.created_at > grouped_trends[found_place_name]["latest_time"]:
                grouped_trends[found_place_name]["latest_time"] = tweet.created_at
                
            # Create TweetModel
            author = users.get(tweet.author_id, None)
            grouped_trends[found_place_name]["tweets_list"].append(
                TweetModel(
                    id=str(tweet.id),
                    text=text,
                    url=f"https://x.com/i/web/status/{tweet.id}",
                    created_at=tweet.created_at.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"),
                    author_name=author.name if author else "X User",
                    author_username=author.username if author else "x_user"
                )
            )

        for p_name, data in grouped_trends.items():
            count = data["tweets_count"]
            score = 30 + (count * 20) + (data["total_retweets"] * 10) + data["total_likes"]
            heat = min(100, int(score))
            
            if heat < 35:
                continue
                
            hashtags = list(data["hashtags"])
            if count >= 3:
                title = f"{p_name} 局地的なトレンド発生中！"
            elif len(hashtags) > 0:
                title = f"{p_name}: {hashtags[0]} が話題"
            else:
                title = f"{p_name} 周辺で盛り上がり"
                
            cat = LOCAL_MAP[p_name]["category"]
            if heat > 70:
                cat = "event"
                
            desc_intro = f"合計 {count} 件の関連投稿を検知。「" if count > 1 else "「"
            desc = desc_intro + data["sample_text"][:40].replace('\n', ' ') + "...」"
            
            now = datetime.datetime.now(datetime.timezone.utc)
            diff_mins = int((now - data["latest_time"]).total_seconds() / 60)
            time_str = f"{diff_mins} mins ago" if diff_mins > 0 else "Just now"

            events.append(EventModel(
                id=p_name,
                name=title,
                category=cat,
                lat=LOCAL_MAP[p_name]["lat"],
                lng=LOCAL_MAP[p_name]["lng"],
                heatScore=heat,
                description=desc,
                keywords=hashtags[:3] if hashtags else [f"#{p_name}", "トレンド"],
                trendingTime=time_str,
                tweetUrl=f"https://x.com/i/web/status/{data['primary_tweet_id']}",
                tweets=data["tweets_list"],
                platform="X"
            ))
            
    except Exception as e:
        print(f"Tweepy execution error: {e}")
        return []
        
    if not events:
        print("No grouped events found. Returning empty list.")
        return []
        
    return events


async def get_real_trends_from_instagram() -> List[EventModel]:
    ig_user_id = os.getenv("INSTAGRAM_USER_ID")
    ig_access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    
    if not ig_user_id or not ig_access_token:
        # キーがない時は空リスト
        return []
        
    events = []
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            hashtags = ["広島グルメ", "広島イベント", "尾道カフェ"]
            all_media = []
            
            for tag in hashtags:
                res_id = await client.get(
                    "https://graph.facebook.com/v19.0/ig_hashtag_search",
                    params={"user_id": ig_user_id, "q": tag, "access_token": ig_access_token}
                )
                if res_id.status_code != 200:
                    print(f"IG Hashtag Search Error ({tag}): {res_id.text}")
                    continue
                data_id = res_id.json()
                if "data" not in data_id or not data_id["data"]:
                    continue
                    
                hashtag_id = data_id["data"][0]["id"]
                
                res_media = await client.get(
                    f"https://graph.facebook.com/v19.0/{hashtag_id}/recent_media",
                    params={
                        "user_id": ig_user_id,
                        "fields": "id,caption,media_url,permalink,timestamp,media_type",
                        "access_token": ig_access_token,
                        "limit": 50
                    }
                )
                if res_media.status_code == 200:
                    data_media = res_media.json()
                    for m in data_media.get("data", []):
                        if "caption" in m:
                            all_media.append(m)
                            
            if not all_media:
                return []

            filtered_media = all_media
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and len(filtered_media) > 0:
                print("Passing IG posts through AI Inference Filter...")
                try:
                    import json
                    from openai import AsyncOpenAI
                    ai_client = AsyncOpenAI(api_key=openai_key)
                    input_data = {str(i): m["caption"][:100] for i, m in enumerate(filtered_media)}
                    
                    prompt = f"""
以下のJSONデータのInstagramキャプションを深く読み込み、それぞれが「本当に広島県の出来事や場所（カフェ・イベント等）に関する話題」かどうかを判定し True / False で返してください。
【許可ルール】広島県内の店舗名、観光地、明確な住所があるものなどポジティブな話題は True。
【除外ルール】県外の同名地名、関連が薄いもの、日常のつぶやきで場所が特定できないものは False。
出力はJSONのkey-valueのみ。例: {{"0": true, "1": false}}
入力データ:
{json.dumps(input_data, ensure_ascii=False)}
"""
                    ai_resp = await ai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        response_format={ "type": "json_object" },
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                    )
                    result_json = json.loads(ai_resp.choices[0].message.content)
                    filtered_media = [m for i, m in enumerate(filtered_media) if result_json.get(str(i), True)]
                except Exception as e:
                    print(f"AI IG Filter Failed: {e}")

            grouped_trends = {}
            for m in filtered_media:
                caption = m["caption"]
                found_places = [p_name for p_name in LOCAL_MAP.keys() if p_name in caption]
                if not found_places:
                    continue
                found_place_name = max(found_places, key=len)
                
                if found_place_name not in grouped_trends:
                    grouped_trends[found_place_name] = {
                        "tweets_list": [],
                        "count": 0,
                        "latest_time": m.get("timestamp", datetime.datetime.now().isoformat()),
                        "sample_text": caption,
                        "primary_id": m["id"]
                    }
                    
                grouped_trends[found_place_name]["count"] += 1
                
                try:
                    dt = datetime.datetime.fromisoformat(m["timestamp"].replace('+0000', '+00:00'))
                    jst_time = dt.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
                    formatted_time = jst_time.strftime("%Y/%m/%d %H:%M")
                except:
                    formatted_time = "Unknown time from IG"
                
                grouped_trends[found_place_name]["tweets_list"].append(
                    TweetModel(
                        id=str(m["id"]),
                        text=caption[:80] + "...",
                        url=m.get("permalink", "https://instagram.com"),
                        created_at=formatted_time,
                        author_name="Instagram User",
                        author_username="instagram",
                        platform="Instagram"
                    )
                )

            for p_name, data in grouped_trends.items():
                count = data["count"]
                score = 40 + (count * 25)
                heat = min(100, int(score))
                if heat < 35:
                    continue
                    
                title = f"{p_name} 注目スポット(IG)"
                cat = "gourmet" if "カフェ" in data["sample_text"] or "ランチ" in data["sample_text"] else LOCAL_MAP[p_name]["category"]
                
                desc_intro = f"合計 {count} 件のInstagram投稿を検知。「" if count > 1 else "「"
                desc = desc_intro + data["sample_text"][:40].replace('\n', ' ') + "...」"
                
                events.append(EventModel(
                    id=f"{p_name}_ig",
                    name=title,
                    category=cat,
                    lat=LOCAL_MAP[p_name]["lat"] + 0.0015, # ちょっとXのピンからずらす
                    lng=LOCAL_MAP[p_name]["lng"] + 0.0015,
                    heatScore=heat,
                    description=desc,
                    keywords=[f"#{p_name}", "インスタ映え"],
                    trendingTime="Recent IG Post",
                    tweetUrl=data["tweets_list"][0].url if data["tweets_list"] else "https://instagram.com",
                    tweets=data["tweets_list"],
                    platform="Instagram"
                ))
                
    except Exception as e:
        print(f"Instagram Execution error: {e}")
        return []
        
    return events


def get_mock_events() -> List[EventModel]:
    now = datetime.datetime.now(datetime.timezone.utc)
    now_jst = now.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
    mock_tweets = [
        TweetModel(
            id="12341", 
            text="広島駅ビルに新しいお好み焼き屋がプレオープン！大行列です。3時間は待ちそう…。",
            url="https://x.com",
            created_at=now_jst.strftime("%Y/%m/%d %H:%M"),
            author_name="ひろしまローカル情報局",
            author_username="hiroshima_local"
        ),
        TweetModel(
            id="12342", 
            text="広島駅に行列ができてる！新しいお店かな？ #広島駅",
            url="https://x.com",
            created_at=(now_jst - datetime.timedelta(minutes=15)).strftime("%Y/%m/%d %H:%M"),
            author_name="たろう",
            author_username="taro_123"
        )
    ]
    
    return [
        EventModel(
            id="mock1", name="広島駅 局地的なトレンド発生中！", category="gourmet",
            lat=34.3976, lng=132.4754, heatScore=95,
            description="合計 2 件の関連投稿を検知。「広島駅ビルに新しいお好み焼き屋がプレオープン...」",
            keywords=["#広島駅", "#お好み焼き", "行列"], trendingTime="15 mins ago",
            tweetUrl="https://x.com",
            tweets=mock_tweets
        ),
        EventModel(
            id="mock2", name="本通 アーケード混雑", category="incident",
            lat=34.3932, lng=132.4589, heatScore=88,
            description="合計 1 件の関連投稿を検知。「本通のパレードで人がすごくて進めない...」",
            keywords=["#本通", "パレード", "激混み"], trendingTime="5 mins ago",
            tweetUrl="https://x.com",
            tweets=[
                TweetModel(
                    id="1", 
                    text="本通のパレードで人がすごくて進めない！", 
                    url="#", 
                    created_at=now_jst.strftime("%Y/%m/%d %H:%M"), 
                    author_name="もみじ", 
                    author_username="momiji_2"
                )
            ]
        ),
    ]

async def refresh_cache():
    global _cached_events, _last_updated
    import asyncio
    print("Refreshing cache...")
    x_events, ig_events = await asyncio.gather(
        get_real_trends_from_x(),
        get_real_trends_from_instagram()
    )
    _cached_events = x_events + ig_events
    _last_updated = datetime.datetime.now(_JST).strftime("%Y/%m/%d %H:%M")
    print(f"Cache refreshed: {len(_cached_events)} events at {_last_updated}")
    save_cache_to_file()

async def schedule_loop():
    update_hours = [9, 12, 15, 18, 21]
    while True:
        now = datetime.datetime.now(_JST)
        next_update = None
        for h in update_hours:
            candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if candidate > now:
                next_update = candidate
                break
        if next_update is None:
            tomorrow = now + datetime.timedelta(days=1)
            next_update = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        wait_seconds = (next_update - now).total_seconds()
        print(f"次の更新: {next_update.strftime('%Y/%m/%d %H:%M')} ({int(wait_seconds/60)}分後)")
        await asyncio.sleep(wait_seconds)
        await refresh_cache()

@app.on_event("startup")
async def startup_event():
    load_cache_from_file()
    asyncio.create_task(schedule_loop())

@app.get("/api/events", response_model=EventsResponse)
async def fetch_events():
    return EventsResponse(events=_cached_events, last_updated=_last_updated)

@app.get("/api/admin/refresh")
async def admin_refresh():
    await refresh_cache()
    return {"status": "ok", "last_updated": _last_updated, "count": len(_cached_events)}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}

# フロントエンドの静的ファイルを配信（本番環境用）
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
