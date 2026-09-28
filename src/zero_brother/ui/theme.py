"""统一 UI 主题：配色 / 面板 / 按钮 / 文本 / 装饰。

所有场景（菜单、选角、HUD、覆盖层）共用这里的构件，保证视觉一致。
风格：深空蓝底 + 青色强调 + 柔和面板，克制发光，圆角卡片。
"""
from __future__ import annotations

import math

import pygame

PALETTE = {
    "bg":      (9, 13, 22),
    "bg2":     (14, 20, 34),
    "panel":   (20, 28, 45),
    "panel2":  (27, 37, 58),
    "line":    (48, 62, 90),
    "text":    (234, 241, 248),
    "muted":   (138, 158, 186),
    "accent":  (63, 208, 214),
    "accent2": (120, 150, 255),
    "gold":    (245, 200, 90),
    "ok":      (104, 224, 154),
    "danger":  (232, 92, 96),
}


# ---------------------------------------------------------------------------
# 基础装饰
# ---------------------------------------------------------------------------
def shadow(surf, rect, radius=14, spread=6, alpha=110):
    r = pygame.Rect(rect).inflate(spread * 2, spread * 2)
    s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 0, 0, alpha), s.get_rect(), border_radius=radius + spread)
    surf.blit(s, (r.x, r.y))


def panel(surf, rect, radius=16, fill=None, border=None, border_w=2, sh=True):
    rect = pygame.Rect(rect)
    if sh:
        shadow(surf, rect, radius=radius, spread=5, alpha=90)
    pygame.draw.rect(surf, fill or PALETTE["panel"], rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, border_w, border_radius=radius)


