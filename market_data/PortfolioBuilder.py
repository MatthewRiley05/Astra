# Import required libraries
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import warnings
import requests
import time
from pathlib import Path

# Try to import screener, fall back if not available
try:
    from yfinance.screener import screen

    SCREENER_AVAILABLE = True
except ImportError:
    SCREENER_AVAILABLE = False
    screen = None

Headers = {"User-Agent": "email@address.com"}


def fetch_possible_stocks(Headers):
    """
    Fetches US stock tickers from the Edgar database.
    Returns a dataframe of stock tickers
    """

    companyTickers = requests.get(
        "https://www.sec.gov/files/company_tickers_exchange.json", headers=Headers
    )

    # convert to pandas dataframe
    companyData = pd.DataFrame(
        companyTickers.json()["data"], columns=companyTickers.json()["fields"]
    )
    # format cik, add leading 0s
    companyData["cik"] = companyData["cik"].apply(lambda x: str(x).zfill(10))

    exchanges = ["Nasdaq", "NYSE", "CBOE"]
    companyData = companyData[companyData["exchange"].isin(exchanges)].reset_index(
        drop=True
    )

    return companyData


def fetch_company_sic(
    companyData, location=None, headers=Headers, requests_per_second=10, max_retries=3
):
    """
    Fetches SIC codes for each company in the provided dataframe.
    Respects rate limit (requests_per_second) and does simple retries with backoff.
    Returns a dataframe with CIK, Ticker, Title, Exchange, SIC and SIC_Description.
    """
    sic_codes = []
    sic_descriptions = []
    delay = (
        1.0 / float(requests_per_second)
        if requests_per_second and requests_per_second > 0
        else 0.1
    )

    session = requests.Session()
    session.headers.update(headers)

    last_request = 0.0
    for cik in companyData["cik"]:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        sic = "N/A"
        desc = "N/A"
        for attempt in range(1, max_retries + 1):
            try:
                resp = session.get(url, timeout=10)
                resp.raise_for_status()
                j = resp.json()
                sic = j.get("sic", "N/A")
                desc = j.get("sicDescription", "N/A")
                break
            except requests.exceptions.RequestException:
                backoff = 0.5 * (2 ** (attempt - 1))
                time.sleep(backoff)
        sic_codes.append(sic)
        sic_descriptions.append(desc)

        # precise rate limiting
        elapsed = time.monotonic() - last_request
        sleep_for = delay - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)
        last_request = time.monotonic()

    companyData["SIC"] = sic_codes
    companyData["SIC_Description"] = sic_descriptions

    if location:
        p = Path(location)
        # if user passed a directory (exists or trailing slash), create dir and use default filename
        if p.exists() and p.is_dir() or str(location).endswith(("/", "\\")):
            p.mkdir(parents=True, exist_ok=True)
            out_path = p / "company_tickers_with_sic.json"
        # if it looks like a filename (has an extension), use it
        elif p.suffix:
            p.parent.mkdir(parents=True, exist_ok=True)
            out_path = p
        else:
            # treat as directory
            p.mkdir(parents=True, exist_ok=True)
            out_path = p / "company_tickers_with_sic.json"

        companyData.to_json(str(out_path), orient="records", lines=True)

    return companyData


