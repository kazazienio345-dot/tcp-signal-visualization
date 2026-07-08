from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QStatusBar,
    QMessageBox,
)

from views.vispy_live_view import VisPyLiveView


class MainWindow(QMainWindow):
    """
    Frontend-only main GUI window.
    Exposes signals through direct widget access for the ViewModel to connect.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TCP Signal Visualization")
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # --- Top controls row: TCP UI (backend teammate wires behavior) ---
        conn_row = QHBoxLayout()
        root.addLayout(conn_row)

        conn_row.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("e.g. 5000")
        self.port_input.setFixedWidth(120)
        conn_row.addWidget(self.port_input)

        self.connect_btn = QPushButton("Connect")
        conn_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        conn_row.addWidget(self.disconnect_btn)

        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setStyleSheet("color: #b00020; font-weight: 600;")
        conn_row.addWidget(self.connection_status_label)

        conn_row.addStretch()

        # --- Signal controls row ---
        signal_row = QHBoxLayout()
        root.addLayout(signal_row)

        signal_row.addWidget(QLabel("Channel:"))
        self.channel_combo = QComboBox()
        self.channel_combo.setFixedWidth(140)
        # 32 channels, user-friendly numbering
        self.channel_combo.addItems([f"Channel {i}" for i in range(1, 33)])
        signal_row.addWidget(self.channel_combo)

        signal_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.setFixedWidth(140)
        self.mode_combo.addItems(["Original", "RMS", "Filtered"])
        signal_row.addWidget(self.mode_combo)

        self.plot_all_btn = QPushButton("Plot All Channels")
        signal_row.addWidget(self.plot_all_btn)

        self.plot_single_btn = QPushButton("Plot Selected Channel")
        signal_row.addWidget(self.plot_single_btn)

        self.offline_btn = QPushButton("Open Offline Plot")
        signal_row.addWidget(self.offline_btn)

        signal_row.addStretch()

        # --- Live plot area ---
        self.live_view = VisPyLiveView()
        root.addWidget(self.live_view.native, stretch=1)

        # --- Status bar ---
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready.")

    # ---------- UI helper methods ----------
    def set_connected_ui(self, connected: bool):
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        if connected:
            self.connection_status_label.setText("Connected")
            self.connection_status_label.setStyleSheet("color: #1b8a3f; font-weight: 600;")
        else:
            self.connection_status_label.setText("Disconnected")
            self.connection_status_label.setStyleSheet("color: #b00020; font-weight: 600;")

    def set_status(self, text: str):
        self._status.showMessage(text)

    def show_error(self, text: str):
        QMessageBox.critical(self, "Error", text)

    def current_channel_index(self) -> int:
        """Returns zero-based channel index [0..31]."""
        return self.channel_combo.currentIndex()

    def current_mode(self) -> str:
        """Returns one of: Original, RMS, Filtered."""
        return self.mode_combo.currentText()