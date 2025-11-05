"""
title: Asset Sentiment Analyzer
author: open-webui
author_url: https://github.com/open-webui
funding_url: https://github.com/open-webui
version: 0.1.0
license: MIT
"""

import requests
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Tools:
    """
    Open WebUI tool that calls the sentiment-analyzer microservice.
    Users can invoke via chat: /sentiment or let the LLM call automatically.
    """

    class Valves(BaseModel):
        SENTIMENT_API_BASE_URL: str = Field(
            default="http://sentiment-analyzer:5501",
            description="Base URL for the sentiment analyzer service (use Docker service name or localhost:5501 for external)",
        )

    def __init__(self):
        self.valves = self.Valves()

    def get_asset_sentiment(
        self,
        asset: str,
        date: Optional[str] = None,
        nlinks: int = 4,
    ) -> str:
        """
        Get daily news sentiment analysis for a financial asset.

        :param asset: The asset or security to analyze (e.g., "Crude Oil", "AAPL", "Gold")
        :param date: Optional date in MM-DD-YYYY format. Defaults to today if not provided.
        :param nlinks: Number of news links to analyze (1-20). Default is 4.
        :return: Sentiment verdict (bullish/bearish/neutral) with news links
        """

        # Normalize date
        if date:
            # Validate/normalize date format
            try:
                dt = datetime.strptime(date, "%m-%d-%Y")
                date_str = dt.strftime("%m-%d-%Y")
            except ValueError:
                return "❌ Invalid date format. Use MM-DD-YYYY (e.g., 11-05-2025)"
        else:
            date_str = datetime.now().strftime("%m-%d-%Y")

        # Call the sentiment API
        url = f"{self.valves.SENTIMENT_API_BASE_URL}/v1/sentiment"
        payload = {
            "asset": asset,
            "date": date_str,
            "nlinks": min(max(nlinks, 1), 20),  # Clamp between 1-20
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            # Format response
            sentiment = data.get("sentiment", "unknown").upper()
            links = data.get("links", [])

            # Build emoji indicator
            emoji = {
                "BULLISH": "📈",
                "BEARISH": "📉",
                "NEUTRAL": "➖",
            }.get(sentiment, "❓")

            result = (
                f"{emoji} **{sentiment}** sentiment for **{asset}** on {date_str}\n\n"
            )

            if links:
                result += "**News Sources:**\n"
                for i, link in enumerate(links[:10], 1):  # Limit display to 10
                    result += f"{i}. {link}\n"
            else:
                result += "_No news links found._\n"

            return result

        except requests.exceptions.RequestException as e:
            return f"❌ Error calling sentiment API: {str(e)}\n\nMake sure the sentiment-analyzer service is running."
        except Exception as e:
            return f"❌ Unexpected error: {str(e)}"

    def generate_sentiment_report(
        self,
        asset: str,
        date: Optional[str] = None,
        max_words: int = 200,
    ) -> str:
        """
        Generate a detailed GPT-powered sentiment report for a financial asset.

        :param asset: The asset or security to analyze (e.g., "Crude Oil", "AAPL", "Gold")
        :param date: Optional date in MM-DD-YYYY format. Defaults to today if not provided.
        :param max_words: Maximum words in the report (50-1000). Default is 200.
        :return: Detailed sentiment analysis report
        """

        # Normalize date
        if date:
            try:
                dt = datetime.strptime(date, "%m-%d-%Y")
                date_str = dt.strftime("%m-%d-%Y")
            except ValueError:
                return "❌ Invalid date format. Use MM-DD-YYYY (e.g., 11-05-2025)"
        else:
            date_str = datetime.now().strftime("%m-%d-%Y")

        # Call the report API
        url = f"{self.valves.SENTIMENT_API_BASE_URL}/v1/report"
        payload = {
            "asset": asset,
            "date": date_str,
            "max_words": min(max(max_words, 50), 1000),  # Clamp between 50-1000
        }

        try:
            response = requests.post(
                url, json=payload, timeout=120
            )  # Reports take longer
            response.raise_for_status()
            data = response.json()

            sentiment = data.get("sentiment", "unknown").upper()
            report = data.get("report", "No report generated.")

            # Build emoji indicator
            emoji = {
                "BULLISH": "📈",
                "BEARISH": "📉",
                "NEUTRAL": "➖",
            }.get(sentiment, "❓")

            result = f"# {emoji} Sentiment Report: {asset}\n"
            result += f"**Date:** {date_str}  \n"
            result += f"**Sentiment:** {sentiment}\n\n"
            result += "---\n\n"
            result += report

            return result

        except requests.exceptions.RequestException as e:
            return f"❌ Error calling sentiment API: {str(e)}\n\nMake sure the sentiment-analyzer service is running."
        except Exception as e:
            return f"❌ Unexpected error: {str(e)}"
