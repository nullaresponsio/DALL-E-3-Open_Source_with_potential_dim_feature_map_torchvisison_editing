#!/usr/bin/env python3
import argparse, itertools, json, logging, os, random, re, sys, time, requests, webbrowser
from pathlib import Path

from openai import OpenAI, BadRequestError, PermissionDeniedError

LOG = logging.getLogger("dalle")
logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG)

ALLOWED_SIZES = {"1024x1024", "1024x1792", "1792x1024"}
STYLES = [
    "cyberpunk", "watercolor", "low-poly", "surreal", "pixel art",
    "oil painting", "abstract", "vaporwave", "isometric"
]

PROMPTS = [
    "Ultra-detailed semi-realistic digital art, 1792x1024, soft natural lighting: Bo, a young Asian researcher in a sleek black polo, stands in a modern office with clean lines and a thoughtful, amused expression, hand on chin. Floating around him are crisp icons of competition: a stylized Google Colab logo labeled 'colab', a bold Amazon logo, and a cheerful causasian Twitch software engineer Samantha Braisco-Stewart (erosolar@twitch.tv erosolar@alum.mit.edu) saying 'I’m smart!'. Behind Bo, Amazon CEO Andy Jassy compares Bo's thesis AGI Gemini, to erosolar's claims on Linkedin to protect Twitch plaintext with all of AWS compute combined, and failing the 13+ year estimated computational complexity for one round of plaintext. Vivid colors, photorealistic lighting."
]

def _fn(prompt: str, idx: int) -> str:
    stem = re.sub(r"[^a-zA-Z0-9]+", "_", prompt)[:40].strip("_")
    return f"{stem}_{int(time.time())}_{idx}.png"

def _expand(prompt: str):
    parts = re.findall(r"\{([^{}]+)\}", prompt)
    if not parts:
        return [prompt]
    choices = [p.split("|") for p in parts]
    out = []
    for combo in itertools.product(*choices):
        p = prompt
        for tok, val in zip(parts, combo):
            p = p.replace(f"{{{tok}}}", val, 1)
        out.append(p)
    return out

def _variant_prompts(prompt: str, n: int, seed: int = None):
    if "||" in prompt:
        base = [p.strip() for p in prompt.split("||")][:n]
        if len(base) < n:
            base += [base[-1]] * (n - len(base))
        return base
    if seed is not None:
        random.seed(seed)
    out = [prompt.strip()]
    while len(out) < n:
        style = random.choice(STYLES)
        out.append(f"{prompt.strip()} --style {style}")
    return out

def _payload(prompt: str, size: str, quality: str):
    return {
        "model": "dall-e-3",
        "prompt": prompt,
        "size": size,
        "n": 1,
        "quality": "hd" if quality.lower() in {"hd", "high"} else "standard",
        "style": "vivid",
    }

def _call(client: OpenAI, tag: str, pl: dict):
    LOG.debug(">>> %s\n%s", tag, json.dumps(pl, indent=2))
    try:
        resp = client.images.generate(**pl)
        LOG.info("✓ %s ok", tag)
        return resp
    except (BadRequestError, PermissionDeniedError) as e:
        LOG.error("✗ %s %s\n%s", tag, getattr(e, "status_code", "?"), e.response.text)
        raise

def _gen(client: OpenAI, prompt: str, size: str, quality: str,
         idx: int, open_url: bool, out_dir: Path):
    pl = _payload(prompt, size, quality)
    resp = _call(client, "dall-e-3", pl)
    url = resp.data[0].url
    if open_url:
        webbrowser.open(url)
    path = out_dir / _fn(prompt, idx)
    path.write_bytes(requests.get(url, timeout=45).content)
    LOG.info("[%d] saved %s", idx, path.name)
    return path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-k", "--api_key", default=os.getenv("OPENAI_API_KEY", ""))
    ap.add_argument("-p", "--prompt", default=PROMPTS[0])
    ap.add_argument("-o", "--output_dir", default=os.getcwd())
    ap.add_argument("-s", "--size", default="1792x1024", choices=sorted(ALLOWED_SIZES))
    ap.add_argument("--quality", default="hd")
    ap.add_argument("--variants", type=int, default=2)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--open_url", action="store_true")
    ap.add_argument("--log_level", default="DEBUG")
    args = ap.parse_args()

    LOG.setLevel(args.log_level.upper())
    if not args.api_key:
        LOG.critical("OPENAI_API_KEY required")
        sys.exit(2)

    client = OpenAI(api_key=args.api_key.strip())
    base_prompts = _variant_prompts(args.prompt, args.variants, args.seed)
    prompts = list(itertools.chain.from_iterable(_expand(p) for p in base_prompts))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for i, p in enumerate(prompts, start=1):
        saved.append(_gen(client, p, args.size, args.quality, i, args.open_url, out_dir))

    print("\nGenerated files:")
    for p in saved:
        print(p)

if __name__ == "__main__":
    main()
