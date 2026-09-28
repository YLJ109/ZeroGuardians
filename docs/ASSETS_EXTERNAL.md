# 外采素材映射表（External Assets Mapping）

| 项 | 内容 |
|---|---|
| 配套 | `docs/ASSETS.md`（缺口清单）、`docs/GDD.md`（玩法） |
| 状态 | 2 个 CC0 包**已下载入库**并验证许可 |
| 许可 | 全部 **CC0 1.0**（公共领域），可商用、可修改、可再分发，署名非必需 |

---

## 0. 结论

网上已找到**质量远高于现有素材**的替代方案，并已实际下载验证：

| 项 | 结果 |
|---|---|
| 角色 | 5 色 × 9 动作（含 duck / hit / climb），**带 SVG 源文件可改色** |
| 敌人 | **18 种**（史莱姆/蜂/蝇/蛙/鼠/蜗/虫/锯/鱼/藤壶/瓢虫/方块…） |
| 地形 | **6 套主题**（草/土/沙/雪/石/紫岩），每套含完整 9 宫格 + 斜坡 + 云台 |
| 道具 | 宝石 4 色、金币、钥匙锁 4 色、开关 4 色、拉杆、门、弹簧、传送带、地刺、梯、岩浆、水 |
| HUD | 全套（心/半心/空心、金币、钥匙、玩家头像 5 色、**数字 0–9**） |
| 背景 | 14 张（含 512×512） |
| 音效 | 10 个玩法音效 + **100 个 UI 音效** |

**原 ASSETS.md 列的 18 个音效缺口，17 个已被覆盖。**

---

## 1. 已入库外采包

| 包 | 许可 | 内容 | 大小 | 路径 |
|---|---|---|---|---|
| **Kenney New Platformer Pack 1.0** | CC0 1.0 | 879 PNG + **433 SVG** + 10 OGG + 17 spritesheets | 3.4 MB（解压 ~7 MB） | `assets/vendor/kenney_new_platformer/` |
| **Kenney Interface Sounds 1.0** | CC0 1.0 | 100 个 OGG（click/back/error/confirm/switch/scroll/tick…） | 834 KB | `assets/vendor/kenney_interface_sounds/` |

**许可原文要点**（已读 `License.txt` 核实）：
- ✅ 个人 / 教育 / **商业**用途均可
- ✅ 可修改、可再分发、可嵌入
- ✅ 署名**非强制**（建议致谢 `Kenney.nl`）
- ❌ **唯一禁止**：不得使用 Kenney 的商标 / logo

---

## 2. 为什么这套比原素材合适

| 对比项 | 你的原素材 | Kenney 这套 |
|---|---|---|
| 来源 | ❌ 未知，许可不明 | ✅ CC0，有 License.txt |
| 尺寸 | 混乱（40×60 / 50×50 / 221×221 / 304×447） | ✅ 统一 128×128（背景 256/512） |
| 风格 | 卡通 | ✅ 圆润卡通矢量，**风格接近** |
| 可缩放 | ❌ 位图放大糊 | ✅ **提供 SVG 源文件**，任意尺寸无损 |
| 敌人种类 | 1 种 | ✅ 18 种 |
| 地形主题 | 1 套（缺洞穴/沙漠/终章） | ✅ 6 套 |
| 角色状态 | 待机/走/跳（缺蹲/受击/死亡） | ✅ 含 **duck / hit / climb** |

> 之前担心的"像素风不匹配"问题不存在——这套**不是像素风**，是 128×128 的矢量导出。

---

## 3. 英雄映射（6 英雄）

Kenney 有 **5 色角色 × 9 动作**：`idle / walk_a / walk_b / jump / duck / hit / front / climb_a / climb_b`

| 我的英雄 | 颜色 | Kenney 前缀 | 状态 |
|---|---|---|---|
| 弓箭手 · 零零 | 绿 | `character_green_*` | ✅ |
| 搬运工 · 砖哥 | 黄 | `character_yellow_*` | ✅ |
| 忍者 · 影 | 紫 | `character_purple_*` | ✅ |
| 门师 · 隙 | 粉 | `character_pink_*` | ✅ |
| 术士 · 烬 | 米 | `character_beige_*` | ✅ |
| 重锤 · 岩 | **需新色** | 由 `Vector/Characters/*.svg` 改色生成（如深蓝） | ⚠️ 需从 SVG 导出 |

