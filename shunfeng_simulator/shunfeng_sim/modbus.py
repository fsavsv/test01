"""Modbus RTU 编解码：顺丰/铁塔协议 V1.1。

支持功能码：
0x01 读开关（遥信）
0x03 读寄存器（遥测）
0x05 写单路开关（遥控）
0x06 写单个寄存器（遥调）
0x0F 写多路开关
0x10 写多个寄存器
"""
from __future__ import annotations

from dataclasses import dataclass, field

FUNC_COIL_READ = 0x01
FUNC_READ = 0x03
FUNC_COIL_WRITE = 0x05
FUNC_REG_WRITE = 0x06
FUNC_COILS_WRITE = 0x0F
FUNC_WRITE = 0x10

SUPPORTED_FUNCS = (
    FUNC_COIL_READ, FUNC_READ, FUNC_COIL_WRITE,
    FUNC_REG_WRITE, FUNC_COILS_WRITE, FUNC_WRITE,
)

EXC_BAD_FUNC = 0x01       # 无效的报文类型
EXC_BAD_ADDRESS = 0x02    # 无效的数据地址，包含数据长度越界
EXC_BAD_VALUE = 0x03      # 写入的数据值无效
EXC_BUSY = 0x06           # 装置忙


class FrameCRCError(ValueError):
    """CRC 校验失败：按协议不应答。"""


class RequestError(ValueError):
    """结构正确（CRC 通过）但内容非法：应返回异常报文。"""

    def __init__(self, message: str, code: int = EXC_BAD_ADDRESS) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class Request:
    addr: int
    func: int
    start: int = 0
    count: int = 0
    values: list[int] = field(default_factory=list)   # 0x10 寄存器值 / 0x0F 位值(0/1)
    coil_on: bool = True                              # 0x05 合/分


def crc16(data: bytes) -> int:
    """初值 0xFFFF，多项式 0xA001（协议 3.4.2）。"""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def with_crc(payload: bytes) -> bytes:
    c = crc16(payload)
    return payload + bytes((c & 0xFF, (c >> 8) & 0xFF))  # 低字节在前


def check_crc(frame: bytes) -> bool:
    return len(frame) >= 4 and crc16(frame[:-2]) == ((frame[-1] << 8) | frame[-2])


def build_coil_read_request(addr: int, start: int, count: int) -> bytes:
    return with_crc(bytes((addr & 0xFF, FUNC_COIL_READ,
                           start >> 8, start & 0xFF,
                           count >> 8, count & 0xFF)))


