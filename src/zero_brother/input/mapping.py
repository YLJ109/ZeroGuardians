"""键位映射：默认绑定、序列化、解析、校验 (GDD §7.4 / §7.6)。

source（来源）统一用字符串表示，落盘到 config/input.json：
  - 键盘：  "K_a" / "K_LEFT" / "K_TAB"  （即 pygame 键名，去掉 pygame. 前缀）
  - 手柄按钮："btn:0"  ("btn:<index>")
  - 手柄轴：  "axis:0"  ("axis:<index>" 取绝对值方向，左右/上下)
              "axis:0:neg" / "axis:0:pos"  (指定方向)
  - 手柄帽：  "hat:0:x" / "hat:0:y"  (x/y 轴，neg/pos 取符号)
  - 手柄扳机："trig:4" / "trig:5" (LT/RT，> DEADZONE 视为按下)

校验规则（§7.6）：
  ① 同 Slot 内同 Action 不重复绑定（自动去重）
  ② 不同 Slot 允许相同键（同屏共用）—— 不检查
  ③ MOVE_LEFT/RIGHT/JUMP 必填，缺则回填默认
  ④ 手柄按 guid 回退，未匹配 guid 按 Slot 序号回退
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import pygame

from .actions import Action, REQUIRED_ACTIONS, DEFAULT_FALLBACK_KEY


# ---------------------------------------------------------------------------
# 默认 4 人键位（§7.4）
# ---------------------------------------------------------------------------
DEFAULT_SLOTS: list[dict] = [
    # P1 —— 左手字母区
    {"device": "keyboard", "bindings": {
        "MOVE_LEFT": ["K_a"], "MOVE_RIGHT": ["K_d"], "JUMP": ["K_w"],
        "CROUCH": ["K_s"], "SKILL_A": ["K_j"], "SKILL_B": ["K_k"],
        "SWAP": ["K_TAB"], "PAUSE": ["K_ESCAPE"]}},
    # P2 —— 方向键区
    {"device": "keyboard", "bindings": {
        "MOVE_LEFT": ["K_LEFT"], "MOVE_RIGHT": ["K_RIGHT"], "JUMP": ["K_UP"],
        "CROUCH": ["K_DOWN"], "SKILL_A": ["K_1"], "SKILL_B": ["K_2"]}},
    # P3 —— 右侧字母区（注意与 P1 的 J/K 重叠，按广播处理，§7.6 ②）
    {"device": "keyboard", "bindings": {
        "MOVE_LEFT": ["K_j"], "MOVE_RIGHT": ["K_l"], "JUMP": ["K_i"],
        "CROUCH": ["K_k"], "SKILL_A": ["K_u"], "SKILL_B": ["K_o"]}},
    # P4 —— 小键盘区
    {"device": "keyboard", "bindings": {
        "MOVE_LEFT": ["K_KP4"], "MOVE_RIGHT": ["K_KP6"], "JUMP": ["K_KP8"],
        "CROUCH": ["K_KP5"], "SKILL_A": ["K_KP7"], "SKILL_B": ["K_KP9"]}},
]


# ---------------------------------------------------------------------------
# source 字符串 <-> 元组
# ---------------------------------------------------------------------------
def parse_source(s: str) -> tuple:
    if s.startswith("btn:"):
        return ("btn", int(s.split(":")[1]))
    if s.startswith("axis:"):
        parts = s.split(":")
        idx = int(parts[1])
        if len(parts) == 3:
            sign = -1 if parts[2] == "neg" else 1
            return ("axis", idx, sign)
        return ("axis", idx, 0)
    if s.startswith("hat:"):
        parts = s.split(":")
        axis = parts[2]  # 'x' / 'y'
        sign = -1 if parts[3] == "neg" else 1
        return ("hat", int(parts[1]), axis, sign)
    if s.startswith("trig:"):
        return ("trig", int(s.split(":")[1]))
    # 键盘 "K_a" -> ("key", pygame.K_a)
    return ("key", getattr(pygame, s))


def format_source(src: tuple) -> str:
    kind = src[0]
    if kind == "key":
        # 反向查 pygame 常量名
        name = _key_name(src[1])
        return name
    if kind == "btn":
        return f"btn:{src[1]}"
    if kind == "axis":
        if len(src) == 3 and src[2] != 0:
            return f"axis:{src[1]}:{'neg' if src[2] < 0 else 'pos'}"
        return f"axis:{src[1]}"
    if kind == "hat":
        return f"hat:{src[1]}:{src[2]}:{'neg' if src[3] < 0 else 'pos'}"
    if kind == "trig":
        return f"trig:{src[1]}"
    raise ValueError(f"unknown source: {src}")


def _key_name(code: int) -> str:
    for name in dir(pygame):
        if name.startswith("K_") and getattr(pygame, name) == code:
            return name
    return f"K_UNKNOWN({code})"


# ---------------------------------------------------------------------------
# 校验与加载
# ---------------------------------------------------------------------------
def _normalize_slot(slot: dict) -> dict:
    bindings = {}
    for act in Action:
        keys = slot.get("bindings", {}).get(act.value, [])
        # ① 去重
        seen, uniq = set(), []
        for k in keys:
            if k not in seen:
                seen.add(k)
                uniq.append(k)
        if uniq:
            bindings[act.value] = uniq
    # ③ 必填回填
    for act in REQUIRED_ACTIONS:
        if act.value not in bindings:
            bindings[act.value] = [DEFAULT_FALLBACK_KEY[act]]
    out = {"device": slot.get("device", "keyboard")}
    if "guid" in slot:
        out["guid"] = slot["guid"]
    out["bindings"] = bindings
    return out


def load_input_config(path: str | None = None) -> dict:
    """载入 input.json；不存在或无效则回退到 4 人默认键位。"""
    slots = [dict(s) for s in DEFAULT_SLOTS]
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get("slots", [])
            if isinstance(raw, list) and raw:
                slots = raw
        except (json.JSONDecodeError, OSError):
            pass  # 回退默认
    normalized = [_normalize_slot(s) for s in slots]
    return {"slots": normalized}


def save_input_config(path: str, data: dict) -> None:
    """落盘（把 source 元组转回字符串）。

    会自动创建父目录：全新 clone / 解压出来的工程里 `config/` 可能并不存在
    （git 不跟踪空目录），此时首跑写默认键位不能失败。
    """
    out = {"slots": []}
    for slot in data["slots"]:
        bindings = {}
        for act, srcs in slot["bindings"].items():
            bindings[act] = [format_source(s) if isinstance(s, tuple) else s for s in srcs]
        entry = {"device": slot.get("device", "keyboard")}
        if "guid" in slot:
            entry["guid"] = slot["guid"]
        entry["bindings"] = bindings
        out["slots"].append(entry)
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
