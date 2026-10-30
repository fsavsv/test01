"""BMS 从机模拟：把收到的请求帧转换为应答帧。"""
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

    def handle(self, frame: bytes) -> SimResult:
        st = self.state
        try:
            addr, func, start, count, values = modbus.parse_request(frame)
        except ValueError as exc:
            return SimResult(None, f"接收 {modbus.format_hex(frame)}", "", str(exc))

        if addr not in (0, self.address):
            return SimResult(
                None,
                f"地址 0x{addr:02X} 不是本机地址（0x{self.address:02X}），忽略",
                "", "",
            )

        if func not in (modbus.FUNC_READ, modbus.FUNC_WRITE):
            if st.settings.forced_exception:
                code = st.settings.forced_exception
            else:
                code = modbus.EXC_UNSUPPORTED
            resp = None if addr == 0 else modbus.build_exception(addr, func, code)
            return SimResult(resp, f"功能码 0x{func:02X}", "", self._exception_text(code))

        if st.settings.forced_exception:
            code = st.settings.forced_exception
            resp = None if addr == 0 else modbus.build_exception(addr, func, code)
            return SimResult(resp, f"功能码 0x{func:02X}", "", self._exception_text(code))

        if func == modbus.FUNC_READ:
            if count < 1 or count > 125:
                code = modbus.EXC_BAD_VALUE
                resp = None if addr == 0 else modbus.build_exception(addr, func, code)
                return SimResult(resp, "读寄存器 数量越界", "", self._exception_text(code))
            if start < 0 or start + count > R.TOTAL_REGISTERS:
                code = modbus.EXC_BAD_ADDRESS
                resp = None if addr == 0 else modbus.build_exception(addr, func, code)
                return SimResult(resp, f"读寄存器 起始 0x{start:04X} 数量 {count}", "",
                                 self._exception_text(code))
            data = st.read_block(start, count)
            if addr == 0:
                return SimResult(None, f"广播读 0x{start:04X}×{count}", "", "")
            resp = modbus.build_read_response(addr, data)
            return SimResult(
                resp,
                f"读寄存器 0x{start:04X} 起 {count} 个",
                f"应答 {count} 个寄存器（{count * 2} 字节）：{self._hex(data)}",
            )

        # 0x10 写多个寄存器
        code = st.write_block(start, values)
        if code:
            resp = None if addr == 0 else modbus.build_exception(addr, func, code)
            return SimResult(
                resp,
                f"写寄存器 0x{start:04X} × {len(values)}：{self._hex(values)}",
                "", self._exception_text(code),
            )
        if addr == 0:
            return SimResult(None,
                             f"广播写 0x{start:04X} × {len(values)}：{self._hex(values)}", "", "")
        resp = modbus.build_write_response(addr, start, len(values))
        return SimResult(
            resp,
            f"写寄存器 0x{start:04X} × {len(values)}：{self._hex(values)}",
            f"确认写入 0x{start:04X} × {len(values)}",
        )

    @staticmethod
    def _exception_text(code: int) -> str:
        name = {
            0x01: "不支持的功能码",
            0x02: "寄存器地址无效",
            0x03: "数据值超出范围",
        }.get(code, "未知异常")
        return f"异常应答 0x{code:02X}（{name}）"
