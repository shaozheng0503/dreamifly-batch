#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dreamifly 批量生图脚本
- 从 prompts.txt 读取提示词（每行一个，# 开头/空行忽略）
- 调用 https://dreamifly.com/api/generate 生成图片
- 把返回的图片下载到 images/，成功的 prompt 移到 done.txt
- 每张图旁边写一个 .json 边车文件，记录 seed/参数，便于复现

鉴权：
- Authorization: Bearer MD5(apiKey + 服务器时间串)   —— 自动从 /api/time 取时间，自己算
- Cookie: 你的登录态                                  —— 读 config/cookie.txt（gpt-image-2 必须登录）

提示词内联参数（用 | 分隔，可任意组合，覆盖 config.json）：
    a cat on the moon | 16:9 | x2 | seed=123 | model=gpt-image-2 | 1024x768 | neg=blurry
    - 16:9        宽高比 aspectRatio
    - x2          本条生成 2 张 (batch_size)
    - 1024x768    宽x高
    - seed=123    固定随机种子
    - model=...   覆盖模型
    - neg=...     负向提示词
    - img=URL     参考图（图生图，实验性，可逗号分隔多张）

常用命令：
    python3 dreamify.py            # 跑完 prompts.txt 全部
    python3 dreamify.py 3          # 只跑前 3 条
    python3 dreamify.py --check    # 只做开跑前预检，不生成
    python3 dreamify.py --dry-run  # 解析并展示将要生成什么，不调用 API
    python3 dreamify.py --aspect 16:9 --batch 2   # 全局覆盖参数
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import hashlib
import datetime
import urllib.request
import urllib.error

# 前端限制：单张参考图 ≤ 10MB（0xa00000）
MAX_IMAGE_BYTES = 10 * 1024 * 1024

BASE = "https://dreamifly.com"
# NEXT_PUBLIC_API_KEY —— 这是打进前端、发给每个浏览器的公开标识，非私密凭证
API_KEY = "6h^&+h4567mk&&9-%@"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS_FILE = os.path.join(HERE, "prompts.txt")
DONE_FILE = os.path.join(HERE, "done.txt")
IMAGES_DIR = os.path.join(HERE, "images")
CONFIG_FILE = os.path.join(HERE, "config", "config.json")
COOKIE_FILE = os.path.join(HERE, "config", "cookie.txt")
LOG_FILE = os.path.join(HERE, "run.log")

# 可被命令行覆盖的运行期路径（main 里按 args 重设）
PATHS = {
    "prompts": PROMPTS_FILE,
    "done": DONE_FILE,
    "images": IMAGES_DIR,
    "config": CONFIG_FILE,
    "cookie": COOKIE_FILE,
}

# config.json 字段校验规则：键 -> (类型, 校验函数 或 None)
CONFIG_SCHEMA = {
    "model": (str, lambda v: len(v) > 0),
    "width": (int, lambda v: 64 <= v <= 4096),
    "height": (int, lambda v: 64 <= v <= 4096),
    "aspectRatio": (str, lambda v: bool(re.fullmatch(r"\d+:\d+", v))),
    "batch_size": (int, lambda v: 1 <= v <= 4),
    "delay_between_seconds": ((int, float), lambda v: v >= 0),
    "max_retries": (int, lambda v: 0 <= v <= 10),
    "request_timeout_seconds": ((int, float), lambda v: v > 0),
}


def log(msg):
    line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_config():
    with open(PATHS["config"], encoding="utf-8") as f:
        return json.load(f)


def validate_config(cfg):
    """返回问题列表（空列表表示通过）。"""
    issues = []
    for key, (types, check) in CONFIG_SCHEMA.items():
        if key not in cfg or cfg[key] is None:
            # 这些有默认值，缺省可接受；只对明显必需的提示
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
    val = ""
    for ln in open(path, encoding="utf-8"):
        s = ln.strip()
        if s and not s.startswith("#"):
            val = s
            break
    return val


