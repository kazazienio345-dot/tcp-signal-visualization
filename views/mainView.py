from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__() #Calls the init from the parent object

        self.setWindowTitle("TCP Signal Visualizer")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.port_label = QLabel("Port:")
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Enter port")
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")


        self.layout.addWidget(self.port_label)
        self.layout.addWidget(self.line_edit)
        self.layout.addWidget(self.connect_button)
        self.layout.addWidget(self.disconnect_button)

        self.connect_button.clicked.connect(self.on_connect)

    def on_connect(self):
        port = self.line_edit.text()
        print(port)
