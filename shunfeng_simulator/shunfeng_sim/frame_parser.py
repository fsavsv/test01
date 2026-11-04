"""增量 Modbus 帧组装（支持 0x01 / 0x03 / 0x05 / 0x06 / 0x0F / 0x10）。

不依赖字节间隔，避免 USB-RS485 转换器 latency timer 把一帧拆成多段。
"""
from __future__ import annotations

from . import modbus

FIXED_LEN_FUNCS = {
    modbus.FUNC_COIL_READ, modbus.FUNC_READ,
    modbus.FUNC_COIL_WRITE, modbus.FUNC_REG_WRITE,
}


class FrameAssembler:
    COMPLETE_TIMEOUT = 0.4      # 9600bps 下最长请求约 265ms

    def __init__(self) -> None:
        self.buf = bytearray()
        self.stamp = 0.0
        self._errors: list[str] = []

    def feed(self, data: bytes, now: float) -> list[bytes]:
        self.buf += data
        self.stamp = now
        return self._extract()

    def has_pending(self) -> bool:
        return bool(self.buf)

    def age(self, now: float) -> float:
        return now - self.stamp

    def expire(self) -> bytes:
        leftovers = bytes(self.buf)
        self.buf.clear()
        return leftovers

    def pop_errors(self) -> list[str]:
        errors, self._errors = self._errors, []
        return errors

    # ---------- 内部 ----------
    def _extract(self) -> list[bytes]:
        frames: list[bytes] = []
        while True:
            if len(self.buf) < 2:
                break
            idx = self._find_candidate()
            if idx is None:
                # 没有候选帧头，除最后一个字节外全丢弃（末字节可能是新帧的地址）
                if len(self.buf) > 1:
                    del self.buf[:-1]
                break
            if idx > 0:
                del self.buf[:idx]
            status, length = self._validate()
            if status == "wait":
                break
            if status == "ok":
                frames.append(bytes(self.buf[:length]))
                del self.buf[:length]
                continue
            # bad：先尝试在当前跨度内重新对齐到真实帧头，否则整帧丢弃
            offset = self._find_resync(length) if length else None
            if offset:
                self._errors.append(
                    f"CRC 校验失败，跳过 {offset} 字节后已重新对齐到后续帧"
                )
                del self.buf[:offset]
                continue
            if length:
                bad = bytes(self.buf[:length])
                self._errors.append(
                    f"CRC 校验失败，已丢弃 {length} 字节：{modbus.format_hex(bad[:24])}"
                )
                del self.buf[:length]
            else:
                del self.buf[:1]
        return frames

    def _find_resync(self, span: int) -> int | None:
        """在前 span 个字节内寻找 CRC 正确的真实帧起点，返回偏移。"""
        limit = min(span, len(self.buf) - 8)
        for start in range(1, limit + 1):
            if not (self.buf[start] <= 247
                    and self.buf[start + 1] in modbus.SUPPORTED_FUNCS):
                continue
            func = self.buf[start + 1]
            length = 8 if func in FIXED_LEN_FUNCS else 9 + self.buf[start + 6]
            if start + length <= len(self.buf) and \
                    modbus.check_crc(bytes(self.buf[start:start + length])):
                return start
        return None

    def _find_candidate(self) -> int | None:
        for i in range(len(self.buf) - 1):
            if self.buf[i] <= 247 and self.buf[i + 1] in modbus.SUPPORTED_FUNCS:
                return i
        return None

    def _validate(self) -> tuple[str, int]:
        addr, func = self.buf[0], self.buf[1]
        if addr > 247 or func not in modbus.SUPPORTED_FUNCS:
            return "bad", 0
        if func in FIXED_LEN_FUNCS:
            length = 8
        else:
            if len(self.buf) < 7:
                return "wait", 0
            length = 9 + self.buf[6]
            if length > 255:
                return "bad", 0
        if len(self.buf) < length:
            return "wait", length
        if not modbus.check_crc(bytes(self.buf[:length])):
            return "bad", length
        return "ok", length
