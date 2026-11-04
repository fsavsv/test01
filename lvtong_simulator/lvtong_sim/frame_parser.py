"""增量 Modbus RTU 帧组装。

不依赖字节间隔切帧：USB-RS485 转换器的 latency timer 常会产生
10–20ms 的字节间空隙，按固定间隔切帧会把一帧拆成多段。
"""
from __future__ import annotations

from . import modbus


class FrameAssembler:
    """从连续字节流中提取完整、CRC 正确的 0x03 / 0x10 请求帧。"""

    COMPLETE_TIMEOUT = 0.4   # 秒，9600bps 下最长请求约 265ms

    def __init__(self) -> None:
        self.buf = bytearray()
        self.last_rx = 0.0
        self.crc_errors: list[str] = []

    def feed(self, data: bytes, now: float) -> list[bytes]:
        self.buf += data
        self.last_rx = now
        return self._extract()

    def has_pending(self) -> bool:
        return bool(self.buf)

    def age(self, now: float) -> float:
        return now - self.last_rx

    def expire(self) -> bytes:
        """超时仍未组帧的残留数据。"""
        data = bytes(self.buf)
        self.buf.clear()
        return data

    def pop_errors(self) -> list[str]:
        errors, self.crc_errors = self.crc_errors, []
        return errors

    def _extract(self) -> list[bytes]:
        frames: list[bytes] = []
        buf = self.buf
        while True:
            start = self._find_candidate()
            if start is None:
                # 没有候选帧头，保留最后 1 字节等待后续数据
                if len(buf) > 1:
                    del buf[:-1]
                return frames
            aligned = start == 0
            if start:
                del buf[:start]

            state, length = self._validate(0)
            if state == "wait":
                return frames
            if state == "bad":
                if aligned and length:
                    self.crc_errors.append(
                        f"CRC 校验失败：{modbus.format_hex(bytes(buf[:length]))}")
                    del buf[:length]
                else:
                    del buf[0]
                continue
            frames.append(bytes(buf[:length]))
            del buf[:length]

    def _find_candidate(self) -> int | None:
        buf = self.buf
        for i in range(len(buf) - 1):
            if buf[i] <= 247 and buf[i + 1] in (modbus.FUNC_READ, modbus.FUNC_WRITE):
                return i
        return None

    def _validate(self, i: int) -> tuple[str, int]:
        buf = self.buf
        remaining = len(buf) - i
        func = buf[i + 1]
        if func == modbus.FUNC_READ:
            length = 8
            if remaining < length:
                return "wait", 0
            if modbus.check_crc(bytes(buf[i:i + length])):
                return "ok", length
            return "bad", length

        length = modbus.FUNC_WRITE
        if remaining < 7:
            return "wait", 0
        count = (buf[i + 4] << 8) | buf[i + 5]
        byte_count = buf[i + 6]
        if count < 1 or count > 123 or byte_count != count * 2:
            return "bad", 7
        total = 9 + byte_count
        if remaining < total:
            return "wait", 0
        if modbus.check_crc(bytes(buf[i:i + total])):
            return "ok", total
        return "bad", total
