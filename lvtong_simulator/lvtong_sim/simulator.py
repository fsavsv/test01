"""BMS 从机模拟：把收到的请求帧转换为应答帧（绿通 V1.9）。"""
from __future__ import annotations

from dataclasses import dataclass

from . import modbus
from . import registers as R
from .state import SimState


@dataclass
class SimResult:
    response: bytes | None
    rx_desc: str
    tx_desc: str
    error: str = ""


class Simulator:
    def __init__(self, state: SimState, address: int = 3) -> None:
        self.state = state
        self.address = address

    def _hex(self, values: list[int]) -> str:
        text = " ".join(f"{v:04X}" for v in values[:8])
        if len(values) > 8:
            text += " …"
        return text

    def _exception(self, addr: int, func: int, code: int, rx_desc: str) -> SimResult:
        resp = None if addr == 0 else modbus.build_exception(addr, func, code)
        return SimResult(resp, rx_desc, "", self._exception_text(code))

    def handle(self, frame: bytes) -> SimResult:
        st = self.state
        try:
            addr, func, start, count, values = modbus.parse_request(frame)
        except ValueError as exc:
            return SimResult(None, "", "", f"报文解析失败：{exc}")

        if addr not in (0, self.address):
            return SimResult(
                None,
                f"地址 0x{addr:02X} 不是本机地址（0x{self.address:02X}），忽略",
                "", "",
            )

        if func not in (modbus.FUNC_READ, modbus.FUNC_WRITE):
            code = st.settings.forced_exception or modbus.EXC_UNSUPPORTED
            return self._exception(addr, func, code, f"功能码 0x{func:02X}")

        if st.settings.forced_exception:
            return self._exception(addr, func, st.settings.forced_exception,
                                   f"功能码 0x{func:02X}")

        if func == modbus.FUNC_READ:
            rx_desc = f"读寄存器 0x{start:04X} 起 {count} 个"
            if count < 1 or count > 125:
                return self._exception(addr, func, modbus.EXC_BAD_VALUE, "读寄存器 数量越界")
            if start < 0 or start + count > R.TOTAL_REGISTERS:
                return self._exception(addr, func, modbus.EXC_BAD_ADDRESS, rx_desc)
            data = st.read_block(start, count)
            if addr == 0:
                return SimResult(None, f"广播读 0x{start:04X}×{count}", "", "")
            resp = modbus.build_read_response(addr, data)
            return SimResult(
                resp, rx_desc,
                f"应答 {count} 个寄存器（{count * 2} 字节）：{self._hex(data)}",
            )

        # 0x10 写多个寄存器
        rx_desc = f"写寄存器 0x{start:04X} × {len(values)}：{self._hex(values)}"
        if start == R.ADDR_IDLE_TIME:
            rx_desc = f"中控空闲时间（0x{R.ADDR_IDLE_TIME:04X}）= {values[0] if values else 0} ms"
        code = st.write_block(start, values)
        if code:
            return self._exception(addr, func, code, rx_desc)
        if addr == 0:
            return SimResult(None, f"广播{rx_desc}", "", "")
        resp = modbus.build_write_response(addr, start, len(values))
        tx_desc = f"确认写入 0x{start:04X} × {len(values)}"
        if 210 <= start < 210 + len(values):
            tx_desc += "（系统控制命令已执行，#210 回到空闲）"
        if 214 <= start < 214 + len(values) and st.get_u16(214) == 0x0002:
            tx_desc += "（签名完成，#231–262 已生成）"
        return SimResult(resp, rx_desc, tx_desc)

    @staticmethod
    def _exception_text(code: int) -> str:
        name = {
            0x01: "不支持的功能码",
            0x02: "寄存器地址无效",
            0x03: "数据值超出范围",
        }.get(code, "未知异常")
        return f"异常应答 0x{code:02X}（{name}）"
