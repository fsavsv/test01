"""Modbus RTU 编解码（0x03 读保持寄存器 / 0x10 写多个寄存器）。"""
from __future__ import annotations

FUNC_READ = 0x03
FUNC_WRITE = 0x10

EXC_UNSUPPORTED = 0x01   # 不支持的功能码
EXC_BAD_ADDRESS = 0x02   # 寄存器地址无效
EXC_BAD_VALUE = 0x03     # 数据值超出范围


def crc16(data: bytes) -> int:
    """协议第 5 章给出的 Modbus CRC16：初值 0xFFFF，多项式 0xA001。"""
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
    return len(frame) >= 4 and crc16(frame[:-2]) == (frame[-1] << 8 | frame[-2])


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
    body = bytes((addr & 0xFF, FUNC_WRITE,
                  start >> 8, start & 0xFF,
                  count >> 8, count & 0xFF))
    return with_crc(body)


def build_exception(addr: int, func: int, code: int) -> bytes:
    return with_crc(bytes((addr & 0xFF, (func | 0x80) & 0xFF, code & 0xFF)))


def parse_request(frame: bytes):
    """解析主机请求，返回 (addr, func, start, count, values) 或抛 ValueError。"""
    if len(frame) < 4:
        raise ValueError("报文长度不足")
    if not check_crc(frame):
        raise ValueError("CRC 校验失败")
    addr, func = frame[0], frame[1]
    if func == FUNC_READ:
        if len(frame) != 8:
            raise ValueError("0x03 请求长度应为 8 字节")
        start = (frame[2] << 8) | frame[3]
        count = (frame[4] << 8) | frame[5]
        return addr, func, start, count, []
    if func == FUNC_WRITE:
        if len(frame) < 9:
            raise ValueError("0x10 请求长度不足")
        start = (frame[2] << 8) | frame[3]
        count = (frame[4] << 8) | frame[5]
        byte_count = frame[6]
        body = frame[7:-2]
        if len(body) != byte_count or byte_count != count * 2:
            raise ValueError("0x10 字节数与寄存器数量不匹配")
        values = [(body[i] << 8) | body[i + 1] for i in range(0, len(body), 2)]
        return addr, func, start, count, values
    return addr, func, 0, 0, []


def format_hex(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)