class yf_screener:
    """
    simple yfinance-based screener wrapper, ask the user if they want to use this to filter for stocks,
    if yes call on available_predefined method.

    - If predef_query is provided (e.g. "aggressive_small_caps") the class will call
      yfinance.screener.screen(predef_query, count=...).
    """

    def __init__(
        self,
        predef_query=None,
        count=10,
        size=None,
        max_results_cap=15,
        session=None,
        headers=None,
    ):
        """Initialize the yf_screener.

        Args:
            predef_query (str|None): name of a predefined yfinance screener query.
            count (int): default count for predefined queries (yfinance uses `count`).
            size (int|None): default size for custom queries.
            max_results_cap (int): maximum number of results to return (default 15).
            session: optional session object to reuse connections.
            headers (dict|None): optional HTTP headers (not used for Yahoo calls by default).
        """
        self.predef_query = predef_query
        self.count = int(count) if count is not None else None
        self.size = int(size) if size is not None else None
        try:
            self.max_results_cap = int(max_results_cap)
            if self.max_results_cap <= 0:
                self.max_results_cap = 15
        except Exception:
            self.max_results_cap = 15
        self.session = session
        self.headers = headers

    def available_predefined(self):
        """Return a list of available predefined screener keys.
        Make sure to run this to have suggested inputs first.
        Tries to read `yf.PREDEFINED_SCREENER_QUERIES` and falls back gracefully.
        """
        if not SCREENER_AVAILABLE:
            return []
        try:
            return list(yf.PREDEFINED_SCREENER_QUERIES.keys())
        except Exception:
            try:
                from yfinance.screener import PREDEFINED_SCREENER_QUERIES

                return list(PREDEFINED_SCREENER_QUERIES.keys())
            except Exception:
                return []

    def _enforce_cap(self, df):
        """Enforce the configured max results cap on a DataFrame and warn if truncated."""
        if not isinstance(df, pd.DataFrame):
            return df
        if self.max_results_cap and len(df) > self.max_results_cap:
            warnings.warn(
                f"max_results_cap exceeded: returning top {self.max_results_cap} results (requested {len(df)}).",
                UserWarning,
            )
            return df.iloc[: self.max_results_cap].reset_index(drop=True)
        return df

    def screen_predefined(
        self, predef_query=None, count=None, sortField=None, sortAsc=None
    ):
        """Run a predefined yfinance screener and return a normalized DataFrame.

        Args:
            predef_query (str|None): name of predefined screener; if None uses self.predef_query.
            count (int|None): override count (yfinance `count` parameter).
            sortField (str|None): optional sort field.
            sortAsc (bool|None): optional sort order.
        Returns:
            pandas.DataFrame: normalized screener results (possibly truncated to max_results_cap).
        """
        if not SCREENER_AVAILABLE:
            warnings.warn(
                "yfinance screener module is not available in this version", UserWarning
            )
            return pd.DataFrame()

        key = predef_query or self.predef_query
        if not key:
            raise ValueError(
                "No predefined query specified. Call with `predef_query` or set one at construction."
            )
        use_count = self.count if count is None else count
        try:
            # yfinance accepts `count` for predefined queries
            resp = screen(key, count=use_count, sortField=sortField, sortAsc=sortAsc)
        except Exception as e:
            warnings.warn(f"yfinance screener call failed: {e}", UserWarning)
            return pd.DataFrame()

        df = self.to_dataframe(resp)
        df = self._enforce_cap(df)
        return df

    '''
    #deprecated for now

    def screen_custom(self, query_obj, size=None, offset=None, sortField=None, sortAsc=None):
        """Run a custom EquityQuery/FundQuery via yfinance `screen` and return a DataFrame.

        Args:
            query_obj: query object or dict as accepted by `yfinance.screener.screen`.
            size (int|None): page size for custom queries (yfinance `size` parameter).
            offset (int|None): pagination offset.
        """
        use_size = self.size if size is None else size
        try:
            resp = screen(query_obj, size=use_size, offset=offset, sortField=sortField, sortAsc=sortAsc)
        except Exception as e:
            warnings.warn(f"yfinance screener call failed: {e}", UserWarning)
            return pd.DataFrame()

        df = self.to_dataframe(resp)
        df = self._enforce_cap(df)
        return df
        
    '''

    def to_dataframe(self, response):
        """Normalize a yfinance screener response into a pandas DataFrame.

        This function is defensive because different yfinance versions return different shapes.
        It attempts to find the list of quote dicts in common keys and falls back to a safe empty DataFrame.
        """
        if response is None:
            return pd.DataFrame()

        quotes = None

        def _find_list_of_dicts(obj):
            """Recursively find the first list of dicts inside obj."""
            if isinstance(obj, list):
                if obj and isinstance(obj[0], dict):
                    return obj
                return None
            if isinstance(obj, dict):
                # direct keys we expect
                for key in ("quotes", "data", "result", "items", "quotesList"):
                    val = obj.get(key)
                    if isinstance(val, list) and val and isinstance(val[0], dict):
                        return val
                # otherwise search deeper
                for v in obj.values():
                    found = _find_list_of_dicts(v)
                    if found:
                        return found
            return None

        quotes = _find_list_of_dicts(response)

        if not quotes:
            return pd.DataFrame()

        try:
            df = pd.json_normalize(quotes)
        except Exception:
            # last resort: build DataFrame from list comprehension
            try:
                df = pd.DataFrame([q if isinstance(q, dict) else {} for q in quotes])
            except Exception:
                return pd.DataFrame()

        # normalize common column names: prefer 'symbol', fall back to 'ticker'
        if "symbol" not in df.columns and "ticker" in df.columns:
            df = df.rename(columns={"ticker": "symbol"})

        # ensure symbol exists and is a clean string (uppercase)
        if "symbol" in df.columns:
            df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()

        return df.reset_index(drop=True)


