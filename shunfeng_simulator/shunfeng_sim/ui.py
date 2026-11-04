"""PySide6 界面：顺丰 BMS 模拟器（铁塔能源 485 协议 V1.1）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QTabWidget, QTextEdit, QVBoxLayout,
    QWidget,
)

import serial.tools.list_ports

from . import modbus
from . import registers as R
from .serial_worker import SerialWorker
from .simulator import Simulator
from .state import SimState

STYLE = """
QWidget#root { background: #f5f6f8; }
QFrame#header { background: #ffffff; border-bottom: 1px solid #e3e6eb; }
QFrame#card { background: #ffffff; border: 1px solid #e3e6eb; border-radius: 6px; }
QLabel#pageTitle { font-size: 14pt; font-weight: 600; color: #1f2329; }
QLabel#cardTitle { font-size: 11pt; font-weight: 600; color: #1f2329; }
QLabel#cardDesc { color: #8a9099; font-size: 9pt; }
QLabel#note { color: #b07a12; font-size: 8.5pt; }
QLabel#chip { color: #8a9099; font-size: 8.5pt; }
QLabel#hint { color: #5b6572; font-size: 9pt; }
QLabel#statusText { color: #5b6572; font-size: 9pt; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #ffffff; border: 1px solid #d0d5dd; border-radius: 4px;
    padding: 3px 6px; min-height: 22px; color: #1f2329;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #2563eb; }
