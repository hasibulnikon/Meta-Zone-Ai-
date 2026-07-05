import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, BooleanVar, IntVar
import csv, subprocess, os, sys, threading, datetime, json, base64, socket, queue
import urllib.request, urllib.error
from PIL import Image

# Drag-and-drop via tkinterdnd2.
# When running as a PyInstaller EXE (sys.frozen=True), the package is
# bundled alongside the binary — never try to pip-install in that case.
# When running as a plain .py, auto-install if missing.
def _ensure_tkdnd():
    if getattr(sys, 'frozen', False):
        # Add the bundled tkinterdnd2 folder to sys.path so the import works
        bundled = os.path.join(sys._MEIPASS, 'tkinterdnd2')
        if bundled not in sys.path:
            sys.path.insert(0, bundled)
        return
    # Plain .py — install silently if missing
    try:
        import tkinterdnd2  # noqa: F401
    except ImportError:
        import subprocess as _sp
        try:
            _sp.check_call([sys.executable, "-m", "pip", "install",
                            "tkinterdnd2", "--quiet"], timeout=60)
        except Exception:
            pass

_ensure_tkdnd()

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    DND_FILES = None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# ── Shared neutrals ────────────────────────────────────────────────────
TXT   = "#eef0fb"; TXT2 = "#a7acc8"; TXT3 = "#5a5f82"
RED   = "#f07878"; RED2 = "#2a1010"
AMB   = "#f5c842"; AMB2 = "#2a2000"
GRN   = "#4dd96e"; GRN2 = "#1c5c30"; GRN3 = "#0a2614"
BLU   = "#5b9ef5"; BLU2 = "#16345e"; BLU3 = "#2563eb"
CYAN  = "#3dd9c4"

# ── Metadata-AI theme (deep blue) ──────────────────────────────────────
META_BG   = "#020314"; META_BG2 = "#06081f"; META_BG3 = "#0b0f2c"
META_CARD = "#080a22"; META_BDR = "#1c2350"; META_BDR2 = "#2a3370"
META_ACC  = "#2f5ce8"; META_ACC2= "#1d3aa8"; META_ACC3= "#0f1d4a"

# ── Embedder theme (deep green) ─────────────────────────────────────────
EMB_BG    = "#020c08"; EMB_BG2  = "#04140d"; EMB_BG3  = "#071e14"
EMB_CARD  = "#04140d"; EMB_BDR  = "#163524" ; EMB_BDR2 = "#1d4530"
EMB_ACC   = "#2a9d52"; EMB_ACC2 = "#1b6e38"; EMB_ACC3 = "#0c2a17"

# Generic aliases used before a theme context is known (title bar, status bar)
BG  = META_BG; BG2 = META_BG2; BG3 = META_BG3
CARD= META_CARD; BDR = META_BDR; BDR2 = META_BDR2
LOG_BG = "#010208"

# ── AI Providers — short display names mapped to real model IDs ───────
AI_PROVIDERS = {
    "OpenRouter": {
        "models": [
            ("Qwen 2.5 VL 72B",      "qwen/qwen2.5-vl-72b-instruct:free"),
            ("Qwen 2.5 VL 32B",      "qwen/qwen2.5-vl-32b-instruct:free"),
            ("Gemini 2.0 Flash",     "google/gemini-2.0-flash-exp:free"),
            ("Llama 4 Maverick",     "meta-llama/llama-4-maverick:free"),
            ("Llama 4 Scout",        "meta-llama/llama-4-scout:free"),
            ("Mistral Small 3.1",    "mistralai/mistral-small-3.1-24b-instruct:free"),
        ],
        "key_url": "https://openrouter.ai/keys",
        "key_hint": "Get free key → openrouter.ai",
        "validate": "openrouter",
    },
    "Gemini": {
        "models": [
            ("Gemini 2.5 Flash",     "gemini-2.5-flash"),
            ("Gemini 2.0 Flash",     "gemini-2.0-flash"),
            ("Gemini 1.5 Flash",     "gemini-1.5-flash"),
            ("Gemini 1.5 Pro",       "gemini-1.5-pro"),
        ],
        "key_url": "https://aistudio.google.com/app/apikey",
        "key_hint": "Get free key → aistudio.google.com",
        "validate": "gemini",
    },
    "Mistral": {
        "models": [
            ("Pixtral 12B",  "pixtral-12b-2409"),
            ("Pixtral Large","pixtral-large-2411"),
        ],
        "key_url": "https://console.mistral.ai/api-keys/",
        "key_hint": "Get key → console.mistral.ai",
        "validate": "mistral",
    },
    "Groq": {
        "models": [
            ("Llama 4 Scout 17B",    "meta-llama/llama-4-scout-17b-16e-instruct"),
            ("Llama 4 Maverick 17B", "meta-llama/llama-4-maverick-17b-128e-instruct"),
        ],
        "key_url": "https://console.groq.com/keys",
        "key_hint": "Get free key → console.groq.com",
        "validate": "groq",
    },
    "OpenAI": {
        "models": [
            ("GPT-4o",      "gpt-4o"),
            ("GPT-4o Mini", "gpt-4o-mini"),
            ("GPT-4.1 Nano","gpt-4.1-nano"),
        ],
        "key_url": "https://platform.openai.com/api-keys",
        "key_hint": "Get key → platform.openai.com",
        "validate": "openai",
    },
    "Claude": {
        "models": [
            ("Claude Haiku 4.5",  "claude-haiku-4-5-20251001"),
            ("Claude Sonnet 4.6", "claude-sonnet-4-6"),
        ],
        "key_url": "https://console.anthropic.com/settings/keys",
        "key_hint": "Get key → console.anthropic.com",
        "validate": "claude",
    },
}

PLATFORM_RULES = {
    "General":      {"kw": 49, "title": 150, "desc": 250},
    "Adobe Stock":  {"kw": 49, "title": 150, "desc": 250},
    "Shutterstock": {"kw": 49, "title": 200, "desc": 200},
    "Getty Images": {"kw": 49, "title": 200, "desc": 500},
    "Freepik":      {"kw": 30, "title": 150, "desc": 200},
    "Pond5":        {"kw": 49, "title": 200, "desc": 500},
    "iStock":       {"kw": 49, "title": 200, "desc": 200},
}

CONTENT_SUFFIXES = {
    "Auto Detect":       "",
    "JPG":               "",
    "Vector":            "This is a vector illustration.",
    "Transparent PNG":   "isolated on transparent background",
    "White Background":  "isolated on solid white background",
}

IMAGE_EXTS  = {'.jpg','.jpeg','.png','.gif','.webp','.tiff','.tif'}
VECTOR_EXTS = {'.svg','.eps','.ai'}
VIDEO_EXTS  = {'.mp4','.mov'}
ALL_SUPPORTED_EXTS = IMAGE_EXTS | VECTOR_EXTS | VIDEO_EXTS

def model_label(provider, model_id):
    for label, mid in AI_PROVIDERS.get(provider, {}).get("models", []):
        if mid == model_id:
            return label
    return model_id.split("/")[-1].split(":")[0][:22]

def model_id_from_label(provider, label):
    for lbl, mid in AI_PROVIDERS.get(provider, {}).get("models", []):
        if lbl == label:
            return mid
    return label

# ── Prefs ──────────────────────────────────────────────────────────────
def prefs_path():
    base = os.path.dirname(sys.executable if getattr(sys,'frozen',False)
                           else os.path.abspath(__file__))
    return os.path.join(base,'prefs.json')

def load_prefs():
    path = prefs_path()
    try:
        with open(path) as f: return json.load(f)
    except Exception:
        # Corrupted or missing prefs.json — preserve the broken file for
        # inspection instead of silently discarding it, then start fresh.
        if os.path.exists(path):
            try: os.replace(path, path + ".corrupt")
            except Exception: pass
        return {}

def save_prefs(p):
    """Atomic write: write to a temp file then rename over the real one.
    This prevents prefs.json from ever being left half-written if the
    app freezes, crashes, or is killed mid-save — which is what silently
    drops stored API keys."""
    path = prefs_path()
    tmp = path + ".tmp"
    try:
        with open(tmp,'w') as f:
            json.dump(p,f,indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except Exception: pass

# ── ExifTool ───────────────────────────────────────────────────────────
def find_exiftool():
    if getattr(sys,'frozen',False):
        b = os.path.join(sys._MEIPASS,'exiftool_pkg','exiftool.exe')
        if os.path.exists(b): return b
    base = os.path.dirname(sys.executable if getattr(sys,'frozen',False)
                           else os.path.abspath(__file__))
    for n in ['exiftool.exe','exiftool']:
        p = os.path.join(base,n)
        if os.path.exists(p): return p
    for d in os.environ.get('PATH','').split(os.pathsep):
        for n in ['exiftool.exe','exiftool']:
            p = os.path.join(d,n)
            if os.path.exists(p): return p
    return None

def find_file(folder,name,match_ext):
    exact=os.path.join(folder,name)
    if os.path.exists(exact): return exact
    if match_ext:
        base=os.path.splitext(name)[0]
        try:
            for f in os.listdir(folder):
                if os.path.splitext(f)[0].lower()==base.lower():
                    return os.path.join(folder,f)
        except: pass
    return None

def find_recursive(folder,name,match_ext):
    r=find_file(folder,name,match_ext)
    if r: return r
    try:
        for root,dirs,files in os.walk(folder):
            if root==folder: continue
            r=find_file(root,name,match_ext)
            if r: return r
    except: pass
    return None

# ── AI Engine ──────────────────────────────────────────────────────────
def img_to_b64(path):
    with open(path,'rb') as f: data=f.read()
    ext=os.path.splitext(path)[1].lower()
    mime={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png',
          '.gif':'image/gif','.webp':'image/webp',
          '.tiff':'image/tiff','.tif':'image/tiff'}.get(ext,'image/jpeg')
    return base64.b64encode(data).decode(),mime

def _post(url,body,headers,timeout=90):
    req=urllib.request.Request(url,data=json.dumps(body).encode(),
                               headers=headers,method="POST")
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            raw=e.read().decode(errors='replace')
            try: msg=json.loads(raw).get("error",{}).get("message") or raw[:300]
            except: msg=raw[:300]
        except: msg=str(e)
        raise RuntimeError(f"HTTP {e.code}: {msg}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {str(e.reason)}")

def call_gemini(key,model,path,prompt):
    b64,mime=img_to_b64(path)
    r=_post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        {"contents":[{"parts":[{"inline_data":{"mime_type":mime,"data":b64}},{"text":prompt}]}],
         "generationConfig":{"temperature":0.3,"maxOutputTokens":1400}},
        {"Content-Type":"application/json"})
    try: return r["candidates"][0]["content"]["parts"][0]["text"]
    except: raise RuntimeError(f"Gemini parse error: {str(r)[:200]}")

