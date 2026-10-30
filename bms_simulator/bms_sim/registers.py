"""寄存器映射表（依据《RS485 协议规范 v1.3》）。"""
from dataclasses import dataclass, field

TOTAL_REGISTERS = 300
RESERVED_VALUE = 0xFFFF


@dataclass
class RegDef:
    addr: int
    name: str
    group: str
    count: int = 1
    fmt: str = "U16"
    access: str = "只读"
    kind: str = "int"          # num / int / temp / hex / ascii / bits / balance / cells / temps / cellinfo
    unit: str = ""
    scale: float = 1.0         # 工程值 -> 原始值 = 工程值 * scale
    decimals: int = 0
    default: object = 0
    desc: str = ""
    bits: list = field(default_factory=list)
    min_raw: int = 0
    max_raw: int = 0xFFFF

    def chip(self) -> str:
        parts = [self.fmt]
        if self.unit:
            parts.append(self.unit)
        parts.append(self.access)
        return " · ".join(parts)


def _bits(*items):
    return list(items)


BMS_SYSTEM_BITS = _bits(
    (0, "充电 MOS 状态（0 断开 / 1 闭合）"),
    (1, "放电 MOS 状态（0 断开 / 1 闭合）"),
    (2, "预充 MOS 状态（0 断开 / 1 闭合）"),
    (3, "加热 MOS 状态（0 断开 / 1 闭合）"),
    (4, "限流模块状态（0 失能 / 1 使能）"),
    (5, "保险丝状态（0 正常 / 1 断开）"),
    (6, "预留（默认 0）"),
    (7, "预留（默认 0）"),
    (8, "满充状态（0 非满充 / 1 满充）"),
    (9, "满放状态（0 非满放 / 1 满放）"),
    (10, "充电状态（0 非充电 / 1 充电）"),
    (11, "放电状态（0 非放电 / 1 放电）"),
    (12, "充电器接入状态（0 未接入 / 1 接入）"),
    (13, "蜂鸣器状态（0 不鸣 / 1 鸣响）"),
    (14, "预留（默认 0）"),
    (15, "预留（默认 0）"),
)

WARNING_BITS = _bits(
    (0, "总压高压告警"), (1, "总压低压告警"),
    (2, "单体电芯过压告警"), (3, "单体电芯欠压告警"),
    (4, "电芯压差大告警"), (5, "充电过流告警"),
    (6, "放电过流告警"), (7, "电芯高温禁充告警"),
    (8, "电芯低温禁充告警"), (9, "电芯高温禁放告警"),
    (10, "电芯低温禁放告警"), (11, "环境高温告警"),
    (12, "环境低温告警"), (13, "MOS 高温告警"),
    (14, "预留（默认 0）"), (15, "预留（默认 0）"),
    (16, "预留"), (17, "预留"), (18, "预留"), (19, "预留"),
    (20, "预留"), (21, "预留"), (22, "预留"), (23, "预留"),
    (24, "预留"), (25, "预留"), (26, "预留"), (27, "预留"),
    (28, "预留"), (29, "预留"), (30, "预留"), (31, "预留"),
)

PROTECT_BITS = _bits(
    (0, "总压高压保护"), (1, "总压低压保护"),
    (2, "单体电芯过压保护"), (3, "单体电芯欠压保护"),
    (4, "电芯压差大保护"), (5, "充电 1 级过流保护"),
    (6, "充电 2 级过流保护"), (7, "放电 1 级过流保护"),
    (8, "放电 2 级过流保护"), (9, "短路保护"),
    (10, "反接保护"), (11, "电芯高温禁充"),
    (12, "电芯低温禁充"), (13, "电芯高温禁放"),
    (14, "电芯低温禁放"), (15, "环境高温保护"),
    (16, "环境低温保护"), (17, "MOS 高温保护"),
    (18, "充电超时保护"),
    (19, "预留（默认 0）"), (20, "预留"), (21, "预留"), (22, "预留"),
    (23, "预留"), (24, "预留"), (25, "预留"), (26, "预留"),
    (27, "预留"), (28, "预留"), (29, "预留"), (30, "预留"), (31, "预留"),
)

FAULT_BITS = _bits(
    (0, "充电 MOS 失效故障"), (1, "放电 MOS 失效故障"),
    (2, "单体电芯电压过高失效故障"), (3, "单体电芯电压过低失效故障"),
    (4, "电芯温度过高失效故障"), (5, "温度探头失效故障"),
    (6, "模拟前端失效故障"), (7, "BMS 自身其他故障"),
    (8, "热失控告警故障"),
    (9, "预留（默认 0）"), (10, "预留"), (11, "预留"), (12, "预留"),
    (13, "预留"), (14, "预留"), (15, "预留"),
)

BALANCE_BITS = _bits(*[(i, f"第 {i + 1} 节电芯均衡（0 未均衡 / 1 均衡中）") for i in range(32)])

