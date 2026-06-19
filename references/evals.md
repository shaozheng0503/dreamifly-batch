# Skill Eval Cases

Use these cases when changing the skill description, trigger boundaries, or workflow.

## Should Load

- "用这 10 个提示词批量出图，便宜一点"
- "把这张图加雪，批量生成 3 个版本"
- "用 happyhorse 做一个 5 秒城市延时视频"
- "先帮我估算这批 prompts 会花多少积分"
- "把失败的 Dreamifly 任务重新跑一下"
- "总结一下这次生图成功了哪些文件"

## Should Not Load

- "帮我润色一个绘画 prompt，但不要生成"
- "解释一下 Stable Diffusion 的 CFG scale"
- "用本地 ComfyUI workflow 跑这张图"
- "帮我找 Midjourney prompt 灵感"

## Forbidden Real Run Without Confirmation

- Any video model request
- Any `nano-banana-2` request
- Any estimate with 5+ credits per item
- Any queue whose model is unknown and cost cannot be verified
