"""
Commodity Pricing Module - Ornstein-Uhlenbeck Mean-Reverting Stochastic Process.

Implements hardcore realistic price fluctuations for materials (Steel, Aluminum, etc.)
that exhibit both random volatility and mean reversion properties.
"""
import math
import random
from typing import List, Dict, Optional
from datetime import datetime


class OrnsteinUhlenbeckPricing:
    """
    Ornstein-Uhlenbeck mean-reverting stochastic process for commodity pricing.
    
    This creates realistic price fluctuations that:
    1. Have random short-term volatility
    2. Tend to revert to a long-term mean price
    3. Never go negative (enforced with floor)
    4. Respond to supply/demand shocks
    
    Mathematical Formula:
        dX_t = θ(μ - X_t)dt + σdW_t
        
        Where:
        - X_t is the current price
        - μ is the long-term mean price
        - θ is the mean reversion speed (higher = faster return to mean)
        - σ is the volatility
        - W_t is a Wiener process (random walk)
        - dt is the time step
    
    Example:
        >>> pricer = OrnsteinUhlenbeckPricing(
        ...     initial_price=5.0,
        ...     long_term_mean=5.5,
        ...     volatility=0.15,
        ...     mean_reversion_speed=0.6
        ... )
        >>> new_price = pricer.step()
        >>> pricer.apply_supply_shock(1.3)  # 30% price spike
    """
    
    def __init__(
        self,
        initial_price: float,
        long_term_mean: float,
        volatility: float = 0.15,
        mean_reversion_speed: float = 0.5,
        dt: float = 1.0,  # Time step (1 = 1 month in our simulation)
        price_floor: float = None,
        price_ceiling: float = None
    ):
        """
        Initialize the OU pricing model.
        
        Args:
            initial_price: Starting price ($/kg typically)
            long_term_mean: Long-term equilibrium price (where price tends to revert)
            volatility: Price volatility (standard deviation of random shocks)
                - 0.08 = Very stable (like Glass)
                - 0.15 = Moderate (like Steel)
                - 0.25 = High (like Oil-linked Plastics)
            mean_reversion_speed: Speed of reversion to mean (0-1)
                - 0.3 = Slow reversion (Electronics - tech deflation)
                - 0.5 = Moderate reversion (Aluminum)
                - 0.7 = Fast reversion (Glass - stable commodity)
            dt: Time step size (1.0 = 1 month in game)
            price_floor: Minimum price (default: 30% of long_term_mean)
            price_ceiling: Maximum price (default: 500% of long_term_mean)
        """
        self.current_price = initial_price
        self.long_term_mean = long_term_mean
        self.volatility = volatility
        self.theta = mean_reversion_speed  # θ in formula
        self.dt = dt
        
        # Safety bounds
        self.price_floor = price_floor or (long_term_mean * 0.3)
        self.price_ceiling = price_ceiling or (long_term_mean * 5.0)
        
        # Price history for analytics
        self.price_history: List[Dict] = [{
            "turn": 0,
            "price": initial_price,
            "timestamp": datetime.utcnow().isoformat()
        }]
    
    def step(self, turn_number: int = None) -> float:
        """
        Advance the price by one time step using the OU process.
        
        Args:
            turn_number: Optional turn number for logging
        
        Returns:
            New price after the step
        """
        # Mean reversion component: pulls price toward long_term_mean
        # The further from mean, the stronger the pull
        drift = self.theta * (self.long_term_mean - self.current_price) * self.dt
        
        # Stochastic component: random market fluctuations
        # Uses Wiener process: dW ~ N(0, sqrt(dt))
        random_shock = self.volatility * random.gauss(0, math.sqrt(self.dt))
        
        # Combine drift and diffusion
        delta_price = drift + random_shock
        new_price = self.current_price + delta_price
        
        # Enforce bounds
        new_price = max(self.price_floor, min(self.price_ceiling, new_price))
        
        self.current_price = new_price
        self.price_history.append({
            "turn": turn_number or len(self.price_history),
            "price": new_price,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return new_price
    
    def apply_supply_shock(self, shock_magnitude: float, reason: str = ""):
        """
        Apply a supply/demand shock to the price.
        
        This simulates sudden market events like:
        - Mining strikes → 1.5-2.0 multiplier
        - Trade embargoes → 1.3-1.8 multiplier
        - Major new mine opening → 0.7-0.85 multiplier
        - Technology breakthrough → 0.5-0.8 multiplier
        
        Args:
            shock_magnitude: Multiplier for the shock
                - 1.5 = 50% price spike
                - 0.7 = 30% price drop
            reason: Human-readable reason for the shock (for event logging)
        """
        old_price = self.current_price
        self.current_price *= shock_magnitude
        
        # Enforce bounds
        self.current_price = max(self.price_floor, min(self.price_ceiling, self.current_price))
        
        self.price_history.append({
            "turn": len(self.price_history),
            "price": self.current_price,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "SUPPLY_SHOCK",
            "reason": reason,
            "magnitude": shock_magnitude,
            "old_price": old_price
        })
    
    def update_long_term_mean(self, new_mean: float, reason: str = ""):
        """
        Update the long-term mean (e.g., due to technology changes, inflation).
        
        This simulates structural changes like:
        - Inflation → increase mean gradually
        - Technology improvement → decrease mean (electronics)
        - Resource scarcity → increase mean
        
        Args:
            new_mean: New long-term equilibrium price
            reason: Reason for the update
        """
        old_mean = self.long_term_mean
        self.long_term_mean = new_mean
        
        # Update bounds proportionally
        self.price_floor = new_mean * 0.3
        self.price_ceiling = new_mean * 5.0
        
        self.price_history.append({
            "turn": len(self.price_history),
            "price": self.current_price,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "MEAN_SHIFT",
            "reason": reason,
            "old_mean": old_mean,
            "new_mean": new_mean
        })
    
    def get_current_deviation(self) -> float:
        """
        Get the current deviation from long-term mean.
        
        Returns:
            Percentage deviation
                - 0.15 = 15% above mean (expensive, buy signal for hoarders)
                - -0.10 = 10% below mean (cheap, sell signal)
                - 0.0 = at equilibrium
        """
        return (self.current_price - self.long_term_mean) / self.long_term_mean
    
    def is_cheap(self, threshold: float = -0.10) -> bool:
        """
        Check if price is significantly below mean (buy signal).
        
        Args:
            threshold: Deviation threshold (default: -10%)
        
        Returns:
            True if price is cheap
        """
        return self.get_current_deviation() < threshold
    
    def is_expensive(self, threshold: float = 0.10) -> bool:
        """
        Check if price is significantly above mean (sell signal).
        
        Args:
            threshold: Deviation threshold (default: +10%)
        
        Returns:
            True if price is expensive
        """
        return self.get_current_deviation() > threshold
    
    def get_price_trend(self, window: int = 12) -> str:
        """
        Analyze recent price trend.
        
        Args:
            window: Number of time steps to analyze (default: 12 months)
        
        Returns:
            "RISING", "FALLING", or "STABLE"
        """
        if len(self.price_history) < window:
            return "STABLE"
        
        recent_entries = self.price_history[-window:]
        prices = [entry["price"] for entry in recent_entries]
        
        start_avg = sum(prices[:window // 2]) / (window // 2)
        end_avg = sum(prices[window // 2:]) / (window - window // 2)
        
        change_percent = (end_avg - start_avg) / start_avg
        
        if change_percent > 0.05:
            return "RISING"
        elif change_percent < -0.05:
            return "FALLING"
        else:
            return "STABLE"
    
    def get_volatility_estimate(self, window: int = 12) -> float:
        """
        Estimate recent price volatility (standard deviation).
        
        Args:
            window: Number of time steps to analyze
        
        Returns:
            Volatility estimate (higher = more volatile)
        """
        if len(self.price_history) < window:
            return 0.0
        
        recent_entries = self.price_history[-window:]
        prices = [entry["price"] for entry in recent_entries]
        
        mean_price = sum(prices) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)
        
        # Normalize by mean price
        return std_dev / mean_price


# Preset configurations for different materials
MATERIAL_PRICING_CONFIGS = {
    "STEEL": {
        "long_term_mean": 1.2,  # $/kg
        "volatility": 0.10,
        "mean_reversion_speed": 0.6,
        "description": "Stable commodity with moderate mean reversion"
    },
    "ALUMINUM": {
        "long_term_mean": 2.8,  # $/kg
        "volatility": 0.15,
        "mean_reversion_speed": 0.5,
        "description": "More volatile, sensitive to energy costs"
    },
    "PLASTIC": {
        "long_term_mean": 1.5,  # $/kg
        "volatility": 0.25,
        "mean_reversion_speed": 0.4,
        "description": "High volatility due to oil price linkage"
    },
    "ELECTRONICS": {
        "long_term_mean": 25.0,  # $/kg
        "volatility": 0.18,
        "mean_reversion_speed": 0.3,
        "description": "Moderate volatility with technology deflation trend"
    },
    "RUBBER": {
        "long_term_mean": 2.0,  # $/kg
        "volatility": 0.20,
        "mean_reversion_speed": 0.5,
        "description": "Commodity-linked with seasonal variations"
    },
    "GLASS": {
        "long_term_mean": 0.8,  # $/kg
        "volatility": 0.08,
        "mean_reversion_speed": 0.7,
        "description": "Very stable, low volatility"
    },
    "COPPER": {
        "long_term_mean": 8.5,  # $/kg
        "volatility": 0.17,
        "mean_reversion_speed": 0.5,
        "description": "Industrial metal with moderate volatility"
    },
    "LITHIUM": {
        "long_term_mean": 45.0,  # $/kg
        "volatility": 0.30,
        "mean_reversion_speed": 0.35,
        "description": "High volatility due to EV demand, speculative market"
    }
}


def create_material_pricer(material_type: str, initial_price: float = None) -> OrnsteinUhlenbeckPricing:
    """
    Factory function to create a pricer for a specific material type.
    
    Args:
        material_type: Material type (e.g., "STEEL", "ALUMINUM")
        initial_price: Override initial price (default: use long_term_mean from config)
    
    Returns:
        Configured OrnsteinUhlenbeckPricing instance
    
    Raises:
        ValueError: If material_type not found in configs
    """
    if material_type not in MATERIAL_PRICING_CONFIGS:
        raise ValueError(f"Unknown material type: {material_type}. "
                       f"Available: {list(MATERIAL_PRICING_CONFIGS.keys())}")
    
    config = MATERIAL_PRICING_CONFIGS[material_type]
    
    return OrnsteinUhlenbeckPricing(
        initial_price=initial_price or config["long_term_mean"],
        long_term_mean=config["long_term_mean"],
        volatility=config["volatility"],
        mean_reversion_speed=config["mean_reversion_speed"]
    )


# Export
__all__ = [
    "OrnsteinUhlenbeckPricing",
    "MATERIAL_PRICING_CONFIGS",
    "create_material_pricer"
]


