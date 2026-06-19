# dreamifly-batch

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![models](https://img.shields.io/badge/models-6%20image%20%2B%202%20video-orange)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)
![License](https://img.shields.io/badge/License-MIT-yellow)

Batch-generate and download **images and videos** from a list of prompts via the
[Dreamifly](https://dreamifly.com) API. Queueing, throttling, auto-retry, resume,
pre-flight check, and multi-model routing — write prompts into `prompts.txt`, run one command.

| | |
|---|---|
| 🌐 Dreamifly | https://dreamifly.com |
| 📦 Repo | https://github.com/shaozheng0503/dreamifly-batch |
| 🌍 中文 | [README.md](./README.md) |

> 🤖 This repo is also a **[Claude Code](https://claude.com/claude-code) Skill / Codex agent tool**: once installed,
> just tell the AI "batch-generate these images / make a video from this picture" and it drives the tool for you.
> 🐍 **Zero dependencies**: Python 3 standard library only.

## Example

**Text-to-image**

| Prompt | Output |
|---|---|
| `a serene japanese garden at sunset, koi pond, soft golden light` | ![sample](./docs/sample-japanese-garden.png) |

**Image-to-image** (`img=` reference, prompt `transform ... into a snowy winter scene`)

| Reference | Output |
|---|---|
| ![ref](./docs/sample-japanese-garden.png) | ![i2i](./docs/sample-i2i-winter.png) |

**Text-to-video** (happyhorse-1.0 · `a cinematic timelapse of a city skyline at sunset` · 5s 720P, real output)

![t2v](./docs/sample-t2v-city-sunset.gif)

▶️ [Full video sample-t2v-city-sunset.mp4](./docs/sample-t2v-city-sunset.mp4) (1280×720 · h264 · 5s)

**Image-to-video** (Wan2.2-I2V-Lightning · the garden image above + `gentle wind, koi swimming, falling leaves` · real output)

| Source (input) | Generated video (output) |
|---|---|
| ![ref](./docs/sample-japanese-garden.png) | ![i2v](./docs/sample-i2v-garden.gif) |

▶️ [Full video sample-i2v-garden.mp4](./docs/sample-i2v-garden.mp4) (1280×720 · h264)

## Models

Run `python3 dreamify.py --list-models` for the live list.

**Image (`/api/generate`)**

| Model | Capability | maxImg | steps | Login | ~Credits |
|---|---|:-:|:-:|:-:|:-:|
| `Wai-SDXL-V150` / `Wai-SDXL-V170` | text-to-image · anime | 0 | 20 | no | ~0.1 |
| `Z-Image-Turbo` | text-to-image · CN · fast | 0 | 10 | no | ~0.325 |
| `Qwen-Image-Edit` | image-to-image · CN | 3 | — | no | ~1.2 |
| `gpt-image-2` | t2i + i2i · CN | 3 | — | yes | premium |
| `nano-banana-2` | t2i + i2i · CN | 3 | — | yes | ~25+ |

`steps` is auto-filled per model (Wai needs 20/30, Z-Image-Turbo 10/20).

**Video (`/api/generate-video`, pricier, slower)**

| Model | Modes | Params | ~Credits |
|---|---|---|:-:|
| `Wan2.2-I2V-Lightning` | image-to-video (**needs 1 source image**) | — | ~200 |
| `happyhorse-1.0` | text/image/reference-to-video + edit | `secs`(3–15) `res`(720P/1080P) | ~150+ |

Video mode is auto-derived: no image → text-to-video, 1 → image-to-video, many → reference-to-video.

## Styles

All 11 platform styles are built in via `style=` (prepended to the prompt). Same prompt `a cat sitting by a window`, different `style=` (Z-Image-Turbo):

| anime | oil | pixel |
|:---:|:---:|:---:|
| ![anime](./docs/style-anime.png) | ![oil](./docs/style-oil.png) | ![pixel](./docs/style-pixel.png) |
| **lego** | **lineart** | **riso** |
| ![lego](./docs/style-lego.png) | ![lineart](./docs/style-lineart.png) | ![riso](./docs/style-riso.png) |

Values: `cartoon anime oil lineart vector pixel lego riso realistic puppet emoji` (Chinese names also accepted).
Usage: `a cat by a window | style=oil | model=Z-Image-Turbo` or global `--style oil`.

## Get your login Cookie (required for gpt-image-2 / nano-banana-2 / video)

The `Authorization` token is computed automatically — the only thing **you** provide is your browser Cookie.

1. Log in at https://dreamifly.com (GitHub / WeChat / etc.). Your credits show bottom-left.
2. Open DevTools (`F12`), go to the **Network** tab.
3. Refresh, click any request to `dreamifly.com`, find **Request Headers → `Cookie:`**, copy the whole line.
4. `cp config/cookie.txt.example config/cookie.txt`, paste the line in (without the `Cookie:` prefix), save.
5. Verify: `python3 dreamify.py --check` → expect `✅ cookie loaded`. Cookies expire; re-copy on a 401.

⚠️ The Cookie equals your login. It is gitignored — never commit or share it.

## Quick start

```bash
git clone https://github.com/shaozheng0503/dreamifly-batch.git
cd dreamifly-batch
cp config/cookie.txt.example config/cookie.txt   # fill in if using login models
python3 dreamify.py --list-models
python3 dreamify.py --check
echo "anime girl with flowers | model=Wai-SDXL-V150" >> prompts.txt
./run.sh
```

## Switching models

Precedence: **inline > CLI flag > config.json**.

```text
# prompts.txt — per-line model
masterpiece, 1girl, sakura | model=Wai-SDXL-V150
edit this, add snow        | model=Qwen-Image-Edit | img=ref.png
a cat running              | model=Wan2.2-I2V-Lightning | img=source.png
city timelapse             | model=happyhorse-1.0 | secs=5 | res=720P
```
```bash
python3 dreamify.py --model Z-Image-Turbo   # whole run
# or edit "model" in config/config.json for the default
```

## Inline params

`model=` · `16:9` · `1024x768` · `x2` (≤4) · `seed=` · `steps=` · `neg=` · `img=path,or,URL` · `secs=` · `res=720P`

## CLI

```bash
python3 dreamify.py --list-models   # list models (online)
python3 dreamify.py --check          # pre-flight only
python3 dreamify.py --dry-run        # preview, no API calls
python3 dreamify.py 3                 # first 3 only
python3 dreamify.py --no-sidecar
```

## Use it inside an AI agent

The repo ships `SKILL.md` (Claude Code) and `AGENTS.md` (Codex / generic agents).

- **Claude Code**: `./install.sh` → installs to `~/.claude/skills/`, then ask in natural language.
- **Codex**: `cd` into the repo and run `codex`; it reads `AGENTS.md` automatically.
- **Any agent**: feed it `SKILL.md`/`AGENTS.md`, let it (1) append prompts to `prompts.txt`, (2) run
  `python3 dreamify.py`, (3) read `run.log`. Any agent that can write files and run shell can use it.

## Notes

- 💸 Video is expensive (Wan ~200, happyhorse ~150+) and slow; no auto-retry for video.
- `img=` image-to-image is verified: local file / URL / data URI, auto base64, ≤10MB, ≤9 images, login required.
- 401 = re-copy your cookie; 402 = out of credits. Failed prompts stay in `prompts.txt` to retry.

## License

[MIT](./LICENSE)
