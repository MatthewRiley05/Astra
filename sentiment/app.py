import os
import urllib.parse
import feedparser
from datetime import datetime, timedelta
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Sentiment Analyzer API")


class SentimentRequest(BaseModel):
    asset: str
    start_date: str | None = None
    end_date: str | None = None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/sentiment")
def get_sentiment(req: SentimentRequest):
    # Date defaults
    today = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    start, end = req.start_date or week_ago, req.end_date or today

    # Fetch news
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(req.asset)}+after:{start}+before:{end}"
    entries = feedparser.parse(url).entries

    if not entries:
        return {
            "asset": req.asset,
            "start_date": start,
            "end_date": end,
            "analysis": "No news found",
        }

    # Extract articles
    articles = [
        {"title": e.title, "link": e.link, "published": e.get("published", "")}
        for e in entries
    ]
    headlines = " ".join(e.title for e in entries)

    # Analyze with LLM
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(500, "DEEPSEEK_API_KEY not set")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    prompt = f"What is the overall sentiment? Provide a sentiment score between -1 to 1 and elaborate your reasons. Use the following context:\n\n{headlines}"

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "You are a financial expert analyzing market sentiment.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    return {
        "asset": req.asset,
        "start_date": start,
        "end_date": end,
        "analysis": response.choices[0].message.content,
        "articles": articles,
    }
