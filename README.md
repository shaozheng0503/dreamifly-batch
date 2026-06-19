# dreamifly-batch

从一个提示词列表，批量调用 [dreamifly.com](https://dreamifly.com) 的生图 API 逐条生成并下载图片。
排队、节流、自动重试、断点续跑——把提示词写进 `prompts.txt`，跑一条命令就行。

> 本仓库同时是一个 **[Claude Code](https://claude.com/claude-code) Skill**：把目录放进 `.claude/skills/`，
> Claude 就能在你说"批量生图"时自动调用它。详见下方 [作为 Claude Code Skill 使用](#作为-claude-code-skill-使用)。

## 功能

- 📝 **队列式**：`prompts.txt` 每行一个提示词，从上往下逐条生成。
- ⬇️ **自动下载**：返回的图片落到 `images/`，文件名带时间戳 + 提示词摘要。
- ✅ **断点续跑**：成功的提示词移到 `done.txt`，失败的留在 `prompts.txt` 下次自动重试。
- 🔁 **重试与退避**：`429` 限流自动退避，`5xx` 自动重试，`401/402` 立即停止并提示原因。
- 🐌 **节流**：可配置每条之间的间隔，避免触发限流。
- ⏰ **可定时**：`run.sh` 自动切到脚本目录，可直接挂到 cron。

## 目录结构

```
.
├── dreamify.py            # 主脚本
├── run.sh                 # 启动器（手动 / cron 都可）
├── prompts.txt            # 提示词队列（每行一个，# 注释）
├── config/
│   ├── config.json        # 生图参数
│   └── cookie.txt.example # 登录态模板（复制为 cookie.txt 后填写）
├── images/                # 生成的图片（git 忽略）
├── done.txt               # 成功记录（git 忽略，运行后生成）
├── run.log                # 运行日志（git 忽略，运行后生成）
└── SKILL.md               # Claude Code Skill 定义
```

## 快速开始

```bash
git clone https://github.com/shaozheng0503/dreamifly-batch.git
cd dreamifly-batch

# 1) 填登录态：复制模板后粘贴你浏览器里 dreamifly.com 的整行 Cookie
cp config/cookie.txt.example config/cookie.txt
#   编辑 config/cookie.txt，删掉注释，粘贴 Cookie

# 2) 写提示词：每行一个
echo "a cyberpunk city street in the rain, neon reflections, cinematic" >> prompts.txt

# 3) 跑起来（全部 / 只跑前 3 条）
./run.sh
./run.sh 3
```

> **获取 Cookie**：浏览器登录 dreamifly.com → 开发者工具(F12) → Network → 刷新后点任意请求
> → Request Headers 里复制 `Cookie` 整行。`gpt-image-2` 必须登录，否则返回 401。

## 配置 `config/config.json`

| 字段 | 说明 | 默认 |
|---|---|---|
| `model` | 生图模型 | `gpt-image-2` |
| `width` / `height` | 图片宽高（像素） | `1024` / `1024` |
| `aspectRatio` | 宽高比 | `1:1` |
| `batch_size` | 每条提示词生成几张 | `1` |
| `steps` | 采样步数（null 为不传） | `null` |
| `negative_prompt` | 负向提示词 | `""` |
| `delay_between_seconds` | 每条之间的节流间隔（秒） | `5` |
| `max_retries` | 单条失败的最大重试次数 | `2` |
| `request_timeout_seconds` | 单次请求超时（秒） | `300` |

## 鉴权说明

- `Authorization: Bearer MD5(apiKey + 服务器时间串)`：脚本自动从 `/api/time` 取时间串并自行计算 token。
- `apiKey` 是打进前端、发给每个浏览器的**公开标识**（`NEXT_PUBLIC_API_KEY`），并非私密凭证，因此随仓库附带。
- `Cookie`：**你个人的登录态**，读自 `config/cookie.txt`。该文件已被 `.gitignore` 排除，**请勿提交**。

## 作为 Claude Code Skill 使用

```bash
# 放到用户级或项目级 skills 目录
cp -r dreamifly-batch ~/.claude/skills/dreamifly-batch
```

之后在 Claude Code 里直接说"用这批提示词批量生图"，Claude 会读取 `SKILL.md`，
帮你把提示词写进 `prompts.txt`、检查 cookie、运行脚本并汇报结果。

## 注意事项

- ⚠️ **不要把 `config/cookie.txt` 提交到任何公开仓库**——它等同于你的登录凭证。
- 积分不足（402）或登录失效（401）时脚本会立即停止并说明原因，已成功的不受影响。
- 失败的提示词会保留在 `prompts.txt`，直接重跑即可续跑。

## License

[MIT](./LICENSE)
