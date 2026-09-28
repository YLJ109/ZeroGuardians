"""固定步长累加器 (GDD §6 结算顺序)。

逻辑更新以 FIXED_DT 为单位逐步结算，渲染可按累加余量做插值 alpha。
这是手感确定性（可回放）与 1–4 人同屏不降帧的基础。
"""
from __future__ import annotations

from typing import Callable


class FixedTimestep:
    def __init__(self, step: float, max_steps: int = 5):
        self.step = step
        self.max_steps = max_steps
        self._acc = 0.0

    def advance(self, frame_dt: float, update: Callable[[float], None]) -> float:
        """把一帧的真实耗时切分为若干固定步长 update 调用，返回插值 alpha。"""
        self._acc += min(frame_dt, self.step * self.max_steps)
        steps = 0
        while self._acc >= self.step and steps < self.max_steps:
            update(self.step)
            self._acc -= self.step
            steps += 1
        return self._acc / self.step
