"""精灵资源层 —— Kenney "New Platformer" (CC0) 真实素材接线。

素材根：assets/vendor/kenney_new_platformer/Sprites/
  - Characters/Default/character_{beige|green|pink|purple|yellow}_{state}.png  (128²)
       state: idle / walk_a / walk_b / jump / duck / hit / front / climb_a / climb_b
  - Enemies/Default/{snail,slime_normal,ladybug,bee,frog,worm_normal,mouse,saw,...}.png  (64²)
  - Tiles/Default/{terrain_<theme>_block_* 自动拼接, spikes, gem_*, coin_gold,
       door_closed(_top), spring, ladder_*, flag_*, block_plank ...}  (64²)
  - Backgrounds/Default/background_{solid_*, fade_*, clouds}.png  (256²)

设计要点：
  - 全部结果按 (rel, w, h, flip, tint, keep_aspect) 缓存，帧内零重建。
  - 6 英雄映射 5 色角色（hammer 用暖珊瑚微调色区分），头顶悬浮「亲和宝石」标识。
  - 地形 16 掩码自动拼接（N/E/S/W 邻接），主题：grass/sand/stone/purple/snow。
"""
from __future__ import annotations

import numpy as np
import pygame

_BASE = "vendor/kenney_new_platformer/Sprites"
_CH = f"{_BASE}/Characters/Default"
_EN = f"{_BASE}/Enemies/Default"
_TL = f"{_BASE}/Tiles/Default"
_BG = f"{_BASE}/Backgrounds/Default"

# 英雄 -> 角色配色 + 亲和宝石（6 英雄用 5 色，hammer 用微调色区分）
HERO_LOOK = {
    "archer":   {"color": "green",  "gem": "gem_green",  "tint": None},
    "builder":  {"color": "yellow", "gem": "gem_yellow", "tint": None},
    "ninja":    {"color": "purple", "gem": "gem_red",    "tint": None},
    "doormage": {"color": "beige",  "gem": "gem_blue",   "tint": None},
    "warlock":  {"color": "pink",   "gem": "gem_blue",   "tint": None},
    "hammer":   {"color": "beige",  "gem": "gem_yellow", "tint": (255, 156, 120)},  # 暖珊瑚色
}
HERO_COLOR = {
    "archer": (90, 200, 120), "builder": (230, 180, 70), "ninja": (150, 150, 190),
    "doormage": (200, 180, 150), "warlock": (220, 120, 200), "hammer": (230, 120, 90),
}
_CHAR_STATE = {"idle": "idle", "front": "front", "jump": "jump", "duck": "duck", "hit": "hit"}
_WALK = ["walk_a", "walk_b"]
_CLIMB = ["climb_a", "climb_b"]

# 主题 -> 地形块前缀（Kenney terrain_{prefix}_block_*）
THEME_TERRAIN = {
    "grass": "grass", "sand": "sand", "stone": "stone",
    "purple": "purple", "snow": "snow",
}
# 主题 -> 背景配方
#   layer      : 剪影贴图名（Kenney color_*，纯白=镂空，见 _knock_white）
#   sky        : (天顶色, 地平线色) 程序化天空渐变
#   desat/tint/tintamt/wash : 去饱和 / 染色 / 泛白（雪），把绿色系改造成岩石/雪原
#   solid_frac : 贴图内「完全实心」处的纵向比例（Kenney 恒为 0.559）
# 远景层复用同一张贴图 + 大气透视（向天空色去饱和），得到经典的两层视差。
THEME_SCENE = {
    "grass": {
        "layer": "background_color_trees",
        "sky": ((96, 170, 246), (198, 231, 255)),
        "desat": 0.0, "tint": None, "tintamt": 0.0, "wash": 0, "solid_frac": 0.559,
    },
    "sand": {
        "layer": "background_color_desert",
        "sky": ((246, 200, 132), (255, 236, 196)),
        "desat": 0.0, "tint": None, "tintamt": 0.0, "wash": 0, "solid_frac": 0.559,
    },
    "stone": {
        "layer": "background_color_hills",
        "sky": ((104, 124, 158), (186, 200, 220)),
        "desat": 0.82, "tint": (150, 166, 194), "tintamt": 0.55, "wash": 0, "solid_frac": 0.559,
    },
    "purple": {
        "layer": "background_color_mushrooms",
        "sky": ((126, 104, 190), (212, 196, 240)),
        "desat": 0.0, "tint": None, "tintamt": 0.0, "wash": 0, "solid_frac": 0.559,
    },
    "snow": {
        "layer": "background_color_trees",
        "sky": ((138, 178, 230), (228, 240, 252)),
        "desat": 0.72, "tint": (226, 238, 252), "tintamt": 0.66, "wash": 26, "solid_frac": 0.559,
    },
}

