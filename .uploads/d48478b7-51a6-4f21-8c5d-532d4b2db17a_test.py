#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
================================================================================
 电池 OTA 交替升级压测脚本（基于 auto-test-framework 框架）
================================================================================

【功能】
    bms-v1.0.10、bms-v1.0.11 两个电池升级包交替升级压测。
    一轮 = 2 次升级：先升 firmware_sequence[0]，等 15 分钟，再升 firmware_sequence[1]。
    多轮执行时全局严格交替：10 -> 11 -> 10 -> 11 ...

【每次升级步骤】
    1. 进入 OTA 任务列表页  https://.../#/ota/job/list
    2. 点击【新增任务】
    3. 产品选择：智莱换电柜
    4. 固件版本选择：本次轮到的固件包
    5. 任务名称：固件版本+日期时分秒（如 bms-v1_0_10-20261013131026，不重复）
       注意：平台任务名校验不允许点号，固件版本的 "." 会替换为 "_"
       （bms-v1.0.10 -> bms-v1_0_10-20261013131026）
    6. 升级模式：立即升级
    7. 升级范围：指定设备
    8. 指定设备范围：设备分组
    9. 请选择分组：智莱测试
    10. 点击【保存】
    11. 【方案A】启动前自动取消同固件的"运行中"任务（平台规定同固件只能有1个job运行）
    12. 回到列表找到刚建的任务，点击【启动】
    13. 等待 15 分钟（不校验升级结果），进入下一次升级

【登录】
    首次自动登录：账号密码 + ddddocr 自动识别图形验证码。
    验证码识别错误会自动刷新重试（最多 login_max_retry 次）。

【运行方法】
    cd battery_ota_stress
    python test.py                  # 用 config.yaml 默认配置
    python test.py --count 3        # 跑 3 轮（6 次升级）
    python test.py --wait 15        # 覆盖每次升级后等待分钟数
    python test.py --channel chrome # 指定浏览器

【依赖】
    pip install playwright pyyaml ddddocr
    （浏览器用系统已装的 Edge/Chrome，无需 playwright install）
================================================================================
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime

# -------------------------------------------------------------------
# 路径设置：把框架根目录加入 sys.path，以便 import core / ui_frameworks
# -------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 框架根目录：优先用环境变量，其次用下面的默认绝对路径
_FRAMEWORK_ROOT = os.environ.get(
    "AUTO_TEST_FRAMEWORK_ROOT",
    r"D:\AI-mode\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6aba3579920dde3fe471f439\auto-test-framework",
)
if _FRAMEWORK_ROOT not in sys.path:
    sys.path.insert(0, _FRAMEWORK_ROOT)

from core.base_test import BaseStressTest
from core.utils import load_yaml_config, wait_with_progress
from ui_frameworks.element_ui import ElementUIHelper

# ddddocr 验证码识别（可选依赖，没装会在登录时报错提示）
try:
    import ddddocr
    _HAS_DDDDOCR = True
except ImportError:
    _HAS_DDDDOCR = False


