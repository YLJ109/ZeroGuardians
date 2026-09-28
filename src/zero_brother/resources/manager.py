"""资源加载器 (GDD §19.1 B3 根治 + B1 根治)。

B3（路径大小写混用 Img/ vs img/）：
  - 所有逻辑路径统一小写 + 正斜杠。
  - 解析时若精确路径不存在，做大小写不敏感回退搜索，杜绝 FileNotFoundError。

B1（SysFont 在本机直接抛 TypeError）：
  - 一律用 pygame.font.Font(path) 加载具体字体文件；绝不调用 SysFont。
  - 字体解析失败回退到内置默认字体，保证冷启动不崩。

资源按种类缓存，避免每帧重建（§15.2 性能预算）。
"""
from __future__ import annotations

import os
from typing import Optional

import pygame

from .manifest import KNOWN_FONTS

# 项目默认字体：随包分发的 Noto Sans SC（OFL，见 vendor/noto_sans_sc/LICENSE.txt）。
# Q6 已闭合 —— 旧占位字体 font/font.ttf（datouren，许可不明、中文度量不均）仅作末位回退。
DEFAULT_FONT = "vendor/noto_sans_sc/NotoSansSC-Regular.otf"
LEGACY_FONT = "font/font.ttf"


class ResourceManager:
    def __init__(self, config, assets_root: Optional[str] = None):
        self.config = config
        # 以本文件为锚，向上查找项目 assets 目录（兼容不同包深度的 src 布局）
        self.assets_root = assets_root or self._locate_assets()
        self._images: dict[str, pygame.Surface] = {}
        self._sounds: dict[str, object] = {}
        self._fonts: dict[tuple, pygame.font.Font] = {}
        self._warnings: list[str] = []
        self._resolved: dict[str, Optional[str]] = {}  # 逻辑路径 -> 真实路径（含失败 None），避免重复 os.walk

    # ------------------------------------------------------------------
    @staticmethod
    def _locate_assets(max_up: int = 6) -> str:
        """从本文件所在目录向上查找包含 assets/ 的目录。"""
        here = os.path.dirname(os.path.abspath(__file__))
        cur = here
        for _ in range(max_up):
            cand = os.path.join(cur, "assets")
            if os.path.isdir(cand):
                return os.path.normpath(cand)
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        # 兜底：默认 src 布局的第三层（不崩）
        return os.path.normpath(os.path.join(here, "..", "..", "..", "assets"))

    # ------------------------------------------------------------------
    # 路径规范化（B3）
    # ------------------------------------------------------------------
    def _canon(self, rel: str) -> str:
        return rel.replace("\\", "/").lower()

    def _resolve_file(self, rel: str) -> Optional[str]:
        """把逻辑路径解析为真实文件；大小写不敏感回退。返回绝对路径或 None（带缓存）。"""
        canon = self._canon(rel)
        if canon in self._resolved:
            return self._resolved[canon]
        base = self.assets_root
        direct = os.path.join(base, *canon.split("/"))
        if os.path.exists(direct):
            self._resolved[canon] = direct
            return direct
        # 大小写不敏感搜索
        target = canon.split("/")
        found = None
        for root, _dirs, files in os.walk(base):
            for f in files:
                rel_parts = os.path.relpath(os.path.join(root, f), base).replace("\\", "/").lower().split("/")
                if rel_parts == target:
                    found = os.path.join(root, f)
                    break
            if found:
                break
        self._resolved[canon] = found
        return found

    # ------------------------------------------------------------------
    # 图像
    # ------------------------------------------------------------------
    def image(self, rel: str, alpha: bool = True) -> Optional[pygame.Surface]:
        key = self._canon(rel)
        if key in self._images:
            return self._images[key]
        path = self._resolve_file(rel)
        if path is None:
            self._warn(f"image not found: {rel}")
            return None
        surf = pygame.image.load(path)
        surf = surf.convert_alpha() if alpha else surf.convert()
        self._images[key] = surf
        return surf

    # ------------------------------------------------------------------
    # 字体（B1：绝不 SysFont）
    # ------------------------------------------------------------------
    def font(self, size: int, name: Optional[str] = None) -> pygame.font.Font:
        key = (name, size)
        if key in self._fonts:
            return self._fonts[key]
        # 指定名称：优先项目 font/ 下同名文件
        if name:
            p = self._resolve_file(f"font/{name}")
            if p and os.path.exists(p):
                f = pygame.font.Font(p, size)
                self._fonts[key] = f
                return f
        else:
            # 未指定名称：优先随包分发的 OFL 字体（中文排版正确），
            # 其次旧占位字体，最后系统已知中文字体；全部失败才用内置默认字体。
            for rel in (DEFAULT_FONT, LEGACY_FONT):
                p = self._resolve_file(rel)
                if p and os.path.exists(p):
                    try:
                        f = pygame.font.Font(p, size)
                        self._fonts[key] = f
                        return f
                    except Exception as e:  # pragma: no cover
                        self._warn(f"font load failed ({rel}): {e}")
        # 回退到系统已知字体
        for cand in KNOWN_FONTS:
            if os.path.exists(cand):
                try:
                    f = pygame.font.Font(cand, size)
                    self._fonts[key] = f
                    return f
                except Exception:  # pragma: no cover
                    continue
        # 最后兜底：内置默认字体（永不崩）
        f = pygame.font.Font(None, size)
        self._fonts[key] = f
        return f

    # ------------------------------------------------------------------
    # 音效（延迟导入 mixer，避免无音频环境报错）
    # ------------------------------------------------------------------
    def sound(self, rel: str):
        key = self._canon(rel)
        if key in self._sounds:
            return self._sounds[key]
        path = self._resolve_file(rel)
        if path is None:
            self._warn(f"sound not found: {rel}")
            return None
        try:
            import pygame.mixer as mixer

            s = mixer.Sound(path)
            self._sounds[key] = s
            return s
        except Exception as e:  # pragma: no cover
            self._warn(f"mixer unavailable: {e}")
            return None

    # ------------------------------------------------------------------
    def _warn(self, msg: str) -> None:
        self._warnings.append(msg)
        # 仅记录，不中断；生产环境可接日志
        print(f"[resource:warn] {msg}")
