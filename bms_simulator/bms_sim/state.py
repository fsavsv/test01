"""模拟器内部寄存器状态。"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from . import registers as R


@dataclass
class Settings:
    auto_link: bool = True        # 按协议自动联动（未接入 / 保护时请求值置 0）
    forced_exception: int = 0     # 0 表示正常应答
    delay_ms: int = 0             # 应答延时


class SimState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.raw = [R.RESERVED_VALUE] * R.TOTAL_REGISTERS
        self.settings = Settings()
        self.reset()

    # ---------- 基础读写 ----------
    def set_u16(self, addr: int, value: int) -> None:
        with self.lock:
            self.raw[addr] = value & 0xFFFF

    def get_u16(self, addr: int) -> int:
        with self.lock:
            return self.raw[addr]

    def set_u32(self, addr: int, value: int) -> None:
        with self.lock:
            value &= 0xFFFFFFFF
            self.raw[addr] = (value >> 16) & 0xFFFF   # 高字在前
            self.raw[addr + 1] = value & 0xFFFF

    def get_u32(self, addr: int) -> int:
        with self.lock:
            return (self.raw[addr] << 16) | self.raw[addr + 1]

    def set_ascii(self, addr: int, text: str, count: int = 12) -> None:
        data = (text.encode("ascii", "replace") + b"\x00" * count * 2)[:count * 2]
        with self.lock:
            for i in range(count):
                self.raw[addr + i] = (data[2 * i] << 8) | data[2 * i + 1]

    def get_ascii(self, addr: int, count: int = 12) -> str:
        with self.lock:
            data = b""
            for i in range(count):
                v = self.raw[addr + i]
                data += bytes(((v >> 8) & 0xFF, v & 0xFF))
        return data.decode("ascii", "replace").rstrip("\x00")

    # ---------- 复位 ----------
    def reset(self) -> None:
        with self.lock:
            self.raw = [R.RESERVED_VALUE] * R.TOTAL_REGISTERS
            for d in R.DEFS:
                if d.kind == "ascii":
                    self.set_ascii(d.addr, str(d.default), d.count)
                elif d.kind == "cells":
                    for i in range(d.count):
                        self.raw[d.addr + i] = d.default
                elif d.kind in ("temps",):
                    for i in range(d.count):
                        self.raw[d.addr + i] = d.default
                elif d.fmt == "U32":
                    self.set_u32(d.addr, int(d.default))
                else:
                    self.set_u16(d.addr, int(d.default))
            # 未使用的单体按串数保留 0xFFFF
            cells = R.DEF_BY_ADDR[143]
            used = min(32, self.raw[142])
            for i in range(32):
                if i >= used:
                    self.raw[143 + i] = R.RESERVED_VALUE
        self.sync_charger_flag()

    # ---------- 充电器接入状态联动 ----------
    def set_charger_status(self, value: int) -> None:
        self.raw[203] = value & 0xFFFF
        self.sync_charger_flag()

    def sync_charger_flag(self) -> None:
        connected = self.raw[203] == 0x55AA
        status = self.raw[118] & 0xFFFF
        if connected:
            status |= (1 << 12)
        else:
            status &= ~(1 << 12)
        self.raw[118] = status

    # ---------- 协议读 ----------
    def _charge_ok(self) -> bool:
        if self.raw[203] != 0x55AA:
            return False
        if self.raw[116] > 95:
            return False
        protect = self.get_u32(123)
        for bit in R.CHARGE_PROTECT_BITS:
            if protect & (1 << bit):
                return False
        return True

    def read_block(self, start: int, count: int) -> list[int]:
        with self.lock:
            values = [self.raw[start + i] & 0xFFFF for i in range(count)]
            if self.settings.auto_link:
                ok = self._charge_ok()
                for addr in (194, 200, 201):
                    if start <= addr < start + count and not ok:
                        values[addr - start] = 0
            return values

    # ---------- 协议写 ----------
    def write_block(self, start: int, values: list[int]) -> int:
        """返回 0 表示成功，否则返回异常码。"""
        with self.lock:
            if start not in (202, 203) or len(values) != 1:
                return 0x02
            if start == 203:
                self.set_charger_status(values[0])
            else:
                self.raw[202] = values[0] & 0xFFFF
            return 0
