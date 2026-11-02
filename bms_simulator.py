# -*- coding: utf-8 -*-
"""仓控板 BMS 模拟器（CAN 2.0B 扩展帧 / 250 kbit/s）

每 5 秒（可通过界面修改）上传一次电池 BMS 信息，共 18 帧：
  0x18101070 ~ 0x18211070

只覆盖协议中的三个字段，其余字节原样使用真实电池数据：
  SOC           Byte 48-49   uint16 LE, 1%
  电芯最低温度  Byte 58-59   int16  LE, 1℃
  电芯最高温度  Byte 102-103 int16  LE, 1℃

运行依赖：Python 3.10+、tkinter；CANalyst-II 使用厂家 ControlCAN.dll，
其余接口需要 python-can。
"""

from __future__ import annotations

import ctypes
import os
import queue
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import can

CAN_BITRATE = 250_000
DEFAULT_CYCLE_SECONDS = 5.0
FRAME_GAP_SECONDS = 0.5

# 真实电池数据（142 字节，最后一帧 DLC=6）
BASE_PAYLOAD = bytes.fromhex(
	"00000000000000000000000047463031464246375730383130313030"
	"30333700000000000000000000000000cf1410000b00560164000000"
	"190015001b00030d020d020d030d000d010d020d030d020d000d010d"
	"010d020d010d010d020d000000000000000016000109dc0534170000"
	"000b0705010101000b00b80b980b0b00000000000000000000000000"
	"65ba"
)

SOC_OFFSET = 48
MIN_CELL_TEMP_OFFSET = 58
MAX_CELL_TEMP_OFFSET = 102

FRAME_IDS = tuple(0x18101070 + (i << 16) for i in range(18))

assert len(BASE_PAYLOAD) == 142, f"模板长度异常: {len(BASE_PAYLOAD)}"
assert len(FRAME_IDS) == 18


def _put_u16_le(buf: bytearray, offset: int, value: int) -> None:
    value &= 0xFFFF
    buf[offset] = value & 0xFF
    buf[offset + 1] = (value >> 8) & 0xFF


def build_payload(soc: int, temp_c: int) -> bytes:
    """在真实电池数据上覆盖 SOC 与电芯最高/最低温度。"""
    buf = bytearray(BASE_PAYLOAD)
    _put_u16_le(buf, SOC_OFFSET, soc)
    _put_u16_le(buf, MIN_CELL_TEMP_OFFSET, temp_c)
    _put_u16_le(buf, MAX_CELL_TEMP_OFFSET, temp_c)
    return bytes(buf)


def split_frames(payload: bytes) -> list[bytes]:
    frames = [payload[i : i + 8] for i in range(0, len(payload), 8)]
    if len(frames) != len(FRAME_IDS):
        raise ValueError(f"报文帧数异常: {len(frames)}")
    return frames


def send_cycle(bus: can.BusABC, payload: bytes, stop_event: threading.Event | None = None) -> int:
    """发送完整的一轮 18 帧，返回实际发送帧数。"""
    sent = 0
    frames = split_frames(payload)
    for index, data in enumerate(frames):
        if stop_event is not None and stop_event.is_set():
            break
        bus.send(
            can.Message(
                arbitration_id=FRAME_IDS[index],
                is_extended_id=True,
                data=data,
            ),
            timeout=1.0,
        )
        sent += 1
        if index < len(frames) - 1:
            time.sleep(FRAME_GAP_SECONDS)
    return sent


def _u16_hex(value: int) -> str:
    """按发送顺序（小端）返回 16 位值的十六进制，如 30 -> '1E 00'。"""
    value &= 0xFFFF
    return f"{value & 0xFF:02X} {value >> 8:02X}"


def frame_note(index: int, soc: int, temp_c: int) -> str:
    if index == 6:
        return f"SOC {soc}% = {_u16_hex(soc)}"
    if index == 7:
        return f"最低温度 {temp_c}℃ = {_u16_hex(temp_c)}"
    if index == 12:
        return f"最高温度 {temp_c}℃ = {_u16_hex(temp_c)}"
    return ""


# ------------------- 自动化验证 -------------------

AUTOTEST_REPORT_DIR = Path(__file__).resolve().parent / "test_reports"
AUTO_STEP_SECONDS = 30.0      # 每个 SOC/温度组合保持时长
AUTO_LOG_READ_DELAY = 20.0    # 切换组合后读取充电机指令日志的时间点
AUTO_SEND_PERIOD = 0.02       # 自动化验证期间的 BMS 发送周期（秒）
AUTO_SEGMENT_TIMEOUT = 5.0    # 等待按需读取日志片段的最长时间（秒）

# 充电电流期望值（原始值单位 0.01A）：3A=300、1.2A=120、0A=0
EXPECTED_CURRENT_RAW = {"3a": 300, "1.2a": 120, "0a": 0}
EXPECTED_CURRENT_TEXT = {"3a": "3A", "1.2a": "1.2A", "0a": "0A", "positive": ">0A"}
CURRENT_MATCH_TOLERANCE = 5   # 允许 ±0.05A 的偏差


@dataclass(frozen=True)
class TestStep:
    """一步验证：下发一组 SOC/温度，并给出终端应有的响应。"""

    soc: int
    temp: int
    expect: str  # "3a"/"1.2a"/"0a"：电流应为对应值；"positive"：只要求电流 > 0
    label: str
    category: str


# 关键边界与充电矩阵分档边界
TEMP_LOW_BOUNDARY = (-30, -20, -11, -10)
TEMP_HIGH_BOUNDARY = (55, 56, 60)
SOC_BOUNDARY = (0, 100)
MATRIX_TEMP_EDGES = (-5, 0, 5, 10, 15, 20, 25, 40, 45, 50)
MATRIX_SOC_EDGES = (0, 10, 20, 30, 40, 50, 60, 70, 80, 85, 90, 95, 100)


def expected_response(soc: int, temp: int) -> str:
    """按充电策略推断终端应下发的电流。

    规则：电量 0 或温度 ≤ -10℃ 时为 3A；温度 > 55℃ 时为 0A；
    电量为 100% 时为 1.2A；其余情况只要求电流 > 0。
    """
    if temp > 55:
        return "0a"
    if soc <= 0 or temp <= -10:
        return "3a"
    if soc >= 100:
        return "1.2a"
    return "positive"


def random_test_step(prev: TestStep | None, rng: random.Random) -> TestStep:
    """随机生成下一步，权重偏向关键边界、联合边界与边界/正常跳变。"""
    mode = rng.choices(
        ("boundary", "combined", "matrix_temp", "matrix_soc", "normal", "jump"),
        weights=(28, 12, 15, 15, 20, 10),
    )[0]
    if mode == "jump" and prev is not None:
        # 强制在“边界/联合边界”和“正常值”之间跳变
        mode = "normal" if prev.category in ("boundary", "combined") else "boundary"

    for _ in range(30):
        if mode == "combined":
            soc = 0
            temp = rng.choice(TEMP_LOW_BOUNDARY)
            expect = "3a"
            label = f"联合边界 SOC=0% 温度={temp}℃（应为 3A）"
        elif mode == "boundary":
            temp = rng.choice(TEMP_LOW_BOUNDARY + TEMP_HIGH_BOUNDARY)
            soc = rng.choice(SOC_BOUNDARY) if rng.random() < 0.6 else rng.randint(1, 99)
            expect = expected_response(soc, temp)
            label = f"随机边界 SOC={soc}% 温度={temp}℃"
        elif mode == "matrix_temp":
            soc = rng.randint(1, 100)
            temp = rng.choice(MATRIX_TEMP_EDGES)
            expect = expected_response(soc, temp)
            label = f"温度分档边界 SOC={soc}% 温度={temp}℃"
        elif mode == "matrix_soc":
            soc = rng.choice(MATRIX_SOC_EDGES)
            temp = rng.randint(-9, 54)
            expect = expected_response(soc, temp)
            label = f"SOC 分档边界 SOC={soc}% 温度={temp}℃"
        else:
            soc = rng.randint(1, 99)
            temp = rng.randint(-9, 54)
            expect = expected_response(soc, temp)
            label = f"正常随机 SOC={soc}% 温度={temp}℃"

        if prev is None or (soc, temp) != (prev.soc, prev.temp):
            return TestStep(soc, temp, expect, label, mode)

    # 极小概率连续重复：回退到固定正常值
    return TestStep(50, 25, "positive", "正常值 SOC=50% 温度=25℃", "normal")


# ------------------- CANalyst-II (ControlCAN.dll) -------------------

CANALYST_IFACE = "CANalyst-II（ZLG）"
VCI_USBCAN2 = 4

