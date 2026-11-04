"""顺丰 / 铁塔能源 BMS 485 协议 V1.1 的点表。"""
from __future__ import annotations

from dataclasses import dataclass

COIL_COUNT = 52
METER_COUNT = 29          # 寄存器 0 – 28
DEVICE_ID_START = 1000
DEVICE_ID_COUNT = 13      # 13 个寄存器 = 26 字节 ASCII


@dataclass
class RegDef:
    addr: int
    name: str
    group: str
    count: int = 1
    fmt: str = "U16"
    access: str = "只读"
    kind: str = "int"       # num / int / temp / cells / ascii
    unit: str = ""
    scale: float = 1.0      # 原始值 = 工程值 × scale
    decimals: int = 0
    default: object = 0
    desc: str = ""
    min_raw: int = 0
    max_raw: int = 0xFFFF

    def chip(self) -> str:
        parts = [self.fmt]
        if self.unit:
            parts.append(self.unit)
        parts.append(self.access)
        return " · ".join(parts)


REGS = [
    RegDef(0, "电池包实际总电压", "meter", kind="num", fmt="U16", unit="V",
           scale=100, decimals=2, default=6000, desc="系数 0.01V"),
    RegDef(1, "电芯数量", "meter", kind="int", fmt="U16", unit="节",
           default=17, max_raw=20, desc="协议按 20 节定义点表，不足 20 节的数据用 0 补齐"),
    RegDef(2, "电量 SOC", "meter", kind="int", fmt="U16", unit="%",
           default=90, max_raw=100, desc="0 ~ 100%"),
    RegDef(3, "剩余容量", "meter", kind="num", fmt="U16", unit="Ah",
           scale=100, decimals=2, default=1782,
           desc="系数 0.01Ah，可能会少于设计容量"),
    RegDef(4, "SOH", "meter", kind="int", fmt="U16", unit="%",
           default=100, max_raw=100, desc="0 ~ 100%"),
    RegDef(5, "充电电流", "meter", kind="num", fmt="S16", unit="A",
           scale=100, decimals=2, default=0, min_raw=-32768, max_raw=32767,
           desc="系数 0.01A；按协议点表该地址为充电电流"),
    RegDef(6, "环境温度", "meter", kind="temp", fmt="S16", unit="°C",
           default=22, min_raw=-32768, max_raw=32767, desc="单位 °C，不需要换算"),
    RegDef(7, "电芯温度", "meter", kind="temp", fmt="S16", unit="°C",
           default=23, min_raw=-32768, max_raw=32767, desc="单位 °C"),
    RegDef(8, "板卡温度", "meter", kind="temp", fmt="S16", unit="°C",
           default=24, min_raw=-32768, max_raw=32767, desc="单位 °C"),
    RegDef(9, "电芯电压", "meter", count=20, kind="cells", fmt="U16", unit="mV",
           default=3520, max_raw=5000,
           desc="电芯 1 – 20，系数 0.001V；超过 #1 电芯数量的部分按协议填 0"),
    RegDef(DEVICE_ID_START, "设备 ID", "device", count=DEVICE_ID_COUNT,
           kind="ascii", fmt="ASCII", access="只读",
           default="KAM123456",
           desc="26 字节（13 个寄存器），只读；格式符合 GBT 34014-2017，"
                "不足 26 字节用 0x00 填充"),
]

REGS_BY_ADDR = {d.addr: d for d in REGS}
METER_DEFS = [d for d in REGS if d.group == "meter"]

WRITABLE_METER_RANGE = (0, METER_COUNT)   # 模拟器允许改写 0 – 28 以便调试


COILS = [
    (0, "保留位", "misc"),
    (1, "电芯压差过大", "misc"),
    (2, "充电过流", "misc"),
    (3, "放电过流", "misc"),
    (4, "短路保护", "misc"),
    (5, "充电高温保护", "misc"),
    (6, "放电高温保护", "misc"),
    (7, "充电低温保护", "misc"),
    (8, "放电低温保护", "misc"),
    (9, "充电 MOS 损坏", "misc"),
    (10, "放电 MOS 损坏", "misc"),
    (11, "内部通讯异常", "misc"),
    *[(12 + i, f"过充电压保护 {i + 1}", "over") for i in range(20)],
    *[(32 + i, f"过放电压保护 {i + 1}", "under") for i in range(20)],
]

COIL_GROUPS = [
    ("misc", "保护与故障", "地址 0 – 11", "开关地址按位编码；1 表示故障或保护动作。"),
    ("over", "过充电压保护", "地址 12 – 31", "依次对应第 1 – 20 节电芯的过充电压保护。"),
    ("under", "过放电压保护", "地址 32 – 51", "依次对应第 1 – 20 节电芯的过放电压保护。"),
]

COIL_NAMES = [name for _, name, _ in COILS]
