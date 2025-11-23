from typing import Optional, Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from EdgarRetriever import EdgarRetriever
import matplotlib

matplotlib.use("Agg")  # Use non-GUI backend
import matplotlib.pyplot as plt
import io
from pathlib import Path
import time

app = FastAPI(title="Financial Data API")

# Create charts directory for storing generated plots
CHARTS_DIR = Path("/app/charts")
CHARTS_DIR.mkdir(exist_ok=True)

# Mount static files for chart serving
app.mount("/charts", StaticFiles(directory=str(CHARTS_DIR)), name="charts")

# Store active retrievers (in production, use proper caching/state management)
retrievers = {}


class CompanyRequest(BaseModel):
    ticker: str
    user_agent: str = "financial-api@example.com"


class InterFrameRequest(BaseModel):
    tag: str
    year: int
    quarter: Optional[int] = None


class IntraConceptRequest(BaseModel):
    ticker: str
    tag: str
    user_agent: str = "financial-api@example.com"


class PlotRequest(BaseModel):
    ticker: str
    data_type: Literal["shares", "float"]
    user_agent: str = "financial-api@example.com"


class PercentChangeRequest(BaseModel):
    ticker: str
    data_type: Literal["shares", "float"]
    time_field: str = "filed"
    y_field: str = "val"
    user_agent: str = "financial-api@example.com"


class FinancialStatementRequest(BaseModel):
    ticker: str
    statement_type: Literal["income_statement", "balance_sheet", "cash_flow"]
    periods: int = 1
    annual: bool = False
    concise_format: bool = True
    user_agent: str = "financial-api@example.com"


class CompanyInfoRequest(BaseModel):
    ticker: str
    user_agent: str = "financial-api@example.com"


class PlotDataRequest(BaseModel):
    ticker: str
    data_type: Literal["shares", "float"]
    x_field: str = "filed"
    y_field: str = "val"
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    title: Optional[str] = None
    kind: str = "line"
    use_sci: bool = True
    user_agent: str = "financial-api@example.com"


class PlotFinancialRequest(BaseModel):
    ticker: str
    statement_type: Literal["income_statement", "balance_sheet", "cash_flow"]
    metric: str  # e.g., "Revenues", "NetIncome", "TotalAssets"
    periods: int = 10
    annual: bool = False
    title: Optional[str] = None
    y_label: Optional[str] = None
    user_agent: str = "financial-api@example.com"


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/company/tickers")
def get_company_tickers(user_agent: str = "financial-api@example.com"):
    """Get all company tickers and exchanges data"""
    try:
        retriever = EdgarRetriever(user_agent=user_agent)
        data = retriever.get_company_tickers_exchange()
        return {"count": len(data), "data": data.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/company/cik")
def get_cik(req: CompanyRequest):
    """Get CIK for a specific ticker"""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )
        return {"ticker": req.ticker, "cik": retriever.current_cik}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/company/filings")
