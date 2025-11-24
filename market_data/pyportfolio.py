# Import packages
from pypfopt.expected_returns import (
    mean_historical_return,
    capm_return,
    ema_historical_return,
)
from pypfopt.risk_models import CovarianceShrinkage, semicovariance, exp_cov, sample_cov
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt import DiscreteAllocation, get_latest_prices, objective_functions
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Import local modules
import PortfolioBuilder as pb


def get_company_tickers_json_path(
    filename: str = "company_tickers_with_sic.json",
) -> Path:
    """Return Path to company_tickers_with_sic.json located next to this module."""
    return Path(__file__).parent / filename


# %% Portfolio Optimizer Class


class PortfolioOptimizer:
    """
    A portfolio optimization class that manages expected returns, covariance matrices,
    and portfolio optimization strategies with automatic risk-free rate management.

    Attributes:
        data: Price data for the portfolio assets
        rf_rate: Risk-free rate for calculations (automatically fetched or manually set)
        holding_period: Treasury holding period for risk-free rate calculation
        period: Corresponding period for yfinance API calls (e.g., plotting)
    """

    # Valid holding periods for risk-free rate fetching
    VALID_HOLDING_PERIODS = [
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
    ]

    def __init__(self, data, holding_period="1 Mo", rf_rate=None):
        """
        Initialize the PortfolioOptimizer with price data and risk-free rate.

        Args:
            data: DataFrame with asset price data
            holding_period: Period for treasury rate - must be one of:
                           ['1 Mo', '3 Mo', '6 Mo', '1 Yr', '2 Yr', '3 Yr', '5 Yr', '7 Yr', '10 Yr', '30 Yr']
            rf_rate: Manual risk-free rate override (if None, will fetch automatically)
        """
        # Validate holding period
        if holding_period not in self.VALID_HOLDING_PERIODS:
            raise ValueError(
                f"holding_period must be one of {self.VALID_HOLDING_PERIODS}"
            )

        self.data = data
        self.holding_period = holding_period
        self.period = self._convert_holding_period_to_yf_period(holding_period)

        # Fetch or set risk-free rate
        if rf_rate is None:
            self.rf_rate = self._fetch_rf_rate()
        else:
            self.rf_rate = rf_rate

    def _fetch_rf_rate(self):
        """Fetch the risk-free rate from market data."""
        try:
            rf = pb.get_riskfree_rate(self.data, holding_period=self.holding_period)
            if rf is None or pd.isna(rf):
                print(f"Warning: Risk-free rate returned None/NaN. Using default 0.02.")
                return 0.02
            print(f"Fetched risk-free rate: {rf:.4f} for {self.holding_period}")
            return rf
        except Exception as e:
            print(
                f"Warning: Could not fetch risk-free rate. Using default 0.02. Error: {e}"
            )
            return 0.02

    @staticmethod
    def _convert_holding_period_to_yf_period(holding_period):
        """
        Convert holding period format to yfinance period format.

        Args:
            holding_period: Period in treasury format (e.g., '1 Mo', '1 Yr', '10 Yr')

        Returns:
            Period in yfinance format (e.g., '1mo', '1y', '10y')
        """
        # Mapping from treasury format to yfinance format
        period_map = {
            "1 Mo": "1mo",
            "3 Mo": "3mo",
            "6 Mo": "6mo",
            "1 Yr": "1y",
            "2 Yr": "2y",
            "3 Yr": "3y",
            "5 Yr": "5y",
            "7 Yr": "7y",
            "10 Yr": "10y",
            "30 Yr": "30y",
        }
        return period_map.get(holding_period, "1mo")

    def set_rf_rate(self, rf_rate):
        """Manually update the risk-free rate."""
        self.rf_rate = rf_rate

    def set_holding_period(self, holding_period):
        """
        Update the holding period and corresponding plot period.
        This will also refetch the risk-free rate.

        Args:
            holding_period: New holding period - must be one of VALID_HOLDING_PERIODS
        """
        if holding_period not in self.VALID_HOLDING_PERIODS:
            raise ValueError(
                f"holding_period must be one of {self.VALID_HOLDING_PERIODS}"
            )

        self.holding_period = holding_period
        self.period = self._convert_holding_period_to_yf_period(holding_period)
        self.rf_rate = self._fetch_rf_rate()

    def get_period(self):
        """Get the yfinance period corresponding to the holding period."""
        return self.period

    def get_rf_rate(self):
        """Get the current risk-free rate."""
        return self.rf_rate

    def get_expected_returns(self, type="mean"):
        """
        Calculate expected returns using various methods.

        Args:
            type: Method to use - 'mean', 'capm', or 'ema'

        Returns:
            Series of expected returns for each asset
        """
        if type == "mean":
            mu = mean_historical_return(self.data)
        elif type == "capm":
            mu = capm_return(self.data)
        elif type == "ema":
            mu = ema_historical_return(self.data)
        else:
            raise ValueError("Invalid type. Use 'mean', 'capm', or 'ema'.")
        return mu

    def get_covariance_matrix(self, type="ledoit_wolf", freq=252):
        """
        Calculate the covariance matrix using various methods.

        Args:
            type: Method to use - 'ledoit_wolf', 'semicovariance', or 'exponential'
            freq: Number of trading periods in a year (default 252 for daily data)

        Returns:
            Covariance matrix DataFrame
        """
        if type == "ledoit_wolf":
            S = CovarianceShrinkage(self.data, frequency=freq).ledoit_wolf()
        elif type == "semicovariance":
            # gets downside risk only
            S = semicovariance(self.data, frequency=freq)
        elif type == "exponential":
            S = exp_cov(self.data, frequency=freq)
        else:
            raise ValueError(
                "Invalid type. Use 'ledoit_wolf', 'semicovariance', or 'exponential'."
            )
        return S

    def get_weights(
        self, mu, S, round=True, method="max_sharpe", target=None, solver="ECOS"
    ):
        """
        Calculate optimal portfolio weights using the specified method.

        Args:
            mu: Expected returns (from get_expected_returns)
            S: Covariance matrix (from get_covariance_matrix)
            round: Whether to round and clean weights
            method: Optimization method - 'max_sharpe', 'min_volatility', 'efficient_return', 'efficient_risk'
            target: Target return (for efficient_return) or target risk (for efficient_risk)
            solver: Solver to use ('ECOS', 'SCS', 'OSQP', etc.) - ECOS is more reliable for portfolios

        Returns:
            Tuple of (portfolio_obj, weights, cleaned_weights)
        """
        try:
            portfolio_obj = EfficientFrontier(mu, S, solver=solver)
            if method != "max_sharpe":
                portfolio_obj.add_objective(objective_functions.L2_reg, gamma=0.1)

            if method == "max_sharpe":
                weights = portfolio_obj.max_sharpe(risk_free_rate=self.rf_rate)
            elif method == "min_volatility":
                weights = portfolio_obj.min_volatility()
            elif method == "efficient_return":
                target_return = target
                # min vol for a given return
                weights = portfolio_obj.efficient_return(target_return=target_return)
            elif method == "efficient_risk":
                target_risk = target
                # max return for a given risk
                weights = portfolio_obj.efficient_risk(target_risk=target_risk)
            else:
                raise ValueError(
                    "Invalid method. Currently only 'max_sharpe', 'min_volatility', 'efficient_return', and 'efficient_risk' are supported."
                )

            if round:
                weights = portfolio_obj.clean_weights(cutoff=1e-4, rounding=3)
            wts = {k: v for k, v in weights.items() if v != 0}
            return portfolio_obj, weights, wts

        except Exception as e:
            print("\n" + "=" * 60)
            print("OPTIMIZATION ERROR - Diagnostics:")
            print("=" * 60)
            print(f"Method: {method}")
            print(f"Solver: {solver}")
            print(f"Risk-free rate: {self.rf_rate}")
            print(f"Number of assets: {len(mu)}")
            print(f"Expected returns range: [{mu.min():.4f}, {mu.max():.4f}]")
            print(f"Expected returns mean: {mu.mean():.4f}")
            print(f"Any NaN in returns? {mu.isna().any()}")
            print(f"Any NaN in covariance? {np.isnan(S).any()}")
            print(f"\nSuggestions:")
            print(f"  1. Try 'min_volatility' method instead of 'max_sharpe'")
            print(f"  2. Use longer data period (e.g., '2 Yr' or more)")
            print(f"  3. Try different solver: solver='SCS' or solver='OSQP'")
            print(f"  4. Reduce number of stocks with insufficient data")
            print("=" * 60)
            raise

    def get_performance(self, mu, S, round=True, method="max_sharpe"):
        """
        Calculate portfolio performance metrics.

        Args:
            mu: Expected returns
            S: Covariance matrix
            round: Whether to round and clean weights
            method: Optimization method

        Returns:
            Tuple of (performance_metrics, weights, cleaned_weights)
        """
        portfolio_obj, weights, wts = self.get_weights(
            mu, S, round=round, method=method
        )
        performance = portfolio_obj.portfolio_performance(
            verbose=True, risk_free_rate=self.rf_rate
        )
        return performance, weights, wts

    def get_allocation(self, weights, port_value):
        """
        Calculate discrete allocation of shares based on portfolio value.

        Args:
            weights: Portfolio weights (from get_weights)
            port_value: Total portfolio value in USD

        Returns:
            Dictionary of share allocations
        """
        latest_prices = get_latest_prices(self.data)
        da = DiscreteAllocation(
            weights, latest_prices, total_portfolio_value=port_value
        )
        allocation, leftover = da.lp_portfolio(verbose=True)
        return allocation

    def plot_returns_vs_sp500(
        self,
        weights,
        index_symbol="^GSPC",
        start=None,
        end=None,
        period=None,
        interval="1d",
    ):
        """
        Plot portfolio returns vs S&P 500 and calculate performance metrics.
        Uses the holding_period by default (converted to yfinance format).

        Args:
            weights: Portfolio weights
            index_symbol: S&P 500 symbol (default '^GSPC')
            start: Start date for comparison (optional - shifts the period window)
            end: End date for comparison (optional - shifts the period window)
            period: Data period (if None, uses the instance's holding_period converted to yfinance format)
                   Must match one of the valid holding periods: ['1mo', '3mo', '6mo', '1y', '2y', '3y', '5y', '7y', '10y', '30y']
            interval: Data interval (default '1d')

        Note:
            yfinance rules: Can use period with EITHER start OR end, but NOT both.
            - period only: fetches recent data for that period
            - start + period: fetches 'period' length starting from start date
            - end + period: fetches 'period' length ending at end date
            - start + end (no period): fetches exact date range
        """
        # Validate parameter combinations (yfinance constraint)
        if start is not None and end is not None and period is not None:
            raise ValueError(
                "Cannot specify all three parameters (start, end, period). "
                "Use period with EITHER start OR end, or use start+end without period."
            )

        # Use instance period if not specified and no date range provided
        if period is None and start is None and end is None:
            period = self.period

        # Validate that period matches our accepted formats (if provided)
        if period is not None:
            valid_periods = [
                "1mo",
                "3mo",
                "6mo",
                "1y",
                "2y",
                "3y",
                "5y",
                "7y",
                "10y",
                "30y",
            ]
            if period not in valid_periods:
                raise ValueError(
                    f"period must be one of {valid_periods} or None (to use holding_period)"
                )

        sp = pb.get_closingPrice_list(
            ticker_list=index_symbol,
            start=start,
            end=end,
            period=period,
            interval=interval,
        )
        sp_returns = sp.pct_change().dropna()
        portfolio_returns = (
            (self.data.pct_change() * pd.Series(weights)).sum(axis=1).dropna()
        )

        combined = pd.DataFrame(
            {"S&P 500": sp_returns[index_symbol], "Portfolio": portfolio_returns}
        ).dropna()
        cumulative_returns = (1 + combined).cumprod()

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
        plt.show()

        # Calculate drawdown, sharpe ratio
        for col in cumulative_returns.columns:
            cumulative_max = cumulative_returns[col].cummax()
            drawdown = (cumulative_returns[col] - cumulative_max) / cumulative_max
            max_drawdown = drawdown.min()
            volatility = np.std(cumulative_returns[col]) * np.sqrt(252)
            mean_returns = np.mean(cumulative_returns[col])
            sharpe_ratio = (mean_returns - self.rf_rate) / volatility

            print(f"{col}:")
            print(f"  Drawdown: {max_drawdown:.2%}")
            print(f"  Volatility (ann.): {volatility:.2%}")
            print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")

        return
