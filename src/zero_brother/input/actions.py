"""语义动作定义 (GDD §7.2)。

输入层只产出 Action，游戏逻辑永不直接读键码。这是键位可配置、手柄支持、
回放系统三者共用同一条链路的前提。
"""
from __future__ import annotations

from enum import Enum


class Action(Enum):
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    JUMP = "JUMP"
    CROUCH = "CROUCH"
    SKILL_A = "SKILL_A"
    SKILL_B = "SKILL_B"
    SWAP = "SWAP"
    PAUSE = "PAUSE"


# 必须由每个 Slot 绑定的必填动作（§7.6 ③）
REQUIRED_ACTIONS = (Action.MOVE_LEFT, Action.MOVE_RIGHT, Action.JUMP)

# 全部动作（用于校验/遍历）
ALL_ACTIONS = tuple(Action)

# 默认设备无关动作（缺失时回填，§7.6 ③）
DEFAULT_FALLBACK_KEY = {
    Action.MOVE_LEFT: "K_a",
    Action.MOVE_RIGHT: "K_d",
    Action.JUMP: "K_w",
    Action.CROUCH: "K_s",
}
