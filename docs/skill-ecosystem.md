# Dreamifly Skill 生态位与联动记录

这份文档记录 `dreamifly-batch` 作为 Agent Skill 的生态位，以及它如何和其他 Skills 串联。它不是执行规则，不会被默认加载；需要讨论生态、集成或产品定位时再读。

## 一句话定位

`dreamifly-batch` 是一个 **Agent 可调用的批量媒体生成后端**：负责把 prompt 队列安全地转成图片/视频文件、结构化结果和可重试记录。

它不负责设计排版、剪辑包装、社交媒体发布或复杂视觉叙事，而是给这些上层 Skills 提供稳定素材和产物。

## 生态位

在 Agent 工作流里，它更像“生成资产层”，不是“最终表达层”：

```text
用户目标
  ↓
内容 / 设计 / 发布类 Skill
  ↓
dreamifly-batch 生成素材或视频片段
  ↓
images/ + sidecar JSON + results.jsonl
  ↓
其他 Skill 继续排版、动效、导出、发布
```

它的核心价值：

- **批量执行**：一批 prompt 可以逐条生成、下载、记录。
- **成本控制**：`--validate`、`--estimate`、高成本阻断，避免 Agent 误扣费。
- **结构化交接**：`results.jsonl` 让下游 Skill 可以读取文件路径、模型、参数和错误。
- **失败可恢复**：`failed.jsonl` + `--retry-failed` 支持重试。
- **跨 Agent 可用**：Cursor、Claude Code、Codex、自定义 Agent 都能用普通文件和 CLI 调用。

## 适合联动的 Skill 类型

### 设计 / 动画 / PPT Skill

典型代表：`baoyu-design`

联动方式：

1. `dreamifly-batch` 批量生成背景图、角色图、产品图或视频片段。
2. 下游设计 Skill 读取 `images/` 和 `results.jsonl`。
3. 设计 Skill 把素材放进 HTML、PPT、动画或品牌展示。
4. 设计 Skill 继续导出为 HTML、PPTX、PDF 或 MP4。

适合场景：

- 先批量生成插画，再制作图文卡片。
- 先生成场景图，再制作产品动画。
- 先生成封面/背景，再制作 PPT 或 landing page。

### 社交媒体发布 Skill

典型代表：小红书、Twitter/X、公众号发布类 Skill

联动方式：

1. `dreamifly-batch` 生成图片或短视频素材。
2. 内容 Skill 改写标题、正文、标签和平台文案。
3. 发布 Skill 上传素材并发布。

适合场景：

- 批量生成小红书封面图。
- 为文章批量生成配图。
- 为活动、餐饮、课程、产品发布生成视觉素材。

### 社交图文卡片 Skill

典型代表：`guizang-social-card-skill`

