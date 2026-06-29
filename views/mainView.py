from PySide6.QtWidgets import QMainWindow, QWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__() #Calls the init from the parent object

        self.setWindowTitle("TCP Signal Visualizer")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)