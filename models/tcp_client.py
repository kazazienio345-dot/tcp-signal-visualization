"""
tcp_client.py

TCP client model for receiving live EMG/biosignal data streamed by the
Exercise 5 server.

This is an extension of the Exercise 5 TcpClientModel. The core
connect / receive / packet-reconstruction logic is unchanged (it already
works correctly). What's added here, specifically for the final project:

    - A second, unbounded buffer that stores the FULL recording, so the
      user can inspect the entire session offline with Matplotlib after
      disconnecting (Ex5 only kept a rolling N-second window).
    - Broader error handling (bad host, connection reset, connection lost
      mid-stream) that reports a status string instead of crashing.
    - A public API surface (get_window, get_all_channels_window,
      get_full_recording, set_selected_channel, status, is_connected)
      that the ViewModel can call without touching sockets or raw bytes.

Architecture note (MVVM):
    This class does NOT use Qt signals and is NOT a QObject. It is a plain
    polling model, matching the Ex5 design: the socket is non-blocking, and
    receive_data() must be called periodically from the ViewModel (e.g. via
    a QTimer, ~16ms interval works well — this matches the poll/render timer
    split used elsewhere in the course). This keeps the Model free of any
    GUI/Qt dependency, per the MVVM requirement that "the Model should not
    contain GUI code."
"""

import socket
import numpy as np


