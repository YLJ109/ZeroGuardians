"""Boss 实体：多段式（§11.2 L5/L10/L15 分别为 2/3/4 段）。

设计：
  - 每段独立血量；一段清空进入下一段（换相位色、变快、召唤更凶）。
  - 空间表现：相位色脉动光环 + 环绕的相位法球 + 落地投影 + 名牌 + 头顶血条，
    让「Boss」在画面上立得住，而不是一只放大的小怪。
  - 行为：上下浮动 + 周期向玩家侧向位移（压迫感）+ 按相位召唤主题小怪。
"""
from __future__ import annotations

import math

import pygame

# 相位色：石 → 霜 → 幽（越往后越"红"，读作危险）
PHASE_COLORS = [(150, 160, 190), (120, 190, 220), (196, 130, 220), (232, 96, 120)]
# 主题 -> Boss 立绘所用的敌人美术
THEME_BOSS_ART = {"stone": "slime", "snow": "frog", "purple": "frog", "grass": "frog", "sand": "frog"}


class Boss:
    def __init__(self, x: float, y: float, cfg, phases: list[int], theme: str = "purple"):
        self.cfg = cfg
        self.theme = theme
        self.x, self.y = x, y
        self.home_y = y
        # 体量 & 悬浮高度经过可达性校核：站立在地面射击（子弹线 ≈ y=818）必须能命中，
        # 因此 cy 落在 760 附近、h=160 → 命中盒纵向覆盖 680~840。
        self.w, self.h = 150, 160
        self.bob_amp = 12
        self.phases = phases
        self.phase = 0
        self.hp = phases[0]
        self.max_hp = phases[0]
        self.alive = True
        self.dead = False
        self.t = 0.0
        self.summon_t = 1.5
        self.recover = 0.0          # 换相位后的短暂无敌/僵直（读作"变身"）
        self.hit_flash = 0.0

    # ------------------------------------------------------------------
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)

    @property
    def color(self):
        return PHASE_COLORS[self.phase % len(PHASE_COLORS)]

    def take_damage(self, d: int) -> None:
        if not self.alive or self.recover > 0:
            return
        self.hp -= d
        self.hit_flash = 0.12
        if self.hp <= 0:
            self._advance()

    def _advance(self) -> None:
        self.phase += 1
        if self.phase >= len(self.phases):
            self.alive = False
            self.dead = True
        else:
            self.hp = self.max_hp = self.phases[self.phase]
            self.recover = 0.9      # 变身硬直：给玩家喘息 + 视觉反馈

    # ------------------------------------------------------------------
    def update(self, dt, game) -> None:
        if not self.alive:
            return
        self.game = game
        self.t += dt
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.recover = max(0.0, self.recover - dt)

        # 上下浮动（压迫感），相位越高越快
        speed = 1.2 + 0.35 * self.phase
        self.y = self.home_y + math.sin(self.t * speed) * self.bob_amp

        # 缓慢向最近的存活玩家靠拢（横向压迫，不贴脸）
        alive = [p for p in game.players if p.alive]
        if alive and self.recover <= 0:
            near = min(alive, key=lambda p: abs(p.body.cx - self.x))
            gap = near.body.cx - self.x
            if abs(gap) > 90:
                self.x += math.copysign(min(abs(gap) - 90, 60 * dt), gap)

        # 周期召唤主题小怪（相位越高越快、上限越高）
        self.summon_t -= dt
        cap = 2 + self.phase
        if self.summon_t <= 0 and len(game.monsters) < cap:
            self.summon_t = max(1.4, 3.2 - 0.5 * self.phase)
            self._summon(game)

    def _summon(self, game) -> None:
        from ..entities.monster import Monster
        kinds = getattr(game, "boss_minion_kinds", None) or ["snail"]
        side = -1 if self.x > game.cfg.LOGIC_W / game.cfg.BLOCK_SIZE / 2 else 1
        x = self.x + side * 130
        y = self.home_y - 20
        m = Monster(x, y, self.cfg, kind=kinds[self.phase % len(kinds)], flyer=False)
        m.body.vx = side * 40
        m.game = game
        game.monsters.append(m)
        game.emit("magic")

    # ------------------------------------------------------------------
    def draw(self, surface, cam):
        cx = self.x - cam.world_left
        cy = self.y - cam.world_top
        col = self.color
        sp = getattr(self, "game", None) and getattr(self.game, "sprites", None)
        bob = math.sin(self.t * 3.0) * 4

        # 落地投影
        shadow = pygame.Surface((self.w + 20, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
        surface.blit(shadow, (cx - (self.w + 20) / 2, cy + self.h / 2 - 6))

        # 脉动光环
        aura_r = int(self.w * 0.62 + math.sin(self.t * 2.6) * 6)
        aura = pygame.Surface((aura_r * 2 + 8, aura_r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(aura, (*col, 46), (aura_r + 4, aura_r + 4), aura_r)
        pygame.draw.circle(aura, (*col, 110), (aura_r + 4, aura_r + 4), aura_r, 3)
        surface.blit(aura, (cx - aura_r - 4, cy - aura_r - 4))

        # 立绘
        drawn = False
        if sp:
            kind = THEME_BOSS_ART.get(self.theme, "frog")
            img = sp.enemy(kind, int(self.t * 4) % 2, self.w, self.h)
            if img:
                if self.hit_flash > 0:
                    img = img.copy()
                    img.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(img, (int(cx - self.w / 2), int(cy - self.h / 2 + bob)))
                drawn = True
        if not drawn:
            pygame.draw.rect(surface, col, (cx - self.w / 2, cy - self.h / 2, self.w, self.h),
                             border_radius=16)

        # 环绕相位法球
        for i in range(3):
            a = self.t * (1.6 + 0.3 * self.phase) + i * (2 * math.pi / 3)
            ox = cx + math.cos(a) * (self.w * 0.62)
            oy = cy + math.sin(a) * (self.h * 0.46)
            pygame.draw.circle(surface, col, (int(ox), int(oy)), 6)
            pygame.draw.circle(surface, (255, 255, 255), (int(ox), int(oy)), 2)

        # 头顶血条（带底槽 + 高光）
        bw, bh = self.w + 16, 10
        bx, by = cx - bw / 2, cy - self.h / 2 - 26
        pygame.draw.rect(surface, (14, 20, 32), (bx - 2, by - 2, bw + 4, bh + 4), border_radius=7)
        pygame.draw.rect(surface, (46, 24, 28), (bx, by, bw, bh), border_radius=5)
        ratio = max(0.0, self.hp / self.max_hp) if self.max_hp else 0.0
        if ratio > 0:
            pygame.draw.rect(surface, (232, 92, 96), (bx, by, bw * ratio, bh), border_radius=5)
            pygame.draw.rect(surface, (255, 176, 176), (bx, by, bw * ratio, 3), border_radius=5)
        # 阶段小圆点
        for i in range(len(self.phases)):
            px = cx - (len(self.phases) - 1) * 8 / 2 + i * 8
            pygame.draw.circle(surface, (255, 255, 255) if i <= self.phase else (90, 96, 116),
                               (int(px), int(by - 10)), 4)