### 动作映射

| 我的状态 | Kenney | 说明 |
|---|---|---|
| `idle` L/R | `idle` | ✅ 需水平镜像生成 Left |
| `run` 4 帧 | `walk_a` / `walk_b` | ⚠️ **只有 2 帧** → 用 `a,b,a,b` 循环，或自行补中间帧 |
| `jump` | `jump` | ✅ |
| `fall` | ❌ 无 | 用 `jump` 复用 + 代码淡出，或改色区分 |
| `crouch` | `duck` | ✅ **原素材没有，这是新增** |
| `hurt` | `hit` | ✅ **原素材没有** |
| `dead` | ❌ 无 | 用 `hit` + 代码缩放淡出 |
| `cast_a/b` | ❌ 无 | 用 `front` + 特效层表现 |
| `portrait` | `hud_player_{color}` | ✅ 选人界面头像直接可用 |

**结论**：蹲下、受击这两个原素材完全没有的状态，**现在有了**。

---

## 4. 怪物 / Boss 映射

Kenney 提供 **18 种敌人**（每种含 2–4 帧动画）：

| 我的怪物 | Kenney 来源 | 状态 |
|---|---|---|
| 巡逻怪 | `slime_normal_walk_a/b` | ✅ |
| 高速追逐怪 | `mouse_walk_a/b` 或 `worm_normal_move_a/b` | ✅ |
| 飞行怪 | `fly_a/b` 或 `bee_a/b` | ✅ |
| 装甲怪（2 次命中） | `block_idle` / `slime_block_*` | ✅ |
| 远程怪 | `barnacle_attack_a/b` 或 `fish_purple_up/down` | ✅ |
| 眩晕态（重踏效果） | `snail_shell` | ✅ |
| 水下/特殊关 | `fish_blue` / `fish_yellow` | ✅（预留） |
| **Boss（L15）** | ❌ 无 | ⚠️ 建议 `slime_block` 或 `block` 放大到 300×300 + 自制受击/死亡帧 |

---

## 5. 地形 / 道具映射

| 我的需求 | Kenney 文件 | 状态 |
|---|---|---|
| 草墙 (tile 1) | `terrain_grass_block` | ✅ |
| 砖墙 (tile 2) | `bricks_brown` / `brick_brown` | ✅ |
| 地刺 (tile 3) | `spikes` | ✅ |
| 纸箱 (tile 4) | `block_plank` / `weight` | ✅ |
| 单向平台 (tile 7) | `bridge` / `block_planks` | ✅ 需改判定 |
| 压力板 (tile 8) | `switch_*` + `switch_*_pressed` | ✅ **两态齐全** |
| 绿宝石 | `gem_green` | ✅ |
| 黄宝石 | `gem_yellow` | ✅ |
| 传送门·蓝 / 橙 | `door_closed` / `door_open` | ⚠️ 需改造配色 |
| 终点传送门 | `door_open_top` 放大 | ⚠️ |
| 子弹 | ❌ 无 | 复用原 `子弹左/右.png` ✅ |
| 持箱态箱子 | `block_plank` | ✅ |
| 飞行中箱子 | `weight` | ✅ |
| 弹簧 | `spring` / `spring_out` | ✅ |
| 传送带 | `conveyor` | ✅ |
| 冰面 | `terrain_snow_*` / `snow` | ✅ |
| 岩浆 / 水 | `lava` / `water` | ✅ 预留危险地形 |
| 钥匙 / 锁（4 色） | `key_*` / `lock_*` | ✅ 可做 L13 机关 |
| 生命 | `heart` / `hud_heart` | ✅ |
| 星星（评分） | `star` | ✅ |
| 终点旗 | `flag_*` | ✅ |

---

## 6. 主题背景（4 主题）

| 我的主题 | Kenney | 状态 |
|---|---|---|
| 草地（L1–L5） | `background_color_hills` / `background_solid_grass` | ✅ |
| 洞穴（L6–L9） | `background_solid_dirt` + `terrain_stone_*` | ✅ |
| 遗迹 / 沙漠（L10–L12） | `background_color_desert` / `background_solid_sand` | ✅ |
| 机械 / 终章（L13–L15） | `background_solid_sky` / `background_clouds` | ⚠️ 需自制机械元素 |

