"""模拟器内部寄存器状态（绿通 V1.9）。"""
from __future__ import annotations

import hashlib
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
        self.idle_time_ms = 0     # 0xFE33 中控下发的空闲时间（不落寄存器表）
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
                elif d.kind in ("cells", "temps"):
                    for i in range(d.count):
                        self.raw[d.addr + i] = int(d.default)
                elif d.kind in ("hexarr", "array"):
                    for i in range(d.count):
                        self.raw[d.addr + i] = int(d.default) & 0xFFFF
                elif d.fmt == "U32" or d.kind == "u32":
                    self.set_u32(d.addr, int(d.default))
                else:
                    self.set_u16(d.addr, int(d.default))
            # 未使用的单体按串数保留 0xFFFF
            cells = R.DEF_BY_ADDR[143]
            used = min(cells.count, self.raw[142])
            for i in range(cells.count):
                if i >= used:
                    self.raw[143 + i] = R.RESERVED_VALUE
        self.sync_charger_flag()

    # ---------- 充电器接入状态联动 ----------
    def set_charger_status(self, value: int) -> None:
        with self.lock:
            self.raw[203] = value & 0xFFFF
            self.sync_charger_flag()

    def sync_charger_flag(self) -> None:
        with self.lock:
            connected = self.raw[203] == 0x55AA
            status = self.raw[118] & 0xFFFF
            if connected:
                status |= (1 << 12)
            else:
                status &= ~(1 << 12)
            self.raw[118] = status

    # ---------- 签名联动 ----------
    def _clear_signature(self) -> None:
        for i in range(231, 263):
            self.raw[i] = 0
        self.raw[214] = 0

    def _make_signature(self) -> None:
        """写入 0x0100 到 #214 触发：按随机数生成伪 ECDSA 签名并置状态 0x02。"""
        nonce = b"".join(self.raw[215 + i].to_bytes(2, "big") for i in range(16))
        digest = hashlib.sha256(b"lvtong-sign" + nonce).digest()
        sig = digest + hashlib.sha256(digest).digest()   # r(32B) + s(32B)
        for i in range(32):
            self.raw[231 + i] = (sig[2 * i] << 8) | sig[2 * i + 1]
        self.raw[214] = 0x0002

    # ---------- 系统控制 ----------
    def _handle_sys_ctrl(self, value: int) -> None:
        if value == 0x0001:        # 软复位
            self.reset()
        elif value == 0x0002:      # 清除故障（仅限允许清除的软告警）
            self.raw[121] = self.raw[122] = 0
            self.raw[123] = self.raw[124] = 0
            self.raw[125] = 0
            self.raw[197] = self.raw[198] = 0
            self.raw[210] = 0
        elif value == 0x0003:      # 清零单次充/放电量
            self.raw[269] = self.raw[270] = 0
            self.raw[271] = self.raw[272] = 0
            self.raw[210] = 0
        else:                      # 命令执行后回到空闲
            self.raw[210] = 0

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
    @staticmethod
    def _writable(addr: int) -> bool:
        if addr in R.WRITABLE_SINGLES:
            return True
        return any(lo <= addr < hi for lo, hi in R.WRITABLE_RANGES)

    def write_block(self, start: int, values: list[int]) -> int:
        """返回 0 表示成功，否则返回异常码。"""
        with self.lock:
            # 中控空闲时间（0xFE33）：轮巡规则专用，应答确认但不落寄存器表
            if start == R.ADDR_IDLE_TIME:
                if len(values) != 1:
                    return 0x02
                self.idle_time_ms = values[0] & 0xFFFF
                return 0

            end = start + len(values)
            if not values or end > R.TOTAL_REGISTERS:
                return 0x02
            if not all(self._writable(a) for a in range(start, end)):
                return 0x02

            for i, v in enumerate(values):
                self.raw[start + i] = v & 0xFFFF

            touched = range(start, end)
            # 写入新随机数 R → 清除数字签名并复位 #214（协议 PS 说明）
            if any(215 <= a < 231 for a in touched):
                self._clear_signature()
            # #203 充电器接入状态 → 同步 #118 bit12
            if 203 in touched:
                self.sync_charger_flag()
            # #210 系统控制
            if 210 in touched:
                self._handle_sys_ctrl(self.raw[210])
            # #214 高字节写 0x01 → 开始签名
            if 214 in touched and (self.raw[214] >> 8) == 0x01:
                self._make_signature()
            return 0
