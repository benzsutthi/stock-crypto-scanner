"""Validate daily OHLCV before calculating any technical signals."""
import numpy as np
import pandas as pd


def clean_history(frame):
    required = ['Close', 'High', 'Low', 'Volume']
    if frame.empty or any(c not in frame.columns for c in required):
        return pd.DataFrame()
    frame = frame.copy()
    frame.index = pd.to_datetime(frame.index, errors='coerce')
    frame = frame.loc[~frame.index.isna()]
    frame = frame[~frame.index.duplicated(keep='last')].sort_index()
    for col in required:
        frame[col] = pd.to_numeric(frame[col], errors='coerce')
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=required)
    valid = ((frame.Close > 0) & (frame.Low > 0) & (frame.Volume >= 0)
             & (frame.High >= frame.Close) & (frame.Low <= frame.Close))
    return frame.loc[valid]
