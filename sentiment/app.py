import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Any
import io
import base64

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for server
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Core analyzer package
try:
    from asset_sentiment_analyzer import SentimentAnalyzer
except Exception:
    SentimentAnalyzer = None  # type: ignore
    logger.error("Could not import SentimentAnalyzer")

app = FastAPI(title="Sentiment Analyzer API", version="0.1.0")

# CORS (useful if calling from a browser UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Models -----
class SentimentRequest(BaseModel):
    asset: str = Field(
        ..., description="Target asset/security, e.g., 'Crude Oil' or 'AAPL'"
    )
    date: Optional[str] = Field(
        None,
        description="Date in MM-dd-YYYY. Defaults to today if omitted.",
        examples=["06-02-2024"],
    )
    nlinks: int = Field(
        4, ge=1, le=4, description="Number of news links to fetch (max 4)"
    )


class ReportRequest(SentimentRequest):
    max_words: int = Field(150, ge=50, le=1200, description="Max words in report")


class TrendRequest(BaseModel):
    asset: str = Field(..., description="Target asset/security")
    days: int = Field(7, ge=1, le=30, description="Number of days to analyze (1-30)")
    end_date: Optional[str] = Field(
        None, description="End date in MM-dd-YYYY. Defaults to today."
    )


# ----- Helpers -----
def _get_analyzer() -> Any:
    if SentimentAnalyzer is None:
        raise HTTPException(
            status_code=500, detail="asset-sentiment-analyzer is not installed"
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    # Optional overrides
    model = os.getenv("OPENAI_MODEL", None)

    # Some envs use OpenAI-compatible providers (e.g., DeepSeek) via base URL
    base_url = os.getenv("OPENAI_API_BASE_URL") or os.getenv("OPENAI_API_BASE")
    if base_url:
        # The asset-sentiment-analyzer package uses the openai SDK internally,
        # which checks these environment variables when creating the client.
        # We need to set BOTH for compatibility with different OpenAI SDK versions.
        os.environ["OPENAI_API_BASE"] = base_url
        os.environ["OPENAI_BASE_URL"] = base_url  # Newer OpenAI SDK versions use this

        # Monkey-patch the openai module to use the custom base_url
        # This ensures the package's internal OpenAI client uses our base URL
        import openai

        # Store original client class
        original_openai_class = openai.OpenAI

        # Create a wrapper that injects base_url
        class CustomOpenAI(original_openai_class):
            def __init__(self, *args, **kwargs):
                if "base_url" not in kwargs:
                    kwargs["base_url"] = base_url
                super().__init__(*args, **kwargs)

        # Replace the OpenAI class
        openai.OpenAI = CustomOpenAI
        logger.info(f"Configured OpenAI client to use base_url: {base_url}")

    # Initialize analyzer (the lib accepts key and model)
    try:
        analyzer = SentimentAnalyzer(asset="", openai_key=api_key, model=model)
    except TypeError:
        # Fallback if older signature
        analyzer = SentimentAnalyzer(asset="", openai_key=api_key)
    return analyzer


def _normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize date string to MM/DD/YYYY format (with slashes).
    This is the format required by the asset-sentiment-analyzer package.
    """
    if not date_str:
        return None
    # Accept datetime-like or already correct strings; enforce MM/DD/YYYY out
    try:
        # Try several common formats
        for fmt in ["%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%m/%d/%Y")  # Format with SLASHES, not dashes
            except ValueError:
                continue
        # If all failed, raise
        raise ValueError("Unsupported date format. Use MM-dd-YYYY or MM/DD/YYYY.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- Routes -----
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/sentiment")
def get_sentiment(req: SentimentRequest):
    analyzer = _get_analyzer()

    # Bind asset now that we have the analyzer
    analyzer.asset = req.asset
    date = _normalize_date(req.date)

    try:
        # Fetch news links first
        logger.info(
            f"Fetching news for asset={req.asset}, date={date}, nlinks={req.nlinks}"
        )
        try:
            links = analyzer.fetch_news_links(news_date=date, nlinks=req.nlinks)
            logger.info(f"Found {len(links)} news links")
        except (AssertionError, Exception) as fetch_error:
            logger.warning(f"Failed to fetch news links: {fetch_error}")
            links = []

        # Check if any news was found
        if not links or len(links) == 0:
            return {
                "asset": req.asset,
                "date": date if date else "today",
                "sentiment": "neutral",
                "analysis_source": "No news articles found for this date",
                "links": [],
                "news_previews": [],
                "links_analyzed": 0,
            }

        # Get sentiment (this analyzes the actual news content)
        logger.info("Getting sentiment analysis...")
        sentiment = analyzer.get_sentiment(date=date)
        logger.info(f"Sentiment result: {sentiment}")

        # Optionally fetch article previews for first few links
        news_previews = []
        for url in links[:3]:  # Preview first 3 articles
            try:
                content = analyzer.show_news_content(url)
                # Get first 200 chars as preview
                preview = content[:200] + "..." if len(content) > 200 else content
                news_previews.append({"url": url, "preview": preview})
            except Exception as preview_error:
                # Skip if article can't be fetched
                logger.warning(f"Could not fetch preview for {url}: {preview_error}")
                news_previews.append(
                    {"url": url, "preview": "[Unable to fetch article content]"}
                )

        return {
            "asset": req.asset,
            "date": date,
            "sentiment": sentiment,
            "analysis_source": "Analyzed from Google News search results and article content",
            "links": links,
            "news_previews": news_previews,
            "links_analyzed": len(links),
        }
    except Exception as e:
        logger.error(f"Error in get_sentiment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get sentiment: {str(e)}"
        )


@app.post("/v1/report")
def get_report(req: ReportRequest):
    analyzer = _get_analyzer()
    analyzer.asset = req.asset
    date = _normalize_date(req.date)

    try:
        # Fetch news links to show what's being analyzed
        links = analyzer.fetch_news_links(news_date=date, nlinks=req.nlinks)

        # Generate report (this uses GPT to analyze the news content)
        report = analyzer.produce_daily_report(date=date, max_words=req.max_words)

        # Get sentiment
        sentiment = analyzer.get_sentiment(date=date)

        return {
            "asset": req.asset,
            "date": date,
            "sentiment": sentiment,
            "report": report,
            "analysis_source": "GPT analysis of Google News articles",
            "news_sources": links,
            "sources_analyzed": len(links),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")


@app.post("/v1/trend-chart")
def get_trend_chart(req: TrendRequest):
    """
    Generate a sentiment trend chart over multiple days.
    Returns a base64-encoded PNG image.
    """
    analyzer = _get_analyzer()
    analyzer.asset = req.asset

    # Determine date range
    if req.end_date:
        end_date = _normalize_date(req.end_date)
        end_dt = datetime.strptime(end_date, "%m-%d-%Y")
    else:
        end_dt = datetime.now()
        end_date = end_dt.strftime("%m-%d-%Y")

    # Collect sentiment data for each day
    dates = []
    sentiments = []
    sentiment_scores = []  # Numeric: bullish=1, neutral=0, bearish=-1

    for i in range(req.days - 1, -1, -1):
        date_dt = end_dt - timedelta(days=i)
        date_str = date_dt.strftime("%m-%d-%Y")

        try:
            sentiment = analyzer.get_sentiment(date=date_str).lower()
            dates.append(date_dt)
            sentiments.append(sentiment)

            # Map to numeric score
            if "bullish" in sentiment:
                sentiment_scores.append(1)
            elif "bearish" in sentiment:
                sentiment_scores.append(-1)
            else:
                sentiment_scores.append(0)
        except Exception:
            # Skip days with errors
            continue

    if not dates:
        raise HTTPException(
            status_code=500, detail="No sentiment data could be collected"
        )

    # Generate chart
    plt.figure(figsize=(12, 6))
    plt.style.use("seaborn-v0_8-darkgrid")

    # Plot line chart
    plt.plot(
        dates, sentiment_scores, marker="o", linewidth=2, markersize=8, color="#3498db"
    )

    # Color the markers
    for i, (date, score) in enumerate(zip(dates, sentiment_scores)):
        color = "red" if score == -1 else "green" if score == 1 else "gray"
        plt.scatter(date, score, color=color, s=100, zorder=5)

    # Formatting
    plt.axhline(y=0, color="black", linestyle="--", linewidth=1, alpha=0.5)
    plt.fill_between(
        dates,
        0,
        sentiment_scores,
        alpha=0.2,
        color=[
            "red" if s < 0 else "green" if s > 0 else "gray" for s in sentiment_scores
        ],
    )

    plt.title(f"Sentiment Trend: {req.asset}", fontsize=16, fontweight="bold")
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("Sentiment", fontsize=12)
    plt.yticks([-1, 0, 1], ["Bearish 📉", "Neutral ➖", "Bullish 📈"])
    plt.grid(True, alpha=0.3)

    # Format x-axis dates
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=max(1, req.days // 7)))
    plt.xticks(rotation=45)

    plt.tight_layout()

    # Convert to base64 PNG
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    plt.close()

    # Encode to base64
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")

    return {
        "asset": req.asset,
        "days": len(dates),
        "date_range": {
            "start": dates[0].strftime("%m-%d-%Y"),
            "end": dates[-1].strftime("%m-%d-%Y"),
        },
        "sentiments": [
            {"date": d.strftime("%m-%d-%Y"), "sentiment": s}
            for d, s in zip(dates, sentiments)
        ],
        "chart": f"data:image/png;base64,{img_base64}",
    }
