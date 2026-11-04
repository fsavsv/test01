"""模拟器内部状态：寄存器 0 – 28、设备 ID 1000 – 1012、开关量 0 – 51。"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from . import registers as R


@dataclass
class Settings:
    forced_exception: int = 0     # 0 表示正常应答；否则对全部指令返回该异常码
    delay_ms: int = 0             # 应答延时


class SimState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.settings = Settings()
        self.regs = [0] * R.METER_COUNT
        self.device = [0] * R.DEVICE_ID_COUNT
        self.coils = [0] * R.COIL_COUNT
        self.reset()

    # ---------- 基础 ----------
    def set_u16(self, addr: int, value: int) -> None:
        with self.lock:
            if 0 <= addr < R.METER_COUNT:
                self.regs[addr] = value & 0xFFFF
                if addr == 1:
                    self._trim_cells()

    def get_u16(self, addr: int) -> int:
        with self.lock:
            if 0 <= addr < R.METER_COUNT:
                return self.regs[addr]
            if R.DEVICE_ID_START <= addr < R.DEVICE_ID_START + R.DEVICE_ID_COUNT:
                return self.device[addr - R.DEVICE_ID_START]
            return 0

    def set_ascii(self, text: str) -> None:
        data = (text.encode("ascii", "replace") + b"\x00" * 26)[:26]
        with self.lock:
            for i in range(R.DEVICE_ID_COUNT):
                self.device[i] = (data[2 * i] << 8) | data[2 * i + 1]

    def get_ascii(self) -> str:
        with self.lock:
            data = b"".join(bytes(((v >> 8) & 0xFF, v & 0xFF)) for v in self.device)
        return data.decode("ascii", "replace").rstrip("\x00")

    def cell_count(self) -> int:
        with self.lock:
            return min(20, max(0, self.regs[1]))

    def _trim_cells(self) -> None:
        for i in range(20):
            if i >= min(20, max(0, self.regs[1])):
                self.regs[9 + i] = 0

    # ---------- 复位 ----------
    def reset(self) -> None:
        with self.lock:
            self.regs = [0] * R.METER_COUNT
            for d in R.REGS:
                if d.group == "device":
                    self.set_ascii(str(d.default))
                elif d.kind == "cells":
                    for i in range(d.count):
                        self.regs[d.addr + i] = int(d.default) & 0xFFFF
                else:
                    self.regs[d.addr] = int(d.default) & 0xFFFF
            self.coils = [0] * R.COIL_COUNT
            self._trim_cells()

    # ---------- 寄存器 ----------
    def read_registers(self, start: int, count: int) -> list[int] | None:
        with self.lock:
            if 0 <= start and start + count <= R.METER_COUNT:
                values = list(self.regs[start:start + count])
            elif (R.DEVICE_ID_START <= start
                  and start + count <= R.DEVICE_ID_START + R.DEVICE_ID_COUNT):
                base = start - R.DEVICE_ID_START
                values = list(self.device[base:base + count])
            else:
                return None
            # 电芯不足 20 节的部分按协议填 0
            for i in range(count):
                addr = start + i
                if 9 <= addr <= 28:
                    if addr - 9 >= self.cell_count():
                        values[i] = 0
            return values

    def write_registers(self, start: int, values: list[int]) -> int:
        with self.lock:
            if not values or start < 0 or start + len(values) > R.METER_COUNT:
                return 0x02
            for i, v in enumerate(values):
                self.regs[start + i] = v & 0xFFFF
            if start <= 1 < start + len(values):
                self._trim_cells()
            return 0

    # ---------- 开关量 ----------
    def read_coils(self, start: int, count: int) -> list[int] | None:
        with self.lock:
            if start < 0 or count < 1 or start + count > R.COIL_COUNT:
                return None
            return list(self.coils[start:start + count])

    def write_coil(self, addr: int, on: bool) -> int:
        with self.lock:
            if addr < 0 or addr >= R.COIL_COUNT:
                return 0x02
            self.coils[addr] = 1 if on else 0
            return 0

    def write_coils(self, start: int, bits: list[int]) -> int:
        with self.lock:
            if not bits or start < 0 or start + len(bits) > R.COIL_COUNT:
                return 0x02
            for i, bit in enumerate(bits):
                self.coils[start + i] = 1 if bit else 0
            return 0
