---
name: dreamifly-batch
description: 批量调用 dreamifly.com 的生图 API，从提示词列表逐条生成并下载 AI 图片。当用户需要根据一批提示词批量生成图片、把提示词排进队列稍后统一出图、自动下载 Dreamifly 生成的图片，或对一组提示词做不同宽高比/数量的批量出图时使用。
---

# Dreamifly 批量生图

逐条读取 `prompts.txt` 里的提示词，调用 `https://dreamifly.com/api/generate` 生成图片，
下载到 `images/`（并在旁边写 `.json` 边车记录 seed/参数），成功的提示词移动到 `done.txt`，
失败的保留在 `prompts.txt` 下次自动重试。

## 何时使用
- 用户有多条提示词需要批量出图
- 用户想把提示词排进队列、稍后或定时统一生成
- 用户要自动下载 Dreamifly 生成的图片
- 用户想对一批提示词指定不同宽高比 / 张数 / 模型

## 给 Claude 的执行 playbook
按顺序执行，不要跳步：

1. **先预检，绝不盲跑。** 运行 `python3 dreamify.py --check`：
   - 出现 `❌` → 停下，按提示修复（配置非法 / 无网络 / 队列为空）再继续。
   - 出现 cookie 为空的 `⚠️` → 告诉用户 gpt-image-2 必须登录，引导其把整行 Cookie 填进
     `config/cookie.txt`（见 `config/cookie.txt.example`），填好再继续。
2. **写入提示词。** 把用户给的每条提示词作为单独一行追加到 `prompts.txt`。
   需要个别参数时用内联语法（见下）。
3. **必要时预演。** 不确定解析是否符合预期，先 `python3 dreamify.py --dry-run`
   看每条会用什么 model / 宽高 / 张数 / seed，确认无误。
4. **批量较大时先确认。** 待处理条数多、或单条 `x张数` 较大时，先向用户报一下
   "共 N 条、预计生成 M 张" 再开跑。
5. **运行。** 全部跑 `./run.sh`；只跑前几条用 `./run.sh 3` 或 `python3 dreamify.py -n 3`。
6. **汇报结果。** 读 `run.log` 末尾，告诉用户成功几条、图片在 `images/`、失败项仍在
   `prompts.txt` 可重跑；如出现 401/402 按"错误处理"指引用户。

## 提示词内联参数
在 `prompts.txt` 一行内用 `|` 分隔，覆盖 `config.json`，可任意组合：

```
a neon cat on the moon | 16:9 | x2 | seed=123 | model=gpt-image-2 | 1024x768 | neg=blurry
```

| 片段 | 含义 |
|---|---|
| `16:9` | 宽高比 aspectRatio |
| `x2` | 本条生成 2 张 |
| `1024x768` | 宽 x 高 |
| `seed=123` | 固定随机种子（便于复现） |
| `model=...` | 覆盖模型 |
| `neg=...` | 负向提示词 |
| `img=URL,URL` | 参考图，图生图（实验性） |

也可用命令行做全局覆盖（优先级低于内联）：
`python3 dreamify.py --aspect 16:9 --batch 2 --model gpt-image-2`

## 命令速查
- `python3 dreamify.py --check` 只预检
- `python3 dreamify.py --dry-run` 解析预演，不调 API
- `./run.sh` / `./run.sh 3` 全部 / 前 3 条
- `python3 dreamify.py -n 3 --no-sidecar` 前 3 条且不写边车

## 鉴权说明
- `Authorization: Bearer MD5(apiKey + 服务器时间串)`：脚本自动从 `/api/time` 取时间串自行计算。
- `apiKey` 是打进前端、发给每个浏览器的公开标识（`NEXT_PUBLIC_API_KEY`），并非私密凭证。
- `Cookie`：用户的登录态，读自 `config/cookie.txt`（gpt-image-2 必须登录）。

## 示例对话
- 用户："帮我用这 5 个提示词各出一张图" → 先 `--check`，把 5 行写进 `prompts.txt`，`./run.sh`，读日志汇报。
- 用户："这条出 3 张、16:9" → 写成 `提示词 | 16:9 | x3`，再跑。
- 用户："怎么一直 401？" → 登录态失效，引导更新 `config/cookie.txt` 后重跑。

## 错误处理
- `401` 未登录 / 登录失效 → 让用户更新 `config/cookie.txt` 后重跑（脚本会立即停止，不浪费）。
- `402` 积分不足 → 提醒用户充值或更换账号（立即停止）。
- `429` 限流 → 脚本自动退避后重试。
- `5xx` 服务端错误 → 自动重试 `max_retries` 次。