CONTROLCAN_CANDIDATES = (
    Path(__file__).resolve().parent / "ControlCAN.dll",
    Path(r"D:\Tool\CAN分析仪资料20220714\二次开发库文件\x64\ControlCAN.dll"),
    Path(r"C:\Windows\System32\ControlCAN.dll"),
    # 厂家示例源码里自带的那份通常是 32 位，排在真正的 x64 路径之后，避免误选
    Path(r"D:\Tool\CAN分析仪资料20220714\二次开发示例源代码\python(x64)\python3.8.0推荐\ControlCAN.dll"),
)


def _pe_machine(path: Path) -> int | None:
    """读取 PE 文件的机器类型：0x8664=AMD64(x64)，0x014c=i386(x86/32位)，读不到返回 None。"""
    try:
        with path.open("rb") as f:
            f.seek(0x3C)
            pe_offset = int.from_bytes(f.read(4), "little")
            f.seek(pe_offset + 4)  # 跳过 PE\\0\\0 签名
            return int.from_bytes(f.read(2), "little")
    except OSError:
        return None


def _describe_bits(machine: int | None) -> str:
    if machine is None:
        return "未知/读不到"
    if machine == 0x8664:
        return "64 位 (x64)"
    if machine == 0x014c:
        return "32 位 (x86)"
    return f"PE 0x{machine:04X}（非常规 DLL）"


def diagnose_controlcan_dlls() -> list[dict]:
    """扫描所有候选 ControlCAN.dll，返回每项的详情。"""
    expected = 0x8664 if sys.maxsize > 2**32 else 0x014c
    py_bits = 64 if sys.maxsize > 2**32 else 32
    result: list[dict] = []
    for path in CONTROLCAN_CANDIDATES:
        exists = path.is_file()
        machine = _pe_machine(path) if exists else None
        bits_match = (machine is not None and machine == expected)
        result.append({
            "path": str(path),
            "exists": exists,
            "machine": machine,
            "bits_desc": _describe_bits(machine),
            "bits_match": bits_match,
            "py_bits": py_bits,
        })
    return result


def diagnose_controlcan_text() -> str:
    items = diagnose_controlcan_dlls()
    py_bits = items[0]["py_bits"] if items else (64 if sys.maxsize > 2**32 else 32)
    header = f"当前 Python {py_bits} 位 · ControlCAN.dll 候选诊断："
    lines = [header]
    for item in items:
        if not item["exists"]:
            tag = "缺失"
            detail = ""
        elif item["bits_match"]:
            tag = "✓ 可用"
            detail = ""
        elif item["machine"] is None:
            tag = "?"
            detail = "(PE 头读不到)"
        else:
            tag = "× 位数不匹配"
            detail = f"(需要 {py_bits} 位，实际 {item['bits_desc']})"
        tail = f"  ← 优先候选" if item["bits_match"] else ""
        lines.append(f"  {tag}  {item['path']}  {item['bits_desc']}{detail}{tail}")
    return "\n".join(lines)


def find_controlcan_dll() -> str:
    """按当前 Python 位数优先挑选匹配的 ControlCAN.dll，避免 32/64 位不匹配导致 WinError 193。"""
    expected = 0x8664 if sys.maxsize > 2**32 else 0x014c  # x64 或 x86
    found: list[tuple[int, int, str]] = []  # (优先级, 原始索引, 路径)
    for idx, path in enumerate(CONTROLCAN_CANDIDATES):
        if not path.is_file():
            continue
        machine = _pe_machine(path)
        if machine == expected:
            priority = 0
        elif machine is None:
            priority = 1
        else:
            priority = 2
        found.append((priority, idx, str(path)))
    if not found:
        return ""
    found.sort()
    return found[0][2]


class _VCI_INIT_CONFIG(ctypes.Structure):
    _fields_ = [
        ("AccCode", ctypes.c_uint),
        ("AccMask", ctypes.c_uint),
        ("Reserved", ctypes.c_uint),
        ("Filter", ctypes.c_ubyte),
        ("Timing0", ctypes.c_ubyte),
        ("Timing1", ctypes.c_ubyte),
        ("Mode", ctypes.c_ubyte),
    ]


class _VCI_CAN_OBJ(ctypes.Structure):
    _fields_ = [
        ("ID", ctypes.c_uint),
        ("TimeStamp", ctypes.c_uint),
        ("TimeFlag", ctypes.c_ubyte),
        ("SendType", ctypes.c_ubyte),
        ("RemoteFlag", ctypes.c_ubyte),
        ("ExternFlag", ctypes.c_ubyte),
        ("DataLen", ctypes.c_ubyte),
        ("Data", ctypes.c_ubyte * 8),
        ("Reserved", ctypes.c_ubyte * 3),
    ]


class CanalystIIBus:
    """用厂家 ControlCAN.dll 发送扩展帧，接口与 python-can 的 Bus 兼容。"""

    def __init__(self, dll_path: str, channel: int = 0, bitrate: int = CAN_BITRATE,
                 device_index: int = 0) -> None:
        if bitrate != CAN_BITRATE:
            raise ValueError(f"CANalyst-II 当前仅支持 {CAN_BITRATE} bit/s。")
        if channel not in (0, 1):
            raise ValueError("CANalyst-II 通道只能为 0 或 1。")
        dll_file = Path(dll_path)
        if not dll_file.is_file():
            raise FileNotFoundError(f"找不到 ControlCAN.dll：{dll_path}")

        # 提前校验位数，避免 ctypes 抛出晦涩的 WinError 193（BadImageFormat）
        pe_machine = _pe_machine(dll_file)
        if pe_machine is not None:
            py_bits = 64 if sys.maxsize > 2**32 else 32
            if pe_machine not in (0x014c, 0x8664):
                raise ImportError(
                    f"无法识别 {dll_file.name} 的 PE 机器类型（0x{pe_machine:04X}），"
                    f"请确认这是 CANalyst-II 配套的 ControlCAN.dll。"
                )
            dll_bits = 64 if pe_machine == 0x8664 else 32
            if dll_bits != py_bits:
                raise ImportError(
                    f"ControlCAN.dll 位数与 Python 不匹配：当前 Python 是 {py_bits} 位，"
                    f"但 {dll_file.name} 是 {dll_bits} 位。\n"
                    f"请改用 {dll_bits} 位的 Python，或在“DLL 路径”处浏览选择 {py_bits} 位的 ControlCAN.dll。\n"
                    f"典型路径：ZLG 官方随盘一般同时提供 x64 和 x86 两个子目录。\n\n"
                    f"{diagnose_controlcan_text()}"
                )

        self._channel = channel
        self._device_index = device_index
        self._closed = False
        self._dll = ctypes.WinDLL(str(dll_file))
        self._dll.VCI_OpenDevice.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
        self._dll.VCI_OpenDevice.restype = ctypes.c_uint
        self._dll.VCI_InitCAN.argtypes = [
            ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(_VCI_INIT_CONFIG)
        ]
        self._dll.VCI_InitCAN.restype = ctypes.c_uint
        self._dll.VCI_StartCAN.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
        self._dll.VCI_StartCAN.restype = ctypes.c_uint
        self._dll.VCI_Transmit.argtypes = [
            ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(_VCI_CAN_OBJ), ctypes.c_uint
        ]
        self._dll.VCI_Transmit.restype = ctypes.c_uint
        self._dll.VCI_CloseDevice.argtypes = [ctypes.c_uint, ctypes.c_uint]
        self._dll.VCI_CloseDevice.restype = ctypes.c_uint

        if self._dll.VCI_OpenDevice(VCI_USBCAN2, device_index, 0) != 1:
            raise RuntimeError(
                "打开 CANalyst-II 失败。请确认设备已连接、驱动已安装，"
                "并关闭 CANTest / USB_CAN_Tool 等正在占用设备的软件。"
            )

        # 250 kbit/s（8 MHz 时钟）：Timing0=0x01, Timing1=0x1C
        config = _VCI_INIT_CONFIG(0, 0xFFFFFFFF, 0, 1, 0x01, 0x1C, 0)
        if self._dll.VCI_InitCAN(VCI_USBCAN2, device_index, channel, ctypes.byref(config)) != 1:
            self._dll.VCI_CloseDevice(VCI_USBCAN2, device_index)
            raise RuntimeError(f"CANalyst-II 通道 {channel} 初始化失败，请检查通道号。")
        if self._dll.VCI_StartCAN(VCI_USBCAN2, device_index, channel) != 1:
            self._dll.VCI_CloseDevice(VCI_USBCAN2, device_index)
            raise RuntimeError(f"CANalyst-II 通道 {channel} 启动失败。")

    def send(self, msg: can.Message, timeout: float | None = None) -> None:
        data = bytes(msg.data)
        if len(data) > 8:
            raise ValueError("经典 CAN 帧数据不能超过 8 字节。")
        obj = _VCI_CAN_OBJ()
        obj.ID = msg.arbitration_id
        obj.SendType = 0
        obj.RemoteFlag = 0
        obj.ExternFlag = 1 if msg.is_extended_id else 0
        obj.DataLen = len(data)
        for index, value in enumerate(data):
            obj.Data[index] = value
        ret = self._dll.VCI_Transmit(
            VCI_USBCAN2, self._device_index, self._channel, ctypes.byref(obj), 1
        )
        if ret != 1:
            raise RuntimeError(f"CANalyst-II 发送失败（VCI_Transmit 返回 {ret}）。")

    def shutdown(self) -> None:
        if not self._closed:
            self._dll.VCI_CloseDevice(VCI_USBCAN2, self._device_index)
            self._closed = True


