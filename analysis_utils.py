"""
Utility helpers for analysis.
"""

import pandas as pd
import numpy as np

def safe_mean(series):
    try:
        return float(pd.to_numeric(series, errors='coerce').dropna().mean())
    except Exception:
        return float(np.nan)
