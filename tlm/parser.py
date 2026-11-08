"""``.adofai`` 谱面解析。

ADOFAI 的谱面有两种轨道写法：
* ``pathData``：一串方向字符（R/L/U/D...），需要换算成角度；
* ``angleData``：直接给角度（新格式）。

本模块把两种格式统一成 ``angleData``，并且尽量修复被截断 / 有语法小错的 JSON
（玩家社群里的谱面经常是被手改过的）。
"""

from __future__ import annotations

import json
import re

from .log import get_logger

logger = get_logger("解析")

#: 方向字符 -> 角度 的映射表
DIRECTION_ANGLES: dict[str, float] = {
    "R": 0,
    "L": 180,
    "U": 90,
    "D": -90,
    "E": 45,
    "Q": 135,
    "Z": -135,
    "C": -45,
    "J": 30,
    "T": 60,
    "G": 120,
    "H": 150,
    "N": -150,
    "F": -120,
    "B": -60,
    "M": -30,
    "p": 15,
    "A": -15,
    "Y": -75,
    "V": -105,
    "x": -165,
    "W": 165,
    "q": 105,
    "o": 75,
    "!": 999,  # 中旋 / 停顿标记
}

#: 相对上一个角度的字符（5/6/7/8 = 正负 72°、360/7°）
RELATIVE_ANGLES: dict[str, float] = {
    "5": 72,
    "6": -72,
    "7": 360 / 7,
    "8": -360 / 7,
}


class Parser:
    """读取并规范化一个 ``.adofai`` 文件。"""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as file:
            self.content: str = file.read()

        self.data: dict = self.parse(self.content)
        if "pathData" in self.data and "angleData" not in self.data:
            self.convert_path_data_to_angle_data()

    def __call__(self) -> dict:
        return self.data

    # ------------------------------------------------------------------ 解析
    def parse(self, data: str) -> dict:
        return self.repair_json(data)

    def repair_json(self, text: str) -> dict:
        """尽最大努力把谱面 JSON 修成能 ``json.loads`` 的样子。"""
        json_text = "".join(ch for ch in text if ch.isprintable() or ch in "\r\n\t")
        if json_text.startswith("\ufeff"):
            json_text = json_text[1:]

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

        repaired = json_text
        # 1) 去掉 } / ] 前多余的逗号
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        # 2) 按栈顺序补全未闭合的括号（必须按嵌套顺序，不能先补齐 } 再补 ]）
        stack: list[str] = []
        for char in repaired:
            if char == "{":
                stack.append("}")
            elif char == "[":
                stack.append("]")
            elif char in "}]" and stack and stack[-1] == char:
                stack.pop()
        repaired += "".join(reversed(stack))

        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        # 4) 最后的粗暴修复：去掉所有空白与连续逗号
        try:
            return json.loads(
                json_text.replace("\n", "")
                .replace(" ", "")
                .replace("\t", "")
                .replace(",,", ",")
                .replace(",]", "]")
                .replace(",}", "}")
                .replace(']"', '],"')
            )
        except json.JSONDecodeError as exc:
            logger.error(f"修复JSON失败: {exc}")
            return {}

    # ------------------------------------------------------- pathData -> angle
    def convert_path_data_to_angle_data(self) -> None:
        """把 ``pathData`` 换算成 ``angleData``（原地写入 ``self.data``）。"""
        angle_data: list[float] = []
        for char in self.data.get("pathData", ""):
            if char in DIRECTION_ANGLES:
                angle_data.append(DIRECTION_ANGLES[char])
            elif char in RELATIVE_ANGLES:
                if not angle_data:
                    logger.error(f"相对角度字符 {char!r} 出现在谱面开头，忽略")
                    continue
                angle_data.append(angle_data[-1] + RELATIVE_ANGLES[char])
            else:
                logger.error(f"未知操作符: {char}")
                raise ValueError(f"未知操作符: {char}")
        self.data["angleData"] = angle_data
