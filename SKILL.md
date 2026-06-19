---
name: dreamifly-batch
description: 批量调用 dreamifly.com 的生图 API，从提示词列表逐条生成并下载 AI 图片。当用户需要根据一批提示词批量生成图片、把提示词排进队列稍后统一出图、或自动下载 Dreamifly 生成的图片时使用。
---

# Dreamifly 批量生图

逐条读取 `prompts.txt` 里的提示词，调用 `https://dreamifly.com/api/generate` 生成图片，
下载到 `images/`，成功的提示词带时间戳和文件名移动到 `done.txt`，失败的保留在 `prompts.txt` 下次重试。

## 何时使用
- 用户有多条提示词需要批量出图
- 用户想把提示词排进队列、稍后或定时统一生成
- 用户要自动下载 Dreamifly 生成的图片

## 前置准备
1. **登录态 cookie**（`gpt-image-2` 模型必须登录）：把浏览器里 dreamifly.com 的整行 Cookie
   粘贴到 `config/cookie.txt`（参考 `config/cookie.txt.example`）。
2. **配置** `config/config.json`：模型、宽高、宽高比、批量数、重试次数、节流间隔等。
3. **提示词** `prompts.txt`：每行一个，`#` 开头的行和空行会被忽略。

## 运行
- 全部跑完：`./run.sh`
- 只跑前 N 条：`./run.sh 3`
- 直接调脚本：`python3 dreamify.py [N]`

## 工作流程（给 Claude）
当用户要批量生图时：
1. 检查 `config/cookie.txt` 是否存在且非空。若缺失，提示用户先按 `cookie.txt.example` 填入有效登录态，
   否则 `gpt-image-2` 会返回 401。
2. 把用户给的提示词逐行追加到 `prompts.txt`。
3. 按需调整 `config/config.json`（如分辨率、宽高比、模型、批量数）。
4. 运行 `./run.sh`（需要限量时带数量参数，如 `./run.sh 3`）。
5. 读 `run.log` 汇报结果：图片在 `images/`，成功记录在 `done.txt`，失败项仍在 `prompts.txt` 等待重试。

## 鉴权说明
- `Authorization: Bearer MD5(apiKey + 服务器时间串)`：脚本自动从 `/api/time` 取时间串自行计算。
- `apiKey` 是打进前端、发给每个浏览器的公开标识（`NEXT_PUBLIC_API_KEY`），并非私密凭证。
- `Cookie`：你的登录态，读自 `config/cookie.txt`（gpt-image-2 必须登录）。

## 错误处理
- `401` 未登录 / 登录失效 → 让用户更新 `config/cookie.txt` 后重跑。
- `402` 积分不足 → 提醒用户充值或更换账号。
- `429` 限流 → 脚本自动退避后重试。
- `5xx` 服务端错误 → 自动重试 `max_retries` 次。
