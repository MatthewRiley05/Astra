from flask import Flask, request, jsonify, send_from_directory
import numpy as np
import pandas as pd
import PortfolioBuilder as pb
from pyportfolio import PortfolioOptimizer, get_company_tickers_json_path
import matplotlib

matplotlib.use("Agg")  # Use non-GUI backend
import matplotlib.pyplot as plt
from pathlib import Path
import time

app = Flask(__name__)

# Create charts directory for storing generated plots
CHARTS_DIR = Path("/app/charts")
CHARTS_DIR.mkdir(exist_ok=True)


# Serve chart images
@app.route("/charts/<filename>")
def serve_chart(filename):
    """Serve generated chart images"""
    return send_from_directory(CHARTS_DIR, filename)


def _validate_and_clean_prices(price_df, requested_tickers):
    """
    Return (clean_df, removed_list) or raise ValueError with message.
    """
    if price_df is None:
        raise ValueError("price data is None")
    if not hasattr(price_df, "empty") or price_df.empty:
        raise ValueError("price data is empty")

    # Drop columns with all NaNs
    clean = price_df.dropna(axis=1, how="all")
    removed = [t for t in requested_tickers if t not in list(clean.columns)]

    # Require at least 2 rows of history
    if clean.shape[0] < 2:
        raise ValueError(
            f"insufficient history rows: {clean.shape[0]} after removing {removed}"
        )

    # Drop tickers with too few observations (e.g., <25% of rows or <2 observations)
    min_obs = max(2, int(len(clean) * 0.25))
    low_obs = [c for c in clean.columns if clean[c].count() < min_obs]
    if low_obs:
        clean = clean.drop(columns=low_obs)
        removed += low_obs

    # Drop constant / zero-variance series
    const_cols = [c for c in clean.columns if clean[c].nunique(dropna=True) <= 1]
    if const_cols:
        clean = clean.drop(columns=const_cols)
        removed += const_cols

    if clean.empty or clean.shape[1] < 1:
        raise ValueError(
            f"no valid tickers left after cleaning; removed={sorted(set(removed))}"
        )

    return clean, sorted(set(removed))


# Health check endpoint
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "market_data"}), 200