def build_coil_read_response(addr: int, bits: list[int]) -> bytes:
    byte_count = (len(bits) + 7) // 8
    data = bytearray(byte_count)
    for i, bit in enumerate(bits):
        if bit:
            data[i // 8] |= 1 << (i % 8)
    return with_crc(bytes((addr & 0xFF, FUNC_COIL_READ, byte_count)) + bytes(data))


def build_coil_write_request(addr: int, coil: int, on: bool) -> bytes:
    value = 0xFF00 if on else 0x0000
    return with_crc(bytes((addr & 0xFF, FUNC_COIL_WRITE,
                           coil >> 8, coil & 0xFF,
                           value >> 8, value & 0xFF)))


def build_coils_write_request(addr: int, start: int, bits: list[int]) -> bytes:
    byte_count = (len(bits) + 7) // 8
    data = bytearray(byte_count)
    for i, bit in enumerate(bits):
        if bit:
            data[i // 8] |= 1 << (i % 8)
    body = bytes((addr & 0xFF, FUNC_COILS_WRITE,
                  start >> 8, start & 0xFF,
                  len(bits) >> 8, len(bits) & 0xFF, byte_count)) + bytes(data)
    return with_crc(body)


def build_single_write_request(addr: int, reg: int, value: int) -> bytes:
    return with_crc(bytes((addr & 0xFF, FUNC_REG_WRITE,
                           reg >> 8, reg & 0xFF,
                           value >> 8, value & 0xFF)))


def build_read_request(addr: int, start: int, count: int) -> bytes:
    return with_crc(bytes((addr & 0xFF, FUNC_READ,
                           start >> 8, start & 0xFF,
                           count >> 8, count & 0xFF)))


def build_write_request(addr: int, start: int, values: list[int]) -> bytes:
    body = bytearray((addr & 0xFF, FUNC_WRITE,
                      start >> 8, start & 0xFF,
                      len(values) >> 8, len(values) & 0xFF,
                      len(values) * 2))
    for v in values:
        body += bytes(((v >> 8) & 0xFF, v & 0xFF))
    return with_crc(bytes(body))


def build_read_response(addr: int, values: list[int]) -> bytes:
    body = bytearray((addr & 0xFF, FUNC_READ, len(values) * 2))
    for v in values:
        body += bytes(((v >> 8) & 0xFF, v & 0xFF))
    return with_crc(bytes(body))


def build_write_response(addr: int, start: int, count: int) -> bytes:
    return with_crc(bytes((addr & 0xFF, FUNC_WRITE,
                           start >> 8, start & 0xFF,
                           count >> 8, count & 0xFF)))


def build_coils_write_response(addr: int, start: int, count: int) -> bytes:
    return with_crc(bytes((addr & 0xFF, FUNC_COILS_WRITE,
                           start >> 8, start & 0xFF,
                           count >> 8, count & 0xFF)))


def build_exception(addr: int, func: int, code: int) -> bytes:
    return with_crc(bytes((addr & 0xFF, (func | 0x80) & 0xFF, code & 0xFF)))


def parse_request(frame: bytes) -> Request:
    if len(frame) < 4:
        raise FrameCRCError("报文长度不足")
    if not check_crc(frame):
        raise FrameCRCError("CRC 校验失败")
    addr, func = frame[0], frame[1]
    if func not in SUPPORTED_FUNCS:
        return Request(addr, func)

    if func in (FUNC_COIL_READ, FUNC_READ, FUNC_COIL_WRITE, FUNC_REG_WRITE):
        if len(frame) != 8:
            raise RequestError(f"0x{func:02X} 请求长度应为 8 字节")
        start = (frame[2] << 8) | frame[3]
        second = (frame[4] << 8) | frame[5]
        if func == FUNC_COIL_READ:
            return Request(addr, func, start, second, [])
        if func == FUNC_READ:
            return Request(addr, func, start, second, [])
        if func == FUNC_COIL_WRITE:
            if second not in (0x0000, 0xFF00):
                raise RequestError(f"开关控制命令 0x{second:04X} 无效", EXC_BAD_VALUE)
            return Request(addr, func, start, 1, [], coil_on=bool(second))
        return Request(addr, func, start, 1, [second])   # 0x06

    # 0x0F / 0x10
    if len(frame) < 9:
        raise RequestError(f"0x{func:02X} 请求长度不足")
    start = (frame[2] << 8) | frame[3]
    count = (frame[4] << 8) | frame[5]
    byte_count = frame[6]
    body = frame[7:-2]
    if len(body) != byte_count:
        raise RequestError(f"0x{func:02X} 数据字节数与报文不符")
    if func == FUNC_WRITE:
        if byte_count != count * 2:
            raise RequestError("0x10 数据字节数应等于寄存器数量 × 2")
        values = [(body[i] << 8) | body[i + 1] for i in range(0, len(body), 2)]
        return Request(addr, func, start, count, values)
    if byte_count != (count + 7) // 8:
        raise RequestError("0x0F 数据字节数应等于 (开关个数 + 7) ÷ 8")
    bits = [(body[i // 8] >> (i % 8)) & 1 for i in range(count)]
    return Request(addr, func, start, count, bits)


def format_hex(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def format_hex_wrapped(data: bytes, per_line: int = 16, indent: str = "    ") -> str:
    chunks = [format_hex(data[i:i + per_line]) for i in range(0, len(data), per_line)]
    return f"\n{indent}".join(chunks)
