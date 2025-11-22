from typing import Optional, Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from EdgarRetriever import EdgarRetriever

app = FastAPI(title="Financial Data API")

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
    """Get cross-company comparison data for a specific financial tag"""
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
    """Get company-specific data for a financial tag"""
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
    """Get financial statements (income statement, balance sheet, or cash flow)"""
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
    """Get financial statements formatted for LLM context processing"""
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
    """Get basic company information"""
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
    """Get basic company information formatted for LLM context"""
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5503)