背景有 **256×256 与 512×512** 两种尺寸，可直接平铺或拉伸到 1600×900。

---

## 7. HUD（全套齐备）

`hud_coin`、`hud_heart`、`hud_heart_empty`、`hud_heart_half`、`hud_key_{blue,green,red,yellow}`、
`hud_player_{5色}`、`hud_player_helmet_{5色}`、**`hud_character_0`~`9`**、`hud_character_multiply`、`hud_character_percent`

→ 血量、金币、钥匙、**数字 0–9**（可用于宝石计数、计时器）全部齐备，无需自制。

---

## 8. 音效映射（18 个缺口的解法）

| 我的音效 | 来源 | 状态 |
|---|---|---|
| 跳 | `sfx_jump.ogg`（或原 `跳.wav`） | ✅ |
| 落地 | `sfx_bump.ogg` | ✅ |
| **二段跳** | `sfx_jump-high.ogg` | ✅ |
| **悬浮** | `sfx_magic.ogg` | ✅ |
| 射击 | 原 `发射.wav` | ✅ |
| 命中 | 原 `碰撞.wav` 或 `sfx_bump.ogg` | ✅ |
| 怪物死 | 原 `怪物死.wav` | ✅ |
| **冲击波** | `sfx_magic.ogg` | ✅ |
| **突刺** | `interface/switch_001.ogg` | ✅ |
| **重踏落地** | `sfx_bump.ogg` | ✅ |
| 吃宝石 | 原 `吃宝石.wav` 或 `sfx_gem.ogg` | ✅ |
| **放箱** | `sfx_throw.ogg` | ✅ |
| **回收箱** | `sfx_disappear.ogg` | ✅ |
| 举箱 | `interface/click_001.ogg` | ✅ |
| **投掷** | `sfx_throw.ogg` | ✅ |
| **传送** | `sfx_magic.ogg` | ✅ |
| 死声 | 原 `死声.wav` | ✅ |
| 胜利 | 原 `胜利.wav` | ✅ |
| **失败** | `interface/error_001.ogg` | ✅ |
| **复活** | `interface/confirmation_001.ogg` | ✅ |
| **UI 点击** | `interface/click_001.ogg` | ✅ |
| **UI 悬停** | `interface/tick_001.ogg` | ✅ |
| **UI 返回** | `interface/back_001.ogg` | ✅ |
| **UI 拒绝** | `interface/error_001.ogg` | ✅ |
| **关卡开始** | `interface/confirmation_001.ogg` | ✅ |
| **Boss 出场/受击/死亡** | ❌ | ⚠️ 仅此 3 个仍缺 |

**100 个 UI 音效分类**：`back / bong / click / close / confirmation / drop / error / glass / glitch / maximize / minimize / open / pluck / question / scratch / scroll / select / switch / tick / toggle`

> 格式是 `.ogg` —— pygame 原生支持 `pygame.mixer.Sound`，无需转换。

---

## 9. 仍缺清单（更新后）

| 项 | 数量 | 建议 | 优先级 |
|---|---|---|---|
| 第 6 个英雄 | 1 套 | 由 `Vector/Characters/*.svg` 改色导出 | P0 |
| Boss | 1 套（约 8 帧） | `slime_block` 放大 + 自制，或外采 | P1 |
| 传送门（蓝/橙/终点） | 3 | `door_*` 改造配色 | P1 |
| Boss 音效 | 3 | 自制或 Freesound 筛 CC0 | P2 |
| 机械主题背景 | 1–2 | 自制 | P2 |
| **中文字体** | 1–2 套 | **思源黑体 / 阿里巴巴普惠体**（见 §10） | **P0（合规阻塞）** |
| BGM | 2–3 | Kenney Music Jingles（CC0）或 OGA 筛 CC0 | P1 |
| 特效粒子 | 约 10 | **程序化生成**，零许可风险 | P1 |
| 走路补帧（2→4） | 6 英雄 × 2 | 可选 | P2 |

对比 `ASSETS.md` 原本列的"缺约 200 个文件"，**外采后实际缺口降到约 30 个**。

---

## 10. 字体方案（解开 QA1 合规阻塞）