# 主题 -> 墙体（砖石）贴图：墙体是**静态瓦片**（不参与重力），
# 用来做障碍/掩体/高台支柱；与地形自动拼接块刻意区分，读起来像"人造物"。
WALL_ART = {
    "grass": "bricks_brown", "sand": "bricks_brown", "purple": "bricks_brown",
    "stone": "bricks_grey", "snow": "bricks_grey",
}

# 装饰（纯视觉、无碰撞）：key -> (Kenney 贴图名, 锚点)
#   anchor: "bottom" 底边贴格底 / "top" 顶边贴格顶 / "center" 居中
# 说明：Kenney 的对象贴图常只占 64² 画布的一角，锚定合成后再 blit，
#       就能稳定地"站在格子底边上"，不必逐个手写偏移。
DECO_ART = {
    "tuft":     ("grass", "bottom"),
    "bush":     ("bush", "bottom"),
    "rock":     ("rock", "bottom"),
    "cactus":   ("cactus", "bottom"),
    "mushroom": ("mushroom_red", "bottom"),
    "mushroom2": ("mushroom_brown", "bottom"),
    "snowcap":  ("snow", "bottom"),
    "sign":     ("sign", "bottom"),
    "torch":    ("torch_on_a", "bottom"),
    "fence":    ("fence", "bottom"),
    "chain":    ("chain", "top"),
    "star":     ("star", "center"),
}

# 敌人种类 -> (帧文件名列表, 是否飞行)
ENEMY_KINDS = {
    "snail":   (["snail_walk_a", "snail_walk_b"], False),
    "slime":   (["slime_normal_walk_a", "slime_normal_walk_b"], False),
    "ladybug": (["ladybug_walk_a", "ladybug_walk_b"], False),
    "worm":    (["worm_normal_move_a", "worm_normal_move_b"], False),
    "mouse":   (["mouse_walk_a", "mouse_walk_b"], False),
    "frog":    (["frog_idle", "frog_jump"], False),
    "bee":     (["bee_a", "bee_b"], True),
    "fly":     (["fly_a", "fly_b"], True),
    "saw":     (["saw_a", "saw_b"], False),
}


