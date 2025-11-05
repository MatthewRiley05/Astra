import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Core analyzer package
try:
    from asset_sentiment_analyzer import SentimentAnalyzer
except Exception as e:
    SentimentAnalyzer = None  # type: ignore
    logger.error(f"Could not import SentimentAnalyzer: {e}")

app = FastAPI(title="Sentiment Analyzer API", version="0.1.0")

# CORS (useful if calling from a browser UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global analyzer instance (initialized once and reused)
_analyzer_instance: Optional[Any] = None


# ----- Models -----
class SentimentRequest(BaseModel):
    asset: str = Field(
        ..., description="Target asset/security, e.g., 'Crude Oil' or 'AAPL'"
    )
    date: Optional[str] = Field(
        None,
        description="Date in MM-dd-YYYY or relative date like 'yesterday', 'today', '3 days ago', 'last week'. Defaults to today if omitted.",
        examples=["06-02-2024", "yesterday", "3 days ago", "last week"],
    )
    nlinks: int = Field(
        4, ge=1, le=4, description="Number of news links to fetch (max 4)"
    )


class ReportRequest(SentimentRequest):
    max_words: int = Field(150, ge=50, le=1200, description="Max words in report")


# ----- Helpers -----
def _configure_openai_base_url(base_url: str) -> None:
    """Configure OpenAI client to use custom base URL."""
    os.environ["OPENAI_API_BASE"] = base_url
    os.environ["OPENAI_BASE_URL"] = base_url

    try:
        import openai

        original_openai_class = openai.OpenAI

        class CustomOpenAI(original_openai_class):
            def __init__(self, *args, **kwargs):
                if "base_url" not in kwargs:
                    kwargs["base_url"] = base_url
                super().__init__(*args, **kwargs)

        openai.OpenAI = CustomOpenAI
        logger.info(f"Configured OpenAI client with base_url: {base_url}")
    except ImportError:
        logger.warning("OpenAI module not available for configuration")


