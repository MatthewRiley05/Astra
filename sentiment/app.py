import os
import urllib.parse
import feedparser
from datetime import datetime, timedelta
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Sentiment Analyzer API")

DATE_FORMAT = "%Y-%m-%d"


class SentimentRequest(BaseModel):
    asset: str = Field(..., description="Target asset/security")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/sentiment")
def get_sentiment(req: SentimentRequest):
    # Set date defaults
    today = (datetime.now() + timedelta(days=1)).strftime(DATE_FORMAT)
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime(DATE_FORMAT)
    start_date = req.start_date or seven_days_ago
    end_date = req.end_date or today

    # Fetch news from Google RSS
    feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(req.asset)}+after:{start_date}+before:{end_date}"
    feed = feedparser.parse(feed_url)
    entries = feed.entries

    if not entries:
        return {
            "asset": req.asset,
            "start_date": start_date,
            "end_date": end_date,
            "analysis": "No news articles found",
        }

    # Collect headlines
    all_headlines = ""
    data = []
    for entry in entries:
        title = entry.title
        all_headlines += title + " "
        data.append(
            {
                "title": title,
                "link": entry.link,
                "published": entry.get("published", ""),
            }
        )

    # Analyze sentiment with DeepSeek
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY not set")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    question = "What is the overall sentiment? Provide a sentiment score between -1 to 1 and elaborate your reasons"
    question_with_context = (
        question + "  Use the following context: \n\n" + all_headlines
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful financial expert, you do not answer questions unrelated to finance.",
            },
            {"role": "user", "content": question_with_context},
        ],
        stream=False,
    )

    analysis = response.choices[0].message.content

    return {
        "asset": req.asset,
        "start_date": start_date,
        "end_date": end_date,
        "analysis": analysis,
        "articles": data,
    }
