# dreamifly-batch

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![models](https://img.shields.io/badge/models-6%20image%20%2B%202%20video-orange)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)
![Codex](https://img.shields.io/badge/Codex-AGENTS.md-000000)
![License](https://img.shields.io/badge/License-MIT-yellow)

把一批提示词交给 [Dreamifly](https://dreamifly.com)，自动选择模型、校验成本、逐条生成并下载 **图片 / 视频**。
它既是一个零依赖 CLI，也是给 Cursor、Claude Code、Codex 和自定义 Agent 使用的批量媒体生成 Skill。

| | |
|---|---|
| 🌐 Dreamifly 官网 | https://dreamifly.com |
| 📦 本仓库 | https://github.com/shaozheng0503/dreamifly-batch |
| 🌍 English | [README_EN.md](./README_EN.md) |

> 对 AI 说"用这批提示词批量生图"或"用这张图生成视频"，Agent 会写队列、校验、估算、预演、确认高成本任务、运行并汇报结果。详见 [在 AI 里使用](#在-ai-里使用)。

## 解决什么问题

你给它：

- 一行一个 prompt 的 `prompts.txt`
- 或结构化的 `jobs.jsonl` / `.json` / `.yaml`
- 可选参考图、宽高比、数量、模型、视频秒数、分辨率

它会产出：

- 下载好的图片 / 视频文件，保存在 `images/`
- 同名 `.json` 边车，记录模型、seed、参数和来源
- `results.jsonl` 结构化结果，方便 Agent 汇报和自动化
- `failed.jsonl` 失败任务，可一条命令重新入队

它重点解决三件事：**批量排队、成本风险控制、Agent 可稳定复用**。

## ✨ 特性

- 🎨 **8 个模型 + 11 种风格**：6 生图 + 2 视频，叠加卡通/动漫/油画/像素/乐高… 风格，一处切换
- 📝 **队列式**：`prompts.txt` 每行一个提示词，逐条出图，`#` 注释、空行自动跳过
- 🎚️ **逐行内联参数**：`| model= | 16:9 | x2 | seed= | img= | secs= | res=`，每行独立覆盖
- 🛫 **开跑前预检**：`--check` 校验配置/模型/cookie/连通性，不让你白跑半批
- 🧰 **Agent 友好命令**：`--validate` / `--estimate` / `--summary` / `--retry-failed`
- 🧪 **零成本预演**：`--dry-run` 看清每条会怎么生成，不调 API、不花积分
- ⬇️ **自动下载 + 边车**：图片/视频落地，旁边写 `.json` 记录模型/seed/参数，可复现
- 📊 **结构化结果**：每条任务追加到 `results.jsonl`，方便 Agent 汇报、统计或接入后续自动化
- ♻️ **缓存去重**：默认按 `results.jsonl` 成功记录跳过重复任务，避免重复扣费
- ✅ **断点续跑**：成功移入 `done.txt`，失败留在 `prompts.txt` 下次自动重试
- 🤖 **AI 原生**：自带 `SKILL.md` / `AGENTS.md`，Claude Code、Codex、自定义 Agent 都能直接调用

## 适合 / 不适合

适合：

- 一次跑几十条图片 prompt，想自动下载、记录参数、失败续跑
- 给每条 prompt 指定不同模型、比例、数量、seed 或参考图
- 让 Agent 代你完成“写队列 → 校验 → 估算 → 预演 → 运行 → 汇报”
- 用低成本模型批量探索，再把少数结果升级到高质量模型
- AI 漫剧 / 短剧 / 分镜团队批量生成一组角色、场景、动作和情绪镜头

不适合：

- 只想让 AI 帮你润色 prompt，但不调用 Dreamifly 生成
- 想用 Midjourney、ComfyUI、fal.ai、Replicate 等其他平台
- 不希望本地保存 prompt、日志或生成文件
- 没有确认预算却想直接跑视频或高成本模型

---

## 目录

- [工作原理](#工作原理)
- [示例](#示例)
- [支持的模型](#支持的模型)
- [风格预设](#风格预设)
- [Skill 架构](#skill-架构)
- [典型联动案例](#典型联动案例)
- [准备：获取登录态 Cookie（最重要）](#准备获取登录态-cookie最重要)
- [快速开始](#快速开始)
- [输出与产物](#输出与产物)
- [切换模型教程](#切换模型教程)
- [提示词内联参数](#提示词内联参数)
- [JSONL / JSON / YAML 批任务](#jsonl--json--yaml-批任务)
- [命令行](#命令行)
- [配置文件](#配置文件)
- [在 AI 里使用](#在-ai-里使用)
  - [在 Cursor 里使用](#在-cursor-里使用)
  - [在 Claude Code 里使用](#在-claude-code-里使用)
  - [在 Codex 里使用](#在-codex-里使用)
  - [让你自己的 Agent 学会调用](#让你自己的-agent-学会调用)
- [鉴权原理](#鉴权原理)
- [常见问题与排错](#常见问题与排错)
- [注意事项](#注意事项)

---

## 工作原理

```mermaid
flowchart LR
    A["prompts.txt / jobs.jsonl<br/>每条一个任务"] --> B{"validate / estimate / dry-run<br/>模型 / 成本 / 参数预演"}
    B --> C{"预检 --check<br/>配置 / cookie / 连通性"}
    C -->|通过| D["逐条解析<br/>model= 路由 + 内联参数"]
    D -->|生图模型| E["POST /api/generate"]
    D -->|视频模型| F["POST /api/generate-video"]
    E --> G["下载到 images/<br/>+ .json 边车"]
    F --> G
    G --> H["results.jsonl / failed.jsonl<br/>成功缓存，失败可重试"]
```

---

## 示例

**文生图**（Wai-SDXL-V150 等）

| 提示词 | 出图 |
|---|---|
| `a serene japanese garden at sunset, koi pond, soft golden light` | ![sample](./docs/sample-japanese-garden.png) |

**图生图**（`img=` 传参考图，提示词 `transform ... into a snowy winter scene, frozen koi pond`）

| 参考图（输入） | 出图（输出） |
|---|---|
| ![ref](./docs/sample-japanese-garden.png) | ![i2i](./docs/sample-i2i-winter.png) |

**文生视频**（happyhorse-1.0 · `a cinematic timelapse of a city skyline at sunset` · 5s 720P，真实生成）

![t2v](./docs/sample-t2v-city-sunset.gif)

▶️ [完整视频 sample-t2v-city-sunset.mp4](./docs/sample-t2v-city-sunset.mp4)（1280×720 · h264 · 5s）

**图生视频**（Wan2.2-I2V-Lightning · 用上面那张庭院图 + `gentle wind, koi swimming, falling leaves` · 真实生成）

| 源图（输入） | 生成视频（输出） |
|---|---|
| ![ref](./docs/sample-japanese-garden.png) | ![i2v](./docs/sample-i2v-garden.gif) |

▶️ [完整视频 sample-i2v-garden.mp4](./docs/sample-i2v-garden.mp4)（1280×720 · h264）

---

## 支持的模型

平台「探索可用的 AI 模型」页面（随时用 `python3 dreamify.py --list-models` 拉取在线最新列表）：

![models-1](./docs/screenshot-models-1.png)
![models-2](./docs/screenshot-models-2.png)

### 生图（`/api/generate`）

| 模型 | 能力 | maxImg | steps | 需登录 | 约积分 |
|---|---|:-:|:-:|:-:|:-:|
| `Wai-SDXL-V150` | 文生图 · 动漫风格 | 0 | 20 | 否 | ~0.1 |
| `Wai-SDXL-V170` | 文生图 · 动漫风格 | 0 | 20 | 否 | ~0.1 |
| `Z-Image-Turbo` | 文生图 · 中文 · 快 | 0 | 10 | 否 | ~0.325 |
| `Qwen-Image-Edit` | 图生图 · 中文 | 3 | — | 否 | ~1.2 |
| `gpt-image-2` | 文生图 + 图生图 · 中文 | 3 | — | 是 | 顶级 |
| `nano-banana-2` | 文生图 + 图生图 · 中文 | 3 | — | 是 | ~25+ |

> `steps` 由脚本按模型自动填（Wai 必须 20、Z-Image-Turbo 10），无需手填。

### 生视频（`/api/generate-video`，单价高、较慢）

| 模型 | 模式 | 参数 | 约积分 |
|---|---|---|:-:|
| `Wan2.2-I2V-Lightning` | 图生视频（**需 1 张源图**） | — | ~200 |
| `happyhorse-1.0` | 文/图/多参考图生视频 + 视频编辑 | `secs`(3–15) `res`(720P/1080P) | ~150 起 |

视频模式按输入自动推导：无图→文生视频，1 张图→图生视频，多张图→多参考图生视频。

### 怎么选模型

| 需求 | 推荐模型 |
|---|---|
| 便宜批量动漫图 / 二次元 | `Wai-SDXL-V150` 或 `Wai-SDXL-V170` |
| 中文通用文生图、快速草图 | `Z-Image-Turbo` |
| 图生图编辑、加元素、改风格 | `Qwen-Image-Edit`（必须带 `img=`） |
| 高质量中文或复杂图像 | `gpt-image-2`；接受更高成本时可用 `nano-banana-2` |
| 图生视频且有 1 张源图 | `Wan2.2-I2V-Lightning` |
| 文生视频 / 多参考图生视频 | `happyhorse-1.0` |

> 成本阻断规则：单次积分消耗 ≥5 的模型运行前必须确认。视频、`nano-banana-2` 未经用户明确同意不要直接跑。

---

## 风格预设

平台「风格」下拉的 **11 种风格**都已接入，用 `style=` 选择（中英文名均可），脚本会把风格描述自动加到提示词前。

同一句提示词 `a cat sitting by a window` + 不同 `style=`（Z-Image-Turbo 真实生成）：

| 动漫 `anime` | 油画 `oil` | 街机像素 `pixel` |
|:---:|:---:|:---:|
| ![anime](./docs/style-anime.png) | ![oil](./docs/style-oil.png) | ![pixel](./docs/style-pixel.png) |
| **乐高 `lego`** | **线稿 `lineart`** | **Riso噪点 `riso`** |
| ![lego](./docs/style-lego.png) | ![lineart](./docs/style-lineart.png) | ![riso](./docs/style-riso.png) |

全部 11 种（`style=` 值，中英文都认；`--list-models` 也能查）：

| 值 | 风格 | 值 | 风格 |
|---|---|---|---|
| `cartoon` | 卡通 | `lego` | 乐高积木 |
| `anime` | 动漫 | `riso` | Riso噪点插画 |
| `oil` | 油画 | `realistic` | 现实风格 |
| `lineart` | 线稿 | `puppet` | 布偶风格 |
| `vector` | 矢量线条 | `emoji` | Emoji图标风格 |
| `pixel` | 街机像素 | | |

用法：`a cat by a window | style=oil | model=Z-Image-Turbo`（或全局 `--style oil`）。

---

## Skill 架构

这个仓库按“中心短，辐射厚”的方式组织 Agent 能力：

```text
SKILL.md                         # 短入口：触发边界、执行协议、安全规则
references/
├── model-selection.md            # 模型选择、参数、成本确认
├── output-contract.md            # 结果文件、汇报格式、隐私边界
├── gotchas.md                    # 真实失败经验：不要盲重试、不要泄露 Cookie
└── evals.md                      # 应该加载 / 不该加载 / 必须确认的测试用例
.cursor/skills/dreamifly-batch/   # Cursor 项目级 Skill
.claude/skills/dreamifly-batch/   # Claude Code 项目级 Skill
examples/prompts.jsonl            # 结构化队列示例
tests/                            # 解析、校验、估算的零 API 单元测试
```

`SKILL.md` 不塞满全部知识，只告诉 Agent 何时加载、按什么顺序执行、哪些风险必须停下。模型选择、失败经验、输出契约和 eval 放在 `references/`，需要时再读，减少上下文负担。

---

## 典型联动案例

`dreamifly-batch` 可以作为其他 Skills 的“媒体生成执行层”：上游 Skill 负责理解内容、制定风格、写 prompt 和 QA；本工具负责校验、估算、调用 Dreamifly、下载、记录和失败重试。

任何需要生图/生视频的 Skill，都可以复用这个模式：**它负责“该生成什么”，`dreamifly-batch` 负责“安全稳定地生成出来”。**

### 案例图 + 对应 Skill

这些图都由 `dreamifly-batch` 调用 Dreamifly 模型生成，展示的是“上游 Skill 决定表达，`dreamifly-batch` 执行生成”的交接方式。

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="./docs/skill-cases/case_xiaohei_gpt.png" alt="小黑正文配图" />
      <br />
      <strong>中文正文配图</strong>
      <br />
      上游：<a href="https://github.com/helloianneo/ian-xiaohei-illustrations">ian-xiaohei-illustrations</a>
      <br />
      位置：读取 shot list / prompt，用 <code>gpt-image-2</code> 一次生成最终正文配图。
    </td>
    <td width="50%" valign="top">
      <img src="./docs/skill-cases/case-social-card.png" alt="社交图文卡片链路" />
      <br />
      <strong>社交图文卡片</strong>
      <br />
      上游：<a href="https://github.com/op7418/guizang-social-card-skill">guizang-social-card-skill</a>
      <br />
      位置：缺少照片/截图/图库素材时，批量补齐封面图、章节图、隐喻图、背景图。
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="./docs/skill-cases/case-slide-deck.png" alt="PPT 配图链路" />
      <br />
      <strong>PPT / Slide Deck 配图</strong>
      <br />
      上游：<a href="https://github.com/jimliu/baoyu-design">baoyu-design</a>
      <br />
      位置：生成 PPT 页面所需配图，再由设计 Skill 插入 HTML/PPTX。
    </td>
    <td width="50%" valign="top">
      <img src="./docs/skill-cases/case-animation-video.png" alt="动画视频素材链路" />
      <br />
      <strong>动画视频素材</strong>
      <br />
      上游：<a href="https://github.com/jimliu/baoyu-design">baoyu-design</a>
      <br />
      位置：生成场景图、角色图、背景图，再进入时间轴动画和 MP4 导出。
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="./docs/skill-cases/ppt-generic/ppt-hero-ribbon.png" alt="网页 PPT 配图链路" />
      <br />
      <strong>网页 PPT 配图</strong>
      <br />
      上游：<a href="https://github.com/op7418/guizang-ppt-skill">guizang-ppt-skill</a>
      <br />
      位置：按 S22(21:9) / S15(多图格) 槽位比例生成封面主视觉、章节图、概念隐喻图，再填进单文件 HTML deck。
    </td>
    <td width="50%" valign="top">
      &nbsp;
    </td>
  </tr>
</table>

参考/对照项目：[`baoyu-image-gen`](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-image-gen) 是通用 AI 生图后端 Skill，支持多 provider / Codex CLI，可作为 `dreamifly-batch` 的架构对照。

完整记录见 [`docs/xiaohei-integration.md`](./docs/xiaohei-integration.md)。更多跨 Skill 定位见 [`docs/skill-ecosystem.md`](./docs/skill-ecosystem.md)。

以 `ian-xiaohei-illustrations` 为例：

```text
中文文章 / 观点
  ↓
ian-xiaohei-illustrations
  - 提炼认知锚点
  - 产出 shot list
  - 写小黑正文配图 prompt
  ↓
dreamifly-batch
  - 写入 jobs.jsonl
  - validate / estimate / dry-run / check
  - 调用 gpt-image-2 生成最终图
  - 写入 images/ + results.jsonl
  ↓
正文配图 / 图文卡片 / PPT / 发布 Skill
```

实测结论：

- `gpt-image-2` 最适合小黑正文配图“一次出图”，中文短标注、白底手绘、小黑动作和留白都更稳定。
- `Z-Image-Turbo` 适合低成本草稿探索，但容易加标题或写错字。
- `Qwen-Image-Edit` 可用于局部修复，但修图时必须显式带 `16:9`，否则可能裁切。

同理，像 [`baoyu-design`](https://github.com/jimliu/baoyu-design) 这类 PPT、动画视频、网站设计 Skill，也可以把 `dreamifly-batch` 当作本地图像生成后端：它决定哪一页/哪一幕需要配图，本工具负责批量生成、下载并通过 `results.jsonl` 把文件路径交回去。相比通用 image backend，`dreamifly-batch` 的优势是 Dreamifly 模型、成本确认、断点续跑和图片/视频统一落地。

社交图文类 Skill 也是同一模式：`guizang-social-card-skill` 决定内容品类、版式骨架、文字压图和渲染尺寸；`dreamifly-batch` 只在缺少合适素材时作为 AI 生图后端介入。这样上游 Skill 不需要自己维护模型调用、下载、失败重试和成本确认。

### AI 漫剧 / 短剧批量分镜

另一个很典型的使用场景是 AI 漫剧、短剧、动态漫画团队。工作人员可以让自己的 Agent 先拆分剧情和分镜，再把每个镜头写进 `jobs.jsonl`，最后交给 `dreamifly-batch` 排队生成：

```text
剧本 / 分镜表
  ↓
Agent
  - 拆镜头
  - 写角色设定
  - 写场景 prompt
  - 统一比例和风格
  ↓
dreamifly-batch
  - validate / estimate / dry-run / check
  - 批量生成角色近景、环境、动作镜头、情绪镜头
  - 下载到 images/ 或指定素材目录
  - results.jsonl 记录每个镜头的文件路径
  ↓
剪辑 / 动画 / 视频 Skill
```

示例：同一段 AI 漫剧的 4 个镜头，用低成本动漫模型批量生成。

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="./docs/skill-cases/ai-comic/ai_comic_ffaba646652c4c20.png" alt="AI 漫剧建立镜头" />
      <br />
      <strong>01 建立镜头</strong>
      <br />
      先交代角色所在的雨夜街巷和整体气氛。
    </td>
    <td width="50%" valign="top">
      <img src="./docs/skill-cases/ai-comic/ai_comic_eddd52baf16afe9b.png" alt="AI 漫剧角色近景" />
      <br />
      <strong>02 角色近景</strong>
      <br />
      用近景锁定主角表情和情绪状态。
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="./docs/skill-cases/ai-comic/ai_comic_a88cefdc57ceb6ba.png" alt="AI 漫剧动作冲突" />
      <br />
      <strong>03 动作冲突</strong>
      <br />
      生成追逐、战斗或事件推进的关键帧。
    </td>
    <td width="50%" valign="top">
      <img src="./docs/skill-cases/ai-comic/ai_comic_21819ba90b46fc14.png" alt="AI 漫剧情绪收束" />
      <br />
      <strong>04 情绪收束</strong>
      <br />
      用远景或静态镜头收束一组分镜。
    </td>
  </tr>
</table>

这种场景可以先用 `Wai-SDXL-V170` 低成本探索分镜方向；如果需要更强角色一致性、复杂构图或最终宣传图，再把少数关键镜头升级到 `gpt-image-2` / `nano-banana-2`，运行前按高成本规则确认。

---

## 准备：获取登录态 Cookie（最重要）

部分模型（`gpt-image-2`、`nano-banana-2`）和**所有视频模型**都要求登录。脚本通过你浏览器的
**登录态 Cookie** 来鉴权。免登录模型（Wai、Z-Image-Turbo、Qwen-Image-Edit）可跳过这一步。

> 鉴权用的 `Authorization` token 脚本会**自动计算**，你**不需要**手动获取——你唯一要提供的就是这个 Cookie。

**第 1 步｜注册并登录**
打开 https://dreamifly.com ，用左下角的 GitHub / 微信 等方式登录。登录后左下角会显示你的用户名和**积分**
（例如截图里的 `2961`）。积分不足时生图/视频会返回 402。

**第 2 步｜打开浏览器开发者工具**
在 dreamifly.com 页面按 `F12`（Mac：`Cmd+Option+I`），切到 **Network（网络）** 标签页。

**第 3 步｜触发一个请求并复制 Cookie**
1. 刷新页面，或点一下「快速生成 / AI 广场」让页面发请求。
2. 在 Network 列表里点任意一个发往 `dreamifly.com` 的请求（如 `models`、`time`）。
3. 右侧找到 **Headers → Request Headers（请求标头）**，找到 **`Cookie:`** 这一行。
4. **复制 `Cookie:` 后面的一整行内容**（很长，包含 `session=...; token=...` 等多段）。

> 备选：开发者工具 **Application（应用）/ 存储 → Cookies → https://dreamifly.com**，也能看到各项；
> 但 Network 里的 `Cookie` 请求头是已拼好的整行，直接复制最省事。

**第 4 步｜写入 `config/cookie.txt`**
```bash
cp config/cookie.txt.example config/cookie.txt
```
编辑 `config/cookie.txt`，把复制的整行粘进去（**不要**带前面的 `Cookie:` 字样），保存。
以 `#` 开头的行会被忽略，脚本取第一条非注释行作为 Cookie。

**第 5 步｜验证**
```bash
python3 dreamify.py --check
```
看到 `✅ 已加载 cookie（N 字符）` 和 `✅ 连通正常` 即可。Cookie 会过期，遇到 401 重新取一次即可。

⚠️ Cookie 等同于你的登录凭证。它已被 `.gitignore` 排除，**切勿提交或分享**。

---

## 快速开始

```bash
git clone https://github.com/shaozheng0503/dreamifly-batch.git
cd dreamifly-batch

# 1) （需登录的模型才需要）按上文填好 config/cookie.txt
cp config/cookie.txt.example config/cookie.txt   # 然后编辑填入

# 2) 看有哪些模型
python3 dreamify.py --list-models

# 3) 写提示词（每行一个，可指定模型）
echo "anime girl with flowers | model=Wai-SDXL-V150" >> prompts.txt

# 4) 校验、估算、预演、预检
python3 dreamify.py --validate
python3 dreamify.py --estimate
python3 dreamify.py --dry-run
python3 dreamify.py --check

# 5) 跑（全部 / 只跑前 3 条）
./run.sh
./run.sh 3
```

结果在 `images/`，成功记录在 `done.txt`，结构化记录写入 `results.jsonl`，失败的留在 `prompts.txt` 下次自动重试。

---

## 输出与产物

每次成功生成会落地两个文件：媒体本体 + 同名 `.json` 边车（记录参数，便于复现/检索）。

```
images/
├── 20260619_122149_masterpiece_1girl_..._0.png    # 图片
├── 20260619_122149_masterpiece_1girl_..._0.json   # 边车
├── 20260619_125051_gentle_wind_koi_..._0.mp4      # 视频
└── 20260619_125051_gentle_wind_koi_..._0.json
done.txt       # 成功记录：时间 \t 提示词 \t 文件名
results.jsonl  # 每条任务一行 JSON：状态 / 模型 / 参数 / 文件 / 错误
failed.jsonl   # 失败任务 JSONL，可用 --retry-failed 重新入队
run.log        # 运行日志（含每条的模型/seed/错误）
```

边车 `.json` 示例（图生视频）：
```json
{
  "type": "video",
  "prompt": "gentle wind, koi swimming slowly, falling leaves, cinematic",
  "model": "Wan2.2-I2V-Lightning",
  "videoMode": "image-to-video",
  "width": 1280, "height": 720, "aspectRatio": "16:9",
  "source_image": "docs/sample-japanese-garden.png",
  "generated_at": "2026-06-19T12:50:51"
}
```

`results.jsonl` 示例：
```json
{"status":"success","type":"image","model":"Z-Image-Turbo","prompt":"a neon cat","files":["20260619_122149_a_neon_cat_0.png"],"cost_estimate":"~0.325"}
```

> `prompts.txt`、`images/`、`done.txt`、`results.jsonl`、`failed.jsonl`、`run.log` 都已被 `.gitignore` 排除，不会误传你的提示词与产物。示例队列见 `prompts.example.txt`。

---

## 切换模型教程

有三种方式指定模型，**优先级：内联参数 > 命令行 flag > config.json**。

**方式一：在某一行提示词里临时指定（最灵活，可逐行不同模型）**
```text
# prompts.txt —— 每行可以用不同模型
masterpiece, 1girl, sakura | model=Wai-SDXL-V150
a photo of a cat, 中文也支持 | model=Z-Image-Turbo
edit this, add snow | model=Qwen-Image-Edit | img=ref.png
a cat running | model=Wan2.2-I2V-Lightning | img=source.png
city timelapse | model=happyhorse-1.0 | secs=5 | res=720P
```

**方式二：本次运行全局指定（不写进文件）**
```bash
python3 dreamify.py --model Wai-SDXL-V170 --aspect 16:9
```

**方式三：改默认模型（长期生效）**
编辑 `config/config.json` 的 `"model"` 字段，例如改成 `"Z-Image-Turbo"`。

> 模型名大小写不敏感（`wai-sdxl-v150` 也行）。拿不准就先 `--list-models`，再 `--dry-run` 预演确认路由。

---

## 提示词内联参数

在 `prompts.txt` 一行内用 `|` 分隔，逐条覆盖配置，可任意组合。`#` 开头的行和空行会被忽略（可用于注释/暂存）。

| 片段 | 含义 | 适用 |
|---|---|---|
| `model=...` | 选择模型（生图或视频） | 全部 |
| `style=...` | 风格预设（cartoon/anime/oil/pixel/lego… 或中文名，见[风格预设](#风格预设)） | 全部 |
| `16:9` | 宽高比，脚本会**自动换算出匹配的宽高**再发（这样比例才真正生效） | 全部 |
| `1024x768` | 显式宽 x 高，**优先级高于比例**，原样使用 | 全部 |

> **关于宽高比**：平台按 `width × height` 出图，单给 `aspectRatio` 而宽高仍是方形会出方图。
> 因此脚本在你只给比例（如 `16:9`）时，会按所选模型的原生像素预算换算出匹配宽高（如 gpt-image-2 → 1536×864）。
> 平台预设比例：`16:9 21:9 4:3 3:2 5:4 1:1 4:5 2:3 3:4 9:16 9:21`；需要精确像素时用 `1024x768` 这种显式写法。
| `x2` | 生成 2 张（≤4） | 生图 |
| `seed=123` | 固定随机种子 | 生图 |
| `steps=20` | 采样步数（一般自动） | 生图 |
| `neg=...` | 负向提示词 | 全部 |
| `img=路径或URL` | 参考图/源图，逗号分隔多张（本地/URL/data，自动转 base64） | 图生图 / 图生视频 |
| `secs=5` | 视频时长秒（happyhorse 3–15） | 生视频 |
| `res=720P` | 视频分辨率（happyhorse：720P / 1080P） | 生视频 |

---

## JSONL / JSON / YAML 批任务

除了 `prompts.txt`，也可以用结构化批任务：

```jsonl
{"prompt":"a neon cat in rain","model":"Z-Image-Turbo","aspectRatio":"16:9","batch_size":1}
{"prompt":"edit this, add snow","model":"Qwen-Image-Edit","images":["ref.png"]}
```

```bash
python3 dreamify.py --prompts jobs.jsonl --validate
python3 dreamify.py --prompts jobs.jsonl --estimate --json
python3 dreamify.py --prompts jobs.jsonl --name-template "{model}_{date}_{index}_{hash}.{ext}"
```

`.json` 支持 `{ "jobs": [...] }` 或数组；`.yaml/.yml` 支持常见的 `prompts:` 列表格式（零依赖轻量解析）。

---

## 命令行

```bash
python3 dreamify.py --list-models           # 列出平台所有可用模型（在线）
python3 dreamify.py --check                  # 只做开跑前预检
python3 dreamify.py --validate               # 校验队列，不调用 API
python3 dreamify.py --estimate               # 估算成本，不调用 API
python3 dreamify.py --dry-run               # 解析预演，不调用 API
python3 dreamify.py --summary               # 汇总 results.jsonl
python3 dreamify.py --retry-failed          # 把 failed.jsonl 追加回 prompts.txt
python3 dreamify.py                          # 跑完队列全部
python3 dreamify.py 3                         # 只跑前 3 条（等价 -n 3）
python3 dreamify.py --model Wai-SDXL-V150 --aspect 16:9   # 全局覆盖
python3 dreamify.py --no-cache              # 忽略缓存，强制重新生成
python3 dreamify.py --name-template "{model}_{date}_{index}_{hash}.{ext}"
python3 dreamify.py --no-sidecar             # 不写 .json 边车
python3 dreamify.py --results-file out.jsonl # 自定义结构化结果路径
python3 dreamify.py --prompts other.txt --images-dir out/   # 自定义路径
```

---

## 配置文件

`config/config.json`：

| 字段 | 说明 | 默认 |
|---|---|---|
| `model` | 默认模型 | `gpt-image-2` |
| `width` / `height` | 生图宽高（与 `aspectRatio` 一致时直接用；不一致则以比例换算） | `1024` / `1024` |
| `aspectRatio` | 生图宽高比（驱动出图形状，脚本据此换算宽高） | `1:1` |
| `batch_size` | 每条生成几张（≤4） | `1` |
| `steps` | 采样步数（null=按模型自动） | `null` |
| `negative_prompt` | 负向提示词 | `""` |
| `delay_between_seconds` | 每条之间节流间隔 | `5` |
| `max_retries` | 单条失败最大重试 | `2` |
| `request_timeout_seconds` | 生图请求超时 | `300` |
| `video_width` / `video_height` | 视频宽高 | `1280` / `720` |
| `video_aspectRatio` | 视频宽高比 | `16:9` |
| `video_seconds` | 视频默认时长（happyhorse） | `5` |
| `video_resolution` | 视频默认分辨率 | `720P` |
| `video_timeout_seconds` | 视频请求超时（排队可能久，建议留足） | `1800` |

---

## 在 AI 里使用

本仓库自带：

- 根目录 `SKILL.md`：Cursor / Claude Code / 其他 Agent 都能读的主 playbook
- `.cursor/skills/dreamifly-batch/`：Cursor 项目级 Skill
- `.claude/skills/dreamifly-batch/`：Claude Code 项目级 Skill
- `AGENTS.md`：Codex / 通用 Agent 指令

核心很简单：**让 AI 把提示词写进 `prompts.txt` 或 `jobs.jsonl`，按 `--validate → --estimate → --dry-run → --check` 检查，再运行 `python3 dreamify.py`，最后读 `--summary` / `results.jsonl` / `run.log` 汇报。**

### 在 Cursor 里使用

本仓库已内置项目级 Cursor Skill：`.cursor/skills/dreamifly-batch/SKILL.md`。在 Cursor 打开本仓库后，可以直接说：

> 用这 3 个提示词各出一张便宜动漫图：樱花少女、赛博城市、雪山

Cursor 会按 Skill 指引：写入队列、校验、估算、预演、低成本模型直接运行；遇到视频或 `nano-banana-2` 这类高成本任务会先停下来征求确认。

如果想安装成全局 Cursor Skill：

```bash
./install.sh cursor     # ~/.cursor/skills/dreamifly-batch
./install.sh .cursor    # 当前项目 .cursor/skills/dreamifly-batch
```

### 在 Claude Code 里使用

**安装为技能（推荐，可被自动调用）：**
```bash
./install.sh            # 安装到 ~/.claude/skills/dreamifly-batch（用户级，全局可用）
./install.sh .claude    # 或安装到 当前项目/.claude/skills（仅本项目）
```
安装后在 Claude Code 里自然语言触发即可：

> 👤：用这 3 个提示词各出一张动漫图：樱花少女、赛博城市、雪山
> 🤖：（自动）写入 `prompts.txt`（带 `model=Wai-SDXL-V150`）→ `--validate` → `--estimate` → `--dry-run` → `--check` → `./run.sh` → 读 `results.jsonl` 汇报：成功 3/3，图片在 `images/`

也可以不安装，直接 clone 后对 Claude 说：「用这个目录里的 `dreamify.py` 批量生图」，Claude 会读 `SKILL.md` 按流程执行。

### 在 Codex 里使用

OpenAI Codex CLI 会自动读取仓库根目录的 **`AGENTS.md`**。本仓库已内置，所以：

```bash
git clone https://github.com/shaozheng0503/dreamifly-batch.git
cd dreamifly-batch
codex          # 在仓库目录里启动 codex
```
然后直接说：

> 用 happyhorse-1.0 把 "a sunset timelapse over the city" 生成一个 5 秒 720P 视频

Codex 会参照 `AGENTS.md`：先把提示词（带 `model=` / `secs=` / `res=`）写进 `prompts.txt`，再运行
`--validate`、`--estimate`、`--dry-run`、`--check`。视频较贵，Codex 会在真实运行前提示大致积分消耗并等你确认。确认后运行 `./run.sh`，最后读 `results.jsonl` 和 `run.log` 告诉你视频在 `images/`。

### 让你自己的 Agent 学会调用

本工具对 Agent 没有任何特殊要求——**任何能"读写文件 + 跑 shell 命令"的 Agent 都能用**。三步即可教会它：

1. **喂说明书**：把 `SKILL.md`（或 `AGENTS.md`）的内容作为 system prompt / 工具说明给你的 Agent。
2. **给它两个动作**：
   - 写文件：把用户的提示词按内联语法追加到 `prompts.txt`
   - 跑命令：`python3 dreamify.py`（先 `--validate` / `--estimate` / `--dry-run` / `--check`）
3. **让它读结果**：优先运行 `python3 dreamify.py --summary` 或解析 `results.jsonl`，必要时结合 `run.log` 末尾与 `done.txt`，把成功/失败和文件路径回报给用户。

最小「工具定义」示例（任意框架通用）：
```json
{
  "name": "dreamifly_batch_generate",
  "description": "批量调用 Dreamifly 生图/生视频。先把提示词写入 prompts.txt 或 jobs.jsonl（可用 model=/16:9/x2/img=/secs=/res= 内联参数），再运行脚本。",
  "command": "cd /path/to/dreamifly-batch && python3 dreamify.py",
  "notes": "先 --validate、--estimate、--dry-run、--check；视频(model=Wan2.2-I2V-Lightning/happyhorse-1.0)单价高，运行前先向用户确认。"
}
```
Python 里直接调用也可以：`subprocess.run(["python3", "dreamify.py", "--check"])`。

---

## 鉴权原理

- `Authorization: Bearer MD5(apiKey + 服务器时间串)`：脚本自动从 `/api/time` 取时间串并自行计算，**无需手动获取**。
- `apiKey` 是打进前端、发给每个浏览器的**公开标识**（`NEXT_PUBLIC_API_KEY`），并非私密凭证，随仓库附带。
- `Cookie`：**你个人的登录态**，读自 `config/cookie.txt`（已被 `.gitignore` 排除，请勿提交）。

---

## 常见问题与排错

| 现象 | 原因 | 解决 |
|---|---|---|
| `HTTP 401` / `LOGIN_REQUIRED` | cookie 缺失或已过期 | 按[获取 Cookie](#准备获取登录态-cookie最重要)重新取一次写入 `config/cookie.txt` |
| `HTTP 402` / `INSUFFICIENT_POINTS` | 积分不足 | 充值，或改用免登录模型（`Wai-SDXL-V150` / `Z-Image-Turbo`） |
| `HTTP 400 Invalid steps` | 该模型对步数有硬性要求 | 脚本已按模型自动填；自定义用 `steps=20`/`steps=30`（Wai）、`10`/`20`（Z-Image-Turbo） |
| 视频很慢 / `Connection reset` | 视频排队耗时长（可能 10 分钟以上） | 已默认 `video_timeout_seconds=1800`；失败项会保留，直接重跑即可 |
| 图生图 / 图生视频"没吃参考图" | 模型不支持 i2i 或忘了 `img=` | i2i 用 `Qwen-Image-Edit`/`gpt-image-2`/`nano-banana-2`；i2v 用 `Wan2.2-I2V-Lightning` 且必须 `img=` |
| 模型名报错 / 路由不对 | 名字拼错 | `--list-models` 查准确 id（大小写不敏感），再 `--dry-run` 预演确认 |
| 中文提示词效果差 | 模型不支持中文 | 用 `Z-Image-Turbo` / `Qwen-Image-Edit` / `gpt-image-2` / `nano-banana-2` |
| 参考图被拒 | 单图超过 10MB | 压缩到 10MB 以内；最多 9 张 |

> 拿不准时的万能流程：`--list-models` → 写好 `prompts.txt` → `--validate` → `--estimate` → `--dry-run` → `--check` → 正式跑。

---

## 注意事项

- ⚠️ **不要把 `config/cookie.txt` 提交到任何公开仓库**——它等同于你的登录凭证。
- 💸 **视频很贵**：`Wan2.2-I2V-Lightning` 约 200 积分/次、`happyhorse-1.0` 约 150 起，生成也较慢；脚本对视频**不自动重试**以免重复扣费。
- 图生图（`img=`）已实测：参考图可为本地文件 / URL / `data:`URI，自动转无前缀 base64；单图 ≤10MB、最多 9 张、需登录。
- 积分不足（402）或登录失效（401）时脚本会立即停止并说明原因，已成功的不受影响。
- 失败的提示词会保留在 `prompts.txt`，直接重跑即可续跑。
- 失败任务也会写入 `failed.jsonl`，可用 `python3 dreamify.py --retry-failed` 重新入队。

## License

[MIT](./LICENSE)
