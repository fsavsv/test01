"""串口接收线程：按 10ms 帧间隔切帧，交由模拟器应答。"""
from __future__ import annotations

import time

import serial
from PySide6.QtCore import QThread, Signal

from . import modbus
from .simulator import Simulator


class SerialWorker(QThread):
    sig_log = Signal(str, str)          # level: rx/tx/err/info, text
    sig_state = Signal(bool, str)       # running, message
    sig_counters = Signal(int, int)     # rx frames, tx frames
    sig_values_changed = Signal()

    FRAME_GAP = 0.012

    def __init__(self, sim: Simulator, port: str, baud: int) -> None:
        super().__init__()
        self.sim = sim
        self.port = port
        self.baud = baud
        self._stop = False
        self.rx_count = 0
        self.tx_count = 0

    def stop(self) -> None:
        self._stop = True
        self.wait(1000)

    def run(self) -> None:
        try:
            ser = serial.Serial(
                port=self.port, baudrate=self.baud,
                bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE, timeout=0.005,
                write_timeout=0.5,
            )
        except Exception as exc:  # 串口打开失败
            self.sig_state.emit(False, f"打开串口失败：{exc}")
            return

        self.sig_state.emit(True, f"{self.port} · {self.baud} · 8N1")
        buf = bytearray()
        last_rx = 0.0
        try:
            while not self._stop:
                waiting = ser.in_waiting
                data = ser.read(waiting if waiting else 1)
                if data:
                    buf += data
                    last_rx = time.monotonic()
                if buf and (time.monotonic() - last_rx) >= self.FRAME_GAP:
                    frame = bytes(buf)
                    buf.clear()
                    self._process(ser, frame)
        except Exception as exc:
            self.sig_log.emit("err", f"串口异常：{exc}")
        finally:
            try:
                ser.close()
            except Exception:
                pass
            self.sig_state.emit(False, "已停止")

    def _process(self, ser: serial.Serial, frame: bytes) -> None:
        self.rx_count += 1
        self.sig_log.emit("rx", f"接收 {modbus.format_hex(frame)}")
        result = self.sim.handle(frame)
        if result.rx_desc:
            self.sig_log.emit("info", result.rx_desc)
        if result.error:
            self.sig_log.emit("err", result.error)
        delay = self.sim.state.settings.delay_ms
        if delay > 0:
            time.sleep(delay / 1000.0)
        if result.response:
            try:
                ser.write(result.response)
                ser.flush()
            except Exception as exc:
                self.sig_log.emit("err", f"发送失败：{exc}")
                return
            self.tx_count += 1
            self.sig_log.emit("tx", f"发送 {modbus.format_hex(result.response)}")
            if result.tx_desc:
                self.sig_log.emit("info", result.tx_desc)
            if result.rx_desc.startswith("写寄存器"):
                self.sig_values_changed.emit()
        self.sig_counters.emit(self.rx_count, self.tx_count)
