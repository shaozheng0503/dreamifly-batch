# AGENTS.md — Dreamifly 批量生图/生视频

本仓库是一个批量调用 [Dreamifly](https://dreamifly.com) 的命令行工具，也是给 AI Agent（Codex / Claude Code /
自定义 Agent）使用的。当用户要求"批量生图 / 图生图 / 文生视频 / 图生视频"时，按下面的流程操作本工具。

仓库：https://github.com/shaozheng0503/dreamifly-batch ｜ 官网：https://dreamifly.com

## 工具是什么
- `python3 dreamify.py`：逐条读取 `prompts.txt` 的提示词，调用 Dreamifly 生成图片/视频，
  下载到 `images/`，成功的移到 `done.txt`，失败的留在 `prompts.txt`。纯 Python 标准库，零依赖。

## 执行流程（务必按顺序）
1. **预检**：`python3 dreamify.py --check`
   - 有 `❌` 就停下修复（配置非法 / 无网络 / 队列空）。
   - cookie 为空且要用 `gpt-image-2` / `nano-banana-2` / 任意视频模型时，引导用户把浏览器里
     dreamifly.com 的整行 Cookie 填进 `config/cookie.txt`（见 README「获取登录态 Cookie」）。
2. **选模型 + 写提示词**：把用户每条提示词作为单独一行写入 `prompts.txt`，用内联语法带参数。
   不确定有哪些模型先 `python3 dreamify.py --list-models`。
3. **预演**：`python3 dreamify.py --dry-run` 确认每条解析成 生图/视频、模式、参数是否符合预期。
4. **成本确认（重要）**：涉及视频或贵模型（`nano-banana-2`）时，先告知用户大致积分消耗并征求同意。
5. **运行**：`./run.sh`（或 `./run.sh 3` / `python3 dreamify.py -n 3`）。
6. **汇报**：读 `run.log` 末尾与 `done.txt`，回报成功/失败数量与文件路径。

## 模型速查
- 生图：`Wai-SDXL-V150`/`Wai-SDXL-V170`（动漫·便宜·免登录）、`Z-Image-Turbo`（中文·快·免登录）、
  `Qwen-Image-Edit`（图生图·免登录）、`gpt-image-2`（顶级·需登录）、`nano-banana-2`（中文·需登录·贵）。
- 视频（贵、慢、不自动重试）：`Wan2.2-I2V-Lightning`（图生视频·必须 1 张源图 ~200 分）、
  `happyhorse-1.0`（文/图/多参考图生视频 ~150 起）。

## 内联参数（在 prompts.txt 一行内用 | 分隔）
`model=` 选模型 ｜ `16:9` 宽高比(自动换算匹配宽高) ｜ `1024x768` 显式宽高(优先) ｜ `x2` 张数(≤4) ｜ `seed=` ｜ `steps=`（一般自动）｜
`neg=` 负向 ｜ `img=路径或URL`（参考图/源图，逗号分隔多张）｜ `secs=` 视频秒(3–15) ｜ `res=720P|1080P`

示例：
```
masterpiece, 1girl, sakura | model=Wai-SDXL-V150
edit this, add snow | model=Qwen-Image-Edit | img=ref.png
a cat running | model=Wan2.2-I2V-Lightning | img=source.png
city timelapse | model=happyhorse-1.0 | secs=5 | res=720P
```

## 注意
- `config/cookie.txt` 是用户私密登录态，**不要打印、提交或外传**。
- 401=登录失效（让用户更新 cookie 重跑）；402=积分不足；视频不自动重试。
