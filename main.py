from __future__ import annotations

import sys
import numpy as np

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication

from views.main_window import MainWindow
from viewmodels.main_viewmodel import MainViewModel


# -----------------------------------------------------------------------------
# TEMP FAKE BACKEND (for frontend testing only)
# Replace this with your teammate's real TCP backend service class.
# -----------------------------------------------------------------------------
class FakeBackendService(QObject):
    data_updated = Signal(object)   # np.ndarray (32, N)
    connected = Signal()
    disconnected = Signal()
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.sampling_rate = 250.0
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

        self._connected = False
        self._buffer_len = 2500
        self._data = np.zeros((32, self._buffer_len), dtype=np.float64)

        self._phase = np.linspace(0, 2 * np.pi, 32, endpoint=False)

    # expected by ViewModel
    def connect(self, port: int):
        if port <= 0:
            raise ValueError("Invalid port")
        self._connected = True
        self.connected.emit()
        self._timer.start(40)  # ~25 FPS GUI updates

    def disconnect(self):
        self._timer.stop()
        self._connected = False
        self.disconnected.emit()

    def has_recorded_data(self) -> bool:
        return self._data.size > 0 and np.any(np.abs(self._data) > 0)

    def get_recorded_data(self) -> np.ndarray:
        return self._data.copy()

    def process_channel(self, channel_1d: np.ndarray, mode: str) -> np.ndarray:
        y = np.asarray(channel_1d, dtype=np.float64)

        if mode == "Original":
            return y
        elif mode == "RMS":
            win = 30
            sq = y * y
            kernel = np.ones(win) / win
            return np.sqrt(np.convolve(sq, kernel, mode="same"))
        elif mode == "Filtered":
            # simple moving average placeholder
            win = 10
            kernel = np.ones(win) / win
            return np.convolve(y, kernel, mode="same")
        else:
            return y

    def process_all(self, data_2d: np.ndarray, mode: str) -> np.ndarray:
        arr = np.asarray(data_2d)
        out = np.zeros_like(arr)
        for ch in range(32):
            out[ch] = self.process_channel(arr[ch], mode)
        return out

    def _tick(self):
        if not self._connected:
            return

        n_new = 18  # same chunk sample count as project statement
        t = np.arange(n_new) / self.sampling_rate

        new_chunk = np.zeros((32, n_new), dtype=np.float64)
        for ch in range(32):
            f = 3 + (ch % 8) * 0.6
            amp = 0.6 + (ch % 5) * 0.12
            noise = 0.08 * np.random.randn(n_new)
            new_chunk[ch] = amp * np.sin(2 * np.pi * f * t + self._phase[ch]) + noise
            self._phase[ch] += 2 * np.pi * f * (n_new / self.sampling_rate)

        self._data = np.roll(self._data, -n_new, axis=1)
        self._data[:, -n_new:] = new_chunk

        self.data_updated.emit(self._data.copy())


def main():
    app = QApplication(sys.argv)

    window = MainWindow()

    # TODO (integration): replace FakeBackendService with real backend service
    backend_service = FakeBackendService()

    _vm = MainViewModel(window, backend_service)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()