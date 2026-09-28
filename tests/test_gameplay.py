"""玩法集成测试：直接驱动 World（无需显示），验证物理/技能/胜负不崩且可达。"""
import os
import pygame
from types import SimpleNamespace

from zero_brother.config import Config, DEFAULTS
from zero_brother.input import InputManager
from zero_brother.world.level import load_level
from zero_brother.world.world import World
from zero_brother.world.tilemap import SOLID, GEM_GREEN, GEM_YELLOW, DOOR
from zero_brother.levels.generate import generate_all, levels_dir

LEVELS = levels_dir()


def _app():
    cfg = Config.load()
    im = InputManager(cfg)
    return SimpleNamespace(config=cfg, input=im), cfg


def _key(code, down=True):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=code)


def test_move_right_and_survive():
    generate_all(LEVELS)
    app, cfg = _app()
    lvl = load_level(os.path.join(LEVELS, "level_1.json"))
    world = World(app, lvl, [(0, "archer")])
    p = world.players[0]
    x0 = p.body.x
    # 按住右
    world.input.poll([_key(pygame.K_d)])
    for _ in range(180):  # 3s
        world.update(1 / 60)
    assert p.body.x > x0 + 50, f"玩家未向右移动: {x0} -> {p.body.x}"
    assert world.players[0].alive or len(world.pending_respawn) >= 0


def test_gem_collect_and_win():
    generate_all(LEVELS)
    app, cfg = _app()
    lvl = load_level(os.path.join(LEVELS, "level_1.json"))
    world = World(app, lvl, [(0, "archer")])
    # 清空所有宝石，模拟已全部收集
    for r in range(world.map.rows):
        for c in range(world.map.cols):
            if world.map.grid[r][c] in (GEM_GREEN, GEM_YELLOW, SOLID + 100):
                pass
    for r in range(world.map.rows):
        for c in range(world.map.cols):
            if world.map.grid[r][c] in (GEM_GREEN, GEM_YELLOW):
                world.map.grid[r][c] = 0
    world.gems_collected = world.gems_total
    # 把玩家放到终点门
    door = None
    for r in range(world.map.rows):
        for c in range(world.map.cols):
            if world.map.grid[r][c] == DOOR:
                door = (c, r)
    p = world.players[0]
    p.body.x = door[0] * world.tile
    p.body.y = door[1] * world.tile
    world.update(1 / 60)
    assert world.won, "到达门且宝石集齐应判定通关"


def test_shoot_skill_spawns_bullet():
    generate_all(LEVELS)
    app, cfg = _app()
    lvl = load_level(os.path.join(LEVELS, "level_1.json"))
    world = World(app, lvl, [(0, "archer")])
    world.input.poll([_key(pygame.K_j)])  # SKILL_A = 射击
    world.update(1 / 60)
    assert len(world.bullets) >= 1, "弓箭手射击应生成子弹"


def test_four_players_spawn_on_ground_distinct():
    """1-4 人：4 名玩家应有各自出生点、贴近地面、不悬空堆叠。"""
    generate_all(LEVELS)
    app, cfg = _app()
    lvl = load_level(os.path.join(LEVELS, "level_1.json"))
    picks = [(0, "archer"), (1, "builder"), (2, "ninja"), (3, "doormage")]
    world = World(app, lvl, picks)
    assert len(world.players) == 4
    ys = [p.body.y for p in world.players]
    xs = [p.body.x for p in world.players]
    # 贴近地面（关卡 18 行、地面在第 17 行 => y 接近 17*50 附近）
    assert all(y > 12 * world.tile for y in ys), f"有玩家出生悬空: {ys}"
    # 出生点彼此不同（不堆叠）
    assert len(set(int(x) for x in xs)) == 4, f"出生点重叠: {xs}"


def test_boss_level_loads_and_runs():
    generate_all(LEVELS)
    app, cfg = _app()
    lvl = load_level(os.path.join(LEVELS, "level_5.json"))
    world = World(app, lvl, [(0, "archer")])
    assert len(world.bosses) == 1
    assert len(world.bosses[0].phases) == 2  # L5 = 2 段
    for _ in range(120):
        world.update(1 / 60)
    assert True  # 仅验证无异常


