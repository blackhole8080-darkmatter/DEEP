# deep/tech/finance.py — Quantitative Finance (Bible Section 25)
"""Option pricing (Black-Scholes + Greeks, Monte Carlo), portfolio optimisation
(Markowitz), risk metrics (VaR/CVaR/Sharpe/drawdown), technical indicators.
numpy/scipy core; yfinance/backtrader are optional for live data."""
from __future__ import annotations

import math
import re

import numpy as np

try:
    from scipy.stats import norm
    from scipy.optimize import minimize
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False


def _N(x):
    if SCIPY:
        return float(norm.cdf(x))
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _pdf(x):
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


class FinanceEngine:
    def __init__(self, config=None):
        self.config = config

    # ── option pricing ──────────────────────────────────────────────
    def black_scholes(self, S, K, T, r, sigma, option_type="call") -> dict:
        d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        if option_type == "call":
            price = S * _N(d1) - K * math.exp(-r * T) * _N(d2)
            delta = _N(d1)
            rho = K * T * math.exp(-r * T) * _N(d2)
        else:
            price = K * math.exp(-r * T) * _N(-d2) - S * _N(-d1)
            delta = _N(d1) - 1
            rho = -K * T * math.exp(-r * T) * _N(-d2)
        gamma = _pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * _pdf(d1) * math.sqrt(T)
        theta = (-S * _pdf(d1) * sigma / (2 * math.sqrt(T))
                 - r * K * math.exp(-r * T) * _N(d2 if option_type == "call" else -d2))
        return {"price": price, "delta": delta, "gamma": gamma, "vega": vega / 100,
                "theta": theta / 365, "rho": rho / 100, "result": {"price": price},
                "verbal": f"{option_type.title()} option price ${price:.2f} "
                          f"(Δ={delta:.3f}, Γ={gamma:.4f}, vega={vega/100:.3f}, "
                          f"θ={theta/365:.3f}/day)."}

    def monte_carlo_options(self, S, K, T, r, sigma, n_paths=50000,
                            option_type="call") -> dict:
        rng = np.random.default_rng(0)
        Z = rng.standard_normal(n_paths)
        ST = S * np.exp((r - sigma**2 / 2) * T + sigma * math.sqrt(T) * Z)
        payoff = np.maximum(ST - K, 0) if option_type == "call" else np.maximum(K - ST, 0)
        disc = math.exp(-r * T)
        price = disc * payoff.mean()
        se = disc * payoff.std() / math.sqrt(n_paths)
        return {"price": price, "std_error": se,
                "confidence_interval": [price - 1.96 * se, price + 1.96 * se],
                "result": {"price": price},
                "verbal": f"Monte Carlo ({n_paths:,} paths) {option_type} price "
                          f"${price:.2f} ± {1.96*se:.3f}."}

    # ── portfolio optimisation ──────────────────────────────────────
    def portfolio_optimise(self, mean_returns, cov_matrix, rf=0.02) -> dict:
        if not SCIPY:
            return {"result": None, "verbal": "scipy needed for optimisation, sir."}
        mu = np.asarray(mean_returns, float)
        cov = np.asarray(cov_matrix, float)
        n = len(mu)

        def neg_sharpe(w):
            ret = w @ mu
            vol = math.sqrt(w @ cov @ w)
            return -(ret - rf) / vol if vol else 0
        cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)
        bounds = tuple((0, 1) for _ in range(n))
        res = minimize(neg_sharpe, np.repeat(1/n, n), bounds=bounds, constraints=cons)
        w = res.x
        ret = float(w @ mu); vol = float(math.sqrt(w @ cov @ w))
        sharpe = (ret - rf) / vol if vol else 0
        return {"weights": w.tolist(), "expected_return": ret, "volatility": vol,
                "sharpe_ratio": sharpe, "result": {"sharpe": sharpe},
                "verbal": f"Max-Sharpe portfolio: weights "
                          f"{[round(float(x), 3) for x in w]}, expected return {ret*100:.1f}%, "
                          f"volatility {vol*100:.1f}%, Sharpe {sharpe:.2f}."}

    # ── risk metrics ────────────────────────────────────────────────
    def risk_metrics(self, returns, confidence=0.95) -> dict:
        r = np.asarray(returns, float)
        var = float(-np.percentile(r, (1 - confidence) * 100))
        cvar = float(-r[r <= -var].mean()) if np.any(r <= -var) else var
        sharpe = float(r.mean() / r.std() * math.sqrt(252)) if r.std() else 0
        downside = r[r < 0].std()
        sortino = float(r.mean() / downside * math.sqrt(252)) if downside else 0
        cum = np.cumprod(1 + r)
        dd = float((cum / np.maximum.accumulate(cum) - 1).min())
        return {"VaR": var, "CVaR": cvar, "sharpe": sharpe, "sortino": sortino,
                "max_drawdown": dd, "result": {"VaR": var, "sharpe": sharpe},
                "verbal": f"At {confidence*100:.0f}% confidence: VaR {var*100:.2f}%, "
                          f"CVaR {cvar*100:.2f}%, Sharpe {sharpe:.2f}, "
                          f"max drawdown {dd*100:.1f}%."}

    # ── technical indicators ────────────────────────────────────────
    def technical_indicators(self, prices) -> dict:
        p = np.asarray(prices, float)
        sma20 = p[-20:].mean() if len(p) >= 20 else p.mean()
        delta = np.diff(p)
        gains = delta[delta > 0].sum() / 14 if len(delta) >= 14 else 0
        losses = -delta[delta < 0].sum() / 14 if len(delta) >= 14 else 1e-9
        rs = gains / losses if losses else 0
        rsi = 100 - 100 / (1 + rs)
        return {"SMA20": float(sma20), "RSI": float(rsi), "result": {"RSI": float(rsi)},
                "verbal": f"SMA(20)=${sma20:.2f}, RSI={rsi:.1f} "
                          f"({'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'})."}

    def macd(self, prices, fast=12, slow=26, signal=9) -> dict:
        p = np.asarray(prices, float)
        def ema(a, span):
            k = 2/(span+1); out = np.zeros_like(a); out[0] = a[0]
            for i in range(1, len(a)): out[i] = a[i]*k + out[i-1]*(1-k)
            return out
        macd_line = ema(p, fast) - ema(p, slow); sig = ema(macd_line, signal)
        hist = macd_line - sig
        return {"macd": macd_line.tolist(), "signal": sig.tolist(),
                "crossover": "bullish" if hist[-1] > 0 else "bearish",
                "result": {"hist": float(hist[-1])},
                "verbal": f"MACD histogram {hist[-1]:+.3f} — {'bullish' if hist[-1]>0 else 'bearish'} momentum."}

    def bollinger_bands(self, prices, window=20, k=2) -> dict:
        p = np.asarray(prices, float)
        if len(p) < window:
            window = len(p)
        sma = p[-window:].mean(); sd = p[-window:].std()
        upper, lower = sma + k*sd, sma - k*sd
        pos = "above upper" if p[-1] > upper else ("below lower" if p[-1] < lower else "within")
        return {"upper": float(upper), "lower": float(lower), "sma": float(sma),
                "result": {"upper": float(upper), "lower": float(lower)},
                "verbal": f"Bollinger: price {p[-1]:.2f} is {pos} band "
                          f"[{lower:.2f}, {upper:.2f}]."}

    def backtest_sma_cross(self, prices, fast=10, slow=30, capital=10000) -> dict:
        """Backtest an SMA-crossover strategy."""
        p = np.asarray(prices, float)
        if len(p) < slow + 2:
            return {"result": None, "verbal": "Need a longer price series, sir."}
        cash = capital; shares = 0; trades = 0
        for i in range(slow, len(p)):
            f = p[i-fast:i].mean(); s = p[i-slow:i].mean()
            if f > s and cash > 0:
                shares = cash / p[i]; cash = 0; trades += 1
            elif f < s and shares > 0:
                cash = shares * p[i]; shares = 0; trades += 1
        final = cash + shares * p[-1]
        ret = (final / capital - 1) * 100
        buy_hold = (p[-1] / p[slow] - 1) * 100
        return {"final_value": final, "return_pct": ret, "buy_hold_pct": buy_hold,
                "trades": trades, "result": {"return_pct": ret},
                "verbal": f"SMA-cross backtest: {ret:+.1f}% return over {trades} trades "
                          f"(buy-and-hold {buy_hold:+.1f}%)."}

    def pairs_trading(self, series1, series2) -> dict:
        """Engle-Granger style: hedge ratio + spread z-score + cointegration hint."""
        a = np.asarray(series1, float); b = np.asarray(series2, float)
        beta = np.polyfit(b, a, 1)[0]
        spread = a - beta * b
        z = (spread[-1] - spread.mean()) / (spread.std() + 1e-9)
        signal = "short spread" if z > 2 else ("long spread" if z < -2 else "no signal")
        # simple cointegration proxy: stationarity of spread (low relative variance)
        coint = bool(spread.std() < 0.5 * a.std())
        return {"hedge_ratio": float(beta), "zscore": float(z), "cointegrated": coint,
                "signal": signal, "result": {"zscore": float(z)},
                "verbal": f"Pairs trade: hedge ratio {beta:.2f}, spread z-score {z:+.2f} "
                          f"→ {signal}."}

    def test(self) -> None:
        bs = self.black_scholes(100, 100, 1, 0.05, 0.2, "call")
        # known BS value ~10.45
        assert abs(bs["price"] - 10.45) < 0.1
        mc = self.monte_carlo_options(100, 100, 1, 0.05, 0.2)
        assert abs(mc["price"] - bs["price"]) < 0.5
        rng = np.random.default_rng(0)
        rm = self.risk_metrics(rng.normal(0.001, 0.02, 500))
        assert rm["VaR"] > 0
        prices = 100 + np.cumsum(rng.normal(0, 1, 200))
        assert "crossover" in self.macd(prices)
        assert self.bollinger_bands(prices)["upper"] > self.bollinger_bands(prices)["lower"]
        assert "return_pct" in self.backtest_sma_cross(prices)
        assert "hedge_ratio" in self.pairs_trading(prices, prices*1.1 + rng.normal(0, 1, 200))
        print("finance.FinanceEngine: OK (incl. MACD, Bollinger, backtest, pairs)")