def glass(surf, rect, radius=14, rgb=(16, 24, 40), alpha=178, border=None, border_w=2):
    """半透明玻璃面板：HUD 用，能透出后景又不影响可读性。"""
    rect = pygame.Rect(rect)
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*rgb, alpha), (0, 0, rect.w, rect.h), border_radius=radius)
    if border:
        pygame.draw.rect(s, (*border, min(255, alpha + 50)), (0, 0, rect.w, rect.h),
                         border_w, border_radius=radius)
    # 顶部一道极淡高光，制造玻璃质感
    hl = pygame.Surface((rect.w, max(1, rect.h // 2)), pygame.SRCALPHA)
    for i in range(hl.get_height()):
        hl.fill((255, 255, 255, max(0, 14 - int(14 * (i / hl.get_height())))), (0, i, rect.w, 1))
    mask = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, rect.w, rect.h), border_radius=radius)
    hl = hl.convert_alpha()
    hl.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(hl, (0, 0))
    surf.blit(s, (rect.x, rect.y))
    return rect


def gradient_v(surf, rect, top, bottom, radius=0):
    """竖直渐变填充（逐行），可选圆角裁切。"""
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return
    s = pygame.Surface((1, h))
    for i in range(h):
        f = i / max(1, h - 1)
        s.set_at((0, i), (int(top[0] + (bottom[0] - top[0]) * f),
                          int(top[1] + (bottom[1] - top[1]) * f),
                          int(top[2] + (bottom[2] - top[2]) * f)))
    s = pygame.transform.smoothscale(s, (w, h)).convert()
    if radius:
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(layer, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
        s = s.convert_alpha()
        s.blit(layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(s, (x, y))


def gradient_h(surf, rect, left, right):
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return
    s = pygame.Surface((w, 1))
    for i in range(w):
        f = i / max(1, w - 1)
        s.set_at((i, 0), (int(left[0] + (right[0] - left[0]) * f),
                          int(left[1] + (right[1] - left[1]) * f),
                          int(left[2] + (right[2] - left[2]) * f)))
    s = pygame.transform.smoothscale(s, (w, h))
    surf.blit(s, (x, y))


# ---------------------------------------------------------------------------
# 文本
# ---------------------------------------------------------------------------
def text(surf, res, s, size, color, topleft=None, center=None, shadow_=False):
    f = res.font(size)
    img = f.render(s, True, color)
    if shadow_:
        sh = f.render(s, True, (0, 0, 0))
        sh.set_alpha(120)
        pos = sh.get_rect(center=center) if center else sh.get_rect(topleft=topleft)
        surf.blit(sh, (pos.x + 1, pos.y + 2))
    r = img.get_rect(center=center) if center else img.get_rect(topleft=topleft)
    surf.blit(img, r)
    return r


def text_center(surf, res, s, size, color, cx, cy, shadow_=False):
    return text(surf, res, s, size, color, center=(cx, cy), shadow_=shadow_)


# ---------------------------------------------------------------------------
# 控件
# ---------------------------------------------------------------------------
def button(surf, res, rect, label, selected=False, sub=None, icon=None, accent=None):
    rect = pygame.Rect(rect)
    accent = accent or PALETTE["accent"]
    fill = PALETTE["panel2"] if selected else PALETTE["panel"]
    border = accent if selected else PALETTE["line"]
    panel(surf, rect, radius=14, fill=fill, border=border, border_w=3 if selected else 2)
    if selected:
        # 左侧强调竖条
        pygame.draw.rect(surf, accent, (rect.x + 2, rect.y + 8, 5, rect.h - 16), border_radius=3)
    x = rect.x + 24
    if icon is not None:
        isz = min(rect.h - 20, 40)
        icon = pygame.transform.smoothscale(icon, (isz, isz))
        surf.blit(icon, (x, rect.centery - isz // 2))
        x += isz + 14
    text(surf, res, label, 30 if selected else 28,
         PALETTE["text"] if selected else PALETTE["muted"], topleft=(x, rect.y + (10 if sub else 18)))
    if sub:
        text(surf, res, sub, 18, PALETTE["muted"] if selected else PALETTE["line"],
             topleft=(x, rect.y + 44))
    return rect


def pill(surf, res, center, label, active=True, w=None):
    f = res.font(20)
    tw = f.size(label)[0]
    w = w or (tw + 34)
    rect = pygame.Rect(0, 0, w, 34)
    rect.center = center
    fill = PALETTE["panel2"] if active else PALETTE["panel"]
    border = PALETTE["accent"] if active else PALETTE["line"]
    pygame.draw.rect(surf, fill, rect, border_radius=17)
    pygame.draw.rect(surf, border, rect, 2, border_radius=17)
    text(surf, res, label, 20, PALETTE["text"] if active else PALETTE["muted"],
         center=center)
    return rect


def stat_chip(surf, res, topleft, icon, value, size=24, label=None):
    """图标 + 像素数字 的小胶囊（HUD 计数器）。"""
    x, y = topleft
    h = size + 12
    if icon is not None:
        surf.blit(icon, (x + 6, y + 6))
        x += size + 12
    if label is not None:
        r = text(surf, res, label, 20, PALETTE["muted"], topleft=(x, y + 6))
        x = r.right + 8
    return x


# ---------------------------------------------------------------------------
# 全屏装饰
# ---------------------------------------------------------------------------
def vignette(surf, strength=140):
    w, h = surf.get_size()
    if not hasattr(vignette, "_cache") or vignette._cache[0] != (w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        steps = 40
        for i in range(steps):
            f = i / steps
            a = int(strength * (f ** 2.2))
            pygame.draw.rect(s, (0, 0, 0, a),
                             (int(w * 0.5 * (1 - f) * 0.6), int(h * 0.5 * (1 - f) * 0.6),
                              int(w - w * (1 - f) * 0.6), int(h - h * (1 - f) * 0.6)))
        vignette._cache = ((w, h), s)
    surf.blit(vignette._cache[1], (0, 0))


def scanlines(surf, alpha=16, gap=3):
    w, h = surf.get_size()
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, gap):
        pygame.draw.line(s, (0, 0, 0, alpha), (0, y), (w, y))
    surf.blit(s, (0, 0))


def _sky_gradient(surf, top, bottom):
    """程序化天空渐变（按 (尺寸,颜色) 缓存），比纯色更有层次。"""
    w, h = surf.get_size()
    key = (w, h, top, bottom)
    cache = getattr(_sky_gradient, "_cache", None)
    if cache is None:
        cache = _sky_gradient._cache = {}
    s = cache.get(key)
    if s is None:
        col = pygame.Surface((1, h))
        for i in range(h):
            f = i / max(1, h - 1)
            col.set_at((0, i), (int(top[0] + (bottom[0] - top[0]) * f),
                                int(top[1] + (bottom[1] - top[1]) * f),
                                int(top[2] + (bottom[2] - top[2]) * f)))
        s = pygame.transform.smoothscale(col, (w, h)).convert()
        cache[key] = s
    surf.blit(s, (0, 0))


def _tile_layer(surf, tile, scroll, px, top_y, alpha=255):
    """把一张可平铺的剪影按视差水平滚动、纵向对齐 blit 到 surf。"""
    if tile is None:
        return
    tw = tile.get_width()
    ox = int(-(scroll * px)) % tw
    if alpha < 255:
        tile = tile.copy()
        tile.set_alpha(alpha)
    x = ox - tw
    while x < surf.get_width():
        surf.blit(tile, (x, top_y))
        x += tw


def parallax_bg(surf, sprites, theme, scroll, darken=0, factor=0.22):
    """Kenney 主题远景：天空渐变 + 两层镂空剪影（视差）+ 地平线雾 + 底部压暗。

    依赖 Kenney 背景的「纯白=镂空」约定（见 Sprites._knock_white），
    因此彩色的 trees/desert/hills/mushrooms 能干净地叠在天空上。
    solid_frac：贴图内「完全实心」处（约 0.559），用它把剪影地平线对齐到屏幕。
    """
    w, h = surf.get_size()
    if sprites is None:
        surf.fill(PALETTE["bg"])
        return
    r = sprites.theme_scene(theme)
    sky = r.get("sky", ((96, 170, 246), (198, 231, 255)))
    _sky_gradient(surf, sky[0], sky[1])

    layer = r.get("layer")
    solid = r.get("solid_frac", 0.559)
    desat = r.get("desat", 0.0)
    tint = r.get("tint")
    tintamt = r.get("tintamt", 0.0)
    wash = r.get("wash", 0)
    # 大气透视：远景向天空色去饱和 + 变淡
    haze_rgb = tuple(int(c * 0.45 + 255 * 0.55) for c in sky[1])
    far_desat = min(1.0, desat + 0.20)
    far_tint = haze_rgb
    far_tintamt = 0.55

    # (层, 缩放, 实心线屏幕位置, 视差系数, 透明度)
    layers = (
        ("far",  0.58, 0.50, factor * 0.38, 190, far_desat, far_tint, far_tintamt, 0),
        ("near", 1.10, 0.62, factor,        255, desat,     tint,     tintamt,     wash),
    )
    for _tag, sc, solid_y, px, alpha, ds, tn, ta, ws in layers:
        if not layer:
            continue
        size = max(64, int(h * sc))
        tile = sprites.scene_layer(layer, size, ds, tn, ta, ws)
        top_y = int(h * solid_y - solid * size)
        _tile_layer(surf, tile, scroll, px, top_y, alpha)

    # 地平线雾：柔和的一条带（两端渐隐，避免出现硬边）
    hz_h = int(h * 0.22)
    haze = pygame.Surface((w, hz_h), pygame.SRCALPHA)
    for i in range(hz_h):
        a = int(38 * math.sin(math.pi * (i / max(1, hz_h - 1))))
        pygame.draw.line(haze, (*sky[1], a), (0, i), (w, i))
    surf.blit(haze, (0, int(h * 0.40)))

    # 底部渐暗：让角色/地形与背景分离
    g = pygame.Surface((w, int(h * 0.55)), pygame.SRCALPHA)
    for i in range(g.get_height()):
        a = int(64 * (i / g.get_height()) ** 1.6)
        pygame.draw.line(g, (10, 16, 28, a), (0, i), (w, i))
    surf.blit(g, (0, h - g.get_height()))
    if darken:
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, darken))
        surf.blit(ov, (0, 0))


def left_scrim(surf, color=(8, 12, 22), max_alpha=170, width=None):
    """左侧渐变遮罩（不遮住右侧背景），用于菜单文字可读。"""
    w, h = surf.get_size()
    width = width or int(w * 0.62)
    g = pygame.Surface((width, h), pygame.SRCALPHA)
    for x in range(width):
        a = int(max_alpha * (1 - x / width) ** 1.5)
        pygame.draw.line(g, (*color, a), (x, 0), (x, h))
    surf.blit(g, (0, 0))