class Sprites:
    def __init__(self, res, cfg):
        self.res = res
        self.cfg = cfg
        self._cache: dict = {}

    # ------------------------------------------------------------------
    # 基础：加载 + 缩放/翻转/调色 + 缓存
    # ------------------------------------------------------------------
    def _load(self, rel, w, h, flip=False, tint=None, keep_aspect=True, smooth=True):
        """载入并按目标尺寸缩放。

        ``smooth=False`` 用最近邻：Kenney 的 HUD 像素图标/数字本身是 64² 的粗像素画，
        缩到 HUD 的 24~34px 时若用平滑缩放，笔画会被插值糊成"空心轮廓"——
        数字 1 看起来不像 1、4 糊成一团。像素画在小尺寸下必须用最近邻才清晰。
        地形/角色等由瓦片尺寸决定的大图仍走平滑缩放（非整数倍降采样更不容易出锯齿）。
        """
        key = (rel, w, h, flip, tint, keep_aspect, smooth)
        if key in self._cache:
            return self._cache[key]
        src = self.res.image(rel)
        out = None
        if src is not None:
            scale = pygame.transform.smoothscale if smooth else pygame.transform.scale
            if keep_aspect:
                sw, sh = src.get_size()
                s = min(w / sw, h / sh)
                nw, nh = max(1, int(sw * s)), max(1, int(sh * s))
                out = scale(src, (nw, nh))
            else:
                out = scale(src, (w, h))
            if tint is not None:
                t = out.copy()
                t.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
                out = t
            if flip:
                out = pygame.transform.flip(out, True, False)
        self._cache[key] = out
        return out

    # ------------------------------------------------------------------
    # 对象贴图重排：Kenney 的「道具/对象」常只画在 64² 画布的一角，
    # 这里统一按不透明包围盒重排到单元格内（底边居中 / 顶边 / 居中），
    # 这样无论原图怎么摆，落到格子上都对齐得漂亮，也不用逐个手写偏移。
    # ------------------------------------------------------------------
    def _anchored(self, rel, size, anchor="bottom", inset=2):
        key = ("anch", rel, size, anchor, inset)
        if key in self._cache:
            return self._cache[key]
        raw = self.res.image(rel)
        out = None
        if raw is not None:
            src = pygame.transform.smoothscale(raw, (size, size))
            bb = _alpha_bbox(src)
            out = pygame.Surface((size, size), pygame.SRCALPHA)
            if bb is None:
                out.blit(src, (0, 0))
            else:
                x0, y0, x1, y1 = bb
                dx = (size - (x1 - x0 + 1)) // 2 - x0
                if anchor == "bottom":
                    dy = (size - inset) - (y1 + 1)
                elif anchor == "top":
                    dy = inset - y0
                else:
                    dy = (size - (y1 - y0 + 1)) // 2 - y0
                out.blit(src, (dx, dy))
        self._cache[key] = out
        return out

    # ------------------------------------------------------------------
    # 角色
    # ------------------------------------------------------------------
    def char(self, hero_id: str, state: str, facing: int, height: int = 64):
        look = HERO_LOOK.get(hero_id, HERO_LOOK["archer"])
        suffix = _CHAR_STATE.get(state, "idle")
        rel = f"{_CH}/character_{look['color']}_{suffix}.png"
        return self._load(rel, height, height, flip=(facing < 0), tint=look["tint"])

    def char_walk(self, hero_id: str, frame: int, facing: int, height: int = 64):
        look = HERO_LOOK.get(hero_id, HERO_LOOK["archer"])
        rel = f"{_CH}/character_{look['color']}_{_WALK[frame % len(_WALK)]}.png"
        return self._load(rel, height, height, flip=(facing < 0), tint=look["tint"])

    def char_climb(self, hero_id: str, frame: int, facing: int, height: int = 64):
        look = HERO_LOOK.get(hero_id, HERO_LOOK["archer"])
        rel = f"{_CH}/character_{look['color']}_{_CLIMB[frame % len(_CLIMB)]}.png"
        return self._load(rel, height, height, flip=(facing < 0), tint=look["tint"])

    def hero_gem(self, hero_id: str, size: int = 14):
        look = HERO_LOOK.get(hero_id, HERO_LOOK["archer"])
        return self._load(f"{_TL}/{look['gem']}.png", size, size)

    def portrait(self, hero_id: str, size: int = 44):
        look = HERO_LOOK.get(hero_id, HERO_LOOK["archer"])
        return self._load(f"{_TL}/hud_player_{look['color']}.png", size, size)

    # ------------------------------------------------------------------
    # 敌人
    # ------------------------------------------------------------------
    def enemy(self, kind: str, frame: int, w: int, h: int):
        frames, _fly = ENEMY_KINDS.get(kind, ENEMY_KINDS["snail"])
        return self._load(f"{_EN}/{frames[frame % len(frames)]}.png", w, h)

    # ------------------------------------------------------------------
    # 地形自动拼接（16 掩码）
    # ------------------------------------------------------------------
    def tile(self, theme: str, mask: int, size: int):
        prefix = THEME_TERRAIN.get(theme, "grass")
        part = _autotile_part(mask)
        if part in ("vertical_middle", "horizontal_middle"):
            name = f"terrain_{prefix}_{part}"          # 这两个变体没有 _block_
        else:
            name = f"terrain_{prefix}_block" + (f"_{part}" if part else "")
        return self._load(f"{_TL}/{name}.png", size, size)

    # ------------------------------------------------------------------
    # 道具 / 元素
    # ------------------------------------------------------------------
    def gem(self, color: str, size: int):
        name = {"green": "gem_green", "yellow": "gem_yellow",
                "red": "gem_red", "blue": "gem_blue"}.get(color, "gem_green")
        return self._load(f"{_TL}/{name}.png", size, size, smooth=False)

    def coin(self, size: int):
        return self._load(f"{_TL}/coin_gold.png", size, size, smooth=False)

    def spike(self, size: int):
        return self._load(f"{_TL}/spikes.png", size, size, smooth=False)

    def crate(self, size: int):
        return self._load(f"{_TL}/block_plank.png", size, size, smooth=False)

    def wall(self, theme: str, size: int):
        """墙体/棱柱：静态实心块（无重力），与地形块刻意区分。"""
        name = WALL_ART.get(theme, "bricks_brown")
        return self._load(f"{_TL}/{name}.png", size, size)

    def ladder(self, size: int, part: str = "middle"):
        """梯子分段（top/middle/bottom），按不透明包围盒重排到格内。"""
        part = part if part in ("top", "middle", "bottom") else "middle"
        return self._anchored(f"{_TL}/ladder_{part}.png", size, "center")

    def spring(self, size: int, extended: bool = False):
        name = "spring_out" if extended else "spring"
        return self._anchored(f"{_TL}/{name}.png", size, "bottom")

    def bridge(self, size: int):
        """单向平台：从上方可站、可从下方跳穿；圆木画在格子顶部，与站立线对齐。"""
        return self._anchored(f"{_TL}/bridge_logs.png", size, "top")

    def deco(self, name: str, size: int):
        """纯装饰（无碰撞）：按 DECO_ART 的锚点重排到格内。"""
        art = DECO_ART.get(name)
        if art is None:
            return None
        rel, anchor = art
        return self._anchored(f"{_TL}/{rel}.png", size, anchor)

    def deco_names(self):
        return tuple(DECO_ART)

    def door(self, top: bool, open_: bool, size: int):
        name = ("door_open" if open_ else "door_closed") + ("_top" if top else "")
        return self._load(f"{_TL}/{name}.png", size, size)

    def flag(self, color: str, frame: int, size: int):
        return self._load(f"{_TL}/flag_{color}_{'a' if frame % 2 == 0 else 'b'}.png", size, size)

    def projectile(self, size: int):
        return self._load(f"{_TL}/fireball.png", size, size)

    def portal(self, is_blue: bool, size: int):
        name = "switch_blue" if is_blue else "switch_yellow"
        return self._load(f"{_TL}/{name}.png", size, size)

    # ------------------------------------------------------------------
    # 背景 / 图块
    # ------------------------------------------------------------------
    def bg_tile(self, name: str, size: int):
        return self._load(f"{_BG}/{name}.png", size, size, keep_aspect=False)

    def theme_scene(self, theme: str):
        """返回该主题的背景配方 dict（layer/sky/desat/tint/solid_frac…）。"""
        return THEME_SCENE.get(theme, THEME_SCENE["grass"])

    # ------------------------------------------------------------------
    # 背景剪影层（Kenney color_* 用纯白作镂空色）
    # ------------------------------------------------------------------
    @staticmethod
    def _knock_white(img, thr: int = 246):
        """把近白像素变透明，返回 RGBA 副本。纯白=镂空，是 Kenney 背景的约定。"""
        rgb = pygame.surfarray.array3d(img).astype(np.int16)
        mask = (rgb[:, :, 0] >= thr) & (rgb[:, :, 1] >= thr) & (rgb[:, :, 2] >= thr)
        out = img.convert_alpha()
        a = pygame.surfarray.pixels_alpha(out)
        a[:] = np.where(mask, 0, 255).astype(np.uint8)
        del a
        return out

    @staticmethod
    def _stylize(img, desat: float = 0.0, tint=None, tintamt: float = 0.0, wash: int = 0):
        """去饱和 + 染色 + 泛白，用于把绿色系的 Kenney 背景改造成岩石/雪原。"""
        if desat <= 0 and tintamt <= 0 and not wash:
            return img
        out = img.convert_alpha()
        arr = pygame.surfarray.pixels3d(out).astype(np.float32)
        if desat > 0:
            lum = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2])
            gray = np.repeat(lum[:, :, None], 3, axis=2)
            arr = arr * (1.0 - desat) + gray * desat
        if tint is not None and tintamt > 0:
            tc = np.array(tint, dtype=np.float32)[None, None, :]
            arr = arr * (1.0 - tintamt) + tc * tintamt
        if wash:
            arr = arr + float(wash)
        arr = np.clip(arr, 0, 255)
        pygame.surfarray.pixels3d(out)[:] = arr.astype(np.uint8)
        return out

    def scene_layer(self, name: str, size: int, desat: float = 0.0, tint=None,
                    tintamt: float = 0.0, wash: int = 0):
        """生成一层可平铺的背景剪影（纯白镂空 + 主题化调色），带缓存。"""
        key = ("layer", name, size, round(desat, 3), tint, round(tintamt, 3), wash)
        if key in self._cache:
            return self._cache[key]
        raw = self.res.image(f"{_BG}/{name}.png")
        out = None
        if raw is not None:
            scaled = pygame.transform.smoothscale(raw, (size, size))
            out = self._knock_white(scaled)
            out = self._stylize(out, desat, tint, tintamt, wash)
        self._cache[key] = out
        return out

    # ------------------------------------------------------------------
    # HUD 图标 / 像素数字
    # ------------------------------------------------------------------
    def hud(self, name: str, size: int):
        return self._load(f"{_TL}/{name}.png", size, size)

    def digit(self, d: int, size: int = 22):
        # 像素数字必须最近邻缩放，否则 24px 下"1"糊成竖条、"4"糊成一团（实测）。
        return self._load(f"{_TL}/hud_character_{d}.png", size, size, smooth=False)

    def number(self, value: int, size: int = 22, spacing: int = 2):
        key = ("num", value, size, spacing)
        if key in self._cache:
            return self._cache[key]
        chars = [self.digit(int(c), size) for c in str(abs(value))]
        chars = [c for c in chars if c is not None]
        w = sum(c.get_width() for c in chars) + spacing * max(0, len(chars) - 1)
        h = max((c.get_height() for c in chars), default=size)
        surf = pygame.Surface((max(1, w), h), pygame.SRCALPHA)
        x = 0
        for c in chars:
            surf.blit(c, (x, h - c.get_height()))
            x += c.get_width() + spacing
        self._cache[key] = surf
        return surf


