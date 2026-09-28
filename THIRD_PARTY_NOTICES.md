# 第三方素材与许可 · Third-Party Notices

本仓库的**代码**以 [MIT](LICENSE) 授权。
随包分发的**素材**各自遵循其原始许可，与 MIT 条款相互独立 —— 见下表。

> 原则：仓库内不放任何来源不明或许可未确认的素材。
> 判定逻辑见 `src/zero_brother/resources/manifest.py` 的 `LICENSE_WHITELIST`，
> 并有测试 `tests/test_content.py::test_every_sound_maps_to_existing_file` 与
> `test_resources.py::test_license_classification` 守护。

## 清单

| 路径 | 内容 | 许可 | 来源 |
| --- | --- | --- | --- |
| `assets/vendor/kenney_new_platformer/` | 角色（idle/walk/jump/duck/hit/climb）、敌人（9 种）、地形自动拼接块、道具（宝石/金币/门/梯子/弹簧/单向平台/砖墙）、视差背景、平台音效 | **CC0 1.0 Universal**（公有领域） | [Kenney.nl — New Platformer Pack](https://kenney.nl/assets/new-platformer-pack) |
| `assets/vendor/kenney_interface_sounds/` | UI 音效（点击/确认/返回/出错/滚动等） | **CC0 1.0 Universal** | [Kenney.nl — Interface Sounds](https://kenney.nl/assets/interface-sounds) |
| `assets/vendor/noto_sans_sc/` | Noto Sans SC 中文字体（子集化：862 KB / 3,964 字） | **SIL Open Font License 1.1** | [Google Noto Fonts](https://fonts.google.com/noto/specimen/Noto+Sans+SC) |

各目录内均保留了上游的 `License.txt` / `LICENSE.txt` 全文，再分发时请一并保留。

## CC0 1.0 要点

素材可自由用于商业/非商业用途，无需署名。Kenney 的署名请求（非强制）：
<https://kenney.nl/> 。本项目的版权页因此仍标注了素材来源。

## SIL OFL 1.1 要点

字体可自由使用、修改、再分发（含嵌入与子集化），但：

- 再分发时必须保留版权声明与许可全文；
- 若对字体本身做了修改并再分发，**不得使用保留字体名（Reserved Font Name）**。

本项目仅做了子集化（裁剪字符集），未修改字形。子集化过程可用
`tools/build_font_subset.py` 复现。

## 已排除的素材

以下目录**不在仓库内**（见 `.gitignore`），且渲染层已完全不引用它们：

| 路径 | 原因 |
| --- | --- |
| `assets/img/`、`assets/wav/`、`assets/video/` | 旧工程遗留素材，**来源与许可不明** |
| `assets/font/font.ttf`（datouren） | 旧占位字体，**非 OFL**，已被上表中的 Noto Sans SC 取代 |

历史与替换记录见 [`docs/ASSETS.md`](docs/ASSETS.md) 与
[`docs/ASSETS_EXTERNAL.md`](docs/ASSETS_EXTERNAL.md)。
