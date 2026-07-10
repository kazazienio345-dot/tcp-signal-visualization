"""
signal_buffer.py

Buffering for streamed EMG/biosignal data.

Two buffers are maintained:
    - A rolling buffer of a fixed window length (in seconds), for the
      live VisPy plot.
    - A full-session buffer that grows for as long as data is streaming,
      for offline Matplotlib inspection after disconnecting.

This class has no knowledge of sockets, byte parsing, or TCP at all — it
only accepts already-reconstructed NumPy packets (channels x samples) and
manages storage. Keeping it separate from TcpClientModel means the
buffering logic can be tested and reasoned about independently of the
network code, and could be reused (e.g. by a future file-replay model)
without dragging socket code along with it.
"""

import numpy as np


class SignalBuffer:
    def __init__(self, channels: int, sampling_rate: int, window_seconds: float,
                 dtype=np.float64):
        self.channels = channels
        self.sampling_rate = sampling_rate
        self.window_seconds = window_seconds
        self.dtype = dtype

        self.window_size = int(sampling_rate * window_seconds)

        # Rolling buffer for the live plot.
        self.data_buffer = np.empty((channels, 0), dtype=dtype)

        # Full-session buffer for offline inspection. Stored as a list of
        # chunks and concatenated on demand (cheap append, avoids
        # repeated full-array copies on every packet).
        self._full_chunks = []

        self.total_samples_received = 0

    def append(self, new_data: np.ndarray):
        """
        Add newly reconstructed samples to both buffers.

        new_data shape: (channels, samples) — may contain one or more
        packets already concatenated together.
        """
        if new_data.shape[0] != self.channels:
            raise ValueError(
                f"Expected {self.channels} channels, got {new_data.shape[0]}"
            )

        # --- rolling buffer ---
        self.data_buffer = np.concatenate((self.data_buffer, new_data), axis=1)
        if self.data_buffer.shape[1] > self.window_size:
            self.data_buffer = self.data_buffer[:, -self.window_size:]

        # --- full-session buffer ---
        self._full_chunks.append(new_data)

        self.total_samples_received += new_data.shape[1]

    def has_data(self) -> bool:
        """True if enough data is available for the live plot."""
        return self.data_buffer.shape[1] >= 2

    def has_recording(self) -> bool:
        """True if there is any data available for offline inspection."""
        return len(self._full_chunks) > 0

    def get_window(self, channel: int):
        """
        Return (x, y) for the live single-channel plot.

        x: relative time axis in seconds for the visible rolling window.
        y: the requested channel's samples.
        """
        if not (0 <= channel < self.channels):
            raise ValueError(
                f"Invalid channel {channel}: must be between 0 and {self.channels - 1}"
            )
        y = self.data_buffer[channel, :]
        x = np.arange(y.shape[0]) / self.sampling_rate
        return x, y

    def get_all_channels_window(self):
        """
        Return (x, data) for the "Plot All Channels" live view.

        data has shape (channels, samples) — the full rolling window
        across all channels, for the GUI to apply vertical offsets to.
        """
        x = np.arange(self.data_buffer.shape[1]) / self.sampling_rate
        return x, self.data_buffer

    def get_full_recording(self):
        """
        Return (x, data) for offline Matplotlib inspection: the entire
        recording since the last clear() call, all channels.

        data has shape (channels, total_samples).
        """
        if not self._full_chunks:
            empty = np.empty((self.channels, 0), dtype=self.dtype)
            return np.array([]), empty

        data = np.concatenate(self._full_chunks, axis=1)
        x = np.arange(data.shape[1]) / self.sampling_rate
        return x, data

    def get_signal_time_seconds(self) -> float:
        """signal_time = total_samples_received / sampling_rate"""
        return self.total_samples_received / self.sampling_rate

    def clear(self):
        """Reset both buffers, e.g. before starting a new recording session."""
        self.data_buffer = np.empty((self.channels, 0), dtype=self.dtype)
        self._full_chunks = []
        self.total_samples_received = 0