现有 3 个字体文件**来源与许可全部未知**，且 `font.ttf` 与 `datouren.ttf` 是同一文件（MD5 相同）。**建议整体替换为**：

| 字体 | 授权 | 特点 | 适用 |
|---|---|---|---|
| **思源黑体** Source Han Sans SC | **SIL OFL 1.1** | 7 字重，简繁日韩全覆盖，可商用/可修改/可嵌入，唯一限制是不可单独售卖字体文件 | 正文 / UI / HUD |
| **阿里巴巴普惠体** | 免费商用声明 | 多字重，数字与西文宽度整齐 | 数据面板 / 计时器 |
| 站酷系列（酷黑/快乐体） | 站酷免费商用 | 风格化 | 标题 |

> 依据思源黑体官方授权：允许任何个人与企业免费、永久、无限制使用、修改、嵌入、分发，可用于商业用途，**无需付费、无需署名**。
> 政策会更新，**以字体官方最新说明为准**。

---

## 11. ⚠️ 尺寸适配（工程必读，否则会变形）

Kenney 的 PNG 是 **128×128 的正方形画布**，角色/道具在画布中居中，**四周有透明边**。

❌ **错误做法**：直接 `pygame.transform.scale(img, (40, 60))` —— 会把透明边一起压进去，角色被**拉伸变形**且实际显示偏小。

✅ **正确做法**：先裁掉透明边，再按比例缩放：

```python
raw = pygame.image.load(path).convert_alpha()
tight = raw.subsurface(raw.get_bounding_rect())   # 裁掉透明边
ratio = min(40 / tight.get_width(), 60 / tight.get_height())
w = int(tight.get_width() * ratio); h = int(tight.get_height() * ratio)
img = pygame.transform.smoothscale(tight, (w, h))  # 保持比例
```

并且**缩放结果必须缓存**（启动时做一次），不要每帧 scale。

更彻底的方案：用 `Vector/*.svg` 直接按目标尺寸导出（需 cairosvg 等库，可选）。

---

## 12. 入库规范

| 规则 | 说明 |
|---|---|
| `vendor/` 只读 | 保留原始包 + `License.txt` + `source.zip`，**不修改、不重命名** |
| 使用副本 | 实际用到的素材按 `ASSETS.md §4` 命名规范复制到 `img/`、`wav/` 对应目录 |
| 记录来源 | `manifest.json` 每条记 `license: "CC0"`、`source: "Kenney New Platformer Pack 1.0"`、`source_url` |
| 致谢 | 建议在游戏"关于"页加一行 `Kenney.nl (CC0)` —— 非强制，但业界惯例 |

---

## 13. 下一步

1. **解锁 QA1**：下载思源黑体替换现有 3 个许可不明的字体（这是唯一阻塞分发的问题）。
2. 用 `Vector/Characters/*.svg` 改色生成第 6 个英雄（重锤·岩）。
3. 按 §3–§8 映射表把素材从 `vendor/` 复制到 `img/`、`wav/`，同时完成中文文件名 → 英文小写重命名。
4. 建 `assets/manifest.json` 记录许可台账。

---

## 14. 使用意见与必须处理的错配（实测）

> 以下结论来自对素材的实际 `getbbox()` 测量，不是目测。

### 14.1 实测数据

| 素材 | 画布 | 有效内容 | 占比 |
|---|---|---|---|
| `character_green_idle` | 128×128 | **81×97** | 63% / 76% |
| `character_green_walk_a` | 128×128 | 84×95 | 66% / 74% |
| `character_green_duck` | 128×128 | 81×84 | 63% / 66% |
| `character_green_jump` | 128×128 | 82×97 | 64% / 76% |
| `terrain_grass_block` | 64×64 | 64×64 | **100%** |
| `bricks_brown` / `block_plank` / `door_open` | 64×64 | 64×64 | **100%** |
| `spikes` | 64×64 | 64×**34** | 100% / 53% |
| `gem_green` | 64×64 | 40×35 | 62% / 55% |
| `slime_normal_walk_a` | 64×64 | 56×42 | 88% / 66% |

**另有一处未在上文提到的结构**：所有素材都有 **`Default/`（1×）与 `Double/`（2×）两套**——角色 128 / 256，地形 64 / 128。

---

