"""
Black-Scholes Option Pricing & Greeks Calculator

Computes Implied Volatility (IV) using Newton-Raphson, then derives
Delta, Gamma, Theta, and Vega for European-style options.

Indian stock options (NSE F&O) are European-style, making Black-Scholes
the appropriate model.

Risk-free rate: 5.25% (RBI repo rate as of Feb 2026)
"""

import math
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# RBI repo rate (Feb 2026)
RISK_FREE_RATE = 0.0525


def _norm_cdf(x):
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x):
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _d1(S, K, T, r, sigma):
    """Calculate d1 in Black-Scholes formula."""
    return (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))


def _d2(S, K, T, r, sigma):
    """Calculate d2 in Black-Scholes formula."""
    return _d1(S, K, T, r, sigma) - sigma * math.sqrt(T)


def bs_price(S, K, T, r, sigma, option_type="CE"):
    """
    Black-Scholes option price.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate (decimal)
        sigma: Volatility (decimal, e.g. 0.25 = 25%)
        option_type: "CE" for Call, "PE" for Put
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    
    d1 = _d1(S, K, T, r, sigma)
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type == "CE":
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def compute_iv(option_price, S, K, T, r=RISK_FREE_RATE, option_type="CE",
               max_iterations=100, tolerance=1e-6):
    """
    Compute Implied Volatility using Newton-Raphson method.
    
    Args:
        option_price: Market price of the option
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        option_type: "CE" or "PE"
        max_iterations: Max Newton-Raphson iterations
        tolerance: Convergence tolerance
        
    Returns:
        IV as decimal (e.g. 0.25 = 25%), or 0 if computation fails
    """
    if option_price <= 0 or S <= 0 or K <= 0 or T <= 0:
        return 0.0
    
    # Check for intrinsic value floor
    if option_type == "CE":
        intrinsic = max(S - K * math.exp(-r * T), 0)
    else:
        intrinsic = max(K * math.exp(-r * T) - S, 0)
    
    if option_price < intrinsic:
        return 0.0
    
    # Initial guess: use Brenner-Subrahmanyam approximation
    sigma = math.sqrt(2.0 * math.pi / T) * (option_price / S)
    sigma = max(min(sigma, 5.0), 0.01)  # Clamp to reasonable range
    
    for i in range(max_iterations):
        try:
            price = bs_price(S, K, T, r, sigma, option_type)
            diff = price - option_price
            
            if abs(diff) < tolerance:
                return sigma
            
            # Vega for Newton-Raphson step
            d1 = _d1(S, K, T, r, sigma)
            vega = S * _norm_pdf(d1) * math.sqrt(T)
            
            if vega < 1e-10:
                break
            
            sigma = sigma - diff / vega
            
            # Keep sigma in reasonable bounds
            if sigma <= 0.001:
                sigma = 0.001
            elif sigma > 5.0:
                sigma = 5.0
                
        except (ValueError, OverflowError, ZeroDivisionError):
            break
    
    # If Newton-Raphson didn't converge, try bisection as fallback
    return _bisection_iv(option_price, S, K, T, r, option_type)


def _bisection_iv(option_price, S, K, T, r, option_type, 
                  low=0.001, high=5.0, max_iterations=100, tolerance=1e-6):
    """Bisection method fallback for IV when Newton-Raphson fails."""
    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        price = bs_price(S, K, T, r, mid, option_type)
        
        if abs(price - option_price) < tolerance:
            return mid
        
        if price > option_price:
            high = mid
        else:
            low = mid
    
    return (low + high) / 2.0


def compute_greeks(S, K, T, r=RISK_FREE_RATE, sigma=None, option_type="CE",
                   option_price=None):
    """
    Compute all Greeks for an option.
    
    If sigma (IV) is not provided, it will be computed from option_price.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        sigma: Implied volatility (if already known)
        option_type: "CE" or "PE"
        option_price: Market price (used to compute IV if sigma not given)
        
    Returns:
        dict with keys: iv, delta, gamma, theta, vega
        All values as floats. IV and Greeks expressed as:
        - iv: percentage (e.g. 25.0 for 25%)
        - delta: -1 to +1
        - gamma: per unit
        - theta: per day (negative = decay)
        - vega: per 1% change in IV
    """
    result = {"iv": 0, "delta": 0, "gamma": 0, "theta": 0, "vega": 0}
    
    if S <= 0 or K <= 0 or T <= 0:
        return result
    
    # Compute IV if not given
    if sigma is None:
        if option_price is None or option_price <= 0:
            return result
        sigma = compute_iv(option_price, S, K, T, r, option_type)
    
    if sigma <= 0:
        return result
    
    try:
        sqrt_T = math.sqrt(T)
        d1 = _d1(S, K, T, r, sigma)
        d2 = d1 - sigma * sqrt_T
        
        # Delta
        if option_type == "CE":
            delta = _norm_cdf(d1)
        else:
            delta = _norm_cdf(d1) - 1.0
        
        # Gamma (same for calls and puts)
        gamma = _norm_pdf(d1) / (S * sigma * sqrt_T)
        
        # Theta (per day)
        first_term = -(S * _norm_pdf(d1) * sigma) / (2.0 * sqrt_T)
        if option_type == "CE":
            theta = first_term - r * K * math.exp(-r * T) * _norm_cdf(d2)
        else:
            theta = first_term + r * K * math.exp(-r * T) * _norm_cdf(-d2)
        theta = theta / 365.0  # Convert to per-day
        
        # Vega (per 1% change in IV)
        vega = S * _norm_pdf(d1) * sqrt_T / 100.0
        
        result = {
            "iv": round(sigma * 100, 2),      # as percentage
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 2),
            "vega": round(vega, 2),
        }
    except (ValueError, OverflowError, ZeroDivisionError) as e:
        logger.warning(f"Greeks computation error for S={S}, K={K}, T={T}, σ={sigma}: {e}")
    
    return result


def parse_expiry_to_T(expiry_str: str) -> float:
    """
    Convert expiry string (e.g. '24FEB2026') to time-to-expiry in years.
    
    Uses calendar days / 365.
    """
    try:
        expiry_date = datetime.strptime(expiry_str, "%d%b%Y").date()
        today = datetime.now().date()
        days = (expiry_date - today).days
        
        if days <= 0:
            return 1.0 / 365.0  # Minimum 1 day for expiry-day calculations
        
        return days / 365.0
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to parse expiry '{expiry_str}': {e}")
        return 0.0
