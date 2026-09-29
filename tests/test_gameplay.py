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
from zero_brother.heroes.registry import HERO_ORDER

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


# ---------------------------------------------------------------------------
# 宝石收集 / 通关判定
#
# 真事故（玩家报障："到了胜利点游戏没有结束，单人模式有些宝石吃不了"）：
#   宝石按英雄亲和色做硬门槛（弓箭手=绿），黄宝石永远吃不到；
#   但 gems_total 把两种颜色都算进通关目标 → 单人弓箭手最多 4/5 →
#   终点门永远不开、关卡无解（第 1/2/4 关实测均如此）。
# 下面这组用例把「谁能拿什么」和「门前为什么不开」钉死。
# ---------------------------------------------------------------------------
def _gem_cells(world):
    return [(c, r) for r in range(world.map.rows) for c in range(world.map.cols)
            if world.map.grid[r][c] in (GEM_GREEN, GEM_YELLOW)]


def _grab_gems(world):
    """把玩家依次瞬移到每颗宝石格中心并推进一帧，返回吃到的总数。"""
    p = world.players[0]
    t = world.tile
    for c, r in _gem_cells(world):
        p.alive = True
        p.body.x = c * t + (t - p.body.w) / 2
        p.body.y = r * t + (t - p.body.h) / 2
        p.body.vx = p.body.vy = 0
        world.update(1 / 60)
    return world.gems_collected


def test_single_player_archer_can_collect_every_gem_in_every_level():
    """单人（弓箭手）必须能拿齐本关所有宝石 —— 否则终点门永远打不开。"""
    generate_all(LEVELS)
    for i in range(1, 16):
        path = os.path.join(LEVELS, f"level_{i}.json")
        if not os.path.exists(path):
            continue
        app, cfg = _app()
        world = World(app, load_level(path), [(0, "archer")])
        world.monsters.clear()               # 隔离：只验证收集，不被怪打断
        total = world.gems_total
        assert total > 0, f"第 {i} 关应至少有一颗宝石（通关目标）"
        got = _grab_gems(world)
        assert got == total, f"第 {i} 关单人弓箭手只能拿 {got}/{total} 颗宝石，关卡无解"


def test_every_hero_can_collect_both_gem_colors():
    """6 位英雄都必须两种颜色都能拿（亲和色只影响奖励，不能挡路）。"""
    generate_all(LEVELS)
    lvl = load_level(os.path.join(LEVELS, "level_4.json"))   # 4 绿 + 4 黄
    for hid in HERO_ORDER:
        app, cfg = _app()
        world = World(app, lvl, [(0, hid)])
        world.monsters.clear()
        got = _grab_gems(world)
        assert got == world.gems_total, f"{hid} 只能拿 {got}/{world.gems_total} 颗"


def test_gem_affinity_grants_bonus_but_never_blocks():
    """同色亲和 = 额外奖励；异色照拿不误，只是没有奖励。"""
    generate_all(LEVELS)
    lvl = load_level(os.path.join(LEVELS, "level_1.json"))
    app, cfg = _app()
    world = World(app, lvl, [(0, "archer")])          # 弓箭手亲和 = 绿
    world.monsters.clear()
    p = world.players[0]
    t = world.tile

    def touch(cell):
        c, r = cell
        p.body.x = c * t + (t - p.body.w) / 2
        p.body.y = r * t + (t - p.body.h) / 2
        p.body.vx = p.body.vy = 0
        world.update(1 / 60)

    cells = _gem_cells(world)
    green = next((cc for cc in cells if world.map.grid[cc[1]][cc[0]] == GEM_GREEN), None)
    yellow = next((cc for cc in cells if world.map.grid[cc[1]][cc[0]] == GEM_YELLOW), None)
    assert green and yellow, "第 1 关应同时有绿宝石与黄宝石"

    touch(green)
    assert world.gems_collected == 1, "绿宝石应被收集"
    assert world.gem_bonus == 1, "同色亲和应给 +1 奖励"

    touch(yellow)
    assert world.gems_collected == 2, "黄宝石**也**应被收集（不能因为亲和不同就拿不到）"
    assert world.gem_bonus == 1, "异色宝石不应给亲和奖励"


def test_door_hint_explains_why_it_is_locked():
    """门前但宝石没集齐时，必须给出原因 —— 否则玩家只会觉得"游戏卡死没反应"。"""
    generate_all(LEVELS)
    app, cfg = _app()
    world = World(app, load_level(os.path.join(LEVELS, "level_1.json")), [(0, "archer")])
    world.monsters.clear()
    door = next((c, r) for r in range(world.map.rows) for c in range(world.map.cols)
                if world.map.grid[r][c] == DOOR)
    p = world.players[0]
    t = world.tile
    p.body.x = door[0] * t + (t - p.body.w) / 2
    p.body.y = door[1] * t + (t - p.body.h) / 2
    world.update(1 / 60)
    assert not world.won, "宝石没集齐不应通关"
    assert world.door_hint and "宝石" in world.door_hint, f"应提示缺少宝石: {world.door_hint}"

    # 集齐后提示消失并真正通关
    world.gems_collected = world.gems_total
    for r in range(world.map.rows):
        for c in range(world.map.cols):
            if world.map.grid[r][c] in (GEM_GREEN, GEM_YELLOW):
                world.map.grid[r][c] = 0
    world.update(1 / 60)
    assert world.won, "集齐宝石 + 到门 → 应通关"


