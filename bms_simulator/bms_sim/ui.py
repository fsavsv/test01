"""PySide6 界面。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget,
)

import serial.tools.list_ports

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
QLabel#statusDot { color: #a0a6ad; font-size: 11pt; }
QLabel#statusText { color: #5b6572; font-size: 9pt; }
QLabel#errorText { color: #dc2626; }
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
QPushButton#ghost { border: 1px solid #e3e6eb; color: #5b6572; }
QTabWidget::pane { border: 1px solid #e3e6eb; background: #ffffff; border-radius: 6px; top: -1px; }
QTabBar::tab {
    background: transparent; padding: 7px 18px; color: #5b6572;
    border-bottom: 2px solid transparent; font-size: 9.5pt;
}
QTabBar::tab:selected { color: #2563eb; border-bottom: 2px solid #2563eb; }
QScrollArea { border: none; background: transparent; }
QCheckBox { spacing: 6px; }
QPlainTextEdit {
    background: #ffffff; border: 1px solid #e3e6eb; border-radius: 4px;
    font-family: Consolas, "Courier New", monospace; font-size: 9pt; color: #333a44;
}
QStatusBar { background: #ffffff; border-top: 1px solid #e3e6eb; color: #5b6572; }
QToolTip { background: #1f2329; color: #ffffff; border: none; padding: 4px 6px; }
"""


def raw_to_signed(raw: int) -> int:
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