# ------------------- 终端电流请求日志 -------------------

DEFAULT_LOG_PATH = "/sdcard/ZhiLaiBatteryExLvtong/logs/zl_batteryex.log"
ADB_CANDIDATES = (Path(r"D:\Tool\scrcpy\adb.exe"),)


def find_adb() -> str:
    for path in ADB_CANDIDATES:
        if path.is_file():
            return str(path)
    return shutil.which("adb") or ""


# 实际终端向充电机下发的 CAN 报文：
# [2026-10-21 17:33:19,477] - [INFO] - [...ChargerCommunicationManager] - [CAN发送数据:  0850108b, src=01 03 48 04 B0]
# 数据共 5 字节：第 1 字节保留；第 2-3 字节为电压（大端）；第 4-5 字节为电流（大端），实际电流 = 原始值 / 100
CHARGE_CAN_RE = re.compile(
    r"ChargerCommunicationManager\].*?\[CAN发送数据:\s*([0-9A-Fa-f]{8})\s*,\s*"
    r"src=((?:[0-9A-Fa-f]{2}\s*){5})\]"
)
TS_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}\]")

# 电流原始值单位为 0.01A，电压原始值单位为 0.1V
CURRENT_SCALE = 100.0
VOLTAGE_SCALE = 10.0
DEFAULT_CHARGE_CAN_ID = "0850108b"


def parse_can_id(text: str) -> int | None:
    """把 0850108b / 0x0850108B 解析为整数，空或非法返回 None。"""
    raw = text.strip().lower()
    if raw.startswith("0x"):
        raw = raw[2:]
    if not raw or len(raw) > 8 or any(ch not in "0123456789abcdef" for ch in raw):
        return None
    return int(raw, 16)


def parse_current_requests(text: str) -> dict[int, tuple]:
    """解析 CAN 下发报文，返回每个 CAN ID 最新一条电压/电流记录。

    记录格式：(时间戳, CAN ID, 电压原始值, 电流原始值, 数据字节串)
    """
    latest: dict[int, tuple] = {}
    for line in text.splitlines():
        match = CHARGE_CAN_RE.search(line)
        if not match:
            continue
        can_id = int(match.group(1), 16)
        parts = match.group(2).split()
        if len(parts) != 5:
            continue
        payload = bytes(int(part, 16) for part in parts)
        timestamp = TS_RE.match(line)
        latest[can_id] = (
            timestamp.group(1) if timestamp else "",
            can_id,
            int.from_bytes(payload[1:3], "big"),
            int.from_bytes(payload[3:5], "big"),
            " ".join(parts).upper(),
        )
    return latest