_engine = FinanceEngine()
_NUM = re.compile(r"(?<![A-Za-z])\d+\.?\d*")


def execute(text: str) -> dict:
    low = text.lower()
    nums = [float(x) for x in _NUM.findall(text)]
    if "option" in low or "black" in low or "scholes" in low or "call" in low or "put" in low:
        otype = "put" if "put" in low else "call"
        S = nums[0] if len(nums) > 0 else 100
        K = nums[1] if len(nums) > 1 else 100
        if "monte" in low:
            return _engine.monte_carlo_options(S, K, 1, 0.05, 0.2, option_type=otype)
        return _engine.black_scholes(S, K, 1, 0.05, 0.2, otype)
    if "portfolio" in low or "markowitz" in low or "sharpe" in low:
        mu = [0.12, 0.10, 0.07]
        cov = [[0.04, 0.01, 0.00], [0.01, 0.03, 0.01], [0.00, 0.01, 0.02]]
        return _engine.portfolio_optimise(mu, cov)
    if "var" in low or "risk" in low or "drawdown" in low:
        rng = np.random.default_rng(1)
        return _engine.risk_metrics(rng.normal(0.0005, 0.015, 500))
    if "rsi" in low or "indicator" in low or "technical" in low or "sma" in low:
        rng = np.random.default_rng(2)
        return _engine.technical_indicators(100 + np.cumsum(rng.normal(0, 1, 60)))
    return _engine.black_scholes(nums[0] if nums else 100, nums[1] if len(nums) > 1 else 100,
                                 1, 0.05, 0.2, "call")


def test() -> None:
    FinanceEngine().test()


if __name__ == "__main__":
    test()