def get_server_timestring():
    """拿服务器时间串（YYYYMMDDHHMM）；失败则回退本地 UTC。"""
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
    salt = get_server_timestring()
    return hashlib.md5((API_KEY + salt).encode("utf-8")).hexdigest()


def parse_prompt_line(line):
    """把一行提示词拆成 (干净提示词, 覆盖项 dict)。
    语法：提示词 | 16:9 | x2 | 1024x768 | seed=123 | model=... | neg=... | img=URL,URL
    无法识别的片段会被忽略（并提示）。
    """
    parts = [p.strip() for p in line.split("|")]
    prompt = parts[0].strip()
    overrides = {}
    for seg in parts[1:]:
        if not seg:
            continue
        low = seg.lower()
        if re.fullmatch(r"\d+:\d+", seg):
            overrides["aspectRatio"] = seg
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
        elif low.startswith("img="):
            urls = [u.strip() for u in seg.split("=", 1)[1].split(",") if u.strip()]
            overrides["images"] = urls
        else:
            log(f"  ⚠️ 忽略无法识别的内联参数：{seg!r}")
    return prompt, overrides


def read_prompt_queue():
    """返回 (所有行, [(行索引, 原始行)] 待处理列表)。"""
    if not os.path.exists(PATHS["prompts"]):
        return [], []
    lines = open(PATHS["prompts"], encoding="utf-8").read().splitlines()
    pending = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s and not s.startswith("#"):
            pending.append((i, s))
    return lines, pending


def remove_lines(done_indices):
    """从 prompts.txt 删除已成功的行，其余（含注释）原样保留。"""
    lines = open(PATHS["prompts"], encoding="utf-8").read().splitlines()
    kept = [ln for i, ln in enumerate(lines) if i not in done_indices]
    with open(PATHS["prompts"], "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))


def append_done(prompt, filenames, note=""):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(PATHS["done"], "a", encoding="utf-8") as f:
        f.write(f"{ts}\t{prompt}\t{', '.join(filenames) or note}\n")


def slugify(text, maxlen=40):
    text = re.sub(r"[一-龥]+", lambda m: m.group(0), text)
    text = re.sub(r"[^\w一-龥]+", "_", text).strip("_")
    return (text[:maxlen] or "image")


def build_body(prompt, cfg, overrides=None, cli=None):
    """构造请求体并返回 (body, seed)。优先级：内联 > 命令行 > config。"""
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

    body = {
        "prompt": prompt,
        "width": pick("width", 1024),
        "height": pick("height", 1024),
        "seed": seed,
        "batch_size": pick("batch_size", 1),
        "model": pick("model", "gpt-image-2"),
        "images": overrides.get("images", []),
        "aspectRatio": pick("aspectRatio", "1:1"),
    }
    steps = pick("steps", None)
    if steps:
        body["steps"] = steps
    neg = pick("negative_prompt", "")
    if neg:
        body["negative_prompt"] = neg
    return body, seed


def post_generate(body, cookie):
    token = make_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": UA,
        "Referer": f"{BASE}/create?model={body.get('model')}",
        "Origin": BASE,
    }
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(
        f"{BASE}/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    return req


def extract_image_urls(payload):
    """从返回里挖出图片 URL（兼容 imageUrl / images[] 等形态）。"""
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
    # 去重保序
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def encode_reference_image(ref):
    """把参考图统一转成 API 要求的「无前缀 base64 字符串」。
    支持：本地文件路径 / http(s) URL / data:URI。
    """
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


def write_sidecar(image_path, meta):
    """在图片旁写 <name>.json 记录生成参数，便于复现。"""
    side = os.path.splitext(image_path)[0] + ".json"
    try:
        with open(side, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"  ⚠️ 写 metadata 边车失败：{e}")


def download(url, prompt, idx):
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = BASE + url
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"
    fn = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{slugify(prompt)}_{idx}{ext}"
    path = os.path.join(PATHS["images"], fn)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())
    return fn, path, url


