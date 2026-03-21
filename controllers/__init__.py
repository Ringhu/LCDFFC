"""Controller module: QP, non-QP baselines, and safe fallback strategies."""


def __getattr__(name):
    if name == "QPController":
        from controllers.qp_controller import QPController
        return QPController
    if name == "SafeFallback":
        from controllers.safe_fallback import SafeFallback
        return SafeFallback
    if name == "ForecastHeuristicController":
        from controllers.baseline_controllers import ForecastHeuristicController
        return ForecastHeuristicController
    if name == "ActionGridController":
        from controllers.baseline_controllers import ActionGridController
        return ActionGridController
    raise AttributeError(f"module 'controllers' has no attribute {name!r}")


__all__ = [
    "QPController",
    "SafeFallback",
    "ForecastHeuristicController",
    "ActionGridController",
]
