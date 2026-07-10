"""
signal_processor.py

Stateless signal processing functions shared by the live VisPy view and
the offline Matplotlib view, so both paths always show identical results
for a given mode.

Defaults used here (document these in the README as required):
    FS          = 2000 Hz   (sampling rate — confirm against your actual
                              recording's device_information; adjust the
                              `fs` argument per-call if it differs)
    Bandpass    = 10-500 Hz, 4th-order Butterworth
    RMS window  = 100 samples

NOTE: these functions are meant to be applied to a *window* of data (the
rolling buffer or the full recording), not to a single raw 18-sample
packet — filtfilt needs enough samples to build its padding, and a
100-sample RMS window needs at least 100 samples to mean anything.
"""

import numpy as np
from scipy.signal import butter, filtfilt

FS = 2000
LOWCUT_HZ = 10
HIGHCUT_HZ = 500
FILTER_ORDER = 4
RMS_WINDOW = 100

VALID_MODES = ("original", "filtered", "rms")


def bandpass_filter(data: np.ndarray, fs: int = FS, lowcut: float = LOWCUT_HZ,
                     highcut: float = HIGHCUT_HZ, order: int = FILTER_ORDER) -> np.ndarray:
    """
    Zero-phase Butterworth bandpass filter, applied along the last axis.

    Works on both a single channel (1D array) and multiple channels
    (2D array, shape channels x samples).

    Falls back to returning the unfiltered data (with no crash) if the
    signal is too short for filtfilt's padding requirement — this can
    happen right after connecting, before the rolling buffer has filled.
    """
    nyq = fs / 2
    b, a = butter(order, [lowcut / nyq, highcut / nyq], btype="band")

    min_len = 3 * max(len(a), len(b))
    if data.shape[-1] <= min_len:
        return data.copy()

    try:
        return filtfilt(b, a, data, axis=-1)
    except ValueError:
        # Still too short in some edge case — don't crash the GUI over it.
        return data.copy()


def rms_signal(data: np.ndarray, window: int = RMS_WINDOW) -> np.ndarray:
    """
    Moving RMS, applied along the last axis. Works on 1D (single channel)
    or 2D (channels x samples) arrays.
    """
    if data.shape[-1] == 0:
        return data.copy()

    squared = data ** 2
    kernel = np.ones(window) / window

    if data.ndim == 1:
        return np.sqrt(np.convolve(squared, kernel, mode="same"))

    return np.sqrt(
        np.apply_along_axis(lambda ch: np.convolve(ch, kernel, mode="same"), axis=-1, arr=squared)
    )


def process(data: np.ndarray, mode: str, fs: int = FS) -> np.ndarray:
    """
    Apply the requested signal mode.

    mode: one of "original", "filtered", "rms"
    Raises ValueError for an unknown mode, so the ViewModel can catch it
    and show a status message (per the "invalid processing selection"
    error-handling requirement) instead of it propagating as a crash.
    """
    if mode == "original":
        return data
    elif mode == "filtered":
        return bandpass_filter(data, fs=fs)
    elif mode == "rms":
        return rms_signal(data)
    else:
        raise ValueError(f"Unknown signal mode '{mode}', expected one of {VALID_MODES}")