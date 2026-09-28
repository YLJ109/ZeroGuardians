"""集中配置系统 (GDD §12 / §9)。

所有可调常量都从这里读取，关卡 / 数值 / 工程共用同一份来源。
Config.load() 会先载入内建 DEFAULTS，再用 config/settings.json 覆盖（若存在）。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# 内建默认值 —— 全部能从 GDD §9 / §12 复算出来
# ---------------------------------------------------------------------------
DEFAULTS: dict[str, Any] = {
    # --- 显示 / 逻辑分辨率 (§2.2) ---
    "LOGIC_W": 1600,
    "LOGIC_H": 900,
    "BLOCK_SIZE": 50,
    "GRID_COLS": 32,
    "GRID_ROWS": 18,
    "FPS": 60,
    "FULLSCREEN": False,

    # --- 固定步长 (§9.1) ---
    "FIXED_DT": 1 / 60,

    # --- 物理 (§9.2, v0.2 修订) ---
    "GRAVITY": 1800,            # px/s^2  (=0.5 px/帧^2)
    "JUMP_VELOCITY": -684,      # px/s   (= sqrt(2*1800*130))
    "MAX_FALL": 1200,           # px/s   (< TILE 50, 防穿透)
    "MOVE_SPEED": 260,          # px/s
    "JUMP_CUT": 0.45,           # 松键 vy *= 0.45
    "COYOTE_TIME": 0.10,        # s
    "JUMP_BUFFER": 0.12,        # s

    # --- 玩家碰撞盒 (§9.3, v0.2 修订) ---
    "PLAYER_SPRITE": (50, 60),
    "PLAYER_HITBOX": (44, 56),

    # --- 建造 / 平衡约束 (§8.5) ---
    "TEAM_CRATES": 12,          # 团队共享箱子上限
    "BUILD_GAP_MIN_ROWS": 5,    # 垂直缺口 >= 5 格 = 250 px (> 二段跳 205 px)
    "TELEPORT_COOLDOWN": 0.5,   # s

    # --- 输入 (§7) ---
    "DEADZONE": 0.25,           # 手柄轴死区
    "MAX_SLOTS": 4,

    # --- 玩法 / 技能数值 (§8.3 / §9 / §10) ---
    "GAMEPLAY": {
        "bullet_speed": 600, "bullet_size": (60, 15), "bullet_cooldown": 0.35, "bullet_max": 3,
        "double_jump_vy": -520, "long_jump_mult": 1.8, "long_jump_time": 0.4, "long_jump_grav": 0.35,
        "dash_speed": 900, "dash_time": 0.18, "dash_cooldown": 1.2,
        "hover_max_fall": 300, "hover_time": 1.2, "hover_cooldown": 3.0,
        "slam_vy": 1400, "slam_radius": 150, "slam_stun": 1.0, "slam_cooldown": 3.0,
        "shockwave_radius": 160, "shockwave_cooldown": 4.0,
        "monster_speed": 90, "monster_stomp_vy": -400,
        "portal_max_dist": 900, "portal_cooldown": 0.6,
        "respawn_time": 0.8,
        "crate_size": 50,
        # 竖向交通（多层立体关卡）：攀爬速度、攀爬时横向减速、弹簧弹跳初速
        #   弹簧弹高 = v²/2g = 1150²/(2*1800) ≈ 367px ≈ 7.3 格 → 可从地面够到 row 10 的高台
        "climb_speed": 155, "climb_speed_mult": 0.7, "spring_vy": -1150,
    },
    "HERO_UNLOCK": {"archer": 0, "builder": 0, "ninja": 4, "doormage": 7, "warlock": 10, "hammer": 13},

    # --- 音频 (§16) ---
    "AUDIO": True,              # 无音频设备时自动静默降级
    "AUDIO_MASTER": 0.85,

    # --- 启动动画 "信号" 主题配色 (锁定版) ---
    "SPLASH": {
        "font_size": 128,
        "letter_spacing": 30,
        "word_color": (238, 243, 247),
        "glow_color": (63, 208, 214),
        "rule_color": (63, 208, 214),
        "presents_color": (95, 169, 179),
        "bg_center": (6, 18, 26),
        "bg_edge": (4, 7, 11),
        "letter_start": 0.85,
        "letter_stagger": 0.06,
        "letter_dur": 0.8,
        "rule_start": 2.0,
        "rule_dur": 1.0,
        "presents_start": 2.35,
        "presents_dur": 1.0,
        "hold_end": 5.2,
        "fade_out": 1.1,
        "loop_end": 7.2,
    },
}


@dataclass
class Config:
    """运行时配置对象。字段名即 DEFAULTS 的键。"""

    # 显示
    LOGIC_W: int = DEFAULTS["LOGIC_W"]
    LOGIC_H: int = DEFAULTS["LOGIC_H"]
    BLOCK_SIZE: int = DEFAULTS["BLOCK_SIZE"]
    GRID_COLS: int = DEFAULTS["GRID_COLS"]
    GRID_ROWS: int = DEFAULTS["GRID_ROWS"]
    FPS: int = DEFAULTS["FPS"]
    FULLSCREEN: bool = DEFAULTS["FULLSCREEN"]

    FIXED_DT: float = DEFAULTS["FIXED_DT"]

    GRAVITY: float = DEFAULTS["GRAVITY"]
    JUMP_VELOCITY: float = DEFAULTS["JUMP_VELOCITY"]
    MAX_FALL: float = DEFAULTS["MAX_FALL"]
    MOVE_SPEED: float = DEFAULTS["MOVE_SPEED"]
    JUMP_CUT: float = DEFAULTS["JUMP_CUT"]
    COYOTE_TIME: float = DEFAULTS["COYOTE_TIME"]
    JUMP_BUFFER: float = DEFAULTS["JUMP_BUFFER"]

    PLAYER_SPRITE: tuple = field(default_factory=lambda: tuple(DEFAULTS["PLAYER_SPRITE"]))
    PLAYER_HITBOX: tuple = field(default_factory=lambda: tuple(DEFAULTS["PLAYER_HITBOX"]))

    TEAM_CRATES: int = DEFAULTS["TEAM_CRATES"]
    BUILD_GAP_MIN_ROWS: int = DEFAULTS["BUILD_GAP_MIN_ROWS"]
    TELEPORT_COOLDOWN: float = DEFAULTS["TELEPORT_COOLDOWN"]

    DEADZONE: float = DEFAULTS["DEADZONE"]
    MAX_SLOTS: int = DEFAULTS["MAX_SLOTS"]

    GAMEPLAY: dict = field(default_factory=lambda: dict(DEFAULTS["GAMEPLAY"]))
    HERO_UNLOCK: dict = field(default_factory=lambda: dict(DEFAULTS["HERO_UNLOCK"]))

    AUDIO: bool = DEFAULTS["AUDIO"]
    AUDIO_MASTER: float = DEFAULTS["AUDIO_MASTER"]

    SPLASH: dict = field(default_factory=lambda: dict(DEFAULTS["SPLASH"]))

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        """载入配置：DEFAULTS 打底，再用 JSON 覆盖。"""
        data = dict(DEFAULTS)
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                overrides = json.load(f)
            _deep_merge(data, overrides)
        # 仅取 dataclass 声明的字段
        known = {f for f in cls.__dataclass_fields__}
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)

    def to_dict(self) -> dict:
        return asdict(self)


def _deep_merge(base: dict, overrides: dict) -> None:
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