def get_closingPrice_list(
    ticker_list, start=None, end=None, period="5d", interval="1d"
):
    """
    Fetches market closing data for a given ticker/list of tickers from yfinance.

    Intervals supported are: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo

    start and end should be in 'YYYY-MM-DD' format strings.
    1m interval is only available for last 7 days.
    """
    data = yf.Tickers(ticker_list)
    close = data.history(start=start, end=end, period=period, interval=interval)[
        "Close"
    ]
    return close


def get_market_data(ticker, start=None, end=None, period="5d", interval="1d"):
    """
    INCLUDES HIGH, LOW, OPEN, CLOSE, VOLUME DATA
    ALSO INCLUDES INFO DICT WITH COMPANY METADATA SUCH AS BUSINESS SUMMARY
    Fetches market data for a given ticker from yfinance.
    This is mostly descriptive, use get_closingPrice_list for getting close price only,
    it also accepts lists of len = 1.
    """
    symbol = yf.Ticker(ticker)
    data = symbol.history(start=start, end=end, period=period, interval=interval)
    info = symbol.get_info()

    return data, info


def get_list_of_screened_stocks(
    predef_query, count=10, size=None, max_results_cap=15, session=None, headers=None
):
    """
    Wrapper function to get a list of screened stocks using yf_screener class.
    Returns a list of ticker symbols.
    """
    screener = yf_screener(
        predef_query=predef_query, count=count, session=session, headers=headers
    )
    df = screener.screen_predefined()
    
    # Check if DataFrame is empty or missing symbol column
    if df.empty:
        return []
    
    if "symbol" not in df.columns:
        raise ValueError(
            f"Screener response missing 'symbol' column. Available columns: {list(df.columns)}"
        )
    
    screened_stocks = list(df["symbol"])
    return screened_stocks


def access_edgar_sic(companyData=None, path=None):
    """
    Function to access an existing companyData DataFrame variable or a file path containing a json file.
    """
    if companyData is not None:
        df = companyData[["SIC", "SIC_Description"]]
    elif path is not None:
        p = Path(path)
        if p.exists() and p.is_file():
            companyData = pd.read_json(str(p), orient="records", lines=True)
            df = companyData[["SIC", "SIC_Description"]]
        else:
            raise FileNotFoundError(
                f"The specified path does not exist or is not a file: {path}"
            )
    else:
        raise ValueError("Either companyData or path must be provided.")

    return df.drop_duplicates(
        subset=["SIC", "SIC_Description"], keep="first"
    ).reset_index(drop=True)


def filter_stocks_by_sic(sic_codes, companyData=None, path=None):
    """
    Filters the companyData DataFrame for stocks matching the provided SIC codes.
    sic_codes should be a list of SIC codes to filter by.
    Returns a list of ticker symbols.
    """
    if companyData is not None:
        df = companyData
    elif path is not None:
        p = Path(path)
        if p.exists() and p.is_file():
            df = pd.read_json(str(p), orient="records", lines=True)
        else:
            raise FileNotFoundError(
                f"The specified path does not exist or is not a file: {path}"
            )
    else:
        raise ValueError("Either companyData or path must be provided.")

    filtered_stocks = df[df["SIC"].isin(sic_codes)].reset_index(drop=True)
    return filtered_stocks["ticker"].to_list()


def get_riskfree_rate(data, holding_period="1 Mo"):
    """
    Fetches the current risk-free rate from the US Treasury website.
    Returns the risk-free rate as a float.

    Args:
        data: This data parameter is the dataframe of closing price data
        holding_period: The holding period for which the risk-free rate is needed
                       ['1 Mo', '3 Mo', '6 Mo', '1 Yr', '2 Yr', '3 Yr', '5 Yr', '7 Yr', '10 Yr', '30 Yr']
    """
    start = str(data.index[0])[0:4]
    end = str(data.index[-1])[0:4]

    link_consol = {}
    for i in range(int(start), int(end) + 1):
        link_consol[i] = (
            f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{i}/all?field_tdr_date_value={i}&type=daily_treasury_yield_curve&page&_format=csv"
        )

    for i in range(int(start), int(end) + 1):
        if i == int(start):
            # Read the first file and create the dataframe
            yields = (
                pd.read_csv(link_consol[i], parse_dates=["Date"], index_col=["Date"])
                .resample("ME")
                .mean()
            )
        else:
            tmp = (
                pd.read_csv(link_consol[i], parse_dates=["Date"], index_col=["Date"])
                .resample("ME")
                .mean()
            )
            yields = pd.concat([yields, tmp], axis=0)

    yields = yields[~yields.index.duplicated(keep="first")]
    if not yields.empty:
        df = yields[holding_period]
        risk_free_rate = df.mean()
        return float(risk_free_rate) / 100  # Convert percentage to decimal
    else:
        raise ValueError("Could not fetch risk-free rate data.")
