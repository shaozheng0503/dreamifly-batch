---
name: dreamifly-batch
description: 批量调用 dreamifly.com 的生图/生视频 API，从提示词列表逐条生成并下载图片或视频，支持平台全部模型。当用户需要批量生成图片、图生图编辑、文生视频、图生视频、把提示词排队统一出图、或对一批提示词指定不同模型/宽高比/数量时使用。
---

# Dreamifly 批量生图 / 生视频

逐条读取 `prompts.txt` 里的提示词，调用 dreamifly.com 生成图片（`/api/generate`）或视频（`/api/generate-video`），
下载到 `images/`（并写 `.json` 边车记录模型/seed/参数），成功的移动到 `done.txt`，失败的保留下次重试。

## 何时使用
- 批量生图 / 图生图（编辑、风格化、加元素）
- 文生视频 / 图生视频 / 多参考图生视频
- 把一批提示词排队，逐条用不同模型/参数出图

## 支持的模型（用 `python3 dreamify.py --list-models` 查在线最新）

**生图**：
- `Wai-SDXL-V150` / `Wai-SDXL-V170`：文生图，动漫风格，便宜（~0.1 积分），免登录
- `Z-Image-Turbo`：文生图，中文友好，快，便宜（~0.325），免登录
- `Qwen-Image-Edit`：图生图（需 `img=`），中文，免登录
- `gpt-image-2`：文+图生图，顶级，**需登录**
- `nano-banana-2`：文+图生图，中文，**需登录**，较贵

**生视频**（单价高、较慢）：
- `Wan2.2-I2V-Lightning`：图生视频，**必须 1 张源图**（~200 积分）
- `happyhorse-1.0`：文/图/多参考图生视频，`secs`(3–15) `res`(720P/1080P)（~150 起）

## 模型选择默认策略

- 便宜批量动漫图 / 二次元：优先 `Wai-SDXL-V150` 或 `Wai-SDXL-V170`
- 中文通用文生图、快速草图：优先 `Z-Image-Turbo`
- 图生图编辑、加元素、改风格：优先 `Qwen-Image-Edit`，必须带 `img=`
- 高质量中文或复杂图像：优先 `gpt-image-2`；用户明确要高质量且接受高成本时可用 `nano-banana-2`
- 图生视频且有 1 张源图：用 `Wan2.2-I2V-Lightning`
- 文生视频 / 多参考图生视频：用 `happyhorse-1.0`

不确定有哪些模型或平台模型有更新时，先运行 `python3 dreamify.py --list-models`。

## Agent 执行 playbook
按顺序执行，不要跳步：

1. **先预检，绝不盲跑。** `python3 dreamify.py --check`：
   - `❌` → 停下修复（配置非法 / 无网络 / 队列空）。
   - cookie 为空的 `⚠️` 且要用 gpt-image-2 / nano-banana-2 / 任意视频 → 引导用户把整行 Cookie
     填进 `config/cookie.txt`（见 `config/cookie.txt.example`）。
2. **选模型 + 写提示词。** 根据需求选模型，把每条提示词作为单独一行写入 `prompts.txt`，用内联语法带参数。
   - 不确定有哪些模型 → 先 `python3 dreamify.py --list-models`。
3. **校验 + 预估 + 预演。**
   - `python3 dreamify.py --validate` 校验模型、参考图、视频源图、高成本项。
   - `python3 dreamify.py --estimate` 汇总模型分布与预计积分。
   - `python3 dreamify.py --dry-run` 看每条解析成 生图/视频、什么模式、什么参数。
4. **成本确认（阻断规则）。** 单次积分消耗 ≥5 的运行前必须告知用户并征求同意：
   - 视频（Wan2.2-I2V-Lightning ~200、happyhorse-1.0 ~150+）、`nano-banana-2`（~25+）必须确认。
   - 用户未明确同意前，必须停止，不能运行真实生成命令。
   - 便宜的 Wai/Z-Image-Turbo/Qwen-Image-Edit（≤2 积分）可直接跑。
5. **运行。** `./run.sh`（或 `./run.sh 3` / `python3 dreamify.py -n 3`）。
6. **汇报。** 优先运行/读取 `python3 dreamify.py --summary`、`results.jsonl` 和 `run.log` 末尾：成功/失败几条、文件在 `images/`。
   - 失败项保留在 `prompts.txt`，可直接重跑续跑。
   - 若是 401/402 致命错误，**先**引导用户更新 `config/cookie.txt` 或充值，**再**重跑——不要盲目重跑。

