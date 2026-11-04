#!/usr/bin/env python3
"""绿通 BMS 模拟器入口（RS485 通讯协议规范 V1.9，二三轮电动车）。"""
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from lvtong_sim.ui import MainWindow, STYLE


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("绿通 BMS 模拟器")
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
