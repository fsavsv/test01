#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绿通设备编码批量提取工具

流程：
  1. 读取 原始数据.xlsx 第一列站点，取末尾 5 位编号；
  2. 登录绿通后台，逐个查询电柜，取出绿通设备编码（cabinetNo）；
  3. 生成 目标设备升级文件.xlsx（原始站点 / 绿通设备编码）；
  4. 复制为 预备升级设备数据.xlsx，并用京东样柜表把绿通编码映射为 ZL 设备编码。

用法：
  python green_tool.py
  python green_tool.py --original 原始数据.xlsx --jd 京东320台样柜电柜号&ZL编码信息_20260817(1).xlsx
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


# ---------------------------------------------------------------- 主流程

def main():
    parser = argparse.ArgumentParser(description="绿通设备编码批量提取")
    parser.add_argument("--original", default=DEFAULT_ORIGINAL, help="原始数据.xlsx 路径")
    parser.add_argument("--jd", default=DEFAULT_JD, help="京东样柜电柜号&ZL编码信息.xlsx 路径")
    parser.add_argument("--outdir", default="输出", help="输出目录")
    parser.add_argument("--interval", type=float, default=0.2, help="每次查询间隔秒数")
    args = parser.parse_args()

    original_path = Path(args.original)
    jd_path = Path(args.jd)
    outdir = Path(args.outdir)

    if not original_path.exists():
        sys.exit(f"找不到原始数据文件: {original_path}")
    if not jd_path.exists():
        sys.exit(f"找不到京东样柜文件: {jd_path}")
    outdir.mkdir(parents=True, exist_ok=True)

    sites = load_sites(original_path)
    print(f"读取原始站点 {len(sites)} 条")

    client = GreenClient(USERNAME, PASSWORD)
    info = client.login()
    print(f"登录成功：{info.get('realName')} (accountId={info.get('accountId')})")

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
        time.sleep(args.interval)

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
        sys.exit(1)


if __name__ == "__main__":
    main()
