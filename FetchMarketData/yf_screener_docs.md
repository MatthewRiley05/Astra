Help on function screen in module yfinance.screener.screener:

screen(query: Union[str, yfinance.screener.query.EquityQuery, yfinance.screener.query.FundQuery], offset: int = None, size: int = None, count: int = None, sortField: str = None, sortAsc: bool = None, userId: str = None, userIdType: str = None, session=None, proxy=<object object at 0x000002BA350EF4E0>)
        Run a screen: predefined query, or custom query.

        :Parameters:
            * Defaults only apply if query = EquityQuery or FundQuery
            query : str | Query:
                The query to execute, either name of predefined or custom query.
                For predefined list run yf.PREDEFINED_SCREENER_QUERIES.keys()
            offset : int
                The offset for the results. Default 0.
            size : int
                number of results to return. Default 100, maximum 250 (Yahoo)
                Use count instead for predefined queries.
            count : int
                number of results to return. Default 25, maximum 250 (Yahoo)
                Use size instead for custom queries.
            sortField : str
                field to sort by. Default "ticker"
            sortAsc : bool
                Sort ascending? Default False
            userId : str
                The user ID. Default empty.
            userIdType : str
                Type of user ID (e.g., "guid"). Default "guid".

        Example: predefined query
            .. code-block:: python

                import yfinance as yf
                response = yf.screen("aggressive_small_caps")

        Example: custom query
            .. code-block:: python

                import yfinance as yf
                from yfinance import EquityQuery
                q = EquityQuery('and', [
                       EquityQuery('gt', ['percentchange', 3]),
                       EquityQuery('eq', ['region', 'us'])
                ])
                response = yf.screen(q, sortField = 'percentchange', sortAsc = True)

        To access predefineds query code
            .. code-block:: python

                import yfinance as yf
                query = yf.PREDEFINED_SCREENER_QUERIES['aggressive_small_caps']


    .. list-table:: Predefined queries (Dec-2024)
       :widths: 25 75
       :header-rows: 1

       * - Key
         - Values
       * - aggressive_small_caps
         - | query:
           |     EquityQuery(AND, [
           |       EquityQuery(IS-IN, ['exchange', 'NMS', 'NYQ']),
           |       EquityQuery(LT, ['epsgrowth.lasttwelvemonths', 15])
           |     ])
           | sortField: eodvolume
           | sortType: desc
       * - day_gainers
         - | query:
           |     EquityQuery(AND, [
           |       EquityQuery(GT, ['percentchange', 3]),
           |       EquityQuery(EQ, ['region', 'us']),
           |       EquityQuery(GTE, ['intradaymarketcap', 2000000000]),
           |       EquityQuery(GTE, ['intradayprice', 5]),
           |       EquityQuery(GT, ['dayvolume', 15000])
           |     ])
           | sortField: percentchange
           | sortType: DESC
       * - day_losers
         - | query:
           |     EquityQuery(AND, [
           |       EquityQuery(LT, ['percentchange', -2.5]),
           |       EquityQuery(EQ, ['region', 'us']),
           |       EquityQuery(GTE, ['intradaymarketcap', 2000000000]),
           |       EquityQuery(GTE, ['intradayprice', 5]),
           |       EquityQuery(GT, ['dayvolume', 20000])
           |     ])
           | sortField: percentchange
           | sortType: ASC
       * - growth_technology_stocks
         - | query:
           |     EquityQuery(AND, [
           |       EquityQuery(GTE, ['quarterlyrevenuegrowth.quarterly', 25]),
           |       EquityQuery(GTE, ['epsgrowth.lasttwelvemonths', 25]),
           |       EquityQuery(EQ, ['sector', 'Technology']),
           |       EquityQuery(IS-IN, ['exchange', 'NMS', 'NYQ'])
           |     ])
           | sortField: eodvolume
           | sortType: desc
       * - most_actives
         - | query:
           |     EquityQuery(AND, [
           |       EquityQuery(EQ, ['region', 'us']),
           |       EquityQuery(GTE, ['intradaymarketcap', 2000000000]),
           |       EquityQuery(GT, ['dayvolume', 5000000])
           |     ])
           | sortField: dayvolume
           | sortType: DESC
       * - most_shorted_stocks
         - | count: 25
           | offset: 0
           | query:
           |     EquityQuery(AND, [
           |       EquityQuery(EQ, ['region', 'us']),
           |       EquityQuery(GT, ['intradayprice', 1]),
           |       EquityQuery(GT, ['avgdailyvol3m', 200000])
           |     ])
           | sortField: short_percentage_of_shares_outstanding.value
           | sortType: DESC
       * - small_cap_gainers
         - | query:
           |     EquityQuery(AND, [
           |       EquityQuery(LT, ['intradaymarketcap', 2000000000]),
           |       EquityQuery(IS-IN, ['exchange', 'NMS', 'NYQ'])
           |     ])
           | sortField: eodvolume
           | sortType: desc
       * - undervalued_growth_stocks
         - | query:
           |     EquityQuery(AND, [
           |       EquityQuery(BTWN, ['peratio.lasttwelvemonths', 0, 20]),
           |       EquityQuery(LT, ['pegratio_5y', 1]),
           |       EquityQuery(GTE, ['epsgrowth.lasttwelvemonths', 25]),
           |       EquityQuery(IS-IN, ['exchange', 'NMS', 'NYQ'])
           |     ])
           | sortField: eodvolume
           | sortType: DESC
       * - undervalued_large_caps
         - | query:
           |     EquityQuery(AND, [
           |       EquityQuery(BTWN, ['peratio.lasttwelvemonths', 0, 20]),
           |       EquityQuery(LT, ['pegratio_5y', 1]),
           |       EquityQuery(BTWN, ['intradaymarketcap', 10000000000, 100000000000]),
           |       EquityQuery(IS-IN, ['exchange', 'NMS', 'NYQ'])
           |     ])
           | sortField: eodvolume
           | sortType: desc
       * - conservative_foreign_funds
         - | query:
           |     FundQuery(AND, [
           |       FundQuery(IS-IN, ['categoryname', 'Foreign Large Value', 'Foreign Large Blend', 'Foreign Large Growth', 'Foreign Small/Mid Growth', 'Foreign Small/Mid Blend', 'Foreign Small/Mid Value']),
           |       FundQuery(IS-IN, ['performanceratingoverall', 4, 5]),
           |       FundQuery(LT, ['initialinvestment', 100001]),
           |       FundQuery(LT, ['annualreturnnavy1categoryrank', 50]),
           |       FundQuery(IS-IN, ['riskratingoverall', 1, 2, 3]),
           |       FundQuery(EQ, ['exchange', 'NAS'])
           |     ])
           | sortField: fundnetassets
           | sortType: DESC
       * - high_yield_bond
         - | query:
           |     FundQuery(AND, [
           |       FundQuery(IS-IN, ['performanceratingoverall', 4, 5]),
           |       FundQuery(LT, ['initialinvestment', 100001]),
           |       FundQuery(LT, ['annualreturnnavy1categoryrank', 50]),
           |       FundQuery(IS-IN, ['riskratingoverall', 1, 2, 3]),
           |       FundQuery(EQ, ['categoryname', 'High Yield Bond']),
           |       FundQuery(EQ, ['exchange', 'NAS'])
           |     ])
           | sortField: fundnetassets
           | sortType: DESC
       * - portfolio_anchors
         - | query:
           |     FundQuery(AND, [
           |       FundQuery(EQ, ['categoryname', 'Large Blend']),
           |       FundQuery(IS-IN, ['performanceratingoverall', 4, 5]),
           |       FundQuery(LT, ['initialinvestment', 100001]),
           |       FundQuery(LT, ['annualreturnnavy1categoryrank', 50]),
           |       FundQuery(EQ, ['exchange', 'NAS'])
           |     ])
           | sortField: fundnetassets
           | sortType: DESC
       * - solid_large_growth_funds
         - | query:
           |     FundQuery(AND, [
           |       FundQuery(EQ, ['categoryname', 'Large Growth']),
           |       FundQuery(IS-IN, ['performanceratingoverall', 4, 5]),
           |       FundQuery(LT, ['initialinvestment', 100001]),
           |       FundQuery(LT, ['annualreturnnavy1categoryrank', 50]),
           |       FundQuery(EQ, ['exchange', 'NAS'])
           |     ])
           | sortField: fundnetassets
           | sortType: DESC
       * - solid_midcap_growth_funds
         - | query:
           |     FundQuery(AND, [
           |       FundQuery(EQ, ['categoryname', 'Mid-Cap Growth']),
           |       FundQuery(IS-IN, ['performanceratingoverall', 4, 5]),
           |       FundQuery(LT, ['initialinvestment', 100001]),
           |       FundQuery(LT, ['annualreturnnavy1categoryrank', 50]),
           |       FundQuery(EQ, ['exchange', 'NAS'])
           |     ])
           | sortField: fundnetassets
           | sortType: DESC
       * - top_mutual_funds
         - | query:
           |     FundQuery(AND, [
           |       FundQuery(GT, ['intradayprice', 15]),
           |       FundQuery(IS-IN, ['performanceratingoverall', 4, 5]),
           |       FundQuery(GT, ['initialinvestment', 1000]),
           |       FundQuery(EQ, ['exchange', 'NAS'])
           |     ])
           | sortField: percentchange
           | sortType: DESC