def adb_shell(adb: str, command: str) -> str:
    proc = subprocess.run(
        [adb, "shell", command],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(detail or f"adb 返回 {proc.returncode}")
    return proc.stdout


def log_size(adb: str, log_path: str) -> int:
    out = adb_shell(adb, f"stat -c %s '{log_path}'").strip()
    try:
        return int(out.splitlines()[-1])
    except (ValueError, IndexError):
        raise RuntimeError(f"无法读取日志大小：{out or '无输出'}")


def fetch_recent_requests(adb: str, log_path: str) -> dict[int, tuple]:
    """从日志尾部读取最近一批充电机下发报文（自动化验证也用它取最新记录）。"""
    for tail_bytes in (2_000_000, 8_000_000, 32_000_000, 128_000_000):
        text = adb_shell(
            adb, f"tail -c {tail_bytes} '{log_path}' | grep 'CAN发送数据' | tail -n 1000"
        )
        records = parse_current_requests(text)
        if records:
            return records
    return {}


def fetch_last_request(adb: str, log_path: str, can_id: int) -> tuple | None:
    """从日志尾部查找指定 CAN ID 的最后一条下发记录。"""
    id_text = f"{can_id:08x}"
    for tail_bytes in (2_000_000, 8_000_000, 32_000_000, 128_000_000):
        text = adb_shell(
            adb, f"tail -c {tail_bytes} '{log_path}' | grep -i '{id_text}' | tail -n 20"
        )
        records = parse_current_requests(text)
        if can_id in records:
            return records[can_id]
    return None


def fetch_new_requests(adb: str, log_path: str, offset: int) -> dict[int, tuple]:
    """只读取 offset 之后新增的内容，避免反复扫描几十 MB 的日志。"""
    # grep 无匹配时退出码为 1，用 || true 避免误判为读取失败
    text = adb_shell(adb, f"tail -c +{offset + 1} '{log_path}' | grep 'CAN发送数据' || true")
    return parse_current_requests(text)


# ----------------------------- GUI -----------------------------

BG = "#f3f4f6"
CARD = "#ffffff"
BORDER = "#e5e7eb"
FG = "#111827"
MUTED = "#6b7280"
ACCENT = "#2563eb"
DANGER = "#dc2626"

FONT = ("Microsoft YaHei UI", 10)
FONT_BOLD = ("Microsoft YaHei UI", 10, "bold")
FONT_TITLE = ("Microsoft YaHei UI", 17, "bold")
FONT_SMALL = ("Microsoft YaHei UI", 9)
MONO = ("Consolas", 9)


class BMSApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.stop_event = threading.Event()
        self._reschedule = threading.Event()
        self.worker: threading.Thread | None = None
        self.messages: queue.Queue = queue.Queue()
        self._values = (78, 23)  # 与真实数据一致: SOC=78%, 温度=23℃
        self._period = DEFAULT_CYCLE_SECONDS
        self._had_error = False
        self._last_send_error: str | None = None

        self.soc_var = tk.StringVar(value="78")
        self.temp_var = tk.StringVar(value="23")
        self.period_var = tk.StringVar(value="5")
        self.iface_var = tk.StringVar(value=CANALYST_IFACE)
        self.channel_var = tk.StringVar(value="0")
        self.dll_var = tk.StringVar(value=find_controlcan_dll())
        self.status_var = tk.StringVar(value="未开始")

        self.auto_period_var = tk.StringVar(value="0.02")
        self.auto_duration_var = tk.StringVar(value="8")
        self.auto_status_var = tk.StringVar(value="空闲 · 未开始自动化验证")
        self.auto_file_var = tk.StringVar(value="")

        # 终端日志与自动化验证共享的状态
        self._latest_records: dict[int, tuple] = {}
        self._record_rev = 0
        self._log_error_text = ""
        self._auto_segment_request: int | None = None
        self._auto_segment_token = 0
        self._auto_segment_dispatched = False
        self._auto_segment_done = False
        self._auto_segment_record: tuple | None = None
        self._auto_segment_error = ""
        self._auto_running = False
        self._auto_job: str | None = None
        self._auto_file: Path | None = None
        self._auto_step: TestStep | None = None
        self._auto_rng = random.Random()
        self._auto_seed = 0
        self._auto_duration = 8 * 3600.0
        self._auto_index = 0
        self._auto_pass = 0
        self._auto_fail = 0
        self._auto_error = 0
        self._auto_consecutive_errors = 0
        self._auto_can_id = int(DEFAULT_CHARGE_CAN_ID, 16)
        self._auto_period = AUTO_SEND_PERIOD
        self._auto_started_sender = False
        self._auto_prev_values = self._values
        self._auto_prev_period = self._period
        self._auto_seen_error: str | None = None
        self._auto_sent_cycles = 0
        self._auto_phase = "sampling"
        self._auto_read_at = 0.0
        self._auto_next_at = 0.0
        self._auto_step_start = 0.0
        self._auto_started_time = 0.0
        self._auto_last_send = 0.0

        self.adb_var = tk.StringVar(value=find_adb())
        self.log_path_var = tk.StringVar(value=DEFAULT_LOG_PATH)
        self.can_id_var = tk.StringVar(value=DEFAULT_CHARGE_CAN_ID)
        self.auto_log_var = tk.BooleanVar(value=True)
        self.voltage_var = tk.StringVar(value="--")
        self.current_var = tk.StringVar(value="--")
        self._alloc_text = "尚未读取终端日志"
        self._fetch_text = "等待读取…"
        self.log_status_var = tk.StringVar(value=f"{self._alloc_text} · {self._fetch_text}")

        self._log_stop = threading.Event()
        self._log_wake = threading.Event()
        self._log_lock = threading.Lock()
        self._log_cfg = (
            self.adb_var.get().strip(),
            self.log_path_var.get().strip(),
            int(DEFAULT_CHARGE_CAN_ID, 16),
            True,
        )

        self._build_ui()

        # 启动时打印 ControlCAN.dll 诊断，并在所有候选都不匹配时自动回退到虚拟总线
        py_bits = 64 if sys.maxsize > 2**32 else 32
        diagnosis = diagnose_controlcan_dlls()
        has_match = any(item["bits_match"] for item in diagnosis)
        if self.iface_var.get() == CANALYST_IFACE and not has_match:
            self.iface_var.set("虚拟总线（测试）")
            self.channel_var.set("bms-sim")
            self._log(
                f"检测到所有候选 ControlCAN.dll 都无法在当前 {py_bits} 位 Python 下加载，"
                f"已自动切换为【虚拟总线（测试）】。\n"
                f"{diagnose_controlcan_text()}\n"
                f"说明：虚拟总线可以正常发报文、跑自动化验证、不依赖任何硬件；"
                f"等你装好了 {py_bits} 位的 ControlCAN.dll，在界面接口下拉里切回 CANalyst-II 即可。"
            )
        else:
            self._log(diagnose_controlcan_text())

        self.soc_var.trace_add("write", self._on_input_changed)
        self.temp_var.trace_add("write", self._on_input_changed)
        self.period_var.trace_add("write", self._on_period_changed)
        self.adb_var.trace_add("write", self._on_log_cfg_changed)
        self.log_path_var.trace_add("write", self._on_log_cfg_changed)
        self.can_id_var.trace_add("write", self._on_log_cfg_changed)
        self.auto_log_var.trace_add("write", self._on_log_cfg_changed)
        self._refresh_preview(78, 23)
        self.root.after(100, self._poll_messages)

        threading.Thread(target=self._log_poll_loop, daemon=True).start()

    # ---------- UI ----------

    def _build_ui(self) -> None:
        self.root.title("仓控板 BMS 模拟器")
        self.root.geometry("1120x1000")
        self.root.minsize(1000, 900)
        self.root.configure(bg=BG)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=FONT, background=BG, foreground=FG)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Card.TLabel", background=CARD, foreground=FG)
        style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=FONT_SMALL)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=FONT_SMALL)
        style.configure("Title.TLabel", background=BG, foreground=FG, font=FONT_TITLE)
        style.configure("CardTitle.TLabel", background=CARD, foreground=FG, font=FONT_BOLD)
        style.configure("TLabelframe", background=CARD, bordercolor=BORDER, relief="solid")
        style.configure("TLabelframe.Label", background=CARD, foreground=FG, font=FONT_BOLD)
        style.configure("TButton", padding=(12, 7))
        style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff", bordercolor=ACCENT)
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("disabled", "#93c5fd")])
        style.configure("Danger.TButton", background=CARD, foreground=DANGER, bordercolor="#fecaca")
        style.map("Danger.TButton", background=[("active", "#fef2f2"), ("disabled", "#f3f4f6")])
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor=BORDER, padding=5)
        style.configure("TCombobox", fieldbackground="#ffffff", padding=5)
        style.configure("TSpinbox", fieldbackground="#ffffff", bordercolor=BORDER, padding=5)
        style.configure("Treeview", background=CARD, fieldbackground=CARD, rowheight=20, font=MONO)
        style.configure("Treeview.Heading", font=FONT_BOLD, background="#f9fafb", foreground=FG)

        outer = ttk.Frame(self.root)
        outer.pack(fill="both", expand=True, padx=16, pady=14)

        ttk.Label(outer, text="仓控板 BMS 模拟器", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="CAN 2.0B 扩展帧 · 250 kbit/s · 上报周期可配置（默认 5 秒） · 每轮 18 帧 · EXTID 0x18101070 ~ 0x18211070",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 12))

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=360)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self._build_can_card(left)
        self._build_data_card(left)
        self._build_action_card(left)
        self._build_log_card(left)
        self._build_preview_card(right)
        self._build_terminal_card(right)
        self._build_autotest_card(right)

    def _build_can_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text=" CAN 接口 ", padding=12)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="接口类型", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        iface = ttk.Combobox(
            card,
            textvariable=self.iface_var,
            values=(CANALYST_IFACE, "PCAN", "SLCAN", "Kvaser", "Vector", "虚拟总线（测试）"),
            state="readonly",
        )
        iface.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)
        iface.bind("<<ComboboxSelected>>", self._on_iface_changed)

        ttk.Label(card, text="通道", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(card, textvariable=self.channel_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 0), pady=4
        )

        self.dll_frame = ttk.Frame(card, style="Card.TFrame")
        self.dll_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=4)
        self.dll_frame.columnconfigure(1, weight=1)
        ttk.Label(self.dll_frame, text="DLL 路径", style="Card.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Entry(self.dll_frame, textvariable=self.dll_var).grid(
            row=0, column=1, sticky="ew", padx=(10, 6)
        )
        ttk.Button(self.dll_frame, text="浏览…", command=self._browse_dll).grid(row=0, column=2)

        ttk.Label(card, text="波特率", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Label(
            card,
            text="250 kbit/s（固定，采样点建议 87.5%）",
            style="CardMuted.TLabel",
            wraplength=260,
            justify="left",
        ).grid(row=3, column=1, sticky="w", padx=(10, 0), pady=4)

    def _build_data_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text=" 模拟数据 ", padding=12)
        card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="SOC（%）", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.soc_spin = ttk.Spinbox(
            card, from_=0, to=100, increment=1, textvariable=self.soc_var, width=10
        )
        self.soc_spin.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=4)

        ttk.Label(card, text="电芯温度（℃）", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.temp_spin = ttk.Spinbox(
            card, from_=-40, to=100, increment=1, textvariable=self.temp_var, width=10
        )
        self.temp_spin.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=4)

        ttk.Label(card, text="上报周期（秒）", style="Card.TLabel").grid(
            row=2, column=0, sticky="w", pady=4
        )
        self.period_spin = ttk.Spinbox(
            card, from_=0.1, to=3600, increment=0.5, textvariable=self.period_var, width=10
        )
        self.period_spin.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=4)

        ttk.Label(
            card,
            text="温度同时写入“电芯最低温度”和“电芯最高温度”；周期范围 0.1~3600 秒，运行中修改下一轮生效。",
            style="CardMuted.TLabel",
            wraplength=300,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _build_action_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text=" 运行 ", padding=12)
        card.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        self.start_btn = ttk.Button(
            card, text="开始发送", style="Accent.TButton", command=self.start
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.stop_btn = ttk.Button(
            card, text="停止", style="Danger.TButton", command=self.stop, state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.status_label = tk.Label(
            card,
            textvariable=self.status_var,
            bg=CARD,
            fg=MUTED,
            font=FONT_SMALL,
            anchor="w",
            justify="left",
            wraplength=340,
        )
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _build_log_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text=" 运行日志 ", padding=10)
        card.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            card,
            width=44,
            height=7,
            bg="#111827",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            font=MONO,
            wrap="char",
            state="disabled",
            padx=8,
            pady=6,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(card, orient="vertical", command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)
        self._log("就绪：选择 CAN 接口后点击“开始发送”。")

    def _build_preview_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text=" 报文预览（当前输入） ", padding=10)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        columns = ("idx", "cid", "dlc", "data", "note")
        self.tree = ttk.Treeview(card, columns=columns, show="headings", selectmode="browse")
        headings = {
            "idx": "帧",
            "cid": "CAN ID",
            "dlc": "DLC",
            "data": "数据（HEX）",
            "note": "说明",
        }
        widths = {"idx": 32, "cid": 88, "dlc": 42, "data": 200, "note": 170}
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor="center" if key != "data" else "w",
                             stretch=(key in ("data", "note")))
        self.tree.tag_configure("touched", background="#eff6ff", foreground="#1d4ed8")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        self.preview_items = []
        for index in range(len(FRAME_IDS)):
            item = self.tree.insert("", "end", values=("", "", "", "", ""))
            self.preview_items.append(item)

        ttk.Label(
            card,
            text="SOC → 48-49    电芯最低温度 → 58-59    电芯最高温度 → 102-103",
            style="CardMuted.TLabel",
            wraplength=520,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_terminal_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text=" 终端下发充电电压/电流（实时） ", padding=8)
        card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="ADB", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        adb_row = ttk.Frame(card, style="Card.TFrame")
        adb_row.grid(row=0, column=1, columnspan=5, sticky="ew", padx=(10, 0), pady=1)
        adb_row.columnconfigure(0, weight=1)
        ttk.Entry(adb_row, textvariable=self.adb_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(adb_row, text="浏览…", command=self._browse_adb).grid(
            row=0, column=1, padx=(6, 0)
        )

        ttk.Label(card, text="日志路径", style="Card.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Entry(card, textvariable=self.log_path_var).grid(
            row=1, column=1, columnspan=5, sticky="ew", padx=(10, 0), pady=1
        )

        ctrl_row = ttk.Frame(card, style="Card.TFrame")
        ctrl_row.grid(row=2, column=1, columnspan=5, sticky="w", padx=(10, 0), pady=(4, 0))
        ttk.Label(ctrl_row, text="充电机 CAN ID", style="Card.TLabel").pack(side="left")
        ttk.Entry(ctrl_row, textvariable=self.can_id_var, width=12).pack(
            side="left", padx=(4, 16)
        )
        ttk.Checkbutton(ctrl_row, text="自动刷新（2 秒）",
                        variable=self.auto_log_var).pack(side="left")
        ttk.Button(ctrl_row, text="立即刷新", command=self._refresh_log_now).pack(
            side="left", padx=(10, 0)
        )

        value_box = tk.Frame(card, bg="#f9fafb", highlightthickness=1,
                             highlightbackground=BORDER)
        value_box.grid(row=3, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        value_row = tk.Frame(value_box, bg="#f9fafb")
        value_row.pack(anchor="w", padx=12, pady=(6, 6))

        for title, unit, variable in (
            ("充电电压", "V", self.voltage_var),
            ("充电电流", "A", self.current_var),
        ):
            block = tk.Frame(value_row, bg="#f9fafb")
            block.pack(side="left", padx=(0, 28))
            tk.Label(block, text=title, bg="#f9fafb", fg=MUTED, font=FONT_SMALL).pack(anchor="w")
            line = tk.Frame(block, bg="#f9fafb")
            line.pack(anchor="w")
            tk.Label(line, textvariable=variable, bg="#f9fafb", fg=ACCENT,
                     font=("Consolas", 20, "bold")).pack(side="left")
            tk.Label(line, text=unit, bg="#f9fafb", fg=MUTED, font=FONT_SMALL).pack(
                side="left", padx=(6, 0), pady=(8, 0)
            )

        self.log_status_label = tk.Label(
            card,
            textvariable=self.log_status_var,
            bg=CARD,
            fg=MUTED,
            font=FONT_SMALL,
            anchor="w",
            justify="left",
            wraplength=640,
        )
        self.log_status_label.grid(row=4, column=0, columnspan=6, sticky="ew", pady=(8, 0))

    def _build_autotest_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text=" 自动化验证（温度 / SOC 边界） ", padding=10)
        card.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        card.columnconfigure(0, weight=1)

        controls = ttk.Frame(card, style="Card.TFrame")
        controls.grid(row=0, column=0, sticky="ew")
        ttk.Label(controls, text="发送周期（秒）", style="Card.TLabel").pack(side="left")
        self.auto_period_spin = ttk.Spinbox(
            controls, from_=0.02, to=10, increment=0.01,
            textvariable=self.auto_period_var, width=5,
        )
        self.auto_period_spin.pack(side="left", padx=(6, 10))
        ttk.Label(controls, text="运行时长（小时）", style="Card.TLabel").pack(side="left")
        self.auto_duration_spin = ttk.Spinbox(
            controls, from_=0, to=24, increment=0.5,
            textvariable=self.auto_duration_var, width=5,
        )
        self.auto_duration_spin.pack(side="left", padx=(6, 12))
        self.auto_start_btn = ttk.Button(
            controls, text="开始验证", style="Accent.TButton", command=self._auto_start
        )
        self.auto_start_btn.pack(side="left")
        self.auto_stop_btn = ttk.Button(
            controls, text="停止验证", style="Danger.TButton",
            command=self._auto_stop, state="disabled",
        )
        self.auto_stop_btn.pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="打开记录", command=self._auto_open_report).pack(
            side="left", padx=(12, 0)
        )

        self.auto_status_label = tk.Label(
            card,
            textvariable=self.auto_status_var,
            bg=CARD,
            fg=MUTED,
            font=FONT_SMALL,
            anchor="w",
            justify="left",
            wraplength=640,
        )
        self.auto_status_label.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        ttk.Label(
            card,
            text=f"随机下发 SOC/温度，每个组合保持 {AUTO_STEP_SECONDS:g} 秒后自动切换；"
                 f"BMS 每 {AUTO_SEND_PERIOD * 1000:g}ms 上报一轮；切换后 {AUTO_LOG_READ_DELAY:g} 秒"
                 "用 adb 拉取日志，查找最近一条指定 CAN ID（默认 0850108b）的下发指令，"
                 "解析电压/电流后记录（不记录原始日志）。"
                 "校验规则：SOC=0% 或温度≤-10℃ 应为 3A；温度>55℃ 应为 0A；"
                 "SOC=100% 应为 1.2A；其余情况电流应大于 0。"
                 "运行时长 0 表示直到手动停止，记录保存到 test_reports 目录。",
            style="CardMuted.TLabel",
            wraplength=640,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))

    # ---------- 输入与预览 ----------

    def _on_iface_changed(self, _event=None) -> None:
        defaults = {
            CANALYST_IFACE: "0",
            "PCAN": "PCAN_USBBUS1",
            "SLCAN": "COM3",
            "Kvaser": "0",
            "Vector": "0",
            "虚拟总线（测试）": "bms-sim",
        }
        iface = self.iface_var.get()
        self.channel_var.set(defaults.get(iface, ""))
        if iface == CANALYST_IFACE:
            self.dll_frame.grid()
        else:
            self.dll_frame.grid_remove()

    def _browse_dll(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 ControlCAN.dll",
            filetypes=(("DLL 文件", "*.dll"), ("所有文件", "*.*")),
        )
        if path:
            self.dll_var.set(path)

    def _read_values(self, show_error: bool = True) -> tuple[int, int] | None:
        try:
            soc = int(self.soc_var.get().strip())
            temp = int(self.temp_var.get().strip())
        except ValueError:
            if show_error:
                messagebox.showerror("输入无效", "SOC 和温度必须是整数。")
            return None
        if not 0 <= soc <= 100:
            if show_error:
                messagebox.showerror("输入无效", "SOC 范围应为 0 ~ 100。")
            return None
        if not -40 <= temp <= 100:
            if show_error:
                messagebox.showerror("输入无效", "温度范围应为 -40 ~ 100 ℃。")
            return None
        return soc, temp

    def _read_period(self, show_error: bool = True) -> float | None:
        try:
            period = float(self.period_var.get().strip())
        except ValueError:
            if show_error:
                messagebox.showerror("输入无效", "上报周期必须是数字（秒）。")
            return None
        if not 0.1 <= period <= 3600:
            if show_error:
                messagebox.showerror("输入无效", "上报周期范围应为 0.1 ~ 3600 秒。")
            return None
        return period

    def _on_period_changed(self, *_args) -> None:
        period = self._read_period(show_error=False)
        if period is not None:
            self._period = period

    def _on_input_changed(self, *_args) -> None:
        values = self._read_values(show_error=False)
        if values is None:
            return
        self._values = values
        self._refresh_preview(*values)

    def _refresh_preview(self, soc: int, temp: int) -> None:
        payload = build_payload(soc, temp)
        for index, (item, data) in enumerate(zip(self.preview_items, split_frames(payload))):
            note = frame_note(index, soc, temp)
            self.tree.item(
                item,
                values=(
                    index + 1,
                    f"0x{FRAME_IDS[index]:08X}",
                    len(data),
                    data.hex(" ").upper(),
                    note,
                ),
                tags=("touched",) if note else (),
            )

    # ---------- 终端请求电流 ----------

    def _browse_adb(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 adb.exe",
            filetypes=(("可执行文件", "*.exe"), ("所有文件", "*.*")),
        )
        if path:
            self.adb_var.set(path)

    def _on_log_cfg_changed(self, *_args) -> None:
        can_id = parse_can_id(self.can_id_var.get())
        with self._log_lock:
            old = self._log_cfg
            self._log_cfg = (
                self.adb_var.get().strip(),
                self.log_path_var.get().strip(),
                old[2] if can_id is None else can_id,
                bool(self.auto_log_var.get()),
            )
        self._log_wake.set()

    def _refresh_alloc_status(self, color: str) -> None:
        self.log_status_var.set(f"{self._alloc_text} · {self._fetch_text}")
        self.log_status_label.configure(fg=color)

    def _refresh_log_now(self) -> None:
        self._log_wake.set()

    def _log_poll_loop(self) -> None:
        last_error = None
        offset: int | None = None
        latest: dict[int, tuple] = {}
        revisions: dict[int, int] = {}
        current_source = None

        while not self._log_stop.is_set():
            with self._log_lock:
                adb, log_path, can_id, auto = self._log_cfg
            manual = self._log_wake.is_set()
            self._log_wake.clear()

            if not (auto or manual or self._auto_running):
                self._log_stop.wait(0.3)
                continue

            error = None
            if not adb:
                error = "未找到 adb.exe，请填写或浏览选择路径"
            elif not log_path:
                error = "请填写终端日志路径"
            else:
                source = (adb, log_path)
                if source != current_source:
                    # 设备或日志路径变化，重新建立读取位置
                    current_source = source
                    offset = None
                    latest = {}
                # 自动化按需读取：优先执行，组合开始 20s 时查找最近一条下发指令
                request = self._auto_segment_request
                if request is not None:
                    self._auto_segment_request = None
                    token = request
                    try:
                        record = fetch_last_request(adb, log_path, can_id)
                        self.messages.put(("auto_segment", (token, True, record)))
                    except subprocess.TimeoutExpired:
                        self.messages.put(
                            (
                                "auto_segment",
                                (token, False, "adb 读取超时（设备可能未连接）"),
                            )
                        )
                    except Exception as exc:
                        self.messages.put(
                            ("auto_segment", (token, False, str(exc)))
                        )

                try:
                    if offset is None:
                        latest = fetch_recent_requests(adb, log_path)
                        offset = log_size(adb, log_path)
                    else:
                        size = log_size(adb, log_path)
                        if size < offset:
                            # 日志被清空或轮转
                            latest = {}
                            offset = None
                            raise RuntimeError("日志已清空或轮转，正在重新读取")
                        if size > offset:
                            new_records = fetch_new_requests(adb, log_path, offset)
                            if new_records:
                                latest.update(new_records)
                                for cab in new_records:
                                    revisions[cab] = revisions.get(cab, 0) + 1
                            offset = size
                except subprocess.TimeoutExpired:
                    error = "adb 读取超时（设备可能未连接）"
                except Exception as exc:
                    error = f"{exc}"
                else:
                    record = latest.get(can_id)
                    if record is None:
                        self.messages.put(("current_none", can_id))
                    else:
                        revision = revisions.get(can_id, 0)
                        self.messages.put(("current", (can_id, record, revision)))
                    self.messages.put(("log_ok", time.strftime("%H:%M:%S")))

            if error is not None and error != last_error:
                self.messages.put(("log_error", error))
            last_error = error

            if not manual:
                # 自动化验证期间加快日志读取；有按需请求时立即唤醒
                self._log_wake.wait(1.0 if self._auto_running else 2.0)

    # ---------- 自动化验证 ----------

    def _read_auto_period(self) -> float | None:
        try:
            period = float(self.auto_period_var.get().strip())
        except ValueError:
            messagebox.showerror("自动化验证", "发送周期必须是数字（秒）。")
            return None
        if not 0.02 <= period <= 10:
            messagebox.showerror("自动化验证", "发送周期范围应为 0.02 ~ 10 秒。")
            return None
        return period

    def _read_auto_duration(self) -> float | None:
        try:
            hours = float(self.auto_duration_var.get().strip())
        except ValueError:
            messagebox.showerror("自动化验证", "运行时长必须是数字（小时）。")
            return None
        if not 0 <= hours <= 24:
            messagebox.showerror("自动化验证", "运行时长范围应为 0 ~ 24 小时（0 表示不限）。")
            return None
        return hours * 3600.0

    def _auto_start(self) -> None:
        if self._auto_running:
            return
        period = self._read_auto_period()
        if period is None:
            return
        duration = self._read_auto_duration()
        if duration is None:
            return
        can_id = parse_can_id(self.can_id_var.get())
        if can_id is None:
            messagebox.showerror(
                "自动化验证", "充电机 CAN ID 必须是十六进制，例如 0850108b。"
            )
            return
        adb = self.adb_var.get().strip()
        log_path = self.log_path_var.get().strip()
        if not adb:
            messagebox.showerror(
                "自动化验证", "请先配置 adb.exe 路径，自动化验证需要读取终端日志。"
            )
            return
        if not log_path:
            messagebox.showerror("自动化验证", "请先填写终端日志路径。")
            return

        seed = int(time.time())
        self._auto_seed = seed
        self._auto_step = None
        self._auto_rng = random.Random(seed)
        self._auto_duration = duration
        self._auto_index = 0
        self._auto_pass = self._auto_fail = self._auto_error = 0
        self._auto_consecutive_errors = 0
        self._auto_can_id = can_id
        self._auto_period = period
        self._auto_started_sender = False
        self._auto_prev_values = self._values
        self._auto_prev_period = self._period
        self._auto_seen_error = self._last_send_error
        self._auto_sent_cycles = 0
        self._auto_job = None
        self._auto_running = True
        self._auto_segment_request = None
        self._auto_segment_token = 0
        self._auto_segment_dispatched = False
        self._auto_segment_done = False
        self._auto_segment_record = None
        self._auto_segment_error = ""
        self._auto_started_time = time.monotonic()
        self._auto_last_send = time.monotonic()

        AUTOTEST_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        self._auto_file = AUTOTEST_REPORT_DIR / (
            f"bms_autotest_{time.strftime('%Y%m%d_%H%M%S')}.log"
        )
        self.auto_file_var.set(str(self._auto_file))
        duration_text = f"{duration / 3600:g} 小时" if duration > 0 else "直到手动停止"
        self._auto_write(
            f"随机自动化验证开始 · 接口={self.iface_var.get()} 通道={self.channel_var.get()} "
            f"充电机 CAN ID=0x{can_id:08X} 组合保持={AUTO_STEP_SECONDS:g}s "
            f"发送周期={period * 1000:g}ms 指令读取=切换后{AUTO_LOG_READ_DELAY:g}s "
            f"运行时长={duration_text} 随机种子={seed}"
        )

        self.auto_start_btn.configure(state="disabled")
        self.auto_stop_btn.configure(state="normal")
        for widget in (
            self.soc_spin, self.temp_spin, self.period_spin,
            self.auto_period_spin, self.auto_duration_spin,
        ):
            widget.configure(state="disabled")
        self.auto_status_var.set("正在检查终端日志…")
        self.auto_status_label.configure(fg=ACCENT)
        self._log("自动化验证：正在检查终端日志…")
        threading.Thread(
            target=self._auto_preflight, args=(adb, log_path), daemon=True
        ).start()

    def _auto_preflight(self, adb: str, log_path: str) -> None:
        try:
            records = fetch_recent_requests(adb, log_path)
        except Exception as exc:
            self.messages.put(("auto_preflight", (False, str(exc))))
        else:
            self.messages.put(("auto_preflight", (True, records)))

    def _auto_begin(self, records: dict[int, tuple]) -> None:
        for can_id, record in records.items():
            self._latest_records.setdefault(can_id, record)

        running = self.worker is not None and self.worker.is_alive()
        if not running:
            self.start()
            self._auto_started_sender = True
        if self.worker is None or not self.worker.is_alive():
            self._auto_finish("CAN 发送未能启动，自动化验证终止", ok=False, show_dialog=False)
            return

        self._period = self._auto_period
        self._auto_last_send = time.monotonic()
        self._auto_seen_error = self._last_send_error
        self._log(
            f"随机自动化验证开始：每个组合保持 {AUTO_STEP_SECONDS:g} 秒，"
            f"每 {self._auto_period * 1000:g}ms 上报一轮，切换后 {AUTO_LOG_READ_DELAY:g} 秒"
            f"用 adb 拉取日志并查找最近一条 CAN ID 0x{self._auto_can_id:08X} 的下发指令"
        )
        self._auto_begin_step()

    def _auto_begin_step(self) -> None:
        step = random_test_step(self._auto_step, self._auto_rng)
        self._auto_step = step
        self.soc_var.set(str(step.soc))
        self.temp_var.set(str(step.temp))
        self._values = (step.soc, step.temp)
        self._period = self._auto_period
        self._reschedule.set()

        self._auto_segment_token += 1
        self._auto_segment_request = None
        self._auto_segment_dispatched = False
        self._auto_segment_done = False
        self._auto_segment_record = None
        self._auto_segment_error = ""
        now = time.monotonic()
        self._auto_step_start = now
        self._auto_phase = "sampling"
        self._auto_read_at = now + AUTO_LOG_READ_DELAY
        self._auto_next_at = now + AUTO_STEP_SECONDS
        self.auto_status_var.set(
            f"{self._auto_elapsed_text()} · 第 {self._auto_index + 1} 步 · {step.label} · "
            f"保持 {AUTO_STEP_SECONDS:g}s，{AUTO_LOG_READ_DELAY:g}s 后读取充电机指令…"
        )
        self.auto_status_label.configure(fg=ACCENT)
        self._auto_schedule_tick()

    def _auto_elapsed_text(self) -> str:
        seconds = int(time.monotonic() - self._auto_started_time)
        return f"已运行 {seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"

    def _auto_schedule_tick(self) -> None:
        if self._auto_running and self._auto_job is None:
            self._auto_job = self.root.after(120, self._auto_tick)

    def _auto_tick(self) -> None:
        self._auto_job = None
        if not self._auto_running:
            return
        if self.worker is None or not self.worker.is_alive():
            self._auto_finish("CAN 发送线程已停止，自动化验证中止", ok=False, show_dialog=True)
            return
        if self._last_send_error and self._last_send_error != self._auto_seen_error:
            self._auto_seen_error = self._last_send_error
            self._auto_write(f"[错误] CAN 发送失败：{self._last_send_error}")
            self._auto_finish("CAN 发送失败，自动化验证中止", ok=False, show_dialog=True)
            return

        now = time.monotonic()
        if self._auto_duration > 0 and now - self._auto_started_time >= self._auto_duration:
            self._auto_finish(None, ok=True, show_dialog=True)
            return
        if now - self._auto_last_send > max(5.0, self._auto_period * 4 + 2):
            self._auto_write("[错误] 发送线程超过预期时间未完成发送")
            self._auto_finish("发送线程无响应，自动化验证中止", ok=False, show_dialog=True)
            return

        if self._auto_phase == "sampling":
            if now < self._auto_read_at:
                self._auto_schedule_tick()
                return
            if not self._auto_segment_dispatched:
                self._auto_segment_dispatched = True
                self._auto_segment_done = False
                self._auto_segment_record = None
                self._auto_segment_error = ""
                # 组合开始 20s：拉取日志尾部，取最近一条下发指令
                self._auto_segment_request = self._auto_segment_token
                self._log_wake.set()
                self.auto_status_var.set(
                    f"{self._auto_elapsed_text()} · 正在拉取终端日志，查找最近一条下发指令…"
                )
                self._auto_schedule_tick()
                return
            if not self._auto_segment_done:
                if now - self._auto_read_at < AUTO_SEGMENT_TIMEOUT:
                    self._auto_schedule_tick()
                    return
                self._auto_segment_done = True
                self._auto_segment_error = "读取超时"

            outcome = self._auto_evaluate(
                self._auto_segment_record
            ) or self._auto_timeout_outcome(
                self._auto_segment_record, self._auto_segment_error
            )
            self._auto_record(outcome)
            self._auto_index += 1
            if self._auto_consecutive_errors >= 10:
                self._auto_finish(
                    "连续 10 步无法验证（终端日志异常），自动化验证中止",
                    ok=False, show_dialog=True,
                )
                return
            self._auto_phase = "holding"
            self.auto_status_var.set(
                f"{self._auto_elapsed_text()} · 第 {self._auto_index} 步已记录 · "
                f"保持至 {AUTO_STEP_SECONDS:g}s 后切换下一组合"
            )
            self._auto_schedule_tick()
            return

        if now < self._auto_next_at:
            self._auto_schedule_tick()
            return
        self._auto_begin_step()

    def _auto_evaluate(self, record: tuple | None) -> dict | None:
        if record is None:
            return None

        step = self._auto_step
        _, _, voltage, current, _ = record
        desc = f"电压={voltage / VOLTAGE_SCALE:.1f}V 电流={current / CURRENT_SCALE:.2f}A"
        target = EXPECTED_CURRENT_RAW.get(step.expect)
        if target is None:
            if current > 0:
                return {"status": "PASS", "detail": f"终端指令 {desc}，电流大于 0"}
        elif abs(current - target) <= CURRENT_MATCH_TOLERANCE:
            return {
                "status": "PASS",
                "detail": f"终端指令 {desc}，符合期望 {EXPECTED_CURRENT_TEXT[step.expect]}",
            }
        return None

    def _auto_timeout_outcome(
        self, record: tuple | None, error: str = ""
    ) -> dict:
        step = self._auto_step
        can_text = f"CAN 0x{self._auto_can_id:08X}"

        if error:
            return {
                "status": "ERROR",
                "detail": f"无法验证：拉取终端日志失败（{error}）",
            }
        if record is None:
            return {
                "status": "ERROR",
                "detail": f"无法验证：终端日志中没有 {can_text} 的下发记录",
            }

        _, _, voltage, current, _ = record
        desc = f"电压={voltage / VOLTAGE_SCALE:.1f}V 电流={current / CURRENT_SCALE:.2f}A"
        expect = {
            "positive": "电流 > 0",
            "3a": "电流 = 3A",
            "1.2a": "电流 = 1.2A",
            "0a": "电流 = 0A",
        }[step.expect]
        return {
            "status": "FAIL",
            "detail": f"终端指令 {desc}，期望{expect}",
        }

    def _auto_record(self, outcome: dict) -> None:
        step = self._auto_step
        status = outcome["status"]
        elapsed = time.monotonic() - self._auto_step_start
        if status == "PASS":
            self._auto_pass += 1
            self._auto_consecutive_errors = 0
        elif status == "FAIL":
            self._auto_fail += 1
            self._auto_consecutive_errors = 0
        else:
            self._auto_error += 1
            self._auto_consecutive_errors += 1

        expect = {
            "positive": "电流>0",
            "3a": "电流=3A",
            "1.2a": "电流=1.2A",
            "0a": "电流=0A",
        }[step.expect]
        line = (
            f"步骤 {self._auto_index + 1} [{step.label}] 期望={expect} → {status} · "
            f"{outcome['detail']} · 组合开始后 {elapsed:.1f}s 读取"
        )
        self._auto_write(line)
        self._log(f"自动化验证 {line}")
        self.auto_status_var.set(
            f"{self._auto_elapsed_text()} · 通过 {self._auto_pass} · "
            f"失败 {self._auto_fail} · 错误 {self._auto_error}"
        )
        self.auto_status_label.configure(fg=DANGER if status != "PASS" else "#15803d")

    def _auto_finish(self, reason: str | None, ok: bool, show_dialog: bool) -> None:
        if not self._auto_running:
            return
        self._auto_running = False
        self._auto_segment_request = None
        if self._auto_job is not None:
            try:
                self.root.after_cancel(self._auto_job)
            except tk.TclError:
                pass
            self._auto_job = None

        prev_soc, prev_temp = self._auto_prev_values
        self._period = self._auto_prev_period
        self.soc_var.set(str(prev_soc))
        self.temp_var.set(str(prev_temp))
        self._reschedule.set()

        for widget in (
            self.soc_spin, self.temp_spin, self.period_spin,
            self.auto_period_spin, self.auto_duration_spin,
        ):
            widget.configure(state="normal")

        sender_alive = self.worker is not None and self.worker.is_alive()
        self.auto_start_btn.configure(state="normal")
        self.auto_stop_btn.configure(state="disabled")
        if self._auto_started_sender and sender_alive:
            self.stop()
        else:
            self.start_btn.configure(state="disabled" if sender_alive else "normal")
            self.stop_btn.configure(state="normal" if sender_alive else "disabled")

        elapsed = time.monotonic() - self._auto_started_time
        if reason:
            self._auto_write(f"[中止] {reason}")
        self._auto_write(
            f"发送线程：{'存活' if sender_alive else '已停止'}，"
            f"验证期间完成 {self._auto_sent_cycles} 轮发送"
        )
        hours = int(elapsed // 3600)
        minutes = int(elapsed % 3600 // 60)
        summary = (
            f"汇总：PASS={self._auto_pass} FAIL={self._auto_fail} ERROR={self._auto_error}，"
            f"执行 {self._auto_index} 步，用时 {hours:02d}:{minutes:02d}:{int(elapsed % 60):02d}，"
            f"随机种子={self._auto_seed}"
        )
        self._auto_write(summary)
        self._log(f"自动化验证{'完成' if ok else '中止'}：{summary}")
        if ok:
            self.auto_status_var.set(
                f"验证完成 · PASS {self._auto_pass} / FAIL {self._auto_fail} / "
                f"ERROR {self._auto_error}"
            )
        else:
            self.auto_status_var.set(f"验证中止 · {reason or ''}")
        self.auto_status_label.configure(
            fg="#15803d" if ok and not self._auto_fail and not self._auto_error else DANGER
        )
        if show_dialog:
            messagebox.showinfo(
                "自动化验证",
                f"{'验证完成' if ok else '验证中止'}\n\n{summary}\n\n记录文件：\n{self._auto_file}",
            )

    def _auto_stop(self) -> None:
        if not self._auto_running:
            return
        self._auto_finish("用户中止自动化验证", ok=False, show_dialog=False)
        self._log("自动化验证已中止。")

    def _auto_write(self, text: str) -> None:
        if self._auto_file is None:
            return
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._auto_file.open("a", encoding="utf-8") as handle:
                handle.write(f"[{stamp}] {text}\n")
        except OSError as exc:
            self._log(f"自动化验证记录写入失败：{exc}")

    def _auto_open_report(self) -> None:
        path = self._auto_file
        if path is None or not path.exists():
            messagebox.showinfo("自动化验证", "还没有生成验证记录，请先开始验证。")
            return
        try:
            os.startfile(str(path))
        except OSError as exc:
            messagebox.showerror("自动化验证", f"无法打开记录文件：{exc}")

    # ---------- 发送 ----------

    def _open_bus(self):
        iface = self.iface_var.get()
        channel = self.channel_var.get().strip()
        if iface == CANALYST_IFACE:
            if channel not in ("0", "1"):
                raise ValueError("CANalyst-II 通道只能填写 0 或 1。")
            dll_path = self.dll_var.get().strip()
            if not dll_path:
                raise ValueError("请选择 ControlCAN.dll 的路径。")
            return CanalystIIBus(dll_path, channel=int(channel), bitrate=CAN_BITRATE)

        if not channel:
            raise ValueError("请填写 CAN 通道。")
        if iface == "虚拟总线（测试）":
            return can.Bus(interface="virtual", channel=channel)
        mapping = {"PCAN": "pcan", "SLCAN": "slcan", "Kvaser": "kvaser", "Vector": "vector"}
        kwargs = {"interface": mapping[iface], "channel": channel, "bitrate": CAN_BITRATE}
        if iface in ("Kvaser", "Vector"):
            kwargs["channel"] = int(channel) if channel.isdigit() else channel
        return can.Bus(**kwargs)

    def start(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        values = self._read_values(show_error=True)
        if values is None:
            return
        period = self._read_period(show_error=True)
        if period is None:
            return
        self._values = values
        self._period = period

        try:
            bus = self._open_bus()
        except Exception as exc:
            self._log(f"打开 CAN 接口失败：{exc}")
            messagebox.showerror(
                "CAN 打开失败",
                f"无法打开 CAN 接口：\n{exc}\n\n请检查接口类型、通道号以及驱动是否安装。",
            )
            return

        self._had_error = False
        self.stop_event.clear()
        self.worker = threading.Thread(target=self._run, args=(bus,), daemon=True)
        self.worker.start()

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_var.set("运行中 · 正在发送…")
        self.status_label.configure(fg="#15803d")
        self._log(
            f"开始发送：{self.iface_var.get()} / {self.channel_var.get()} / "
            f"250 kbit/s，SOC={values[0]}%，温度={values[1]}℃，周期={period:g} 秒"
        )

    def stop(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            self.stop_event.set()
            self.stop_btn.configure(state="disabled")
            self.status_var.set("正在停止…")
            self._log("已请求停止发送。")

    def _run(self, bus: can.BusABC) -> None:
        next_time = time.monotonic()
        try:
            while not self.stop_event.is_set():
                soc, temp = self._values
                interval = self._period
                payload = build_payload(soc, temp)
                sent = send_cycle(bus, payload, self.stop_event)
                self.messages.put(("sent", (sent, soc, temp, interval)))

                next_time += interval
                delay = next_time - time.monotonic()
                if delay > 0:
                    deadline = time.monotonic() + delay
                    while not self.stop_event.is_set():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        if self._reschedule.is_set():
                            # 自动化验证修改参数后立即按新值发送
                            self._reschedule.clear()
                            next_time = time.monotonic()
                            break
                        if self.stop_event.wait(min(remaining, 0.1)):
                            break
                else:
                    next_time = time.monotonic()
        except Exception as exc:
            self.messages.put(("error", str(exc)))
        finally:
            try:
                bus.shutdown()
            except Exception:
                pass
            self.messages.put(("stopped", None))

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "sent":
                    sent, soc, temp, interval = payload
                    self.status_var.set(
                        f"运行中 · 每 {interval:g} 秒 · 上次发送 {time.strftime('%H:%M:%S')} · "
                        f"SOC {soc}% · {temp}℃ · {sent}/18 帧"
                    )
                    self._auto_last_send = time.monotonic()
                    if self._auto_running:
                        self._auto_sent_cycles += 1
                    else:
                        self._log(
                            f"已发送 {sent}/18 帧，SOC={soc}%，温度={temp}℃，周期={interval:g} 秒"
                        )
                elif kind == "error":
                    self._had_error = True
                    self._last_send_error = str(payload)
                    self.status_var.set("发送失败")
                    self.status_label.configure(fg=DANGER)
                    self._log(f"发送失败：{payload}")
                    if not self._auto_running:
                        messagebox.showerror("发送失败", f"CAN 发送失败：\n{payload}")
                elif kind == "stopped":
                    self.worker = None
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    if self._auto_running:
                        self._auto_finish(
                            "CAN 发送线程已停止，自动化验证中止", ok=False, show_dialog=True
                        )
                    elif not self._had_error:
                        self.status_var.set("已停止")
                        self.status_label.configure(fg=MUTED)
                        self._log("已停止发送。")
                elif kind == "current":
                    can_id, record, revision = payload
                    timestamp, _, voltage, current, data_hex = record
                    self._latest_records[can_id] = record
                    self._record_rev = revision
                    self.voltage_var.set(f"{voltage / VOLTAGE_SCALE:.1f}")
                    self.current_var.set(f"{current / CURRENT_SCALE:.2f}")
                    self._alloc_text = (
                        f"CAN 0x{can_id:08X} · 数据 {data_hex} · "
                        f"电压原始值 {voltage} 电流原始值 {current} · "
                        f"日志 {timestamp[11:] if timestamp else '未知'}"
                    )
                    self._refresh_alloc_status("#15803d")
                elif kind == "current_none":
                    self.voltage_var.set("--")
                    self.current_var.set("--")
                    self._alloc_text = f"CAN 0x{payload:08X} 暂无下发报文"
                    self._refresh_alloc_status(MUTED)
                elif kind == "auto_preflight":
                    okay, data = payload
                    if not self._auto_running:
                        continue
                    if not okay:
                        self._auto_finish(
                            f"终端日志不可用：{data}", ok=False, show_dialog=True
                        )
                    else:
                        self._auto_begin(data)
                elif kind == "auto_segment":
                    if not self._auto_running:
                        continue
                    token, okay, data = payload
                    if token != self._auto_segment_token:
                        continue
                    self._auto_segment_done = True
                    if okay:
                        self._auto_segment_record = data
                        self._auto_segment_error = ""
                    else:
                        self._auto_segment_record = None
                        self._auto_segment_error = str(data)
                elif kind == "log_ok":
                    self._log_error_text = ""
                    self._fetch_text = f"已读取 {payload}"
                    self._refresh_alloc_status("#15803d")
                elif kind == "log_error":
                    self._log_error_text = str(payload)
                    self._fetch_text = f"读取失败：{payload}"
                    self._refresh_alloc_status(DANGER)
                    self._log(f"终端日志读取失败：{payload}")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_messages)

    def _log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {text}\n")
        # 长时间运行时只保留最近 600 行，避免界面日志无限增长
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 600:
            self.log_text.delete("1.0", f"{lines - 600 + 1}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def on_close(self) -> None:
        if self._auto_running:
            self._auto_running = False
            if self._auto_job is not None:
                try:
                    self.root.after_cancel(self._auto_job)
                except tk.TclError:
                    pass
                self._auto_job = None
            self._auto_write("[中止] 程序关闭，自动化验证中止")
            self._auto_write(
                f"汇总：PASS={self._auto_pass} FAIL={self._auto_fail} "
                f"ERROR={self._auto_error}，执行 {self._auto_index} 步，"
                f"随机种子={self._auto_seed}"
            )
        self.stop_event.set()
        self._log_stop.set()
        self._log_wake.set()
        if self.worker is not None:
            self.worker.join(timeout=1.5)
        self.root.destroy()


def main() -> None:
    py_bits = 64 if sys.maxsize > 2**32 else 32
    print(f"[BMS 模拟器] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} {py_bits} 位 · 进程 PID={os.getpid()}")
    print(diagnose_controlcan_text())
    print()

    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    app = BMSApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
