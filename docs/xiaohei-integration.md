# 典型联动案例：ian-xiaohei-illustrations + dreamifly-batch

这个案例记录如何把 [`ian-xiaohei-illustrations`](https://github.com/helloianneo/ian-xiaohei-illustrations) 这类“内容理解 / 配图策划 Skill”和 `dreamifly-batch` 串起来。

核心结论：当一个 Skill 需要生图或生视频，但自己不想维护模型调用、下载、成本确认、失败重试和结果汇报时，可以把 `dreamifly-batch` 当作 **媒体生成执行层**。

## 两个 Skill 的分工

`ian-xiaohei-illustrations` 负责上游判断：

- 阅读中文文章、帖子、博客、Notion 文档或方法论内容。
- 提炼适合配图的认知锚点。
- 输出 shot list。
- 规定画面风格：16:9、纯白背景、手绘线稿、小黑 IP、少量红橙蓝中文批注。
- 用 QA checklist 判断是否像 PPT、是否太满、是否小黑只是装饰、是否有标题或错字。

`dreamifly-batch` 负责执行：

- 把每张图的 prompt 写成 `prompts.txt` 或 `jobs.jsonl`。
- 运行 `--validate`、`--estimate`、`--dry-run`、`--check`。
- 调用 Dreamifly 模型生成图片或视频。
- 下载到 `images/`。
- 写 `.json` 边车、`results.jsonl`、`failed.jsonl`。
- 按成本规则阻断高成本任务。

## 推荐链路

```text
文章 / 观点 / 方法论
  ↓
ian-xiaohei-illustrations
  - 提炼认知锚点
  - 产出 shot list
  - 写单张生图 prompt
  ↓
dreamifly-batch
  - 写入 jobs.jsonl
  - validate / estimate / dry-run / check
  - 调用 Dreamifly 生成
  - 下载和记录结果
  ↓
ian-xiaohei QA
  - 检查标题、错字、小黑动作、留白、PPT 感
  ↓
最终插图
```

## 模型选择建议

### 最终正文配图：优先 `gpt-image-2`

如果目标是“一次出图尽量过 QA”，推荐直接用 `gpt-image-2`。

实测表现：

- 更能遵守 16:9、白底、手绘、留白。
- 更能让小黑承担核心动作。
- 中文短标注更稳定。
- 更少出现左上角标题。
- 不容易把英文单词写错。

适合：

- 正式文章正文配图。
- 对风格一致性和一次成功率有要求。
- 不想走“便宜模型初稿 + 编辑修复”的两步流程。

注意：

- `gpt-image-2` 需要登录 Cookie。
- 属于高质量/高成本模型，真实运行前必须明确确认。

### 批量草稿探索：可用 `Z-Image-Turbo`

`Z-Image-Turbo` 适合低成本探索画面隐喻和构图方向。

实测优点：

- 能抓住白底、小黑、橙色路径、怪诞隐喻。
- 速度快、成本低。

实测问题：

- 容易自动加左上角标题。
- 可能出现中文或英文错字。
- 可能偏卡通。

### 局部修复：`Qwen-Image-Edit`

如果已经有不错的图，只需要去标题、改局部文字或轻微修复，可以用 `Qwen-Image-Edit`。

关键 gotcha：

- 修图时必须显式带 `16:9`，否则可能被重生成 1:1 或裁切。

## JSONL 示例

`jobs.jsonl`：

```jsonl
{"prompt":"Create one standalone 16:9 horizontal Chinese article illustration, Ian Xiaohei style. Pure white background, lots of blank space, minimalist black hand-drawn line art with slightly wobbly pen lines. Required character: 小黑, a small solid-black odd creature with white dot eyes and tiny thin legs. 小黑 must operate the core mechanism, not decorate the scene. Topic: Agent 放大能力差距. Core idea: Agent amplifies clear goals and also amplifies chaos. Composition: a strange low-tech amplification machine. 小黑 pulls a heavy lever. On the left, a neat paper ball and a tangled paper ball enter. On the right, the neat input becomes one clean orange path, while the messy input becomes a larger black knot with a small red warning triangle. Chinese handwritten labels: 清晰 / 混乱 / 放大 / 更乱. No title, no English text, no top-left heading, no PPT infographic look.","model":"gpt-image-2","aspectRatio":"16:9","batch_size":1}
```

运行：

```bash
python3 dreamify.py --prompts jobs.jsonl --validate
python3 dreamify.py --prompts jobs.jsonl --estimate
python3 dreamify.py --prompts jobs.jsonl --dry-run
python3 dreamify.py --prompts jobs.jsonl --check
python3 dreamify.py --prompts jobs.jsonl --name-template "xiaohei_{model}_{date}_{index}_{hash}.{ext}"
python3 dreamify.py --summary
```

## 实测记录

### `Z-Image-Turbo`

输出：

```text
images/xiaohei_test_Z_Image_Turbo_20260619_0_ba1b397dc4be06f0.png
```

结论：

- 画面方向成立。
- 但出现左上角标题。
- 英文 `Agent` 被写成类似 `Aget`。
- 更适合草稿探索，不适合作为最终图首选。

### `Qwen-Image-Edit`

输出：

```text
images/xiaohei_edit_16x9_test_Qwen_Image_Edit_20260619_0_c944f43cb26225ae.png
```

结论：

- 可以去掉标题。
- 显式带 `16:9` 后能保留横版。
- 不适合作为默认链路，因为多一步编辑会增加复杂度和成本。

### `gpt-image-2`

输出：

```text
images/xiaohei_gpt_test_gpt_image_2_20260619_0_2e769c693ff1911d.png
```

结论：

- 一次出图质量最好。
- 中文短标注可读。
- 小黑承担核心动作。
- 没有多余左上角标题。
- 更适合作为小黑正文配图最终生成模型。

## 可复用模式

这个案例不只适用于小黑配图。任何上游 Skill 只要需要生图/生视频，都可以采用同样模式：

```text
上游 Skill
  - 负责理解任务
  - 负责风格、结构、prompt、QA
  ↓
dreamifly-batch
  - 负责模型调用
  - 负责成本确认
  - 负责下载、记录、失败重试
  ↓
下游 Skill 或用户
  - 负责排版、发布、演示、归档
```

适合接入的上游 Skill：

- 文章配图 Skill
- 小红书图文 Skill
- PPT / 报告 Skill
- 动画 / 视频 Skill
- 营销素材 Skill
- 课程讲义 Skill

## 写给 Agent 的调用原则

- 不要让上游 Skill 自己盲跑图像模型。
- 先让上游 Skill 产出 prompt 队列和 QA 标准。
- 再让 `dreamifly-batch` 负责真实生成。
- 如果模型成本 ≥5，必须先问用户。
- 最终汇报必须从 `results.jsonl` 或 `--summary` 读取。
- 生成结果再交给上游 Skill 做 QA 或交给下游 Skill 做排版/发布。

## 结论

`ian-xiaohei-illustrations` 是 `dreamifly-batch` 的高匹配上游案例：它把“该画什么、怎么画、怎么判断好坏”说清楚，`dreamifly-batch` 把“怎么稳定生成、下载、记录、重试”做扎实。

这正是 `dreamifly-batch` 的生态位：不是取代其他创作 Skills，而是成为它们可调用的媒体生成执行层。
