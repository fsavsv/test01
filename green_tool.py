#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备升级清单生成工具

阶段一（绿通平台）：
  1. 读取 原始数据.xlsx 第一列站点，取末尾 5 位编号；
  2. 登录绿通后台，逐个查询电柜，取出绿通设备编码（cabinetNo）；
  3. 生成 目标设备升级文件.xlsx（原始站点 / 绿通设备编码）；
  4. 复制为 预备升级设备数据.xlsx，并用京东样柜表把绿通编码映射为 ZL 设备编码。

阶段二（智莱采集平台）：
  5. 登录智莱采集系统，创建（或复用）分组；
  6. 按 ZL 设备编码逐个搜索设备、勾选并加入分组；
  7. 回读分组设备列表，校验设备编码与预备升级设备数据.xlsx 完全一致。

用法：
  python green_tool.py                      # 两个阶段都执行
  python green_tool.py --stage green        # 只生成 Excel
  python green_tool.py --stage zl           # 只把现有 Excel 导入分组
  python green_tool.py --group 工具测试分组  # 指定智莱分组名
"""

import argparse
import re
import shutil
import sys
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://admin.diantoulvtong.cn"
LOGIN_API = f"{BASE_URL}/api/admin/v1/auth/login"
CABINET_API = f"{BASE_URL}/api/admin/v1/cabinets"

USERNAME = "zltest0001"
PASSWORD = "Zltest202608"

TARGET_FILE = "目标设备升级文件.xlsx"
READY_FILE = "预备升级设备数据.xlsx"

DEFAULT_ORIGINAL = "原始数据.xlsx"
DEFAULT_JD = "京东320台样柜电柜号&ZL编码信息_20260817(1).xlsx"

ZL_BASE_URL = "https://battery.zhilai.com:81/api"
ZL_TENANT_CODE = "100"
ZL_USERNAME = "admin"
ZL_PASSWORD = "Zhilai!@#2026"
DEFAULT_GROUP = "工具测试分组"


def app_dir() -> Path:
    """程序所在目录：打包成 exe 后取 exe 目录，源码运行时取脚本目录"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# ---------------------------------------------------------------- 数据读取

def extract_5_digits(site_text: str) -> str:
    """'巴城-五联路3004-20326' -> '20326'"""
    match = re.search(r"(\d{5})\s*$", str(site_text).strip())
    if not match:
        raise ValueError(f"无法从站点中提取 5 位编号: {site_text}")
    return match.group(1)


def load_sites(path: Path) -> list[dict]:
    df = pd.read_excel(path, header=None, dtype=str)
    sites = []
    for value in df.iloc[:, 0].dropna():
        raw = str(value).strip()
        if not raw:
            continue
        sites.append({"原始站点": raw, "5位编号": extract_5_digits(raw)})
    return sites


def load_zl_mapping(jd_path: Path) -> dict[str, str]:
    """京东样柜表：G 列绿通设备编码 -> F 列 ZL 设备编码"""
    df = pd.read_excel(jd_path, header=None, dtype=str).fillna("")
    mapping = {}
    for _, row in df.iterrows():
        if len(row) < 7:
            continue
        green = str(row.iloc[6]).strip()
        zl = str(row.iloc[5]).strip()
        if green.startswith("KABAC") and zl:
            mapping[green] = zl
    return mapping


# ---------------------------------------------------------------- 绿通接口

