"""顺丰 BMS 从机模拟：把请求帧转换为应答帧（协议 V1.1）。"""
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
    def __init__(self, state: SimState, address: int = 1) -> None:
        self.state = state
        self.address = address

    def _exception(self, addr: int, func: int, code: int, rx_desc: str) -> SimResult:
        resp = modbus.build_exception(addr, func, code)
        return SimResult(resp, rx_desc, "", self._exception_text(code))

    def _silent(self, text: str) -> SimResult:
        return SimResult(None, text, "", "")

    def handle(self, frame: bytes) -> SimResult:
        st = self.state
        try:
            req = modbus.parse_request(frame)
        except modbus.FrameCRCError as exc:
            return SimResult(None, "", "", f"报文解析失败：{exc}")
        except modbus.RequestError as exc:
            if len(frame) >= 2 and frame[0] == self.address:
                return self._exception(self.address, frame[1], exc.code,
                                       f"报文非法：{exc}")
            return SimResult(None, "", "", f"报文非法：{exc}")

        addr, func = req.addr, req.func
        if addr != self.address:
            return self._silent(
                f"地址 0x{addr:02X} 不是本机地址（0x{self.address:02X}），不应答")

        if func not in modbus.SUPPORTED_FUNCS:
            code = st.settings.forced_exception or modbus.EXC_BAD_FUNC
            return self._exception(addr, func, code, f"功能码 0x{func:02X}")

        if st.settings.forced_exception:
            return self._exception(addr, func, st.settings.forced_exception,
                                   f"功能码 0x{func:02X}")

        if func == modbus.FUNC_COIL_READ:
            rx = f"读开关 0x{req.start:04X} 起 {req.count} 个"
            bits = st.read_coils(req.start, req.count)
            if bits is None:
                return self._exception(addr, func, modbus.EXC_BAD_ADDRESS, rx)
            resp = modbus.build_coil_read_response(addr, bits)
            on = sum(bits)
            return SimResult(resp, rx,
                             f"应答 {len(bits)} 个开关（{len(bits) // 8 + 1} 字节数据），"
                             f"其中 {on} 个为合")

        if func == modbus.FUNC_READ:
            rx = f"读寄存器 0x{req.start:04X} 起 {req.count} 个"
            if req.count < 1 or req.count > 125:
                return self._exception(addr, func, modbus.EXC_BAD_ADDRESS, rx)
            values = st.read_registers(req.start, req.count)
            if values is None:
                return self._exception(addr, func, modbus.EXC_BAD_ADDRESS, rx)
            resp = modbus.build_read_response(addr, values)
            return SimResult(resp, rx,
                             f"应答 {len(values)} 个寄存器（{len(values) * 2} 字节）")

        if func == modbus.FUNC_COIL_WRITE:
            rx = f"写开关 0x{req.start:04X} = {'合' if req.coil_on else '分'}"
            code = st.write_coil(req.start, req.coil_on)
            if code:
                return self._exception(addr, func, code, rx)
            return SimResult(frame, rx, "确认遥控，应答报文与请求相同")

        if func == modbus.FUNC_REG_WRITE:
            value = req.values[0] if req.values else 0
            rx = f"写单个寄存器 0x{req.start:04X} = {value}"
            if req.start >= R.DEVICE_ID_START:
                return self._exception(addr, func, modbus.EXC_BAD_ADDRESS, rx)
            code = st.write_registers(req.start, [value])
            if code:
                return self._exception(addr, func, code, rx)
            return SimResult(frame, rx, "确认遥调，应答报文与请求相同")

        if func == modbus.FUNC_COILS_WRITE:
            rx = f"写多路开关 0x{req.start:04X} 起 {req.count} 个"
            code = st.write_coils(req.start, req.values)
            if code:
                return self._exception(addr, func, code, rx)
            resp = modbus.build_coils_write_response(addr, req.start, req.count)
            return SimResult(resp, rx, f"确认写入 {req.count} 个开关")

        # 0x10 写多个寄存器
        rx = f"写多个寄存器 0x{req.start:04X} 起 {len(req.values)} 个"
        if req.start >= R.DEVICE_ID_START:
            return self._exception(addr, func, modbus.EXC_BAD_ADDRESS, rx)
        code = st.write_registers(req.start, req.values)
        if code:
            return self._exception(addr, func, code, rx)
        resp = modbus.build_write_response(addr, req.start, len(req.values))
        return SimResult(resp, rx, f"确认写入 {len(req.values)} 个寄存器")

    @staticmethod
    def _exception_text(code: int) -> str:
        name = {
            modbus.EXC_BAD_FUNC: "无效的报文类型",
            modbus.EXC_BAD_ADDRESS: "无效的数据地址（含长度越界）",
            modbus.EXC_BAD_VALUE: "写入的数据值无效",
            modbus.EXC_BUSY: "装置忙",
        }.get(code, "未知异常")
        return f"异常应答 0x{code:02X}（{name}）"