## 提示词内联参数
一行内用 `|` 分隔，覆盖 `config.json`。`#` 开头的行和空行会被忽略（可用于暂存/注释，不会被处理）。

```
# 生图
a neon cat | model=Z-Image-Turbo | 16:9 | x2 | seed=123 | neg=blurry
edit this, add snow | model=Qwen-Image-Edit | img=ref.png
# 生视频
a cat running | model=Wan2.2-I2V-Lightning | img=source.png
city timelapse | model=happyhorse-1.0 | secs=5 | res=720P
```

| 片段 | 含义 |
|---|---|
| `model=...` | 选择模型（生图或视频） |
| `style=...` | 风格预设：cartoon/anime/oil/lineart/vector/pixel/lego/riso/realistic/puppet/emoji（或中文名），作为前缀加到提示词 |
| `16:9` / `1024x768` | 宽高比（自动换算匹配宽高，比例才真生效）/ 显式宽x高（优先） |
| `x2` | 生成 2 张（≤4，生图） |
| `seed=123` / `steps=20` | 种子 / 步数（步数一般自动） |
| `neg=...` | 负向提示词 |
| `img=路径或URL` | 参考图/源图，逗号分隔多张，本地/URL/data 自动转 base64 |
| `secs=5` | 视频时长秒（happyhorse 3–15） |
| `res=720P` | 视频分辨率（happyhorse：720P / 1080P） |

> `steps` 由脚本按模型自动填（Wai 必须 20，Z-Image-Turbo 10），无需手填。
> 视频模式自动推导：无图→文生视频，1 图→图生视频，多图→多参考图生视频。Wan2.2 必须给 1 张源图。

## 命令速查
- `python3 dreamify.py --list-models` 在线列模型
- `python3 dreamify.py --check` 只预检
- `python3 dreamify.py --validate` 校验队列，不调 API
- `python3 dreamify.py --estimate` 估算成本，不调 API
- `python3 dreamify.py --dry-run` 解析预演，不调 API
- `python3 dreamify.py --summary` 汇总 `results.jsonl`
- `python3 dreamify.py --retry-failed` 把 `failed.jsonl` 追加回 `prompts.txt`
- `./run.sh` / `./run.sh 3` 全部 / 前 3 条
- `python3 dreamify.py --results-file out.jsonl` 指定结构化结果文件
- `python3 dreamify.py --prompts jobs.jsonl` 使用 JSONL/JSON/YAML 批任务
- `python3 dreamify.py --name-template "{model}_{date}_{index}_{hash}.{ext}"` 自定义输出文件名
- 默认会按 `results.jsonl` 成功记录缓存去重；需要强制重生时加 `--no-cache`

## 错误处理
- `401` 未登录/失效 → 更新 `config/cookie.txt` 后重跑（脚本立即停止，不浪费）。
- `402` 积分不足 → 提醒充值/换号（立即停止）。
- `400 Invalid steps` → 该模型对步数有要求；脚本已按注册表自动处理，如自定义请用 `steps=`。
- `429` 限流 → 生图自动退避重试；**视频不自动重试**（单价高，避免重复扣费）。

## 鉴权
- `Authorization: Bearer MD5(apiKey + 服务器时间串)`，脚本自动从 `/api/time` 取时间串计算。
- `apiKey` 是公开前端标识（`NEXT_PUBLIC_API_KEY`），非私密。
- `Cookie`：用户登录态，读自 `config/cookie.txt`。
- ⚠️ **`config/cookie.txt` 是用户私密登录态，等同于登录凭证——绝对不要打印、外传、写入聊天回复、或提交到 git。** 汇报预检结果时只说"已加载 N 字符"，不要复述内容。

## 隐私与产物
- `prompts.txt`、`done.txt`、`run.log`、`results.jsonl`、`images/*` 都可能包含用户私密内容或生成产物，默认不提交。
- `failed.jsonl` 记录失败项，方便 `--retry-failed` 续跑，也默认不提交。
- 示例提示词放在 `prompts.example.txt`；真实队列写入 `prompts.txt`。
- `results.jsonl` 每行是一条结构化结果，包含 prompt、模型、状态、参数摘要、输出文件和错误信息，适合 Agent 汇报或接入后续自动化。
