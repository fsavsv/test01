#!/usr/bin/env python3
"""BMS 模拟器入口。"""
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from bms_sim.ui import MainWindow, STYLE


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("BMS 模拟器")
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei UI")
    font.setPointSize(9)
    app.setFont(font)
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