### 14.2 ⚠️ 错配 1：角色宽高比对不上（最严重）

| | 宽高比 | 形状 |
|---|---|---|
| Kenney 角色实际内容 | 81 : 97 = **0.835** | 矮胖 Q 版 |
| GDD §9.3 现定 | 40 : 60 = **0.667** | 瘦高 |

**后果**：直接 `scale((40,60))` 会把角色**拉瘦拉高约 20%**，脸会变形。
按比例缩放则得到 40×48，**比设计高度矮 12 px**。

**✅ 修正建议**：贴图尺寸由 `40×60` 改为 **`50×60`**
- 宽高比 `50:60 = 0.833` ≈ Kenney `0.835` → **几乎零变形**
- 高度 60 px 不变，宽度增加到 1 格（50 px），视觉更饱满
- 相应把碰撞盒由 `36×56` 调整为 **`44×56`**（GDD §9.3 需同步改）

---

### 14.3 ⚠️ 错配 2：角色比设计高 27%，跳跃手感会变

- Kenney 角色高 `97`，地形块 `64` → 角色高 = **1.52 个格子**
- 按 `TILE=50`，角色实际高 ≈ **76 px**，而现设计是 60 px

| | 跳跃高度 / 角色身高 | 观感 |
|---|---|---|
| 现状（角色 60 px） | 110 / 60 = **1.83 倍** | 跳得高、飘 |
| 换素材后（角色 76 px） | 110 / 76 = **1.45 倍** | 明显变"钝" |

**✅ 修正建议（二选一）**：
- **A**：跳跃高度由 110 px 提到 **130 px**（`JUMP_VELOCITY` 由 -630 改为 **-684 px/s**），恢复到约 1.7 倍 → 推荐，改动小
- **B**：接受角色变大，但**必须重算 GDD §8.5 的"垂直缺口 ≥ 4 格"约束**（角色变高后 185 px 的二段跳上限也要跟着改）

> 推导：`v₀ = √(2·g·h) = √(2 × 1800 × 130) = √468000 ≈ 684 px/s`

---

### 14.4 ✅ 好消息：地形块完美匹配

`terrain_grass_block` / `bricks_brown` / `block_plank` / `door_open` 都是 **64×64 满画布**（100%），
缩放到 `50×50` 无变形、无缝拼接。

`spikes` 是 `64×34`（只占下半部），缩放到 50×27 —— **正好符合 GDD 里"地刺绘制在格子下部、判定框 50×20"的设计**，不用改。

---

### 14.5 ✅ 建议：用 `Double/` 版本，别用 `Default/`

| 场景 | 建议 |
|---|---|
| 窗口模式 1600×900 | `Default/` 够用 |
| **全屏 / 高 DPI（GDD §4.1）** | **必须用 `Double/` 下采样** |

理由：全屏时 `scale` 可能 > 1（1920×1080 时 scale=1.2），用 128 的素材放大就会糊；
而 `Double/`（256）下采样永远比上采样清晰。**建议统一用 `Double/`，代价只是加载稍慢**。

---

### 14.6 🎨 我的判断：这套适合"跑通玩法"，不适合"直接当终版"

| 优点 | 问题 |
|---|---|
| ✅ CC0，零法律风险 | ⚠️ **Kenney 素材被全球大量独立游戏使用**，辨识度低，容易"撞脸" |
| ✅ 风格统一、成套（地形/敌人/HUD/背景同源） | ⚠️ 圆润 Q 版偏"低龄"，与"守护者"题材的严肃感有差距 |
| ✅ 带 SVG，可改色改造 | ⚠️ 缺 Boss、缺传送门、走路只有 2 帧 |

**建议路线（分两阶段）**：

| 阶段 | 做法 |
|---|---|
| **M0–M5（跑通玩法）** | 直接用 Kenney 原色，把精力放在玩法、手感、关卡上。**不要在这里纠结美术** |
| **M6–M7（终版包装）** | 用 SVG 做**统一改色 + 加小配饰**（如给每个英雄加一个专属头饰/披风），把"Kenney 脸"降到最低 |

最低成本的差异化就是**改配色方案**——同一套形状换一套配色，观感差异会非常大。

---

### 14.7 风格割裂警告：不要混用旧背景