def _alpha_bbox(img, thr: int = 8):
    """不透明像素的包围盒 (x0, y0, x1, y1)；全透明返回 None。

    pygame.surfarray.pixels_alpha 返回 [x][y] 的二维数组，故 argwhere 的列即 (x, y)。
    """
    try:
        a = pygame.surfarray.pixels_alpha(img)
    except Exception:
        return None
    pts = np.argwhere(a > thr)
    del a
    if len(pts) == 0:
        return None
    lo = pts.min(axis=0)
    hi = pts.max(axis=0)
    return int(lo[0]), int(lo[1]), int(hi[0]), int(hi[1])


def _autotile_part(mask: int) -> str:
    """把 N/E/S/W 邻接掩码映射到 Kenney 的 block 部件名。"""
    if mask == 15:
        return "center"
    if mask == 0:
        return ""
    n, e, s, w = mask & 1, mask & 2, mask & 4, mask & 8
    if not n and not s:
        return "vertical_middle"
    if not e and not w:
        return "horizontal_middle"
    if not n and not w:
        return "top_left"
    if not n and not e:
        return "top_right"
    if not s and not w:
        return "bottom_left"
    if not s and not e:
        return "bottom_right"
    if not n:
        return "top"
    if not s:
        return "bottom"
    if not w:
        return "left"
    if not e:
        return "right"
    return "center"
