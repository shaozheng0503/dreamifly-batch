# dreamifly-batch

Batch-generate and download images from a list of prompts via the
[dreamifly.com](https://dreamifly.com) API. Queueing, throttling, auto-retry,
resume-on-failure, and a pre-flight check — write prompts into `prompts.txt`,
run one command.

> 🌐 中文: [README.md](./README.md)
> 🤖 This repo is also a **[Claude Code](https://claude.com/claude-code) Skill**: drop the folder
> into `.claude/skills/` and Claude will invoke it when you ask to "batch generate images".
> 🐍 **Zero dependencies**: Python 3 standard library only — no `pip install`.

## Example

| Prompt | Output |
|---|---|
| `a serene japanese garden at sunset, koi pond, soft golden light, ultra detailed` | ![sample](./docs/sample-japanese-garden.png) |

## Features

- 📝 **Queue-based**: one prompt per line in `prompts.txt`, processed top to bottom.
- 🎚️ **Inline params**: override per line with `| 16:9 | x2 | seed=123`.
- 🛫 **Pre-flight check**: `--check` validates config, connectivity, and cookie before burning a whole batch.
- 🧪 **Dry run**: `--dry-run` shows what would be generated without calling the API.
- ⬇️ **Auto download + sidecar**: images saved to `images/`, with a `.json` next to each recording seed/params for reproducibility.
- ✅ **Resume**: successful prompts move to `done.txt`; failures stay in `prompts.txt` to retry.
- 🔁 **Retry & backoff**: `429` backs off, `5xx` retries, `401/402` stop immediately with a reason.
- ⏰ **Cron-friendly**: `run.sh` cd's to its own dir.

## Quick start

```bash
git clone https://github.com/shaozheng0503/dreamifly-batch.git
cd dreamifly-batch

# 1) Auth: copy the template and paste your dreamifly.com Cookie line
cp config/cookie.txt.example config/cookie.txt
#    edit config/cookie.txt, remove comments, paste your Cookie

# 2) Pre-flight (recommended)
python3 dreamify.py --check

# 3) Add prompts, one per line
echo "a cyberpunk city street in the rain, neon reflections, cinematic" >> prompts.txt

# 4) Run (all / first 3)
./run.sh
./run.sh 3
```

> **Get the cookie**: log in to dreamifly.com → DevTools (F12) → Network → click any request
> → copy the whole `Cookie` line from Request Headers. `gpt-image-2` requires login or you get 401.

## Inline prompt params

Separate with `|` inside a single line in `prompts.txt` (overrides `config.json`):

```
a neon cat on the moon | 16:9 | x2 | seed=123 | model=gpt-image-2 | 1024x768 | neg=blurry
```

| Segment | Meaning |
|---|---|
| `16:9` | aspect ratio |
| `x2` | generate 2 images for this line |
| `1024x768` | width x height |
| `seed=123` | fixed seed (reproducible) |
| `model=...` | override model |
| `neg=...` | negative prompt |
| `img=URL,URL` | reference image(s), image-to-image (experimental) |

## CLI

```bash
python3 dreamify.py --check                 # pre-flight only
python3 dreamify.py --dry-run               # parse & preview, no API calls
python3 dreamify.py                         # process the whole queue
python3 dreamify.py 3                        # first 3 only (same as -n 3)
python3 dreamify.py --aspect 16:9 --batch 2 # global overrides (below inline)
python3 dreamify.py --no-sidecar            # skip .json sidecars
```

Precedence: **inline params > CLI flags > config.json**.

## Config `config/config.json`

| Field | Description | Default |
|---|---|---|
| `model` | generation model | `gpt-image-2` |
| `width` / `height` | pixels | `1024` / `1024` |
| `aspectRatio` | aspect ratio | `1:1` |
| `batch_size` | images per prompt | `1` |
| `steps` | sampling steps (null = omit) | `null` |
| `negative_prompt` | negative prompt | `""` |
| `delay_between_seconds` | throttle between prompts | `5` |
| `max_retries` | retries per failed prompt | `2` |
| `request_timeout_seconds` | per-request timeout | `300` |

## Auth

- `Authorization: Bearer MD5(apiKey + serverTimeString)` — computed automatically from `/api/time`.
- `apiKey` is the public front-end identifier (`NEXT_PUBLIC_API_KEY`), not a secret, so it ships with the repo.
- `Cookie` — **your** login session, read from `config/cookie.txt`, gitignored. **Never commit it.**

## Install as a Claude Code Skill

```bash
./install.sh            # to ~/.claude/skills/dreamifly-batch (user level)
./install.sh .claude    # to ./.claude/skills (project level)
```

## License

[MIT](./LICENSE)