[`guizang-social-card-skill`](https://github.com/op7418/guizang-social-card-skill) 的核心不是“画一张图”，而是把文章、截图、产品笔记、字幕或照片变成小红书 3:4 图文组图、公众号 21:9 + 1:1 封面对。它内置：

- Editorial / Swiss 两套视觉系统。
- 小红书 3:4、公众号 21:9、公众号 1:1 三种画板。
- 28 个版式骨架。
- 10 套主题色板。
- 图片来源工作流：用户图优先；无图时图库；必要时 AI 生图。
- HTML/CSS 单文件排版，再用 Playwright 渲染 PNG。
- 版式 validator 检查溢出、字号、footer 碰撞、密度等问题。

它和 `dreamifly-batch` 的分工非常清晰：

```text
文章 / 文案 / 截图 / 产品笔记
  ↓
guizang-social-card-skill
  - 判断内容品类
  - 选择 Editorial / Swiss
  - 选择 3:4 / 21:9 / 1:1 版式骨架
  - 规划每页需要什么图
  ↓
缺少合适图片时
  ↓
dreamifly-batch
  - 批量生成封面图 / 章节图 / 隐喻图 / 背景图
  - 写入 images/ + results.jsonl
  ↓
guizang-social-card-skill
  - 读取图片
  - 压图、遮罩、人脸/主体避让
  - 渲染 PNG 组图
```

推荐链路：

1. 先让 `guizang-social-card-skill` 做 Intake、内容拆页、风格选择和版式规划。
2. 如果用户没有照片/截图，或图库找不到合适图，让它输出每页所需的图像 prompt。
3. 把 prompt 写成 `jobs.jsonl`。
4. 用 `dreamifly-batch` 运行 `--validate`、`--estimate`、`--dry-run`、`--check`。
5. 对正式发布图，优先用 `gpt-image-2`；对草稿探索，可用低成本模型。
6. `guizang-social-card-skill` 从 `results.jsonl` 读取图片路径，插入 HTML 卡片。
7. 用它自己的 render/validator 流程输出最终 PNG。

为什么适配：

- 社交卡片 Skill 需要“内容理解 + 排版系统 + 图源策略”，不应该自己维护所有模型调用细节。
- `dreamifly-batch` 正好提供批量生成、成本阻断、下载落地、失败重试和结构化结果。
- 对小红书/公众号这类最终 PNG 交付，`results.jsonl` 是很好的中间交接格式。

注意：

- 图文卡片的主质量来自版式、文案压缩、真实照片/截图和文字落点，不是盲目 AI 生图。
- `dreamifly-batch` 只负责补齐缺失素材，不负责替代 `guizang-social-card-skill` 的排版和 QA。
- 如果是正式发布封面，优先 `gpt-image-2`，少走编辑修复。

### 内容生产 Skill

典型代表：写作、文章转卡片、营销素材、课程资料 Skill

联动方式：

1. 内容 Skill 先拆解文章或大纲，提取每张图的主题。
2. `dreamifly-batch` 把主题队列生成视觉素材。
3. 内容 Skill 组合图文，生成最终稿。

适合场景：

- 文章配图。
- 课程讲义插图。
- 营销活动视觉素材。
- 多版本广告素材探索。

### 中文正文配图 Skill

典型代表：`ian-xiaohei-illustrations`

这是目前最适合与 `dreamifly-batch` 联动的 Skill 类型之一。它负责：

- 阅读中文文章或观点。
- 提炼 4-8 个适合配图的认知锚点。
- 产出 shot list。
- 规定稳定视觉风格：16:9、白底、手绘、小黑 IP、少量红橙蓝中文批注。
- 用 QA checklist 检查是否像 PPT、是否太满、是否小黑只是装饰、是否出现错误标题或错字。

`dreamifly-batch` 负责：

- 把每张图的 prompt 变成 JSONL 队列。
- 用 `gpt-image-2` 直接生成最终质量图，尽量一次通过 QA。
- 必要时用便宜模型探索构图，或用图生图编辑模型修补标题、错字或局部问题。
- 把结果写入 `images/`、sidecar JSON 和 `results.jsonl`。

推荐链路：

```text
文章 / 观点
  ↓
ian-xiaohei-illustrations 提炼 shot list + 单图 prompt
  ↓
dreamifly-batch 用 gpt-image-2 生成最终图
  ↓
ian-xiaohei QA checklist 检查
  ↓
必要时再用 Qwen-Image-Edit 修局部问题
  ↓
assets/<article-slug>-illustrations/
```

实测结论：

- `Z-Image-Turbo` 可以抓住白底、小黑、橙色路径、怪诞隐喻和中文标注，适合低成本批量出初稿。
- 容易出现的问题：左上角自动加标题、英文或中文错字、局部过于卡通。
- `Qwen-Image-Edit` 可以修复“去掉标题”这类局部问题。
- 修图时必须显式带 `16:9`，否则可能被重生成 1:1 或裁切。
- `gpt-image-2` 一次出图质量明显更好，更适合作为小黑正文配图最终生成模型。

实测产物：

```text
images/xiaohei_test_Z_Image_Turbo_20260619_0_ba1b397dc4be06f0.png
images/xiaohei_edit_16x9_test_Qwen_Image_Edit_20260619_0_c944f43cb26225ae.png
images/xiaohei_gpt_test_gpt_image_2_20260619_0_2e769c693ff1911d.png
```

### 数据 / 研究 Skill

联动方式：

1. 研究 Skill 产出结构化洞察、场景或关键词。
2. `dreamifly-batch` 生成可视化隐喻图、封面图或报告插图。
3. 报告 Skill 整合为 PDF、PPT 或网页。

适合场景：

- 调研报告封面。
- 趋势图文解释。
- 概念视觉化。

### AI 漫剧 / 短剧 / 分镜生产

这类团队经常需要批量生产一组角色、场景、动作和情绪镜头。`dreamifly-batch` 的队列模式很适合做这一层：

```text
剧本 / 分镜表
  ↓
Agent 拆镜头并写 prompts
  ↓
dreamifly-batch 批量生成素材
  ↓
剪辑 / 动画 / 视频 Skill 继续处理
```

适合场景：

- 批量探索一集短剧的关键帧。
- 为同一角色生成不同景别：建立镜头、近景、动作、情绪收束。
- 先用低成本动漫模型探索，再把关键镜头升级到高质量模型。
- 给后续动画、剪辑、图生视频 Skill 提供素材。

实测示例：

```text
docs/skill-cases/ai-comic/ai_comic_ffaba646652c4c20.png
docs/skill-cases/ai-comic/ai_comic_eddd52baf16afe9b.png
docs/skill-cases/ai-comic/ai_comic_a88cefdc57ceb6ba.png
docs/skill-cases/ai-comic/ai_comic_21819ba90b46fc14.png
```

## 与 baoyu-design 的实测链路

已实测 `baoyu-design` 的视频导出链路：

1. 拉取 `JimLiu/baoyu-design`。
2. 读取 `skills/baoyu-design/SKILL.md`。
3. 读取 `built-in-skills/animated-video.md`。
4. 读取 `built-in-skills/export-as-video.md`。
5. 安装并构建 `agents/gen-video`。
6. 创建一个 2 秒 timeline HTML。
7. 启动本地 HTTP 服务。
8. 用 Playwright 驱动 headless Chromium 逐帧截图。
9. 通过 ffmpeg 输出 MP4。

实测输出：

```text
/tmp/baoyu-video-test/out/baoyu-design-chain-test.mp4
```

输出参数：

- 2 秒
- 12 fps
- 24 帧
- MP4
- 文件约 28 KB

测试中出现 `capture_mode_off` warning，因为测试页是手写最小 timeline bridge，不是 `baoyu-design` 官方 `animations.jsx` Stage。真实使用官方 Stage 时，`?capture` 会自动隐藏播放器外壳和 letterboxing。

## 作为 baoyu-design 的图像生成后端

`baoyu-design` 已支持在制作 PPT、动画视频或网站时调用画图 Skill 配图。它的上游生态里也有 `baoyu-image-gen` / `baoyu-imagine` 这类 image backend：内容 Skill 负责决定哪里需要图、图要表达什么，image backend 负责真实生成图片。

`dreamifly-batch` 可以承担同样位置，但生态位略有不同：

```text
baoyu-design / slide deck / animated video
  ↓
需要封面图、章节图、场景图、产品图、插画
  ↓
写入 jobs.jsonl
  ↓
dreamifly-batch
  - validate
  - estimate
  - dry-run
  - check
  - 生成并下载图片
  ↓
baoyu-design 读取 images/ 和 results.jsonl
  ↓
插入 PPT / HTML / 动画视频
  ↓
导出 PPTX / PDF / MP4
```

和 `baoyu-image-gen` / `baoyu-imagine` 的差异：

- `baoyu-image-gen` 更像多 provider 的通用图像生成后端，覆盖 OpenAI、Google、DashScope、Replicate、Codex CLI 等。
- `dreamifly-batch` 更像 Dreamifly 专用的本地批量生成层，重点是队列、成本确认、下载、断点续跑、`results.jsonl` 交接和视频模型。
- 如果用户已经在 Dreamifly 有积分或 Cookie，`dreamifly-batch` 能让 baoyu-design 直接用 Dreamifly 模型生产素材。
- 如果用户需要 GPT Image 2 且希望稳定落地文件，`dreamifly-batch + gpt-image-2` 是很直接的路径。

推荐用法：

1. 让 baoyu-design 先完成 PPT / 动画 / 网站结构。
2. 对每个需要配图的位置生成单图 prompt。
3. 写入 `jobs.jsonl`，用 `model=gpt-image-2` 或低成本模型探索。
4. 运行 `dreamify.py --prompts jobs.jsonl --validate --estimate --dry-run --check`。
5. 成本确认后运行生成。
6. baoyu-design 从 `results.jsonl` 读取文件路径并插入页面。

注意：

- 高成本模型仍必须先确认。
- `results.jsonl` 可能包含 prompt 和素材路径，不要公开提交。
- 如果是 PPT 最终稿，建议优先 `gpt-image-2`，减少后期修图。
- 如果只是寻找配图方向，可以先用低成本模型批量探索。

## 与 guizang-ppt-skill 的联动（网页 PPT 配图后端）

[`guizang-ppt-skill`](https://github.com/op7418/guizang-ppt-skill) 生成的是**单文件 HTML 横向翻页 PPT**（电子杂志风 / 瑞士国际主义风两套）。它的版式系统里有明确的**图片槽位**——`S22 Image Hero`（21:9 顶部主视觉）、`S15/S16` 多图格——并自带 `image-prompts.md` 描述配图类型、比例和提示词规则。

也就是说，它天然需要一个"按槽位比例稳定出图"的后端。这正是 `dreamifly-batch` 的位置：

```text
内容 / 大纲
  ↓
guizang-ppt-skill
  - 选风格(杂志风 / 瑞士风)、主题色、版式
  - 决定哪一页需要图、放进哪个槽位、要什么比例(S22 → 21:9 / S15 → 统一 21:9 或 16:10)
  - 写出每张图的主题 prompt
  ↓
缺图时
  ↓
dreamifly-batch
  - 写入 jobs.jsonl(带 aspectRatio 对齐槽位)
  - validate / estimate / dry-run / check
  - 批量生成并下载到 images/
  - results.jsonl 交回文件路径
  ↓
guizang-ppt-skill
  - 按 {页号}-{语义}.png 命名放进 images/
  - 填进 S22 / S15 槽位,渲染最终 deck
```

分工要点：

- **比例必须先定再生成**：S22 主视觉用 `21:9`，S15/S16 同组多图统一 `21:9` 或 `16:10`。在 `jobs.jsonl` 里用 `aspectRatio` 对齐，`dreamifly-batch` 会按模型像素预算换算匹配宽高。
- **草稿用便宜模型探索，终稿再升级**：先用 `Z-Image-Turbo` 低成本试构图方向；选定后对正式主视觉用 `gpt-image-2`，运行前按高成本规则确认。
- **PPT skill 不必自己维护模型调用**：它只管"该画什么、放哪、什么比例"，`dreamifly-batch` 管"安全生成、下载、记录、重试"。

`jobs.jsonl` 示例（按 PPT 槽位对齐比例）：

```jsonl
{"prompt":"ultra-wide minimalist abstract hero, flowing klein-blue light ribbons over clean off-white, geometric Swiss feel, lots of negative space, no text, no logo","model":"Z-Image-Turbo","aspectRatio":"21:9","negative_prompt":"text, watermark, logo, people"}
{"prompt":"clean isometric illustration of a minimalist desk with a laptop, muted palette with one blue accent, no text, no brand","model":"Z-Image-Turbo","aspectRatio":"21:9","negative_prompt":"text, watermark, logo, brand"}
{"prompt":"a single blue paper origami boat on a vast off-white surface, soft shadow, calm metaphor, no text","model":"Z-Image-Turbo","aspectRatio":"16:9","negative_prompt":"text, watermark, logo, people"}
```

实测样例（`Z-Image-Turbo` 真实生成，均为**无文字、无品牌、无敏感信息的通用占位配图**，仅用于演示"PPT skill 槽位 ← dreamifly-batch 出图"的交接，不代表任何具体 deck 内容）：

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="./skill-cases/ppt-generic/ppt-hero-ribbon.png" alt="PPT 封面主视觉占位图(21:9)" />
      <br /><strong>S22 封面主视觉 · 21:9</strong><br />抽象主视觉，铺满顶部 hero 槽位。
    </td>
    <td width="50%" valign="top">
      <img src="./skill-cases/ppt-generic/ppt-section-desk.png" alt="PPT 章节配图占位图(21:9)" />
      <br /><strong>章节 / 案例配图 · 21:9</strong><br />中性场景图，进 S15/S16 图片格。
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="./skill-cases/ppt-generic/ppt-concept-boat.png" alt="PPT 概念隐喻占位图(16:9)" />
      <br /><strong>概念隐喻 · 16:9</strong><br />单一隐喻图，给观点页做视觉锚点。
    </td>
    <td width="50%" valign="top">
      &nbsp;
    </td>
  </tr>
</table>

脱敏注意：

- 真实 deck（含人名、内部规划、业务数据、产品截图等）**不要**生成进配图、也不要把这类图提交到公开仓库。
- 仓库里只放**无关紧要的通用占位图**作演示；正式配图在本地生成、随 deck 一起管理，按 `dreamifly-batch` 的隐私规则处理 `results.jsonl` 与 `images/`。
- 需要图里带具体文字/数据时，优先在 PPT skill 的 HTML 文本层写，而不是让模型把文字画进图片（容易错字，也更难脱敏）。

## 推荐的跨 Skill 工作流

### 图像素材 → 动画视频

```text
用户：做一个 10 秒动画，主题是赛博城市里的蓝色纸船

Agent:
1. 用 dreamifly-batch 生成 3-5 张候选场景图
2. 读取 results.jsonl，选择成功文件
3. 调用 baoyu-design 的 animated-video 流程
4. 把生成图作为 ImageSprite / 背景素材
5. 预览 HTML 动画
6. 调用 export-as-video 导出 MP4
7. 汇报 MP4 路径和素材来源
```

### 图片素材 → 图文卡片

```text
用户：帮我把这篇文章做成小红书图文

Agent:
1. 内容 Skill 提取 6-9 张卡片主题
2. dreamifly-batch 批量生成封面和插图
3. 设计 Skill 排版成 3:4 图文卡片
4. 发布 Skill 上传到平台
```

### 研究报告 → PPT

```text
用户：把这份趋势报告做成演示稿，需要一些概念图

Agent:
1. PPT Skill 拆分页面结构
2. dreamifly-batch 生成封面、章节图和隐喻插图
3. PPT Skill 把图片放入版式
4. 导出 HTML/PPTX/PDF
```

## 不建议的联动方式

- 不要让 `dreamifly-batch` 直接承担排版、动效或发布，它的边界是生成和下载媒体。
- 不要让上游 Skill 绕过 `--validate` / `--estimate` 直接运行高成本任务。
- 不要把 `config/cookie.txt` 交给其他 Skill。
- 不要把 `results.jsonl` 当成公开数据，它可能包含私密 prompt。
- 不要把视频模型当作可自动重试的普通任务。

## 产品化方向

`dreamifly-batch` 适合成为其他 Skills 的“媒体生成插件层”：

- 对人：用户只知道“批量生成素材”，不用理解 Dreamifly API。
- 对 Agent：提供稳定 CLI、结构化输入输出、失败恢复和成本确认。
- 对其他 Skill：提供可读取的本地媒体文件和 metadata。

长期可以考虑：

- 增加 `--export-manifest`，生成下游 Skill 更容易读取的素材清单。
- 增加 `--select-best` 或人工选择流程，把多张候选图筛给设计 Skill。
- 增加 `workflow examples`，记录 Dreamifly + baoyu-design、小红书、PPT 的完整示例。
- 增加 `references/composition.md`，只在用户明确要跨 Skill 串联时读取。

## 结论

`dreamifly-batch` 的生态位不是“全能创作 Skill”，而是 **可靠、低门槛、可审计的媒体生成资产层**。

它和设计、内容、发布、报告类 Skills 的关系是互补：上游 Skill 定义表达目标，下游 Skill 负责包装和交付，`dreamifly-batch` 负责把视觉素材稳定生产出来。