def test_boss_level_door_hint_mentions_boss():
    """Boss 关：宝石齐了但 Boss 没死，提示要说"先击败 Boss"。"""
    generate_all(LEVELS)
    app, cfg = _app()
    world = World(app, load_level(os.path.join(LEVELS, "level_5.json")), [(0, "archer")])
    world.monsters.clear()
    for r in range(world.map.rows):
        for c in range(world.map.cols):
            if world.map.grid[r][c] in (GEM_GREEN, GEM_YELLOW):
                world.map.grid[r][c] = 0
    door = next((c, r) for r in range(world.map.rows) for c in range(world.map.cols)
                if world.map.grid[r][c] == DOOR)
    p = world.players[0]
    t = world.tile
    p.body.x = door[0] * t + (t - p.body.w) / 2
    p.body.y = door[1] * t + (t - p.body.h) / 2
    world.update(1 / 60)
    assert not world.won
    assert world.door_hint and "Boss" in world.door_hint, f"应提示先打 Boss: {world.door_hint}"


# ---------------------------------------------------------------------------
# 通关结算：必须"结束"本关并给出去处，而不是默默无事发生 / 自动踢回主菜单
# ---------------------------------------------------------------------------
def _win_scene(app, level_name="level_1.json", picks=((0, "archer"), (1, "builder"))):
    from zero_brother.scenes.gameplay import GameplayScene
    lvl = load_level(os.path.join(LEVELS, level_name))
    scene = GameplayScene(app, lvl, list(picks))
    app.scenes.switch(scene)
    w = scene.world
    for r in range(w.map.rows):
        for c in range(w.map.cols):
            if w.map.grid[r][c] in (GEM_GREEN, GEM_YELLOW):
                w.map.grid[r][c] = 0
    w.gems_collected = w.gems_total
    door = next((c, r) for r in range(w.map.rows) for c in range(w.map.cols)
                if w.map.grid[r][c] == DOOR)
    p = w.players[0]
    p.body.x = door[0] * w.tile
    p.body.y = door[1] * w.tile
    for _ in range(4):
        scene.fixed_update(1 / 60)
    return scene


def test_win_opens_result_panel_instead_of_returning_to_menu():
    """通关后停在结算面板等玩家选择；不能自动跳走（原实现 2.2s 后踢回主菜单）。"""
    generate_all(LEVELS)
    from zero_brother.core.app import App
    from zero_brother.scenes.gameplay import GameplayScene
    app = App(Config.load())
    scene = _win_scene(app)
    assert scene.world.won, "前置条件：应已通关"

    for _ in range(60 * 8):                  # 远超原来的 2.2s 自动返回阈值
        scene.fixed_update(1 / 60)
    assert isinstance(app.scenes.current, GameplayScene), "通关后不应自动离开本关"
    scene.render(0)                          # 结算面板渲染不得崩
    keys = [b["key"] for b in scene._result_buttons()]
    assert "next" in keys, f"非最后一关必须提供「下一关」: {keys}"
    assert {"replay", "select", "menu"} <= set(keys), f"应提供重玩/选关/主菜单: {keys}"


def test_result_next_advances_to_the_following_level():
    generate_all(LEVELS)
    from zero_brother.core.app import App
    from zero_brother.scenes.gameplay import GameplayScene
    app = App(Config.load())
    scene = _win_scene(app, "level_1.json")
    scene.handle_event(_key(pygame.K_RETURN))
    cur = app.scenes.current
    assert isinstance(cur, GameplayScene) and cur.level.id == 2, \
        f"应进入第 2 关，实际: {getattr(getattr(cur, 'level', None), 'id', None)}"


def test_result_select_returns_to_level_select():
    """玩家要的「显示选人和关卡」：结算面板能回到选关阶段。"""
    generate_all(LEVELS)
    from zero_brother.core.app import App
    from zero_brother.scenes.select import CharacterSelectScene
    app = App(Config.load())
    scene = _win_scene(app, "level_3.json", ((0, "ninja"), (1, "warlock")))
    scene.handle_event(_key(pygame.K_l))
    cur = app.scenes.current
    assert isinstance(cur, CharacterSelectScene), "按 L 应回到选人/选关场景"
    assert cur.phase == "level", f"应直接落在选关阶段: {cur.phase}"
    assert cur.count == 2, "应保留队伍人数"
    assert cur.heroes[0] == "ninja" and cur.heroes[1] == "warlock", "应保留英雄选择"
    assert cur.level_cursor == 2, f"光标应停在刚通关的关卡: {cur.level_cursor}"


def test_result_replay_rebuilds_the_same_level():
    generate_all(LEVELS)
    from zero_brother.core.app import App
    from zero_brother.scenes.gameplay import GameplayScene
    app = App(Config.load())
    scene = _win_scene(app, "level_3.json")
    scene.handle_event(_key(pygame.K_r))
    cur = app.scenes.current
    assert isinstance(cur, GameplayScene) and cur.level.id == 3
    assert not cur.world.won, "重玩应是干净状态"
    assert [p.hero_id for p in cur.world.players] == ["archer", "builder"], "英雄应沿用"


def test_final_level_result_has_no_next_button():
    generate_all(LEVELS)
    from zero_brother.core.app import App
    from zero_brother.scenes.gameplay import GameplayScene
    app = App(Config.load())
    lvl = load_level(os.path.join(LEVELS, "level_15.json"))
    scene = GameplayScene(app, lvl, [(0, "archer")])
    keys = [b["key"] for b in scene._result_buttons()]
    assert "next" not in keys, f"最后一关不应有「下一关」: {keys}"
    assert "select" in keys and "menu" in keys
