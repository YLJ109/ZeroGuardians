"""角色选择场景（1-4 人）—— 两阶段向导 + 统一主题 UI。

阶段 1 heroes：选择人数(1-4) + 每位活跃玩家用**自己的键位/手柄**循环切换英雄并「准备」。
  交互双轨：键盘（1/2/3/4 选人数、← → 换英雄、跳键准备、Enter 一键全就绪）
  + 鼠标（点人数胶囊、点英雄卡加入/取消准备），保证"没有小键盘 / 不记得键位"
  也能把 3 人、4 人流程走完。
阶段 2 level ：选择 1-15 关（L5/L10/L15 为 Boss），确认后进入 GameplayScene。
展示使用 Kenney 真实角色素材（行走动画）+ 亲和宝石 + 技能汉化名。
"""
from __future__ import annotations

import math
import os

import pygame

from ..core.scene import Scene, blit_letterbox
from ..heroes.registry import HERO_ORDER, hero as hero_def, SKILL_NAMES
from ..world.sprites import Sprites, HERO_COLOR
from ..world.level import level_facts
from ..input.actions import Action
from ..levels.generate import levels_dir
from ..ui import theme as T

BOSS_LEVELS = {5, 10, 15}
LEVEL_COUNT = 15

# 英雄能力雷达（5 分制）—— 用于卡片上的能力条，帮助玩家快速理解定位
HERO_STATS = {
    "archer":   {"机动": 3, "技巧": 2, "支援": 3},
    "builder":  {"机动": 2, "技巧": 3, "支援": 5},
    "ninja":    {"机动": 5, "技巧": 4, "支援": 1},
    "doormage": {"机动": 4, "技巧": 3, "支援": 4},
    "warlock":  {"机动": 3, "技巧": 4, "支援": 3},
    "hammer":   {"机动": 2, "技巧": 4, "支援": 3},
}
HERO_ROLE = {
    "archer": "远程输出", "builder": "建造解谜", "ninja": "高速机动",
    "doormage": "空间支援", "warlock": "控场法术", "hammer": "重击破坏",
}
THEME_CN = {"grass": "草原", "sand": "沙漠", "snow": "雪原", "stone": "岩地", "purple": "菌林"}
# 小地图取值 -> 颜色（覆盖所有碰撞字符，含新增的立体机制）
_MINIMAP = {
    "#": (104, 118, 146), "W": (170, 138, 106),
    "1": (104, 224, 154), "2": (245, 200, 90),
    "3": (150, 150, 190), "4": (120, 170, 255),
    "M": (232, 92, 96), "F": (196, 120, 220), "C": (196, 142, 82),
    "g": (104, 224, 154), "y": (245, 200, 90), "$": (255, 214, 102),
    "^": (226, 84, 92), "D": (63, 208, 214),
    "L": (216, 178, 116), "S": (255, 140, 180), "=": (150, 200, 230),
    "a": (120, 170, 255), "b": (245, 200, 90),
}

# pygame 键名 -> 卡面上显示的短名（只列容易读错的；其余走 K_xxx -> XXX 兜底）
_KEY_ALIAS = {
    "K_UP": "↑", "K_DOWN": "↓", "K_LEFT": "←", "K_RIGHT": "→",
    "K_RETURN": "Enter", "K_SPACE": "空格", "K_LSHIFT": "Shift",
    "K_COMMA": ",", "K_PERIOD": ".", "K_SLASH": "/", "K_SEMICOLON": ";",
    "K_QUOTE": "'", "K_LEFTBRACKET": "[", "K_RIGHTBRACKET": "]",
}

# 选人界面几何常量：渲染与命中测试共用同一份，避免两处各写一遍导致点击偏移
PILL_STEP, PILL_W, PILL_H, PILL_Y = 112, 92, 34, 150
PILL_LEFT = -168
CARD_W, CARD_H, CARD_GAP, CARD_Y = 322, 520, 26, 196
CARD_PAD = 20                       # 卡内左右留白（文案不得越过它）
GEM_ICON, GEM_ICON_PAD, GEM_ROW_GAP = 22, 8, 22
GEM_CN = {"green": "绿宝石", "yellow": "黄宝石", "any": "任意宝石"}