你的旧背景（`界面背景.png` 1600×900、`背景(1700x900)22.png`）与 Kenney 的画风**不是一套**。
如果角色/地形用 Kenney、背景用旧的，会像**拼贴画**。

**✅ 建议**：背景也一并换成 Kenney 的 `Backgrounds/`（14 张，含 512×512），
6 套地形主题正好对应 GDD §3.5 的 4 个主题分区（草地/洞穴/沙漠/终章）。

---

### 14.8 其余意见

| # | 意见 |
|---|---|
| 1 | **走路只有 2 帧**（`walk_a`/`walk_b`）→ 用 `a→b→a→b` 循环即可，很多独立游戏都这样，不必补帧 |
| 2 | **缺 `fall`（下落）帧** → 复用 `jump` 或代码内垂直翻转，不必另做 |
| 3 | **缺施法帧** → 用 `front`（正面）+ 特效层表现技能，够用 |
| 4 | **第 6 英雄** → 从 `Vector/Characters/*.svg` 改色导出（建议重锤用铁灰/深蓝，与其它 5 色拉开） |
| 5 | **Boss 美术方案（v0.3 修订）** → 用户已裁决 **L5 / L10 / L15 均为真 Boss 关**（石巨像 / 双核守卫 / 终焉之门，2/3/4 段）。不再走"L15 多波敌人"妥协。低成本做法：用 `slime_block`/`block` 放大到 300×300 + 自制受击/死亡帧 + 特效层（§14 受击闪白、碎裂粒子）表现多段；Boss 音用 Kenney Interface Sounds 合成。Boss 关机制见 GDD §11.2 与用例 P/Q/R |
| 6 | **传送门** → `door_closed`/`door_open` 改色充当蓝/橙门；终点门用 `door_open_top` 放大到 100×150 |
| 7 | **字体已裁决（v0.3）** → Q6 已关，3 个旧字体改换**思源黑体 / 阿里巴巴普惠体（SIL OFL 1.1）**，M0 资源加载器建立许可白名单（见 §10）。分发合规阻断解除 |

---

## 15. v0.5 实施更新（素材真正接进渲染层）

前面的章节是「选型与评估」，这一节是**已经落地的结果**，可以直接对照代码验收。

### 15.1 背景：从「一张糊底图」到「两层视差 + 镂空合成」

**踩到的坑**：Kenney `Backgrounds/Default/*.png` 全部是 **不透明** PNG（256²）。
按「一张铺满」的用法会让每一关都糊成一整块，看不出主题，也让地形与后景混在一起。

**关键发现**：`background_color_*` 这组图用**纯白 (255,255,255) 表示镂空**——
白色区域是要被扣掉的天空，只有剪影本身有颜色。实测四张图的「完全实心线」都在
`y/256 = 0.559`，据此可以把剪影的地平线精确对齐到屏幕任意高度。

**落地做法**（`world/sprites.py` + `ui/theme.py`）：

| 步骤 | 实现 |
|---|---|
| 天空 | 程序化竖直渐变（`_sky_gradient`），每个主题一组 (天顶色, 地平线色) |
| 镂空 | `Sprites._knock_white()` 把近白像素（≥246）alpha 置 0，得到带透明的剪影层 |
| 主题化 | `Sprites._stylize()` 做「去饱和 + 染色 + 泛白」：石头 = 灰蓝化，雪原 = 白化 |
| 视差 | 远层（`h*0.58`，α=190，视差 ×0.38）+ 近层（`h*1.10`，α=255，视差 ×1.0） |
| 收口 | 地平线雾（正弦带，两端渐隐）+ 底部渐暗，把角色/地形与后景分离 |

因此 5 个主题各有独立天空色与剪影色调，不再靠"换底色"糊弄。

### 15.2 字体：Q6 正式闭合（思源同源 OFL 字体，随包分发）

| 项 | 内容 |
|---|---|
| 字体 | **Noto Sans SC Regular**（与思源黑体 Source Han Sans 同源同设计） |
| 上游 | https://github.com/googlefonts/noto-cjk · `Sans/SubsetOTF/SC/NotoSansSC-Regular.otf` |
| 许可 | **SIL Open Font License 1.1**，全文随包 → `assets/vendor/noto_sans_sc/LICENSE.txt` |
| 体积 | 完整 8.3 MB → **子集化后 862 KB**（3,964 字：GB2312 一级 3,755 + ASCII + CJK 标点 + UI 符号） |
| 复现 | `python tools/build_font_subset.py`（扫全项目字符串 → 生成字符集 → 调 fontTools 子集） |
| 解析链 | `vendor/noto_sans_sc` → 旧 `font/font.ttf`（仅兜底）→ 系统 CJK 字体 → pygame 内置 |