# ===================================================================
# 电池 OTA 压测业务类
# ===================================================================
class BatteryOTAStressTest(BaseStressTest):
    """
    【功能】电池 OTA 交替升级压测业务逻辑。
    继承 BaseStressTest：循环、统计、日志、报告都由基类负责，
    本类只写业务：登录（含验证码）、新增升级任务、启动任务。
    """

    # ---------------------------------------------------------------
    # 默认配置（与基类合并；实际值以 config.yaml 为准）
    # ---------------------------------------------------------------
    DEFAULT_CONFIG = dict(BaseStressTest.DEFAULT_CONFIG, **{
        "project_name": "battery_ota_stress",
        "platform": {
            "base_url": "https://hdcloud-iot-webconsole-test.jd.com",
            "login": {
                "username": "",
                "password": "",
                "max_retry": 10,             # 验证码识别错误时的最大重试次数
            },
            "pages": {
                "ota_job_list": "/#/ota/job/list",
            },
        },
        "ota": {
            # 交替升级的固件序列（一轮内按顺序各升一次，多轮全局交替）
            "firmware_sequence": ["bms-v1.0.10", "bms-v1.0.11"],
            "product_name": "智莱换电柜",
            "upgrade_mode": "立即升级",
            "upgrade_scope": "指定设备",
            "device_scope": "设备分组",
            "group_name": "智莱测试",
            "wait_after_upgrade_minutes": 15,   # 每次升级后等待分钟数
            # 【方案A】启动新任务前自动取消同固件"运行中"任务
            "cancel_running_before_start": True,
        },
    })

    # ---------------------------------------------------------------
    # 初始化
    # ---------------------------------------------------------------
    def setup(self):
        """启动浏览器 + 初始化 UI 助手 + 初始化验证码识别器。"""
        super().setup()
        self.ui = ElementUIHelper(self.page, self.logger)
        self.ocr = None
        if _HAS_DDDDOCR:
            try:
                # show_ad=False 关广告输出；beta=True 用新模型（旧版本不支持则降级）
                try:
                    self.ocr = ddddocr.DdddOcr(show_ad=False, beta=True)
                except TypeError:
                    try:
                        self.ocr = ddddocr.DdddOcr(show_ad=False)
                    except TypeError:
                        self.ocr = ddddocr.DdddOcr()
                self.logger.info("ddddocr 验证码识别器已初始化")
            except Exception as e:
                self.logger.warning(f"ddddocr 初始化失败（登录时需手动输验证码）: {e}")
        else:
            self.logger.warning("未安装 ddddocr，验证码将无法自动识别！请执行: pip install ddddocr")

        # 全局升级计数器（跨轮累计，保证多轮也严格交替）
        self._upgrade_counter = 0

    # ============================================================
    # 通用小工具（元素定位兜底，兼容 Element UI 及其他前端框架）
    # ============================================================
    def _click_first_visible(self, locator, timeout=3000) -> bool:
        """在一批匹配元素中找到第一个可见的并点击。成功返回 True。"""
        try:
            count = locator.count()
        except Exception:
            return False
        for i in range(min(count, 30)):
            item = locator.nth(i)
            try:
                if item.is_visible():
                    item.click(timeout=timeout)
                    return True
            except Exception:
                continue
        return False

    def _first_visible(self, locator):
        """返回第一个可见元素，没有返回 None。"""
        try:
            count = locator.count()
        except Exception:
            return None
        for i in range(min(count, 30)):
            item = locator.nth(i)
            try:
                if item.is_visible():
                    return item
            except Exception:
                continue
        return None

    def _smart_click(self, text_options, desc, timeout=4000, exact=True):
        """
        按文字找元素并点击（兼容 button/a/label/span 等写法）。
        text_options: 候选文字列表；exact=True 精确匹配。
        """
        for text in text_options:
            if exact:
                selectors = [
                    f"button:has-text('{text}'), a:has-text('{text}')",
                    f"label:has(span:text-is('{text}'))",
                    f":text-is('{text}')",
                    f"label:has-text('{text}')",
                    f"text='{text}'",
                ]
            else:
                selectors = [
                    f"button:has-text('{text}'), a:has-text('{text}')",
                    f"label:has-text('{text}')",
                    f"text='{text}'",
                    f"text={text}",
                ]
            for idx, sel in enumerate(selectors):
                try:
                    if self._click_first_visible(self.page.locator(sel), timeout):
                        self.logger.info(f"  [OK] {desc} -> 命中【{text}】(策略{idx + 1})")
                        return True
                except Exception:
                    continue
        raise Exception(f"点击失败：{desc}（候选：{'、'.join(text_options)}）")

    def _select_option(self, option_text, trigger_candidates, desc, exact=False):
        """
        通用下拉框选择，依次尝试：
          1. 平铺选项（文字直接可点）
          2. 原生 <select>
          3. Element UI 弹窗内按 label 选择
          4. 点开自定义下拉再点选项
          5. 可搜索下拉：键盘输入过滤后再点
        """
        # 1. 平铺选项直接点
        try:
            if self._click_first_visible(self.page.get_by_text(option_text, exact=exact), 1500):
                self.logger.info(f"  [OK] 已选择{desc}：【{option_text}】(平铺)")
                self.page.wait_for_timeout(600)
                return
        except Exception:
            pass

        # 2. 原生 select
        try:
            selects = self.page.locator("select:visible")
            for i in range(min(selects.count(), 5)):
                s = selects.nth(i)
                opts = s.locator("option")
                for j in range(min(opts.count(), 100)):
                    try:
                        if option_text in (opts.nth(j).inner_text() or ""):
                            s.select_option(index=j)
                            self.logger.info(f"  [OK] 已选择{desc}：【{option_text}】(原生select)")
                            self.page.wait_for_timeout(600)
                            return
                    except Exception:
                        continue
        except Exception:
            pass

        # 3. Element UI：按 label 关键字选下拉
        try:
            if self.ui.select_option(self.page, desc, option_text):
                self.logger.info(f"  [OK] 已选择{desc}：【{option_text}】(ElementUI)")
                self.page.wait_for_timeout(600)
                return
        except Exception:
            pass

        # 4/5. 点开自定义下拉再点选项
        # 【重要】该平台下拉选项是异步加载的（实测：选完产品后固件版本列表
        # 偶发加载慢，面板显示"暂无数据"）。因此采用：
        #   打开下拉 -> 轮询等待选项出现 -> 清空残留过滤词 -> 关闭重开重新加载
        # 最多 3 轮，最后一轮再用键盘输入远程搜索兜底。
        option_loc = self.page.get_by_text(option_text, exact=exact)
        for round_idx in range(3):
            # 打开（第 2、3 轮即关闭后重新打开，重新触发选项加载）
            self._smart_click(trigger_candidates, f"打开[{desc}]下拉框", timeout=5000)
            self.page.wait_for_timeout(1000)

            # 轮询等待目标选项出现（最多约 6 秒，选项可能正在异步加载）
            for _ in range(12):
                if self._click_first_visible(option_loc, 500):
                    self.logger.info(f"  [OK] 已选择{desc}：【{option_text}】(下拉)")
                    self.page.wait_for_timeout(600)
                    return
                self.page.wait_for_timeout(500)

            # 未找到：可能是下拉搜索框里残留了过滤文字把结果过滤成"暂无数据"，
            # 找到下拉面板内/当前聚焦的输入框并清空，再等选项回来
            try:
                dropdown_inputs = self.page.locator(
                    ".el-select-dropdown input:visible, .ant-select-dropdown input:visible, "
                    "[class*='select-dropdown'] input:visible, [class*='dropdown'] input:visible")
                for k in range(min(dropdown_inputs.count(), 3)):
                    inp = dropdown_inputs.nth(k)
                    try:
                        if inp.input_value():
                            inp.fill("")
                            self.logger.info(f"  [{desc}] 已清空下拉内残留的过滤文字")
                    except Exception:
                        continue
                # 当前聚焦元素若是输入框，也整体删一次
                focused = self.page.locator("input:focus:visible")
                if focused.count() > 0 and (focused.first.input_value() or ""):
                    focused.first.press("Control+A")
                    focused.first.press("Delete")
                self.page.wait_for_timeout(1500)
                if self._click_first_visible(option_loc, 2000):
                    self.logger.info(f"  [OK] 已选择{desc}：【{option_text}】(清空过滤后)")
                    self.page.wait_for_timeout(600)
                    return
            except Exception:
                pass

            # 最后一轮：键盘输入做远程搜索兜底
            if round_idx == 2:
                try:
                    self.page.keyboard.type(option_text, delay=120)
                    self.page.wait_for_timeout(2000)
                    if self._click_first_visible(option_loc, 4000):
                        self.logger.info(f"  [OK] 已选择{desc}：【{option_text}】(搜索)")
                        self.page.wait_for_timeout(600)
                        return
                except Exception:
                    pass

            # 关闭下拉，下一轮重新打开触发加载
            self.logger.info(f"  [{desc}] 下拉中暂无选项【{option_text}】，关闭后重新打开重试（{round_idx + 2}/3）")
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass
            self.page.wait_for_timeout(1500)

        # 诊断：3 轮都找不到，dump 页面所有可见下拉面板内的选项真实文本，
        # 便于发现"配置名与平台选项名不一致"（如多了空格/后缀）这类问题
        try:
            self._smart_click(trigger_candidates, f"打开[{desc}]下拉框", timeout=3000)
            self.page.wait_for_timeout(1500)
        except Exception:
            pass
        try:
            diag = self.page.evaluate(
                """
                () => {
                    const out = [];
                    const panels = document.querySelectorAll(
                        '.el-select-dropdown, .ant-select-dropdown, [class*="select-dropdown"], '
                        + '[class*="dropdown-menu"], [class*="select-options"], [class*="picker-panel"]');
                    panels.forEach(panel => {
                        const r = panel.getBoundingClientRect();
                        if (r.width === 0 || r.height === 0) return;
                        const items = panel.querySelectorAll(
                            "li, .el-select-dropdown__item, [class*='option'], [class*='item'], span, div");
                        const texts = [];
                        items.forEach(it => {
                            const t = (it.innerText || '').trim().replace(/\\s+/g, ' ');
                            // 只收短文本叶子节点（真正的选项文字）
                            if (t && t.length <= 80 && it.children.length <= 1) texts.push(t);
                        });
                        out.push(...texts);
                    });
                    return Array.from(new Set(out));
                }
                """
            )
            if diag:
                self.logger.error(f"  [诊断] 可见下拉面板中的选项共 {len(diag)} 个：{diag[:60]}")
            else:
                self.logger.error("  [诊断] 当前没有任何可见的下拉面板/选项")
        except Exception as de:
            self.logger.warning(f"  [诊断] dump 下拉选项异常: {de}")

        raise Exception(f"下拉框中找不到选项【{option_text}】（{desc}，已重试3次）")

    # ============================================================
    # 登录相关（含验证码自动识别）
    # ============================================================
    def _ota_list_url(self) -> str:
        return self.config["platform"]["base_url"] + self.config["platform"]["pages"]["ota_job_list"]

    def _is_logged_in(self) -> bool:
        """访问 OTA 列表页，能看到【新增任务】且不在登录页，视为已登录。"""
        try:
            self.page.goto(self._ota_list_url(), wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(3000)
        except Exception as e:
            self.logger.warning(f"访问 OTA 列表页异常: {e}")

        url = (self.page.url or "").lower()
        if "login" in url:
            return False
        # 能看到"新增任务"按钮 -> 已登录且在目标页
        try:
            if self.page.locator("text=新增任务").count() > 0:
                return True
        except Exception:
            pass
        # 兜底：URL 不在登录页，且页面上有登录后才有的导航元素
        if "login" not in url:
            for sel in ["text=退出", "text=注销", "[class*='avatar']", "[class*='user']",
                        ".ant-menu:visible", ".el-menu:visible"]:
                try:
                    if self.page.locator(sel).count() > 0:
                        return True
                except Exception:
                    continue
        return False

    def _ensure_login(self, run_index: int):
        """确保已登录，未登录则自动登录。"""
        self.log_step("检查登录状态（已登录则跳过）")
        if self._is_logged_in():
            self.logger.info("当前已登录，跳过登录")
            return True
        self.logger.info("未登录，开始自动登录（账号+密码+验证码识别）")
        return self._do_login(run_index)

    # ---------- 登录页元素定位（多选择器兜底） ----------
    def _find_username_input(self):
        for sel in [
            "input[placeholder*='账号']", "input[placeholder*='用户名']",
            "input[placeholder*='账户']", "input[placeholder*='工号']",
            "input[name*='username' i]", "input[name*='account' i]",
            "input[id*='username' i]", "input[id*='account' i]",
            "input[autocomplete='username']",
        ]:
            item = self._first_visible(self.page.locator(sel))
            if item is not None:
                return item
        # 兜底：第一个可见文本框（排除验证码框）
        try:
            inputs = self.page.locator("input[type='text']:visible, input:not([type]):visible")
            for i in range(min(inputs.count(), 8)):
                inp = inputs.nth(i)
                ph = inp.get_attribute("placeholder") or ""
                if any(k in ph for k in ["验证码", "captcha", "图形", "校验码"]):
                    continue
                return inp
        except Exception:
            pass
        return None

    def _find_password_input(self):
        return self._first_visible(self.page.locator("input[type='password']"))

    def _find_captcha_image(self):
        """定位验证码图片（img 或 canvas 实现）。"""
        for sel in [
            "img[src*='captcha' i]", "img[src*='verify' i]", "img[src*='kaptcha' i]",
            "img[src*='code' i]", "img[src*='validcode' i]", "img[src*='validateCode' i]",
            ".captcha img:visible", ".login-code img:visible", ".code-img img:visible",
            ".verify-img img:visible", "[class*='captcha'] img:visible",
            "[class*='verify'] img:visible", "[class*='code-img'] img:visible",
        ]:
            item = self._first_visible(self.page.locator(sel))
            if item is not None:
                return item
        for sel in [
            "canvas[class*='captcha' i]", "canvas[class*='verify' i]",
            "canvas[class*='code' i]", "[class*='captcha'] canvas:visible",
            "[class*='verify'] canvas:visible",
        ]:
            item = self._first_visible(self.page.locator(sel))
            if item is not None:
                return item
        return None

    def _find_captcha_input(self):
        for sel in [
            "input[placeholder*='验证码']", "input[placeholder*='图形码']",
            "input[placeholder*='校验码']", "input[placeholder*='captcha' i]",
            "input[placeholder*='verify' i]", "input[placeholder*='code' i]",
            "input[name*='captcha' i]", "input[name*='verify' i]",
            "input[id*='captcha' i]", "input[id*='verify' i]",
            "input[maxlength='4']", "input[maxlength='5']", "input[maxlength='6']",
        ]:
            item = self._first_visible(self.page.locator(sel))
            if item is not None:
                return item
        return None

    def _find_login_button(self):
        for sel in [
            "button:has-text('登录')", "button:has-text('登 录')",
            "button:has-text('立即登录')", "button:has-text('Sign in')",
            "button[type='submit']:visible", ".login-button:visible",
            ".login-btn:visible", "[class*='login'] button:visible",
        ]:
            item = self._first_visible(self.page.locator(sel))
            if item is not None:
                return item
        return None

    def _refresh_captcha(self, captcha_element):
        """点击验证码图片换一张新的（或点"换一张"按钮）。"""
        try:
            captcha_element.click(timeout=3000)
            self.page.wait_for_timeout(1000)
            return True
        except Exception:
            pass
        for text in ["换一张", "看不清", "刷新", "点击刷新"]:
            try:
                if self._click_first_visible(self.page.locator(f"text='{text}'"), 1500):
                    self.page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue
        return False

    def _read_login_error(self) -> str:
        """读取登录失败提示文字（覆盖 element-ui/antd/自定义样式）。"""
        for sel in [
            ".el-message--error:visible", ".el-message__content:visible",
            ".ant-message-error:visible", ".ant-form-item-explain-error:visible",
            ".error-message:visible", ".error-msg:visible", ".tip-error:visible",
            ".login-error:visible", "[class*='error']:visible",
        ]:
            try:
                loc = self.page.locator(sel)
                if loc.count() > 0:
                    for i in range(min(loc.count(), 5)):
                        txt = loc.nth(i).inner_text(timeout=500)
                        if txt and txt.strip():
                            return txt.strip()
            except Exception:
                continue
        return ""

    def _do_login(self, run_index: int) -> bool:
        """
        自动登录主流程：
          定位账号/密码/验证码元素 -> OCR 识别验证码 -> 填入 -> 点登录
          失败则刷新验证码重试，最多 max_retry 次。
        """
        self.log_step("自动登录平台")
        login_cfg = self.config["platform"]["login"]
        max_retry = int(login_cfg.get("max_retry", 10))

        # 先访问 OTA 列表页，未登录会被重定向到登录页
        self.page.goto(self._ota_list_url(), wait_until="domcontentloaded", timeout=30000)
        self.page.wait_for_timeout(3000)
        self.screenshot("login_page", run_index)

        for attempt in range(1, max_retry + 1):
            self.logger.info(f"---- 登录第 {attempt}/{max_retry} 次尝试 ----")

            # 每次重试都重新定位（防止 DOM 刷新后旧引用失效）
            username_input = self._find_username_input()
            password_input = self._find_password_input()
            captcha_img = self._find_captcha_image()
            captcha_input = self._find_captcha_input()
            login_btn = self._find_login_button()

            if username_input is None or password_input is None:
                self.screenshot(f"login_locate_{attempt}", run_index)
                self.logger.error("账号或密码输入框定位失败")
                self.page.wait_for_timeout(2000)
                if attempt == 1:
                    continue
                raise Exception("登录页账号/密码输入框定位失败，请查看截图确认页面结构")

            # 填账号（先清空防自动填充干扰）
            try:
                username_input.click(timeout=3000)
                username_input.fill("")
                username_input.fill(login_cfg["username"])
                self.logger.info(f"  [OK] 账号已填入: {login_cfg['username']}")
            except Exception as e:
                self.logger.warning(f"  填账号异常: {e}")

            # 填密码
            try:
                password_input.click(timeout=3000)
                password_input.fill("")
                password_input.fill(login_cfg["password"])
                self.logger.info("  [OK] 密码已填入: " + "*" * len(login_cfg["password"]))
            except Exception as e:
                self.logger.warning(f"  填密码异常: {e}")

            # 验证码识别与填入
            captcha_text = ""
            if captcha_img is not None:
                if self.ocr is None:
                    self.logger.warning("  页面有验证码，但 ddddocr 不可用！")
                else:
                    try:
                        # 截取验证码图片字节 -> ddddocr 识别 -> 只保留字母数字
                        img_bytes = captcha_img.screenshot(timeout=5000)
                        raw_text = self.ocr.classification(img_bytes)
                        captcha_text = re.sub(r"[^A-Za-z0-9]", "", raw_text or "")
                        self.logger.info(f"  [OK] 验证码识别: 原始【{raw_text}】-> 清洗【{captcha_text}】")
                    except Exception as e:
                        self.logger.warning(f"  验证码识别异常: {e}")

                if captcha_input is not None and captcha_text:
                    try:
                        captcha_input.click(timeout=3000)
                        captcha_input.fill("")
                        captcha_input.fill(captcha_text)
                        self.logger.info("  [OK] 验证码已填入")
                    except Exception as e:
                        self.logger.warning(f"  填验证码异常: {e}")
            else:
                self.logger.info("  页面无验证码，直接账号密码登录")

            self.screenshot("login_filled", run_index)

            # 点登录（找不到按钮就回车提交）
            if login_btn is not None:
                try:
                    login_btn.click(timeout=5000)
                    self.logger.info("  [OK] 已点击登录按钮")
                except Exception as e:
                    self.logger.warning(f"  点击登录按钮异常: {e}，尝试回车提交")
                    try:
                        password_input.press("Enter")
                    except Exception:
                        pass
            else:
                try:
                    password_input.press("Enter")
                    self.logger.info("  [OK] 通过回车提交登录")
                except Exception as e:
                    raise Exception(f"无法提交登录表单: {e}")

            self.page.wait_for_timeout(3000)

            # 判定登录结果
            if self._is_logged_in():
                self.logger.info(f">>>> 自动登录成功！（第 {attempt} 次尝试）")
                self.screenshot("login_success", run_index)
                return True

            err = self._read_login_error()
            self.logger.warning(f"  登录未成功{f'，页面提示：{err}' if err else '，未读到错误提示'}")

            # 刷新验证码供下次识别
            if captcha_img is not None:
                new_img = self._find_captcha_image()
                if new_img is not None:
                    self._refresh_captcha(new_img)
                    self.logger.info("  已刷新验证码")
                self.page.wait_for_timeout(1000)

        self.screenshot("login_final_fail", run_index)
        raise Exception(f"自动登录失败，已重试 {max_retry} 次，请查看截图排查")

    # ============================================================
    # OTA 新增任务 + 启动 业务流程
    # ============================================================
    # 离开确认弹窗的提示语关键词（用于判断弹窗是否存在）
    _LEAVE_CONFIRM_KEYWORDS = ["确定要返回吗", "丢失已编辑", "确定要离开", "确认离开", "确定离开", "放弃编辑"]
    # 弹窗上"确认离开"按钮可能的文字（该平台按钮文字常带空格，如"保 存"、"返 回"）
    _LEAVE_CONFIRM_BTNS = ["返 回", "返回", "确 定", "确定", "确 认", "确认离开", "离 开", "离开", "放 弃", "放弃"]

    def _dismiss_leave_confirm(self):
        """
        处理路由离开确认弹窗：
        表单页/详情页跳转时，平台可能弹"当前页面处于编辑状态，返回会丢失
        已编辑的内容 确定要返回吗？"等确认框，点【返回/确定】确认离开。
        注意：
          1) 绝不能点【取消】（取消=留在当前页）；
          2) 该平台按钮文字可能带空格（实测"保 存"，弹窗按钮可能是"返 回"），
             且可能不是 <button>，所以除 Playwright 选择器外再用 JS 归一化
             （去除所有空白）文本匹配兜底。
        """
        try:
            hit = False
            for kw in self._LEAVE_CONFIRM_KEYWORDS:
                if self.page.locator(f"text={kw}").count() > 0:
                    hit = True
                    break
            if not hit:
                return
        except Exception:
            return

        # 方式1：Playwright 选择器（在弹窗容器内找，避免误点面包屑/菜单）
        for text in self._LEAVE_CONFIRM_BTNS:
            try:
                loc = self.page.locator(
                    f".el-message-box__btns button:has-text('{text}'), "
                    f".el-dialog__footer button:has-text('{text}'), "
                    f".ant-modal-confirm-btns button:has-text('{text}'), "
                    f"[role='dialog'] button:has-text('{text}'), "
                    f"button:has-text('{text}'), a:has-text('{text}'), span:text-is('{text}')"
                )
                if self._click_first_visible(loc, 1200):
                    self.logger.info(f"  [OK] 离开确认弹窗已点【{text}】")
                    self.page.wait_for_timeout(1200)
                    return
            except Exception:
                continue

        # 方式2：JS 归一化文本匹配（去空格后比较，兼容"返 回"/非 button 元素）
        try:
            clicked = self.page.evaluate(
                """
                (keywords) => {
                    const norm = s => (s || '').replace(/\\s+/g, '');
                    const isVisible = el => {
                        if (!el) return false;
                        const r = el.getBoundingClientRect();
                        if (r.width === 0 || r.height === 0) return false;
                        const st = window.getComputedStyle(el);
                        return st.display !== 'none' && st.visibility !== 'hidden' && st.opacity !== '0';
                    };
                    const dialogs = Array.from(document.querySelectorAll(
                        '.el-message-box, .el-dialog, .ant-modal, [role="dialog"], .modal, .layui-layer, .van-dialog'));
                    for (const d of dialogs) {
                        if (!isVisible(d)) continue;
                        const body = norm(d.innerText || '');
                        if (!keywords.some(k => body.includes(norm(k)))) continue;
                        const want = ['返回', '确定', '确认', '离开', '放弃'];
                        let nodes = Array.from(d.querySelectorAll('button, a, span, div'))
                            .filter(el => isVisible(el) && want.includes(norm(el.innerText || '')));
                        // 选文本最短的（叶子按钮），避免点到包裹整个弹窗的容器
                        nodes.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
                        if (nodes.length) { nodes[0].click(); return true; }
                    }
                    return false;
                }
                """,
                self._LEAVE_CONFIRM_KEYWORDS,
            )
            if clicked:
                self.logger.info("  [OK] 离开确认弹窗已通过 JS 兜底点击确认按钮")
                self.page.wait_for_timeout(1200)
                return
        except Exception as e:
            self.logger.warning(f"  JS 兜底处理离开弹窗异常: {e}")

        self.logger.warning("  出现离开确认弹窗但未找到确认按钮")

    def _is_on_ota_list(self) -> bool:
        """判断当前是否真的在任务列表页（URL 含 /list 且能看到【新增任务】按钮）。"""
        try:
            url_ok = "ota/job/list" in (self.page.url or "")
            btn_ok = self.page.locator("text=新增任务").count() > 0
            return url_ok and btn_ok
        except Exception:
            return False

    def _check_save_validation(self):
        """
        保存后检测表单是否有红字校验错误（如任务名格式不合法）。
        有则抛出异常（带上错误文字），避免无效地去列表找根本不存在的任务。
        """
        for sel in [".el-form-item__error:visible",
                    ".ant-form-item-explain-error:visible",
                    "[class*='form-item'][class*='error']:visible"]:
            try:
                loc = self.page.locator(sel)
                if loc.count() > 0:
                    for i in range(min(loc.count(), 5)):
                        txt = loc.nth(i).inner_text(timeout=500)
                        if txt and txt.strip():
                            raise Exception(f"表单校验未通过，保存失败：{txt.strip()}")
            except Exception as e:
                if "表单校验未通过" in str(e):
                    raise
                continue

    def _navigate_to_ota_list(self, run_index: int):
        """
        进入 OTA 任务列表页。
        带到达校验（必须能看到【新增任务】按钮）：点【启动】后平台可能跳到
        任务详情页，且详情页/表单页有路由离开拦截，第一次 goto 可能被拦下，
        因此最多重试 3 次，并用面包屑/菜单【任务管理】作为兜底返回方式。
        """
        self.log_step("进入 OTA 任务列表页")
        for attempt in range(1, 4):
            try:
                self.page.goto(self._ota_list_url(), wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                self.logger.warning(f"  goto 列表页异常: {e}")
            self.page.wait_for_timeout(2000)
            self._dismiss_leave_confirm()  # 处理"确定要返回吗"等离开拦截弹窗
            self.page.wait_for_timeout(1000)

            if self._is_on_ota_list():
                self.screenshot("ota_job_list", run_index)
                return

            self.logger.warning(f"  第 {attempt} 次进入列表页未成功（可能停在详情页或被弹窗拦截）")
            # 兜底：点面包屑/左侧菜单中的"任务管理"返回列表
            try:
                if self._click_first_visible(
                    self.page.locator(".ant-breadcrumb text=任务管理, .el-breadcrumb text=任务管理, "
                                      "a:has-text('任务管理'), span:text-is('任务管理')"),
                    2000,
                ):
                    self.logger.info("  [OK] 通过【任务管理】导航返回列表页")
                    self.page.wait_for_timeout(2000)
                    self._dismiss_leave_confirm()
                    if self._is_on_ota_list():
                        self.screenshot("ota_job_list", run_index)
                        return
            except Exception:
                pass

        # 3 次都没成功也截图留证，让后续步骤抛出更明确的错误
        self.screenshot("ota_job_list_fail", run_index)
        raise Exception("多次尝试后仍无法进入任务列表页（看不到【新增任务】按钮），请查看截图")

    def _open_create_dialog(self, run_index: int):
        """点击【新增任务】按钮，进入新建任务表单/弹窗。"""
        self.log_step("点击【新增任务】")
        self._smart_click(["新增任务", "新建任务", "添加任务", "新增升级任务"], "新增任务")
        self.page.wait_for_timeout(2500)
        # 若新开了标签页则切换过去
        try:
            pages = self.context.pages
            if len(pages) > 1 and pages[-1] is not self.page:
                pages[-1].bring_to_front()
                self.page = pages[-1]
                self.logger.info("  检测到新标签页，已切换")
        except Exception:
            pass
        self.screenshot("create_dialog_opened", run_index)

    def _fill_task_form(self, firmware: str, task_name: str, run_index: int):
        """填写新建任务表单。"""
        ota_cfg = self.config["ota"]

        # 3. 产品选择
        self.log_step(f"选择产品：{ota_cfg['product_name']}")
        self._select_option(
            ota_cfg["product_name"],
            ["选择产品", "请选择产品", "请选择产品名称", "请选择产品/固件", "请选择"],
            "产品",
        )
        self.page.wait_for_timeout(2000)  # 选完产品后固件列表需异步加载，多等一会避免"暂无数据"

        # 4. 固件版本选择（选项可能带附加信息，用包含匹配）
        self.log_step(f"选择固件版本：{firmware}")
        self._select_option(
            firmware,
            ["请选择固件版本", "请选择固件", "请选择版本", "请选择"],
            "固件版本",
        )

        # 5. 任务名称
        self.log_step(f"填写任务名称：{task_name}")
        filled = False
        for sel in ["input[placeholder*='任务名称']",
                    "textarea[placeholder*='任务名称']",
                    "input[placeholder*='请输入任务名称']"]:
            loc = self.page.locator(sel)
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.fill(task_name)
                    filled = True
                    break
            except Exception:
                continue
        if not filled:
            try:
                label_loc = self.page.locator("label:has-text('任务名称')")
                if label_loc.count() > 0:
                    inp = label_loc.first.locator("xpath=following::input[1]")
                    if inp.count() > 0:
                        inp.first.fill(task_name)
                        filled = True
            except Exception:
                pass
        if not filled:
            raise Exception("找不到【任务名称】输入框")
        self.logger.info(f"  [OK] 任务名称：{task_name}")
        self.page.wait_for_timeout(500)

        # 6-9. 升级模式 / 升级范围 / 指定设备范围 / 分组（单选或下拉，均做兼容）
        for label, value, triggers in [
            ("升级模式", ota_cfg["upgrade_mode"], ["请选择升级模式", "请选择"]),
            ("升级范围", ota_cfg["upgrade_scope"], ["请选择升级范围", "请选择"]),
            ("指定设备范围", ota_cfg["device_scope"], ["请选择设备范围", "请选择"]),
            ("请选择分组", ota_cfg["group_name"], ["选择设备分组", "请选择设备分组", "请选择分组名称", "请选择"]),
        ]:
            self.log_step(f"设置{label}：{value}")
            try:
                # 优先按单选按钮/文字直接点
                self._smart_click([value], f"{label}[{value}]", timeout=3000, exact=True)
            except Exception:
                # 再按下拉框处理
                self._select_option(value, triggers, label, exact=True)
            self.page.wait_for_timeout(500)

        self.screenshot("form_all_filled", run_index)

    def _collect_visible_toasts(self):
        """收集页面上当前可见的 toast/通知条文本（ElementUI/Ant 等多种实现都兼容）。"""
        texts = []
        selectors = [".el-message:visible", ".el-notification:visible",
                     ".ant-message-notice:visible", ".ant-notification-notice:visible",
                     "[class*='message']:visible", "[class*='toast']:visible",
                     "[class*='notice']:visible"]
        for sel in selectors:
            try:
                loc = self.page.locator(sel)
                for i in range(min(loc.count(), 6)):
                    try:
                        t = loc.nth(i).inner_text(timeout=300)
                    except Exception:
                        continue
                    t = (t or "").strip()
                    # 去掉内部换行、去重、过滤太长的误命中
                    t = re.sub(r"\s+", " ", t)
                    if t and 0 < len(t) <= 120 and t not in texts:
                        texts.append(t)
            except Exception:
                continue
        return texts

    def _save_task(self, run_index: int):
        """
        点击【保存】并确认保存成功（页面跳回任务列表）。
        保存点击后可能：
          a) 正常跳回列表；
          b) 接口慢，需要多等几秒；
          c) 平台弹 toast 拒绝（如重复任务等），红字/黑条一闪而过；
          d) 点击未生效（偶发），需要重点一次。
        因此轮询 URL + toast + 表单红字，最多点击 3 次保存，避免盲目跳转。
        """
        self.log_step("点击【保存】")
        last_toasts = []
        saved_ok = False
        for click_idx in range(1, 4):
            if click_idx == 1:
                self._smart_click(["保 存", "保存", "确定", "提交"], "保存")
            else:
                self.logger.info(f"  保存后页面未跳转，第 {click_idx} 次点击【保存】")
                try:
                    self._smart_click(["保 存", "保存"], "保存", timeout=5000)
                except Exception as ce:
                    self.logger.warning(f"  第 {click_idx} 次点击保存失败: {ce}")

            # 轮询最多约 10 秒，等待跳转或提示出现
            for _ in range(10):
                self.page.wait_for_timeout(1000)
                try:
                    url = self.page.url or ""
                except Exception:
                    url = ""
                # 已离开新增页 = 保存成功
                if "ota/job/add" not in url and "ota/job/edit" not in url:
                    saved_ok = True
                    break
                # 收集 toast 提示
                toasts = self._collect_visible_toasts()
                for t in toasts:
                    if t not in last_toasts:
                        self.logger.info(f"  平台提示：{t}")
                last_toasts = toasts
                # 表单红字校验错误
                try:
                    self._check_save_validation()
                except Exception:
                    self.screenshot("after_save_validation_error", run_index)
                    raise
                # toast 中出现明确的错误措辞
                err_kw = ("失败", "已存在", "不能", "无法", "错误", "请选择", "请填写", "不允许", "超过")
                if any(any(k in t for k in err_kw) for t in toasts):
                    self.page.wait_for_timeout(800)  # 等提示稳定后截图
                    self.screenshot("after_save_error", run_index)
                    raise Exception(f"保存被平台拒绝：{' | '.join(toasts)}")

            self.screenshot("after_save", run_index)
            if saved_ok:
                break

        if not saved_ok:
            self.screenshot("after_save_no_response", run_index)
            raise Exception("点击保存后页面一直停留在新增表单页（未跳转、无错误提示），请查看截图")

        self.logger.info("  [OK] 保存成功，已离开新增表单页")
        self.page.wait_for_timeout(1500)

        # 回到任务列表（保存后若表单标签页被关，切换回列表页）
        try:
            _ = self.page.url
        except Exception:
            pages = self.context.pages
            if pages:
                self.page = pages[-1]
        if "ota/job/list" in (self.page.url or ""):
            self.page.reload(wait_until="domcontentloaded")
            self.page.wait_for_timeout(2000)
        else:
            try:
                self.page.goto(self._ota_list_url(), wait_until="domcontentloaded", timeout=30000)
                self.page.wait_for_timeout(2000)
                self._dismiss_leave_confirm()  # 处理"确定要返回吗"弹窗（若有）
                self.page.wait_for_timeout(1000)
            except Exception:
                pass

    def _find_task_row(self, task_name: str):
        """
        在任务列表中定位刚创建的任务行。

        【注意】平台对任务名称列做了截断显示（实测约 20 个字符），截断后的
        文本直接存进 DOM，完整任务名并不存在于 HTML 中！且无 title 属性、无搜索框。
        不同固件前缀长度不同，截断位置也不同：
          - bms-v1_0_10-20261014123237      -> 显示 bms-v1_0_10-20261014（20字符）
          - firmware-v2_3_11-20261014123237 -> 显示 firmware-v2_3_11-202（20字符）

        【匹配策略】任务名前 20 字符（主）或前 16 字符（兜底，防止列宽变化）
        任一命中行文本 + 固件版本列匹配 + 5 分钟新鲜度，三重校验；
        列表按更新时间倒序，第一个匹配行即为刚创建的任务。
        """
        # 名称匹配候选：前 20 字符（实测截断长度）+ 前 16 字符（兜底）
        # 短前缀对 firmware-v2_3_11 / v2_3_12 仍可区分（第 15 字符即不同）
        name_prefixes = [task_name[:20]]
        if len(task_name) >= 16:
            name_prefixes.append(task_name[:16])
        # 固件版本列文字（bms-v1_0_10-... -> v1.0.10；firmware-v2_3_11-... -> v2.3.11），
        # 取 "-v版本-" 之间部分，兼容任意固件类型前缀
        firmware_col = ""
        m = re.search(r"-(v[\d_]+)-", task_name)
        if m:
            firmware_col = m.group(1).replace("_", ".")
        self.logger.info(f"  列表匹配规则：名称前缀候选{name_prefixes} + 固件列【{firmware_col}】")

        try:
            rows = self.page.locator("tr")
            count = min(rows.count(), 30)
        except Exception:
            return None
        for i in range(count):
            row = rows.nth(i)
            try:
                txt = row.inner_text() or ""
            except Exception:
                continue
            # 名称前缀候选任一命中，且固件版本列匹配
            if not any(p in txt for p in name_prefixes):
                continue
            if firmware_col and firmware_col not in txt:
                continue
            # 新鲜度校验：行的"更新时间"必须在 5 分钟内。
            # 同日同固件的历史任务前缀相同，防止列表缓存未刷新时误点旧任务。
            # （服务器时钟可能比本地快，age 为负数也算新鲜）
            tm = re.search(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", txt)
            if tm:
                try:
                    row_time = datetime.strptime(tm.group(0).replace("T", " "), "%Y-%m-%d %H:%M:%S")
                    age = (datetime.now() - row_time).total_seconds()
                    if age > 5 * 60:
                        self.logger.info(f"  跳过历史任务行（更新时间 {tm.group(0)}，{int(age)} 秒前）")
                        continue
                except Exception:
                    pass
            return row
        return None

    def _try_search_task(self, task_name: str) -> bool:
        """用列表页搜索框搜索任务名。"""
        try:
            search = self.page.locator("input[placeholder*='任务名称'], input[placeholder*='搜索']")
            if search.count() > 0 and search.first.is_visible():
                search.first.fill(task_name)
                self.page.wait_for_timeout(500)
                search.first.press("Enter")
                self.page.wait_for_timeout(1500)
                try:
                    self._smart_click(["查询", "搜索", "查 询"], "查询", timeout=2000)
                except Exception:
                    pass
                self.page.wait_for_timeout(1500)
                return True
        except Exception:
            pass
        return False

    def _confirm_popup_if_any(self):
        """启动后的二次确认弹窗自动点确认。"""
        self.page.wait_for_timeout(1500)
        dialog = self.page.locator(
            ".ant-modal:visible, .el-message-box:visible, .el-dialog:visible, [role='dialog']:visible"
        )
        try:
            if dialog.count() == 0:
                return
        except Exception:
            return
        for text in ["确定", "确认", "是", "OK"]:
            try:
                if self._click_first_visible(dialog.first.locator(f"button:has-text('{text}')"), 3000):
                    self.logger.info(f"  [OK] 二次确认弹窗点【{text}】")
                    return
            except Exception:
                continue

    # ============================================================
    # 【方案A】启动前自动取消同固件"运行中"任务
    # ============================================================
    def _cancel_running_tasks_same_firmware(self, firmware: str, run_index: int):
        """
        【方案A】启动新任务前，自动取消列表中同固件的"运行中"任务。

        【原因】平台规定同一固件同时只允许 1 个 job 运行；
        若有"运行中"的旧任务（可能是本脚本上一轮启动的，也可能是共享环境
        中其他人启动的），新任务的【启动】会被拒绝并提示
        "指定固件下只能有一个job运行"。

        【做法】遍历列表行，找到固件列匹配且状态为"运行中"的行，
        点击其操作列的【取消】按钮，处理可能的取消确认弹窗。
        """
        ota_cfg = self.config["ota"]
        if not ota_cfg.get("cancel_running_before_start", True):
            return

        self.log_step(f"【方案A】检查并取消固件【{firmware}】的运行中任务")
        # 确保停在列表页（点启动后可能跳到详情页，带校验的重试导航）
        try:
            for _nav_attempt in range(3):
                if self._is_on_ota_list():
                    break
                self.page.goto(self._ota_list_url(), wait_until="domcontentloaded", timeout=30000)
                self.page.wait_for_timeout(2000)
                self._dismiss_leave_confirm()
                self.page.wait_for_timeout(1000)
        except Exception:
            pass

        # 从固件名提取版本号用于列表行匹配
        # （config 里是 "bms-v1.0.10"，但列表行固件版本列只显示 "v1.0.10"）
        fw_version = firmware.split("-", 1)[1] if "-" in firmware else firmware

        try:
            rows = self.page.locator("tr")
            count = min(rows.count(), 30)
        except Exception:
            return

        cancelled = 0
        for i in range(count):
            row = rows.nth(i)
            try:
                txt = row.inner_text() or ""
            except Exception:
                continue
            # 必须同时满足：固件版本列匹配 + 状态为运行中
            # 注意：行文本里固件版本列是 "v1.0.10"（不含 bms- 前缀）
            if fw_version not in txt:
                continue
            if "运行中" not in txt:
                continue
            # 排除表头行
            if "任务名称" in txt and "操作" in txt:
                continue

            self.logger.info(f"  发现运行中任务（行{i}）：{txt[:100]}")
            # 点击行内【取消】按钮（平台操作列为 span，用精确文本匹配避免点偏）
            cancel_loc = row.get_by_text("取消", exact=True)
            if not self._click_first_visible(cancel_loc, 3000):
                btn = row.locator("button:has-text('取消'), a:has-text('取消'), span:text-is('取消')")
                if not self._click_first_visible(btn, 3000):
                    self.logger.warning(f"  行{i}未找到【取消】按钮")
                    continue

            self.page.wait_for_timeout(1500)
            # 处理可能的取消确认弹窗
            self._confirm_popup_if_any()
            self.page.wait_for_timeout(2000)
            # 刷新列表以获取最新状态
            try:
                self.page.reload(wait_until="domcontentloaded")
                self.page.wait_for_timeout(2000)
            except Exception:
                pass
            cancelled += 1
            self.logger.info(f"  [OK] 已取消固件【{firmware}】的运行中任务")

        if cancelled == 0:
            self.logger.info(f"  固件【{firmware}】无运行中任务，无需取消")
        else:
            self.logger.info(f"  【方案A】共取消 {cancelled} 个固件【{firmware}】的运行中任务")
            self.screenshot("after_cancel_running", run_index)

    def _start_task_on_list(self, task_name: str, run_index: int):
        """在任务列表找到刚创建的任务，点击【启动】。"""
        self.log_step(f"查找任务【{task_name}】并点击启动")
        for attempt in range(1, 4):
            self.logger.info(f"  查找任务（第 {attempt} 次）...")
            row = self._find_task_row(task_name)
            if row is not None:
                for text in ["启动", "开始升级", "启动升级", "开始"]:
                    # 【关键】必须用精确文本匹配！
                    # 操作列"查看进度/启动/编辑/删除"可能被同一个外层 span 包裹，
                    # 用 has-text（子串匹配）会命中外层元素，点击中心点偏到
                    # 【查看进度】误入任务详情页。exact=True 只匹配文本恰好相等的叶子元素。
                    clicked = False
                    exact_loc = row.get_by_text(text, exact=True)
                    if self._click_first_visible(exact_loc, 2500):
                        clicked = True
                    else:
                        btn = row.locator(
                            f"button:has-text('{text}'), a:has-text('{text}'), span:text-is('{text}')"
                        )
                        clicked = self._click_first_visible(btn, 2500)
                    if clicked:
                        self.logger.info(f"  [OK] 已点击任务【{task_name}】的【{text}】按钮")
                        self._confirm_popup_if_any()
                        self.page.wait_for_timeout(2000)
                        self.screenshot("task_started", run_index)
                        # 若点击后误入任务详情页（点偏或平台自动跳转），返回列表页
                        if not self._is_on_ota_list():
                            self.logger.info("  点击后不在列表页（可能进入了任务详情），导航回列表页")
                            try:
                                self.page.goto(self._ota_list_url(),
                                               wait_until="domcontentloaded", timeout=30000)
                                self.page.wait_for_timeout(2000)
                                self._dismiss_leave_confirm()
                            except Exception:
                                pass
                        return
                # 行内没有启动按钮但状态显示进行中，视为已启动
                try:
                    row_text = row.inner_text()
                    if any(k in row_text for k in ["升级中", "进行中", "已启动", "正在升级", "运行中"]):
                        self.logger.info("  无启动按钮但任务状态为进行中/运行中，视为已启动")
                        return
                except Exception:
                    pass
                raise Exception(f"任务【{task_name}】所在行没有找到启动按钮")
            # 没找到：先搜索，再重新导航到列表页
            # （用 goto 而非 reload——若当前停在详情页，reload 仍停在详情页）
            if not self._try_search_task(task_name):
                try:
                    self.page.goto(self._ota_list_url(), wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    self.page.reload(wait_until="domcontentloaded")
                self.page.wait_for_timeout(2000)
                self._dismiss_leave_confirm()
                self.page.wait_for_timeout(2000)
        raise Exception(f"任务列表中始终找不到任务【{task_name}】，请查看截图")

    def _do_one_upgrade(self, firmware: str, run_index: int, seq_in_round: int) -> dict:
        """
        执行一次完整升级：新增任务 -> 保存 -> 【方案A】取消同固件运行中任务 -> 启动。
        返回该次升级的阶段结果。
        """
        # 任务名称 = 固件版本 + 日期时分秒（精确到秒，不重复）
        # 注意：平台校验规则只允许 中文/英文/数字/连字符/下划线（不允许点号），
        # 所以把固件版本中的 "." 替换为 "_"，如 bms-v1.0.10 -> bms-v1_0_10
        safe_firmware = firmware.replace(".", "_")
        task_name = "%s-%s" % (safe_firmware, datetime.now().strftime("%Y%m%d%H%M%S"))
        stage_name = f"升级{firmware}"
        self.logger.info(f"\n>>> 第 {run_index + 1} 轮 - 第 {seq_in_round} 次升级，固件：{firmware}，任务名：{task_name}")

        try:
            self._navigate_to_ota_list(run_index)
            # 填表阶段对"下拉选项异步加载失败（暂无数据）"重试 1 次：
            # 重新回列表->重新进入新增页->重新填表（此阶段尚未保存，不会产生重复任务）
            for form_attempt in range(2):
                self._open_create_dialog(run_index)
                try:
                    self._fill_task_form(firmware, task_name, run_index)
                    break
                except Exception as fe:
                    if form_attempt == 0 and ("下拉框中找不到选项" in str(fe) or "暂无数据" in str(fe)):
                        self.logger.warning("  表单下拉选项加载失败（暂无数据），重新进入新增页再试一次")
                        try:
                            self.page.goto(self._ota_list_url(),
                                           wait_until="domcontentloaded", timeout=30000)
                            self.page.wait_for_timeout(2000)
                            self._dismiss_leave_confirm()
                        except Exception:
                            pass
                        continue
                    raise
            self._save_task(run_index)
            # 【方案A】启动前取消同固件运行中任务（平台规定同固件只能有1个job运行）
            self._cancel_running_tasks_same_firmware(firmware, run_index)
            self._start_task_on_list(task_name, run_index)
            self.logger.info(f">>>> 任务【{task_name}】已成功启动升级！")
            return {"name": stage_name, "firmware": firmware, "task": task_name, "ok": True}
        except Exception as e:
            self.logger.error(f"任务【{task_name}】执行失败: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            self.screenshot(f"error_upgrade_{firmware}", run_index)
            return {"name": stage_name, "firmware": firmware, "task": task_name,
                    "ok": False, "error": str(e)}

    # ============================================================
    # 单轮业务流程（基类循环调用）
    # ============================================================
    def run_one_round(self, round_index: int) -> dict:
        """
        一轮 = firmware_sequence 中每个固件各升级一次。
        多轮执行时靠 self._upgrade_counter 全局计数，保证严格交替。
        每次升级后等待 wait_after_upgrade_minutes 分钟（不校验升级结果）。
        """
        result = {"success": False, "error": None, "stages": []}
        ota_cfg = self.config["ota"]
        sequence = ota_cfg["firmware_sequence"]
        wait_minutes = ota_cfg["wait_after_upgrade_minutes"]

        # 1. 确保已登录
        self._ensure_login(round_index)

        # 2. 本轮内按序列逐个升级
        for seq_idx, _ in enumerate(sequence):
            # 用全局计数器取固件，保证跨轮也严格交替：10 -> 11 -> 10 -> 11 ...
            firmware = sequence[self._upgrade_counter % len(sequence)]
            self._upgrade_counter += 1

            stage = self._do_one_upgrade(firmware, round_index, seq_idx + 1)
            result["stages"].append(stage)

            # 不是本轮最后一次升级 -> 等待指定分钟数
            if seq_idx < len(sequence) - 1:
                self.log_step(f"等待 {wait_minutes} 分钟后开始本轮第 {seq_idx + 2} 次升级")
                wait_with_progress(int(wait_minutes * 60), self.logger,
                                   f"升级等待中（下次升级 {sequence[self._upgrade_counter % len(sequence)]}）",
                                   interval_seconds=60)

        # 3. 本轮成功 = 所有升级都成功
        result["success"] = all(s["ok"] for s in result["stages"])
        return result


# ===================================================================
# 主入口
# ===================================================================
def main():
    parser = argparse.ArgumentParser(description="电池 OTA 交替升级压测脚本")
    parser.add_argument("--config", type=str,
                        default=os.path.join(_SCRIPT_DIR, "config.yaml"),
                        help="配置文件路径（默认 ./config.yaml）")
    parser.add_argument("--count", type=int, default=None,
                        help="执行轮次（覆盖配置文件 rounds；1 轮 = 2 次升级）")
    parser.add_argument("--headless", action="store_true",
                        help="无头模式（不显示浏览器窗口）")
    parser.add_argument("--wait", type=float, default=None,
                        help="每次升级后等待分钟数（覆盖配置）")
    parser.add_argument("--channel", type=str, default=None,
                        choices=["msedge", "chrome", "chromium"],
                        help="浏览器通道（覆盖配置）")
    args = parser.parse_args()

    # 加载配置文件
    config = load_yaml_config(args.config)

    # 命令行覆盖配置（命令行优先级最高）
    if args.count is not None:
        config["rounds"] = args.count
    if args.headless:
        config["headless"] = True
    if args.wait is not None:
        config.setdefault("ota", {})["wait_after_upgrade_minutes"] = args.wait
    if args.channel:
        config["browser_channel"] = args.channel

    test = BatteryOTAStressTest(config)
    sys.exit(test.run())


if __name__ == "__main__":
    main()
