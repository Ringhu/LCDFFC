"""Safe fallback controller: conservative strategy when QP fails or is untrusted."""

import numpy as np


class SafeFallback:
    """Conservative fallback that does nothing (zero action) or follows simple rules.

    Used when:
    - QP solver returns infeasible
    - Forecast confidence is too low
    - LLM router signals uncertainty
    """

    def act(self, state: dict, **kwargs) -> np.ndarray:
        """Return a safe (zero) action.

        Args:
            state: Current state dict.

        Returns:
            Zero action array (do nothing).
        """
        num_buildings = len(state.get("soc", [0]))
        return np.zeros(num_buildings)