class GreenClient:
    def __init__(self, username: str, password: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/login",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
        })
        self.token = ""

    def login(self):
        resp = self.session.post(
            LOGIN_API,
            json={"accountName": USERNAME, "password": PASSWORD},
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 0:
            raise RuntimeError(f"登录失败: {body.get('message')}")
        self.token = body["data"]["token"]
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        return body["data"]

    def search_cabinet(self, keyword: str) -> list[dict]:
        resp = self.session.get(
            CABINET_API,
            params={"keyword": keyword, "pageNo": 1, "pageSize": 100},
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 0:
            raise RuntimeError(f"查询 {keyword} 失败: {body.get('message')}")
        return body["data"].get("list") or []


def pick_cabinet(rows: list[dict], raw_site: str, code_5: str) -> tuple[str | None, str]:
    """在查询结果中挑选目标电柜，返回 (绿通编码, 说明)"""
    if not rows:
        return None, "未查询到结果"

    # 1. 站点名完全一致
    for row in rows:
        if str(row.get("stationName", "")).strip() == raw_site:
            return str(row.get("cabinetNo", "")).strip(), "站点名匹配"

    # 2. 电柜号末 5 位一致
    suffix_hits = [
        row for row in rows
        if str(row.get("cabinetNo", "")).strip().endswith(code_5)
    ]
    if len(suffix_hits) == 1:
        return str(suffix_hits[0].get("cabinetNo", "")).strip(), "电柜号后5位匹配"
    if len(suffix_hits) > 1:
        return str(suffix_hits[0].get("cabinetNo", "")).strip(), f"后5位命中{len(suffix_hits)}条，取第一条"

    # 3. 仅一条结果
    if len(rows) == 1:
        return str(rows[0].get("cabinetNo", "")).strip(), "唯一结果"
    return None, f"结果不唯一({len(rows)}条)，无法确定"


# ---------------------------------------------------------------- 输出

def write_target(results: list[dict], outdir: Path) -> Path:
    df = pd.DataFrame(results)[["原始站点", "绿通设备编码"]]
    path = outdir / TARGET_FILE
    df.to_excel(path, index=False)
    return path


def write_ready(target_path: Path, mapping: dict[str, str], outdir: Path) -> tuple[Path, pd.DataFrame]:
    ready_path = outdir / READY_FILE
    shutil.copy(target_path, ready_path)

    df = pd.read_excel(ready_path, dtype=str).fillna("")
    df["ZL设备编码"] = df["绿通设备编码"].map(
        lambda code: mapping.get(str(code).strip(), "")
    )
    df.to_excel(ready_path, index=False)
    return ready_path, df


# ---------------------------------------------------------------- 智莱平台

class ZlClient:
    """智莱物联网采集平台（RuoYi）接口客户端"""

    def __init__(self, username: str, password: str, tenant_code: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Origin": "https://battery.zhilai.com:81",
            "Referer": "https://battery.zhilai.com:81/index",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
        })
        self.username = username
        self.password = password
        self.tenant_code = tenant_code

    def _request(self, method: str, path: str, **kwargs):
        resp = self.session.request(method, f"{ZL_BASE_URL}{path}", timeout=30, **kwargs)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 200:
            raise RuntimeError(f"{path} 调用失败: {body.get('msg')}")
        return body

    def login(self) -> dict:
        body = self._request("POST", "/login", json={
            "username": self.username,
            "password": self.password,
            "code": "",
            "uuid": "",
            "tenantCode": self.tenant_code,
        })
        self.session.headers["Authorization"] = f"Bearer {body['token']}"
        return body

    def find_groups(self) -> list[dict]:
        body = self._request("GET", "/device/device-group/list",
                             params={"pageNum": 1, "pageSize": 200})
        return body.get("data") or []

    def ensure_group(self, group_name: str) -> str:
        for group in self.find_groups():
            if group.get("groupName") == group_name:
                return str(group["id"])

        self._request("POST", "/device/device-group",
                      json={"groupName": group_name, "parentId": "0"})
        for group in self.find_groups():
            if group.get("groupName") == group_name:
                return str(group["id"])
        raise RuntimeError(f"分组创建后未查询到: {group_name}")

    def group_devices(self, group_id: str) -> list[dict]:
        devices, page = [], 1
        while True:
            body = self._request("GET", "/device/device/list-by-group-id", params={
                "pageNum": page, "pageSize": 200, "groupId": group_id,
            })
            rows = body.get("rows") or []
            devices.extend(rows)
            if not rows or len(devices) >= int(body.get("total") or 0):
                return devices
            page += 1

    def search_available_device(self, device_name: str, group_id: str) -> list[dict]:
        body = self._request("GET", "/device/device/list-not-cur-group-device", params={
            "pageNum": 1, "pageSize": 20, "deviceName": device_name, "groupId": group_id,
        })
        return [row for row in (body.get("rows") or [])
                if str(row.get("deviceName", "")).strip() == device_name]

    def add_devices(self, group_id: str, device_ids: list[str]):
        self._request("POST", "/device/device/add-device-group",
                      json={"deviceIds": device_ids, "groupId": group_id})


def run_zl(ready_path: Path, group_name: str, interval: float) -> int:
    if not ready_path.exists():
        sys.exit(f"找不到预备升级设备数据: {ready_path}")

    df = pd.read_excel(ready_path, dtype=str).fillna("")
    codes = [str(code).strip() for code in df["ZL设备编码"] if str(code).strip()]
    duplicates = sorted({c for c in codes if codes.count(c) > 1})
    if duplicates:
        print(f"注意：表内存在重复 ZL 编码 {duplicates}")
        codes = list(dict.fromkeys(codes))

    invalid = [c for c in codes if not re.fullmatch(r"\d{18}", c)]
    if invalid:
        print(f"注意：{len(invalid)} 个编码格式异常，将跳过: {invalid[:10]}")

    client = ZlClient(ZL_USERNAME, ZL_PASSWORD, ZL_TENANT_CODE)
    client.login()
    print(f"智莱平台登录成功，待处理 ZL 编码 {len(codes)} 个")

    group_id = client.ensure_group(group_name)
    existing = {str(row.get("deviceName", "")).strip()
                for row in client.group_devices(group_id)}
    print(f"分组「{group_name}」id={group_id}，现有设备 {len(existing)} 台")

    added, skipped, missing = [], [], []
    for idx, code in enumerate(codes, 1):
        if code in existing:
            skipped.append(code)
            print(f"[{idx}/{len(codes)}] {code} 已在分组，跳过")
            continue

        rows = client.search_available_device(code, group_id)
        if not rows:
            missing.append(code)
            print(f"[{idx}/{len(codes)}] {code} 未搜索到设备")
            continue

        client.add_devices(group_id, [str(rows[0]["id"])])
        added.append(code)
        print(f"[{idx}/{len(codes)}] {code} 已加入分组")
        time.sleep(interval)

    # 回读分组设备列表做一致性校验
    final_codes = {str(row.get("deviceName", "")).strip()
                   for row in client.group_devices(group_id)}
    not_in_group = [c for c in codes if c not in final_codes]
    extra = sorted(final_codes - set(codes))

    print("\n分组导入结果:")
    print(f"  本次新增 {len(added)} 台，已存在跳过 {len(skipped)} 台，"
          f"未搜到 {len(missing)} 台")
    print(f"  分组内设备 {len(final_codes)} 台，目标编码覆盖 "
          f"{len(codes) - len(not_in_group)}/{len(codes)}")
    if extra:
        print(f"  分组内另有 {len(extra)} 台不在本次清单中: {extra[:10]}")

    if not_in_group:
        print("  校验不一致（未在分组内）:")
        for code in not_in_group:
            print(f"    {code}")
        return 1
    print("  校验通过：分组内设备编码与预备升级设备数据完全一致")
    return 0


# ---------------------------------------------------------------- 主流程

def run_green(original_path: Path, jd_path: Path, outdir: Path, interval: float) -> tuple[Path, int]:
    sites = load_sites(original_path)
    print(f"读取原始站点 {len(sites)} 条")

    client = GreenClient(USERNAME, PASSWORD)
    info = client.login()
    print(f"绿通平台登录成功：{info.get('realName')} (accountId={info.get('accountId')})")

    results = []
    for idx, site in enumerate(sites, 1):
        raw_site, code_5 = site["原始站点"], site["5位编号"]
        try:
            rows = client.search_cabinet(code_5)
            green_code, note = pick_cabinet(rows, raw_site, code_5)
        except Exception as exc:  # 单条失败不中断整体流程
            green_code, note = None, f"异常: {exc}"

        results.append({"原始站点": raw_site, "绿通设备编码": green_code or "", "备注": note})
        flag = green_code if green_code else f"未匹配（{note}）"
        print(f"[{idx}/{len(sites)}] {raw_site} -> {flag}")
        time.sleep(interval)

    target_path = write_target(results, outdir)
    print(f"\n已生成: {target_path}")

    mapping = load_zl_mapping(jd_path)
    ready_path, df = write_ready(target_path, mapping, outdir)
    print(f"已生成: {ready_path}")

    total = len(df)
    matched_zl = int((df["ZL设备编码"] != "").sum())
    print(f"绿通编码提取成功: {int((df['绿通设备编码'] != '').sum())}/{total}")
    print(f"ZL 编码映射成功: {matched_zl}/{total}")

    if matched_zl < total:
        print("未匹配明细:")
        for _, row in df[df["ZL设备编码"] == ""].iterrows():
            print(f"  {row['原始站点']}  绿通={row['绿通设备编码'] or '空'}")
        return ready_path, 1
    return ready_path, 0


def main():
    parser = argparse.ArgumentParser(description="设备升级清单生成与分组导入工具")
    parser.add_argument("--stage", choices=["all", "green", "zl"], default="all",
                        help="all=生成 Excel 并导入分组；green=只生成 Excel；zl=只导入分组")
    parser.add_argument("--original", default=str(app_dir() / DEFAULT_ORIGINAL),
                        help="原始数据.xlsx 路径")
    parser.add_argument("--jd", default=str(app_dir() / DEFAULT_JD),
                        help="京东样柜电柜号&ZL编码信息.xlsx 路径")
    parser.add_argument("--outdir", default=str(app_dir() / "输出"), help="输出目录")
    parser.add_argument("--group", default=DEFAULT_GROUP, help="智莱平台分组名称")
    parser.add_argument("--ready", default=None,
                        help="预备升级设备数据.xlsx 路径，默认取输出目录下的文件")
    parser.add_argument("--interval", type=float, default=0.2, help="每次请求间隔秒数")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ready_path = Path(args.ready) if args.ready else outdir / READY_FILE

    exit_code = 0
    if args.stage in ("all", "green"):
        original_path = Path(args.original)
        jd_path = Path(args.jd)
        if not original_path.exists():
            sys.exit(f"找不到原始数据文件: {original_path}")
        if not jd_path.exists():
            sys.exit(f"找不到京东样柜文件: {jd_path}")
        ready_path, exit_code = run_green(original_path, jd_path, outdir, args.interval)

    if args.stage in ("all", "zl"):
        exit_code = run_zl(ready_path, args.group, args.interval) or exit_code

    sys.exit(exit_code)


if __name__ == "__main__":
    if getattr(sys, "frozen", False) and len(sys.argv) == 1:
        # 双击 exe 运行时，交互式确认分组并在结束后保留窗口
        group = input(f"请输入智莱分组名称（回车使用 {DEFAULT_GROUP}）：").strip()
        if group:
            sys.argv += ["--group", group]
        try:
            main()
        except SystemExit as exc:
            if exc.code not in (0, None):
                print(f"\n执行失败: {exc.code}")
            input("\n按回车键退出...")
    else:
        main()
