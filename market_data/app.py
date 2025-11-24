from flask import Flask, request, jsonify
import numpy as np
import PortfolioBuilder as pb
from pyportfolio import PortfolioOptimizer, get_company_tickers_json_path

app = Flask(__name__)


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
                    "description": "Calculates optimal asset allocation for a portfolio using various optimization methods (max Sharpe ratio, min volatility, etc.). Returns expected return, volatility, Sharpe ratio, and optimal weights for each ticker.",
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
                                            "description": "List of stock tickers to include in portfolio (minimum 2 stocks recommended)",
                                            "example": [
                                                "AAPL",
                                                "MSFT",
                                                "GOOGL",
                                                "AMZN",
                                            ],
                                        },
                                        "period": {
                                            "type": "string",
                                            "default": "1y",
                                            "description": "Historical data period for analysis",
                                            "example": "1y",
                                        },
                                        "method": {
                                            "type": "string",
                                            "default": "max_sharpe",
                                            "enum": [
                                                "max_sharpe",
                                                "min_volatility",
                                                "max_quadratic_utility",
                                                "efficient_risk",
                                                "efficient_return",
                                            ],
                                            "description": "Optimization method: max_sharpe (maximize risk-adjusted returns), min_volatility (minimize risk), or others",
                                            "example": "max_sharpe",
                                        },
                                        "returns_type": {
                                            "type": "string",
                                            "default": "mean",
                                            "enum": ["mean", "capm", "ema"],
                                            "description": "Expected returns calculation method",
                                            "example": "mean",
                                        },
                                        "cov_type": {
                                            "type": "string",
                                            "default": "ledoit_wolf",
                                            "enum": [
                                                "ledoit_wolf",
                                                "semicovariance",
                                                "exp_cov",
                                            ],
                                            "description": "Covariance matrix estimation method",
                                            "example": "ledoit_wolf",
                                        },
                                        "portfolio_value": {
                                            "type": "number",
                                            "description": "Optional: Total portfolio value in dollars for allocation calculation",
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
                                                        "type": "number"
                                                    },
                                                    "volatility": {"type": "number"},
                                                    "sharpe_ratio": {"type": "number"},
                                                },
                                            },
                                            "weights": {"type": "object"},
                                            "risk_free_rate": {"type": "number"},
                                            "allocation": {"type": "object"},
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
                    "description": "Returns list of stocks matching specified Standard Industrial Classification (SIC) codes. Useful for sector-based analysis or finding companies in specific industries.",
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
                        "200": {"description": "List of stocks matching SIC codes"}
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
        return jsonify({"stocks": stocks, "count": len(stocks)}), 200
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
        return jsonify({"stocks": stocks, "count": len(stocks)}), 200
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
        tickers = data.get("tickers", [])
        period = data.get("period", "1y")
        holding_period = data.get("holding_period", "1 Yr")
        method = data.get("method", "max_sharpe")
        returns_type = data.get("returns_type", "mean")
        cov_type = data.get("cov_type", "ledoit_wolf")
        portfolio_value = data.get("portfolio_value")

        if not tickers:
            return jsonify({"error": "tickers list is required"}), 400

        # Fetch price data
        price_data = pb.get_closingPrice_list(
            ticker_list=tickers, period=period, interval="1d"
        )

        # Create optimizer
        optimizer = PortfolioOptimizer(price_data, holding_period=holding_period)

        # Get expected returns and covariance matrix
        mu = optimizer.get_expected_returns(type=returns_type)
        S = optimizer.get_covariance_matrix(type=cov_type)

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
        tickers = data.get("tickers", [])
        period = data.get("period", "1y")
        holding_period = data.get("holding_period", "1 Yr")
        num_portfolios = data.get("num_portfolios", 5000)

        if not tickers:
            return jsonify({"error": "tickers list is required"}), 400

        # Fetch price data
        price_data = pb.get_closingPrice_list(
            ticker_list=tickers, period=period, interval="1d"
        )

        # Create optimizer
        optimizer = PortfolioOptimizer(price_data, holding_period=holding_period)

        # Get expected returns and covariance matrix
        mu = optimizer.get_expected_returns(type="mean")
        S = optimizer.get_covariance_matrix(type="ledoit_wolf")

        # Generate random portfolios for efficient frontier
        results = []
        np.random.seed(42)

        for _ in range(num_portfolios):
            weights = np.random.random(len(tickers))
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