class BitsDialog(QDialog):
    def __init__(self, parent, d: R.RegDef, value: int):
        super().__init__(parent)
        self.setWindowTitle(f"{d.name} · 位定义")
        self.value = value
        self.total = 32 if d.fmt == "U32" else 16
        self._checks: list[tuple[int, QCheckBox]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        grid = QGridLayout(host)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(6)
        cols = 1 if self.total <= 16 else 2
        for i, (bit, label) in enumerate(d.bits):
            cb = QCheckBox(f"bit{bit}  {label}")
            cb.setChecked(bool(value & (1 << bit)))
            cb.toggled.connect(self._sync)
            grid.addWidget(cb, i // cols, i % cols)
            self._checks.append((bit, cb))
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)

        bottom = QHBoxLayout()
        self.hex_label = QLabel()
        self.hex_label.setObjectName("hint")
        bottom.addWidget(self.hex_label)
        bottom.addStretch(1)
        clear = QPushButton("全部清 0")
        clear.clicked.connect(self._clear)
        bottom.addWidget(clear)
        layout.addLayout(bottom)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        localize_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(560, 560 if self.total > 16 else 440)
        self._sync()

    def _clear(self) -> None:
        for _, cb in self._checks:
            cb.setChecked(False)
        self._sync()

    def _sync(self) -> None:
        v = 0
        for bit, cb in self._checks:
            if cb.isChecked():
                v |= 1 << bit
        self.value = v
        self.hex_label.setText(f"当前值：0x{v:04X}    {v}")

    def accept(self) -> None:
        self._sync()
        super().accept()


class CellsDialog(QDialog):
    def __init__(self, parent, d: R.RegDef, values: list[int], used: int):
        super().__init__(parent)
        self.setWindowTitle(f"{d.name} · 编辑（{used} 节）")
        self.values = list(values)
        self.used = used
        self.spins: list[QSpinBox] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)

        info = QLabel(f"共 {used} 节（由 0x008E 电芯串数决定）；未使用的节保留 0xFFFF。")
        info.setObjectName("cardDesc")
        layout.addWidget(info)

        top = QHBoxLayout()
        top.addWidget(QLabel("统一设置："))
        self.uniform = QSpinBox()
        self.uniform.setRange(0, 5000)
        self.uniform.setSuffix(" mV")
        self.uniform.setValue(values[0] if values else 3300)
        top.addWidget(self.uniform)
        apply_btn = QPushButton("应用到全部")
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
        for i in range(used):
            lab = QLabel(f"第 {i + 1} 节")
            spin = QSpinBox()
            spin.setRange(0, 5000)
            spin.setSuffix(" mV")
            val = self.values[i] if i < len(self.values) else 3300
            spin.setValue(min(5000, max(0, val)))
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
        self.resize(780, min(620, 180 + (used // 4 + 1) * 36))

    def _apply_uniform(self) -> None:
        for spin in self.spins:
            spin.setValue(self.uniform.value())


class TempsDialog(QDialog):
    def __init__(self, parent, d: R.RegDef, values: list[int]):
        super().__init__(parent)
        self.setWindowTitle(f"{d.name} · 编辑（{d.count} 点）")
        self.values = list(values)
        self.spins: list[QDoubleSpinBox] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)

        top = QHBoxLayout()
        top.addWidget(QLabel("统一设置："))
        self.uniform = QDoubleSpinBox()
        self.uniform.setRange(-50, 120)
        self.uniform.setDecimals(1)
        self.uniform.setSuffix(" °C")
        self.uniform.setValue((values[0] if values else 298) - 273.15)
        top.addWidget(self.uniform)
        apply_btn = QPushButton("应用到全部")
        apply_btn.clicked.connect(self._apply_uniform)
        top.addWidget(apply_btn)
        top.addStretch(1)
        layout.addLayout(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        for i in range(d.count):
            lab = QLabel(f"温度 {i + 1}")
            spin = QDoubleSpinBox()
            spin.setRange(-50, 120)
            spin.setDecimals(1)
            spin.setSuffix(" °C")
            v = self.values[i] if i < len(self.values) else 298
            spin.setValue(v - 273.15)
            self.spins.append(spin)
            grid.addWidget(lab, i // 2, (i % 2) * 2)
            grid.addWidget(spin, i // 2, (i % 2) * 2 + 1)
        layout.addLayout(grid)
        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        localize_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(520, 300)

    def _apply_uniform(self) -> None:
        for spin in self.spins:
            spin.setValue(self.uniform.value())


class Card(QFrame):
    def __init__(self, title: str, subtitle: str = "", note: str = ""):
        super().__init__()
        self.setObjectName("card")
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(16, 13, 16, 13)
        vbox.setSpacing(6)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        vbox.addWidget(title_label)
        if subtitle:
            desc = QLabel(subtitle)
            desc.setObjectName("cardDesc")
            desc.setWordWrap(True)
            vbox.addWidget(desc)
        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 4, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(7)
        self.grid.setColumnMinimumWidth(0, 168)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnMinimumWidth(2, 132)
        vbox.addLayout(self.grid)
        self._row = 0
        if note:
            note_label = QLabel(note)
            note_label.setObjectName("note")
            note_label.setWordWrap(True)
            vbox.addWidget(note_label)

    def add_row(self, name: str, widget: QWidget, chip: str, desc: str = "") -> None:
        label = QLabel(name)
        label.setToolTip(desc)
        widget.setToolTip(desc)
        chip_label = QLabel(chip)
        chip_label.setObjectName("chip")
        chip_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid.addWidget(label, self._row, 0)
        self.grid.addWidget(widget, self._row, 1)
        self.grid.addWidget(chip_label, self._row, 2)
        self._row += 1


class ParamEditor(QWidget):
    """按寄存器类型生成编辑控件，并同步到 SimState。"""

    def __init__(self, state: SimState, d: R.RegDef, on_register):
        super().__init__()
        self.state = state
        self.d = d
        self.refresh = lambda: None
        self._build()
        on_register(d.addr, self.refresh)

    def _build(self) -> None:
        d, st = self.d, self.state
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        kind = d.kind

        if kind == "int":
            spin = QSpinBox()
            spin.setMaximumWidth(190)
            spin.setRange(d.min_raw, d.max_raw)
            if d.unit:
                spin.setSuffix(f" {d.unit}")
            spin.valueChanged.connect(
                lambda v: st.set_u16(d.addr, v))
            layout.addWidget(spin)

            def refresh_int():
                spin.blockSignals(True)
                spin.setValue(st.get_u16(d.addr))
                spin.blockSignals(False)
            self.refresh = refresh_int

        elif kind == "num":
            spin = QDoubleSpinBox()
            spin.setMaximumWidth(190)
            step = 10 ** (-d.decimals)
            spin.setDecimals(d.decimals)
            spin.setSingleStep(step)
            low = d.min_raw / d.scale
            high = d.max_raw / d.scale
            spin.setRange(low, high)
            spin.setSuffix(f" {d.unit}")
            spin.valueChanged.connect(lambda v: st.set_u16(
                d.addr, round(v * d.scale) & 0xFFFF))
            layout.addWidget(spin)

            def refresh_num():
                raw = st.get_u16(d.addr)
                if d.fmt == "S16":
                    raw = raw_to_signed(raw)
                spin.blockSignals(True)
                spin.setValue(raw / d.scale)
                spin.blockSignals(False)
            self.refresh = refresh_num

        elif kind == "temp":
            spin = QDoubleSpinBox()
            spin.setMaximumWidth(170)
            spin.setRange(-50, 120)
            spin.setDecimals(1)
            spin.setSingleStep(0.1)
            spin.setSuffix(" °C")
            spin.valueChanged.connect(lambda v: st.set_u16(
                d.addr, max(0, min(65535, round(v + 273.15))))
            )
            layout.addWidget(spin)

            def refresh_temp():
                spin.blockSignals(True)
                spin.setValue(st.get_u16(d.addr) - 273.15)
                spin.blockSignals(False)
            self.refresh = refresh_temp

        elif kind == "hex":
            edit = QLineEdit()
            edit.setMaximumWidth(150)
            edit.setValidator(QRegularExpressionValidator(
                QRegularExpression(r"^(0[xX])?[0-9A-Fa-f]{1,4}$"), edit))

            def commit_hex():
                text = edit.text().strip()
                try:
                    value = int(text, 16) if text.lower().startswith("0x") else int(text, 16)
                    st.set_u16(d.addr, value)
                except ValueError:
                    pass
                self.refresh()
            edit.editingFinished.connect(commit_hex)
            layout.addWidget(edit)

            def refresh_hex():
                edit.blockSignals(True)
                edit.setText(f"0x{st.get_u16(d.addr):04X}")
                edit.blockSignals(False)
            self.refresh = refresh_hex

        elif kind == "ascii":
            edit = QLineEdit()
            edit.setMaxLength(d.count * 2)
            edit.editingFinished.connect(
                lambda: st.set_ascii(d.addr, edit.text(), d.count))
            layout.addWidget(edit)

            def refresh_ascii():
                edit.blockSignals(True)
                edit.setText(st.get_ascii(d.addr, d.count))
                edit.blockSignals(False)
            self.refresh = refresh_ascii

        elif kind in ("bits", "balance"):
            edit = QLineEdit()
            edit.setMaximumWidth(120)
            is32 = d.fmt == "U32"
            edit.setValidator(QRegularExpressionValidator(
                QRegularExpression(r"^(0[xX])?[0-9A-Fa-f]{1,8}$"), edit))
            button = QPushButton("位编辑…")
            layout.addWidget(edit)
            layout.addWidget(button)
            layout.addStretch(1)

            def current() -> int:
                return st.get_u32(d.addr) if is32 else st.get_u16(d.addr)

            def commit_bits():
                text = edit.text().strip()
                try:
                    v = int(text, 16)
                except ValueError:
                    self.refresh()
                    return
                if is32:
                    st.set_u32(d.addr, v)
                else:
                    st.set_u16(d.addr, v)
                self.refresh()
            edit.editingFinished.connect(commit_bits)
            button.clicked.connect(lambda: self._open_bits_dialog(current()))

            def refresh_bits():
                v = current()
                edit.blockSignals(True)
                edit.setText(f"0x{v:04X}" if not is32 else f"0x{v:08X}")
                edit.blockSignals(False)
            self.refresh = refresh_bits

        elif kind == "cells":
            summary = QLabel()
            summary.setObjectName("hint")
            button = QPushButton(f"编辑 {d.count} 节…")
            layout.addWidget(summary, 1)
            layout.addWidget(button)
            button.clicked.connect(self._open_cells_dialog)

            def refresh_cells():
                vals = [st.get_u16(d.addr + i) for i in range(d.count)]
                used = st.get_u16(142)
                valid = vals[:min(d.count, used)]
                if valid:
                    summary.setText(
                        f"{used} 节使用 · 最低 {min(valid)} mV / 最高 {max(valid)} mV")
                else:
                    summary.setText("未配置")
            self.refresh = refresh_cells

        elif kind == "temps":
            summary = QLabel()
            summary.setObjectName("hint")
            button = QPushButton(f"编辑 {d.count} 点…")
            layout.addWidget(summary, 1)
            layout.addWidget(button)
            button.clicked.connect(self._open_temps_dialog)

            def refresh_temps():
                vals = [st.get_u16(d.addr + i) for i in range(d.count)]
                avg = sum(vals) / len(vals)
                summary.setText(f"{d.count} 点 · 平均 {avg - 273.15:.1f} °C")
            self.refresh = refresh_temps

        elif kind == "cellinfo":
            type_combo = QComboBox()
            type_combo.addItems(["0 LFP 磷酸铁锂", "1 NCM 三元锂", "2 LMO 锰酸锂", "3 LTO 钛酸锂"])
            type_combo.setMaximumWidth(190)
            count_spin = QSpinBox()
            count_spin.setRange(1, 32)
            count_spin.setSuffix(" 串")
            count_spin.setMaximumWidth(100)
            layout.addWidget(type_combo)
            layout.addWidget(count_spin)
            layout.addStretch(1)

            def commit_cellinfo():
                st.set_u16(d.addr, (type_combo.currentIndex() << 8) | count_spin.value())
            type_combo.currentIndexChanged.connect(lambda _: commit_cellinfo())
            count_spin.valueChanged.connect(lambda _: commit_cellinfo())

            def refresh_cellinfo():
                raw = st.get_u16(d.addr)
                type_combo.blockSignals(True)
                count_spin.blockSignals(True)
                type_combo.setCurrentIndex(min(3, raw >> 8))
                count_spin.setValue(max(1, raw & 0xFF))
                type_combo.blockSignals(False)
                count_spin.blockSignals(False)
            self.refresh = refresh_cellinfo

        elif kind == "vendor":
            pack_spin = QSpinBox()
            pack_spin.setRange(0, 255)
            pack_spin.setPrefix("PACK ")
            pack_spin.setMaximumWidth(110)
            bms_spin = QSpinBox()
            bms_spin.setRange(0, 255)
            bms_spin.setPrefix("BMS ")
            bms_spin.setMaximumWidth(110)
            layout.addWidget(pack_spin)
            layout.addWidget(bms_spin)
            layout.addStretch(1)

            def commit_vendor():
                st.set_u16(d.addr, (pack_spin.value() << 8) | bms_spin.value())
            pack_spin.valueChanged.connect(lambda _: commit_vendor())
            bms_spin.valueChanged.connect(lambda _: commit_vendor())

            def refresh_vendor():
                raw = st.get_u16(d.addr)
                pack_spin.blockSignals(True)
                bms_spin.blockSignals(True)
                pack_spin.setValue(raw >> 8)
                bms_spin.setValue(raw & 0xFF)
                pack_spin.blockSignals(False)
                bms_spin.blockSignals(False)
            self.refresh = refresh_vendor

        self.refresh()

    def _open_bits_dialog(self, value: int) -> None:
        dlg = BitsDialog(self, self.d, value)
        if dlg.exec() == QDialog.Accepted:
            if self.d.fmt == "U32":
                self.state.set_u32(self.d.addr, dlg.value)
            else:
                self.state.set_u16(self.d.addr, dlg.value)
            self.refresh()

    def _open_cells_dialog(self) -> None:
        d = self.d
        used = min(d.count, max(1, self.state.get_u16(142)))
        values = [self.state.get_u16(d.addr + i) for i in range(used)]
        dlg = CellsDialog(self, d, values, used)
        if dlg.exec() == QDialog.Accepted:
            for i, spin in enumerate(dlg.spins):
                self.state.set_u16(d.addr + i, spin.value())
            self.refresh()

    def _open_temps_dialog(self) -> None:
        d = self.d
        values = [self.state.get_u16(d.addr + i) for i in range(d.count)]
        dlg = TempsDialog(self, d, values)
        if dlg.exec() == QDialog.Accepted:
            for i, spin in enumerate(dlg.spins):
                self.state.set_u16(d.addr + i, max(0, round(spin.value() + 273.15)))
            self.refresh()


class ParamCard(Card):
    def __init__(self, state: SimState, defs: list[R.RegDef], title: str,
                 subtitle: str, note: str, on_register):
        super().__init__(title, subtitle, note)
        self.editors: list[ParamEditor] = []
        for d in defs:
            editor = ParamEditor(state, d, on_register)
            chip = d.chip()
            if d.kind == "ascii":
                chip = f"ASCII · {d.count * 2} 字节 · {d.access}"
            self.add_row(d.name, editor, chip, d.desc)
            self.editors.append(editor)

    def refresh(self) -> None:
        for editor in self.editors:
            editor.refresh()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BMS 模拟器 — RS485 Modbus RTU")
        self.resize(1040, 760)
        self.state = SimState()
        self.sim = Simulator(self.state, address=3)
        self.worker: SerialWorker | None = None
        self.cards: list[ParamCard] = []
        self.addr_refreshers: dict[int, list] = {}
        self.cells_card: ParamCard | None = None

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 10, 12, 8)
        body_layout.addWidget(self._build_tabs())
        outer.addWidget(body, 1)
        self._build_status_bar()
        self._refresh_ports()
        self._refresh_all()

    # ---------------- 顶部串口区 ----------------
    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("header")
        box = QVBoxLayout(header)
        box.setContentsMargins(14, 10, 14, 8)
        box.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("串口"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setMinimumWidth(128)
        self.port_combo.setMaximumWidth(150)
        row.addWidget(self.port_combo)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        row.addWidget(self.refresh_btn)

        row.addSpacing(10)
        row.addWidget(QLabel("BMS 地址"))
        self.addr_spin = QSpinBox()
        self.addr_spin.setRange(1, 247)
        self.addr_spin.setValue(3)
        self.addr_spin.setFixedWidth(72)
        self.addr_spin.valueChanged.connect(lambda v: setattr(self.sim, "address", v))
        row.addWidget(self.addr_spin)

        row.addSpacing(10)
        row.addWidget(QLabel("波特率"))
        self.baud_combo = QComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems(["9600", "19200", "115200"])
        self.baud_combo.setCurrentText("19200")
        self.baud_combo.setFixedWidth(104)
        row.addWidget(self.baud_combo)

        row.addSpacing(10)
        hint = QLabel("8 数据位 / 无校验 / 1 停止位 / 无流控")
        hint.setObjectName("hint")
        row.addWidget(hint)
        row.addStretch(1)

        self.start_btn = QPushButton("启动模拟")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumWidth(96)
        self.start_btn.clicked.connect(self._start)
        row.addWidget(self.start_btn)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setMinimumWidth(80)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        row.addWidget(self.stop_btn)
        box.addLayout(row)

        state_row = QHBoxLayout()
        state_row.setSpacing(6)
        self.dot_label = QLabel("●")
        self.dot_label.setObjectName("statusDot")
        self.state_label = QLabel("已停止")
        self.state_label.setObjectName("statusText")
        self.detail_label = QLabel()
        self.detail_label.setObjectName("statusText")
        state_row.addWidget(self.dot_label)
        state_row.addWidget(self.state_label)
        state_row.addWidget(self.detail_label)
        state_row.addStretch(1)
        box.addLayout(state_row)
        return header

    # ---------------- 主体 ----------------
    def _build_tabs(self) -> QWidget:
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_params_tab(), "模拟响应参数")
        self.tabs.addTab(self._build_log_tab(), "通讯日志")
        self.tabs.addTab(self._build_tester_tab(), "报文调试")
        return self.tabs

    def _on_register(self, addr: int, fn) -> None:
        self.addr_refreshers.setdefault(addr, []).append(fn)

    def _build_params_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        bar = QHBoxLayout()
        title = QLabel("模拟响应参数")
        title.setObjectName("pageTitle")
        bar.addWidget(title)
        chip = QLabel("寄存器值实时写入模拟器，串口运行中修改立即生效")
        chip.setObjectName("cardDesc")
        bar.addSpacing(10)
        bar.addWidget(chip)
        bar.addStretch(1)
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self._reset_defaults)
        bar.addWidget(reset_btn)
        layout.addLayout(bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(2, 2, 8, 10)
        host_layout.setSpacing(10)

        host_layout.addWidget(self._build_settings_card())
        for gid, title, rng, desc in R.GROUPS:
            defs = R.DEFS_BY_GROUP[gid]
            note = ""
            if gid == "general":
                note = "提示：0x0004 – 0x0063 为预留寄存器，读回 0xFFFF。"
            elif gid == "sop":
                note = "提示：0x00C3 – 0x00C7（195 – 199）预留，读回 0xFFFF。"
            elif gid == "charge":
                note = "提示：0x00CC – 0x012B（204 – 299）预留，读回 0xFFFF。"
            card = ParamCard(self.state, defs, f"{title}　{rng}", desc, note,
                             self._on_register)
            self.cards.append(card)
            host_layout.addWidget(card)
        host_layout.addStretch(1)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)
        return page

    def _build_settings_card(self) -> QWidget:
        card = Card("响应设置", "用于验证主机的超时、异常处理；0x00 为广播地址，写入执行但不应答，"
                               "非本机地址的请求静默忽略。")
        self.force_exc_combo = QComboBox()
        self.force_exc_combo.addItems([
            "无（正常应答）",
            "0x01 不支持的功能码",
            "0x02 寄存器地址无效",
            "0x03 数据值超出范围",
        ])
        self.force_exc_combo.setMaximumWidth(260)
        self.force_exc_combo.currentIndexChanged.connect(self._apply_settings)
        card.add_row("强制异常码", self.force_exc_combo, "调试用", "所有请求强制返回异常应答")

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 500)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.setMaximumWidth(140)
        self.delay_spin.valueChanged.connect(self._apply_settings)
        card.add_row("应答延时", self.delay_spin, "0 – 500 ms", "模拟主机 500ms 超时")

        self.auto_link_check = QCheckBox("按协议自动联动 194 / 200 / 201")
        self.auto_link_check.setChecked(True)
        self.auto_link_check.toggled.connect(self._apply_settings)
        card.add_row("协议联动", self.auto_link_check, "默认开启",
                     "充电器未接入（#203≠0x55AA）、SoC>95% 或存在充电类保护时，"
                     "回馈电流与请求充电电压/电流读回 0")
        return card

    def _apply_settings(self) -> None:
        self.state.settings.forced_exception = self.force_exc_combo.currentIndex()
        self.state.settings.delay_ms = self.delay_spin.value()
        self.state.settings.auto_link = self.auto_link_check.isChecked()

    def _refresh_all(self) -> None:
        for card in self.cards:
            card.refresh()
        for fn in self.addr_refreshers.get(118, []):
            fn()
        for addr in (202, 203):
            for fn in self.addr_refreshers.get(addr, []):
                fn()

    def _reset_defaults(self) -> None:
        self.state.reset()
        self._refresh_all()
        self._log("info", "已恢复协议默认参数")

    # ---------------- 日志 ----------------
    def _build_log_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        bar = QHBoxLayout()
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(lambda: self.log_view.clear())
        bar.addWidget(clear_btn)
        self.autoscroll_check = QCheckBox("自动滚动")
        self.autoscroll_check.setChecked(True)
        bar.addWidget(self.autoscroll_check)
        bar.addStretch(1)
        self.counter_label = QLabel("接收 0 帧 · 应答 0 帧")
        self.counter_label.setObjectName("cardDesc")
        bar.addWidget(self.counter_label)
        layout.addLayout(bar)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(4000)
        layout.addWidget(self.log_view, 1)
        return page

    def _log(self, level: str, text: str) -> None:
        from datetime import datetime
        stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = {"rx": "#5b6572", "tx": "#2563eb", "err": "#dc2626",
                 "info": "#8a9099"}.get(level, "#5b6572")
        tag = {"rx": "RX", "tx": "TX", "err": "ERR", "info": "·"}.get(level, "")
        safe = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        self.log_view.appendHtml(
            f'<span style="color:#a0a6ad">[{stamp}]</span> '
            f'<span style="color:{color}">{tag} {safe}</span>')
        if self.autoscroll_check.isChecked():
            self.log_view.verticalScrollBar().setValue(
                self.log_view.verticalScrollBar().maximum())

    # ---------------- 报文调试 ----------------
    def _build_tester_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        tip = QLabel("离线调试：不占用串口，直接使用当前参数生成应答，便于核对帧格式与 CRC。")
        tip.setObjectName("cardDesc")
        layout.addWidget(tip)

        row = QHBoxLayout()
        self.req_edit = QLineEdit()
        self.req_edit.setPlaceholderText("输入请求帧 HEX，例如 01 03 00 72 00 06 20 7D")
        font = QFont("Consolas")
        font.setPointSize(10)
        self.req_edit.setFont(font)
        row.addWidget(self.req_edit, 1)
        send_btn = QPushButton("生成应答")
        send_btn.setObjectName("primary")
        send_btn.clicked.connect(self._offline_send)
        row.addWidget(send_btn)
        layout.addLayout(row)

        quick = QHBoxLayout()
        quick.setSpacing(8)
        for text, handler in (
            ("读 114 起 6 个", lambda: self._quick_read(114, 6)),
            ("读 200 起 2 个", lambda: self._quick_read(200, 2)),
            ("写入 203 = 0x55AA", lambda: self._quick_write(203, 0x55AA)),
            ("写入 202 = 10.00A", lambda: self._quick_write(202, 1000)),
        ):
            btn = QPushButton(text)
            btn.setObjectName("ghost")
            btn.clicked.connect(handler)
            quick.addWidget(btn)
        quick.addStretch(1)
        layout.addLayout(quick)

        self.tester_view = QPlainTextEdit()
        self.tester_view.setReadOnly(True)
        layout.addWidget(self.tester_view, 1)
        return page

    def _quick_read(self, start: int, count: int) -> None:
        from . import modbus
        frame = modbus.build_read_request(self.sim.address, start, count)
        self.req_edit.setText(modbus.format_hex(frame))
        self._offline_send()

    def _quick_write(self, addr: int, value: int) -> None:
        from . import modbus
        frame = modbus.build_write_request(self.sim.address, addr, [value])
        self.req_edit.setText(modbus.format_hex(frame))
        self._offline_send()

    def _offline_send(self) -> None:
        from . import modbus
        text = self.req_edit.text().strip().replace(",", " ").replace("0x", "").replace("0X", "")
        try:
            data = bytes.fromhex(text)
        except ValueError:
            self.tester_view.appendPlainText("报文格式错误：请输入十六进制字节，如 01 03 00 72 00 06 20 7D")
            return
        if not data:
            return
        self._log("rx", f"接收 {modbus.format_hex(data)}")
        result = self.sim.handle(data)
        lines = []
        if result.rx_desc:
            lines.append(f"解析：{result.rx_desc}")
        if result.error:
            lines.append(f"错误：{result.error}")
            self._log("err", result.error)
        if result.response:
            lines.append(f"应答：{modbus.format_hex(result.response)}")
            if result.tx_desc:
                lines.append(f"说明：{result.tx_desc}")
            self._log("tx", f"发送 {modbus.format_hex(result.response)}")
            if result.tx_desc:
                self._log("info", result.tx_desc)
        else:
            lines.append("应答：无（广播或地址不匹配）")
        self.tester_view.appendPlainText("\n".join(lines) + "\n")
        if result.rx_desc.startswith("写寄存器") and result.response:
            for addr in (118, 202, 203):
                for fn in self.addr_refreshers.get(addr, []):
                    fn()

    # ---------------- 串口 ----------------
    def _refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        self.port_combo.clear()
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            label = port.device
            if port.description and port.description != "n/a":
                label = f"{port.device}"
            self.port_combo.addItem(port.device, label)
        if current:
            self.port_combo.setCurrentText(current)
        elif ports:
            self.port_combo.setCurrentIndex(0)
        else:
            self.port_combo.setEditText("")
        self.port_combo.lineEdit().setPlaceholderText("COM1 / /dev/ttyUSB0")
        if not ports:
            self._log("info", "未检测到串口，可手动输入端口名（如 COM19）")

    def _start(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        port = self.port_combo.currentText().strip()
        if not port:
            show_message(self, QMessageBox.Warning, "BMS 模拟器", "请选择或输入串口名称。")
            return
        try:
            baud = int(self.baud_combo.currentText().strip())
        except ValueError:
            show_message(self, QMessageBox.Warning, "BMS 模拟器", "波特率无效。")
            return
        self.sim.address = self.addr_spin.value()
        self._apply_settings()
        self.worker = SerialWorker(self.sim, port, baud)
        self.worker.sig_log.connect(self._log)
        self.worker.sig_state.connect(self._on_serial_state)
        self.worker.sig_counters.connect(self._on_counters)
        self.worker.sig_values_changed.connect(self._on_values_changed)
        self.worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.addr_spin.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.state_label.setText("正在打开串口…")

    def _stop(self) -> None:
        if self.worker:
            self.worker.stop()
            self.worker = None
        self._on_serial_state(False, "已停止")

    def _on_serial_state(self, running: bool, message: str) -> None:
        if running:
            self.state_label.setText("运行中")
            self.dot_label.setStyleSheet("color:#16a34a;")
            self.detail_label.setText(
                f"· {message} · 地址 0x{self.sim.address:02X}")
        else:
            self.state_label.setText("已停止")
            self.dot_label.setStyleSheet("color:#a0a6ad;")
            if message != "已停止":
                self.detail_label.setText(f"· {message}")
                self.state_label.setStyleSheet("color:#dc2626;")
                show_message(self, QMessageBox.Critical, "BMS 模拟器", message)
            else:
                self.detail_label.setText("")
                self.state_label.setStyleSheet("")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.addr_spin.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.worker = None

    def _on_counters(self, rx: int, tx: int) -> None:
        self.counter_label.setText(f"接收 {rx} 帧 · 应答 {tx} 帧")

    def _on_values_changed(self) -> None:
        for addr in (118, 202, 203):
            for fn in self.addr_refreshers.get(addr, []):
                fn()

    def _build_status_bar(self) -> None:
        bar = self.statusBar()
        left = QLabel("响应参数已自动应用，串口运行中立即生效")
        bar.addWidget(left)
        self.bar_state = QLabel("已停止")
        bar.addPermanentWidget(self.bar_state)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.worker:
            self.worker.stop()
        event.accept()
