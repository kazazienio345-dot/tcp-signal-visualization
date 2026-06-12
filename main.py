import sys
from PySide6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)

label = QLabel("Proyecto listo con uv 🚀")
label.show()

sys.exit(app.exec())