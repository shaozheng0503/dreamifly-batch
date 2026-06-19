#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dreamifly 批量生图脚本
- 从 prompts.txt 读取提示词（每行一个，# 开头/空行忽略）
- 调用 https://dreamifly.com/api/generate 生成图片
- 把返回的图片下载到 images/，成功的 prompt 移到 done.txt
鉴权：
- Authorization: Bearer MD5(apiKey + 服务器时间串)   —— 自动从 /api/time 取时间，自己算
- Cookie: 你的登录态                                  —— 读 config/cookie.txt（gpt-image-2 必须登录）
"""

import json
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

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS_FILE = os.path.join(HERE, "prompts.txt")
DONE_FILE = os.path.join(HERE, "done.txt")
IMAGES_DIR = os.path.join(HERE, "images")
CONFIG_FILE = os.path.join(HERE, "config", "config.json")
COOKIE_FILE = os.path.join(HERE, "config", "cookie.txt")
LOG_FILE = os.path.join(HERE, "run.log")


def log(msg):
    line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_cookie():
    if not os.path.exists(COOKIE_FILE):
        return ""
    val = ""
    for ln in open(COOKIE_FILE, encoding="utf-8"):
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


def read_prompt_queue():
    """返回 (所有行, 待处理 prompt 行的索引->文本)。"""
    if not os.path.exists(PROMPTS_FILE):
        return [], []
    lines = open(PROMPTS_FILE, encoding="utf-8").read().splitlines()
    pending = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s and not s.startswith("#"):
            pending.append((i, s))
    return lines, pending


def remove_lines(done_indices):
    """从 prompts.txt 删除已成功的行，其余（含注释）原样保留。"""
    lines = open(PROMPTS_FILE, encoding="utf-8").read().splitlines()
    kept = [ln for i, ln in enumerate(lines) if i not in done_indices]
    with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))


def append_done(prompt, filenames, note=""):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts}\t{prompt}\t{', '.join(filenames) or note}\n")


def slugify(text, maxlen=40):
    text = re.sub(r"[一-龥]+", lambda m: m.group(0), text)
    text = re.sub(r"[^\w一-龥]+", "_", text).strip("_")
    return (text[:maxlen] or "image")


def build_body(prompt, cfg):
    body = {
        "prompt": prompt,
        "width": cfg.get("width", 1024),
        "height": cfg.get("height", 1024),
        "seed": int.from_bytes(os.urandom(4), "big") % 100000000,
        "batch_size": cfg.get("batch_size", 1),
        "model": cfg.get("model", "gpt-image-2"),
        "images": [],
        "aspectRatio": cfg.get("aspectRatio", "1:1"),
    }
    if cfg.get("steps"):
        body["steps"] = cfg["steps"]
    if cfg.get("negative_prompt"):
        body["negative_prompt"] = cfg["negative_prompt"]
    return body


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


def download(url, prompt, idx):
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = BASE + url
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"
    fn = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{slugify(prompt)}_{idx}{ext}"
    path = os.path.join(IMAGES_DIR, fn)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())
    return fn


def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    cfg = load_config()
    cookie = load_cookie()
    if not cookie:
        log("⚠️  config/cookie.txt 里还没有 cookie，gpt-image-2 需要登录态，可能会 401。")

    lines, pending = read_prompt_queue()
    if not pending:
        log("prompts.txt 里没有待处理的 prompt，结束。")
        return

    # 可选：命令行限制本次最多处理几条，例如  python3 dreamify.py 1
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    if limit is not None:
        pending = pending[:limit]

    log(f"开始：待处理 {len(pending)} 条，模型 {cfg.get('model')} {cfg.get('width')}x{cfg.get('height')}")
    done_indices = set()
    max_retries = cfg.get("max_retries", 2)

    for n, (line_idx, prompt) in enumerate(pending, 1):
        log(f"[{n}/{len(pending)}] 生成中：{prompt[:60]}")
        body = build_body(prompt, cfg)
        ok = False
        for attempt in range(max_retries + 1):
            try:
                req = post_generate(body, cookie)
                with urllib.request.urlopen(req, timeout=cfg.get("request_timeout_seconds", 300)) as r:
                    payload = json.loads(r.read().decode())
                urls = extract_image_urls(payload)
                if not urls:
                    log(f"  返回里没找到图片 URL：{json.dumps(payload, ensure_ascii=False)[:300]}")
                    break
                files = []
                for i, u in enumerate(urls):
                    files.append(download(u, prompt, i))
                log(f"  ✅ 下载 {len(files)} 张：{', '.join(files)}")
                append_done(prompt, files)
                done_indices.add(line_idx)
                ok = True
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
                    return
                if code == 402:
                    log("  ❌ 账号积分不足 —— 终止本次。")
                    remove_lines(done_indices)
                    return
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
        if not ok:
            append_done(prompt, [], note="FAILED（保留在 prompts.txt，下次重试）")
        # 节流
        if n < len(pending):
            time.sleep(cfg.get("delay_between_seconds", 5))

    remove_lines(done_indices)
    log(f"完成：成功 {len(done_indices)}/{len(pending)} 条。图片在 images/，记录在 done.txt。")


if __name__ == "__main__":
    main()