QPushButton {
    background: #ffffff; border: 1px solid #d0d5dd; border-radius: 4px;
    padding: 5px 14px; color: #1f2329;
}
QPushButton:hover { background: #f2f4f7; }
QPushButton:pressed { background: #e8ebf0; }
QPushButton:disabled { color: #b6bcc4; background: #fafafa; }
QPushButton#primary { background: #2563eb; border-color: #2563eb; color: #ffffff; }
QPushButton#primary:hover { background: #1d4ed8; }
QPushButton#primary:disabled { background: #a9bdf1; border-color: #a9bdf1; }
QTabWidget::pane { border: 1px solid #e3e6eb; background: #ffffff; border-radius: 6px; top: -1px; }
QTabBar::tab {
    background: transparent; padding: 7px 18px; color: #5b6572;
    border-bottom: 2px solid transparent; font-size: 9.5pt;
}
QTabBar::tab:selected { color: #2563eb; border-bottom: 2px solid #2563eb; }
QScrollArea { border: none; background: transparent; }
QCheckBox { spacing: 6px; }
QTextEdit {
    background: #ffffff; border: 1px solid #e3e6eb; border-radius: 4px;
    font-family: Consolas, "Courier New", monospace; font-size: 9pt; color: #333a44;
}
QStatusBar { background: #ffffff; border-top: 1px solid #e3e6eb; color: #5b6572; }
QToolTip { background: #1f2329; color: #ffffff; border: none; padding: 4px 6px; }
"""


def signed(raw: int) -> int:
    return raw - 0x10000 if raw & 0x8000 else raw


def localize_buttons(box: QDialogButtonBox) -> None:
    ok = box.button(QDialogButtonBox.Ok)
    if ok is not None:
        ok.setText("确定")
    cancel = box.button(QDialogButtonBox.Cancel)
    if cancel is not None:
        cancel.setText("取消")


def show_message(parent, icon, title: str, text: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    ok = box.button(QMessageBox.Ok)
    if ok is not None:
        ok.setText("确定")
    box.exec()


class CellsDialog(QDialog):
    """电芯电压编辑：仅前「电芯数量」节可编辑，其余按协议填 0。"""

    def __init__(self, parent, values: list[int], used: int):
        super().__init__(parent)
        self.setWindowTitle(f"电芯电压 · 编辑（{used} 节）")
        self.used = max(0, min(20, used))
        self.spins: list[QSpinBox] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)

        info = QLabel(f"协议按 20 节定义点表，当前电芯数量为 {self.used} 节；"
                      f"第 {self.used + 1} – 20 节向主站返回 0。")
        info.setObjectName("cardDesc")
        info.setWordWrap(True)
        layout.addWidget(info)

        top = QHBoxLayout()
        top.addWidget(QLabel("统一设置："))
        self.uniform = QSpinBox()
        self.uniform.setRange(0, 5000)
        self.uniform.setSuffix(" mV")
        self.uniform.setValue(values[0] if values else 3520)
        top.addWidget(self.uniform)
        apply_btn = QPushButton("应用到全部已用电芯")
        apply_btn.clicked.connect(self._apply_uniform)
        top.addWidget(apply_btn)
        top.addStretch(1)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        grid = QGridLayout(host)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        for i in range(20):
            lab = QLabel(f"第 {i + 1} 节")
            spin = QSpinBox()
            spin.setRange(0, 5000)
            spin.setSuffix(" mV")
            spin.setValue(values[i] if i < len(values) else 0)
            spin.setEnabled(i < self.used)
            self.spins.append(spin)
            grid.addWidget(lab, i // 4, (i % 4) * 2)
            grid.addWidget(spin, i // 4, (i % 4) * 2 + 1)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        localize_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(720, 560)

    def _apply_uniform(self) -> None:
        for spin in self.spins[:self.used]:
            spin.setValue(self.uniform.value())


class Card(QFrame):
    def __init__(self, title: str, subtitle: str = "", note: str = ""):
        super().__init__()
        self.setObjectName("card")
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(16, 13, 16, 13)
        self.vbox.setSpacing(7)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        self.vbox.addWidget(title_label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("cardDesc")
            sub.setWordWrap(True)
            self.vbox.addWidget(sub)
        if note:
            note_label = QLabel(note)
            note_label.setObjectName("note")
            note_label.setWordWrap(True)
            self.vbox.addWidget(note_label)

    def add_row(self, label: str, widget, chip: str = "") -> None:
        row = QHBoxLayout()
        row.setSpacing(10)
        name = QLabel(label)
        name.setMinimumWidth(160)
        row.addWidget(name)
        row.addWidget(widget, 1)
        if chip:
            chip_label = QLabel(chip)
            chip_label.setObjectName("chip")
            chip_label.setMinimumWidth(150)
            chip_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(chip_label)
        self.vbox.addLayout(row)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("顺丰 BMS 模拟器 — 铁塔能源 485 协议 V1.1")
        self.state = SimState()
        self.sim = Simulator(self.state, 1)
        self.worker: SerialWorker | None = None
        self.refreshers = []
        self.coil_checks: list[tuple[int, QCheckBox]] = []
        self._log_lines = 0
        self._build_ui()
        self.resize(1080, 880)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_params_tab(), "模拟响应参数")
        self.tabs.addTab(self._build_coils_tab(), "开关量")
        self.tabs.addTab(self._build_log_tab(), "通讯日志")
        self.tabs.addTab(self._build_debug_tab(), "报文调试")

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 10, 12, 8)
        body_layout.addWidget(self.tabs)
        outer.addWidget(body, 1)
        self._build_statusbar()
        self._refresh_all()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("header")
        row = QHBoxLayout(header)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(8)

        row.addWidget(QLabel("串口"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(140)
        self.port_combo.setEditable(True)
        row.addWidget(self.port_combo)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_ports)
        row.addWidget(refresh_btn)

        row.addSpacing(6)
        row.addWidget(QLabel("设备地址"))
        self.addr_spin = QSpinBox()
        self.addr_spin.setRange(1, 247)
        self.addr_spin.setValue(1)
        self.addr_spin.setToolTip("协议规定装置地址固定为 1，每个保护板单独 485 口通讯")
        self.addr_spin.valueChanged.connect(self._on_address_changed)
        row.addWidget(self.addr_spin)

        row.addWidget(QLabel("波特率"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "115200"])
        row.addWidget(self.baud_combo)

        fixed = QLabel("8 数据位 / 无校验 / 1 停止位 / 无流控")
        fixed.setObjectName("hint")
        row.addWidget(fixed)
        row.addStretch(1)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color:#a0a6ad; font-size:12pt;")
        row.addWidget(self.status_dot)
        self.header_state = QLabel("已停止")
        self.header_state.setObjectName("statusText")
        row.addWidget(self.header_state)

        self.start_btn = QPushButton("启动模拟")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start)
        row.addWidget(self.start_btn)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        row.addWidget(self.stop_btn)

        self._refresh_ports()
        return header

    def _build_statusbar(self) -> None:
        bar = self.statusBar()
        self.bar_state = QLabel("已停止")
        self.bar_state.setStyleSheet("color:#5b6572;")
        bar.addWidget(self.bar_state)
        self.bar_count = QLabel("接收 0 帧 · 应答 0 帧 · 异常 0")
        bar.addPermanentWidget(self.bar_count)

    # -------------------------------------------------------------- 参数页
    def _build_params_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("模拟响应参数")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        hint = QLabel("寄存器值实时写入模拟器，串口运行中修改立即生效")
        hint.setObjectName("hint")
        top.addWidget(hint)
        top.addStretch(1)
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self._reset)
        top.addWidget(reset_btn)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        vbox = QVBoxLayout(host)
        vbox.setContentsMargins(0, 0, 6, 0)
        vbox.setSpacing(10)
        vbox.addWidget(self._build_settings_card())
        vbox.addWidget(self._build_meter_card())
        vbox.addWidget(self._build_cells_card())
        vbox.addWidget(self._build_device_card())
        vbox.addStretch(1)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)
        return page

    def _build_settings_card(self) -> Card:
        card = Card("响应设置",
                    "用于验证主站的超时与异常处理；异常异常码含义见协议 3.2.3。")
        combo = QComboBox()
        for code, label in ((0, "无（正常应答）"), (1, "0x01 无效的报文类型"),
                            (2, "0x02 无效的数据地址"), (3, "0x03 写入的数据值无效"),
                            (6, "0x06 装置忙")):
            combo.addItem(label, code)
        combo.setMaximumWidth(260)
        combo.currentIndexChanged.connect(
            lambda: setattr(self.state.settings, "forced_exception", combo.currentData()))
        card.add_row("强制异常码", combo, "全局生效，用于调试")

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 500)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.setMaximumWidth(190)
        self.delay_spin.valueChanged.connect(
            lambda v: setattr(self.state.settings, "delay_ms", v))
        card.add_row("应答延时", self.delay_spin, "0 – 500 ms")
        return card

    def _build_meter_card(self) -> Card:
        card = Card("模拟量寄存器 0x0000 – 0x001C（0 – 28）",
                    "总压 0.01V、SOC/SOH 为百分比、剩余容量 0.01Ah、充电电流 0.01A；"
                    "温度与单体电压按协议直接以 °C / mV 表示。")
        for d in R.METER_DEFS:
            if d.kind == "cells":
                continue
            card.add_row(f"{d.name}（#{d.addr}）", self._make_editor(d), d.chip())
        return card

    def _build_cells_card(self) -> Card:
        card = Card("单体电压 0x0009 – 0x001C（9 – 28）",
                    "20 节电芯，系数 0.001V；超过「电芯数量」的节向主站返回 0。")
        self.cells_summary = QLabel()
        self.cells_summary.setObjectName("hint")
        button = QPushButton("编辑电芯电压…")
        button.clicked.connect(self._open_cells_dialog)
        row = QHBoxLayout()
        row.addWidget(self.cells_summary, 1)
        row.addWidget(button)
        card.vbox.addLayout(row)
        return card

    def _build_device_card(self) -> Card:
        d = R.REGS_BY_ADDR[R.DEVICE_ID_START]
        card = Card("设备 ID 0x03E8 – 0x03F4（1000 – 1012）",
                    d.desc)
        self.device_edit = QLineEdit()
        self.device_edit.setMaxLength(26)
        self.device_edit.setPlaceholderText("KAM123456")
        self.device_edit.editingFinished.connect(self._commit_device)
        card.add_row("设备 ID（ASCII）", self.device_edit, d.chip())

        note = QLabel("提示：Modbus 写入设备 ID 会返回异常 0x02；此处仅修改模拟器内部值。")
        note.setObjectName("note")
        note.setWordWrap(True)
        card.vbox.addWidget(note)
        self.refreshers.append(self._refresh_device)
        return card

    def _make_editor(self, d: R.RegDef):
        st = self.state
        if d.kind == "num":
            spin = QDoubleSpinBox()
            spin.setDecimals(d.decimals)
            spin.setRange(d.min_raw / d.scale, d.max_raw / d.scale)
            spin.setSuffix(f" {d.unit}" if d.unit else "")
            spin.setMaximumWidth(190)
            spin.valueChanged.connect(
                lambda v, a=d.addr, s=d.scale: st.set_u16(a, int(round(v * s)) & 0xFFFF))

            def refresh(_d=d, _spin=spin):
                raw = st.get_u16(_d.addr)
                if _d.fmt == "S16":
                    raw = signed(raw)
                _spin.blockSignals(True)
                _spin.setValue(raw / _d.scale)
                _spin.blockSignals(False)
            self.refreshers.append(refresh)
            return spin

        if d.kind == "temp":
            spin = QSpinBox()
            spin.setRange(-40, 120)
            spin.setSuffix(f" {d.unit}" if d.unit else "")
            spin.setMaximumWidth(150)
            spin.valueChanged.connect(
                lambda v, a=d.addr: st.set_u16(a, v & 0xFFFF))

            def refresh_temp(_d=d, _spin=spin):
                _spin.blockSignals(True)
                _spin.setValue(signed(st.get_u16(_d.addr)))
                _spin.blockSignals(False)
            self.refreshers.append(refresh_temp)
            return spin

        spin = QSpinBox()
        spin.setRange(0, d.max_raw if d.max_raw <= 1000 else 65535)
        spin.setSuffix(f" {d.unit}" if d.unit else "")
        spin.setMaximumWidth(150)
        spin.valueChanged.connect(lambda v, a=d.addr: st.set_u16(a, v))

        def refresh_int(_d=d, _spin=spin):
            _spin.blockSignals(True)
            _spin.setValue(st.get_u16(_d.addr))
            _spin.blockSignals(False)
        self.refreshers.append(refresh_int)
        return spin

    # -------------------------------------------------------------- 开关量页
    def _build_coils_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("开关量（遥信）0 – 51")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        hint = QLabel("协议按 20 节电芯定义；勾选表示该开关为「合 / 故障」，主站用功能码 01 读取")
        hint.setObjectName("hint")
        top.addWidget(hint)
        top.addStretch(1)
        clear_btn = QPushButton("全部清 0")
        clear_btn.clicked.connect(self._clear_coils)
        top.addWidget(clear_btn)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        vbox = QVBoxLayout(host)
        vbox.setContentsMargins(0, 0, 6, 0)
        vbox.setSpacing(10)
        for gid, gtitle, grange, note in R.COIL_GROUPS:
            card = Card(f"{gtitle}（{grange}）", note)
            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(7)
            items = [c for c in R.COILS if c[2] == gid]
            cols = 3 if len(items) <= 20 else 4
            for i, (addr, name, _) in enumerate(items):
                cb = QCheckBox(f"bit{addr}  {name}")
                cb.toggled.connect(
                    lambda checked, a=addr: self.state.write_coil(a, checked))
                self.coil_checks.append((addr, cb))
                grid.addWidget(cb, i // cols, i % cols)
            card.vbox.addLayout(grid)
            vbox.addWidget(card)
        vbox.addStretch(1)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)
        return page

    # -------------------------------------------------------------- 日志页
    def _build_log_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        top = QHBoxLayout()
        title = QLabel("通讯日志")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        hint = QLabel("接收 / 应答 / 异常逐帧记录；长帧每 16 字节换行")
        hint.setObjectName("hint")
        top.addWidget(hint)
        top.addStretch(1)
        self.autoscroll = QCheckBox("自动滚动")
        self.autoscroll.setChecked(True)
        top.addWidget(self.autoscroll)
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self._clear_log)
        top.addWidget(clear_btn)
        layout.addLayout(top)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)
        return page

    # -------------------------------------------------------------- 调试页
    def _build_debug_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        note = QLabel("离线调试：不占用串口，直接使用当前参数生成应答，便于核对帧格式与 CRC。")
        note.setObjectName("hint")
        layout.addWidget(note)

        row = QHBoxLayout()
        self.req_edit = QLineEdit()
        self.req_edit.setPlaceholderText("输入十六进制请求帧，如 01 03 00 00 00 1D 85 C3")
        self.req_edit.returnPressed.connect(self._offline_send)
        row.addWidget(self.req_edit, 1)
        send_btn = QPushButton("生成应答")
        send_btn.setObjectName("primary")
        send_btn.clicked.connect(self._offline_send)
        row.addWidget(send_btn)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(lambda: self.debug_view.clear())
        row.addWidget(clear_btn)
        layout.addLayout(row)

        quick = [
            ("读设备 ID 1000×13", lambda: self._quick(modbus.build_read_request(1, 1000, 13))),
            ("读模拟量 0×29", lambda: self._quick(modbus.build_read_request(1, 0, 29))),
            ("读开关量 0×52", lambda: self._quick(modbus.build_coil_read_request(1, 0, 52))),
            ("读开关 4–8", lambda: self._quick(modbus.build_coil_read_request(1, 4, 5))),
            ("开关 1 合闸", lambda: self._quick(modbus.build_coil_write_request(1, 1, True))),
            ("写单个寄存器 4 = -300", lambda: self._quick(
                modbus.build_single_write_request(1, 4, -300 & 0xFFFF))),
            ("写多路开关 1–3", lambda: self._quick(
                modbus.build_coils_write_request(1, 1, [1, 0, 1]))),
            ("写多个寄存器 2–4", lambda: self._quick(
                modbus.build_write_request(1, 2, [400, -500 & 0xFFFF, 700]))),
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        for i, (text, handler) in enumerate(quick):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, h=handler: h())
            grid.addWidget(btn, i // 4, i % 4)
        layout.addLayout(grid)

        self.debug_view = QTextEdit()
        self.debug_view.setReadOnly(True)
        layout.addWidget(self.debug_view, 1)
        return page

    # ------------------------------------------------------------ 串口控制
    def _refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        self.port_combo.clear()
        for info in serial.tools.list_ports.comports():
            self.port_combo.addItem(info.device, info.device)
        if current:
            self.port_combo.setCurrentText(current)

    def _on_address_changed(self, value: int) -> None:
        self.sim.address = value

    def _start(self) -> None:
        port = self.port_combo.currentText().strip()
        if not port:
            show_message(self, QMessageBox.Warning, "顺丰 BMS 模拟器", "请选择串口。")
            return
        baud = int(self.baud_combo.currentText())
        self.worker = SerialWorker(self.sim, port, baud)
        self.worker.sig_log.connect(self._log)
        self.worker.sig_state.connect(self._on_serial_state)
        self.worker.sig_counters.connect(self._on_counters)
        self.worker.sig_values_changed.connect(self._refresh_all)
        self.worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _stop(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_serial_state(self, running: bool, message: str) -> None:
        if running:
            self.status_dot.setStyleSheet("color:#16a34a; font-size:12pt;")
            self.header_state.setText("运行中")
            self.bar_state.setText(
                f"运行中 · {self.port_combo.currentText()} · {self.baud_combo.currentText()}bps")
            self.bar_state.setStyleSheet("color:#16a34a;")
        else:
            self.status_dot.setStyleSheet("color:#a0a6ad; font-size:12pt;")
            self.header_state.setText(message or "已停止")
            self.bar_state.setText("已停止")
            self.bar_state.setStyleSheet("color:#5b6572;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            if message.startswith("打开串口失败"):
                self._log("err", message)

    def _on_counters(self, rx: int, tx: int, errors: int) -> None:
        self.bar_count.setText(f"接收 {rx} 帧 · 应答 {tx} 帧 · 异常 {errors}")

    # ------------------------------------------------------------ 参数联动
    def _reset(self) -> None:
        self.state.reset()
        self._refresh_all()
        self._log("info", "已恢复默认参数（设备 ID = KAM123456）")

    def _refresh_all(self) -> None:
        for refresh in self.refreshers:
            refresh()
        self._refresh_coils()
        self._refresh_cells_summary()

    def _refresh_device(self) -> None:
        self.device_edit.blockSignals(True)
        self.device_edit.setText(self.state.get_ascii())
        self.device_edit.blockSignals(False)

    def _commit_device(self) -> None:
        text = self.device_edit.text().strip()
        if len(text) > 26:
            text = text[:26]
            self.device_edit.setText(text)
        self.state.set_ascii(text)

    def _refresh_coils(self) -> None:
        for addr, cb in self.coil_checks:
            cb.blockSignals(True)
            cb.setChecked(bool(self.state.coils[addr]))
            cb.blockSignals(False)

    def _clear_coils(self) -> None:
        self.state.write_coils(0, [0] * R.COIL_COUNT)
        self._refresh_coils()
        self._log("info", "全部开关量已清零")

    def _refresh_cells_summary(self) -> None:
        used = self.state.cell_count()
        vals = [self.state.get_u16(9 + i) for i in range(used)]
        if vals:
            text = (f"当前 {used} 节：最低 {min(vals)} mV / 最高 {max(vals)} mV / "
                    f"压差 {max(vals) - min(vals)} mV（第 {used + 1} – 20 节返回 0）")
        else:
            text = f"当前电芯数量为 {used} 节，第 1 – 20 节均返回 0"
        self.cells_summary.setText(text)

    def _open_cells_dialog(self) -> None:
        used = self.state.cell_count()
        values = [self.state.get_u16(9 + i) for i in range(20)]
        dlg = CellsDialog(self, values, used)
        if dlg.exec() == QDialog.Accepted:
            for i, spin in enumerate(dlg.spins):
                self.state.set_u16(9 + i, spin.value() if i < used else 0)
            self._refresh_cells_summary()

    # -------------------------------------------------------------- 日志
    def _log(self, level: str, text: str) -> None:
        color = {"rx": "#2563eb", "tx": "#16a34a", "err": "#dc2626"}.get(level, "#5b6572")
        prefix = {"rx": "RX", "tx": "TX", "err": "!!", "info": "  "}.get(level, "  ")
        body = text.replace("\n", "<br>&nbsp;&nbsp;&nbsp;&nbsp;")
        self.log_view.append(
            f'<span style="color:#98a2b3;">{prefix}</span> '
            f'<span style="color:{color};">{body}</span>')
        self._log_lines += 1
        if self.autoscroll.isChecked():
            self.log_view.verticalScrollBar().setValue(
                self.log_view.verticalScrollBar().maximum())

    def _clear_log(self) -> None:
        self.log_view.clear()
        self._log_lines = 0

    # -------------------------------------------------------------- 调试
    def _quick(self, frame: bytes) -> None:
        self.req_edit.setText(modbus.format_hex(frame))
        self._offline_send()

    def _offline_send(self) -> None:
        text = self.req_edit.text().strip().replace(",", " ")
        if not text:
            return
        cleaned = text.replace("0x", "").replace("0X", "")
        try:
            frame = bytes.fromhex(cleaned)
        except ValueError:
            self.debug_view.append('<span style="color:#dc2626;">输入不是合法的十六进制字节串</span>')
            return
        result = self.sim.handle(frame)
        parts = [f'<span style="color:#5b6572;">请求：{modbus.format_hex(frame)}</span>']
        if result.rx_desc:
            parts.append(f'<span style="color:#2563eb;">解析：{result.rx_desc}</span>')
        if result.response is not None:
            parts.append(
                f'<span style="color:#16a34a;">应答：'
                f'{modbus.format_hex_wrapped(result.response)}</span>')
            parts.append(f'<span style="color:#5b6572;">{len(result.response)} 字节，'
                         f'CRC 已校验</span>')
        else:
            parts.append('<span style="color:#b07a12;">应答：无（按协议不应答或仅静默忽略）</span>')
        if result.error:
            parts.append(f'<span style="color:#dc2626;">{result.error}</span>')
        if result.tx_desc:
            parts.append(f'<span style="color:#5b6572;">说明：{result.tx_desc}</span>')
        self.debug_view.append("<br>".join(parts))
        self.debug_view.append("")