def preflight(cfg, cookie, need_network=True):
    """开跑前预检：配置/提示词/cookie/连通性。返回 (能否继续, 是否有警告)。"""
    log("—— 预检 ——")
    fatal = False
    warned = False

    # 1) 配置校验
    issues = validate_config(cfg)
    if issues:
        for it in issues:
            log(f"  ❌ {it}")
        fatal = True
    else:
        log(f"  ✅ 配置有效：{cfg.get('model')} {cfg.get('width')}x{cfg.get('height')} "
            f"{cfg.get('aspectRatio')} x{cfg.get('batch_size', 1)}")

    # 2) 提示词队列
    _, pending = read_prompt_queue()
    if not pending:
        log("  ❌ prompts.txt 里没有待处理的 prompt")
        fatal = True
    else:
        log(f"  ✅ 待处理提示词 {len(pending)} 条")

    # 3) cookie
    if not cookie:
        log("  ⚠️ config/cookie.txt 为空或不存在 —— gpt-image-2 需要登录态，可能 401。"
            "（参考 config/cookie.txt.example）")
        warned = True
    else:
        log(f"  ✅ 已加载 cookie（{len(cookie)} 字符）")

    # 4) 连通性（顺带验证能否取到服务器时间串、算 token）
    if need_network:
        try:
            req = urllib.request.Request(f"{BASE}/api/time", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            if data.get("timeString"):
                log(f"  ✅ 连通正常，服务器时间串 {data['timeString']}")
            else:
                log("  ⚠️ /api/time 返回异常，token 计算可能回退本地时间")
                warned = True
        except Exception as e:
            log(f"  ❌ 无法连接 {BASE}/api/time：{e}")
            fatal = True

    log("—— 预检结束 ——")
    return (not fatal), warned


def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="dreamify.py", description="Dreamifly 批量生图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("limit", nargs="?", type=int, default=None,
                   help="本次最多处理几条（位置参数，兼容 ./run.sh 3）")
    p.add_argument("-n", "--limit", dest="limit_flag", type=int, default=None,
                   help="同上，flag 形式；与位置参数同时给时以 flag 为准")
    p.add_argument("--check", action="store_true", help="只做开跑前预检，不生成")
    p.add_argument("--dry-run", action="store_true", help="解析并展示将要生成什么，不调用 API")
    p.add_argument("--no-sidecar", action="store_true", help="不写每张图的 .json 边车文件")
    # 全局覆盖（低于内联参数、高于 config）
    p.add_argument("--model")
    p.add_argument("--aspect", dest="aspectRatio")
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--batch", dest="batch_size", type=int)
    # 路径覆盖
    p.add_argument("--config")
    p.add_argument("--prompts")
    p.add_argument("--images-dir", dest="images_dir")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    # 应用路径覆盖
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
        log(f"❌ 找不到配置文件：{PATHS['config']}")
        return 2
    except json.JSONDecodeError as e:
        log(f"❌ 配置文件不是合法 JSON：{e}")
        return 2

    cookie = load_cookie()

    # CLI 全局覆盖
    cli = {k: getattr(args, k) for k in ("model", "aspectRatio", "width", "height", "batch_size")}

    # 预检
    ok, _ = preflight(cfg, cookie, need_network=not args.dry_run)
    if args.check:
        return 0 if ok else 1
    if not ok:
        log("预检未通过，已终止。修复上述 ❌ 后重跑（或先 --check 复检）。")
        return 1

    lines, pending = read_prompt_queue()
    limit = args.limit_flag if args.limit_flag is not None else args.limit
    if limit is not None:
        pending = pending[:limit]

    if args.dry_run:
        log(f"[dry-run] 将处理 {len(pending)} 条，以下是解析结果：")
        for n, (_, raw) in enumerate(pending, 1):
            prompt, ov = parse_prompt_line(raw)
            body, seed = build_body(prompt, cfg, ov, cli)
            log(f"  [{n}] {prompt[:50]} -> {body['model']} {body['width']}x{body['height']} "
                f"{body['aspectRatio']} x{body['batch_size']} seed={seed}"
                + (f" img={len(body['images'])}张参考" if body['images'] else ""))
        log("[dry-run] 未调用任何 API。")
        return 0

    log(f"开始：待处理 {len(pending)} 条")
    done_indices = set()
    max_retries = cfg.get("max_retries", 2)

    for n, (line_idx, raw) in enumerate(pending, 1):
        prompt, overrides = parse_prompt_line(raw)
        body, seed = build_body(prompt, cfg, overrides, cli)
        log(f"[{n}/{len(pending)}] 生成中：{prompt[:60]} "
            f"({body['model']} {body['width']}x{body['height']} x{body['batch_size']} seed={seed})")

        # 图生图：把参考图编码为无前缀 base64 后再发（body 里保留原始引用给边车记录）
        send_body = body
        if body["images"]:
            try:
                encoded = [encode_reference_image(x) for x in body["images"]]
                send_body = dict(body)
                send_body["images"] = encoded
                log(f"  🖼️ 已编码 {len(encoded)} 张参考图（图生图）")
            except Exception as e:
                log(f"  ❌ 参考图处理失败：{e} —— 跳过本条。")
                append_done(prompt, [], note=f"FAILED 参考图错误：{e}")
                if n < len(pending):
                    time.sleep(cfg.get("delay_between_seconds", 5))
                continue

        ok_item = False
        for attempt in range(max_retries + 1):
            try:
                req = post_generate(send_body, cookie)
                with urllib.request.urlopen(req, timeout=cfg.get("request_timeout_seconds", 300)) as r:
                    payload = json.loads(r.read().decode())
                urls = extract_image_urls(payload)
                if not urls:
                    log(f"  返回里没找到图片 URL：{json.dumps(payload, ensure_ascii=False)[:300]}")
                    break
                files = []
                for i, u in enumerate(urls):
                    fn, path, src = download(u, prompt, i)
                    files.append(fn)
                    if not args.no_sidecar:
                        # API 可能内联返回 data:URI；别把整段 base64 写进边车
                        src_disp = (f"data:inline({len(src)} chars)"
                                    if src.startswith("data:") else src)
                        write_sidecar(path, {
                            "prompt": prompt,
                            "model": body["model"],
                            "width": body["width"],
                            "height": body["height"],
                            "aspectRatio": body["aspectRatio"],
                            "seed": seed,
                            "batch_index": i,
                            "source_url": src_disp,
                            "reference_images": body["images"],
                            "negative_prompt": body.get("negative_prompt", ""),
                            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                        })
                log(f"  ✅ 下载 {len(files)} 张：{', '.join(files)}")
                append_done(prompt, files)
                done_indices.add(line_idx)
                ok_item = True
                break
            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode()[:400]
                except Exception:
                    pass
                code = e.code
                log(f"  HTTP {code}: {err_body}")
                if code == 401:
                    log("  ❌ 未登录/登录失效 —— 请更新 config/cookie.txt 后重跑。终止本次。")
                    remove_lines(done_indices)
                    return 1
                if code == 402:
                    log("  ❌ 账号积分不足 —— 终止本次。")
                    remove_lines(done_indices)
                    return 1
                if code == 429:
                    wait = 30 * (attempt + 1)
                    log(f"  限流，等待 {wait}s 重试…")
                    time.sleep(wait)
                    continue
                if 500 <= code < 600 and attempt < max_retries:
                    time.sleep(5)
                    continue
                break  # 其他错误不重试
            except Exception as e:
                log(f"  请求异常（第 {attempt+1} 次）：{e}")
                if attempt < max_retries:
                    time.sleep(5)
                    continue
                break
        if not ok_item:
            append_done(prompt, [], note="FAILED（保留在 prompts.txt，下次重试）")
        # 节流
        if n < len(pending):
            time.sleep(cfg.get("delay_between_seconds", 5))

    remove_lines(done_indices)
    log(f"完成：成功 {len(done_indices)}/{len(pending)} 条。图片在 images/，记录在 done.txt。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
