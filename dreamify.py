#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dreamifly 批量生图 / 生视频脚本
- 从 prompts.txt 读取提示词（每行一个，# 开头/空行忽略）
- 生图：调用 https://dreamifly.com/api/generate
- 生视频：调用 https://dreamifly.com/api/generate-video（同步返回 videoUrl）
- 把结果下载到 images/，每个文件旁写 .json 边车（记录 seed/模型/参数），成功的 prompt 移到 done.txt

支持的模型（见 --list-models 获取在线最新列表）：
  生图：Wai-SDXL-V150 / Wai-SDXL-V170 / Z-Image-Turbo / Qwen-Image-Edit / gpt-image-2 / nano-banana-2
  视频：Wan2.2-I2V-Lightning（图生视频）/ happyhorse-1.0（文/图/多参考图生视频）

鉴权：
- Authorization: Bearer MD5(apiKey + 服务器时间串)   —— 自动从 /api/time 取时间，自己算
- Cookie: 你的登录态                                  —— 读 config/cookie.txt（部分模型/视频必须登录）

提示词内联参数（用 | 分隔，可任意组合，覆盖 config.json）：
    a cat | model=Wai-SDXL-V150 | 16:9 | x2 | seed=123 | 1024x768 | neg=blurry | img=ref.png
    生视频示例：
    a cat running | model=Wan2.2-I2V-Lightning | img=source.png            （图生视频，需 1 张源图）
    a sunset timelapse | model=happyhorse-1.0 | secs=5 | res=720P          （文生视频）
    - model=...   选择模型（生图或视频）
    - 16:9 / 1024x768 / x2 / seed= / neg=   生图参数
    - img=路径或URL（逗号分隔）   参考图/源图，自动转 base64
    - secs=N      视频时长秒（happyhorse 3-15）
    - res=720P    视频分辨率（happyhorse：720P / 1080P）

常用命令：
    python3 dreamify.py                 # 跑完队列全部
    python3 dreamify.py 3               # 只跑前 3 条
    python3 dreamify.py --check         # 只做开跑前预检
    python3 dreamify.py --dry-run       # 解析并展示将要生成什么，不调用 API
    python3 dreamify.py --list-models   # 列出平台所有可用模型（在线）
