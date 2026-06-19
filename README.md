# dreamifly-batch

从一个提示词列表，批量调用 [dreamifly.com](https://dreamifly.com) 的生图 API 逐条生成并下载图片。
排队、节流、自动重试、断点续跑、开跑前预检——把提示词写进 `prompts.txt`，跑一条命令就行。

> 🌐 English: [README_EN.md](./README_EN.md)
> 🤖 本仓库同时是一个 **[Claude Code](https://claude.com/claude-code) Skill**：把目录放进 `.claude/skills/`，
> Claude 就能在你说"批量生图"时自动调用它。详见 [作为 Claude Code Skill 使用](#作为-claude-code-skill-使用)。
> 🐍 **零依赖**：只需 Python 3，全部用标准库，无需 `pip install`。

## 示例

| 提示词 | 出图 |
|---|---|
| `a serene japanese garden at sunset, koi pond, soft golden light, ultra detailed` | ![sample](./docs/sample-japanese-garden.png) |

## 功能

- 📝 **队列式**：`prompts.txt` 每行一个提示词，从上往下逐条生成。
- 🎚️ **内联参数**：单行里直接写 `| 16:9 | x2 | seed=123`，逐条覆盖配置。
- 🛫 **开跑前预检**：`--check` 先校验配置、连通性、cookie，避免整批跑一半才失败。
- 🧪 **预演**：`--dry-run` 解析并展示将要生成什么，不调用 API、不花积分。
- ⬇️ **自动下载 + 边车**：图片落到 `images/`，旁边写 `.json` 记录 seed/参数，便于复现。
- ✅ **断点续跑**：成功的提示词移到 `done.txt`，失败的留在 `prompts.txt` 下次自动重试。
- 🔁 **重试与退避**：`429` 限流自动退避，`5xx` 自动重试，`401/402` 立即停止并提示原因。
- ⏰ **可定时**：`run.sh` 自动切到脚本目录，可直接挂到 cron。

## 目录结构

```
.
├── dreamify.py            # 主脚本（纯标准库，零依赖）
├── run.sh                 # 启动器（手动 / cron 都可）
├── install.sh             # 一键安装为 Claude Code Skill
├── prompts.txt            # 提示词队列（每行一个，# 注释）
├── config/
│   ├── config.json        # 生图参数
│   └── cookie.txt.example # 登录态模板（复制为 cookie.txt 后填写）
├── docs/                  # 示例图等
├── images/                # 生成的图片 + .json 边车（git 忽略）
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

# 2) 先预检（强烈建议）
python3 dreamify.py --check

# 3) 写提示词：每行一个
echo "a cyberpunk city street in the rain, neon reflections, cinematic" >> prompts.txt

# 4) 跑起来（全部 / 只跑前 3 条）
./run.sh
./run.sh 3
```

> **获取 Cookie**：浏览器登录 dreamifly.com → 开发者工具(F12) → Network → 刷新后点任意请求
> → Request Headers 里复制 `Cookie` 整行。`gpt-image-2` 必须登录，否则返回 401。

## 提示词内联参数

在 `prompts.txt` 一行内用 `|` 分隔，逐条覆盖 `config.json`，可任意组合：

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

## 命令行

```bash
python3 dreamify.py --check                 # 只做开跑前预检
python3 dreamify.py --dry-run               # 解析预演，不调用 API
python3 dreamify.py                         # 跑完队列全部
python3 dreamify.py 3                        # 只跑前 3 条（等价 -n 3）
python3 dreamify.py --aspect 16:9 --batch 2 # 全局覆盖（优先级低于内联）
python3 dreamify.py --model gpt-image-2 --width 1024 --height 768
python3 dreamify.py --no-sidecar            # 不写 .json 边车
python3 dreamify.py --prompts other.txt --images-dir out/   # 自定义路径
```

参数优先级：**内联参数 > 命令行 flag > config.json**。

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
# 一键安装到 ~/.claude/skills/dreamifly-batch（用户级）
./install.sh
# 或安装到 当前项目/.claude/skills（项目级）
./install.sh .claude
```

之后在 Claude Code 里直接说"用这批提示词批量生图"，Claude 会读取 `SKILL.md`，
按内置 playbook 先预检、再把提示词写进 `prompts.txt`、运行脚本并汇报结果。

## 注意事项

- ⚠️ **不要把 `config/cookie.txt` 提交到任何公开仓库**——它等同于你的登录凭证。
- 积分不足（402）或登录失效（401）时脚本会立即停止并说明原因，已成功的不受影响。
- 失败的提示词会保留在 `prompts.txt`，直接重跑即可续跑。
- `img=` 图生图为实验性：API 对参考图的具体格式未做充分验证，遇到异常请回退为纯文生图。

## License

[MIT](./LICENSE)
