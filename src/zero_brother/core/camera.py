"""相机：跟随目标并把世界坐标夹在世界边界内（逻辑分辨率内渲染，外层再做 letterbox 缩放）。"""
from __future__ import annotations


class Camera:
    def __init__(self, view_w: int, view_h: int, world_w: int, world_h: int):
        self.view_w = view_w
        self.view_h = view_h
        self.world_w = world_w
        self.world_h = world_h
        self.world_left = 0
        self.world_top = 0

    def follow(self, cx: float, cy: float) -> None:
        if self.world_w <= self.view_w:
            self.world_left = (self.world_w - self.view_w) / 2
        else:
            self.world_left = max(0, min(cx - self.view_w / 2, self.world_w - self.view_w))
        if self.world_h <= self.view_h:
            self.world_top = (self.world_h - self.view_h) / 2
        else:
            self.world_top = max(0, min(cy - self.view_h / 2, self.world_h - self.view_h))

    def apply(self, x: float, y: float) -> tuple:
        return x - self.world_left, y - self.world_top
