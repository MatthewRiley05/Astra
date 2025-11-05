import os
from datetime import datetime
from typing import Optional, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Core analyzer package
try:
    from asset_sentiment_analyzer import SentimentAnalyzer
except Exception:
    SentimentAnalyzer = None  # type: ignore

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
    nlinks: int = Field(4, ge=1, le=20, description="Number of news links to fetch")


class ReportRequest(SentimentRequest):
    max_words: int = Field(150, ge=50, le=1200, description="Max words in report")


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
        # Many libraries pick this up from env. The upstream package uses openai python SDK,
        # which respects OPENAI_API_BASE in recent versions; set both names for safety.
        os.environ["OPENAI_API_BASE"] = base_url

    # Initialize analyzer (the lib accepts key and model)
    try:
        analyzer = SentimentAnalyzer(asset="", openai_key=api_key, model=model)
    except TypeError:
        # Fallback if older signature
        analyzer = SentimentAnalyzer(asset="", openai_key=api_key)
    return analyzer


def _normalize_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    # Accept datetime-like or already correct strings; enforce MM-dd-YYYY out
    try:
        # Try several common formats
        for fmt in ["%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%m-%d-%Y")
            except ValueError:
                continue
        # If all failed, raise
        raise ValueError("Unsupported date format. Use MM-dd-YYYY.")
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
        sentiment = analyzer.get_sentiment(date=date)
        links = analyzer.fetch_news_links(news_date=date, nlinks=req.nlinks)
        return {
            "asset": req.asset,
            "date": date,
            "sentiment": sentiment,
            "links": links,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sentiment: {e}")


@app.post("/v1/report")
def get_report(req: ReportRequest):
    analyzer = _get_analyzer()
    analyzer.asset = req.asset
    date = _normalize_date(req.date)

    try:
        report = analyzer.produce_daily_report(date=date, max_words=req.max_words)
        sentiment = analyzer.get_sentiment(date=date)
        return {
            "asset": req.asset,
            "date": date,
            "sentiment": sentiment,
            "report": report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")