def _get_analyzer() -> Any:
    """Get or create singleton analyzer instance."""
    global _analyzer_instance

    if _analyzer_instance is not None:
        return _analyzer_instance

    if SentimentAnalyzer is None:
        raise HTTPException(
            status_code=500, detail="asset-sentiment-analyzer is not installed"
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    # Configure custom base URL if provided
    base_url = os.getenv("OPENAI_API_BASE_URL") or os.getenv("OPENAI_API_BASE")
    if base_url:
        _configure_openai_base_url(base_url)

    # Initialize analyzer once
    model = os.getenv("OPENAI_MODEL", None)
    try:
        _analyzer_instance = SentimentAnalyzer(
            asset="", openai_key=api_key, model=model
        )
    except TypeError:
        # Fallback if older signature doesn't support model parameter
        _analyzer_instance = SentimentAnalyzer(asset="", openai_key=api_key)

    logger.info("Sentiment analyzer initialized")
    return _analyzer_instance


def _parse_relative_date(date_str: str) -> Optional[datetime]:
    """
    Parse relative date expressions like 'yesterday', 'today', 'last week', etc.
    Returns a datetime object or None if not a relative date.
    """
    date_lower = date_str.lower().strip()
    today = datetime.now()

    # Handle common relative dates with dict lookup for performance
    relative_dates = {
        "today": timedelta(days=0),
        "now": timedelta(days=0),
        "yesterday": timedelta(days=1),
        "last week": timedelta(weeks=1),
        "a week ago": timedelta(weeks=1),
        "last month": timedelta(days=30),
        "a month ago": timedelta(days=30),
    }

    if date_lower in relative_dates:
        return today - relative_dates[date_lower]

    # Handle "X days/weeks ago" format
    parts = date_lower.split()
    if len(parts) >= 3 and parts[0].isdigit():
        try:
            num = int(parts[0])
            if "day" in parts[1]:
                return today - timedelta(days=num)
            elif "week" in parts[1]:
                return today - timedelta(weeks=num)
        except (ValueError, IndexError):
            pass

    return None


def _normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize date string to MM/DD/YYYY format.
    Supports absolute dates and relative expressions like 'yesterday'.
    """
    if not date_str:
        return None

    # Try relative dates first
    relative_dt = _parse_relative_date(date_str)
    if relative_dt:
        return relative_dt.strftime("%m/%d/%Y")

    # Try common date formats
    for fmt in ["%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            continue

    raise HTTPException(
        status_code=400,
        detail="Unsupported date format. Use MM-dd-YYYY, MM/DD/YYYY, or relative dates like 'yesterday', 'today', 'X days ago'.",
    )


def _get_sentiment_emoji(sentiment: str) -> str:
    """Get emoji for sentiment."""
    sentiment_lower = sentiment.lower()
    if "bullish" in sentiment_lower:
        return "📈"
    elif "bearish" in sentiment_lower:
        return "📉"
    return "➖"


def _fetch_news_previews(analyzer: Any, links: list, max_previews: int = 3) -> list:
    """Fetch article previews for given links."""
    news_previews = []
    for url in links[:max_previews]:
        try:
            content = analyzer.show_news_content(url)
            preview = content[:200] + "..." if len(content) > 200 else content
            news_previews.append({"url": url, "preview": preview})
        except Exception as e:
            logger.warning(f"Could not fetch preview for {url}: {e}")
            news_previews.append(
                {"url": url, "preview": "[Unable to fetch article content]"}
            )
    return news_previews


def _create_no_news_summary(asset: str, date: Optional[str]) -> str:
    """Create summary for when no news is found."""
    date_display = date if date else "today"
    return f"""[INSTRUCTION FOR AI ASSISTANT: Present this no-news scenario in a clear, formatted way using a markdown table.]

Present the following sentiment analysis results in a professional table format:

| **Metric** | **Value** |
|------------|-----------|
| **Asset** | {asset} |
| **Date Analyzed** | {date_display} |
| **Sentiment** | NEUTRAL ➖ |
| **Articles Analyzed** | 0 |
| **Status** | ⚠️ No News Available |

### Analysis Note
No recent news articles were found for {asset} on {date_display}. This could be due to:
- Limited news coverage for this asset
- The date selected may not have significant news activity
- The asset name may need verification

**Suggestion**: Try checking a different date or verify the asset name."""


def _create_sentiment_summary(
    asset: str, date: Optional[str], sentiment: str, links: list, news_previews: list
) -> str:
    """Create formatted sentiment summary for AI presentation."""
    date_display = date if date else "today"
    sentiment_emoji = _get_sentiment_emoji(sentiment)

    summary = f"""[INSTRUCTION FOR AI ASSISTANT: Present this sentiment analysis data in a clean, well-formatted table. Use markdown table format with clear headers and rows. Make it visually appealing and easy to read. Make sure all URLs in the news sources are formatted as clickable hyperlinks using markdown link syntax [text](url).]

Present the following sentiment analysis results in a professional table format:

| **Metric** | **Value** |
|------------|-----------|
| **Asset** | {asset} |
| **Date Analyzed** | {date_display} |
| **Sentiment** | {sentiment.upper()} {sentiment_emoji} |
| **Articles Analyzed** | {len(links)} |
| **Data Source** | Google News |

### Market Sentiment Analysis
The current market sentiment for **{asset}** is **{sentiment.upper()} {sentiment_emoji}** based on analysis of {len(links)} recent news articles."""

    if news_previews:
        summary += "\n\n### News Sources Analyzed"
        for i, preview in enumerate(news_previews[:3], 1):
            domain = urlparse(preview["url"]).netloc
            preview_text = preview["preview"].split("\n")[0][:150]
            summary += f"\n{i}. [{domain}]({preview['url']}): {preview_text}..."

    return summary


# ----- Routes -----
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/sentiment")
def get_sentiment(req: SentimentRequest):
    """Get sentiment analysis for an asset."""
    analyzer = _get_analyzer()
    analyzer.asset = req.asset
    date = _normalize_date(req.date)

    try:
        # Fetch news links
        logger.info(
            f"Fetching news for asset={req.asset}, date={date}, nlinks={req.nlinks}"
        )
        try:
            links = analyzer.fetch_news_links(news_date=date, nlinks=req.nlinks)
            logger.info(f"Found {len(links)} news links")
        except (AssertionError, Exception) as fetch_error:
            logger.warning(f"Failed to fetch news links: {fetch_error}")
            links = []

        # Handle no news case
        if not links:
            return {
                "asset": req.asset,
                "date": date if date else "today",
                "sentiment": "neutral",
                "summary": _create_no_news_summary(req.asset, date),
                "analysis_source": "No news articles found for this date",
                "links": [],
                "news_previews": [],
                "links_analyzed": 0,
            }

        # Get sentiment analysis
        logger.info("Getting sentiment analysis...")
        sentiment = analyzer.get_sentiment(date=date)
        logger.info(f"Sentiment result: {sentiment}")

        # Fetch article previews
        news_previews = _fetch_news_previews(analyzer, links)

        # Create summary
        summary = _create_sentiment_summary(
            req.asset, date, sentiment, links, news_previews
        )

        return {
            "asset": req.asset,
            "date": date,
            "sentiment": sentiment,
            "summary": summary,
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
    """Generate comprehensive report for an asset."""
    analyzer = _get_analyzer()
    analyzer.asset = req.asset
    date = _normalize_date(req.date)

    try:
        # Fetch news links
        logger.info(f"Generating report for asset={req.asset}, date={date}")
        links = analyzer.fetch_news_links(news_date=date, nlinks=req.nlinks)

        # Generate report using GPT analysis
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
        logger.error(f"Error in get_report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate report: {str(e)}"
        )
