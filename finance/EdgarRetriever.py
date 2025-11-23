import requests
import pandas as pd
import matplotlib.ticker as mticker
from edgar import Company,set_identity


class EdgarRetriever:
    def __init__(self, user_agent="email@address.com", ticker=None):
        self.headers = {'User-Agent': user_agent}
        self.company_data = self.get_company_tickers_exchange()
        self._current_ticker = None
        self._current_cik = None

        #use setter to initialize if ticker provided
        if ticker is not None:
            self.current_ticker = ticker

    @property
    def current_ticker(self):
        return self._current_ticker
    

    @property
    def current_cik(self):
        return self._current_cik

    @current_ticker.setter
    def current_ticker(self, ticker):
        """Set ticker and immediately update current_cik if possible."""
        if ticker is None:
            self._current_ticker = None
            self._current_cik = None
            return
        self._current_ticker = ticker.upper()
        # try to resolve CIK immediately; leave as None if not found
        match = self.company_data[self.company_data['ticker'] == self._current_ticker]
        if not match.empty:
            self._current_cik = match['cik'].squeeze()
        else:
            self._current_cik = None
    

    def get_company_tickers_exchange(self):
        '''get company tickers and exchanges data, returns a dataframe containing their cik, 
        ticker, title, and exchange, filters for the Nasdaq, NYSE, and CBOE exchanges only'''

        companyTickers = requests.get(
            "https://www.sec.gov/files/company_tickers_exchange.json",
            headers=self.headers
            )

        #convert to pandas dataframe
        companyData = pd.DataFrame(companyTickers.json()['data'], columns=companyTickers.json()['fields'])
        # format cik, add leading 0s
        companyData['cik'] = companyData['cik'].apply(lambda x: str(x).zfill(10))

        #filter for exchanges of interest
        exchanges = ['Nasdaq', 'NYSE', 'CBOE']
        companyData = companyData[companyData['exchange'].isin(exchanges)].reset_index(drop=True)

        return companyData
    

    def get_cik_from_ticker(self, ticker):
        '''get cik for a specific ticker'''
        cik = self.company_data[self.company_data['ticker'] == ticker.upper()].cik
        if cik.empty:
            return f"No data found for ticker: {ticker}"
        else:
            self.current_cik = cik.squeeze()


    def get_company_file_data(self):
        
        '''get company filing metadata for a specific ticker, returns a dataframe containing
        filingDate, reportDate, accessionNumber, form, primaryDocDescription'''

        # get company specific filing metadata
        filingMetadata = requests.get(
            f'https://data.sec.gov/submissions/CIK{self.current_cik}.json',
            headers=self.headers
            )
        allForms = pd.DataFrame(filingMetadata.json()['filings']['recent'])
        return allForms[['filingDate', 'reportDate', 'accessionNumber', 'form', 'primaryDocDescription']]
    

    def get_inter_frameData(self, tag, year, quarter = None):

        #allows for comparison of different companies on the specific tag (company financial line item)
        '''sample tags: {'AccountsPayableCurrent', 
        'AssetsCurrent', 
        'LiabilitiesCurrent', 
        'Revenues', 
        'NetIncomeLoss'}
        
        refer to possible tags in the possible_tags.txt file 
        
        '''

        if quarter is None:
            schedule = year
        else:
            schedule = f'{year}Q{quarter}I'
        frameData = requests.get(
            f"https://data.sec.gov/api/xbrl/frames/us-gaap/{tag}/USD/CY{schedule}.json", 
            headers=self.headers)
        
        try:
            frameData = pd.DataFrame(frameData.json()['data'])
        except (KeyError, IndexError):
            return f"No frame data found for tag: {tag}, year: {year}, quarter: {quarter}"
        
        return frameData

    def get_intra_conceptData(self, tag):

        #gets the data for a specific company on a specific tag (company financial line item)

        conceptData = requests.get(
            f"https://data.sec.gov/api/xbrl/companyconcept/CIK{self.current_cik}/us-gaap/{tag}.json",
            headers=self.headers
            )
        
        try:
            conceptData = pd.DataFrame(conceptData.json()['units']['USD'])
        except (KeyError, IndexError):
            return f"No concept data found for ticker: {self.current_ticker}, CIK: {self.current_cik} and tag: {tag}"

        return conceptData
    

    def get_CompanyShare_History(self):

        '''get the outstanding shares for a specific company by cik'''
    
        companyShareHistory = requests.get(
            f'https://data.sec.gov/api/xbrl/companyfacts/CIK{self.current_cik}.json',
            headers=self.headers
        )

        try:
            shares_outstanding = companyShareHistory.json()['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares']
            return pd.DataFrame(shares_outstanding)
        except (KeyError, IndexError):
            return f"No outstanding shares history data found for CIK: {self.current_cik}"
        
    def get_CompanyFloat_History(self):

        '''get the float shares (public shares, non affiliate) for a specific company by cik in USD'''
        
        companyFloatShares = requests.get(
            f'https://data.sec.gov/api/xbrl/companyfacts/CIK{self.current_cik}.json',
            headers=self.headers
        )

        try:
            float_shares = companyFloatShares.json()['facts']['dei']['EntityPublicFloat']['units']['USD']
            return pd.DataFrame(float_shares)
        except (KeyError, IndexError):
            return f"No float shares data found for ticker: {self.current_ticker}"
        

    def get_financial_statement_user(self, statement_type='balance_sheet', periods=1, annual=False, concise_format=True):
        """
        Confidence is the possibility of it being accurate due to changing reporting standards over time
        Retrieve financial statements for the current company.
        statement_type: 'income_statement', 'balance_sheet', or 'cash_flow'
        periods: number of periods to retrieve
        concise_format: if True, formats large numbers (e.g., 1,000,000 as 1.0M)
        Returns a pandas DataFrame.
        """
        set_identity(self.headers['User-Agent'])
        company = Company(self.current_cik)
        
        if statement_type == 'income_statement':
            stmt = company.income_statement(periods=periods, annual=annual, concise_format=concise_format)
        elif statement_type == 'balance_sheet':
            stmt = company.balance_sheet(periods=periods, annual=annual, concise_format=concise_format)
        elif statement_type == 'cash_flow':
            stmt = company.cash_flow(periods=periods, annual=annual, concise_format=concise_format)
        else:
            raise ValueError("Invalid statement_type. Choose from 'income_statement', 'balance_sheet', or 'cash_flow'.")

        return stmt
    

    def _get_financial_statement_process(self, statement_type='balance_sheet', periods=1, annual=False, concise_format=True):
        """
        NOTE, THIS IS FOR PROCESSING THE DATA INTO LLM CONTEXT FORMAT NOT FOR DISPLAYING TO THE USER
        Confidence is the possibility of it being accurate due to changing reporting standards over time
        Retrieve financial statements for the current company.
        statement_type: 'income_statement', 'balance_sheet', or 'cash_flow'
        periods: number of periods to retrieve
        concise_format: if True, formats large numbers (e.g., 1,000,000 as 1.0M)
        Returns a pandas DataFrame.
        """
        set_identity(self.headers['User-Agent'])
        company = Company(self.current_cik)
        
        if statement_type == 'income_statement':
            stmt = company.income_statement(periods=periods, annual=annual, concise_format=concise_format).to_llm_context()
        elif statement_type == 'balance_sheet':
            stmt = company.balance_sheet(periods=periods, annual=annual, concise_format=concise_format).to_llm_context()
        elif statement_type == 'cash_flow':
            stmt = company.cash_flow(periods=periods, annual=annual, concise_format=concise_format).to_llm_context()
        else:
            raise ValueError("Invalid statement_type. Choose from 'income_statement', 'balance_sheet', or 'cash_flow'.")

        return stmt
    

    def get_company_info(self):
        """Retrieve basic company information as rich output."""
        set_identity(self.headers['User-Agent'])
        company = Company(self.current_cik)
        return company


    def _get_company_info(self):
        """NOTE this is for processing only
        Retrieve basic company information."""
        set_identity(self.headers['User-Agent'])
        company = Company(self.current_cik)
        info = company.to_context()
        return info
    

    def plot_2d(self, data, x_field, y_field, x_label=None, y_label=None, title=None, kind='line', use_sci=True):

        '''
        simple 2d plot function, please feed the proper labels and title based on the data
        accepts a pandas dataframe as data input

        x_label and y_label are optional; if omitted the axis labels are left unchanged.
        '''

        # accept anything convertible to DataFrame
        if not isinstance(data, pd.DataFrame):
            try:
                data = pd.DataFrame(data)
            except Exception:
                raise ValueError("data must be a pandas DataFrame or convertible to one")

        if x_field not in data.columns or y_field not in data.columns:
            raise ValueError(f"Columns not found in data: {x_field}, {y_field}")

        ax = data.plot(x=x_field, y=y_field, title=title, kind=kind)

        if x_label is not None:
            ax.set_xlabel(x_label)
        if y_label is not None:
            ax.set_ylabel(y_label)

        
        if use_sci:
            # force scientific notation and render exponent as math text (e.g. ×10^10)
            ax.yaxis.set_major_formatter(mticker.ScalarFormatter(useMathText=True))
            ax.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
            # optionally move the offset text into the ylabel if a label was provided
            offset = ax.yaxis.get_offset_text().get_text()
            if offset and y_label:
                ax.yaxis.get_offset_text().set_visible(False)
                ax.set_ylabel(f"{y_label} ({offset})")
        else:
            # show plain numbers (no scientific offset)
            ax.ticklabel_format(style='plain', axis='y')


        return ax
    
    def pct_change(self, data, time_field, y_field):
        """
        Return (CAGR, total_return) for the series in `y_field` over the time index `time_field`.
        - data: pandas DataFrame or convertible
        - y_field: column with values (price/metric)
        - time_field: column with datelike values
        Returns tuple of floats: (cagr, total_return) where total_return = (end/start)-1.
        If CAGR cannot be computed (zero elapsed time or invalid start value) cagr is None.
        """
        # convert to DataFrame if needed
        if not isinstance(data, pd.DataFrame):
            try:
                data = pd.DataFrame(data)
            except Exception:
                raise ValueError("data must be a pandas DataFrame or convertible to one")

        if x_field := time_field not in data.columns:  # intentional simple check for readability
            pass
        if time_field not in data.columns or y_field not in data.columns:
            raise ValueError(f"Columns not found in data: {time_field}, {y_field}")

        # ensure datetime and drop missing values
        data = data[[time_field, y_field]].dropna().copy()
        data[time_field] = pd.to_datetime(data[time_field], errors='coerce')
        data = data.dropna(subset=[time_field, y_field])
        if data.empty:
            raise ValueError("No valid rows after parsing datetime / dropping NaNs")

        data = data.sort_values(time_field).reset_index(drop=True)

        start_val = float(data.iloc[0][y_field])
        end_val = float(data.iloc[-1][y_field])
        start_date = data.iloc[0][time_field]
        end_date = data.iloc[-1][time_field]

        if start_val == 0:
            raise ValueError("Start value is zero; cannot compute returns")

        total_return = end_val / start_val - 1.0

        delta_days = (end_date - start_date).days
        if delta_days <= 0:
            cagr = None
        else:
            years = delta_days / 365.25
            # guard against negative/zero start value handled above
            try:
                cagr = (end_val / start_val) ** (1.0 / years) - 1.0
            except Exception:
                cagr = None

        pct_change = dict(CAGR=cagr, total_return=total_return)
        return pct_change



