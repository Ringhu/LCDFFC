"""KPI metrics for CityLearn evaluation."""

import numpy as np


def compute_cost(electricity_consumption: np.ndarray, prices: np.ndarray) -> float:
    """Total electricity cost."""
    return float(np.sum(electricity_consumption * prices))


def compute_carbon(electricity_consumption: np.ndarray, carbon_intensity: np.ndarray) -> float:
    """Total carbon emissions."""
    return float(np.sum(electricity_consumption * carbon_intensity))


def compute_peak(net_load: np.ndarray) -> float:
    """Peak net electricity demand."""
    return float(np.max(net_load))


def compute_ramping(net_load: np.ndarray) -> float:
    """Sum of absolute changes in net load (ramping penalty)."""
    return float(np.sum(np.abs(np.diff(net_load))))


def compute_all_kpis(
    electricity_consumption: np.ndarray,
    prices: np.ndarray,
    carbon_intensity: np.ndarray,
    net_load: np.ndarray,
) -> dict[str, float]:
    """Compute all KPIs and return as dict."""
    return {
        "cost": compute_cost(electricity_consumption, prices),
        "carbon": compute_carbon(electricity_consumption, carbon_intensity),
        "peak": compute_peak(net_load),
        "ramping": compute_ramping(net_load),
    }