def get_company_filings(req: CompanyRequest):
    """Get filing metadata for a specific company"""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        filings = retriever.get_company_file_data()
        return {
            "ticker": req.ticker,
            "cik": retriever.current_cik,
            "count": len(filings),
            "filings": filings.to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/frame/inter")
def get_inter_frame_data(req: InterFrameRequest):
    """[ADVANCED USE ONLY] Get cross-company comparison data for specific XBRL tags. Requires knowledge of XBRL taxonomy. For standard company financial data, use /v1/financial/statement-llm instead."""
    try:
        retriever = EdgarRetriever()
        data = retriever.get_inter_frameData(req.tag, req.year, req.quarter)

        # Check if error message was returned
        if isinstance(data, str):
            raise HTTPException(status_code=404, detail=data)

        return {
            "tag": req.tag,
            "year": req.year,
            "quarter": req.quarter,
            "count": len(data),
            "data": data.to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/concept/intra")
def get_intra_concept_data(req: IntraConceptRequest):
    """[ADVANCED USE ONLY] Get raw XBRL concept data for specific financial tags. DO NOT use this for general financial statements - use /v1/financial/statement-llm instead. This endpoint requires knowledge of XBRL taxonomy tags (e.g., 'us-gaap:Revenue'). For standard income statements, balance sheets, and cash flows, always use the dedicated financial statement endpoints."""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        response = retriever.get_intra_conceptData(req.tag)

        # Check if error message was returned
        if isinstance(response, str):
            raise HTTPException(status_code=404, detail=response)

        return {
            "ticker": req.ticker,
            "cik": retriever.current_cik,
            "tag": req.tag,
            "count": len(response),
            "data": response.to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/company/shares")
def get_shares_outstanding(req: CompanyRequest):
    """Get outstanding shares history for a company"""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        shares = retriever.get_CompanyShare_History()
        if isinstance(shares, str):
            raise HTTPException(status_code=404, detail=shares)

        return {
            "ticker": req.ticker,
            "cik": retriever.current_cik,
            "count": len(shares),
            "data": shares.to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/company/float")
def get_float_shares(req: CompanyRequest):
    """Get public float shares history for a company"""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        float_shares = retriever.get_CompanyFloat_History()
        if isinstance(float_shares, str):
            raise HTTPException(status_code=404, detail=float_shares)

        return {
            "ticker": req.ticker,
            "cik": retriever.current_cik,
            "count": len(float_shares),
            "data": float_shares.to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/analysis/pct-change")
def calculate_percent_change(req: PercentChangeRequest):
    """Calculate CAGR and total return for company shares or float"""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        # Get data based on type
        if req.data_type == "shares":
            data = retriever.get_CompanyShare_History()
        else:
            data = retriever.get_CompanyFloat_History()

        if isinstance(data, str):
            raise HTTPException(status_code=404, detail=data)

        # Calculate percent change
        pct_change = retriever.pct_change(data, req.time_field, req.y_field)

        return {
            "ticker": req.ticker,
            "cik": retriever.current_cik,
            "data_type": req.data_type,
            "cagr": pct_change.get("CAGR"),
            "total_return": pct_change.get("total_return"),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/financial/statement")
def get_financial_statement(req: FinancialStatementRequest):
    """[DEPRECATED - Use /v1/financial/statement-llm for AI/LLM] Get financial statements formatted for human display (income statement, balance sheet, or cash flow). This endpoint returns rich formatted output meant for end users, not LLMs."""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        stmt = retriever.get_financial_statement_user(
            statement_type=req.statement_type,
            periods=req.periods,
            annual=req.annual,
            concise_format=req.concise_format,
        )

        # Convert to dict for JSON response
        return {
            "ticker": req.ticker,
            "cik": retriever.current_cik,
            "statement_type": req.statement_type,
            "periods": req.periods,
            "annual": req.annual,
            "data": str(stmt),  # Financial statement as string representation
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/financial/statement-llm")
def get_financial_statement_llm(req: FinancialStatementRequest):
    """[PRIMARY ENDPOINT FOR FINANCIAL DATA] Get financial statements including income statement, balance sheet, and cash flow statement. This is the main endpoint for retrieving company financials like revenue, net income, assets, liabilities, etc. Optimized for AI/LLM with structured formatting. Use this for all standard financial statement queries - DO NOT use concept/intra endpoints unless you need raw XBRL tags."""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        stmt = retriever._get_financial_statement_process(
            statement_type=req.statement_type,
            periods=req.periods,
            annual=req.annual,
            concise_format=req.concise_format,
        )

        return {
            "ticker": req.ticker,
            "cik": retriever.current_cik,
            "statement_type": req.statement_type,
            "periods": req.periods,
            "annual": req.annual,
            "llm_context": stmt,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/company/info")
def get_company_info(req: CompanyInfoRequest):
    """[DEPRECATED - Use /v1/company/info-llm for AI/LLM] Get basic company information formatted for human display. This endpoint returns rich formatted output meant for end users, not LLMs."""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        info = retriever.get_company_info()

        return {"ticker": req.ticker, "cik": retriever.current_cik, "info": str(info)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/company/info-llm")
def get_company_info_llm(req: CompanyInfoRequest):
    """[RECOMMENDED FOR AI/LLM] Get basic company information formatted specifically for LLM context. Returns structured data optimized for AI analysis."""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        info = retriever._get_company_info()

        return {"ticker": req.ticker, "cik": retriever.current_cik, "llm_context": info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/plot/data")
def plot_data(req: PlotDataRequest):
    """[RECOMMENDED FOR AI/LLM] Generate a plot for company data (shares/float history) and return as base64-encoded PNG in JSON. The base64 string can be decoded and displayed in chat interfaces like Open WebUI."""
    try:
        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        # Get data based on type
        if req.data_type == "shares":
            data = retriever.get_CompanyShare_History()
        else:
            data = retriever.get_CompanyFloat_History()

        if isinstance(data, str):
            raise HTTPException(status_code=404, detail=data)

        # Sort data by date in chronological order (oldest to newest)
        data = data.sort_values(by=req.x_field)

        # Create plot
        retriever.plot_2d(
            data=data,
            x_field=req.x_field,
            y_field=req.y_field,
            x_label=req.x_label or "Filing Date",
            y_label=req.y_label or req.data_type.title(),
            title=req.title or f"{req.ticker} {req.data_type.title()} History",
            kind=req.kind,
            use_sci=req.use_sci,
        )

        # Generate unique filename with timestamp
        filename = f"{req.ticker}_{req.data_type}_{int(time.time())}.png"
        filepath = CHARTS_DIR / filename

        # Save plot to file
        plt.savefig(filepath, format="png", dpi=150, bbox_inches="tight")
        plt.close()

        # Return ONLY the markdown image - no extra text or metadata
        chart_url = f"http://localhost:5503/charts/{filename}"
        return {
            "image": f"![{req.ticker} {req.data_type.title()} History]({chart_url})"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/plot/data-image/{ticker}/{data_type}")
def plot_data_image(
    ticker: str,
    data_type: Literal["shares", "float"],
    x_field: str = "filed",
    y_field: str = "val",
    user_agent: str = "financial-api@example.com",
):
    """Generate a plot and return as PNG image directly"""
    try:
        retriever = EdgarRetriever(user_agent=user_agent, ticker=ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {ticker}"
            )

        # Get data based on type
        if data_type == "shares":
            data = retriever.get_CompanyShare_History()
        else:
            data = retriever.get_CompanyFloat_History()

        if isinstance(data, str):
            raise HTTPException(status_code=404, detail=data)

        # Create plot
        ax = retriever.plot_2d(
            data=data,
            x_field=x_field,
            y_field=y_field,
            title=f"{ticker} {data_type.title()} History",
            kind="line",
            use_sci=True,
        )

        # Save plot to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)

        # Get image bytes
        image_bytes = buf.read()

        # Clean up
        plt.close()
        buf.close()

        return Response(content=image_bytes, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/plot/financial")
def plot_financial_metric(req: PlotFinancialRequest):
    """[RECOMMENDED FOR AI/LLM] Generate a plot for financial statement metrics (e.g., Revenue, Net Income, Total Assets) and return as base64-encoded PNG in JSON. Use this to visualize financial trends over time. The image will be automatically displayed in the chat."""
    try:
        from edgar import Company, set_identity

        retriever = EdgarRetriever(user_agent=req.user_agent, ticker=req.ticker)
        if retriever.current_cik is None:
            raise HTTPException(
                status_code=404, detail=f"No CIK found for ticker: {req.ticker}"
            )

        # Get financial statement using edgar library
        set_identity(req.user_agent)
        company = Company(retriever.current_cik)

        if req.statement_type == "income_statement":
            stmt = company.income_statement(periods=req.periods, annual=req.annual)
        elif req.statement_type == "balance_sheet":
            stmt = company.balance_sheet(periods=req.periods, annual=req.annual)
        elif req.statement_type == "cash_flow":
            stmt = company.cash_flow(periods=req.periods, annual=req.annual)
        else:
            raise HTTPException(status_code=400, detail="Invalid statement_type")

        # Convert to dataframe and extract metric
        df = stmt.to_dataframe()

        # Find the metric row (case-insensitive search)
        metric_row = None
        for idx in df.index:
            if req.metric.lower() in str(idx).lower():
                metric_row = idx
                break

        if metric_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Metric '{req.metric}' not found in {req.statement_type}. Available metrics: {list(df.index)}",
            )

        # Extract the data for plotting
        plot_data = df.loc[metric_row]

        # Filter out metadata columns (keep only period columns like Q1 2024, Q2 2024, etc.)
        # Metadata columns include: confidence, section, is_total, is_abstract, depth
        metadata_cols = [
            "confidence",
            "section",
            "is_total",
            "is_abstract",
            "depth",
            "label",
        ]
        plot_data = plot_data.drop(labels=metadata_cols, errors="ignore")

        # Reverse to show oldest to newest (left to right)
        plot_data = plot_data[::-1]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot the data - convert values properly
        periods = list(plot_data.index)  # Use actual period labels from columns
        values = []
        for v in plot_data.values:
            if v is None or v == "":
                values.append(0)
            else:
                # Handle numeric values directly
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    values.append(0)

        ax.plot(periods, values, marker="o", linewidth=2, markersize=8)
        ax.set_xlabel("Period (Quarter/Year)")
        ax.set_ylabel(req.y_label or req.metric)
        ax.set_title(req.title or f"{req.ticker} - {req.metric}")
        ax.grid(True, alpha=0.3)

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha="right")

        # Format y-axis with currency notation
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(
                lambda x, p: f"${x / 1e9:.2f}B" if abs(x) >= 1e9 else f"${x / 1e6:.2f}M"
            )
        )

        plt.tight_layout()

        # Generate unique filename with timestamp
        filename = f"{req.ticker}_{req.metric.replace(' ', '_')}_{int(time.time())}.png"
        filepath = CHARTS_DIR / filename

        # Save plot to file
        plt.savefig(filepath, format="png", dpi=150, bbox_inches="tight")
        plt.close()

        # Return ONLY the markdown image - no extra text or metadata
        chart_url = f"http://localhost:5503/charts/{filename}"
        return {"image": f"![{req.ticker} - {req.metric}]({chart_url})"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5503)