def gem_row_text(hero_gem: str) -> tuple[str, str]:
    """英雄的亲和宝石 -> (左「亲和 X」, 右「奖励 X」) 两段文案。

    单行拼成「亲和 绿宝石 · 同色 +1 奖励」在 18px 下宽 316px > 卡内可用 282px，
    会顶到卡边（同类"文案超出盒子"事故）；拆成左右两段后最宽 231px。
    """
    return (f"亲和 {GEM_CN.get(hero_gem, hero_gem)}",
            "同色 +1" if hero_gem != "any" else "全色 +1")


def _short_key(src: str) -> str:
    """输入源字符串 -> 卡面上显示的短名（手柄/轴类返回空串，由调用方兜底）。"""
    if src.startswith("K_KP"):
        return f"小键盘{src[4:]}"
    if src in _KEY_ALIAS:
        return _KEY_ALIAS[src]
    if src.startswith("K_"):
        return src[2:].upper()
    return ""



class CharacterSelectScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.count = 2
        self.heroes = ["archer", "builder", "ninja", "doormage"]
        self.ready = [False] * 4
        self.phase = "heroes"  # heroes | level
        self.level_cursor = 0
        self.t = 0.0
        self.hover = None            # ('pill', i) / ('card', i) / None —— 鼠标高亮
        self.logic = pygame.Surface((app.config.LOGIC_W, app.config.LOGIC_H))
        self.sprites = Sprites(app.resources, app.config) if getattr(app, "resources", None) else None
        self._start_timer = 0.0
        self._prev_held: dict = {}
        self.levels: dict = {}
        self._dim = None
        self._load_levels()

    def _load_levels(self) -> None:
        from ..world.level import load_level
        d = levels_dir()
        for i in range(1, LEVEL_COUNT + 1):
            path = os.path.join(d, f"level_{i}.json")
            if os.path.exists(path):
                try:
                    self.levels[i] = load_level(path)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    def _edge(self, slot: int, action) -> bool:
        cur = self.app.input.held(slot, action)
        key = (slot, action)
        prev = self._prev_held.get(key, False)
        self._prev_held[key] = cur
        return cur and not prev

    def fixed_update(self, dt: float) -> None:
        self.t += dt
        audio = getattr(self.app, "audio", None)
        if self.phase == "heroes":
            for slot in range(self.count):
                # 每帧都消费一次边沿（保持 _prev_held 新鲜），再按状态决定是否生效
                left = self._edge(slot, Action.MOVE_LEFT)
                right = self._edge(slot, Action.MOVE_RIGHT)
                fire = self._edge(slot, Action.JUMP) or self._edge(slot, Action.SKILL_A)
                # 「已准备」的槽位锁定英雄。为什么需要：P1 的技能键 J 同时是 P3 的
                # MOVE_LEFT（§7.6 ② 同屏共用键是设计如此），不锁的话 P1 一按 J 就会
                # 把 P3 已经选好的英雄转走、顺带清掉 P3 的准备状态。
                if not self.ready[slot] and (left or right):
                    step = -1 if left else 1
                    idx = HERO_ORDER.index(self.heroes[slot])
                    self.heroes[slot] = HERO_ORDER[(idx + step) % len(HERO_ORDER)]
                    if audio:
                        audio.play("hover")
                if fire:
                    self.ready[slot] = not self.ready[slot]
                    if audio:
                        audio.play("confirm" if self.ready[slot] else "back")
            if all(self.ready[s] for s in range(self.count)):
                self._start_timer += dt
                if self._start_timer > 0.4:
                    self.phase = "level"
                    self._start_timer = 0.0
                    self.hover = None
                    if audio:
                        audio.play("confirm")
            else:
                self._start_timer = 0.0
        else:
            before = self.level_cursor
            if self._edge(0, Action.MOVE_LEFT):
                self.level_cursor = (self.level_cursor - 1) % LEVEL_COUNT
            if self._edge(0, Action.MOVE_RIGHT):
                self.level_cursor = (self.level_cursor + 1) % LEVEL_COUNT
            if self._edge(0, Action.JUMP):
                self.level_cursor = (self.level_cursor - self._GRID_COLS) % LEVEL_COUNT
            if self._edge(0, Action.CROUCH):
                self.level_cursor = (self.level_cursor + self._GRID_COLS) % LEVEL_COUNT
            if self.level_cursor != before and audio:
                audio.play("scroll")
            for slot in range(self.count):
                if self._edge(slot, Action.SKILL_A) or self._edge(slot, Action.SKILL_B):
                    self._start()
                    return

    # ------------------------------------------------------------------
    def handle_event(self, event) -> None:
        audio = getattr(self.app, "audio", None)
        if self.phase == "heroes":
            if event.type == pygame.MOUSEMOTION:
                h = self._hero_hit(event.pos)
                if h != self.hover:
                    self.hover = h
                    if h is not None and audio:
                        audio.play("hover")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._hero_click(event.pos, audio)
            elif event.type == pygame.KEYDOWN:
                self._hero_key(event.key, audio)
            return

        if event.type == pygame.MOUSEMOTION:
            i = self._level_at(event.pos)
            if i is not None and i != self.level_cursor:
                self.level_cursor = i
                if audio:
                    audio.play("hover")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            i = self._level_at(event.pos)
            if i is not None:
                self.level_cursor = i
                self._start()
        elif event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                if audio:
                    audio.play("back")
                self.phase = "heroes"
                self.ready = [False] * 4
                self.hover = None
            elif pygame.K_1 <= k <= pygame.K_9:
                self.level_cursor = k - pygame.K_1
            elif k == pygame.K_0:
                self.level_cursor = 9
            elif k == pygame.K_RETURN:
                self._start()

    # ---- 选人阶段的两套操作入口（键盘 / 鼠标共用同一批状态改动）----
    def _hero_key(self, k: int, audio) -> None:
        if k == pygame.K_ESCAPE:
            if audio:
                audio.play("back")
            from .menu import MenuScene
            self.app.scenes.switch(MenuScene(self.app))
        elif pygame.K_1 <= k <= pygame.K_4:
            self._set_count(k - pygame.K_0, audio)
        elif k == pygame.K_RETURN:
            self.ready = [True] * 4
            if audio:
                audio.play("confirm")

    def _set_count(self, n: int, audio) -> None:
        if n == self.count:
            return
        self.count = n
        self.ready = [False] * 4
        if audio:
            audio.play("toggle")

    def _pill_rect(self, i: int) -> pygame.Rect:
        cfg = self.app.config
        r = pygame.Rect(0, 0, PILL_W, PILL_H)
        r.center = (cfg.LOGIC_W // 2 + PILL_LEFT + i * PILL_STEP, PILL_Y)
        return r

    def _card_rect(self, i: int) -> pygame.Rect:
        cfg = self.app.config
        total = CARD_W * 4 + CARD_GAP * 3
        x0 = (cfg.LOGIC_W - total) // 2
        return pygame.Rect(x0 + i * (CARD_W + CARD_GAP), CARD_Y, CARD_W, CARD_H)

    def _hero_hit(self, pos):
        """鼠标命中：('pill', i) 改人数 / ('card', i) 加入或准备 / None。"""
        for i in range(4):
            if self._pill_rect(i).collidepoint(pos):
                return ("pill", i)
        for i in range(4):
            if self._card_rect(i).collidepoint(pos):
                return ("card", i)
        return None

    def _hero_click(self, pos, audio) -> bool:
        hit = self._hero_hit(pos)
        if hit is None:
            return False
        kind, i = hit
        if kind == "pill":
            self._set_count(i + 1, audio)
            return True
        if i < self.count:
            # 已加入的玩家：点一下切换「准备」
            self.ready[i] = not self.ready[i]
            if audio:
                audio.play("confirm" if self.ready[i] else "back")
        else:
            # 点「未加入」的卡片 = 让该玩家加入，并顺手就绪（少点一次）
            self.count = i + 1
            self.ready = [False] * 4
            self.ready[i] = True
            if audio:
                audio.play("confirm")
        return True

    def _key_label(self, slot: int, action: str = "JUMP") -> str:
        """该槽位的「就绪键」可读短名；有多个绑定时写成「主键 或 后备键」。

        没有小键盘的笔记本按不出 K_KP8 —— 卡片上直接把两个键都写明，
        比让玩家自己猜要友好得多（P4 的 JUMP = 小键盘8 或 /）。
        """
        im = getattr(self.app, "input", None)
        slots = getattr(im, "slots", None) or []
        if slot >= len(slots):
            return "跳"
        srcs = (slots[slot].get("bindings") or {}).get(action) or []
        labels = [lab for lab in (_short_key(s) for s in srcs) if lab]
        if not labels:
            return "跳"
        return " 或 ".join(labels[:2])

    def _start(self) -> None:
        audio = getattr(self.app, "audio", None)
        path = os.path.join(levels_dir(), f"level_{self.level_cursor + 1}.json")
        if not os.path.exists(path):
            if audio:
                audio.play("deny")
            return
        if audio:
            audio.play("confirm")
        from ..world.level import load_level
        from .gameplay import GameplayScene
        level = load_level(path)
        picks = [(s, self.heroes[s]) for s in range(self.count)]
        self.app.scenes.switch(GameplayScene(self.app, level, picks))

    # ------------------------------------------------------------------
    def render(self, alpha: float) -> None:
        cfg = self.app.config
        g = self.logic
        T.parallax_bg(g, self.sprites, "purple", self.t * 30, factor=0.18)
        if self._dim is None:
            ov = pygame.Surface((cfg.LOGIC_W, cfg.LOGIC_H), pygame.SRCALPHA)
            # 只做"够读"的压暗：旧值 198->120 太黑，把卡面上的名字/定位/技能
            # /能力条全吃掉了（玩家反馈"选英雄界面有点暗"）。
            for i in range(cfg.LOGIC_H):
                a = int(132 - 52 * (i / max(1, cfg.LOGIC_H - 1)))
                pygame.draw.line(ov, (8, 12, 24, a), (0, i), (cfg.LOGIC_W, i))
            self._dim = ov
        g.blit(self._dim, (0, 0))
        if self.phase == "heroes":
            self._render_heroes(g, cfg)
        else:
            self._render_levels(g, cfg)
        T.vignette(g, 54)
        blit_letterbox(self.app.screen, g, cfg)

    # ---- 阶段 1：选人 ----
    def _render_heroes(self, g, cfg) -> None:
        T.text(g, self.app.resources, "选择英雄", 56, T.PALETTE["text"], center=(cfg.LOGIC_W // 2, 58), shadow_=True)
        T.text(g, self.app.resources,
                "点击胶囊 或 按 1/2/3/4 选人数 · 各自 ← → 换英雄 · 跳键 / 点击卡片「准备」"
                " · Enter 一键全就绪 · ESC 返回",
                20, T.PALETTE["muted"], center=(cfg.LOGIC_W // 2, 106))
        # 人数胶囊（鼠标可点 → 3 人 / 4 人不再只能靠键盘）
        for i, n in enumerate("1234"):
            hovered = self.hover == ("pill", i)
            T.pill(g, self.app.resources, self._pill_rect(i).center, f"{n} 人",
                   active=(i + 1 == self.count) or hovered, w=PILL_W)

        for i in range(4):
            r = self._card_rect(i)
            self._hero_card(g, cfg, i, r.x, r.y, r.w, r.h)

    def _hero_card(self, g, cfg, slot, x, y, w, h) -> None:
        res = self.app.resources
        active = slot < self.count
        hid = self.heroes[slot] if active else None
        accent = HERO_COLOR.get(hid, T.PALETTE["line"]) if active else T.PALETTE["line"]
        hovered = self.hover == ("card", slot)
        if active and self.ready[slot]:
            border = T.PALETTE["ok"]
        elif hovered:
            border = T.PALETTE["accent"]
        else:
            border = accent if active else T.PALETTE["line"]
        T.glass(g, (x, y, w, h), radius=18, alpha=236 if active else 172, border=border,
                border_w=3 if active else 2)
        # 顶部玩家色带
        if active:
            T.gradient_h(g, (x + 2, y + 2, w - 4, 6), accent, (255, 255, 255))
        T.text(g, res, f"玩家 {slot + 1}  ·  P{slot + 1}", 22,
               T.PALETTE["text"] if active else T.PALETTE["muted"],
               center=(x + w // 2, y + 30))
        if active and self.ready[slot]:
            T.pill(g, res, (x + w // 2, y + 62), "已准备", active=True, w=None)
        elif active:
            # 把"该玩家该按什么键就绪"直接写在状态胶囊上：4 人同屏时每人的键位
            # 都不一样，光写"准备中"等于没说（P4 尤其需要一个明确提示）。
            T.pill(g, res, (x + w // 2, y + 62),
                   f"准备中 · {self._key_label(slot)}", active=False, w=None)

        if not active:
            T.text(g, res, "未加入", 26, T.PALETTE["muted"], center=(x + w // 2, y + h // 2 - 10))
            T.text(g, res, "点击此卡加入", 19, T.PALETTE["accent"], center=(x + w // 2, y + h // 2 + 26))
            T.text(g, res, f"或按 {slot + 1} 键", 17, T.PALETTE["muted"],
                   center=(x + w // 2, y + h // 2 + 52))
            return

        hdef = hero_def(hid)
        role = HERO_ROLE.get(hid, "")
        # 角色立绘（准备时行走动画，否则待机 + 轻微呼吸）
        if self.sprites:
            if self.ready[slot]:
                img = self.sprites.char_walk(hid, int(self.t * 7) % 2, 1, 158)
            else:
                img = self.sprites.char(hid, "idle", 1, 158)
            if img:
                bob = math.sin(self.t * 3 + slot) * 3
                # 脚下光圈（呼应 HERO_COLOR，作为落点阴影/聚光）
                aura = pygame.Surface((148, 34), pygame.SRCALPHA)
                pygame.draw.ellipse(aura, (*accent, 62), aura.get_rect())
                pygame.draw.ellipse(aura, (*accent, 110), aura.get_rect().inflate(-58, -20))
                g.blit(aura, (x + w // 2 - 74, y + 238 + int(bob)))
                g.blit(img, (x + w // 2 - img.get_width() // 2, y + 96 + int(bob)))
        # 名字 + 定位
        T.text(g, res, hdef["name"], 29, tuple(hdef["color"]), center=(x + w // 2, y + 276))
        T.text(g, res, role, 19, T.PALETTE["muted"], center=(x + w // 2, y + 302))
        # 亲和宝石（亲和只影响奖励，任何英雄都能拿任何宝石 —— 否则单人关卡无解）
        # 排版：左「亲和 <颜色>」+ 右「奖励」，避免一整行顶到卡边。
        gem = self.sprites.hero_gem(hid, GEM_ICON) if self.sprites else None
        left_s, right_s = gem_row_text(hdef["gem"])
        f18 = res.font(18)
        left, right = f18.render(left_s, True, T.PALETTE["muted"]), f18.render(right_s, True, accent)
        icw = (gem.get_width() + GEM_ICON_PAD) if gem else 0
        cy = y + 332
        gx = x + w // 2 - (icw + left.get_width() + GEM_ROW_GAP + right.get_width()) // 2
        if gem:
            g.blit(gem, (gx, cy - gem.get_height() // 2))
            gx += icw
        g.blit(left, (gx, cy - left.get_height() // 2))
        g.blit(right, (gx + left.get_width() + GEM_ROW_GAP, cy - right.get_height() // 2))
        # 能力条
        stats = HERO_STATS.get(hid, {})
        sy = y + 356
        for k, v in stats.items():
            T.text(g, res, k, 17, T.PALETTE["muted"], topleft=(x + 24, sy + 2))
            bx = x + 88
            bw, bh = w - 116, 10
            pygame.draw.rect(g, (16, 22, 36), (bx, sy + 4, bw, bh), border_radius=5)
            pygame.draw.rect(g, accent, (bx, sy + 4, int(bw * v / 5), bh), border_radius=5)
            sy += 22
        # 技能
        a = SKILL_NAMES.get(hdef["skill_a"], hdef["skill_a"])
        b = SKILL_NAMES.get(hdef["skill_b"], hdef["skill_b"])
        self._skill_row(g, x + 24, sy + 8, "技能 A", a, accent)
        self._skill_row(g, x + 24, sy + 38, "技能 B", b, accent)
        hint = "已锁定 · 再按一次取消准备" if self.ready[slot] else "←→ 换英雄 · 也可点卡片准备"
        T.text(g, res, hint, 17, T.PALETTE["muted"], center=(x + w // 2, y + h - 20))

    def _skill_row(self, g, x, y, key, value, accent) -> None:
        res = self.app.resources
        pygame.draw.circle(g, accent, (x + 8, y + 12), 7)
        T.text(g, res, key, 19, T.PALETTE["muted"], topleft=(x + 24, y))
        T.text(g, res, value, 21, T.PALETTE["text"], topleft=(x + 96, y - 1))

    # ---- 阶段 2：选关 ----
    _GRID_COLS, _CW, _CH, _CGAP = 3, 236, 88, 14

    def _level_rect(self, i, cfg):
        cols, cw, ch, gap = self._GRID_COLS, self._CW, self._CH, self._CGAP
        x0 = 52
        y0 = 180
        c, r = i % cols, i // cols
        return pygame.Rect(x0 + c * (cw + gap), y0 + r * (ch + gap), cw, ch)

    def _level_at(self, pos):
        cfg = self.app.config
        for i in range(LEVEL_COUNT):
            if self._level_rect(i, cfg).collidepoint(pos):
                return i
        return None

    def _render_levels(self, g, cfg) -> None:
        res = self.app.resources
        T.text(g, res, "选择关卡", 52, T.PALETTE["text"], center=(cfg.LOGIC_W // 2, 54), shadow_=True)
        picks = " · ".join(hero_def(self.heroes[s])["name"] for s in range(self.count))
        T.text(g, res, f"队伍：{picks}", 22, T.PALETTE["accent"], center=(cfg.LOGIC_W // 2, 104))

        for i in range(LEVEL_COUNT):
            r = self._level_rect(i, cfg)
            lv = i + 1
            sel = i == self.level_cursor
            boss = lv in BOSS_LEVELS
            base = (52, 32, 52) if boss else T.PALETTE["panel"]
            if sel:
                base = (92, 50, 62) if boss else (24, 78, 88)
            T.panel(g, r, radius=14, fill=base,
                    border=T.PALETTE["accent"] if sel else ((150, 110, 160) if boss else T.PALETTE["line"]),
                    border_w=3 if sel else 2)
            # 序号徽标
            badge = pygame.Rect(r.x + 12, r.y + 20, 48, 48)
            pygame.draw.rect(g, (12, 18, 30), badge, border_radius=12)
            pygame.draw.rect(g, T.PALETTE["accent"] if sel else T.PALETTE["line"], badge, 2, border_radius=12)
            T.text(g, res, str(lv), 30, T.PALETTE["text"], center=badge.center)
            lv_obj = self.levels.get(lv)
            name = lv_obj.name if lv_obj else f"第 {lv} 关"
            T.text(g, res, name, 23, T.PALETTE["text"] if sel else T.PALETTE["muted"],
                   topleft=(r.x + 72, r.y + 22))
            tag = "BOSS 关" if boss else THEME_CN.get(getattr(lv_obj, "theme", ""), "关卡")
            T.text(g, res, tag, 17, T.PALETTE["gold"] if boss else T.PALETTE["muted"],
                   topleft=(r.x + 72, r.y + 52))
            if sel:
                pygame.draw.rect(g, T.PALETTE["accent"], (r.x + 2, r.y + 14, 4, r.h - 28), border_radius=2)

        self._level_preview(g, cfg)

        T.text(g, res, "← → 选列 · W / S 选行 · Enter 或技能键开始 · ESC 返回选人",
               22, T.PALETTE["muted"], center=(cfg.LOGIC_W // 2, cfg.LOGIC_H - 46))

    # ---- 右侧关卡片：名称 / 小地图 / 纵向剖面 / 图例 / 机制 / 统计 ----
    def _level_preview(self, g, cfg) -> None:
        res = self.app.resources
        px, py, pw, ph = 824, 180, 724, 620
        T.glass(g, (px, py, pw, ph), radius=18, alpha=200, border=T.PALETTE["line"])
        lv = self.levels.get(self.level_cursor + 1)
        if lv is None:
            T.text(g, res, "关卡数据缺失", 24, T.PALETTE["muted"], center=(px + pw // 2, py + ph // 2))
            return
        boss = lv.id in BOSS_LEVELS
        facts = level_facts(lv)

        # ---- 标题区 ----
        T.text(g, res, f"第 {lv.id} 关", 20, T.PALETTE["muted"], topleft=(px + 26, py + 20))
        T.text(g, res, lv.name, 38, T.PALETTE["text"], topleft=(px + 26, py + 42), shadow_=True)
        badge = "BOSS 关" if boss else THEME_CN.get(lv.theme, lv.theme)
        T.pill(g, res, (px + pw - 84, py + 46), badge, active=True, w=118)

        # ---- 小地图 + 右侧纵向剖面 ----
        cs = 13
        mw, mh = 32 * cs, 18 * cs
        mx, my = px + (pw - mw) // 2, py + 104
        self._minimap(g, lv, mx, my, cs)
        self._tier_profile(g, facts, mx + mw + 14, my, px + pw - 16, my + mh)

        # ---- 图例 / 机制 / 统计 ----
        self._legend_row(g, px + 26, my + mh + 14, pw - 52)
        bottom = self._mech_rows(g, px + 26, my + mh + 46, pw - 52, facts, lv)
        sy = self._stat_cards(g, px + 26, bottom + 14, pw - 52, facts)

        # ---- 底部说明 ----
        if boss and lv.boss:
            line1 = f"阶段数 {len(lv.boss.get('phases', []))} · 击败全部阶段即可通关"
            col1 = T.PALETTE["danger"]
        else:
            line1 = "从左侧出发 → 收集宝石 → 抵达右侧终点门"
            col1 = T.PALETTE["muted"]
        T.text(g, res, line1, 18, col1, center=(px + pw // 2, sy + 28))
        T.text(g, res, f"本关 {facts['layers']} 层立体结构 · 上层跑台也藏有道具，爬梯或踩弹簧上去",
               17, T.PALETTE["accent2"], center=(px + pw // 2, sy + 52))

    # ---- 小地图：把碰撞层的字符画成色块 ----
    def _minimap(self, g, lv, mx, my, cs) -> None:
        mw, mh = len(lv.rows[0]) * cs, len(lv.rows) * cs
        pygame.draw.rect(g, (10, 15, 26), (mx - 4, my - 4, mw + 8, mh + 8), border_radius=8)
        # 先铺一层"层位参考线"（每层跑台一行），再画色块 —— 色块会盖住线，
        # 于是只在没有内容的地方留下淡淡的横线，提示"这里还有一层"。
        for r in range(len(lv.rows) - 1):
            if sum(1 for ch in lv.rows[r] if ch in "#=L") >= 3:
                pygame.draw.rect(g, (30, 40, 60), (mx, my + r * cs + cs - 2, mw, 2))
        for rr, row in enumerate(lv.rows):
            for cc, ch in enumerate(row):
                col = _MINIMAP.get(ch)
                if col is None:
                    continue
                pygame.draw.rect(g, col, (mx + cc * cs, my + rr * cs, cs - 1, cs - 1),
                                 border_radius=2)
        pygame.draw.rect(g, T.PALETTE["line"], (mx - 4, my - 4, mw + 8, mh + 8), 2, border_radius=8)

    # ---- 纵向剖面：每层的道具密度条形图（顶层在上、地面在下）----
    def _tier_profile(self, g, facts, x, y, right, bottom) -> None:
        res = self.app.resources
        T.text(g, res, "纵向剖面", 16, T.PALETTE["muted"], topleft=(x, y - 22))
        tiers = list(reversed(facts["tiers"]))          # 高层在上，地面在下
        n = max(1, len(tiers))
        lane = min(34, max(18, (bottom - y) // n))
        bar_x = x + 40
        bar_w = max(24, right - bar_x - 22)
        top_items = max(1, max(t["items"] for t in tiers))
        for i, t in enumerate(tiers):
            ry = y + i * lane
            alt = facts["ground_row"] - t["stand"]
            lab = f"+{alt}" if alt else "地面"
            T.text(g, res, lab, 15,
                   T.PALETTE["text"] if not alt else T.PALETTE["muted"], topleft=(x, ry + 2))
            pygame.draw.rect(g, (14, 20, 33), (bar_x, ry + 3, bar_w, 11), border_radius=5)
            if t["items"]:
                w = max(6, int(bar_w * t["items"] / top_items))
                col = T.PALETTE["gold"] if not alt else T.PALETTE["accent"]
                pygame.draw.rect(g, col, (bar_x, ry + 3, w, 11), border_radius=5)
            T.text(g, res, str(t["items"]), 15, T.PALETTE["muted"],
                   topleft=(bar_x + bar_w + 4, ry + 2))

    # ---- 图例：小地图上的关键色块都代表什么 ----
    def _legend_row(self, g, x, y, width) -> None:
        res = self.app.resources
        items = [("#", "地形"), ("1", "出生点"), ("D", "终点门"),
                 ("M", "敌人"), ("F", "飞行怪"), ("g", "宝石")]
        slot = width / len(items)
        for i, (ch, name) in enumerate(items):
            ix = int(x + i * slot)
            pygame.draw.rect(g, _MINIMAP.get(ch, (140, 150, 170)), (ix, y + 4, 14, 14),
                             border_radius=4)
            T.text(g, res, name, 16, T.PALETTE["muted"], topleft=(ix + 20, y + 2))

    # ---- 机制图例：本关用到的立体元素（有图片用图片，没有则用图元）----
    def _mech_rows(self, g, x, y, width, facts, lv) -> int:
        res = self.app.resources
        c = facts["counts"]
        items = [
            ("L", "梯子", len(facts["ladder_cols"]), "上下攀爬，通往上层"),
            ("S", "弹簧", c["spring"], "踩上去弹到高处"),
            ("=", "单向平台", c["bridge"], "下方跳穿，上方可站"),
            ("W", "静墙", c["wall"], "固定障碍，不受重力"),
            ("$", "金币", c["coin"], "可选奖励，不计通关"),
            ("^", "地刺", c["spike"], "碰到即阵亡，跳过它"),
        ]
        cw = (width - 14) // 2
        rowh, gap = 28, 4
        for i, (key, name, num, desc) in enumerate(items):
            col, row = i % 2, i // 2
            bx = x + col * (cw + 14)
            by = y + row * (rowh + gap)
            on = num > 0
            T.glass(g, (bx, by, cw, rowh), radius=9, alpha=170 if on else 104,
                    border=T.PALETTE["line"] if on else (46, 56, 76))
            ix = bx + 8
            icon = self._mech_icon(lv, key)
            if icon is not None:
                if not on:      # 未出现的机制：图标一起压暗，保持"整条都在休息"的统一感
                    icon = icon.copy()
                    icon.fill((104, 112, 128), special_flags=pygame.BLEND_RGB_MULT)
                g.blit(icon, (ix, by + (rowh - icon.get_height()) // 2))
                ix += 30
            r = T.text(g, res, name, 16,
                       T.PALETTE["text"] if on else (124, 140, 166), topleft=(ix, by + 5))
            T.text(g, res, desc, 14,
                   T.PALETTE["muted"] if on else (88, 102, 126), topleft=(r.right + 10, by + 7))
            tag = f"×{num}" if on else "—"
            T.text(g, res, tag, 16,
                   T.PALETTE["accent"] if on else (92, 106, 130),
                   topleft=(bx + cw - 12 - res.font(16).size(tag)[0], by + 5))
        rows = (len(items) + 1) // 2
        return y + rows * (rowh + gap) - gap

    def _mech_icon(self, lv, key):
        sp = self.sprites
        if sp is None:
            return None
        theme = getattr(lv, "theme", "grass")
        return {"L": lambda: sp.ladder(28),
                "S": lambda: sp.spring(28),
                "=": lambda: sp.bridge(28),
                "W": lambda: sp.wall(theme, 26),
                "$": lambda: sp.coin(24),
                "^": lambda: sp.spike(26)}.get(key, lambda: None)()

    # ---- 要素统计：五张小玻璃卡 ----
    def _stat_cards(self, g, x, y, width, facts) -> int:
        res = self.app.resources
        c = facts["counts"]
        stats = [("宝石", c["gem"]), ("金币", c["coin"]), ("敌人", c["enemy"]),
                 ("地刺", c["spike"]), ("建造箱", c["crate"])]
        gap = 8
        cw = (width - gap * (len(stats) - 1)) // len(stats)
        for i, (k, v) in enumerate(stats):
            bx = x + i * (cw + gap)
            T.glass(g, (bx, y, cw, 60), radius=12, alpha=150, border=T.PALETTE["line"])
            T.text(g, res, k, 16, T.PALETTE["muted"], topleft=(bx + 12, y + 8))
            T.text(g, res, str(v), 28, T.PALETTE["text"], topleft=(bx + 12, y + 26))
        return y + 60
