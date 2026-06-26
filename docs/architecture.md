# 架构与鉴权

这份文档记录 `dreamifly-batch` 的仓库组织方式和鉴权原理。属于实现细节，首次使用不需要读；想了解它怎么被 Agent 加载、或排查鉴权问题时再看。

## Skill 架构

这个仓库按“中心短，辐射厚”的方式组织 Agent 能力：

```text
SKILL.md                          # 短入口：触发边界、执行协议、安全规则
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

## 鉴权原理

- `Authorization: Bearer MD5(apiKey + 服务器时间串)`：脚本自动从 `/api/time` 取时间串并自行计算，**无需手动获取**。
- `apiKey` 是打进前端、发给每个浏览器的**公开标识**（`NEXT_PUBLIC_API_KEY`），并非私密凭证，随仓库附带。
- `Cookie`：**你个人的登录态**，读自 `config/cookie.txt`（已被 `.gitignore` 排除，请勿提交）。

获取 Cookie 的步骤见 [README 的「配置登录态 Cookie」](../README.md#快速开始)。
