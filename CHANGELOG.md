# CHANGELOG

本仓库基于 [asdfd3/3d-memory-sea](https://github.com/asdfd3/3d-memory-sea)（MIT）修改。
下面记录相对原版的所有改动。

---

## [0.2.0] — 2026-11-01

### 新增：双星系

原来所有点在一片盘里。现在私聊和群聊分成两片独立星云：

- `layoutOne(points, cx, rOuter, arms, seed)` —— 每个星系独立算螺旋
- 私聊 3 条旋臂、半径 340，在左；群聊 2 条旋臂、半径 215，在右
- 两片之间的连线自动成为「桥」，视觉上自然连起来
- 星系标签用屏幕坐标偏移（`dy`），不跟着 3D 投影跑

**关键坑**：`TWIST`（螺旋缠绕强度）必须按圈数算 —— `TWIST = (2π × 圈数) / rOuter`。
写死一个常数会让小星系（半径 215）的螺旋退化成直线，因为 `dist × TWIST` 总转角太小。

### 新增：三视角

左下角三个按钮，点一下平滑飞过去（0.3 秒，每帧走 18%）：

| 按钮 | 效果 | URL 参数 |
|---|---|---|
| 家里 | 私聊星系放到最大居中 | `?view=home` |
| 外面 | 群聊星系放到最大居中 | `?view=out` |
| 全景 | 退回看两片 | 无 |

**关键坑**：`panX` 要取反。投影是 `wx = point.x + cam.panX`，左盘中心在 `-430`，
要把它移到屏幕中心，`panX` 必须是 `+430`。

### 新增：选中高亮

点中一颗星：

- 直接相连的星亮起（`neighborBoost = 1.35`，光晕 `glowR = base × 5`）
- 连线加粗到 `lineWidth = 2.2`，按类型上色（主题蓝 / 关键词青 / 时间橙）
- 其余点 dim 到 0.1
- 右侧详情卡列出「连着 N 颗星，最紧的 N 颗」及每条关联原因

### 新增：四块面板

| 面板 | 数据来源 | 说明 |
|---|---|---|
| 遗忘曲线 | 常量 | 约定永不衰减 / 事实 30 天 / 偏好 60 天 / 事件 7 天 |
| 上下文水位 | `meta.contextUsage.sessions` | 每个会话当前 token、剩余、预计多久压缩 |
| 服务器资源 | `meta.contextUsage.server` | 内存 / 磁盘 / 交换 / 负载，>65% 黄 >85% 红 |
| 每日花费 | `meta.contextUsage.usage` | 柱状图 + 数据截止时间 |

会话显示真名靠 `meta.sessionMap`（session → 会话 key）+ `meta.qqNames`（QQ 号 → 昵称）。
在用的会话排前面，历史遗留标「弃用」并置灰，**合计只算在用的**。

### 新增：`examples/export-example.py`

零依赖导出脚本，把任意 JSONL 对话转成 `data/my.json`：

- 字段别名表（时间认 `at/ts/time/timestamp`，正文认 `text/content/message/body`……）
- 秒级时间戳自动 ×1000
- 从 `isSelf` / `isOwner` / `sender` 三个线索推断谁在说话
- **兼容 BOM**（Windows 记事本的 UTF-8 文件带 BOM，用普通 utf-8 读会让第一行解析失败）

### 改进：`server.mjs` 热重载

原来数据文件换了必须重启进程（因为 `createSceneService` 在启动时就把数据读进了内存）。

现在每次请求先比一下 `fs.statSync(dataFile).mtimeMs`，变了就重建——**改完数据刷新页面就行**。

静态资源同时改成 `no-store`，改前端也不用硬刷新。

### 改进：视觉

- 深空背景：离屏预渲染（渐变 + 5 团星云 + 银河尘埃带 + 900 远星 + 420 近星），每帧只贴图
- 220 颗闪烁星每帧现算（`sin(t/2100 + phase)`）
- 盘面厚度随半径递减（`thick = 40 × (1 - t × 0.75)`），内圈隆起像核球

---

## 未改动的部分

- `src/memory-store.js` —— 长期记忆状态机，原样保留
- `src/memory-retrieve.js` —— 检索打分，原样保留
- `src/mind-sea.js` 的点/边/簇生成逻辑（只在 `layout` 部分接入了外部布局函数）
- `data/demo.json` —— 合成演示数据，原样保留
- `tests/` —— 三套单测原样保留，全部通过（10 + 16 + 11）

---

## 上游

```
bcc1bb6  feat: memory-sea 0.1.0 — 3D memory sea from long-term memory, chat and diary
```