DEFS = [
    # ---- 通用寄存器 ----
    RegDef(0, "协议版本号", "general", kind="hex", fmt="U16", default=0x0001,
           desc="第 1 字节大版本、第 2 字节小版本，0x0001 表示 v0.1"),
    RegDef(1, "软件版本号", "general", kind="hex", fmt="U16", default=0x0001,
           desc="第 1 字节大版本、第 2 字节小版本"),
    RegDef(2, "硬件版本号", "general", kind="hex", fmt="U16", default=0x0001,
           desc="第 1 字节大版本、第 2 字节小版本"),
    RegDef(3, "设备类型", "general", kind="hex", fmt="U16", default=0x0001,
           desc="当前固定为 1，即 BMS 设备"),
    RegDef(100, "电池编码", "general", count=12, fmt="ASCII", kind="ascii",
           default="JD-BMS-SIM-0000000001", desc="24 字节 ASCII 电池编码"),
    RegDef(112, "厂商信息", "general", kind="vendor", fmt="U16", default=0x0101,
           desc="第 1 字节 PACK 厂商信息，第 2 字节 BMS 厂商信息"),
    RegDef(113, "电芯信息", "general", kind="cellinfo", fmt="U16", default=0x0010,
           desc="第 1 字节电芯类型：0 LFP / 1 NCM / 2 LMO / 3 LTO；第 2 字节电芯串数"),

    # ---- 实时状态 ----
    RegDef(114, "总电压", "status", kind="num", fmt="U16", unit="V", scale=100,
           decimals=2, default=5200, max_raw=0xFFFF, desc="10mV"),
    RegDef(115, "总电流", "status", kind="num", fmt="S16", unit="A", scale=100,
           decimals=2, default=0, min_raw=-32768, max_raw=32767,
           desc="10mA，充电为正、放电为负"),
    RegDef(116, "SOC", "status", kind="int", fmt="U16", unit="%", default=80, max_raw=100),
    RegDef(117, "SOH", "status", kind="int", fmt="U16", unit="%", default=98, max_raw=100),
    RegDef(118, "BMS 系统状态", "status", kind="bits", fmt="U16", default=0x0003,
           bits=BMS_SYSTEM_BITS,
           desc="MOS / 满充满放 / 充放电 / 充电器接入 / 蜂鸣器状态"),
    RegDef(119, "BMS 均衡状态", "status", count=2, kind="balance", fmt="U32", default=0,
           bits=BALANCE_BITS, desc="bit0–bit31 依次对应第 1–32 节电芯，0 未均衡 / 1 均衡中"),
    RegDef(121, "BMS 告警状态", "status", count=2, kind="bits", fmt="U32", default=0,
           bits=WARNING_BITS, desc="只告警，不动作 MOS"),
    RegDef(123, "BMS 保护状态", "status", count=2, kind="bits", fmt="U32", default=0,
           bits=PROTECT_BITS, desc="保护会断开对应的充电或放电 MOS"),
    RegDef(125, "BMS 故障状态", "status", kind="bits", fmt="U16", default=0,
           bits=FAULT_BITS, desc="故障会断开充放电 MOS"),

    # ---- 容量与极值 ----
    RegDef(126, "剩余容量", "capacity", kind="num", fmt="U16", unit="Ah", scale=100,
           decimals=2, default=4000, desc="10mAh"),
    RegDef(127, "设计容量", "capacity", kind="num", fmt="U16", unit="Ah", scale=100,
           decimals=2, default=5000, desc="10mAh"),
    RegDef(128, "满充容量", "capacity", kind="num", fmt="U16", unit="Ah", scale=100,
           decimals=2, default=4800, desc="10mAh"),
    RegDef(129, "循环次数", "capacity", kind="int", fmt="U16", unit="次", default=300),
    RegDef(130, "最高电芯电压", "capacity", kind="int", fmt="U16", unit="mV", default=3400),
    RegDef(131, "最低电芯电压", "capacity", kind="int", fmt="U16", unit="mV", default=3300),
    RegDef(132, "电芯电压最值位置", "capacity", kind="hex", fmt="U16", default=0x0102,
           desc="第 1 字节最高电芯电压位置，第 2 字节最低电芯电压位置"),
    RegDef(133, "最高电芯温度", "capacity", kind="temp", fmt="U16", unit="°C", default=300,
           desc="寄存器单位 K"),
    RegDef(134, "最低电芯温度", "capacity", kind="temp", fmt="U16", unit="°C", default=295,
           desc="寄存器单位 K"),
    RegDef(135, "电芯温度最值位置", "capacity", kind="hex", fmt="U16", default=0x0102,
           desc="第 1 字节最高电芯温度位置，第 2 字节最低电芯温度位置"),
    RegDef(136, "最高环境温度", "capacity", kind="temp", fmt="U16", unit="°C", default=298,
           desc="寄存器单位 K"),
    RegDef(137, "最低环境温度", "capacity", kind="temp", fmt="U16", unit="°C", default=293,
           desc="寄存器单位 K"),
    RegDef(138, "环境温度最值位置", "capacity", kind="hex", fmt="U16", default=0x0102,
           desc="第 1 字节最高环境温度位置，第 2 字节最低环境温度位置"),
    RegDef(139, "最高 MOS 温度", "capacity", kind="temp", fmt="U16", unit="°C", default=300,
           desc="寄存器单位 K"),
    RegDef(140, "最低 MOS 温度", "capacity", kind="temp", fmt="U16", unit="°C", default=295,
           desc="寄存器单位 K"),
    RegDef(141, "MOS 温度最值位置", "capacity", kind="hex", fmt="U16", default=0x0102,
           desc="第 1 字节最高 MOS 温度位置，第 2 字节最低 MOS 温度位置"),
    RegDef(142, "电芯串数", "capacity", kind="int", fmt="U16", unit="个", default=16,
           max_raw=32, desc="最大为 32 串"),

    # ---- 单体电压 ----
    RegDef(143, "电芯电压", "cells", count=32, kind="cells", fmt="U16", unit="mV",
           default=3300, max_raw=5000, desc="32 节单体电压，mV；未使用的节保留 0xFFFF"),

    # ---- 温度 ----
    RegDef(175, "电芯温度个数", "temps", kind="int", fmt="U16", unit="个", default=8,
           max_raw=8),
    RegDef(176, "电芯温度", "temps", count=8, kind="temps", fmt="U16", unit="°C",
           default=298, desc="最多 8 个温度点，寄存器单位 K"),
    RegDef(184, "环境和 MOS 温度个数", "temps", kind="hex", fmt="U16", default=0x0202,
           desc="第 1 字节环境温度个数（≤4），第 2 字节 MOS 温度个数（≤4）"),
    RegDef(185, "环境温度", "temps", count=4, kind="temps", fmt="U16", unit="°C",
           default=298, desc="最多 4 个温度点，寄存器单位 K"),
    RegDef(189, "MOS 温度", "temps", count=4, kind="temps", fmt="U16", unit="°C",
           default=300, desc="最多 4 个温度点，寄存器单位 K"),

    # ---- 放电能力 ----
    RegDef(193, "电池可持续放电电流", "sop", kind="num", fmt="S16", unit="A", scale=100,
           decimals=2, default=10000, min_raw=-32768, max_raw=32767,
           desc="10mA，根据放电 Map 确定"),
    RegDef(194, "电池回馈电流", "sop", kind="num", fmt="S16", unit="A", scale=100,
           decimals=2, default=5000, min_raw=-32768, max_raw=32767,
           desc="10mA，根据充电 Map 确定；SoC>95% 或不满足充电条件时为 0"),

    # ---- 充电交互 ----
    RegDef(200, "BMS 请求充电电压", "charge", kind="num", fmt="U16", unit="V", scale=100,
           decimals=2, default=5840,
           desc="10mV；充电器未接入或存在充电类保护时请求值自动置 0"),
    RegDef(201, "BMS 请求充电电流", "charge", kind="num", fmt="S16", unit="A", scale=100,
           decimals=2, default=1000, min_raw=-32768, max_raw=32767,
           desc="10mA；充电器未接入或存在充电类保护时请求值自动置 0"),
    RegDef(202, "充电器输出电流", "charge", kind="num", fmt="S16", unit="A", scale=100,
           decimals=2, default=0, min_raw=-32768, max_raw=32767, access="读写",
           desc="充电器写入，10mA，表示充电器实际输出电流"),
    RegDef(203, "充电器接入状态", "charge", kind="hex", fmt="U16", default=0x0000,
           access="读写", desc="0x55AA = 充电器接入，其他值 = 未接入"),
]