"""

import argparse
import base64
import json
import math
import os
import re
import sys
import time
import hashlib
import datetime
import urllib.request
import urllib.error

BASE = "https://dreamifly.com"
# NEXT_PUBLIC_API_KEY —— 这是打进前端、发给每个浏览器的公开标识，非私密凭证
API_KEY = "6h^&+h4567mk&&9-%@"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")

# 前端限制：单张参考图 ≤ 10MB（0xa00000）
MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp")
VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v", ".gif")

# 已知模型注册表（离线兜底；--list-models 会拉取在线最新）。
# 成本为大致值，最终以平台扣费为准。
# steps：部分模型（Wai/Z）必须传指定步数，否则 400；其余传 None（不发）。
# pixels：模型原生分辨率像素预算（用于按 aspectRatio 换算宽高，来自前端 normalResolutionPixels）。
IMAGE_MODELS = {
    "Wai-SDXL-V150":   {"t2i": True,  "i2i": False, "max_images": 0, "login": False, "steps": 20,   "pixels": 1048576, "cost": "~0.1",   "tags": "动漫风格"},
    "Wai-SDXL-V170":   {"t2i": True,  "i2i": False, "max_images": 0, "login": False, "steps": 20,   "pixels": 1048576, "cost": "~0.1",   "tags": "动漫风格"},
    "Z-Image-Turbo":   {"t2i": True,  "i2i": False, "max_images": 0, "login": False, "steps": 10,   "pixels": 1048576, "cost": "~0.325", "tags": "中文/快"},
    "Qwen-Image-Edit": {"t2i": False, "i2i": True,  "max_images": 3, "login": False, "steps": None, "pixels": 1048576, "cost": "~1.2",   "tags": "图生图/中文"},
    "gpt-image-2":     {"t2i": True,  "i2i": True,  "max_images": 3, "login": True,  "steps": None, "pixels": 1327104, "cost": "顶级",    "tags": "文/图生图·中文"},
    "nano-banana-2":   {"t2i": True,  "i2i": True,  "max_images": 3, "login": True,  "steps": None, "pixels": 1048576, "cost": "~25+",   "tags": "文/图生图·中文"},
}
DEFAULT_PIXELS = 1048576       # 未知生图模型的像素预算（≈1024x1024）
VIDEO_PIXELS = 921600          # 视频像素预算（=1280x720，来自前端 totalPixels）

# 平台支持的预设宽高比（前端下拉项）。脚本会据此把比例换算成匹配的 width/height 再发。
ASPECT_RATIOS = ["16:9", "21:9", "4:3", "3:2", "5:4", "1:1", "4:5", "2:3", "3:4", "9:16", "9:21"]
VIDEO_MODELS = {
    "Wan2.2-I2V-Lightning": {
        "provider": "comfy", "mode": "image-to-video", "needs_image": True,
        "use_seconds": False, "use_resolution": False, "cost": "~200", "tags": "图生视频/快",
    },
    "happyhorse-1.0": {
        "provider": "happyhorse", "mode": "text-to-video", "needs_image": False,
        "use_seconds": True, "default_seconds": 5, "min_seconds": 3, "max_seconds": 15,
        "use_resolution": True, "resolutions": ["720P", "1080P"], "default_resolution": "720P",
        "max_reference_images": 9, "cost": "~150+", "tags": "文/图/多参考图生视频",
    },
}

HERE = os.path.dirname(os.path.abspath(__file__))
PATHS = {
    "prompts": os.path.join(HERE, "prompts.txt"),
    "done": os.path.join(HERE, "done.txt"),
    "images": os.path.join(HERE, "images"),
    "config": os.path.join(HERE, "config", "config.json"),
    "cookie": os.path.join(HERE, "config", "cookie.txt"),
}
LOG_FILE = os.path.join(HERE, "run.log")

CONFIG_SCHEMA = {
    "model": (str, lambda v: len(v) > 0),
    "width": (int, lambda v: 64 <= v <= 4096),
    "height": (int, lambda v: 64 <= v <= 4096),
    "aspectRatio": (str, lambda v: bool(re.fullmatch(r"\d+:\d+", v))),
    "batch_size": (int, lambda v: 1 <= v <= 4),
    "delay_between_seconds": ((int, float), lambda v: v >= 0),
    "max_retries": (int, lambda v: 0 <= v <= 10),
    "request_timeout_seconds": ((int, float), lambda v: v > 0),
    "video_seconds": (int, lambda v: 1 <= v <= 60),
    "video_resolution": (str, lambda v: str(v).upper() in ("720P", "1080P")),
    "video_timeout_seconds": ((int, float), lambda v: v > 0),
}


def log(msg):
    line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---------- 配置 / cookie ----------

def load_config():
    with open(PATHS["config"], encoding="utf-8") as f:
        return json.load(f)


def validate_config(cfg):
    issues = []
    for key, (types, check) in CONFIG_SCHEMA.items():
        if key not in cfg or cfg[key] is None:
            if key in ("model", "width", "height"):
                issues.append(f"config 缺少必需字段：{key}")
            continue
        val = cfg[key]
        if not isinstance(val, types):
            issues.append(f"config.{key} 类型应为 {types}，实际 {type(val).__name__}")
            continue
        if check and not check(val):
            issues.append(f"config.{key} 取值不合法：{val!r}")
    return issues


def load_cookie():
    path = PATHS["cookie"]
    if not os.path.exists(path):
        return ""
    for ln in open(path, encoding="utf-8"):
        s = ln.strip()
        if s and not s.startswith("#"):
            return s
    return ""


# ---------- 鉴权 ----------

def get_server_timestring():
    try:
        req = urllib.request.Request(
            f"{BASE}/api/time",
            headers={"User-Agent": UA, "Cache-Control": "no-cache, no-store, must-revalidate"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            ts = data.get("timeString")
            if ts and re.fullmatch(r"\d{12}", ts):
                return ts
    except Exception as e:
        log(f"  /api/time 获取失败，回退本地 UTC：{e}")
    return datetime.datetime.utcnow().strftime("%Y%m%d%H%M")


def make_token():
    return hashlib.md5((API_KEY + get_server_timestring()).encode("utf-8")).hexdigest()


def base_headers(model):
    h = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {make_token()}",
        "User-Agent": UA,
        "Referer": f"{BASE}/create?model={model}",
        "Origin": BASE,
    }
    return h


# ---------- 模型 ----------

def canonical_model(name):
    """大小写不敏感地把用户输入归一到注册表里的标准 id。"""
    if not name:
        return name
    for k in list(IMAGE_MODELS) + list(VIDEO_MODELS):
        if k.lower() == name.lower():
            return k
    return name


def is_video_model(model):
    return model in VIDEO_MODELS


def resolve_model(overrides, cli, cfg):
    name = overrides.get("model") or cli.get("model") or cfg.get("model", "gpt-image-2")
    return canonical_model(name)


def list_models():
    def fetch(path):
        req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode()).get("models", [])
    try:
        ims, vms = fetch("/api/models"), fetch("/api/video-models")
        print("AI 生图模型（/api/generate）：")
        for m in ims:
            caps = ([("文生图" if m.get("use_t2i") else None),
                     ("图生图" if m.get("use_i2i") else None)])
            caps = "/".join(c for c in caps if c)
            print(f"  {m.get('id',''):24} {caps:10} maxImg={m.get('maxImages',0)} "
                  f"login={bool(m.get('requiresLogin'))}  {m.get('description','')[:30]}")
        print("\nAI 视频模型（/api/generate-video）：")
        for m in vms:
            print(f"  {m.get('id',''):24} {m.get('mode',''):16} tags={','.join(m.get('tags',[]))}")
        return 0
    except Exception as e:
        print(f"在线获取失败（{e}），内置已知模型：")
        for k, v in IMAGE_MODELS.items():
            print(f"  [图] {k:24} t2i={v['t2i']} i2i={v['i2i']} cost={v['cost']}")
        for k, v in VIDEO_MODELS.items():
            print(f"  [视频] {k:24} {v['tags']} cost={v['cost']}")
        return 1


# ---------- 提示词队列 ----------

def parse_prompt_line(line):
    """把一行拆成 (干净提示词, 覆盖项 dict)。"""
    parts = [p.strip() for p in line.split("|")]
    prompt = parts[0].strip()
    overrides = {}
    for seg in parts[1:]:
        if not seg:
            continue
        low = seg.lower()
        if re.fullmatch(r"\d+:\d+", seg):
            overrides["aspectRatio"] = seg
            if seg not in ASPECT_RATIOS:
                log(f"  ⚠️ {seg} 不在平台预设比例 {ASPECT_RATIOS} 内，脚本仍会按它换算宽高，但平台可能不识别该比例标签。")
        elif re.fullmatch(r"x\d+", low):
            overrides["batch_size"] = int(low[1:])
        elif re.fullmatch(r"\d+x\d+", low):
            w, h = low.split("x")
            overrides["width"], overrides["height"] = int(w), int(h)
        elif low.startswith("seed="):
            try:
                overrides["seed"] = int(seg.split("=", 1)[1])
            except ValueError:
                log(f"  ⚠️ 无法解析 seed：{seg}")
        elif low.startswith("model="):
            overrides["model"] = seg.split("=", 1)[1].strip()
        elif low.startswith(("neg=", "negative=")):
            overrides["negative_prompt"] = seg.split("=", 1)[1].strip()
        elif low.startswith("steps="):
            try:
                overrides["steps"] = int(seg.split("=", 1)[1])
            except ValueError:
                log(f"  ⚠️ 无法解析 steps：{seg}")
        elif low.startswith(("secs=", "seconds=")):
            try:
                overrides["seconds"] = int(seg.split("=", 1)[1])
            except ValueError:
                log(f"  ⚠️ 无法解析 secs：{seg}")
        elif low.startswith(("res=", "resolution=")):
            overrides["resolution"] = seg.split("=", 1)[1].strip()
        elif low.startswith("img="):
            urls = [u.strip() for u in seg.split("=", 1)[1].split(",") if u.strip()]
            overrides["images"] = urls
        else:
            log(f"  ⚠️ 忽略无法识别的内联参数：{seg!r}")
    return prompt, overrides


def read_prompt_queue():
    if not os.path.exists(PATHS["prompts"]):
        return [], []
    lines = open(PATHS["prompts"], encoding="utf-8").read().splitlines()
    pending = [(i, ln.strip()) for i, ln in enumerate(lines)
               if ln.strip() and not ln.strip().startswith("#")]
    return lines, pending


def remove_lines(done_indices):
    lines = open(PATHS["prompts"], encoding="utf-8").read().splitlines()
    kept = [ln for i, ln in enumerate(lines) if i not in done_indices]
    with open(PATHS["prompts"], "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))


def append_done(prompt, filenames, note=""):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(PATHS["done"], "a", encoding="utf-8") as f:
        f.write(f"{ts}\t{prompt}\t{', '.join(filenames) or note}\n")


def slugify(text, maxlen=40):
    text = re.sub(r"[^\w一-龥]+", "_", text).strip("_")
    return (text[:maxlen] or "media")


# ---------- 请求体 ----------

def _parse_ratio(ar):
    m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", ar or "")
    if not m:
        return None
    rw, rh = int(m.group(1)), int(m.group(2))
    return (rw, rh) if rw > 0 and rh > 0 else None


def _reduce_ratio(w, h):
    g = math.gcd(int(w), int(h)) or 1
    return f"{int(w)//g}:{int(h)//g}"


def dims_for_ratio(aspect, target_px, multiple=16, cap=2048):
    """按宽高比 + 像素预算换算出宽高（取 16 的整数倍，尽量贴近目标比例与像素）。"""
    rw, rh = _parse_ratio(aspect) or (1, 1)
    scale = (target_px / (rw * rh)) ** 0.5
    w = max(multiple, min(cap, int(round(rw * scale / multiple) * multiple)))
    h = max(multiple, min(cap, int(round(rh * scale / multiple) * multiple)))
    return w, h


def resolve_dimensions(overrides, cli, cfg, *, target_px, cfg_w, cfg_h, cfg_ar, default_ar):
    """统一解析宽高与宽高比。
    - 显式像素尺寸（内联 WxH 或 --width+--height）→ 原样使用；
    - 指定了 aspectRatio（内联 16:9 或 --aspect）→ 按比例 + 像素预算换算宽高（修复比例不生效）；
    - 否则用 config 宽高（若与 config 宽高比一致），不一致则按 config 宽高比换算。
    返回 (width, height, aspectRatio)。
    """
    inline_dims = ("width" in overrides) and ("height" in overrides)
    cli_dims = (cli.get("width") is not None) and (cli.get("height") is not None)
    aspect_set = ("aspectRatio" in overrides) or (cli.get("aspectRatio") is not None)
    aspect = overrides.get("aspectRatio") or cli.get("aspectRatio") or cfg.get(cfg_ar, default_ar)

    if inline_dims:
        w, h = int(overrides["width"]), int(overrides["height"])
        return w, h, (aspect if aspect_set else _reduce_ratio(w, h))
    if cli_dims:
        w, h = int(cli["width"]), int(cli["height"])
        return w, h, (aspect if aspect_set else _reduce_ratio(w, h))
    if aspect_set:
        w, h = dims_for_ratio(aspect, target_px)
        return w, h, aspect

    cw = int(cfg.get(cfg_w, 1024) or 1024)
    ch = int(cfg.get(cfg_h, 1024) or 1024)
    pr = _parse_ratio(aspect)
    if pr and abs((cw / ch) - (pr[0] / pr[1])) < 0.02:
        return cw, ch, aspect          # config 宽高与宽高比一致，原样用（向后兼容默认 1024x1024）
    if pr:
        w, h = dims_for_ratio(aspect, target_px)
        return w, h, aspect            # config 宽高与宽高比不一致，以宽高比为准换算
    return cw, ch, aspect


def build_body(prompt, cfg, overrides=None, cli=None):
    """生图请求体，返回 (body, seed)。优先级：内联 > 命令行 > config。"""
    overrides = overrides or {}
    cli = cli or {}

    def pick(key, default):
        if key in overrides:
            return overrides[key]
        if cli.get(key) is not None:
            return cli[key]
        return cfg.get(key, default)

    seed = overrides.get("seed")
    if seed is None:
        seed = int.from_bytes(os.urandom(4), "big") % 100000000

    model = canonical_model(pick("model", "gpt-image-2"))
    target_px = IMAGE_MODELS.get(model, {}).get("pixels", DEFAULT_PIXELS)
    width, height, aspectRatio = resolve_dimensions(
        overrides, cli, cfg, target_px=target_px,
        cfg_w="width", cfg_h="height", cfg_ar="aspectRatio", default_ar="1:1")
    body = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "seed": seed,
        "batch_size": pick("batch_size", 1),
        "model": model,
        "images": overrides.get("images", []),
        "aspectRatio": aspectRatio,
    }
    # steps：内联/cli/config 优先，否则用模型注册表默认（Wai 必须 20/30，Z-Image-Turbo 10/20）
    steps = pick("steps", None)
    if steps is None:
        steps = IMAGE_MODELS.get(model, {}).get("steps")
    if steps:
        body["steps"] = steps
    neg = pick("negative_prompt", "")
    if neg:
        body["negative_prompt"] = neg
    return body, seed


def build_video_body(prompt, model, cfg, overrides=None, cli=None):
    """生视频请求体，返回 (body, mode)。body 里 image/referenceImages 仍是原始引用，发送前再编码。"""
    overrides = overrides or {}
    cli = cli or {}
    meta = VIDEO_MODELS.get(model, {})
    imgs = overrides.get("images", [])

    # 推导 videoMode（comfy 类如 Wan 固定为其自身 mode）
    if meta.get("provider") == "comfy":
        mode = meta.get("mode", "image-to-video")
    elif len(imgs) > 1:
        mode = "reference-to-video"
    elif len(imgs) == 1:
        mode = "image-to-video"
    else:
        mode = "text-to-video"

    width, height, aspectRatio = resolve_dimensions(
        overrides, cli, cfg, target_px=VIDEO_PIXELS,
        cfg_w="video_width", cfg_h="video_height", cfg_ar="video_aspectRatio", default_ar="16:9")

    body = {
        "prompt": prompt,
        "negative_prompt": (overrides.get("negative_prompt") or "").strip(),
        "width": width,
        "height": height,
        "aspectRatio": aspectRatio,
        "model": model,
        "videoMode": mode,
    }

    if meta.get("use_seconds"):
        secs = overrides.get("seconds", cfg.get("video_seconds", meta.get("default_seconds", 5)))
        secs = max(meta.get("min_seconds", 3), min(meta.get("max_seconds", 15), int(secs)))
        body["videoSeconds"] = secs
    if meta.get("use_resolution"):
        res = str(overrides.get("resolution", cfg.get("video_resolution", meta.get("default_resolution", "720P")))).upper()
        if not res.endswith("P"):
            res += "P"
        body["resolution"] = res

    # 源图 / 参考图（保留原始引用，发送前编码）
    if mode in ("image-to-video",) and imgs:
        body["image"] = imgs[0]
    elif mode == "reference-to-video":
        body["referenceImages"] = imgs[:meta.get("max_reference_images", 9)]
    return body, mode


# ---------- 网络 ----------

def post_generate(body, cookie):
    headers = base_headers(body.get("model"))
    if cookie:
        headers["Cookie"] = cookie
    return urllib.request.Request(f"{BASE}/api/generate",
                                  data=json.dumps(body).encode("utf-8"),
                                  headers=headers, method="POST")


def post_generate_video(body, cookie):
    headers = base_headers(body.get("model"))
    if cookie:
        headers["Cookie"] = cookie
    return urllib.request.Request(f"{BASE}/api/generate-video",
                                  data=json.dumps(body).encode("utf-8"),
                                  headers=headers, method="POST")


def extract_image_urls(payload):
    urls = []
    if isinstance(payload, dict):
        for k in ("imageUrl", "url", "image"):
            v = payload.get(k)
            if isinstance(v, str) and v:
                urls.append(v)
        for k in ("imageUrls", "images", "urls"):
            v = payload.get(k)
            if isinstance(v, list):
                urls += [x for x in v if isinstance(x, str) and x]
                for x in v:
                    if isinstance(x, dict):
                        for kk in ("imageUrl", "url", "image"):
                            if isinstance(x.get(kk), str):
                                urls.append(x[kk])
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def encode_reference_image(ref):
    """把参考图/源图统一转成 API 要求的「无前缀 base64 字符串」。支持本地路径 / http(s) URL / data:URI。"""
    if ref.startswith("data:"):
        return ref.split(",", 1)[1]
    if ref.startswith(("http://", "https://", "//")):
        url = ("https:" + ref) if ref.startswith("//") else ref
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    else:
        path = os.path.abspath(os.path.expanduser(ref))
        if not os.path.exists(path):
            raise FileNotFoundError(f"参考图不存在：{ref}")
        with open(path, "rb") as f:
            data = f.read()
    if len(data) > MAX_IMAGE_BYTES:
        log(f"  ⚠️ 参考图 {ref} 约 {len(data)//1024//1024}MB，超过 10MB 上限，可能被拒。")
    return base64.b64encode(data).decode("ascii")


def write_sidecar(media_path, meta):
    side = os.path.splitext(media_path)[0] + ".json"
    try:
        with open(side, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"  ⚠️ 写 metadata 边车失败：{e}")


def download(url, prompt, idx, kind="image"):
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = BASE + url
    allowed = VIDEO_EXTS if kind == "video" else IMG_EXTS
    default = ".mp4" if kind == "video" else ".png"
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    if ext not in allowed:
        ext = default
    fn = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{slugify(prompt)}_{idx}{ext}"
    path = os.path.join(PATHS["images"], fn)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    with urllib.request.urlopen(req, timeout=300) as r, open(path, "wb") as f:
        f.write(r.read())
    return fn, path, url


# ---------- 单条处理 ----------

def process_image_item(prompt, body, seed, cookie, cfg, args):
    max_retries = cfg.get("max_retries", 2)
    send_body = body
    if body["images"]:
        try:
            send_body = dict(body)
            send_body["images"] = [encode_reference_image(x) for x in body["images"]]
            log(f"  🖼️ 已编码 {len(send_body['images'])} 张参考图（图生图）")
        except Exception as e:
            return {"ok": False, "files": [], "fatal": False, "note": f"FAILED 参考图错误：{e}"}

    for attempt in range(max_retries + 1):
        try:
            req = post_generate(send_body, cookie)
            with urllib.request.urlopen(req, timeout=cfg.get("request_timeout_seconds", 300)) as r:
                payload = json.loads(r.read().decode())
            urls = extract_image_urls(payload)
            if not urls:
                log(f"  返回里没找到图片 URL：{json.dumps(payload, ensure_ascii=False)[:300]}")
                return {"ok": False, "files": [], "fatal": False, "note": "FAILED 无图片URL"}
            files = []
            for i, u in enumerate(urls):
                fn, path, src = download(u, prompt, i, "image")
                files.append(fn)
                if not args.no_sidecar:
                    src_disp = f"data:inline({len(src)} chars)" if src.startswith("data:") else src
                    write_sidecar(path, {
                        "type": "image", "prompt": prompt, "model": body["model"],
                        "width": body["width"], "height": body["height"],
                        "aspectRatio": body["aspectRatio"], "seed": seed, "batch_index": i,
                        "source_url": src_disp, "reference_images": body["images"],
                        "negative_prompt": body.get("negative_prompt", ""),
                        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                    })
            log(f"  ✅ 下载 {len(files)} 张：{', '.join(files)}")
            return {"ok": True, "files": files, "fatal": False, "note": ""}
        except urllib.error.HTTPError as e:
            err = ""
            try:
                err = e.read().decode()[:400]
            except Exception:
                pass
            log(f"  HTTP {e.code}: {err}")
            if e.code == 401:
                log("  ❌ 未登录/登录失效 —— 请更新 config/cookie.txt 后重跑。")
                return {"ok": False, "files": [], "fatal": True, "note": "401"}
            if e.code == 402:
                log("  ❌ 账号积分不足 —— 终止本次。")
                return {"ok": False, "files": [], "fatal": True, "note": "402"}
            if e.code == 429:
                wait = 30 * (attempt + 1)
                log(f"  限流，等待 {wait}s 重试…")
                time.sleep(wait)
                continue
            if 500 <= e.code < 600 and attempt < max_retries:
                time.sleep(5)
                continue
            return {"ok": False, "files": [], "fatal": False, "note": f"FAILED HTTP{e.code}"}
        except Exception as e:
            log(f"  请求异常（第 {attempt+1} 次）：{e}")
            if attempt < max_retries:
                time.sleep(5)
                continue
            return {"ok": False, "files": [], "fatal": False, "note": f"FAILED {e}"}
    return {"ok": False, "files": [], "fatal": False, "note": "FAILED（保留重试）"}


def process_video_item(prompt, body, mode, model, cookie, cfg, args):
    meta = VIDEO_MODELS.get(model, {})
    send_body = dict(body)
    try:
        if send_body.get("image"):
            send_body["image"] = encode_reference_image(send_body["image"])
        if send_body.get("referenceImages"):
            send_body["referenceImages"] = [encode_reference_image(x) for x in send_body["referenceImages"]]
    except Exception as e:
        return {"ok": False, "files": [], "fatal": False, "note": f"FAILED 源图错误：{e}"}

    if meta.get("needs_image") and not send_body.get("image"):
        log(f"  ❌ {model} 需要 1 张源图（用 img=路径），本条按 {mode} 缺图，跳过。")
        return {"ok": False, "files": [], "fatal": False, "note": "FAILED 缺源图"}

    timeout = cfg.get("video_timeout_seconds", 900)
    log(f"  ⏳ 视频生成中（{mode}，最长等 {timeout}s）…")
    # 视频单价高，不做自动重试以免重复扣费
    try:
        req = post_generate_video(send_body, cookie)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        err = ""
        try:
            err = e.read().decode()[:500]
        except Exception:
            pass
        log(f"  HTTP {e.code}: {err}")
        if e.code == 401:
            return {"ok": False, "files": [], "fatal": True, "note": "401"}
        if e.code == 402:
            return {"ok": False, "files": [], "fatal": True, "note": "402"}
        return {"ok": False, "files": [], "fatal": False, "note": f"FAILED HTTP{e.code}"}
    except Exception as e:
        log(f"  请求异常：{e}")
        return {"ok": False, "files": [], "fatal": False, "note": f"FAILED {e}"}

    video_url = payload.get("videoUrl")
    if not video_url:
        log(f"  返回里没有 videoUrl：{json.dumps(payload, ensure_ascii=False)[:300]}")
        return {"ok": False, "files": [], "fatal": False, "note": "FAILED 无videoUrl"}
    fn, path, src = download(video_url, prompt, 0, "video")
    if not args.no_sidecar:
        src_disp = f"data:inline({len(src)} chars)" if src.startswith("data:") else src
        write_sidecar(path, {
            "type": "video", "prompt": prompt, "model": model, "videoMode": mode,
            "videoSeconds": body.get("videoSeconds"), "resolution": body.get("resolution"),
            "width": body["width"], "height": body["height"], "aspectRatio": body["aspectRatio"],
            "source_image": body.get("image"), "reference_images": body.get("referenceImages"),
            "source_url": src_disp, "cover_image": bool(payload.get("imageUrl")),
            "media_id": payload.get("mediaId"),
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        })
    log(f"  ✅ 视频已下载：{fn}")
    return {"ok": True, "files": [fn], "fatal": False, "note": ""}


# ---------- 预检 / CLI ----------

def preflight(cfg, cli, cookie, need_network=True):
    log("—— 预检 ——")
    fatal = False
    for it in validate_config(cfg):
        log(f"  ❌ {it}"); fatal = True

    model = resolve_model({}, cli, cfg)
    if is_video_model(model):
        meta = VIDEO_MODELS[model]
        log(f"  ✅ 默认模型：{model}（视频，约 {meta['cost']} 积分/次，{meta['tags']}）")
    elif model in IMAGE_MODELS:
        meta = IMAGE_MODELS[model]
        log(f"  ✅ 默认模型：{model}（生图，约 {meta['cost']} 积分，{meta['tags']}）")
    else:
        log(f"  ⚠️ 默认模型 {model} 不在已知注册表（可能是新模型）；--list-models 可查在线列表。")

    _, pending = read_prompt_queue()
    if not pending:
        log("  ❌ prompts.txt 里没有待处理的 prompt"); fatal = True
    else:
        log(f"  ✅ 待处理提示词 {len(pending)} 条")

    if not cookie:
        log("  ⚠️ config/cookie.txt 为空 —— gpt-image-2/nano-banana-2/视频 需要登录态，可能 401。")
    else:
        log(f"  ✅ 已加载 cookie（{len(cookie)} 字符）")

    if need_network:
        try:
            req = urllib.request.Request(f"{BASE}/api/time", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            if data.get("timeString"):
                log(f"  ✅ 连通正常，服务器时间串 {data['timeString']}")
            else:
                log("  ⚠️ /api/time 返回异常，token 可能回退本地时间")
        except Exception as e:
            log(f"  ❌ 无法连接 {BASE}/api/time：{e}"); fatal = True

    log("—— 预检结束 ——")
    return not fatal


def parse_args(argv):
    p = argparse.ArgumentParser(prog="dreamify.py", description="Dreamifly 批量生图/生视频",
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("limit", nargs="?", type=int, default=None, help="本次最多处理几条（兼容 ./run.sh 3）")
    p.add_argument("-n", "--limit", dest="limit_flag", type=int, default=None, help="同上，flag 形式")
    p.add_argument("--check", action="store_true", help="只做开跑前预检")
    p.add_argument("--dry-run", action="store_true", help="解析并展示将要生成什么，不调用 API")
    p.add_argument("--list-models", action="store_true", help="列出平台所有可用模型（在线）")
    p.add_argument("--no-sidecar", action="store_true", help="不写 .json 边车")
    p.add_argument("--model")
    p.add_argument("--aspect", dest="aspectRatio")
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--batch", dest="batch_size", type=int)
    p.add_argument("--config")
    p.add_argument("--prompts")
    p.add_argument("--images-dir", dest="images_dir")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.list_models:
        return list_models()

    if args.config:
        PATHS["config"] = os.path.abspath(args.config)
    if args.prompts:
        PATHS["prompts"] = os.path.abspath(args.prompts)
    if args.images_dir:
        PATHS["images"] = os.path.abspath(args.images_dir)

    os.makedirs(PATHS["images"], exist_ok=True)

    try:
        cfg = load_config()
    except FileNotFoundError:
        log(f"❌ 找不到配置文件：{PATHS['config']}"); return 2
    except json.JSONDecodeError as e:
        log(f"❌ 配置文件不是合法 JSON：{e}"); return 2

    cookie = load_cookie()
    cli = {k: getattr(args, k) for k in ("model", "aspectRatio", "width", "height", "batch_size")}

    ok = preflight(cfg, cli, cookie, need_network=not args.dry_run)
    if args.check:
        return 0 if ok else 1
    if not ok:
        log("预检未通过，已终止。修复上述 ❌ 后重跑（或先 --check 复检）。")
        return 1

    _, pending = read_prompt_queue()
    limit = args.limit_flag if args.limit_flag is not None else args.limit
    if limit is not None:
        pending = pending[:limit]

    if args.dry_run:
        log(f"[dry-run] 将处理 {len(pending)} 条：")
        for n, (_, raw) in enumerate(pending, 1):
            prompt, ov = parse_prompt_line(raw)
            model = resolve_model(ov, cli, cfg)
            if is_video_model(model):
                body, mode = build_video_body(prompt, model, cfg, ov, cli)
                extra = mode
                if body.get("videoSeconds"):
                    extra += f" {body['videoSeconds']}s {body.get('resolution', '')}"
                if body.get("image"):
                    extra += " +源图"
                if body.get("referenceImages"):
                    extra += f" +{len(body['referenceImages'])}参考图"
                log(f"  [{n}] 🎬 {prompt[:38]} -> {model} [{extra}]")
            else:
                body, seed = build_body(prompt, cfg, ov, cli)
                tail = f" img={len(body['images'])}" if body["images"] else ""
                log(f"  [{n}] 🖼️ {prompt[:38]} -> {model} {body['width']}x{body['height']} "
                    f"{body['aspectRatio']} x{body['batch_size']} seed={seed}{tail}")
        log("[dry-run] 未调用任何 API。")
        return 0

    log(f"开始：待处理 {len(pending)} 条")
    done_indices = set()

    for n, (line_idx, raw) in enumerate(pending, 1):
        prompt, overrides = parse_prompt_line(raw)
        model = resolve_model(overrides, cli, cfg)
        if is_video_model(model):
            body, mode = build_video_body(prompt, model, cfg, overrides, cli)
            log(f"[{n}/{len(pending)}] 🎬 {prompt[:50]} ({model} / {mode})")
            res = process_video_item(prompt, body, mode, model, cookie, cfg, args)
        else:
            body, seed = build_body(prompt, cfg, overrides, cli)
            log(f"[{n}/{len(pending)}] 🖼️ {prompt[:50]} "
                f"({model} {body['width']}x{body['height']} x{body['batch_size']} seed={seed})")
            res = process_image_item(prompt, body, seed, cookie, cfg, args)

        if res["fatal"]:
            remove_lines(done_indices)
            log("已终止本次（致命错误：见上）。失败项保留在 prompts.txt。")
            return 1
        if res["ok"]:
            append_done(prompt, res["files"])
            done_indices.add(line_idx)
        else:
            append_done(prompt, [], note=res["note"])
        if n < len(pending):
            time.sleep(cfg.get("delay_between_seconds", 5))

    remove_lines(done_indices)
    log(f"完成：成功 {len(done_indices)}/{len(pending)} 条。结果在 images/，记录在 done.txt。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