def call_openrouter(key,model,path,prompt):
    b64,mime=img_to_b64(path)
    r=_post("https://openrouter.ai/api/v1/chat/completions",
        {"model":model,"max_tokens":1400,"messages":[{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
            {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}",
         "HTTP-Referer":"https://metazone.app","X-Title":"Meta Zone"})
    try: return r["choices"][0]["message"]["content"]
    except: raise RuntimeError(f"OpenRouter parse error: {str(r)[:200]}")

def call_claude(key,model,path,prompt):
    b64,mime=img_to_b64(path)
    r=_post("https://api.anthropic.com/v1/messages",
        {"model":model,"max_tokens":1400,"messages":[{"role":"user","content":[
            {"type":"image","source":{"type":"base64","media_type":mime,"data":b64}},
            {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"})
    try: return r["content"][0]["text"]
    except: raise RuntimeError(f"Claude parse error: {str(r)[:200]}")

def call_openai(key,model,path,prompt):
    b64,mime=img_to_b64(path)
    r=_post("https://api.openai.com/v1/chat/completions",
        {"model":model,"max_tokens":1400,"messages":[{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
            {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    try: return r["choices"][0]["message"]["content"]
    except: raise RuntimeError(f"OpenAI parse error: {str(r)[:200]}")

def call_groq(key,model,path,prompt):
    b64,mime=img_to_b64(path)
    r=_post("https://api.groq.com/openai/v1/chat/completions",
        {"model":model,"max_tokens":1400,"messages":[{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
            {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    try: return r["choices"][0]["message"]["content"]
    except: raise RuntimeError(f"Groq parse error: {str(r)[:200]}")

def call_mistral(key,model,path,prompt):
    b64,mime=img_to_b64(path)
    r=_post("https://api.mistral.ai/v1/chat/completions",
        {"model":model,"max_tokens":1400,"messages":[{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
            {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    try: return r["choices"][0]["message"]["content"]
    except: raise RuntimeError(f"Mistral parse error: {str(r)[:200]}")

CALLERS={"Gemini":call_gemini,"OpenRouter":call_openrouter,"Claude":call_claude,
         "OpenAI":call_openai,"Groq":call_groq,"Mistral":call_mistral}

# ── API key validation (lightweight, cheap calls) ──────────────────────
def validate_key(provider, key):
    """Returns (ok: bool, message: str)"""
    key = key.strip()
    if not key:
        return False, "Empty key"
    try:
        if provider == "Gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=12) as r:
                json.loads(r.read())
            return True, "Valid"
        elif provider == "OpenRouter":
            req = urllib.request.Request("https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {key}"}, method="GET")
            with urllib.request.urlopen(req, timeout=12) as r:
                json.loads(r.read())
            return True, "Valid"
        elif provider == "Mistral":
            req = urllib.request.Request("https://api.mistral.ai/v1/models",
                headers={"Authorization": f"Bearer {key}"}, method="GET")
            with urllib.request.urlopen(req, timeout=12) as r:
                json.loads(r.read())
            return True, "Valid"
        elif provider == "Groq":
            req = urllib.request.Request("https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}"}, method="GET")
            with urllib.request.urlopen(req, timeout=12) as r:
                json.loads(r.read())
            return True, "Valid"
        elif provider == "OpenAI":
            req = urllib.request.Request("https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"}, method="GET")
            with urllib.request.urlopen(req, timeout=12) as r:
                json.loads(r.read())
            return True, "Valid"
        elif provider == "Claude":
            body = json.dumps({"model":"claude-haiku-4-5-20251001","max_tokens":1,
                               "messages":[{"role":"user","content":"hi"}]}).encode()
            req = urllib.request.Request("https://api.anthropic.com/v1/messages",
                data=body, headers={"Content-Type":"application/json","x-api-key":key,
                "anthropic-version":"2023-06-01"}, method="POST")
            with urllib.request.urlopen(req, timeout=12) as r:
                json.loads(r.read())
            return True, "Valid"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, "Invalid key"
        elif e.code == 429:
            return True, "Valid (rate-limited)"
        else:
            return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"Error: {str(e)[:40]}"
    return False, "Unknown"

def get_active_keys(prefs):
    seq=[]
    for provider,cfg in AI_PROVIDERS.items():
        keys=prefs.get("ai_keys",{}).get(provider,[])
        model=prefs.get("ai_models",{}).get(provider, cfg["models"][0][1])
        active_keys=[k for k in keys if k.get("active") and k.get("key")]
        for i,k in enumerate(active_keys,1):
            seq.append((provider,k["key"],model,i))
    return seq

def call_with_failover(path,prompt,prefs,status_cb=None):
    seq=get_active_keys(prefs)
    if not seq: raise RuntimeError("No active API keys. Open 'API Configuration'.")
    last_err=""
    for provider,key,model,key_idx in seq:
        try:
            if status_cb: status_cb(f"Trying {provider} · {model_label(provider,model)}…")
            raw=CALLERS[provider](key,model,path,prompt)
            return raw,provider,model,key_idx
        except Exception as e:
            last_err=f"{provider}: {str(e)[:120]}"
    raise RuntimeError(f"All keys failed. Last: {last_err}")


# ── FIXED prompt builder with stronger output enforcement ──────────────
def build_meta_prompt(title_c, desc_c, kw_n, custom_prompt="",
                      single_kw=False, themes="", prefix="", suffix_title=""):
    directives = []
    if themes:
        directives.append(f"Content theme: {themes}. Reflect this in the metadata.")
    if single_kw:
        directives.append(f"Every keyword must be a single word only (no spaces or hyphens).")
    if custom_prompt.strip():
        directives.append(
            f"MANDATORY COMMAND — override your defaults and apply this to title+description+keywords: "
            f"\"{custom_prompt.strip()}\"")
    directive_block = ("\n\nEXTRA RULES:\n" +
        "\n".join(f"- {d}" for d in directives)) if directives else ""

    prefix_note = f' Start the title with: "{prefix}".' if prefix else ""
    suffix_note = f' End the title with: "{suffix_title}".' if suffix_title else ""

    # Key change: we put KEYWORDS FIRST in the format so models don't
    # run out of context/tokens before generating them.
    return (
        f"You are a professional stock image metadata writer for stock photo agencies.\n"
        f"Analyze the image carefully and return metadata in EXACTLY this format "
        f"(3 lines, nothing else before or after):\n\n"
        f"TITLE: <title>\n"
        f"DESCRIPTION: <description>\n"
        f"KEYWORDS: <keywords>\n\n"
        f"STRICT REQUIREMENTS — every single one must be satisfied:\n"
        f"1. TITLE: {max(title_c-20,10)}–{title_c} characters.{prefix_note}{suffix_note}\n"
        f"2. DESCRIPTION: {max(desc_c-30,20)}–{desc_c} characters. Include subject, "
        f"mood, setting, use-case, colors.\n"
        f"3. KEYWORDS: Write EXACTLY {kw_n} keywords separated by commas. "
        f"No fewer, no more. Sort by relevance — most specific first. "
        f"No duplicates. No brand names. Cover subject/action/setting/mood/color/style.\n"
        f"4. Output ONLY the 3 lines. No preamble, no markdown, no numbering, "
        f"no extra explanation.{directive_block}"
    )


def build_prompt_prompt(max_words, styles, custom_prompt=""):
    style_str = ", ".join(styles) if styles else "realistic photography"
    extra = f"\n- MANDATORY: {custom_prompt.strip()}" if custom_prompt.strip() else ""
    return (
        f"You are an expert AI image generation prompt writer.\n"
        f"Analyze the image and write a detailed generation prompt.\n"
        f"Output ONLY the prompt text — no labels, no explanation.\n"
        f"Rules:\n"
        f"- Max {max_words} words.\n"
        f"- Style: {style_str}.\n"
        f"- Include: subject, lighting, colors, composition, mood, camera angle.\n"
        f"- Write as a flowing comma-separated description.{extra}"
    )


# ── ROBUST parser: handles blank lines, reordered sections, missing labels ──
def parse_meta(text):
    """
    Robust 3-pass parser:
    Pass 1 — exact prefix match on each line
    Pass 2 — looser case-insensitive scan with common label variants
    Pass 3 — positional fallback (line1=title, line2=desc, line3+=kw)
    """
    title = desc = kw = ""
    lines = [l.strip() for l in text.strip().splitlines()]

    def _after(line, prefix):
        return line[len(prefix):].strip()

    # Pass 1: exact prefix match
    i = 0
    while i < len(lines):
        u = lines[i].upper()
        if u.startswith("TITLE:") and not title:
            title = _after(lines[i], lines[i][:6])
        elif (u.startswith("DESCRIPTION:") or u.startswith("DESC:")) and not desc:
            tag_len = 12 if u.startswith("DESCRIPTION:") else 5
            desc = lines[i][tag_len:].strip()
            # absorb continuation lines (skip blanks, stop at next key)
            i += 1
            while i < len(lines):
                nxt = lines[i].upper()
                if nxt.startswith("KEYWORD") or nxt.startswith("TITLE:") or nxt.startswith("TAGS:"):
                    i -= 1; break
                if lines[i]:   # skip blank continuation lines — don't absorb
                    desc += " " + lines[i]
                i += 1
            desc = desc.strip()
        elif (u.startswith("KEYWORDS:") or u.startswith("KEYWORD:") or
              u.startswith("TAGS:") or u.startswith("KW:")) and not kw:
            col = lines[i].index(":") + 1
            kw = lines[i][col:].strip()
            i += 1
            while i < len(lines):
                nxt = lines[i].upper()
                if nxt.startswith("TITLE:") or nxt.startswith("DESCRIPTION:") or nxt.startswith("DESC:"):
                    i -= 1; break
                if lines[i]: kw += " " + lines[i]
                i += 1
            kw = kw.strip()
        i += 1

    # Pass 2: looser scan if any field still missing
    if not desc or not kw:
        for line in lines:
            u = line.upper().lstrip("*-# ")
            if not desc and any(u.startswith(p) for p in ["DESCRIPTION","DESC"]):
                desc = line.split(":",1)[-1].strip()
            if not kw and any(u.startswith(p) for p in ["KEYWORD","KW","TAG"]):
                kw = line.split(":",1)[-1].strip()

    # Pass 3: positional fallback — models sometimes drop the labels entirely
    if not title and not desc and not kw:
        non_blank = [l for l in lines if l]
        if len(non_blank) >= 1: title = non_blank[0]
        if len(non_blank) >= 2: desc  = non_blank[1]
        if len(non_blank) >= 3: kw    = ", ".join(non_blank[2:])

    return title.strip(), desc.strip(), kw.strip()


def enforce_single_keywords(kw_string):
    raw = [k.strip() for k in kw_string.split(",") if k.strip()]
    seen = set(); result = []
    for kw in raw:
        single = kw.split()[0] if kw.split() else kw
        if single.lower() not in seen:
            seen.add(single.lower()); result.append(single)
    return ", ".join(result)


def make_thumb(path, size=(120,85)):
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in VECTOR_EXTS or ext in VIDEO_EXTS: return None
        img = Image.open(path).convert("RGB")
        img.thumbnail(size, Image.LANCZOS)
        return ctk.CTkImage(img, size=img.size)
    except: return None


def check_online():
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8",53))
        return True
    except: return False


# ══════════════════════════════════════════════════════════════════════
#  PALETTE  —  Black Glassmorphic
# ══════════════════════════════════════════════════════════════════════
BG1="#0a0a0a"; BG2="#111111"; BG3="#1a1a1a"; BG4="#222222"
GLASS="#161616"; GLASS_BDR="#2a2a2a"; GLASS_BDR_AC="#00c853"
TXT="#f0f0f0"; TXT2="#a0a0a0"; TXT3="#606060"
GRN="#00c853"; GRN_H="#00a040"; GRN_DIM="#00331a"
RED_BTN="#e53935"; RED_BTN_H="#b71c1c"; RED_DIM="#2a0000"
AMB_BTN="#f9a825"; AMB_BTN_H="#c67c00"; AMB_DIM="#2a1a00"
CYAN="#00e5ff"; LOG_BG="#050505"
ABSOLUTE_BG="#000000"
AI_PROVIDERS_ORDERED=["Gemini","Mistral","Groq","OpenAI","Claude","OpenRouter"]


# ══════════════════════════════════════════════════════════════════════
#  API KEY MANAGER
# ══════════════════════════════════════════════════════════════════════
class APIManagerWindow(ctk.CTkToplevel):
    def __init__(self,parent,prefs,on_close=None):
        super().__init__(parent); self.title("API Configuration")
        self.configure(fg_color=BG1); self.resizable(False,False); self.grab_set()
        self.prefs=prefs; self.on_close=on_close; self._cur=AI_PROVIDERS_ORDERED[0]
        self._build(); self._center(920,620)
        self.protocol("WM_DELETE_WINDOW",self._done)

    def _center(self,w,h):
        self.update_idletasks()
        x=self.master.winfo_x()+(self.master.winfo_width()-w)//2
        y=self.master.winfo_y()+(self.master.winfo_height()-h)//2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _tab_text(self,p):
        n=sum(1 for k in self.prefs.get("ai_keys",{}).get(p,[]) if k.get("active"))
        return p+(f"  ●{n}" if n else "")

    def _build(self):
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(2,weight=1)
        hdr=ctk.CTkFrame(self,fg_color=BG2,corner_radius=0,height=52)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(hdr,text="API Configuration",
            font=ctk.CTkFont("Segoe UI",15,"bold"),text_color=TXT,fg_color=BG2
        ).grid(row=0,column=0,sticky="w",padx=18,pady=14)
        ctk.CTkButton(hdr,text="✕",width=34,height=34,fg_color="transparent",
            hover_color=RED_DIM,text_color=TXT3,corner_radius=6,command=self._done
        ).grid(row=0,column=1,padx=10)

        tab_bar=ctk.CTkFrame(self,fg_color=BG2,corner_radius=0,height=50)
        tab_bar.grid(row=1,column=0,sticky="ew"); tab_bar.grid_propagate(False)
        self._tabs={}
        for p in AI_PROVIDERS_ORDERED:
            btn=ctk.CTkButton(tab_bar,text=self._tab_text(p),width=116,height=34,
                font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=GRN if p==self._cur else BG3,
                hover_color=GRN_H if p==self._cur else BG4,
                text_color=ABSOLUTE_BG if p==self._cur else TXT2,corner_radius=8,
                command=lambda pv=p:self._switch(pv))
            btn.pack(side="left",padx=(10 if p==AI_PROVIDERS_ORDERED[0] else 3,0),pady=8)
            self._tabs[p]=btn

        body=ctk.CTkFrame(self,fg_color=BG1,corner_radius=0)
        body.grid(row=2,column=0,sticky="nsew")
        body.grid_columnconfigure(0,weight=0); body.grid_columnconfigure(1,weight=1)
        body.grid_rowconfigure(0,weight=1)
        self._lp=ctk.CTkFrame(body,fg_color=BG2,corner_radius=0,width=420)
        self._lp.grid(row=0,column=0,sticky="nsew"); self._lp.grid_propagate(False)
        self._rp=ctk.CTkFrame(body,fg_color=BG1,corner_radius=0)
        self._rp.grid(row=0,column=1,sticky="nsew",padx=(1,0))
        self._rp.grid_columnconfigure(0,weight=1); self._rp.grid_rowconfigure(1,weight=1)

        ftr=ctk.CTkFrame(self,fg_color=BG2,corner_radius=0,height=52)
        ftr.grid(row=3,column=0,sticky="ew"); ftr.grid_propagate(False)
        ctk.CTkButton(ftr,text="Done",width=100,height=34,
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,corner_radius=8,
            command=self._done).pack(side="right",padx=16,pady=9)
        self._render()

    def _switch(self,p):
        self._cur=p
        for pv,btn in self._tabs.items():
            s=(pv==p)
            btn.configure(text=self._tab_text(pv),
                fg_color=GRN if s else BG3,hover_color=GRN_H if s else BG4,
                text_color=ABSOLUTE_BG if s else TXT2)
        self._render()

    def _render(self):
        for w in self._lp.winfo_children(): w.destroy()
        for w in self._rp.winfo_children(): w.destroy()
        p=self._cur; cfg=AI_PROVIDERS[p]
        keys=self.prefs.setdefault("ai_keys",{}).setdefault(p,[])
        models=cfg["models"]
        cur_id=self.prefs.setdefault("ai_models",{}).get(p,models[0][1])

        inner=ctk.CTkScrollableFrame(self._lp,fg_color=BG2,scrollbar_button_color=BG3,corner_radius=0)
        inner.place(relx=0,rely=0,relwidth=1,relheight=1)
        inner.grid_columnconfigure(0,weight=1)

        ctk.CTkLabel(inner,text="CONFIGURATION",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=GRN,fg_color=BG2).pack(anchor="w",padx=18,pady=(16,8))
        ctk.CTkLabel(inner,text="Model Selection",font=ctk.CTkFont("Segoe UI",12),
            text_color=TXT2,fg_color=BG2).pack(anchor="w",padx=18,pady=(0,4))
        mv=StringVar(value=model_label(p,cur_id))
        ctk.CTkComboBox(inner,variable=mv,values=[m[0] for m in models],state="readonly",
            font=ctk.CTkFont("Segoe UI",12),fg_color=BG3,text_color=TXT,border_color=GLASS_BDR,
            button_color=GRN,button_hover_color=GRN_H,dropdown_fg_color=BG3,
            dropdown_text_color=TXT,dropdown_hover_color=BG4,corner_radius=8,height=40,
            command=lambda v:self._save_model(p,v)).pack(fill="x",padx=18,pady=(0,16))
        ctk.CTkFrame(inner,fg_color=GLASS_BDR,height=1,corner_radius=0).pack(fill="x")

        ctk.CTkLabel(inner,text="Add New API Key",font=ctk.CTkFont("Segoe UI",12),
            text_color=TXT2,fg_color=BG2).pack(anchor="w",padx=18,pady=(14,4))
        nkv=StringVar()
        er=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        er.pack(fill="x",padx=18,pady=(0,4)); er.grid_columnconfigure(0,weight=1)
        entry=ctk.CTkEntry(er,textvariable=nkv,placeholder_text="Paste API key here...",show="•",
            font=ctk.CTkFont("Segoe UI",12),fg_color=BG3,text_color=TXT,
            border_color=GLASS_BDR,corner_radius=8,height=40)
        entry.grid(row=0,column=0,sticky="ew")
        vld_lbl=ctk.CTkLabel(inner,text="",font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT3,fg_color=BG2)

        ctk.CTkButton(er,text="Save",width=76,height=40,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,corner_radius=8,
            command=lambda:self._add_key(p,nkv.get().strip(),vld_lbl)
        ).grid(row=0,column=1,padx=(8,0))
        vld_lbl.pack(anchor="w",padx=18,pady=(2,10))

        def _live_validate(e=None):
            kv=nkv.get().strip()
            if len(kv)<8: vld_lbl.configure(text="",text_color=TXT3); return
            vld_lbl.configure(text="⟳  Checking…",text_color=AMB_BTN)
            def _run():
                ok,msg=validate_key(p,kv)
                self.after(0,lambda:vld_lbl.configure(
                    text="✓  Valid" if ok else f"✗  {msg}",
                    text_color=GRN if ok else RED_BTN))
            threading.Thread(target=_run,daemon=True).start()
        entry.bind("<FocusOut>",_live_validate)
        entry.bind("<Return>",_live_validate)

        ctk.CTkButton(inner,text=f"🔑  Get API Key from {p}",height=38,
            font=ctk.CTkFont("Segoe UI",11),fg_color=BG3,hover_color=BG4,text_color=TXT2,
            border_width=1,border_color=GLASS_BDR,corner_radius=8,
            command=lambda:self._open_url(cfg["key_url"])).pack(fill="x",padx=18,pady=(0,18))

        # RIGHT: stored keys — show ALL
        ctk.CTkLabel(self._rp,text="STORED KEYS",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT2,fg_color=BG1).pack(anchor="w",padx=16,pady=(16,8))
        ks=ctk.CTkScrollableFrame(self._rp,fg_color=BG1,corner_radius=0,scrollbar_button_color=BG3)
        ks.pack(fill="both",expand=True); ks.grid_columnconfigure(0,weight=1)
        if not keys:
            ctk.CTkLabel(ks,text="No keys saved yet.",font=ctk.CTkFont("Segoe UI",12),
                text_color=TXT3,fg_color=BG1).pack(pady=30); return
        for i,k in enumerate(keys):
            self._key_card(ks,p,i,k)

    def _key_card(self,parent,prov,idx,k):
        is_active=k.get("active",False); kv=k.get("key","")
        key_disp="..."+kv[-10:] if len(kv)>10 else kv
        bdr=GLASS_BDR_AC if is_active else GLASS_BDR
        card=ctk.CTkFrame(parent,fg_color="#0a1a0a" if is_active else BG3,
            corner_radius=10,border_width=1,border_color=bdr)
        card.pack(fill="x",padx=12,pady=(0,8)); card.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(card,text="🔑",font=ctk.CTkFont("Segoe UI",14),
            fg_color="transparent",text_color=TXT2
        ).grid(row=0,column=0,padx=(12,8),pady=(10,4),sticky="w")
        kf=ctk.CTkFrame(card,fg_color="transparent",corner_radius=0)
        kf.grid(row=0,column=1,sticky="ew",pady=(10,4))
        ctk.CTkLabel(kf,text=key_disp,font=ctk.CTkFont("Consolas",12,"bold"),
            text_color=TXT,fg_color="transparent",anchor="w").pack(anchor="w")
        if is_active:
            ctk.CTkLabel(card,text="● Active",font=ctk.CTkFont("Segoe UI",10,"bold"),
                fg_color=GRN_DIM,text_color=GRN,corner_radius=20,padx=10,pady=3
            ).grid(row=0,column=2,padx=(0,10),pady=(10,4),sticky="e")
        af=ctk.CTkFrame(card,fg_color="transparent",corner_radius=0)
        af.grid(row=1,column=0,columnspan=3,sticky="ew",padx=10,pady=(0,8))
        ctk.CTkButton(af,text="👁",width=34,height=28,fg_color="transparent",
            hover_color=BG4,text_color=TXT3,corner_radius=6,
            command=lambda kv2=kv,lb=kf:self._toggle_show(kv2,lb)).pack(side="left",padx=(0,4))
        ctk.CTkButton(af,text="⧉",width=34,height=28,fg_color="transparent",
            hover_color=BG4,text_color=TXT3,corner_radius=6,
            command=lambda kv2=kv:self._copy(kv2)).pack(side="left",padx=(0,4))
        vl=ctk.CTkLabel(af,text="? Test",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT3,fg_color=BG4,corner_radius=6,padx=8,pady=4,cursor="hand2")
        vl.pack(side="left",padx=(0,4))
        vl.bind("<Button-1>",lambda e,kv2=kv,lb=vl:(
            lb.configure(text="⟳…",text_color=AMB_BTN),
            threading.Thread(target=lambda:
                self.after(0,lambda:lb.configure(
                    **({"text":"✓ OK","text_color":GRN} if validate_key(prov,kv2)[0]
                       else {"text":"✗ Bad","text_color":RED_BTN}))),
            daemon=True).start()))
        if not is_active:
            ctk.CTkButton(af,text="Activate",width=84,height=28,
                font=ctk.CTkFont("Segoe UI",10,"bold"),fg_color=BG4,hover_color=GRN_DIM,
                text_color=TXT2,border_width=1,border_color=GLASS_BDR,corner_radius=6,
                command=lambda i=idx:self._activate(prov,i)).pack(side="left",padx=(0,4))
        else:
            ctk.CTkButton(af,text="Deactivate",width=90,height=28,
                font=ctk.CTkFont("Segoe UI",10,"bold"),fg_color=BG4,hover_color=RED_DIM,
                text_color=TXT2,border_width=1,border_color=GLASS_BDR,corner_radius=6,
                command=lambda i=idx:self._deactivate(prov,i)).pack(side="left",padx=(0,4))
        # DELETE button — always visible
        ctk.CTkButton(af,text="🗑",width=34,height=28,fg_color="transparent",
            hover_color=RED_DIM,text_color=TXT3,corner_radius=6,
            command=lambda i=idx:self._del(prov,i)).pack(side="right")

    def _toggle_show(self,kv,lf):
        ch=lf.winfo_children()
        if ch:
            short="..."+kv[-10:] if len(kv)>10 else kv
            ch[0].configure(text=kv if ch[0].cget("text")==short else short)
    def _copy(self,kv): self.clipboard_clear(); self.clipboard_append(kv)
    def _activate(self,p,i):
        self.prefs["ai_keys"][p][i]["active"]=True; save_prefs(self.prefs); self._refresh(); self._render()
    def _deactivate(self,p,i):
        self.prefs["ai_keys"][p][i]["active"]=False; save_prefs(self.prefs); self._refresh(); self._render()
    def _del(self,p,i):
        if not messagebox.askyesno("Delete","Delete this key?",parent=self): return
        self.prefs["ai_keys"][p].pop(i); save_prefs(self.prefs); self._refresh(); self._render()
    def _add_key(self,p,key,vld_lbl=None):
        if not key: messagebox.showwarning("Empty","Paste a key first.",parent=self); return
        keys=self.prefs["ai_keys"][p]
        if any(k["key"]==key for k in keys):
            messagebox.showinfo("Duplicate","Already saved.",parent=self); return
        for k in keys: k["active"]=False
        keys.append({"key":key,"active":True})
        save_prefs(self.prefs); self._refresh(); self._render()
    def _save_model(self,p,label):
        self.prefs.setdefault("ai_models",{})[p]=model_id_from_label(p,label); save_prefs(self.prefs)
    def _refresh(self):
        for pv,btn in self._tabs.items():
            s=(pv==self._cur)
            btn.configure(text=self._tab_text(pv),fg_color=GRN if s else BG3,
                text_color=ABSOLUTE_BG if s else TXT2)
    def _open_url(self,url):
        import webbrowser; webbrowser.open(url)
    def _done(self):
        if self.on_close: self.on_close()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  RESULT CARD  (in Generated Metadata section)
# ══════════════════════════════════════════════════════════════════════
class MetaResultCard(ctk.CTkFrame):
    def __init__(self,master,path,result,on_redo,**kw):
        super().__init__(master,fg_color=GLASS,corner_radius=12,
            border_width=1,border_color=GLASS_BDR,**kw)
        self.path=path; self.result=result
        self._build(on_redo)

    def _build(self,on_redo):
        self.grid_columnconfigure(1,weight=1)

        # Thumbnail
        tf=ctk.CTkFrame(self,fg_color=BG3,corner_radius=10,width=90,height=90)
        tf.grid(row=0,column=0,rowspan=5,padx=(10,8),pady=10,sticky="n")
        tf.grid_propagate(False)
        self._tlbl=ctk.CTkLabel(tf,text="🖼",font=ctk.CTkFont("Segoe UI",20),
            fg_color=BG3,text_color=TXT3,width=88,height=88,corner_radius=8)
        self._tlbl.pack()
        threading.Thread(target=self._load_thumb,daemon=True).start()

        # Filename
        fname=os.path.basename(self.path)
        ctk.CTkLabel(self,text=fname,font=ctk.CTkFont("Segoe UI",11,"bold"),
            text_color=TXT2,fg_color="transparent",anchor="w"
        ).grid(row=0,column=1,sticky="w",pady=(10,2),padx=(0,10))

        title=self.result.get("title","")
        desc=self.result.get("desc","")
        kw=self.result.get("kw","")
        kw_count=len([x for x in kw.split(",") if x.strip()]) if kw else 0

        for row_idx,(label,val,color,is_kw) in enumerate([
            ("Title",    title, CYAN,     False),
            ("Description",desc,TXT2,    False),
            (f"Keywords  ({kw_count})",kw,GRN,True),
        ],1):
            hdr=ctk.CTkFrame(self,fg_color="transparent",corner_radius=0)
            hdr.grid(row=row_idx*2-1,column=1,sticky="ew",padx=(0,10),pady=(4,0))
            hdr.grid_columnconfigure(1,weight=1)
            ctk.CTkLabel(hdr,text=label,font=ctk.CTkFont("Segoe UI",9,"bold"),
                text_color=TXT3,fg_color="transparent").grid(row=0,column=0,sticky="w")

            # Copy + Paste buttons
            btn_f=ctk.CTkFrame(hdr,fg_color="transparent",corner_radius=0)
            btn_f.grid(row=0,column=2,sticky="e")
            ctk.CTkButton(btn_f,text="⧉ Copy",width=62,height=18,
                font=ctk.CTkFont("Segoe UI",9),fg_color=BG4,hover_color=BG3,
                text_color=TXT3,corner_radius=20,
                command=lambda v=val:self._copy(v)).pack(side="left",padx=(0,4))
            ctk.CTkButton(btn_f,text="⎙ Paste",width=62,height=18,
                font=ctk.CTkFont("Segoe UI",9),fg_color=BG4,hover_color=BG3,
                text_color=TXT3,corner_radius=20,
                command=lambda k=label,row=row_idx:self._paste(k)).pack(side="left")

            preview=val[:250]+"…" if len(val)>250 else (val or "(none)")
            ctk.CTkLabel(self,text=preview,
                font=ctk.CTkFont("Segoe UI",10),text_color=color if val else TXT3,
                fg_color="transparent",anchor="w",wraplength=520,justify="left"
            ).grid(row=row_idx*2,column=1,sticky="ew",padx=(0,10),pady=(0,2))

        # Footer
        ftr=ctk.CTkFrame(self,fg_color="transparent",corner_radius=0)
        ftr.grid(row=7,column=1,sticky="ew",padx=(0,10),pady=(6,10))
        ftr.grid_columnconfigure(1,weight=1)
        stats=f"Title: {len(title)} chars   Desc: {len(desc)} chars   Keywords: {kw_count}"
        ctk.CTkLabel(ftr,text=stats,font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT3,fg_color="transparent").grid(row=0,column=0,sticky="w")
        model_used=self.result.get("model_used","")
        if model_used:
            ctk.CTkLabel(ftr,text=model_used,font=ctk.CTkFont("Segoe UI",9),
                text_color=TXT3,fg_color=BG4,corner_radius=20,padx=8,pady=2
            ).grid(row=0,column=1,sticky="e",padx=(8,0))
        ctk.CTkButton(ftr,text="↺ Redo",width=76,height=26,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=BG4,hover_color=AMB_DIM,text_color=AMB_BTN,
            border_width=1,border_color=GLASS_BDR,corner_radius=8,
            command=on_redo).grid(row=0,column=2,padx=(8,0))

    def _copy(self,text): self.clipboard_clear(); self.clipboard_append(text)

    def _paste(self,field_key):
        """Replace the clicked field with clipboard content."""
        try:
            clip=self.clipboard_get()
        except: return
        key_map={"Title":"title","Description":"desc"}
        if "Keywords" in field_key: key_map_key="kw"
        else: key_map_key=key_map.get(field_key,"")
        if key_map_key and clip.strip():
            self.result[key_map_key]=clip.strip()
            # Rebuild display in-place
            for w in self.winfo_children(): w.destroy()
            self._build(lambda:None)

    def _load_thumb(self):
        img=make_thumb(self.path,(86,86))
        if img:
            self.after(0,lambda:(self._tlbl.configure(image=img,text=""),
                setattr(self._tlbl,"_image",img)))


# ══════════════════════════════════════════════════════════════════════
#  DnD MIXIN + MAIN APP
# ══════════════════════════════════════════════════════════════════════
if DND_AVAILABLE:
    class DnDCTk(ctk.CTk,TkinterDnD.DnDWrapper):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw)
            self.TkdndVersion=TkinterDnD._require(self)
else:
    DnDCTk=ctk.CTk


class App(DnDCTk):
    VERSION="v1.2"

    def __init__(self):
        super().__init__()
        self.title("Meta Zone"); self.configure(fg_color=BG1)
        self.resizable(True,True)
        self.prefs=load_prefs()

        self._all_paths=[]; self._results={}
        self._thumb_queue=queue.Queue()
        self.ai_running=False; self.ai_stop_flag=False; self.current_mode="meta"
        self._result_cards=[]; self._source_folder=""

        # Embed state
        self.csv_rows=[]; self.csv_headers=[]; self.embed_running=False
        self.csv_path_var=StringVar(); self.folder_path_var=StringVar()
        self.col_file_var=StringVar(value="(skip)"); self.col_title_var=StringVar(value="(skip)")
        self.col_kw_var=StringVar(value="(skip)"); self.col_desc_var=StringVar(value="(skip)")
        self.match_only_var=BooleanVar(value=True); self.subfolder_var=BooleanVar(value=True)
        self.rm_prog_var=BooleanVar(value=True)

        # AI settings
        self.ai_title_var   =StringVar(value=str(self.prefs.get("title_len",130)))
        self.ai_desc_var    =StringVar(value=str(self.prefs.get("desc_len",200)))
        self.ai_kw_var      =StringVar(value=str(self.prefs.get("kw_count",49)))
        self.ai_words_var   =StringVar(value=str(self.prefs.get("prompt_words",60)))
        self.ai_custom_var  =StringVar(value=self.prefs.get("custom_prompt",""))
        self.ai_single_kw_var=BooleanVar(value=self.prefs.get("single_keywords",False))
        self.ai_concurrency_var=IntVar(value=self.prefs.get("concurrency",1))
        self.ai_prefix_on_var=BooleanVar(value=False)
        self.ai_suffix_on_var=BooleanVar(value=False)
        self.ai_prefix_text_var=StringVar(value=self.prefs.get("prefix_text",""))
        self.ai_suffix_text_var=StringVar(value=self.prefs.get("suffix_text",""))

        self._style_vars={}
        for s in ["Silhouette","White Background","Transparent","Vector","Videos"]:
            self._style_vars[s]=BooleanVar(value=False)

        self._build_ui()
        self._center(1320,920)
        self.minsize(1000,700)
        self.after(200,self._check_et)
        self.after(500,self._online_loop)
        self.after(80,self._poll_thumb_queue)

    def _center(self,w,h):
        self.update_idletasks()
        sw=self.winfo_screenwidth(); sh=self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def ts(self): return datetime.datetime.now().strftime("%H:%M:%S")

    def _online_loop(self):
        def _chk():
            online=check_online()
            self.after(0,lambda:self._set_online(online))
            self.after(8000,self._online_loop)
        threading.Thread(target=_chk,daemon=True).start()

    def _set_online(self,online):
        self._is_online=online
        self._online_dot.configure(text_color=GRN if online else RED_BTN)
        self._online_lbl.configure(text="Online" if online else "Offline",
            text_color=TXT2 if online else RED_BTN)
        self._blink(0)

    def _blink(self,n=0):
        if n<6:
            base=GRN if getattr(self,"_is_online",True) else RED_BTN
            self._online_dot.configure(text_color=TXT3 if n%2==0 else base)
            self.after(350,lambda:self._blink(n+1))

    def _poll_thumb_queue(self):
        done=0
        try:
            while done<15:
                (w,img)=self._thumb_queue.get_nowait()
                try:
                    if w.winfo_exists(): w.configure(image=img,text=""); w._image=img
                except: pass
                done+=1
        except queue.Empty: pass
        self.after(80,self._poll_thumb_queue)

    # ── BUILD UI ───────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0,weight=1)
        self.grid_rowconfigure(0,weight=0); self.grid_rowconfigure(1,weight=0)
        self.grid_rowconfigure(2,weight=1); self.grid_rowconfigure(3,weight=0)
        self._build_titlebar(); self._build_tabbar(); self._build_statusbar()

    def _build_titlebar(self):
        tb=ctk.CTkFrame(self,fg_color=BG2,corner_radius=0,height=54)
        tb.grid(row=0,column=0,sticky="ew"); tb.grid_propagate(False)
        tb.grid_columnconfigure(2,weight=1)
        ctk.CTkLabel(tb,text="✦",font=ctk.CTkFont("Segoe UI",16,"bold"),
            fg_color=BG4,text_color=GRN,corner_radius=8,width=28,height=28
        ).grid(row=0,column=0,padx=(16,8),pady=13)
        ctk.CTkLabel(tb,text="Meta Zone",font=ctk.CTkFont("Segoe UI",18,"bold"),
            text_color=TXT,fg_color=BG2).grid(row=0,column=1,sticky="w")
        ctk.CTkLabel(tb,text=self.VERSION,font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=GRN,fg_color=GRN_DIM,corner_radius=20,padx=8,pady=2
        ).grid(row=0,column=2,sticky="w",padx=(8,0))
        # Online indicator
        of=ctk.CTkFrame(tb,fg_color=BG3,corner_radius=20)
        of.grid(row=0,column=3,padx=(0,16),pady=12)
        self._online_dot=ctk.CTkLabel(of,text="●",font=ctk.CTkFont("Segoe UI",16),
            text_color=GRN,fg_color=BG3); self._online_dot.pack(side="left",padx=(12,4),pady=4)
        self._online_lbl=ctk.CTkLabel(of,text="Online",font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=TXT2,fg_color=BG3); self._online_lbl.pack(side="left",padx=(0,12),pady=4)
        cr=ctk.CTkFrame(tb,fg_color=BG2,corner_radius=0)
        cr.grid(row=0,column=4,padx=(0,18),sticky="e")
        ctk.CTkLabel(cr,text="All Rights Reserved By",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT2,fg_color=BG2).pack(anchor="e")
        ctk.CTkLabel(cr,text="© HASIBNIKON",font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=TXT,fg_color=BG2).pack(anchor="e")

    def _build_tabbar(self):
        tb=ctk.CTkFrame(self,fg_color=BG2,corner_radius=0,height=46)
        tb.grid(row=1,column=0,sticky="ew"); tb.grid_propagate(False)
        tb.grid_columnconfigure(2,weight=1)
        self._ai_tab_btn=ctk.CTkButton(tb,text="✨  Metadata AI",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,
            width=160,height=30,corner_radius=15,command=lambda:self._switch_tab("ai"))
        self._ai_tab_btn.grid(row=0,column=0,padx=(12,4),pady=8)
        self._emb_tab_btn=ctk.CTkButton(tb,text="📋  Embed Metadata",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BG3,hover_color=BG4,text_color=TXT3,
            width=178,height=30,corner_radius=15,command=lambda:self._switch_tab("embed"))
        self._emb_tab_btn.grid(row=0,column=1,padx=4,pady=8)
        self._content=ctk.CTkFrame(self,fg_color=BG1,corner_radius=0)
        self._content.grid(row=2,column=0,sticky="nsew")
        self._content.grid_columnconfigure(0,weight=1); self._content.grid_rowconfigure(0,weight=1)
        self._ai_frame=ctk.CTkFrame(self._content,fg_color=BG1,corner_radius=0)
        self._emb_frame=ctk.CTkFrame(self._content,fg_color=BG1,corner_radius=0)
        self._ai_frame.grid(row=0,column=0,sticky="nsew")
        self._emb_frame.grid(row=0,column=0,sticky="nsew")
        self._build_ai_tab(self._ai_frame)
        self._build_embed_tab(self._emb_frame)
        self._switch_tab("ai")

    def _switch_tab(self,which):
        if which=="ai":
            self._ai_frame.tkraise()
            self._ai_tab_btn.configure(fg_color=GRN,text_color=ABSOLUTE_BG)
            self._emb_tab_btn.configure(fg_color=BG3,text_color=TXT3)
        else:
            self._emb_frame.tkraise()
            self._emb_tab_btn.configure(fg_color=GRN,text_color=ABSOLUTE_BG)
            self._ai_tab_btn.configure(fg_color=BG3,text_color=TXT3)

    # ── AI TAB ─────────────────────────────────────────────────────
    def _build_ai_tab(self,parent):
        parent.grid_columnconfigure(0,weight=0); parent.grid_columnconfigure(1,weight=1)
        parent.grid_rowconfigure(0,weight=1)
        self._sb_frame=ctk.CTkFrame(parent,fg_color=BG2,corner_radius=0,width=268)
        self._sb_frame.grid(row=0,column=0,sticky="nsew"); self._sb_frame.grid_propagate(False)
        self._main=ctk.CTkFrame(parent,fg_color=BG1,corner_radius=0)
        self._main.grid(row=0,column=1,sticky="nsew")
        self._main.grid_columnconfigure(0,weight=1)
        self._build_sidebar(); self._build_main()

    # ── SIDEBAR ────────────────────────────────────────────────────
    def _build_sidebar(self):
        sb=self._sb_frame; sb.grid_rowconfigure(1,weight=1); sb.grid_columnconfigure(0,weight=1)
        hdr_bg=ctk.CTkFrame(sb,fg_color=BG3,corner_radius=0,height=38)
        hdr_bg.grid(row=0,column=0,sticky="ew"); hdr_bg.grid_propagate(False)
        ctk.CTkLabel(hdr_bg,text="CONTROL PANEL",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT3,fg_color=BG3).pack(side="left",padx=12,pady=10)
        inner=ctk.CTkScrollableFrame(sb,fg_color=BG2,scrollbar_button_color=BG3,corner_radius=0)
        inner.grid(row=1,column=0,sticky="nsew"); inner.grid_columnconfigure(0,weight=1)
        self._sb=inner

        # API Config button
        ctk.CTkButton(inner,text="🔑  API Configuration",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,
            height=38,corner_radius=8,command=self._open_api_mgr
        ).pack(fill="x",padx=10,pady=(10,3))
        self._api_lbl=ctk.CTkLabel(inner,text="",font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT3,fg_color=BG2); self._api_lbl.pack(anchor="w",padx=12,pady=(0,4))
        self._refresh_api_lbl()

        # Concurrency slider (1-4)
        conc_f=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        conc_f.pack(fill="x",padx=10,pady=(0,6)); conc_f.grid_columnconfigure(0,weight=1)
        top=ctk.CTkFrame(conc_f,fg_color=BG2,corner_radius=0); top.pack(fill="x")
        top.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(top,text="Concurrent Generations",
            font=ctk.CTkFont("Segoe UI",11),text_color=TXT2,fg_color=BG2
        ).grid(row=0,column=0,sticky="w")
        self._conc_lbl=ctk.CTkLabel(top,text=f"{self.ai_concurrency_var.get()}x",
            font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=GRN,
            fg_color=BG3,corner_radius=20,padx=7,pady=2)
        self._conc_lbl.grid(row=0,column=1)
        conc_sl=ctk.CTkSlider(conc_f,from_=1,to=4,number_of_steps=3,
            progress_color=GRN,fg_color=BG3,button_color=TXT,
            button_hover_color="#ddffdd",height=14,variable=self.ai_concurrency_var,
            command=lambda v:(self._conc_lbl.configure(text=f"{int(v)}x"),
                self._save_settings()))
        conc_sl.pack(fill="x",pady=(3,0))

        self._div(inner)

        # Mode switch
        mf=ctk.CTkFrame(inner,fg_color=BG3,corner_radius=8)
        mf.pack(fill="x",padx=10,pady=(4,8))
        mf.grid_columnconfigure(0,weight=1); mf.grid_columnconfigure(1,weight=1)
        self._meta_mode_btn=ctk.CTkButton(mf,text="≡  METADATA",height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,corner_radius=6,
            command=lambda:self._set_mode("meta"))
        self._meta_mode_btn.grid(row=0,column=0,sticky="ew",padx=(4,2),pady=4)
        self._prompt_mode_btn=ctk.CTkButton(mf,text="✨  PROMPT",height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color="transparent",hover_color=BG4,text_color=TXT3,corner_radius=6,
            command=lambda:self._set_mode("prompt"))
        self._prompt_mode_btn.grid(row=0,column=1,sticky="ew",padx=(2,4),pady=4)

        # Metadata sliders
        self._meta_sliders_f=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        self._meta_sliders_f.pack(fill="x")
        msf=self._meta_sliders_f
        self._lbl(msf,"METADATA SETTINGS")
        self._title_sl=self._slider(msf,"Title Length",self.ai_title_var,10,200,int(self.ai_title_var.get()))
        self._desc_sl =self._slider(msf,"Description Length",self.ai_desc_var,20,500,int(self.ai_desc_var.get()))
        self._kw_sl   =self._slider(msf,"Keywords Count",self.ai_kw_var,5,49,int(self.ai_kw_var.get()))
        # Single keyword toggle
        sk_row=ctk.CTkFrame(msf,fg_color=BG2,corner_radius=0)
        sk_row.pack(fill="x",padx=10,pady=(2,6)); sk_row.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(sk_row,text="Single Word Keywords",font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2,fg_color=BG2).grid(row=0,column=0,sticky="w")
        ctk.CTkSwitch(sk_row,text="",variable=self.ai_single_kw_var,
            progress_color=GRN,button_color=TXT,fg_color=GLASS_BDR,
            onvalue=True,offvalue=False,width=46,height=24,command=self._save_settings
        ).grid(row=0,column=1,sticky="e")

        self._slider_anchor=ctk.CTkFrame(inner,fg_color=BG2,height=0,corner_radius=0)
        self._slider_anchor.pack(fill="x")

        # Prompt sliders (hidden initially)
        self._prompt_sliders_f=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        self._lbl(self._prompt_sliders_f,"PROMPT SETTINGS")
        self._words_sl=self._slider(self._prompt_sliders_f,"Max Prompt Words",
            self.ai_words_var,10,200,int(self.ai_words_var.get()))

        self._div(inner)

        # Content Themes (replaces Content Type)
        self._lbl(inner,"CONTENT THEMES")
        for s in ["Silhouette","White Background","Transparent","Vector","Videos"]:
            rf=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
            rf.pack(fill="x",padx=10,pady=1); rf.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(rf,text=s,font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT2,fg_color=BG2).grid(row=0,column=0,sticky="w")
            ctk.CTkSwitch(rf,text="",variable=self._style_vars[s],
                progress_color=GRN,button_color=TXT,fg_color=GLASS_BDR,
                onvalue=True,offvalue=False,width=46,height=24
            ).grid(row=0,column=1,sticky="e")

        # Prefix / Suffix toggles
        self._div(inner)
        self._lbl(inner,"TITLE PREFIX / SUFFIX")
        for label,on_var,text_var in [
            ("Add Prefix",self.ai_prefix_on_var,self.ai_prefix_text_var),
            ("Add Suffix",self.ai_suffix_on_var,self.ai_suffix_text_var),
        ]:
            toggle_row=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
            toggle_row.pack(fill="x",padx=10,pady=(1,0)); toggle_row.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(toggle_row,text=label,font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT2,fg_color=BG2).grid(row=0,column=0,sticky="w")
            txt_entry=ctk.CTkEntry(inner,textvariable=text_var,
                placeholder_text=f"Enter {label.split()[1].lower()}…",height=32,
                font=ctk.CTkFont("Segoe UI",11),fg_color=BG3,text_color=TXT,
                border_color=GLASS_BDR,corner_radius=8)

            def _toggle_entry(v,entry=txt_entry,var=on_var):
                if var.get(): entry.pack(fill="x",padx=10,pady=(2,6))
                else: entry.pack_forget()
            sw=ctk.CTkSwitch(toggle_row,text="",variable=on_var,
                progress_color=GRN,button_color=TXT,fg_color=GLASS_BDR,
                onvalue=True,offvalue=False,width=46,height=24,
                command=lambda v=None,ov=on_var,e=txt_entry:
                    (e.pack(fill="x",padx=10,pady=(2,6)) if ov.get() else e.pack_forget()))
            sw.grid(row=0,column=1,sticky="e")

        self._div(inner)

        # Custom System Prompt
        cp_hdr=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        cp_hdr.pack(fill="x",padx=10); cp_hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(cp_hdr,text="Custom System Prompt",
            font=ctk.CTkFont("Segoe UI",11,"bold"),text_color=TXT2,fg_color=BG2
        ).grid(row=0,column=0,sticky="w")
        ctk.CTkLabel(cp_hdr,text="Auto-Saved",font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT3,fg_color=BG3,corner_radius=20,padx=6,pady=2
        ).grid(row=0,column=1,sticky="e")
        self._custom_box=ctk.CTkTextbox(inner,height=72,
            font=ctk.CTkFont("Segoe UI",11),fg_color=BG3,text_color=TXT,
            border_color=GLASS_BDR,border_width=1,corner_radius=8,wrap="word")
        self._custom_box.pack(fill="x",padx=10,pady=(4,4))
        if self.ai_custom_var.get(): self._custom_box.insert("1.0",self.ai_custom_var.get())
        self._custom_box.bind("<KeyRelease>",lambda e:self._save_custom())
        ctk.CTkButton(inner,text="↺  Reset to Default",height=30,
            font=ctk.CTkFont("Segoe UI",11),fg_color="transparent",
            hover_color=BG3,text_color=CYAN,corner_radius=6,anchor="w",
            command=self._reset_defaults).pack(anchor="w",padx=10,pady=(0,16))

    def _set_mode(self,mode):
        self.current_mode=mode
        if mode=="meta":
            self._meta_mode_btn.configure(fg_color=GRN,text_color=ABSOLUTE_BG)
            self._prompt_mode_btn.configure(fg_color="transparent",text_color=TXT3)
            self._prompt_sliders_f.pack_forget()
            self._meta_sliders_f.pack(fill="x",before=self._slider_anchor)
        else:
            self._prompt_mode_btn.configure(fg_color=GRN,text_color=ABSOLUTE_BG)
            self._meta_mode_btn.configure(fg_color="transparent",text_color=TXT3)
            self._meta_sliders_f.pack_forget()
            self._prompt_sliders_f.pack(fill="x",before=self._slider_anchor)
        self._clear_results()

    def _reset_defaults(self):
        for var,sl,val in [(self.ai_title_var,self._title_sl,130),
                           (self.ai_desc_var,self._desc_sl,200),
                           (self.ai_kw_var,self._kw_sl,49),
                           (self.ai_words_var,self._words_sl,60)]:
            var.set(str(val)); sl.set(val)
            lbl=getattr(sl,"_value_label",None)
            if lbl: lbl.configure(text=str(val))
        self._custom_box.delete("1.0","end"); self.ai_custom_var.set("")
        for v in self._style_vars.values(): v.set(False)
        self._save_settings()

    def _div(self,parent):
        ctk.CTkFrame(parent,fg_color=GLASS_BDR,height=1,corner_radius=0
        ).pack(fill="x",padx=8,pady=6)

    def _lbl(self,parent,text):
        ctk.CTkLabel(parent,text=text,font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3,fg_color=BG2).pack(anchor="w",padx=12,pady=(4,2))

    def _slider(self,parent,label,var,from_,to,init):
        fr=ctk.CTkFrame(parent,fg_color=BG2,corner_radius=0)
        fr.pack(fill="x",padx=10,pady=(0,6)); fr.grid_columnconfigure(0,weight=1)
        top=ctk.CTkFrame(fr,fg_color=BG2,corner_radius=0); top.pack(fill="x")
        top.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(top,text=label,font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2,fg_color=BG2).grid(row=0,column=0,sticky="w")
        vl=ctk.CTkLabel(top,text=str(init),font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=GRN,fg_color=BG3,corner_radius=20,padx=7,pady=2)
        vl.grid(row=0,column=1)
        sl=ctk.CTkSlider(fr,from_=from_,to=to,number_of_steps=to-from_,
            progress_color=GRN,fg_color=BG3,button_color=TXT,
            button_hover_color="#ddffdd",height=14)
        sl.set(init); sl.pack(fill="x",pady=(3,0)); sl._value_label=vl
        def _upd(v): iv=int(v); var.set(str(iv)); vl.configure(text=str(iv)); self._save_settings()
        sl.configure(command=_upd)
        return sl

    def _save_settings(self):
        self.prefs.update({
            "title_len":int(self.ai_title_var.get() or 130),
            "desc_len":int(self.ai_desc_var.get() or 200),
            "kw_count":min(int(self.ai_kw_var.get() or 49),49),
            "prompt_words":int(self.ai_words_var.get() or 60),
            "single_keywords":self.ai_single_kw_var.get(),
            "concurrency":int(self.ai_concurrency_var.get()),
            "prefix_text":self.ai_prefix_text_var.get(),
            "suffix_text":self.ai_suffix_text_var.get(),
        })
        save_prefs(self.prefs)

    def _save_custom(self):
        v=self._custom_box.get("1.0","end").strip()
        self.ai_custom_var.set(v); self.prefs["custom_prompt"]=v; save_prefs(self.prefs)

    def _refresh_api_lbl(self):
        seq=get_active_keys(self.prefs); total=len(seq)
        providers=list(dict.fromkeys(p for p,_,_,_ in seq))
        if total:
            self._api_lbl.configure(
                text=f"✓ {total} key{'s' if total!=1 else ''} · {len(providers)} provider{'s' if len(providers)!=1 else ''}",
                text_color=GRN)
        else:
            self._api_lbl.configure(text="⚠ No active keys",text_color=RED_BTN)

    def _open_api_mgr(self):
        APIManagerWindow(self,self.prefs,on_close=self._refresh_api_lbl)

    # ── MAIN AREA ──────────────────────────────────────────────────
    def _build_main(self):
        main=self._main
        main.grid_rowconfigure(0,weight=0)  # topbar
        main.grid_rowconfigure(1,weight=0)  # upload workspace
        main.grid_rowconfigure(2,weight=0)  # progress bar
        main.grid_rowconfigure(3,weight=1)  # generated metadata

        # TOP BAR: platform tabs + action buttons
        topbar=ctk.CTkFrame(main,fg_color=BG2,corner_radius=0,height=52)
        topbar.grid(row=0,column=0,sticky="ew"); topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0,weight=1)
        plat_f=ctk.CTkFrame(topbar,fg_color=BG2,corner_radius=0)
        plat_f.grid(row=0,column=0,sticky="w",padx=8,pady=8)
        self._plat_btns={}
        for plat in PLATFORM_RULES:
            short=plat.replace(" Stock","").replace(" Images","")[:8]
            btn=ctk.CTkButton(plat_f,text=short,width=80,height=30,
                font=ctk.CTkFont("Segoe UI",10,"bold"),
                fg_color=GRN if plat=="Adobe Stock" else BG3,
                hover_color=GRN_H,
                text_color=ABSOLUTE_BG if plat=="Adobe Stock" else TXT2,
                border_width=1,
                border_color=GRN if plat=="Adobe Stock" else GLASS_BDR,
                corner_radius=6,command=lambda p=plat:self._sel_platform(p))
            btn.pack(side="left",padx=(0,3)); self._plat_btns[plat]=btn

        btn_f=ctk.CTkFrame(topbar,fg_color=BG2,corner_radius=0)
        btn_f.grid(row=0,column=1,padx=8,pady=8,sticky="e")
        ctk.CTkButton(btn_f,text="🗑  Clear All",width=96,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=RED_DIM,hover_color=RED_BTN_H,text_color=RED_BTN,
            border_width=1,border_color=RED_BTN,corner_radius=8,
            command=lambda:self._clear_all(confirm=True)).pack(side="left",padx=(0,6))
        self._pause_btn=ctk.CTkButton(btn_f,text="⏸  Pause",width=90,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=AMB_DIM,hover_color=AMB_BTN_H,text_color=AMB_BTN,
            border_width=1,border_color=AMB_BTN,corner_radius=8,
            command=self._stop_ai)
        self._pause_btn.pack(side="left",padx=(0,6))
        self._gen_btn=ctk.CTkButton(btn_f,text="✨  Generate (0)",width=165,height=32,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,corner_radius=8,
            command=self.start_generate)
        self._gen_btn.pack(side="left",padx=(0,6))
        self._export_btn=ctk.CTkButton(btn_f,text="⬇  Export CSV",width=130,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,hover_color=BG4,text_color=TXT2,
            border_width=1,border_color=GLASS_BDR,corner_radius=8,
            command=self._export_csv)
        self._export_btn.pack(side="left",padx=(0,6))
        self._zip_btn=ctk.CTkButton(btn_f,text="📦  Download ZIP",width=140,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,hover_color=BG4,text_color=TXT2,
            border_width=1,border_color=GLASS_BDR,corner_radius=8,
            command=self._download_zip)
        self._zip_btn.pack(side="left")

        # UPLOAD WORKSPACE — vertically compact, thumbnail grid
        ws=ctk.CTkFrame(main,fg_color=GLASS,corner_radius=12,
            border_width=1,border_color=GLASS_BDR)
        ws.grid(row=1,column=0,sticky="ew",padx=8,pady=(6,4))
        ws.grid_columnconfigure(0,weight=1)
        ws.grid_rowconfigure(0,weight=1)

        # Scrollable inner container for thumbnails — horizontal scroll
        self._thumb_scroll=ctk.CTkScrollableFrame(ws,
            fg_color=BG3,corner_radius=8,
            orientation="horizontal",
            scrollbar_button_color=BG4,
            scrollbar_button_hover_color=GLASS_BDR,
            height=110)
        self._thumb_scroll.grid(row=0,column=0,sticky="ew",padx=8,pady=8)
        self._thumb_scroll.grid_columnconfigure(0,weight=1)
        # _thumb_grid is the inner frame we place cells into
        self._thumb_grid=self._thumb_scroll

        self._ws_empty=ctk.CTkLabel(self._thumb_scroll,
            text="🖼️  🎬  ✦     Drag & drop or click to browse"
                 "\nJPG  PNG  GIF  WEBP  TIFF  SVG  EPS  MP4  MOV",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            text_color=TXT3,fg_color=BG3,justify="center")
        self._ws_empty.pack(expand=True,fill="both",padx=20,pady=12)

        # Bind clicks to browse on all ws surfaces
        for w in (ws,self._thumb_scroll,self._ws_empty):
            w.bind("<Button-1>",lambda e:self._browse_images())
        # Also bind on the scrollable frame's internal canvas
        try:
            self._thumb_scroll._parent_canvas.bind(
                "<Button-1>",lambda e:self._browse_images())
        except: pass

        if DND_AVAILABLE:
            for w in (self._thumb_scroll,self._ws_empty,ws):
                try:
                    w.drop_target_register(DND_FILES)
                    w.dnd_bind("<<DropEnter>>",self._on_drag_enter)
                    w.dnd_bind("<<DropLeave>>",self._on_drag_leave)
                    w.dnd_bind("<<Drop>>",self._on_drop)
                except: pass
            try:
                self._thumb_scroll._parent_canvas.drop_target_register(DND_FILES)
                self._thumb_scroll._parent_canvas.dnd_bind("<<DropEnter>>",self._on_drag_enter)
                self._thumb_scroll._parent_canvas.dnd_bind("<<DropLeave>>",self._on_drag_leave)
                self._thumb_scroll._parent_canvas.dnd_bind("<<Drop>>",self._on_drop)
            except: pass

        # Progress bar row
        prog=ctk.CTkFrame(main,fg_color=BG1,corner_radius=0,height=30)
        prog.grid(row=2,column=0,sticky="ew"); prog.grid_propagate(False)
        prog.grid_columnconfigure(1,weight=1)
        self._prog_lbl=ctk.CTkLabel(prog,text="● System Ready.",
            font=ctk.CTkFont("Segoe UI",10),text_color=TXT3,fg_color=BG1)
        self._prog_lbl.grid(row=0,column=0,padx=(10,8),pady=5)
        self._prog_bar=ctk.CTkProgressBar(prog,progress_color=GRN,fg_color=BG3,
            height=6,corner_radius=3)
        self._prog_bar.grid(row=0,column=1,sticky="ew",pady=12,padx=(0,8)); self._prog_bar.set(0)
        self._prog_pct=ctk.CTkLabel(prog,text="",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=GRN,fg_color=BG1,width=40)
        self._prog_pct.grid(row=0,column=2,padx=(0,10))

        # Generated Metadata section
        gen=ctk.CTkFrame(main,fg_color=GLASS,corner_radius=12,
            border_width=1,border_color=GLASS_BDR)
        gen.grid(row=3,column=0,sticky="nsew",padx=8,pady=(0,8))
        gen.grid_columnconfigure(0,weight=1); gen.grid_rowconfigure(1,weight=1)
        gen_hdr=ctk.CTkFrame(gen,fg_color="transparent",corner_radius=0,height=42)
        gen_hdr.grid(row=0,column=0,sticky="ew",padx=14,pady=(10,0))
        gen_hdr.grid_propagate(False); gen_hdr.grid_columnconfigure(0,weight=1)
        self._gen_count_lbl=ctk.CTkLabel(gen_hdr,text="Generated Metadata (0)",
            font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=TXT,fg_color="transparent")
        self._gen_count_lbl.grid(row=0,column=0,sticky="w")
        self._gen_scroll=ctk.CTkScrollableFrame(gen,fg_color="transparent",
            scrollbar_button_color=BG3,scrollbar_button_hover_color=BG4,corner_radius=0)
        self._gen_scroll.grid(row=1,column=0,sticky="nsew",padx=8,pady=(6,8))
        self._gen_scroll.grid_columnconfigure(0,weight=1)
        self._gen_empty_lbl=ctk.CTkLabel(self._gen_scroll,
            text="Results will appear here after generation.",
            font=ctk.CTkFont("Segoe UI",12),text_color=TXT3,fg_color="transparent")
        self._gen_empty_lbl.grid(row=0,column=0,pady=40)

    def _sel_platform(self,plat):
        rules=PLATFORM_RULES.get(plat,{})
        kw_val=min(rules.get("kw",49),49)
        for var,sl,val in [(self.ai_title_var,self._title_sl,rules.get("title",130)),
                           (self.ai_desc_var,self._desc_sl,rules.get("desc",200)),
                           (self.ai_kw_var,self._kw_sl,kw_val)]:
            var.set(str(val)); sl.set(val)
            lbl=getattr(sl,"_value_label",None)
            if lbl: lbl.configure(text=str(val))
        for p,btn in self._plat_btns.items():
            btn.configure(fg_color=GRN if p==plat else BG3,
                text_color=ABSOLUTE_BG if p==plat else TXT2,
                border_color=GRN if p==plat else GLASS_BDR)
        self._save_settings()

    # ── DnD ────────────────────────────────────────────────────────
    def _on_drag_enter(self,event):
        self._ws_empty.configure(text_color=GRN)
        self._thumb_scroll.configure(fg_color=GRN_DIM); return event.action
    def _on_drag_leave(self,event):
        self._ws_empty.configure(text_color=TXT3)
        self._thumb_scroll.configure(fg_color=BG3); return event.action
    def _on_drop(self,event):
        self._on_drag_leave(event)
        raw=event.data
        paths=[p.strip('{}') for p in raw.split('} {')] if '{' in raw else raw.split()
        paths=[p.strip('{}') for p in paths]
        expanded=[]
        for p in paths:
            if os.path.isdir(p):
                try:
                    for fn in os.listdir(p):
                        fp=os.path.join(p,fn)
                        if os.path.isfile(fp): expanded.append(fp)
                except: pass
            elif os.path.isfile(p): expanded.append(p)
        self._add_images(expanded)

    # ── Image import ────────────────────────────────────────────────
    def _browse_images(self):
        paths=filedialog.askopenfilenames(title="Select images",
            filetypes=[("Supported","*.jpg *.jpeg *.png *.webp *.gif *.tiff *.tif *.svg *.eps *.mp4 *.mov"),
                       ("All","*.*")])
        if paths: self._add_images(list(paths))

    def _add_images(self,paths):
        existing=set(self._all_paths)
        new=[p for p in paths if p not in existing
             and os.path.splitext(p)[1].lower() in ALL_SUPPORTED_EXTS]
        if not new: return
        # Track source folder for CSV naming
        if new and not self._source_folder:
            self._source_folder=os.path.dirname(new[0])
        for p in new:
            self._all_paths.append(p); self._results[p]={"status":"waiting"}
        self._rebuild_thumb_grid()
        self._gen_btn.configure(text=f"✨  Generate ({len(self._all_paths)})")
        self._update_progress()

    def _rebuild_thumb_grid(self):
        # Destroy all thumb cells (not the empty label — it's managed separately)
        for w in self._thumb_grid.winfo_children():
            if w is not self._ws_empty:
                try: w.destroy()
                except: pass

        total=len(self._all_paths)
        if total==0:
            self._ws_empty.pack(expand=True,fill="both",padx=20,pady=12)
            return
        self._ws_empty.pack_forget()

        CELL=90
        for i,path in enumerate(self._all_paths):
            cell=ctk.CTkFrame(self._thumb_grid,fg_color=BG4,
                corner_radius=4,width=CELL,height=CELL)
            cell.pack(side="left",padx=(0,2))
            cell.pack_propagate(False)

            lbl=ctk.CTkLabel(cell,text="⟳",
                font=ctk.CTkFont("Segoe UI",11),
                fg_color=BG4,text_color=TXT3,
                width=CELL,height=CELL,corner_radius=4)
            lbl.place(relx=0.5,rely=0.5,anchor="center")

            # Status dot overlay
            st=self._results.get(path,{}).get("status","waiting")
            dot_text= "✓" if st=="done" else ("✗" if st=="failed" else "")
            dot_bg  = GRN_DIM if st=="done" else (RED_DIM if st=="failed" else "")
            dot_fg  = GRN if st=="done" else (RED_BTN if st=="failed" else "")
            if dot_text:
                dot=ctk.CTkLabel(cell,text=dot_text,
                    font=ctk.CTkFont("Segoe UI",8,"bold"),
                    fg_color=dot_bg,text_color=dot_fg,
                    corner_radius=8,width=14,height=14)
                dot.place(relx=1.0,rely=0.0,anchor="ne",x=-2,y=2)

            def _load(p=path,l=lbl):
                img=make_thumb(p,(CELL-4,CELL-4))
                if img: self._thumb_queue.put((l,img))
            threading.Thread(target=_load,daemon=True).start()


    def _update_progress(self,done=None,total=None,msg=None):
        t=total or len(self._all_paths)
        d=done if done is not None else sum(1 for r in self._results.values() if r.get("status")=="done")
        failed=sum(1 for r in self._results.values() if r.get("status")=="failed")
        if t==0:
            self._prog_lbl.configure(text="● System Ready.",text_color=TXT3)
            self._prog_bar.set(0); self._prog_pct.configure(text=""); return
        self._prog_lbl.configure(
            text=msg or f"Generated {d}/{t}  |  {d} successful  |  {failed} failed",
            text_color=TXT2)
        pct=d/t if t else 0
        self._prog_bar.set(pct); self._prog_pct.configure(text=f"{int(pct*100)}%" if t else "")
        self.p_ok.configure(text=f"✓  {d} done")
        self.p_err.configure(text=f"✗  {failed} failed")
        self.p_pend.configure(text=f"○  {t-d-failed} pending")

    def _clear_all(self,confirm=True):
        if self.ai_running: messagebox.showwarning("Busy","Stop generation first."); return
        if confirm and self._all_paths:
            if not messagebox.askyesno("Clear","Remove all files and results?"): return
        self._all_paths.clear(); self._results.clear(); self._source_folder=""
        self._clear_results(); self._rebuild_thumb_grid()
        self._gen_btn.configure(text="✨  Generate (0)")
        self._update_progress()

    def _clear_results(self):
        for c in self._result_cards:
            try: c.destroy()
            except: pass
        self._result_cards=[]
        self._gen_count_lbl.configure(text="Generated Metadata (0)")
        self._gen_empty_lbl.grid(row=0,column=0,pady=40)

    def _add_result_card(self,path):
        if self._gen_empty_lbl.winfo_viewable():
            self._gen_empty_lbl.grid_remove()
        res=self._results.get(path,{})
        idx=len(self._result_cards)
        card=MetaResultCard(self._gen_scroll,path,res,on_redo=lambda p=path:self._redo_single(p))
        card.grid(row=idx,column=0,sticky="ew",padx=4,pady=(0,6))
        self._result_cards.append(card)
        done=sum(1 for r in self._results.values() if r.get("status")=="done")
        self._gen_count_lbl.configure(text=f"Generated Metadata ({done})")
        try: self._gen_scroll._parent_canvas.yview_moveto(1.0)
        except: pass

    # ── GENERATE (concurrent) ─────────────────────────────────────
    def start_generate(self):
        if self.ai_running: messagebox.showwarning("Busy","Already generating."); return
        if not self._all_paths: messagebox.showerror("No Images","Add images first."); return
        if not get_active_keys(self.prefs):
            messagebox.showerror("No API Keys","Open 'API Configuration'."); return
        self.ai_running=True; self.ai_stop_flag=False
        self._gen_btn.configure(state="disabled",text="⟳  Generating…")
        targets=[p for p in self._all_paths
                 if self._results.get(p,{}).get("status") in ("waiting","failed")]
        for p in targets: self._results[p]={"status":"waiting"}
        self._rebuild_thumb_grid()
        threading.Thread(target=self._gen_thread,args=(targets,),daemon=True).start()

    def _stop_ai(self):
        self.ai_stop_flag=True; self.set_status("■  Stopping…",AMB_BTN)

    def _gen_thread(self,targets):
        mode=self.current_mode
        custom=self.ai_custom_var.get()
        single_kw=self.ai_single_kw_var.get()
        themes=", ".join(s for s,v in self._style_vars.items() if v.get())
        prefix=(self.ai_prefix_text_var.get().strip()
                if self.ai_prefix_on_var.get() else "")
        suffix_title=(self.ai_suffix_text_var.get().strip()
                      if self.ai_suffix_on_var.get() else "")
        concurrency=max(1,min(4,int(self.ai_concurrency_var.get())))

        if mode=="meta":
            tc=int(self.ai_title_var.get() or 130)
            dc=int(self.ai_desc_var.get() or 200)
            kn=min(int(self.ai_kw_var.get() or 49),49)
            prompt=build_meta_prompt(tc,dc,kn,custom,single_kw,themes,prefix,suffix_title)
        else:
            mw=int(self.ai_words_var.get() or 60)
            prompt=build_prompt_prompt(mw,list(self._style_vars.keys()),custom)

        total=len(targets); done_count=0
        worker_sem=threading.Semaphore(concurrency)
        lock=threading.Lock()
        finished=threading.Event()
        remaining=[total]

        def process_one(path,i):
            nonlocal done_count
            try:
                if self.ai_stop_flag: return
                fname=os.path.basename(path)
                self._results[path]={"status":"working"}
                self.after(0,lambda f=fname,n=i+1,t=total:
                    self._update_progress(done=done_count,total=t,
                        msg=f"⟳  [{n}/{t}] {f}"))
                try:
                    ext=os.path.splitext(path)[1].lower()
                    if ext in VECTOR_EXTS or ext in VIDEO_EXTS:
                        raise ValueError("Vector/video: needs JPG preview")
                    raw,provider,model_id,key_idx=call_with_failover(
                        path,prompt,self.prefs,
                        status_cb=lambda msg:self.after(0,
                            lambda m=msg:self.set_status(f"⟳  {m}",GRN)))
                    model_used=(f"⚙ {provider} · {model_label(provider,model_id)}"
                                +(f" ({key_idx})" if key_idx else ""))
                    if mode=="meta":
                        title,desc,kw=parse_meta(raw)
                        # Apply prefix/suffix to title
                        if prefix and not title.startswith(prefix):
                            title=prefix+" "+title
                        if suffix_title and not title.endswith(suffix_title):
                            title=title+" "+suffix_title
                        # Trim to char limit
                        if len(title)>tc: title=title[:tc].rsplit(" ",1)[0]
                        if single_kw: kw=enforce_single_keywords(kw)
                        self._results[path]={
                            "status":"done","title":title,"desc":desc,
                            "kw":kw,"model_used":model_used}
                    else:
                        self._results[path]={"status":"done",
                            "prompt":raw.strip(),"model_used":model_used}
                    with lock: done_count+=1
                    self.after(0,lambda p=path:(
                        self._add_result_card(p),self._rebuild_thumb_grid()))
                except Exception as e:
                    self._results[path]={"status":"failed","error":str(e)[:120]}
                    self.after(0,self._rebuild_thumb_grid)
                self.after(0,lambda n=done_count,t=total:
                    self._update_progress(done=n,total=t))
            finally:
                worker_sem.release()
                with lock:
                    remaining[0]-=1
                    if remaining[0]==0: finished.set()

        for i,path in enumerate(targets):
            if self.ai_stop_flag: break
            worker_sem.acquire()
            t=threading.Thread(target=process_one,args=(path,i),daemon=True)
            t.start()

        # Signal remaining threads to finish
        # Wait for all workers
        finished.wait(timeout=3600)
        self.after(0,self._gen_done)

    def _gen_done(self):
        self.ai_running=False
        total=len(self._all_paths)
        done=sum(1 for r in self._results.values() if r.get("status")=="done")
        failed=sum(1 for r in self._results.values() if r.get("status")=="failed")
        self._gen_btn.configure(state="normal",text=f"✨  Generate ({total})")
        self.set_status(f"● Done — {done} generated · {failed} failed",
                        GRN if failed==0 else AMB_BTN)
        self._update_progress(done=done,total=total)
        self._rebuild_thumb_grid()

    def _redo_single(self,path):
        if self.ai_running: return
        self._results[path]={"status":"waiting"}
        self._result_cards=[c for c in self._result_cards if c.path!=path]
        self.ai_running=True; self.ai_stop_flag=False
        self._gen_btn.configure(state="disabled")
        threading.Thread(target=self._gen_thread,args=([path],),daemon=True).start()

    # ── EXPORT ─────────────────────────────────────────────────────
    def _export_csv(self):
        done=[p for p in self._all_paths if self._results.get(p,{}).get("status")=="done"]
        if not done: messagebox.showinfo("No Results","No generated results yet."); return
        # CSV filename: #foldername
        folder_name=os.path.basename(self._source_folder) if self._source_folder else "export"
        ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name=f"#{folder_name}.csv"
        path=filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")],initialfile=default_name)
        if not path: return
        try:
            mode=self.current_mode
            fields=(["Filename","Title","Description","Keywords"]
                    if mode=="meta" else ["Filename","Prompt"])
            def row_for(p):
                r=self._results[p]; fn=os.path.basename(p)
                if mode=="meta":
                    return {"Filename":fn,"Title":r.get("title",""),
                            "Description":r.get("desc",""),"Keywords":r.get("kw","")}
                return {"Filename":fn,"Prompt":r.get("prompt","")}
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
                w.writerows(row_for(p) for p in done)
            self.set_status(f"✓  CSV saved — {len(done)} rows",GRN)
            messagebox.showinfo("Saved",f"CSV saved:\n{path}")
        except Exception as e: messagebox.showerror("Error",str(e))

    def _download_zip(self):
        done=[p for p in self._all_paths if self._results.get(p,{}).get("status")=="done"]
        if not done: messagebox.showinfo("No Results","No generated results yet."); return
        import zipfile,pathlib
        downloads=pathlib.Path.home()/"Downloads"; downloads.mkdir(exist_ok=True)
        folder_name=os.path.basename(self._source_folder) if self._source_folder else "export"
        out=downloads/f"#{folder_name}.zip"
        try:
            with zipfile.ZipFile(out,"w",zipfile.ZIP_STORED) as zf:
                for p in done: zf.write(p,os.path.basename(p))
            self.set_status(f"✓  ZIP saved → Downloads/{out.name}",GRN)
            messagebox.showinfo("ZIP Saved",f"Saved {len(done)} files to:\n{out}")
        except Exception as e: messagebox.showerror("ZIP Error",str(e))

    # ══════════════════════════════════════════════════════════════
    #  EMBED TAB
    # ══════════════════════════════════════════════════════════════
    def _build_embed_tab(self,parent):
        parent.grid_columnconfigure(0,weight=1); parent.grid_columnconfigure(1,weight=0)
        parent.grid_rowconfigure(0,weight=1)
        left=ctk.CTkScrollableFrame(parent,fg_color=BG1,scrollbar_button_color=BG3,corner_radius=0)
        left.grid(row=0,column=0,sticky="nsew",padx=(14,6),pady=12)
        left.grid_columnconfigure(0,weight=1); self._el=left
        log_outer=ctk.CTkFrame(parent,fg_color=BG2,corner_radius=16,
            border_width=1,border_color=GLASS_BDR,width=220)
        log_outer.grid(row=0,column=1,sticky="nsew",padx=(0,10),pady=10)
        log_outer.grid_propagate(False); log_outer.grid_rowconfigure(1,weight=1)
        log_outer.grid_columnconfigure(0,weight=1)
        self._build_embed_log(log_outer)
        self._build_emb_actions(); self._build_csv_card()
        self._build_folder_card(); self._build_map_card()

    def _ec(self):
        f=ctk.CTkFrame(self._el,fg_color=GLASS,corner_radius=12,
            border_width=1,border_color=GLASS_BDR)
        f.pack(fill="x",pady=(0,10)); f.grid_columnconfigure(0,weight=1); return f

    def _ech(self,p,num,title,bcmd=None):
        h=ctk.CTkFrame(p,fg_color=BG3,corner_radius=12,height=52)
        h.pack(fill="x"); h.grid_propagate(False); h.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(h,text=str(num),font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=GRN,text_color=ABSOLUTE_BG,corner_radius=50,width=36,height=36
        ).grid(row=0,column=0,padx=(14,10),pady=8)
        ctk.CTkLabel(h,text=title,font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=TXT2,fg_color=BG3).grid(row=0,column=1,sticky="w")
        if bcmd:
            ctk.CTkButton(h,text="Browse",width=98,height=34,
                font=ctk.CTkFont("Segoe UI",12,"bold"),
                fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,
                corner_radius=20,command=bcmd).grid(row=0,column=2,padx=(0,12),pady=9)

    def _esw(self,p,t,v):
        return ctk.CTkSwitch(p,text=t,variable=v,font=ctk.CTkFont("Segoe UI",12),
            progress_color=GRN,button_color=TXT,text_color=TXT2,
            fg_color=GLASS_BDR,onvalue=True,offvalue=False,width=56,height=28)

    def _build_emb_actions(self):
        row=ctk.CTkFrame(self._el,fg_color=BG1,corner_radius=0)
        row.pack(fill="x",pady=(0,10)); row.grid_columnconfigure(0,weight=1)
        self.embed_btn=ctk.CTkButton(row,text="▶  Start Embedding",
            font=ctk.CTkFont("Segoe UI",15,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,
            height=54,corner_radius=27,command=self.start_embed)
        self.embed_btn.grid(row=0,column=0,sticky="ew")
        ctk.CTkButton(row,text="↺",width=54,height=54,
            font=ctk.CTkFont("Segoe UI",20,"bold"),
            fg_color=RED_DIM,hover_color=RED_BTN_H,text_color=RED_BTN,
            corner_radius=27,command=self.reset_embed).grid(row=0,column=1,padx=(8,0))
        ctk.CTkButton(row,text="💾  Save Log",width=136,height=54,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BG3,hover_color=BG4,text_color=TXT2,
            corner_radius=27,command=self.export_log).grid(row=0,column=2,padx=(8,0))

    def _build_csv_card(self):
        c=self._ec(); self._ech(c,"1","Load CSV",self.load_csv)
        body=ctk.CTkFrame(c,fg_color=GLASS,corner_radius=0)
        body.pack(fill="x",padx=14,pady=(10,12)); body.grid_columnconfigure(0,weight=1)
        ctk.CTkEntry(body,textvariable=self.csv_path_var,state="readonly",height=40,
            font=ctk.CTkFont("Segoe UI",12),fg_color=BG3,text_color=TXT,
            border_color=GLASS_BDR,corner_radius=12).pack(fill="x",pady=(0,10))
        row=ctk.CTkFrame(body,fg_color=GLASS,corner_radius=0); row.pack(fill="x")
        row.grid_columnconfigure(0,weight=1)
        self.csv_badge=ctk.CTkLabel(row,text="No CSV loaded",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,text_color=TXT3,corner_radius=12,padx=12,pady=5)
        self.csv_badge.grid(row=0,column=0,sticky="w")
        self._esw(row,"Match Filename Only",self.match_only_var).grid(row=0,column=1,sticky="e",padx=(10,0))

    def _build_folder_card(self):
        c=self._ec(); self._ech(c,"2","Image Folder",self.browse_embed_folder)
        body=ctk.CTkFrame(c,fg_color=GLASS,corner_radius=0)
        body.pack(fill="x",padx=14,pady=(10,12)); body.grid_columnconfigure(0,weight=1)
        ctk.CTkEntry(body,textvariable=self.folder_path_var,state="readonly",height=40,
            font=ctk.CTkFont("Segoe UI",12),fg_color=BG3,text_color=TXT,
            border_color=GLASS_BDR,corner_radius=12).pack(fill="x",pady=(0,10))
        row=ctk.CTkFrame(body,fg_color=GLASS,corner_radius=0); row.pack(fill="x")
        row.grid_columnconfigure(0,weight=1)
        self.folder_badge=ctk.CTkLabel(row,text="No folder selected",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,text_color=TXT3,corner_radius=12,padx=12,pady=5)
        self.folder_badge.grid(row=0,column=0,sticky="w")
        self._esw(row,"Include Sub-Folders",self.subfolder_var).grid(row=0,column=1,sticky="e",padx=(10,0))

    def _build_map_card(self):
        c=self._ec(); self._ech(c,"3","Map Columns")
        body=ctk.CTkFrame(c,fg_color=GLASS,corner_radius=0)
        body.pack(fill="x",padx=14,pady=(10,12))
        body.grid_columnconfigure(0,weight=1); body.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(body,text="Auto-detected from column names.",
            font=ctk.CTkFont("Segoe UI",11),text_color=TXT3,fg_color=GLASS
        ).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,8))
        self.col_combos={}
        for i,(lbl,var) in enumerate([("FILENAME",self.col_file_var),("TITLE",self.col_title_var),
                                       ("KEYWORDS",self.col_kw_var),("DESCRIPTION",self.col_desc_var)]):
            r=(i//2)+1; col=i%2
            cell=ctk.CTkFrame(body,fg_color=GLASS,corner_radius=0)
            cell.grid(row=r,column=col,sticky="ew",padx=(0 if col==0 else 8,0),pady=4)
            cell.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(cell,text=lbl,font=ctk.CTkFont("Segoe UI",10,"bold"),
                text_color=TXT3,fg_color=GLASS).pack(anchor="w")
            cb=ctk.CTkComboBox(cell,variable=var,values=["(skip)"],state="readonly",
                font=ctk.CTkFont("Segoe UI",12),fg_color=BG3,text_color=TXT,
                border_color=GLASS_BDR,button_color=GRN,button_hover_color=GRN_H,
                dropdown_fg_color=BG3,dropdown_text_color=TXT,dropdown_hover_color=BG4,
                corner_radius=12,height=38,command=lambda v:self._update_match())
            cb.pack(fill="x",pady=(4,0)); self.col_combos[lbl]=cb
        ctk.CTkFrame(body,fg_color=GLASS_BDR,height=1,corner_radius=0).grid(
            row=3,column=0,columnspan=2,sticky="ew",pady=(12,8))
        rm=ctk.CTkFrame(body,fg_color=BG3,corner_radius=12)
        rm.grid(row=4,column=0,columnspan=2,sticky="ew",pady=(0,4)); rm.grid_columnconfigure(0,weight=1)
        info=ctk.CTkFrame(rm,fg_color=BG3,corner_radius=0)
        info.grid(row=0,column=0,sticky="w",padx=14,pady=12)
        ctk.CTkLabel(info,text="Remove Program Name",font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=TXT2,fg_color=BG3).pack(anchor="w")
        ctk.CTkLabel(info,text="Clears upscaler/software name from metadata",
            font=ctk.CTkFont("Segoe UI",11),text_color=TXT3,fg_color=BG3).pack(anchor="w")
        self._esw(rm,"On",self.rm_prog_var).grid(row=0,column=1,padx=(0,14),pady=12)

    def _build_embed_log(self,parent):
        hdr=ctk.CTkFrame(parent,fg_color=BG3,corner_radius=12,height=44)
        hdr.grid(row=0,column=0,sticky="ew",padx=8,pady=(8,4)); hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(hdr,text="ACTIVITY LOG",font=ctk.CTkFont("Segoe UI",11,"bold"),
            text_color=TXT3,fg_color=BG3).grid(row=0,column=0,sticky="w",padx=12)
        ctk.CTkButton(hdr,text="Clear",width=58,height=28,fg_color=BG1,hover_color=BG4,
            text_color=TXT3,corner_radius=12,command=self.clear_log
        ).grid(row=0,column=1,padx=(0,8))
        self.log_text=ctk.CTkTextbox(parent,font=ctk.CTkFont("Consolas",11),
            fg_color=LOG_BG,text_color=TXT,corner_radius=12,wrap="word",state="disabled",
            scrollbar_button_color=BG3,scrollbar_button_hover_color=BG4)
        self.log_text.grid(row=1,column=0,sticky="nsew",padx=8,pady=(0,8))

    def log(self,msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end",f"{self.ts()}   {msg}\n")
        self.log_text.see("end"); self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_text.configure(state="normal"); self.log_text.delete("1.0","end")
        self.log_text.configure(state="disabled")

    def export_log(self):
        content=self.log_text.get("1.0","end").strip()
        if not content: messagebox.showinfo("Log","Empty."); return
        p=filedialog.asksaveasfilename(defaultextension=".txt",filetypes=[("Text","*.txt")],
            initialfile=f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if p:
            with open(p,'w',encoding='utf-8') as f: f.write(content)
            self.log(f"✓  Saved → {os.path.basename(p)}")

    def load_csv(self):
        p=filedialog.askopenfilename(title="Select CSV",filetypes=[("CSV","*.csv"),("All","*.*")])
        if p: self._do_load_csv(p)

    def _do_load_csv(self,path):
        try:
            with open(path,newline='',encoding='utf-8-sig') as f:
                reader=csv.DictReader(f)
                self.csv_rows=list(reader); self.csv_headers=list(reader.fieldnames or [])
            self.csv_path_var.set(path)
            self.csv_badge.configure(text=f"🗂  {len(self.csv_rows)} rows",
                fg_color=GRN_DIM,text_color=GRN)
            self.log(f"✓  CSV — {len(self.csv_rows)} rows")
            self._update_combos(); self._update_match()
        except Exception as e: messagebox.showerror("CSV Error",str(e))

    def _update_combos(self):
        opts=["(skip)"]+self.csv_headers
        hints={"FILENAME":["filename","file","name","image"],"TITLE":["title"],
               "KEYWORDS":["keyword","tag","kw"],"DESCRIPTION":["desc","caption","description"]}
        vmap={"FILENAME":self.col_file_var,"TITLE":self.col_title_var,
              "KEYWORDS":self.col_kw_var,"DESCRIPTION":self.col_desc_var}
        for lbl,cb in self.col_combos.items():
            cb.configure(values=opts)
            g=next((c for h in hints.get(lbl,[]) for c in self.csv_headers if h in c.lower()),"")
            vmap[lbl].set(g or "(skip)")

    def browse_embed_folder(self):
        p=filedialog.askdirectory(title="Select folder")
        if p: self.folder_path_var.set(p); self._update_match(); self.log(f"✓  Folder — {p}")

    def _update_match(self):
        folder=self.folder_path_var.get(); col_f=self.col_file_var.get()
        if not folder or not self.csv_rows or not col_f or col_f=="(skip)": return
        finder=find_recursive if self.subfolder_var.get() else find_file
        matched=sum(1 for row in self.csv_rows
            if finder(folder,(row.get(col_f) or "").strip(),self.match_only_var.get()))
        total=len(self.csv_rows)
        color=GRN if matched==total else AMB_BTN if matched>0 else RED_BTN
        self.folder_badge.configure(text=f"📁  {matched} of {total} matched",
            fg_color=GRN_DIM,text_color=color)

    def reset_embed(self):
        if self.embed_running: messagebox.showwarning("Busy","Wait."); return
        if not messagebox.askyesno("Reset","Clear everything?"): return
        self.csv_path_var.set(""); self.folder_path_var.set("")
        for v in [self.col_file_var,self.col_title_var,self.col_kw_var,self.col_desc_var]:
            v.set("(skip)")
        self.csv_rows=[]; self.csv_headers=[]
        self.csv_badge.configure(text="No CSV loaded",fg_color=BG3,text_color=TXT3)
        self.folder_badge.configure(text="No folder selected",fg_color=BG3,text_color=TXT3)
        for cb in self.col_combos.values(): cb.configure(values=["(skip)"])
        self.embed_btn.configure(text="▶  Start Embedding",state="normal")
        self.clear_log(); self.log("↺  Reset")

    def start_embed(self):
        if self.embed_running: return
        et=find_exiftool()
        if not et: messagebox.showerror("ExifTool not found","Place exiftool.exe next to this app."); return
        if not self.csv_rows: messagebox.showerror("No CSV","Load a CSV first."); return
        if not self.folder_path_var.get(): messagebox.showerror("No folder","Select folder."); return
        fc=self.col_file_var.get()
        if not fc or fc=="(skip)": messagebox.showerror("Column missing","Select filename column."); return
        self.embed_running=True
        self.embed_btn.configure(state="disabled",text="⟳  Processing…")
        threading.Thread(target=self._embed_thread,args=(et,),daemon=True).start()

    def _embed_thread(self,et):
        folder=self.folder_path_var.get(); col_f=self.col_file_var.get()
        col_t=self.col_title_var.get(); col_k=self.col_kw_var.get(); col_d=self.col_desc_var.get()
        use_sub=self.subfolder_var.get(); use_ext=self.match_only_var.get(); rm_prog=self.rm_prog_var.get()
        total=len(self.csv_rows); ok=skipped=errors=0
        finder=find_recursive if use_sub else find_file
        self.after(0,lambda:self.log(f"▶  Batch — {total} rows"))
        for i,row in enumerate(self.csv_rows):
            fn=(row.get(col_f) or "").strip()
            if not fn: skipped+=1; continue
            fp=finder(folder,fn,use_ext)
            if not fp: skipped+=1; self.after(0,lambda f=fn:self.log(f"⚠  Not found: {f}")); continue
            cmd=[et,'-overwrite_original','-codedcharacterset=UTF8']
            title=(row.get(col_t) or "").strip() if col_t and col_t!="(skip)" else ""
            kw_raw=(row.get(col_k) or "").strip() if col_k and col_k!="(skip)" else ""
            desc=(row.get(col_d) or "").strip() if col_d and col_d!="(skip)" else ""
            if title: cmd+=[f'-Title={title}',f'-ObjectName={title}',f'-Headline={title}']
            if kw_raw:
                for kw in [k.strip() for k in kw_raw.replace(';',',').split(',') if k.strip()]:
                    cmd+=[f'-Keywords={kw}',f'-Subject={kw}']
            if desc: cmd+=[f'-Description={desc}',f'-Caption-Abstract={desc}']
            if rm_prog: cmd+=['-Software=','-CreatorTool=','-HistorySoftwareAgent=']
            cmd.append(fp)
            try:
                flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
                res=subprocess.run(cmd,capture_output=True,text=True,timeout=30,creationflags=flags)
                actual=os.path.basename(fp)
                if res.returncode==0: ok+=1; self.after(0,lambda fn=actual:self.log(f"✓  {fn}"))
                else:
                    errors+=1; err=(res.stderr or res.stdout or "Unknown").strip()
                    self.after(0,lambda fn=actual,e=err:self.log(f"✗  {fn} — {e}"))
            except Exception as ex:
                errors+=1; self.after(0,lambda fn=fn,e=str(ex):self.log(f"✗  {fn} — {e}"))
        summary=f"{ok} embedded · {skipped} not found · {errors} errors"
        self.after(0,lambda:(self.log(f"● Done — {summary}"),
            self.set_status(f"Done — {summary}",GRN),
            self.embed_btn.configure(state="normal",text="▶  Start Again"),
            setattr(self,'embed_running',False)))

    # ── STATUS BAR ─────────────────────────────────────────────────
    def _build_statusbar(self):
        sb=ctk.CTkFrame(self,fg_color=BG2,corner_radius=0,height=40)
        sb.grid(row=3,column=0,sticky="ew"); sb.grid_propagate(False)
        sb.grid_columnconfigure(4,weight=1)
        self.p_ok=ctk.CTkLabel(sb,text="✓  0 done",font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=GRN_DIM,text_color=GRN,corner_radius=20,padx=10,pady=3)
        self.p_ok.grid(row=0,column=0,padx=(10,4),pady=8)
        self.p_err=ctk.CTkLabel(sb,text="✗  0 failed",font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=RED_DIM,text_color=RED_BTN,corner_radius=20,padx=10,pady=3)
        self.p_err.grid(row=0,column=1,padx=4,pady=8)
        self.p_pend=ctk.CTkLabel(sb,text="○  0 pending",font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=AMB_DIM,text_color=AMB_BTN,corner_radius=20,padx=10,pady=3)
        self.p_pend.grid(row=0,column=2,padx=4,pady=8)
        self.sb_status=ctk.CTkLabel(sb,text="",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=GRN,fg_color=BG2)
        self.sb_status.grid(row=0,column=3,padx=(8,0),sticky="w")
        self.sb_et=ctk.CTkLabel(sb,text="ExifTool · checking…",
            font=ctk.CTkFont("Segoe UI",10),text_color=TXT3,fg_color=BG2)
        self.sb_et.grid(row=0,column=5,padx=(0,14))

    def set_status(self,msg,color=None):
        self.sb_status.configure(text=msg,text_color=color or TXT3)

    def _check_et(self):
        et=find_exiftool()
        if et: self.sb_et.configure(text="ExifTool · ready",text_color=GRN)
        else: self.sb_et.configure(text="ExifTool · missing",text_color=RED_BTN)


if __name__=='__main__':
    app=App(); app.mainloop()
