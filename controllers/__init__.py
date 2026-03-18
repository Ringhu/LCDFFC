"""Controller module: QP-MPC and safe fallback strategies."""


def __getattr__(name):
    if name == "QPController":
        from controllers.qp_controller import QPController
        return QPController
    if name == "SafeFallback":
        from controllers.safe_fallback import SafeFallback
        return SafeFallback
    raise AttributeError(f"module 'controllers' has no attribute {name!r}")


__all__ = ["QPController", "SafeFallback"]