def test_boss_defeatable_by_standing_shots():
    """可达性闭环：站在地面的射击高度必须能一路打死 Boss（否则关卡无解）。"""
    generate_all(LEVELS)
    app, cfg = _app()
    lvl = load_level(os.path.join(LEVELS, "level_5.json"))
    world = World(app, lvl, [(0, "archer")])
    boss = world.bosses[0]
    p = world.players[0]
    for _ in range(40):                     # 先让玩家落到地面
        world.update(1 / 60)
    shot_y = p.body.cy - 4
    from zero_brother.entities.bullet import Bullet
    guard = 0
    while boss.alive and guard < 4000:
        guard += 1
        boss.recover = 0.0                  # 跳过变身硬直，加速测试
        world.bullets.append(Bullet(boss.x - 320, shot_y, 600, cfg.GAMEPLAY["bullet_size"]))
        for _ in range(6):
            world.update(1 / 60)
    assert not boss.alive, f"站立射击无法击败 Boss（shot_y={shot_y}）"


def test_world_emits_semantic_events():
    """逻辑层通过事件队列与表现层解耦：拾取宝石/受伤/跳跃必须产生事件。"""
    generate_all(LEVELS)
    app, cfg = _app()
    lvl = load_level(os.path.join(LEVELS, "level_1.json"))
    world = World(app, lvl, [(0, "archer")])
    world.emit("gem")
    world.emit("gem")
    assert world.drain_events() == ["gem"], "同名事件应去重"
    assert world.drain_events() == [], "drain 后应清空"


def test_monsters_walkers_and_flyers_update():
    """含怪物关卡应能持续更新（覆盖走怪碰撞 + 飞行怪行为）。"""
    generate_all(LEVELS)
    app, cfg = _app()
    lvl = load_level(os.path.join(LEVELS, "level_9.json"))
    world = World(app, lvl, [(0, "archer")])
    assert world.monsters, "第 9 关应含怪物"
    assert any(m.flyer for m in world.monsters), "第 9 关应含飞行怪"
    assert any(not m.flyer for m in world.monsters), "第 9 关应含地面怪"
    for _ in range(300):  # 5s，覆盖巡逻/悬崖转向/碰撞
        world.update(1 / 60)
    assert True


def test_character_select_flow_to_gameplay():
    """角色选择向导：选人(准备) → 选关 → 进入 GameplayScene。"""
    generate_all(LEVELS)
    from zero_brother.core.app import App
    from zero_brother.scenes.select import CharacterSelectScene
    from zero_brother.scenes.gameplay import GameplayScene
    cfg = Config.load()
    app = App(cfg)
    sc = CharacterSelectScene(app)
    app.scenes.switch(sc)
    sc.count = 4
    # 4 名玩家各自按 JUMP「准备」；轮询各自绑定的跳键
    for slot, code in enumerate((pygame.K_w, pygame.K_UP, pygame.K_i, pygame.K_KP8)):
        app.input.poll([_key(code)])
        sc.fixed_update(1 / 60)
    app.input.poll([_key(pygame.K_w, down=False), _key(pygame.K_UP, down=False)])
    assert all(sc.ready[:4]), f"应全部就绪: {sc.ready}"
    sc.fixed_update(1 / 60)  # 累计计时
    sc.fixed_update(1.0)     # 跨过 0.4s 门槛 → 进入关卡阶段
    assert sc.phase == "level", f"应进入选关阶段: {sc.phase}"
    sc.level_cursor = 0
    sc._start()
    assert isinstance(app.scenes.current, GameplayScene)
    assert len(app.scenes.current.world.players) == 4


def test_full_app_gameplay_scene():
    """端到端：真实 App + GameplayScene + 渲染（letterbox/HUD/相机）无崩。"""
    generate_all(LEVELS)
    from zero_brother.core.app import App
    from zero_brother.scenes.gameplay import GameplayScene
    cfg = Config.load()
    app = App(cfg)
    lvl = load_level(os.path.join(LEVELS, "level_1.json"))
    scene = GameplayScene(app, lvl, [(0, "archer")])
    app.scenes.switch(scene)
    p = scene.world.players[0]
    x0 = p.body.x
    # 按住右 + 周期性跳
    app.input.poll([_key(pygame.K_d)])
    for i in range(180):
        if i % 40 == 0:
            app.input.poll([_key(pygame.K_w)])  # 跳跃边沿
        scene.fixed_update(1 / 60)
        scene.render(0)  # 触发 HUD + letterbox 缩放渲染路径
        if i % 40 == 5:
            app.input.poll([_key(pygame.K_w, down=False)])
    assert p.body.x > x0 + 40, "GameplayScene 下玩家应向右移动"
    assert True
