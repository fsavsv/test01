"""寄存器映射表（依据《RS485 通讯协议规范 V1.9（二三轮电动车）》）。"""
from dataclasses import dataclass, field

TOTAL_REGISTERS = 360
RESERVED_VALUE = 0xFFFF

# 中控空闲时间专用地址（协议第 5 节轮巡规则，写 1 个寄存器，如 0x012C=300ms）
ADDR_IDLE_TIME = 0xFE33


@dataclass
class RegDef:
    addr: int
    name: str
    group: str
    count: int = 1
    fmt: str = "U16"
    access: str = "只读"
    kind: str = "int"          # num / int / temp / hex / ascii / bits / balance / cells
                               # temps / cellinfo / celltype / vendor / choice / u32
                               # hexarr / array
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
    (6, "预放 MOS 状态（0 断开 / 1 闭合）"),
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

BALANCE_BITS = _bits(*[(i, f"第 {i + 1} 节电芯均衡（0 未均衡 / 1 均衡中）") for i in range(32)])

WARNING_BITS = _bits(
    (0, "总压高压告警"), (1, "总压低压告警"),
    (2, "单体电芯过压告警"), (3, "单体电芯欠压告警"),
    (4, "电芯压差大告警"), (5, "充电过流告警"),
    (6, "放电过流告警"), (7, "电芯高温禁充告警"),
    (8, "电芯低温禁充告警"), (9, "电芯高温禁放告警"),
    (10, "电芯低温禁放告警"), (11, "环境高温告警"),
    (12, "环境低温告警"), (13, "MOS 高温告警"),
    (14, "回馈过流告警"),
    (15, "预留（默认 0）"),
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
    (18, "充电超时保护"), (19, "充电 3 级过流保护"),
    (20, "放电 3 级过流保护"), (21, "回馈 1 级过流保护"),
    (22, "回馈 2 级过流保护"), (23, "从 BMS 通讯丢失保护"),
    (24, "主 BMS 通讯丢失保护"),
    (25, "预留（默认 0）"), (26, "预留"), (27, "预留"),
    (28, "预留"), (29, "预留"), (30, "预留"), (31, "预留"),
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

FAULT2_BITS = _bits(
    (0, "电池管理系统异常重启故障"), (1, "电量计量功能故障"),
    (2, "EEPROM 功能故障"), (3, "采样电路功能故障"),
    (4, "底座连接信号异常"), (5, "认证故障"),
    (6, "认证非法"), (7, "单体电芯过放故障"),
    (8, "预充电路短路故障"), (9, "温度采样功能故障"),
    (10, "电流采样功能故障"), (11, "温度传感器温度差过大"),
    (12, "采样电路硬件故障"), (13, "电压采样功能故障"),
    (14, "预留（默认 0）"), (15, "预留"),
    (16, "预留"), (17, "预留"), (18, "预留"), (19, "预留"),
    (20, "预留"), (21, "预留"), (22, "预留"), (23, "预留"),
    (24, "预留"), (25, "预留"), (26, "预留"), (27, "预留"),
    (28, "预留"), (29, "预留"), (30, "预留"), (31, "预留"),
)

SWITCH_BITS = _bits(
    (0, "充电（C-FET）授权（0 禁止充电 / 1 允许充电）"),
    (1, "放电（D-FET）授权（0 禁止放电 / 1 允许放电）"),
    (2, "预留"), (3, "预留"), (4, "预留"), (5, "预留"), (6, "预留"), (7, "预留"),
    (8, "预留"), (9, "预留"), (10, "预留"), (11, "预留"), (12, "预留"), (13, "预留"),
    (14, "预留"), (15, "预留"),
)

BATTYPE_BITS = _bits(
    (0, "圆柱电池"), (1, "方形硬壳电池"), (2, "软包电池"),
    (3, "预留"), (4, "预留"), (5, "预留"), (6, "预留"), (7, "预留"),
    (8, "预留"), (9, "预留"), (10, "预留"), (11, "预留"), (12, "预留"),
    (13, "预留"), (14, "预留"), (15, "预留"),
)

CABINET_ERR_BITS = _bits(
    (0, "充电模块状态（0 正常 / 1 故障）"),
    (1, "预留"), (2, "预留"), (3, "预留"), (4, "预留"), (5, "预留"), (6, "预留"),
    (7, "预留"), (8, "预留"), (9, "预留"), (10, "预留"), (11, "预留"),
    (12, "预留"), (13, "预留"), (14, "预留"), (15, "预留"),
)

AUTH_BITS = _bits(
    (0, "授权状态（0 未授权 / 1 已授权）"),
    (1, "预留"), (2, "预留"), (3, "预留"), (4, "预留"), (5, "预留"), (6, "预留"),
    (7, "预留"), (8, "预留"), (9, "预留"), (10, "预留"), (11, "预留"),
    (12, "预留"), (13, "预留"), (14, "预留"), (15, "预留"),
)

CELL_TYPES = [
    "0 LFP 磷酸铁锂", "1 NCM 三元锂", "2 LMO 锰酸锂", "3 LTO 钛酸锂",
    "4 LMFP 磷酸锰铁锂", "5 LCO 钴酸锂", "6 NMC 镍钴锰三元", "7 NCA 镍钴铝三元",
]

PACK_TYPES = ["0 圆柱电池", "1 方形硬壳电池", "2 软包电池"]

BAUD_CHOICES = [(0, "0x0000 = 9600（默认）"), (1, "0x0001 = 19200"), (2, "0x0002 = 115200")]
PARITY_CHOICES = [(0, "0x0000 = 无校验（默认）"), (1, "0x0001 = 奇校验 Odd"), (2, "0x0002 = 偶校验 Even")]
STOP_CHOICES = [(1, "0x0001 = 1 个停止位（默认）"), (2, "0x0002 = 2 个停止位")]

RECORD_LABELS = _bits(
    (0, "故障发生时间戳（U32 高 16 位）"),
    (1, "故障发生时间戳（U32 低 16 位）"),
    (2, "案发 #114 总电压（U16，10mV）"),
    (3, "案发 #115 总电流（S16，10mA）"),
    (4, "#121 告警状态快照（U16）"),
    (5, "#123 保护状态快照（U32 高 16 位）"),
    (6, "#123 保护状态快照（U32 低 16 位）"),
    (7, "#125 故障状态快照（U16）"),
    (8, "#197 故障状态快照（U32 高 16 位）"),
    (9, "#197 故障状态快照（U32 低 16 位）"),
)

DEFS = [
    # ---- 通用寄存器 ----
    RegDef(0, "协议版本号", "general", kind="hex", fmt="U16", default=0x0109,
           desc="第 1 字节大版本、第 2 字节小版本，0x0109 表示 V1.9"),
    RegDef(1, "软件版本号", "general", kind="hex", fmt="U16", default=0x0100,
           desc="第 1 字节大版本、第 2 字节小版本"),
    RegDef(2, "硬件版本号", "general", kind="hex", fmt="U16", default=0x0100,
           desc="第 1 字节大版本、第 2 字节小版本"),
    RegDef(3, "厂商信息", "general", kind="vendor", fmt="U16", default=0x0101,
           desc="第 1 字节 PACK 厂商信息，第 2 字节 BMS 厂商信息"),
    RegDef(4, "电芯信息与电池类型", "general", kind="celltype", fmt="U16", default=0x0001,
           desc="第 1 字节电芯类型（0 LFP / 1 NCM / 2 LMO / 3 LTO / 4 LMFP / 5 LCO / 6 NMC / 7 NCA），"
                "第 2 字节电池类型（0 圆柱 / 1 方形硬壳 / 2 软包）"),
    RegDef(5, "电池编码", "general", count=12, fmt="ASCII", kind="ascii", access="读写",
           default="LT-BMS-SIM-000000000001", desc="24 字节 ASCII 电池编码"),
    RegDef(17, "电芯厂商信息", "general", count=12, fmt="ASCII", kind="ascii",
           default="CATLLFP50AH-V2260313B001",
           desc="24 字节：[厂商 4 位]+[型号 10 位]+[日期 YYMMDD 6 位]+[批次/预留 4 位]"),
    RegDef(100, "电池编码", "general", count=12, fmt="ASCII", kind="ascii", access="读写",
           default="LT-BMS-SIM-000000000001", desc="24 字节 ASCII 电池编码（BMS 设备区）"),
    RegDef(112, "厂商信息", "general", kind="vendor", fmt="U16", default=0x0101,
           desc="第 1 字节 PACK 厂商信息，第 2 字节 BMS 厂商信息"),
    RegDef(113, "电芯信息", "general", kind="cellinfo", fmt="U16", default=0x0010,
           desc="第 1 字节电芯类型（0–7），第 2 字节电芯串数（16:16S / 20:20S）"),

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
           bits=WARNING_BITS, desc="只告警，不进行 MOS 动作"),
    RegDef(123, "BMS 保护状态", "status", count=2, kind="bits", fmt="U32", default=0,
           bits=PROTECT_BITS, desc="保护会断开对应的充电或放电 MOS"),
    RegDef(125, "BMS 故障状态", "status", kind="bits", fmt="U16", default=0,
           bits=FAULT_BITS, desc="故障会断开充放电 MOS"),
    RegDef(197, "BMS 故障状态（扩展）", "status", count=2, kind="bits", fmt="U32", default=0,
           bits=FAULT2_BITS, desc="系统 / 计量 / 采样 / 认证类故障，故障会断开充放电 MOS"),

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
           desc="10mA，电池根据放电 Map 确定的可持续放电电流"),
    RegDef(194, "电池回馈电流", "sop", kind="num", fmt="S16", unit="A", scale=100,
           decimals=2, default=5000, min_raw=-32768, max_raw=32767,
           desc="10mA，根据充电 Map 确定；SoC＞95% 或不满足充电条件时为 0"),
    RegDef(196, "满充使能", "sop", kind="int", fmt="U16", default=0, max_raw=1,
           desc="0：不需满充；1：需要满充"),

    # ---- 充电交互 ----
    RegDef(200, "BMS 请求充电电压", "charge", kind="num", fmt="U16", unit="V", scale=100,
           decimals=2, default=5840,
           desc="10mV；充电器未接入或存在充电类保护时请求值自动置 0，禁止充电"),
    RegDef(201, "BMS 请求充电电流", "charge", kind="num", fmt="S16", unit="A", scale=100,
           decimals=2, default=1000, min_raw=-32768, max_raw=32767,
           desc="10mA；充电器未接入或存在充电类保护时请求值自动置 0"),
    RegDef(202, "充电器输出电流", "charge", kind="num", fmt="S16", unit="A", scale=100,
           decimals=2, default=0, min_raw=-32768, max_raw=32767, access="读写",
           desc="充电器写入，10mA，表示充电器实际输出电流大小"),
    RegDef(203, "充电器接入状态", "charge", kind="hex", fmt="U16", default=0x0000,
           access="读写", desc="0x55AA = 充电器接入，其他值 = 未接入"),
    RegDef(204, "中控 ACC 状态", "charge", kind="int", fmt="U16", default=0, max_raw=2,
           access="读写",
           desc="0：None；1：ACC ON 仪表上电；2：ACC OFF 仪表下电"),
    RegDef(205, "电池类型", "charge", kind="bits", fmt="U16", default=0x0002,
           bits=BATTYPE_BITS, desc="bit0 圆柱 / bit1 方形硬壳 / bit2 软包"),
    RegDef(206, "SOC 主", "charge", kind="int", fmt="U16", unit="%", default=80, max_raw=100,
           desc="双包模式主包 SOC"),
    RegDef(207, "SOC 从", "charge", kind="int", fmt="U16", unit="%", default=80, max_raw=100,
           desc="双包模式从包 SOC"),
    RegDef(208, "工作模式", "charge", kind="int", fmt="U16", default=0, max_raw=1,
           desc="0：单包模式；1：双包模式"),

    # ---- 控制与授权 ----
    RegDef(195, "BMS 开关控制", "control", kind="bits", fmt="U16", default=0x0003,
           access="读写", bits=SWITCH_BITS,
           desc="bit0 充电（C-FET）授权，bit1 放电（D-FET）授权"),
    RegDef(209, "直流充（换）电柜错误信息", "control", kind="bits", fmt="U16", default=0,
           access="读写", bits=CABINET_ERR_BITS, desc="bit0 充电模块状态 0 正常 / 1 故障"),
    RegDef(210, "系统控制", "control", kind="choice", fmt="U16", default=0,
           access="读写",
           bits=[(0, "0x0000 空闲"), (1, "0x0001 软复位 BMS"),
                 (2, "0x0002 清除故障（仅限允许清除的软告警）"),
                 (3, "0x0003 清零单次充/放电量")],
           desc="写入命令执行后自动回到 0x0000 空闲"),
    RegDef(213, "授权状态", "control", kind="bits", fmt="U16", default=0,
           access="读写", bits=AUTH_BITS, desc="bit0 授权状态 0 未授权 / 1 已授权"),
    RegDef(214, "签名状态", "control", kind="hex", fmt="U16", default=0,
           access="读写",
           desc="高字节写入 0x01=开始签名；低字节读取：0x00 空闲 / 0x01 计算中 / "
                "0x02 签名完成（数据有效）/ 0xEE 计算错误"),

    # ---- 签名与随机数 ----
    RegDef(215, "随机数输入（Nonce R）", "auth", count=16, kind="hexarr", fmt="U8 Array",
           access="读写", desc="16 个寄存器 = 32 字节（256 bit），大端模式；"
           "写入新随机数会清除数字签名并复位 #214"),
    RegDef(231, "数字签名（Signature）", "auth", count=32, kind="hexarr", fmt="U8 Array",
           desc="ECDSA 签名结果 (r, s) 64 字节；前 16 寄存器存 r、后 16 寄存器存 s，默认 0x00"),

    # ---- 电量统计 ----
    RegDef(263, "累计充电电量", "energy", count=2, kind="u32", fmt="U32", unit="×10mWh",
           default=0, access="读写", desc="支持重写，10mWh"),
    RegDef(265, "累计放电电量", "energy", count=2, kind="u32", fmt="U32", unit="×10mWh",
           default=0, access="读写", desc="支持重写，10mWh"),
    RegDef(267, "故障/告警最新记录索引", "energy", kind="int", fmt="U16", default=0,
           desc="指向 280–359 故障记录组"),
    RegDef(268, "累计故障触发总次数", "energy", kind="int", fmt="U16", default=0),
    RegDef(269, "单次充电电量", "energy", count=2, kind="u32", fmt="U32", unit="×10mWh",
           default=0, desc="10mWh，可由 #210=0x0003 清零"),
    RegDef(271, "单次放电电量", "energy", count=2, kind="u32", fmt="U32", unit="×10mWh",
           default=0, desc="10mWh，可由 #210=0x0003 清零"),

    # ---- 通讯参数 ----
    RegDef(273, "Modbus 通讯地址（ID）", "comm", kind="int", fmt="U16", default=3,
           min_raw=1, max_raw=247, access="读写",
           desc="有效范围 1–247，出厂默认 0x03（电池 #1）或 0x04，用于多电池并联地址冲突"),
    RegDef(274, "波特率（Baud Rate）", "comm", kind="choice", fmt="U16", default=0,
           access="读写", bits=BAUD_CHOICES, desc="0x0000=9600（默认）/ 0x0001=19200 / 0x0002=115200"),
    RegDef(275, "校验位（Parity）", "comm", kind="choice", fmt="U16", default=0,
           access="读写", bits=PARITY_CHOICES, desc="0x0000 无校验（默认）/ 0x0001 奇校验 / 0x0002 偶校验"),
    RegDef(276, "停止位（Stop Bits）", "comm", kind="choice", fmt="U16", default=1,
           access="读写", bits=STOP_CHOICES, desc="0x0001 = 1 个停止位（默认）/ 0x0002 = 2 个停止位"),
    RegDef(277, "数据位（Data Bits）", "comm", kind="int", fmt="U16", default=8,
           min_raw=8, max_raw=8, access="读写",
           desc="推荐固定返回 0x0008（8 位），标准 Modbus RTU 强制要求 8 数据位"),

    # ---- 故障记录（280–359，8 组 × 10 个寄存器）----
    *[RegDef(280 + 10 * i, f"故障/保护/告警记录组 {i}", "records", count=10,
             kind="array", fmt="U16", default=0, bits=RECORD_LABELS,
             desc="时间戳 U32 + 案发总压/总流 + 告警/保护/故障状态快照")
      for i in range(8)],
]

