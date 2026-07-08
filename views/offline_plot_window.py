from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class OfflinePlotWindow(QMainWindow):
    """
    Offline Matplotlib inspection window.
    Frontend-only: data is provided by ViewModel via set_data_provider(...) callback.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Offline Signal Inspection")
        self.resize(1000, 700)

        self._data_provider = None  # callable(channel_idx:int, mode:str) -> (time_1d, signal_1d)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Controls
        top = QHBoxLayout()
        root.addLayout(top)

        top.addWidget(QLabel("Channel:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems([f"Channel {i}" for i in range(1, 33)])
        top.addWidget(self.channel_combo)

        top.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Original", "RMS", "Filtered"])
        top.addWidget(self.mode_combo)

        top.addStretch()

        # Matplotlib canvas
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        root.addWidget(self.canvas, stretch=1)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Offline Signal")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude")
        self.ax.grid(True, alpha=0.3)

        # Events
        self.channel_combo.currentIndexChanged.connect(self.refresh_plot)
        self.mode_combo.currentTextChanged.connect(self.refresh_plot)

    def set_data_provider(self, provider_callable):
        """
        provider_callable(channel_idx:int, mode:str) -> tuple[np.ndarray, np.ndarray]
        """
        self._data_provider = provider_callable
        self.refresh_plot()

    def refresh_plot(self):
        self.ax.clear()
        self.ax.set_title("Offline Signal")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude")
        self.ax.grid(True, alpha=0.3)

        if self._data_provider is None:
            self.ax.text(0.5, 0.5, "No data provider set", ha="center", va="center", transform=self.ax.transAxes)
            self.canvas.draw_idle()
            return

        ch_idx = self.channel_combo.currentIndex()
        mode = self.mode_combo.currentText()

        try:
            t, y = self._data_provider(ch_idx, mode)
            if t is None or y is None:
                raise ValueError("No data available.")
            t = np.asarray(t)
            y = np.asarray(y)
            if t.size == 0 or y.size == 0:
                raise ValueError("No data available.")
            self.ax.plot(t, y, linewidth=1.2)
            self.ax.set_title(f"Offline Signal — Channel {ch_idx + 1} — {mode}")
        except Exception as exc:
            self.ax.text(
                0.5,
                0.5,
                f"Could not plot offline data:\n{exc}",
                ha="center",
                va="center",
                transform=self.ax.transAxes,
            )

        self.canvas.draw_idle()