"""顺丰 BMS 模拟器（铁塔能源 BMS 与换电柜上位机 485 串口通讯协议 V1.1）。"""
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from shunfeng_sim.ui import MainWindow, STYLE


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("顺丰 BMS 模拟器")
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