GROUPS = [
    ("general", "通用寄存器", "0x0000 – 0x0071（0 – 113）",
     "版本、厂商与电芯信息、电池编码、电芯厂商信息；未定义寄存器返回 0xFFFF。"),
    ("status", "实时状态", "0x0072 – 0x00C6（114 – 125 / 197）",
     "总压 / 总流 / SOC / SOH、MOS 与充放电状态、均衡、告警 / 保护 / 故障。"),
    ("capacity", "容量与极值", "0x007E – 0x008E（126 – 142）",
     "容量、循环次数、电芯电压 / 温度极值与位置、串数。"),
    ("cells", "单体电压", "0x008F – 0x00AE（143 – 174）",
     "32 节单体电压（mV）；未使用的节保留 0xFFFF。"),
    ("temps", "温度", "0x00AF – 0x00C0（175 – 192）",
     "电芯、环境、MOS 温度（寄存器单位 K）与个数。"),
    ("sop", "放电能力", "0x00C1 – 0x00C4（193 – 196）",
     "可持续放电电流、电池回馈电流；SoC > 95% 或条件不满足时回馈电流为 0。"),
    ("charge", "充电交互", "0x00C8 – 0x00D0（200 – 208）",
     "BMS 请求充电电压 / 电流；充电器写入输出电流与接入状态（0x55AA）；"
     "ACC 状态、电池类型、双包 SOC 与工作模式。未接入或存在充电类保护时，请求值自动置 0。"),
    ("control", "控制与授权", "0x00C3 / 0x00D1 – 0x00D6（195 / 209 – 214）",
     "BMS 开关控制、充电柜错误信息、系统控制、授权与签名状态。"),
    ("auth", "签名与随机数", "0x00D7 – 0x0106（215 – 262）",
     "随机数输入（32 字节）与 ECDSA 数字签名（64 字节）；写入新随机数自动清除签名。"),
    ("energy", "电量统计", "0x0107 – 0x0110（263 – 272）",
     "累计 / 单次充放电电量（10mWh）、故障记录索引与次数。"),
    ("comm", "通讯参数", "0x0111 – 0x0115（273 – 277）",
     "Modbus 地址、波特率、校验位、停止位、数据位。"),
    ("records", "故障记录", "0x0118 – 0x0167（280 – 359）",
     "8 组故障 / 保护 / 告警记录，每组 10 个寄存器：时间戳、案发总压总流、状态快照。"),
]

GROUP_ORDER = {g[0]: i for i, g in enumerate(GROUPS)}
DEF_BY_ADDR = {d.addr: d for d in DEFS}
DEFS_BY_GROUP = {g[0]: [d for d in DEFS if d.group == g[0]] for g in GROUPS}

# 充电类保护位（存在任一位时，200/201/194 输出 0）
CHARGE_PROTECT_BITS = (0, 2, 4, 5, 6, 10, 11, 12, 15, 16, 17, 18, 19)

# 协议可写寄存器（0x10）：单个地址与连续区间 [start, end)
WRITABLE_SINGLES = frozenset({195, 202, 203, 204, 209, 210, 213, 214, 273, 274, 275, 276, 277})
WRITABLE_RANGES = ((5, 17), (100, 112), (211, 213), (215, 231), (263, 267))