GROUPS = [
    ("general", "通用寄存器", "0x0000 – 0x0071（0 – 113）",
     "版本、设备类型、电池编码、厂商与电芯信息；未定义寄存器返回 0xFFFF。"),
    ("status", "实时状态", "0x0072 – 0x007D（114 – 125）",
     "总压 / 总流 / SOC / SOH、MOS 与充放电状态、均衡、告警 / 保护 / 故障。"),
    ("capacity", "容量与极值", "0x007E – 0x008E（126 – 142）",
     "容量、循环次数、电芯电压 / 温度极值与位置、串数。"),
    ("cells", "单体电压", "0x008F – 0x00AF（143 – 175）",
     "32 节单体电压（mV）与电芯温度个数。"),
    ("temps", "温度", "0x00B0 – 0x00BD（176 – 189）",
     "电芯、环境、MOS 温度（寄存器单位 K）与个数。"),
    ("sop", "放电能力", "0x00C1 – 0x00C2（193 – 194）",
     "可持续放电电流、电池回馈电流；SoC > 95% 或条件不满足时回馈电流为 0。"),
    ("charge", "充电交互", "0x00C8 – 0x00CB（200 – 203）",
     "BMS 请求充电电压 / 电流；充电器写入输出电流与接入状态（0x55AA）。"
     "未接入或存在充电类保护时，请求值自动置 0。"),
]

GROUP_ORDER = {g[0]: i for i, g in enumerate(GROUPS)}
DEF_BY_ADDR = {d.addr: d for d in DEFS}
DEFS_BY_GROUP = {g[0]: [d for d in DEFS if d.group == g[0]] for g in GROUPS}

# 充电类保护位（存在任一位时，200/201/194 输出 0）
CHARGE_PROTECT_BITS = (0, 2, 4, 5, 6, 10, 11, 12, 15, 16, 17, 18)