class TcpClientModel:
    """
    TCP client model for receiving EMG data.

    Expected server data (see Exercise 5 server):
        - 32 channels
        - 18 samples per packet
        - float64 values
        - raw bytes sent with current_window.tobytes(order="C")

    Two buffers are maintained:
        - A rolling buffer of `window_seconds` seconds, used for the live
          VisPy plot (fast, fixed size).
        - A full-session buffer that grows for as long as data is
          streaming, used for offline Matplotlib inspection after
          disconnecting.
    """

    def __init__(
        self,
        host="localhost",
        port=12345,
        sampling_rate=2000,
        channels=32,
        samples_per_packet=18,
        window_seconds=10,
        selected_channel=0,
    ):
        self.host = host
        self.port = port
        self.sampling_rate = sampling_rate
        self.channels = channels
        self.samples_per_packet = samples_per_packet
        self.window_seconds = window_seconds
        self.selected_channel = selected_channel

        # Must match the dtype used by the server before .tobytes().
        self.dtype = np.float64

        self.socket = None
        self.is_connected = False

        # Human-readable status for the GUI status label.
        # e.g. "Disconnected", "Connected to localhost:12345",
        # "Could not connect: ...", "Connection lost"
        self.status = "Disconnected"

        self.packet_size = self.channels * self.samples_per_packet
        self.packet_size_bytes = self.packet_size * np.dtype(self.dtype).itemsize

        self.window_size = int(self.sampling_rate * self.window_seconds)

        self.byte_buffer = bytearray()

        # Rolling buffer for the live plot (last `window_seconds` seconds).
        self.data_buffer = np.empty((self.channels, 0), dtype=self.dtype)

        # Full-session buffer for offline inspection. Stored as a list of
        # packet chunks and concatenated on demand (cheap append, avoids
        # repeated full-array copies on every packet).
        self._full_chunks = []

        self.total_samples_received = 0

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------

    def connect(self):
        """
        Connect to the TCP server.

        Does not raise on failure — sets self.status with a readable
        error message instead, so the ViewModel can display it directly
        (per the project's error-handling requirement).
        """
        if self.is_connected:
            return

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3.0)  # only used for the initial connect
            self.socket.connect((self.host, self.port))
            self.socket.setblocking(False)
            self.is_connected = True
            self.status = f"Connected to {self.host}:{self.port}"
        except (ConnectionRefusedError, socket.timeout, OSError) as error:
            self.status = f"Could not connect: {error}"
            self.is_connected = False
            if self.socket is not None:
                self.socket.close()
                self.socket = None

    def disconnect(self):
        """
        Close the TCP connection.

        Intentionally does NOT clear data_buffer / _full_chunks — the user
        needs the full recording to still be available for offline
        inspection after disconnecting. Call clear_buffers() explicitly
        (e.g. right before starting a new connection) if a fresh session
        is wanted.
        """
        self.is_connected = False
        self.status = "Disconnected"

        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def clear_buffers(self):
        """Reset both buffers, e.g. before starting a new recording session."""
        self.data_buffer = np.empty((self.channels, 0), dtype=self.dtype)
        self._full_chunks = []
        self.total_samples_received = 0

    # ------------------------------------------------------------------
    # Receiving data
    # ------------------------------------------------------------------

    def receive_data(self):
        """
        Receive all currently available TCP data.

        Meant to be called repeatedly (e.g. from a QTimer in the
        ViewModel). TCP is a byte stream, so one recv() does not
        necessarily contain exactly one packet — bytes are accumulated
        in self.byte_buffer and complete packets are extracted from it.
        """
        if not self.is_connected or self.socket is None:
            return

        while True:
            try:
                new_bytes = self.socket.recv(self.packet_size_bytes)

                if not new_bytes:
                    # Server closed the connection cleanly (e.g. recording
                    # finished, or server stopped).
                    self.status = "Connection lost (server closed connection)"
                    self.disconnect()
                    return

                self.byte_buffer.extend(new_bytes)

            except BlockingIOError:
                # No more data available right now — not an error.
                break
            except (ConnectionResetError, ConnectionAbortedError, OSError) as error:
                # Real connection failure mid-stream.
                self.status = f"Connection lost: {error}"
                self.disconnect()
                return

        self._extract_packets_from_buffer()

    def _extract_packets_from_buffer(self):
        """
        Convert complete byte packets into NumPy arrays and append them
        to both the rolling buffer and the full-session buffer.

        One complete packet: channels * samples_per_packet values
        (32 * 18 = 576 values -> 576 * 8 bytes = 4608 bytes for float64).
        """
        packets = []

        while len(self.byte_buffer) >= self.packet_size_bytes:
            packet_bytes = self.byte_buffer[: self.packet_size_bytes]
            del self.byte_buffer[: self.packet_size_bytes]

            try:
                packet = np.frombuffer(packet_bytes, dtype=self.dtype)
                packet = packet.reshape((self.channels, self.samples_per_packet))
            except ValueError as error:
                # Malformed packet (shouldn't normally happen, but don't
                # crash the app over it).
                self.status = f"Malformed packet skipped: {error}"
                continue

            packets.append(packet)

        if len(packets) == 0:
            return

        new_data = np.concatenate(packets, axis=1)

        # --- rolling buffer (for live plot) ---
        self.data_buffer = np.concatenate((self.data_buffer, new_data), axis=1)
        if self.data_buffer.shape[1] > self.window_size:
            self.data_buffer = self.data_buffer[:, -self.window_size :]

        # --- full-session buffer (for offline inspection) ---
        self._full_chunks.append(new_data)

        self.total_samples_received += new_data.shape[1]

    # ------------------------------------------------------------------
    # Public accessors for the ViewModel
    # ------------------------------------------------------------------

    def has_data(self):
        """True if enough data is available for the live plot."""
        return self.data_buffer.shape[1] >= 2

    def has_recording(self):
        """True if there is any data available for offline inspection."""
        return len(self._full_chunks) > 0

    def set_selected_channel(self, channel: int):
        """Change which channel the live single-channel plot shows."""
        if not (0 <= channel < self.channels):
            raise ValueError(
                f"Invalid channel {channel}: must be between 0 and {self.channels - 1}"
            )
        self.selected_channel = channel

    def get_window(self):
        """
        Return (x, y) for the live single-channel plot.

        x: relative time axis in seconds for the visible rolling window.
        y: the currently selected channel's samples.
        """
        y = self.data_buffer[self.selected_channel, :]
        x = np.arange(y.shape[0]) / self.sampling_rate
        return x, y

    def get_all_channels_window(self):
        """
        Return (x, data) for the "Plot All Channels" live view.

        data has shape (channels, samples) — the full rolling window
        across all 32 channels, for the GUI to apply vertical offsets to.
        """
        x = np.arange(self.data_buffer.shape[1]) / self.sampling_rate
        return x, self.data_buffer

    def get_full_recording(self):
        """
        Return (x, data) for offline Matplotlib inspection: the entire
        recording since the last clear_buffers() call, all channels.

        data has shape (channels, total_samples).
        """
        if not self._full_chunks:
            empty = np.empty((self.channels, 0), dtype=self.dtype)
            return np.array([]), empty

        data = np.concatenate(self._full_chunks, axis=1)
        x = np.arange(data.shape[1]) / self.sampling_rate
        return x, data

    def get_signal_time_seconds(self):
        """signal_time = total_samples_received / sampling_rate"""
        return self.total_samples_received / self.sampling_rate


if __name__ == "__main__":
    # Standalone smoke test: connect to a locally running Ex5 server and
    # print incoming window shapes. Run the server first, then:
    #   python models/tcp_client.py
    import time

    client = TcpClientModel(host="localhost", port=12345)
    client.connect()
    print(client.status)

    if client.is_connected:
        for _ in range(50):
            client.receive_data()
            if client.has_data():
                x, y = client.get_window()
                print(f"window shape: {y.shape}, t={client.get_signal_time_seconds():.2f}s")
            time.sleep(0.05)
        client.disconnect()