**为什么必须换**：旧 `font/font.ttf`（`datouren.ttf`）中文**字宽不一致**
（22px 字号下 5 个汉字的推进量是 17/14/21/20/22 px），字形互相挤在一起，
是"界面看着廉价"的头号原因。换成 Noto Sans SC 后中文推进量恒为等宽，
排版立刻端正。已加回归用例：`test_bundled_font_renders_chinese_uniformly`。

### 15.3 音效：语义名 → Kenney CC0 素材，全部接线

`systems/audio.py` 建立「语义名 → (素材, 音量)」映射表，覆盖：

| 类别 | 语义名 |
|---|---|
| 玩法 | `jump` `jump_hi` `gem` `hurt` `bump` `magic` `throw` `vanish` `place` `boss_hit` `boss_down` `win` `lose` |
| UI | `hover` `confirm` `back` `toggle` `deny` `scroll` |

架构上**逻辑层不依赖音频**：实体只调用 `world.emit("gem")`，由 `GameplayScene._flush_events()`
消费事件队列后才播放音效。无音频设备时 `AudioManager` 静默降级，绝不阻断主循环。
用例 `test_every_sound_maps_to_existing_file` 保证音效名不会"接了个不存在的文件"。

### 15.4 Boss：从「放大的小怪」到「站得住的 Boss」

| 维度 | 之前的做法 | 现在 |
|---|---|---|
| 立绘 | 2 帧小怪直接放大 | 130×150 立绘 + 落地投影 + 脉动相位光环 + 3 颗环绕法球 |
| 反馈 | 无 | 受击闪白、换相位 0.9s 硬直（读作"变身"）、头顶血条 + 阶段圆点 |
| 行为 | 只有召唤 | 浮动 + 向最近玩家横向压迫 + 按相位加速召唤主题小怪 |
| 名称 | 无 | 主题名（磐石魔像 / 霜牙守卫 / 幽孢女王），与关卡名一致 |

**一个真实的可达性 bug**：Boss 原本悬在 `y=7 格（350px）`，而弓箭手站在地面的
子弹线在 `y=818`——**子弹永远打不到 Boss，关卡无解**。现已把悬浮中心校核到
`y=15.2 格（760px）`、命中盒 680~840，覆盖站立与多数跳跃射击高度，
并加回归用例 `test_boss_defeatable_by_standing_shots`（真打完整条血）。

### 15.5 关卡：从「随机撒」到「四段式 + 可验证约束」

生成器（`levels/generate.py`）按四段式节奏（开场 0–20% / 发展 20–80% / 高潮 80–95% / 收尾）
布置，并把设计约束**写成测试**，避免后续改动悄悄破坏可玩性：

| 测试 | 守住的约束 |
|---|---|
| `test_gaps_are_jumpable` | 任何缺口 ≤ 3 格（单跳水平距离 ≈197px ≈ 3.9 格） |
| `test_doors_have_clear_landing_zone` | 门前 3 格净空（防"落点在刺上"/"被怪堵门"） |
| `test_spawn_lane_is_clear` | 出生点左侧净空（防开局即死） |
| `test_walkers_stand_on_solid_ground` | 地面怪脚下必须有地（防掉出界） |
| `test_no_element_stacking` | 宝石/怪/箱子不得悬在地刺上方 |
| `test_early_levels_teach_without_enemies` | L1–L3 无敌人（introduce 阶段，先教机制） |
| `test_difficulty_ramps_up` | 发展关敌人数量单调不降 |
| `test_generation_is_deterministic` | 同种子结果一致（可复现构建） |

Boss 关参数（`BOSS_LEVELS` / `BOSS_THEME`）：L5 石 = 2 段、L10 霜 = 3 段、L15 幽 = 4 段；
三关主题分别是 stone / snow / purple，避免三关全落在同一底色。