# OpenAPI specification endpoint
@app.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """OpenAPI specification for the market data API - Enhanced for LLM tool use"""
    import json

    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Market Data & Portfolio API",
            "version": "1.0.0",
            "description": "Comprehensive API for stock market data retrieval, screening, and portfolio optimization using Modern Portfolio Theory",
        },
        "servers": [{"url": "http://market-data:5003"}],
        "paths": {
            "/api/screen/predefined": {
                "post": {
                    "operationId": "screen_stocks_by_criteria",
                    "summary": "Screen stocks using predefined investment strategies",
                    "description": "Returns a list of stock tickers matching predefined screening criteria. IMPORTANT: Use the EXACT ticker symbols returned in the 'tickers' array for subsequent API calls - do not modify or substitute them.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "Predefined screening query name (use /api/screen/available to get list)",
                                            "example": "aggressive_small_caps",
                                        },
                                        "count": {
                                            "type": "number",
                                            "default": 10,
                                            "description": "Maximum number of stocks to return",
                                            "example": 10,
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successfully screened stocks",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tickers": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "description": "Array of stock ticker symbols. USE THESE EXACT TICKERS for portfolio optimization.",
                                            },
                                            "count": {"type": "number"},
                                            "query": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/screen/available": {
                "get": {
                    "operationId": "get_available_stock_screens",
                    "summary": "Get list of available stock screening criteria",
                    "description": "Returns all available predefined screening query names that can be used with /api/screen/predefined.",
                    "responses": {
                        "200": {
                            "description": "List of available screening queries",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "queries": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            }
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/market/closing-prices": {
                "post": {
                    "operationId": "get_stock_closing_prices",
                    "summary": "Retrieve historical closing prices for stocks",
                    "description": "Fetches closing price history for one or more stock tickers. Use this to analyze price trends, calculate returns, or prepare data for portfolio analysis.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["tickers"],
                                    "properties": {
                                        "tickers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])",
                                            "example": ["AAPL", "MSFT"],
                                        },
                                        "period": {
                                            "type": "string",
                                            "default": "1y",
                                            "description": "Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
                                            "example": "1y",
                                        },
                                        "interval": {
                                            "type": "string",
                                            "default": "1d",
                                            "description": "Data interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo",
                                            "example": "1d",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successfully retrieved closing prices",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "dates": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                            "data": {"type": "object"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/market/ticker-info": {
                "post": {
                    "operationId": "get_stock_detailed_info",
                    "summary": "Get comprehensive market data and company information",
                    "description": "Retrieves detailed information for a stock including OHLCV data, company metadata, financials, and key statistics. Use this for fundamental analysis.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["ticker"],
                                    "properties": {
                                        "ticker": {
                                            "type": "string",
                                            "description": "Stock ticker symbol (e.g., 'AAPL')",
                                            "example": "AAPL",
                                        },
                                        "period": {
                                            "type": "string",
                                            "default": "1mo",
                                            "description": "Historical data period",
                                            "example": "1mo",
                                        },
                                        "interval": {
                                            "type": "string",
                                            "default": "1d",
                                            "description": "Data interval",
                                            "example": "1d",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successfully retrieved ticker information"
                        }
                    },
                }
            },
            "/api/portfolio/optimize": {
                "post": {
                    "operationId": "optimize_portfolio_allocation",
                    "summary": "Optimize portfolio weights using Modern Portfolio Theory",
                    "description": "Calculates optimal asset allocation for a portfolio using various optimization methods (max Sharpe ratio, min volatility, etc.). IMPORTANT: This endpoint validates all tickers and may remove delisted/invalid ones. Always check 'used_tickers' and 'removed_tickers' in the response to see which stocks were actually used in optimization.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["tickers", "period", "holding_period"],
                                    "properties": {
                                        "tickers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of stock tickers to include in portfolio. Use EXACT ticker symbols from screening/filtering endpoints. Invalid tickers will be automatically removed.",
                                            "example": [
                                                "AAPL",
                                                "MSFT",
                                                "GOOGL",
                                                "AMZN",
                                            ],
                                        },
                                        "period": {
                                            "type": "string",
                                            "description": "REQUIRED: Historical data period for analysis. ASK USER: 'How far back should I analyze historical data?' Valid values: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max. Recommended: 1y or longer for reliable optimization.",
                                            "enum": [
                                                "1d",
                                                "5d",
                                                "1mo",
                                                "3mo",
                                                "6mo",
                                                "1y",
                                                "2y",
                                                "5y",
                                                "10y",
                                                "ytd",
                                                "max",
                                            ],
                                            "example": "1y",
                                        },
                                        "holding_period": {
                                            "type": "string",
                                            "description": "REQUIRED: Investment time horizon for risk-free rate calculation. ASK USER: 'What is your investment time horizon?' Valid values: '1 Mo', '3 Mo', '6 Mo', '1 Yr', '2 Yr', '3 Yr', '5 Yr', '7 Yr', '10 Yr', '30 Yr' (NOTE: Use space and title case, e.g. '1 Yr' not '1y'). This fetches the appropriate Treasury rate from live market data.",
                                            "enum": [
                                                "1 Mo",
                                                "3 Mo",
                                                "6 Mo",
                                                "1 Yr",
                                                "2 Yr",
                                                "3 Yr",
                                                "5 Yr",
                                                "7 Yr",
                                                "10 Yr",
                                                "30 Yr",
                                            ],
                                            "example": "1 Yr",
                                        },
                                        "method": {
                                            "type": "string",
                                            "description": "Optimization method. ASK USER if not obvious: 'What optimization strategy would you like?' max_sharpe (maximize risk-adjusted returns - RECOMMENDED), min_volatility (minimize risk), or others.",
                                            "enum": [
                                                "max_sharpe",
                                                "min_volatility",
                                                "max_quadratic_utility",
                                                "efficient_risk",
                                                "efficient_return",
                                            ],
                                            "default": "max_sharpe",
                                            "example": "max_sharpe",
                                        },
                                        "returns_type": {
                                            "type": "string",
                                            "enum": ["mean", "capm", "ema"],
                                            "description": "Expected returns calculation method. Default 'mean' is recommended for most users.",
                                            "default": "mean",
                                            "example": "mean",
                                        },
                                        "cov_type": {
                                            "type": "string",
                                            "enum": [
                                                "ledoit_wolf",
                                                "semicovariance",
                                                "exp_cov",
                                            ],
                                            "description": "Covariance matrix estimation method. Default 'ledoit_wolf' is recommended for most users.",
                                            "default": "ledoit_wolf",
                                            "example": "ledoit_wolf",
                                        },
                                        "portfolio_value": {
                                            "type": "number",
                                            "description": "Total portfolio value in dollars for share allocation calculation. ASK USER: 'How much money would you like to invest?' (e.g., 10000 for $10,000). If not provided, will return percentage weights only.",
                                            "example": 10000,
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successfully optimized portfolio",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "performance": {
                                                "type": "object",
                                                "properties": {
                                                    "expected_return": {
                                                        "type": "number",
                                                        "description": "Expected annual return",
                                                    },
                                                    "volatility": {
                                                        "type": "number",
                                                        "description": "Expected annual volatility (risk)",
                                                    },
                                                    "sharpe_ratio": {
                                                        "type": "number",
                                                        "description": "Risk-adjusted return metric",
                                                    },
                                                },
                                            },
                                            "weights": {
                                                "type": "object",
                                                "description": "Optimal portfolio weights for each ticker (only includes used tickers)",
                                            },
                                            "risk_free_rate": {"type": "number"},
                                            "allocation": {
                                                "type": "object",
                                                "description": "Share allocation if portfolio_value was provided",
                                            },
                                            "requested_tickers": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "description": "Original tickers requested",
                                            },
                                            "used_tickers": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "description": "Tickers actually used in optimization (after validation)",
                                            },
                                            "removed_tickers": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "description": "Tickers removed due to invalid/delisted data",
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/portfolio/plot-returns": {
                "post": {
                    "operationId": "plot_portfolio_vs_benchmark",
                    "summary": "Generate portfolio performance chart vs S&P 500",
                    "description": "Creates a visualization comparing portfolio cumulative returns against S&P 500 benchmark. Returns markdown image URL and performance metrics including drawdown, volatility, and Sharpe ratio for both portfolio and benchmark.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": [
                                        "tickers",
                                        "weights",
                                        "period",
                                        "holding_period",
                                    ],
                                    "properties": {
                                        "tickers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of stock tickers in the portfolio",
                                            "example": ["AAPL", "MSFT", "GOOGL"],
                                        },
                                        "weights": {
                                            "type": "object",
                                            "description": "Portfolio weights for each ticker (must sum to 1.0). Use the weights from the optimization result.",
                                            "example": {
                                                "AAPL": 0.4,
                                                "MSFT": 0.3,
                                                "GOOGL": 0.3,
                                            },
                                        },
                                        "period": {
                                            "type": "string",
                                            "description": "REQUIRED: Time period for comparison chart. Should match the period used in optimization. Valid: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
                                            "enum": [
                                                "1d",
                                                "5d",
                                                "1mo",
                                                "3mo",
                                                "6mo",
                                                "1y",
                                                "2y",
                                                "5y",
                                                "10y",
                                                "ytd",
                                                "max",
                                            ],
                                            "example": "1y",
                                        },
                                        "holding_period": {
                                            "type": "string",
                                            "enum": [
                                                "1 Mo",
                                                "3 Mo",
                                                "6 Mo",
                                                "1 Yr",
                                                "2 Yr",
                                                "3 Yr",
                                                "5 Yr",
                                                "7 Yr",
                                                "10 Yr",
                                                "30 Yr",
                                            ],
                                            "description": "REQUIRED: Investment time horizon for risk-free rate. Should match the holding_period used in optimization. Format: '1 Yr' with space and title case.",
                                            "example": "1 Yr",
                                        },
                                        "index_symbol": {
                                            "type": "string",
                                            "default": "^GSPC",
                                            "description": "Benchmark index symbol (default: S&P 500)",
                                            "example": "^GSPC",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successfully generated chart",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "image": {
                                                "type": "string",
                                                "description": "Markdown image syntax with chart URL",
                                            },
                                            "metrics": {
                                                "type": "object",
                                                "description": "Performance metrics for portfolio and benchmark",
                                            },
                                            "removed_tickers": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "description": "Tickers removed due to invalid/delisted data",
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/portfolio/efficient-frontier": {
                "post": {
                    "operationId": "generate_efficient_frontier",
                    "summary": "Generate efficient frontier simulation data",
                    "description": "Simulates thousands of random portfolio combinations to map the efficient frontier showing risk-return tradeoffs. Returns data points for plotting and optimal portfolio details.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["tickers", "period", "holding_period"],
                                    "properties": {
                                        "tickers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of stock tickers for frontier analysis",
                                            "example": [
                                                "AAPL",
                                                "MSFT",
                                                "GOOGL",
                                                "AMZN",
                                            ],
                                        },
                                        "period": {
                                            "type": "string",
                                            "description": "REQUIRED: Historical data period. ASK USER if not specified. Valid: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
                                            "enum": [
                                                "1d",
                                                "5d",
                                                "1mo",
                                                "3mo",
                                                "6mo",
                                                "1y",
                                                "2y",
                                                "5y",
                                                "10y",
                                                "ytd",
                                                "max",
                                            ],
                                            "example": "1y",
                                        },
                                        "holding_period": {
                                            "type": "string",
                                            "enum": [
                                                "1 Mo",
                                                "3 Mo",
                                                "6 Mo",
                                                "1 Yr",
                                                "2 Yr",
                                                "3 Yr",
                                                "5 Yr",
                                                "7 Yr",
                                                "10 Yr",
                                                "30 Yr",
                                            ],
                                            "description": "REQUIRED: Investment time horizon for risk-free rate calculation. ASK USER if not specified. Format: '1 Yr' with space and title case.",
                                            "example": "1 Yr",
                                        },
                                        "num_portfolios": {
                                            "type": "number",
                                            "default": 5000,
                                            "description": "Number of random portfolio combinations to generate",
                                            "example": 5000,
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successfully generated efficient frontier",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "frontier_points": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "return": {"type": "number"},
                                                        "volatility": {
                                                            "type": "number"
                                                        },
                                                        "sharpe": {"type": "number"},
                                                    },
                                                },
                                            },
                                            "optimal_portfolio": {
                                                "type": "object",
                                                "properties": {
                                                    "expected_return": {
                                                        "type": "number"
                                                    },
                                                    "volatility": {"type": "number"},
                                                    "sharpe_ratio": {"type": "number"},
                                                    "weights": {"type": "object"},
                                                },
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/stocks/by-sic": {
                "post": {
                    "operationId": "filter_stocks_by_industry",
                    "summary": "Filter stocks by SIC industry codes",
                    "description": "Returns list of stocks matching specified Standard Industrial Classification (SIC) codes. IMPORTANT: Use the EXACT ticker symbols returned in the 'tickers' array for subsequent API calls - do not modify or substitute them.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["sic_codes"],
                                    "properties": {
                                        "sic_codes": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of 4-digit SIC codes (e.g., ['3674' for semiconductors, '6282' for investment advice])",
                                            "example": ["3674", "7372"],
                                        }
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "List of stocks matching SIC codes",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tickers": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "description": "Array of stock ticker symbols. USE THESE EXACT TICKERS for portfolio optimization.",
                                            },
                                            "count": {"type": "number"},
                                            "sic_codes": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                            "message": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/stocks/sic-list": {
                "get": {
                    "operationId": "get_available_sic_codes",
                    "summary": "Get all available SIC industry codes and descriptions",
                    "description": "Returns complete list of SIC codes with descriptions. Use this to discover industry codes before filtering stocks.",
                    "responses": {
                        "200": {"description": "List of SIC codes with descriptions"}
                    },
                }
            },
        },
    }

    # Use json.dumps to ensure proper JSON boolean serialization (true/false not True/False)
    return json.dumps(spec), 200, {"Content-Type": "application/json"}


# Stock screening endpoints
@app.route("/api/screen/predefined", methods=["POST"])
def screen_predefined():
    """
    Screen stocks using predefined yfinance queries.
    Request body:
    {
        "query": "aggressive_small_caps",
        "count": 10
    }
    """
    try:
        data = request.get_json()
        query = data.get("query")
        count = data.get("count", 10)

        if not query:
            return jsonify({"error": "query parameter is required"}), 400

        stocks = pb.get_list_of_screened_stocks(query, count=count)
        return jsonify(
            {
                "tickers": stocks,
                "count": len(stocks),
                "query": query,
                "message": f"Found {len(stocks)} stocks matching '{query}' criteria. Use these exact ticker symbols for portfolio optimization.",
            }
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/screen/available", methods=["GET"])
def available_queries():
    """Get list of available predefined screener queries"""
    try:
        screener = pb.yf_screener()
        queries = screener.available_predefined()
        return jsonify({"queries": queries}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Market data endpoints
@app.route("/api/market/closing-prices", methods=["POST"])
def get_closing_prices():
    """
    Get closing prices for a list of tickers.
    Request body:
    {
        "tickers": ["AAPL", "GOOGL", "MSFT"],
        "period": "1y",
        "interval": "1d"
    }
    """
    try:
        data = request.get_json()
        tickers = data.get("tickers", [])
        period = data.get("period", "1y")
        interval = data.get("interval", "1d")
        start = data.get("start")
        end = data.get("end")

        if not tickers:
            return jsonify({"error": "tickers list is required"}), 400

        prices = pb.get_closingPrice_list(
            ticker_list=tickers, start=start, end=end, period=period, interval=interval
        )

        # Convert DataFrame to JSON-serializable format
        result = {
            "dates": prices.index.strftime("%Y-%m-%d").tolist(),
            "data": prices.to_dict(orient="list"),
        }

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/market/ticker-info", methods=["POST"])
def get_ticker_info():
    """
    Get detailed market data and info for a single ticker.
    Request body:
    {
        "ticker": "AAPL",
        "period": "1mo",
        "interval": "1d"
    }
    """
    try:
        data = request.get_json()
        ticker = data.get("ticker")
        period = data.get("period", "1mo")
        interval = data.get("interval", "1d")
        start = data.get("start")
        end = data.get("end")

        if not ticker:
            return jsonify({"error": "ticker is required"}), 400

        market_data, info = pb.get_market_data(
            ticker=ticker, start=start, end=end, period=period, interval=interval
        )

        # Convert DataFrame to JSON-serializable format
        result = {
            "historical_data": {
                "dates": market_data.index.strftime("%Y-%m-%d").tolist(),
                "data": market_data.to_dict(orient="list"),
            },
            "info": info,
        }

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# SIC filtering endpoints
@app.route("/api/stocks/by-sic", methods=["POST"])
def filter_by_sic():
    """
    Filter stocks by SIC codes.
    Request body:
    {
        "sic_codes": ["3674", "3571"]
    }
    """
    try:
        data = request.get_json()
        sic_codes = data.get("sic_codes", [])

        if not sic_codes:
            return jsonify({"error": "sic_codes list is required"}), 400

        # Get the path to company tickers JSON
        path = get_company_tickers_json_path()

        stocks = pb.filter_stocks_by_sic(sic_codes=sic_codes, path=path)
        return jsonify(
            {
                "tickers": stocks,
                "count": len(stocks),
                "sic_codes": sic_codes,
                "message": f"Found {len(stocks)} stocks in SIC codes {sic_codes}. Use these exact ticker symbols for portfolio optimization.",
            }
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stocks/sic-list", methods=["GET"])
def get_sic_list():
    """Get list of unique SIC codes and descriptions"""
    try:
        path = get_company_tickers_json_path()
        sic_df = pb.access_edgar_sic(path=path)

        result = sic_df.to_dict(orient="records")
        return jsonify({"sic_codes": result, "count": len(result)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Portfolio optimization endpoints
@app.route("/api/portfolio/optimize", methods=["POST"])
def optimize_portfolio():
    """
    Optimize portfolio using various methods.
    Request body:
    {
        "tickers": ["AAPL", "GOOGL", "MSFT"],
        "period": "1y",
        "holding_period": "1 Yr",
        "method": "max_sharpe",
        "returns_type": "mean",
        "cov_type": "ledoit_wolf",
        "portfolio_value": 10000
    }
    """
    try:
        data = request.get_json()
        tickers = data.get("tickers")
        period = data.get("period")
        holding_period = data.get("holding_period")
        method = data.get("method", "max_sharpe")
        returns_type = data.get("returns_type", "mean")
        cov_type = data.get("cov_type", "ledoit_wolf")
        portfolio_value = data.get("portfolio_value")

        if not tickers:
            return jsonify({"error": "tickers list is required"}), 400
        if not period:
            return jsonify(
                {
                    "error": "period is required. Ask user: 'How far back should I analyze historical data? (e.g., 1y, 2y, 5y)'"
                }
            ), 400
        if not holding_period:
            return jsonify(
                {
                    "error": "holding_period is required. Ask user: 'What is your investment time horizon? (e.g., 1 Yr, 5 Yr, 10 Yr)'"
                }
            ), 400

        # Fetch price data
        price_data = pb.get_closingPrice_list(
            ticker_list=tickers, period=period, interval="1d"
        )

        # Validate/clean price data
        try:
            clean_price_data, removed = _validate_and_clean_prices(price_data, tickers)
        except Exception as e:
            return jsonify({"error": "Invalid price data", "details": str(e)}), 400

        # Create optimizer
        optimizer = PortfolioOptimizer(clean_price_data, holding_period=holding_period)

        # Get expected returns and covariance matrix
        mu = optimizer.get_expected_returns(type=returns_type)
        S = optimizer.get_covariance_matrix(type=cov_type)

        # Validate mu and S
        if mu is None or S is None:
            return (
                jsonify(
                    {
                        "error": "Failed to compute returns/covariance",
                        "removed_tickers": removed,
                    }
                ),
                500,
            )
        if getattr(mu, "isnull", lambda: False)().any() or (
            hasattr(S, "isnull") and S.isnull().values.any()
        ):
            return (
                jsonify(
                    {
                        "error": "Computed returns or covariance contain NaNs",
                        "removed_tickers": removed,
                    }
                ),
                500,
            )

        # Get optimal weights and performance
        performance, weights, clean_weights = optimizer.get_performance(
            mu, S, round=True, method=method
        )

        result = {
            "performance": {
                "expected_return": float(performance[0]),
                "volatility": float(performance[1]),
                "sharpe_ratio": float(performance[2]),
            },
            "weights": clean_weights,
            "risk_free_rate": float(optimizer.get_rf_rate()),
            "requested_tickers": tickers,
            "used_tickers": list(clean_price_data.columns),
            "removed_tickers": removed,
        }

        # Add allocation if portfolio value provided
        if portfolio_value:
            allocation = optimizer.get_allocation(weights, portfolio_value)
            # Convert numpy int64 to Python int for JSON serialization
            result["allocation"] = {
                k: int(v) if isinstance(v, (np.integer, np.int64)) else float(v)
                for k, v in allocation.items()
            }

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio/plot-returns", methods=["POST"])
def plot_portfolio_returns():
    """
    Plot portfolio returns vs S&P 500 and return as markdown image URL.
    Request body:
    {
        "tickers": ["AAPL", "GOOGL", "MSFT"],
        "weights": {"AAPL": 0.4, "GOOGL": 0.3, "MSFT": 0.3},
        "period": "1y",
        "holding_period": "1 Yr",
        "index_symbol": "^GSPC"
    }
    """
    try:
        data = request.get_json()
        tickers = data.get("tickers")
        weights_dict = data.get("weights")
        period = data.get("period")
        holding_period = data.get("holding_period")
        index_symbol = data.get("index_symbol", "^GSPC")

        if not tickers or not weights_dict:
            return jsonify({"error": "tickers and weights are required"}), 400
        if not period:
            return jsonify(
                {"error": "period is required (should match optimization period)"}
            ), 400
        if not holding_period:
            return jsonify(
                {
                    "error": "holding_period is required (should match optimization holding_period)"
                }
            ), 400

        # Fetch price data
        price_data = pb.get_closingPrice_list(
            ticker_list=tickers, period=period, interval="1d"
        )

        # Validate/clean price data
        try:
            clean_price_data, removed = _validate_and_clean_prices(price_data, tickers)
        except Exception as e:
            return jsonify({"error": "Invalid price data", "details": str(e)}), 400

        # Create optimizer
        optimizer = PortfolioOptimizer(clean_price_data, holding_period=holding_period)

        # Fetch S&P 500 data
        sp = pb.get_closingPrice_list(
            ticker_list=index_symbol, period=period, interval="1d"
        )
        sp_returns = sp.pct_change().dropna()
        portfolio_returns = (
            (clean_price_data.pct_change() * pd.Series(weights_dict))
            .sum(axis=1)
            .dropna()
        )

        combined = pd.DataFrame(
            {"S&P 500": sp_returns[index_symbol], "Portfolio": portfolio_returns}
        ).dropna()
        cumulative_returns = (1 + combined).cumprod()

        # Create plot
        plt.figure(figsize=(12, 6))
        plt.plot(
            cumulative_returns.index,
            cumulative_returns["Portfolio"],
            label="Portfolio",
            linewidth=2,
        )
        plt.plot(
            cumulative_returns.index,
            cumulative_returns["S&P 500"],
            label="S&P 500",
            linewidth=2,
        )
        plt.xlabel("Date")
        plt.ylabel("Cumulative Returns")
        plt.title("Portfolio Returns vs S&P 500")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # Generate unique filename with timestamp
        filename = f"portfolio_returns_{int(time.time())}.png"
        filepath = CHARTS_DIR / filename

        # Save plot to file
        plt.savefig(filepath, format="png", dpi=150, bbox_inches="tight")
        plt.close()

        # Calculate metrics
        metrics = {}
        rf_annual = float(
            optimizer.get_rf_rate() or 0.0
        )  # must be annual decimal (e.g. 0.02)

        # 'combined' holds daily returns for both series — use it for mean/std
        for col in combined.columns:
            returns = combined[col].dropna()  # daily returns

            # drawdown: use cumulative product of (1 + returns)
            cum = (1 + returns).cumprod()
            cum_max = cum.cummax()
            drawdown = (cum - cum_max) / cum_max
            max_drawdown = float(drawdown.min())

            # annualize from daily returns
            mean_daily = float(returns.mean())
            std_daily = float(returns.std(ddof=0))
            annual_return = mean_daily * 252
            annual_volatility = std_daily * (252**0.5)

            sharpe = None
            if annual_volatility and not np.isnan(annual_volatility):
                sharpe = float((annual_return - rf_annual) / annual_volatility)

            metrics[col] = {
                "drawdown": max_drawdown,
                "annual_return": annual_return,
                "volatility": annual_volatility,
                "sharpe_ratio": sharpe,
            }

        # Return ONLY the markdown image - no extra text or metadata
        chart_url = f"http://localhost:5003/charts/{filename}"
        return jsonify(
            {
                "image": f"![Portfolio Returns vs S&P 500]({chart_url})",
                "metrics": metrics,
                "removed_tickers": removed,
            }
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio/efficient-frontier", methods=["POST"])
def efficient_frontier():
    """
    Generate efficient frontier data points.
    Request body:
    {
        "tickers": ["AAPL", "GOOGL", "MSFT"],
        "period": "1y",
        "holding_period": "1 Yr",
        "num_portfolios": 5000
    }
    """
    try:
        data = request.get_json()
        tickers = data.get("tickers")
        period = data.get("period")
        holding_period = data.get("holding_period")
        num_portfolios = data.get("num_portfolios", 5000)

        if not tickers:
            return jsonify({"error": "tickers list is required"}), 400
        if not period:
            return jsonify(
                {
                    "error": "period is required. Ask user: 'How far back should I analyze historical data? (e.g., 1y, 2y, 5y)'"
                }
            ), 400
        if not holding_period:
            return jsonify(
                {
                    "error": "holding_period is required. Ask user: 'What is your investment time horizon? (e.g., 1 Yr, 5 Yr, 10 Yr)'"
                }
            ), 400

        # Fetch price data
        price_data = pb.get_closingPrice_list(
            ticker_list=tickers, period=period, interval="1d"
        )

        # Validate/clean price data
        try:
            clean_price_data, removed = _validate_and_clean_prices(price_data, tickers)
        except Exception as e:
            return jsonify({"error": "Invalid price data", "details": str(e)}), 400

        # Create optimizer
        optimizer = PortfolioOptimizer(clean_price_data, holding_period=holding_period)

        # Get expected returns and covariance matrix
        mu = optimizer.get_expected_returns(type="mean")
        S = optimizer.get_covariance_matrix(type="ledoit_wolf")

        # Validate mu and S
        if (
            mu is None
            or S is None
            or getattr(mu, "isnull", lambda: False)().any()
            or (hasattr(S, "isnull") and S.isnull().values.any())
        ):
            return (
                jsonify(
                    {
                        "error": "Computed returns or covariance invalid",
                        "removed_tickers": removed,
                    }
                ),
                500,
            )

        # Generate random portfolios for efficient frontier
        results = []
        np.random.seed(42)

        for _ in range(num_portfolios):
            # use number of valid columns, not original tickers list
            n = clean_price_data.shape[1]
            weights = np.random.random(n)
            weights /= np.sum(weights)

            portfolio_return = np.dot(weights, mu)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(S, weights)))
            sharpe = (portfolio_return - optimizer.get_rf_rate()) / portfolio_volatility

            results.append(
                {
                    "return": float(portfolio_return),
                    "volatility": float(portfolio_volatility),
                    "sharpe": float(sharpe),
                }
            )

        # Get optimal portfolio
        _, _, optimal_weights = optimizer.get_weights(mu, S, method="max_sharpe")
        optimal_performance = optimizer.get_performance(mu, S, method="max_sharpe")[0]

        return jsonify(
            {
                "frontier_points": results,
                "optimal_portfolio": {
                    "expected_return": float(optimal_performance[0]),
                    "volatility": float(optimal_performance[1]),
                    "sharpe_ratio": float(optimal_performance[2]),
                    "weights": optimal_weights,
                },
            }
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
