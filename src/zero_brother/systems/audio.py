"""音频系统 —— Kenney CC0 音效（无音频设备时静默降级，绝不阻断主循环）。

设计：
  - 语义化音效名（jump/gem/hurt/…），调用方不关心文件名与音量。
  - 全部使用 pygame.mixer.Sound，按需加载 + 缓存；加载失败只告警不抛异常。
  - 同一帧内同名音效只播一次（防抖），UI 音效还额外加了毫秒级冷却。
  - 支持整体静音开关（M 键）与音量调节。

素材：assets/vendor/kenney_new_platformer/Sounds/*.ogg（CC0）
      assets/vendor/kenney_interface_sounds/Audio/*.ogg（CC0）
"""
from __future__ import annotations

import time

_PF = "vendor/kenney_new_platformer/Sounds"
_UI = "vendor/kenney_interface_sounds/Audio"

# 语义名 -> (素材路径, 音量)
SOUND_MAP: dict[str, tuple[str, float]] = {
    # ---- 玩法 ----
    "jump":     (f"{_PF}/sfx_jump.ogg", 0.42),
    "jump_hi":  (f"{_PF}/sfx_jump-high.ogg", 0.42),
    "gem":      (f"{_PF}/sfx_gem.ogg", 0.55),
    "coin":     (f"{_PF}/sfx_coin.ogg", 0.5),
    "hurt":     (f"{_PF}/sfx_hurt.ogg", 0.6),
    "bump":     (f"{_PF}/sfx_bump.ogg", 0.45),
    "magic":    (f"{_PF}/sfx_magic.ogg", 0.45),
    "throw":    (f"{_PF}/sfx_throw.ogg", 0.45),
    "vanish":   (f"{_PF}/sfx_disappear.ogg", 0.45),
    "place":    (f"{_UI}/drop_002.ogg", 0.5),
    "spring":   (f"{_PF}/sfx_jump-high.ogg", 0.5),
    "ladder":   (f"{_UI}/click_005.ogg", 0.22),
    "boss_hit": (f"{_UI}/glass_003.ogg", 0.35),
    "boss_down": (f"{_UI}/maximize_006.ogg", 0.5),
    "win":      (f"{_UI}/confirmation_002.ogg", 0.55),
    "lose":     (f"{_UI}/minimize_004.ogg", 0.5),
    # ---- UI ----
    "hover":    (f"{_UI}/select_002.ogg", 0.28),
    "confirm":  (f"{_UI}/confirmation_001.ogg", 0.45),
    "back":     (f"{_UI}/back_001.ogg", 0.4),
    "toggle":   (f"{_UI}/toggle_001.ogg", 0.35),
    "deny":     (f"{_UI}/error_004.ogg", 0.35),
    "scroll":   (f"{_UI}/scroll_003.ogg", 0.25),
}

# 同名音效最小间隔（秒）——UI 音特别需要，避免连按糊成噪音
_MIN_GAP = {
    "hover": 0.05, "scroll": 0.05, "gem": 0.03, "coin": 0.03,
    "bump": 0.05, "boss_hit": 0.04, "place": 0.05, "jump": 0.06,
    "ladder": 0.30, "spring": 0.10,
}


class AudioManager:
    def __init__(self, resources, enabled: bool = True):
        self.res = resources
        self.enabled = bool(enabled)
        self.ok = False
        self.muted = False
        self.master = 0.85
        self._sounds: dict[str, object] = {}
        self._last: dict[str, float] = {}
        self._warned: set[str] = set()
        if self.enabled:
            self._init_mixer()

    # ------------------------------------------------------------------
    def _init_mixer(self) -> None:
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(24)
            self.ok = True
        except Exception as e:  # 无音频设备 / 驱动异常
            self.ok = False
            print(f"[audio:warn] mixer unavailable, running silent: {e}")

    # ------------------------------------------------------------------
    def _sound(self, name: str):
        if not self.ok:
            return None
        if name in self._sounds:
            return self._sounds[name]
        entry = SOUND_MAP.get(name)
        if entry is None:
            if name not in self._warned:
                self._warned.add(name)
                print(f"[audio:warn] unknown sound '{name}'")
            self._sounds[name] = None
            return None
        rel, vol = entry
        snd = self.res.sound(rel) if self.res is not None else None
        if snd is not None:
            try:
                snd.set_volume(min(1.0, vol * self.master))
            except Exception:
                pass
        self._sounds[name] = snd
        return snd

    # ------------------------------------------------------------------
    def play(self, name: str, volume_scale: float = 1.0) -> None:
        """播放语义音效；任何失败都静默忽略。"""
        if not self.ok or self.muted:
            return
        now = time.monotonic()
        gap = _MIN_GAP.get(name, 0.0)
        if gap and now - self._last.get(name, 0.0) < gap:
            return
        self._last[name] = now
        snd = self._sound(name)
        if snd is None:
            return
        try:
            if volume_scale != 1.0:
                _rel, vol = SOUND_MAP[name]
                snd.set_volume(max(0.0, min(1.0, vol * self.master * volume_scale)))
            snd.play()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted

    def set_master(self, v: float) -> None:
        self.master = max(0.0, min(1.0, v))
        for name, snd in self._sounds.items():
            if snd is None:
                continue
            try:
                _rel, vol = SOUND_MAP[name]
                snd.set_volume(min(1.0, vol * self.master))
            except Exception:
                pass
