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

def check_online():
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

def make_thumb(path, size=(120,85)):
    """Build a CTkImage off the main thread. Returns None on failure."""
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in VECTOR_EXTS or ext in VIDEO_EXTS:
            return None
        img = Image.open(path)
        img = img.convert("RGB")
        img.thumbnail(size, Image.LANCZOS)
        return ctk.CTkImage(img, size=img.size)
    except Exception:
        return None

# ── AI Engine ──────────────────────────────────────────────────────────
def img_to_b64(path):
    with open(path,'rb') as f: data=f.read()
    ext=os.path.splitext(path)[1].lower()
    mime={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png',
          '.gif':'image/gif','.webp':'image/webp',
          '.tiff':'image/tiff','.tif':'image/tiff'}.get(ext,'image/jpeg')
    return base64.b64encode(data).decode(),mime

def _post(url,body,headers,timeout=30):
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
    """Try each active key exactly once in order.
    On failure, immediately move to the next key.
    If all keys fail, raise with the last error."""
    seq=get_active_keys(prefs)
    if not seq: raise RuntimeError("No active API keys. Open 'API Configuration'.")
    last_err=""
    for provider,key,model,key_idx in seq:
        try:
            if status_cb:
                status_cb(f"{provider} · {model_label(provider,model)}…")
            raw=CALLERS[provider](key,model,path,prompt)
            return raw,provider,model,key_idx
        except Exception as e:
            last_err=f"{provider}: {str(e)[:120]}"
            # Log the failure and immediately try the next key
            continue
    raise RuntimeError(f"All keys failed. Last error: {last_err}")


# ── FIXED prompt builder with stronger output enforcement ──────────────
def build_meta_prompt(title_c, desc_c, kw_n, custom_prompt="",
                      single_kw=False, themes="", prefix="", suffix_title="",
                      avoid_copyright=False):
    directives = []
    if themes:
        directives.append(f"Content theme: {themes}. Reflect this in the metadata.")
    if single_kw:
        directives.append(f"Every keyword must be a single word only (no spaces or hyphens).")
    if avoid_copyright:
        directives.append(
            "Do not include any brand names, company names, trademarked terms, copyrighted "
            "character names, logos, product names, or celebrity names. Use only generic "
            "descriptive language instead (e.g. 'logo' not the brand name, 'sports car' not "
            "the manufacturer, 'cartoon character' not the character's name)."
        )
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


# Common brand/trademark fragments to filter from keywords when avoid_copyright is on.
# This is a post-processing safety net — the main enforcement is in the prompt itself.
_COPYRIGHT_KW_BLOCKLIST = {
    "nike","adidas","puma","reebok","apple","iphone","android","samsung","sony","disney",
    "marvel","pixar","dc comics","warner bros","netflix","coca-cola","coke","pepsi",
    "mcdonalds","starbucks","google","microsoft","windows","facebook","instagram","twitter",
    "tesla","bmw","mercedes","audi","toyota","honda","ford","chevrolet","ferrari","lamborghini",
    "louis vuitton","gucci","chanel","prada","rolex","batman","superman","spiderman",
    "mickey mouse","hello kitty","pokemon","mario","minecraft","playstation","xbox","nintendo",
}

def _strip_copyright_keywords(kw_string):
    """Drop any keyword that matches (or contains) a known brand/trademark fragment."""
    if not kw_string:
        return kw_string
    raw = [k.strip() for k in kw_string.split(",") if k.strip()]
    kept = []
    for kw in raw:
        low = kw.lower()
        if any(term in low for term in _COPYRIGHT_KW_BLOCKLIST):
            continue
        kept.append(kw)
    return ", ".join(kept)

# ══════════════════════════════════════════════════════════════════════
#  PALETTE — Black Glassmorphic
# ══════════════════════════════════════════════════════════════════════
BG1="#0a0a0a"; BG2="#111111"; BG3="#1a1a1a"; BG4="#222222"
GLASS="#161616"; GLASS_BDR="#2a2a2a"; GLASS_BDR_AC="#00c853"
TXT="#f0f0f0"; TXT2="#a0a0a0"; TXT3="#505050"
GRN="#00c853"; GRN_H="#00a040"; GRN_DIM="#00331a"
RED_BTN="#e53935"; RED_BTN_H="#b71c1c"; RED_DIM="#2a0000"
AMB_BTN="#f9a825"; AMB_BTN_H="#c67c00"; AMB_DIM="#2a1a00"
CYAN="#00e5ff"; LOG_BG="#050505"; ABSOLUTE_BG="#000000"

AI_PROVIDERS_ORDERED=["Gemini","Mistral","Groq","OpenAI","Claude","OpenRouter"]

PLATFORM_RULES = {
    "General":      {"kw":49,"title":150,"desc":250},
    "Adobe Stock":  {"kw":49,"title":150,"desc":250},
    "Shutterstock": {"kw":50,"title":200,"desc":200},
    "Getty Images": {"kw":50,"title":200,"desc":500},
    "Freepik":      {"kw":30,"title":150,"desc":200},
    "Pond5":        {"kw":50,"title":200,"desc":500},
    "iStock":       {"kw":50,"title":200,"desc":200},
    "Vecteezy":     {"kw":50,"title":200,"desc":200},
}

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
        return p+(f" ●{n}" if n else "")

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
                hover_color=GRN_H,text_color=ABSOLUTE_BG if p==self._cur else TXT2,
                corner_radius=8,command=lambda pv=p:self._switch(pv))
            btn.pack(side="left",padx=(8 if p==AI_PROVIDERS_ORDERED[0] else 3,0),pady=8)
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
            btn.configure(fg_color=GRN if s else BG3,
                text_color=ABSOLUTE_BG if s else TXT2,
                text=self._tab_text(pv))
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
            font=ctk.CTkFont("Segoe UI",12),fg_color=BG3,text_color=TXT,border_color=GRN_DIM,
            border_width=2,button_color=GRN,button_hover_color=GRN_H,dropdown_fg_color=BG4,
            dropdown_text_color=TXT,dropdown_hover_color=GRN_DIM,
            dropdown_font=ctk.CTkFont("Segoe UI",12),corner_radius=8,height=40,
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
        vld_lbl=ctk.CTkLabel(inner,text="",font=ctk.CTkFont("Segoe UI",11),text_color=TXT3,fg_color=BG2)
        ctk.CTkButton(er,text="Save",width=76,height=40,
            font=ctk.CTkFont("Segoe UI",12,"bold"),fg_color=GRN,hover_color=GRN_H,
            text_color=ABSOLUTE_BG,corner_radius=8,
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
                    text="✓  Valid" if ok else f"✗  {msg}",text_color=GRN if ok else RED_BTN))
            threading.Thread(target=_run,daemon=True).start()
        entry.bind("<FocusOut>",_live_validate); entry.bind("<Return>",_live_validate)
        ctk.CTkButton(inner,text=f"🔑  Get API Key from {p}",height=38,
            font=ctk.CTkFont("Segoe UI",11),fg_color=BG3,hover_color=BG4,text_color=TXT2,
            border_width=1,border_color=GLASS_BDR,corner_radius=8,
            command=lambda:self._open_url(cfg["key_url"])).pack(fill="x",padx=18,pady=(0,18))
        # RIGHT
        ctk.CTkLabel(self._rp,text="STORED KEYS",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT2,fg_color=BG1).pack(anchor="w",padx=16,pady=(16,8))
        ks=ctk.CTkScrollableFrame(self._rp,fg_color=BG1,corner_radius=0,scrollbar_button_color=BG3)
        ks.pack(fill="both",expand=True); ks.grid_columnconfigure(0,weight=1)
        if not keys:
            ctk.CTkLabel(ks,text="No keys saved yet.",font=ctk.CTkFont("Segoe UI",12),
                text_color=TXT3,fg_color=BG1).pack(pady=30); return
        for i,k in enumerate(keys): self._key_card(ks,p,i,k)

    def _key_card(self,parent,prov,idx,k):
        is_active=k.get("active",False); kv=k.get("key","")
        key_disp="..."+kv[-10:] if len(kv)>10 else kv
        card=ctk.CTkFrame(parent,fg_color="#0a1a0a" if is_active else BG3,
            corner_radius=10,border_width=1,border_color=GLASS_BDR_AC if is_active else GLASS_BDR)
        card.pack(fill="x",padx=12,pady=(0,8)); card.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(card,text="🔑",font=ctk.CTkFont("Segoe UI",14),
            fg_color="transparent",text_color=TXT2).grid(row=0,column=0,padx=(12,8),pady=(10,4),sticky="w")
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
        ctk.CTkButton(af,text="👁",width=34,height=28,fg_color="transparent",hover_color=BG4,
            text_color=TXT3,corner_radius=6,
            command=lambda kv2=kv,lb=kf:self._toggle_show(kv2,lb)).pack(side="left",padx=(0,4))
        ctk.CTkButton(af,text="⧉",width=34,height=28,fg_color="transparent",hover_color=BG4,
            text_color=TXT3,corner_radius=6,
            command=lambda kv2=kv:self._copy(kv2)).pack(side="left",padx=(0,4))
        vl=ctk.CTkLabel(af,text="? Test",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT3,fg_color=BG4,corner_radius=6,padx=8,pady=4,cursor="hand2")
        vl.pack(side="left",padx=(0,4))
        def _test(e=None,kv2=kv,lb=vl):
            lb.configure(text="⟳…",text_color=AMB_BTN)
            def _r():
                ok,msg=validate_key(prov,kv2)
                self.after(0,lambda:lb.configure(text="✓ OK" if ok else "✗ Bad",
                    text_color=GRN if ok else RED_BTN))
            threading.Thread(target=_r,daemon=True).start()
        vl.bind("<Button-1>",_test)
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
        ctk.CTkButton(af,text="🗑",width=34,height=28,fg_color="transparent",
            hover_color=RED_DIM,text_color=TXT3,corner_radius=6,
            command=lambda i=idx:self._del(prov,i)).pack(side="right")

    def _toggle_show(self,kv,lf):
        ch=lf.winfo_children()
        if ch:
            short="..."+kv[-10:] if len(kv)>10 else kv
            ch[0].configure(text=kv if ch[0].cget("text")==short else short)
    def _copy(self,kv): self.clipboard_clear(); self.clipboard_append(kv)
    def _activate(self,p,i): self.prefs["ai_keys"][p][i]["active"]=True; save_prefs(self.prefs); self._switch(p)
    def _deactivate(self,p,i): self.prefs["ai_keys"][p][i]["active"]=False; save_prefs(self.prefs); self._switch(p)
    def _del(self,p,i):
        if not messagebox.askyesno("Delete","Delete this key?",parent=self): return
        self.prefs["ai_keys"][p].pop(i); save_prefs(self.prefs); self._switch(p)
    def _add_key(self,p,key,vld_lbl=None):
        if not key: messagebox.showwarning("Empty","Paste a key first.",parent=self); return
        keys=self.prefs["ai_keys"][p]
        if any(k["key"]==key for k in keys): messagebox.showinfo("Duplicate","Already saved.",parent=self); return
        for k in keys: k["active"]=False
        keys.append({"key":key,"active":True})
        save_prefs(self.prefs); self._switch(p)
    def _save_model(self,p,label):
        self.prefs.setdefault("ai_models",{})[p]=model_id_from_label(p,label); save_prefs(self.prefs)
    def _open_url(self,url):
        import webbrowser; webbrowser.open(url)
    def _done(self):
        if self.on_close: self.on_close()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  EMBED WINDOW (compact popup)
# ══════════════════════════════════════════════════════════════════════
class EmbedWindow(ctk.CTkToplevel):
    def __init__(self,parent,csv_path=None,folder_path=None):
        super().__init__(parent); self.title("Embed Metadata")
        self.configure(fg_color=BG1); self.resizable(True,True)
        self.grab_set()
        self.csv_rows=[]; self.csv_headers=[]; self.embed_running=False
        self.col_combos={}  # set for real inside _build(); defensive default so
                             # a partial/failed build can never raise the
                             # "no attribute 'col_combos'" error on later use
        self.csv_path_var=StringVar(); self.folder_path_var=StringVar()
        self.col_file_var=StringVar(value="(skip)"); self.col_title_var=StringVar(value="(skip)")
        self.col_kw_var=StringVar(value="(skip)"); self.col_desc_var=StringVar(value="(skip)")
        self.match_only_var=BooleanVar(value=True); self.subfolder_var=BooleanVar(value=True)
        self.rm_prog_var=BooleanVar(value=True); self.rm_copy_var=BooleanVar(value=True)
        self._build()
        # Match the API Manager window's size, as requested
        self._center(920,620)
        self.protocol("WM_DELETE_WINDOW",self.destroy)
        # Auto-load whatever was just generated, so "generate then embed" is
        # a one-click flow instead of re-browsing for the CSV and folder.
        if folder_path:
            self.folder_path_var.set(folder_path)
            self.folder_status.configure(text=f"✓ {os.path.basename(folder_path)}",
                fg_color=GRN_DIM,text_color=GRN)
        if csv_path: self._do_load_csv(csv_path)

    def _center(self,w,h):
        self.update_idletasks()
        x=self.master.winfo_x()+(self.master.winfo_width()-w)//2
        y=self.master.winfo_y()+(self.master.winfo_height()-h)//2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1)
        # Header
        hdr=ctk.CTkFrame(self,fg_color=BG2,corner_radius=0,height=50)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(hdr,text="📋  Embed Metadata",
            font=ctk.CTkFont("Segoe UI",14,"bold"),text_color=TXT,fg_color=BG2
        ).grid(row=0,column=0,sticky="w",padx=16,pady=13)
        ctk.CTkButton(hdr,text="✕",width=32,height=32,fg_color="transparent",
            hover_color=RED_DIM,text_color=TXT3,corner_radius=6,
            command=self.destroy).grid(row=0,column=1,padx=10)

        # Body
        body=ctk.CTkFrame(self,fg_color=BG1,corner_radius=0)
        body.grid(row=1,column=0,sticky="nsew",padx=12,pady=12)
        body.grid_columnconfigure(0,weight=1)

        # 1. CSV row
        r1=self._section(body,"1","Load CSV",self._load_csv,0)
        self.csv_status=ctk.CTkLabel(r1,text="No CSV loaded",
            font=ctk.CTkFont("Segoe UI",10),text_color=TXT3,fg_color=BG3,
            corner_radius=8,padx=8,pady=2)
        self.csv_status.pack(side="left",padx=(8,0))

        # 2. Folder row
        r2=self._section(body,"2","Image Folder",self._browse_folder,1)
        self.folder_status=ctk.CTkLabel(r2,text="No folder selected",
            font=ctk.CTkFont("Segoe UI",10),text_color=TXT3,fg_color=BG3,
            corner_radius=8,padx=8,pady=2)
        self.folder_status.pack(side="left",padx=(8,0))

        # Column map (compact 2x2)
        cmap=ctk.CTkFrame(body,fg_color=GLASS,corner_radius=10,border_width=1,border_color=GLASS_BDR)
        cmap.grid(row=2,column=0,sticky="ew",pady=(0,8))
        cmap.grid_columnconfigure(0,weight=1); cmap.grid_columnconfigure(1,weight=1)
        self.col_combos={}
        fields=[("Filename",self.col_file_var),("Title",self.col_title_var),
                ("Keywords",self.col_kw_var),("Description",self.col_desc_var)]
        for i,(lbl,var) in enumerate(fields):
            r,c=i//2,i%2
            cell=ctk.CTkFrame(cmap,fg_color="transparent",corner_radius=0)
            cell.grid(row=r,column=c,sticky="ew",padx=(8 if c==0 else 4,4 if c==0 else 8),pady=4)
            cell.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(cell,text=lbl.upper(),font=ctk.CTkFont("Segoe UI",9,"bold"),
                text_color=TXT3,fg_color="transparent").pack(anchor="w")
            cb=ctk.CTkComboBox(cell,variable=var,values=["(skip)"],state="readonly",
                font=ctk.CTkFont("Segoe UI",11),fg_color=BG3,text_color=TXT,
                border_color=GRN_DIM,border_width=2,button_color=GRN,button_hover_color=GRN_H,
                dropdown_fg_color=BG4,dropdown_text_color=TXT,dropdown_hover_color=GRN_DIM,
                dropdown_font=ctk.CTkFont("Segoe UI",11),
                corner_radius=8,height=34,command=lambda v:None)
            cb.pack(fill="x",pady=(2,0)); self.col_combos[lbl]=cb

        # 4 toggles in 2x2 grid
        opts=ctk.CTkFrame(body,fg_color=GLASS,corner_radius=10,border_width=1,border_color=GLASS_BDR)
        opts.grid(row=3,column=0,sticky="ew",pady=(0,8))
        opts.grid_columnconfigure(0,weight=1); opts.grid_columnconfigure(1,weight=1)
        toggles=[
            ("Match Filename Only",self.match_only_var),
            ("Include Sub-Folders",self.subfolder_var),
            ("Remove Program Name",self.rm_prog_var),
            ("Remove Copyright",self.rm_copy_var),
        ]
        for i,(lbl,var) in enumerate(toggles):
            r,c=i//2,i%2
            tf=ctk.CTkFrame(opts,fg_color="transparent",corner_radius=0)
            tf.grid(row=r,column=c,sticky="ew",padx=10,pady=6)
            tf.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(tf,text=lbl,font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT2,fg_color="transparent").grid(row=0,column=0,sticky="w")
            ctk.CTkSwitch(tf,text="",variable=var,progress_color=GRN,button_color=TXT,
                fg_color=GLASS_BDR,onvalue=True,offvalue=False,width=44,height=22
            ).grid(row=0,column=1,sticky="e")

        # Action + log
        af=ctk.CTkFrame(body,fg_color="transparent",corner_radius=0)
        af.grid(row=4,column=0,sticky="ew",pady=(0,8))
        af.grid_columnconfigure(0,weight=1)
        self._emb_btn=ctk.CTkButton(af,text="▶  Start Embedding",height=44,
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,corner_radius=22,
            command=self._start)
        self._emb_btn.grid(row=0,column=0,sticky="ew")
        ctk.CTkButton(af,text="↺",width=44,height=44,
            font=ctk.CTkFont("Segoe UI",18,"bold"),fg_color=RED_DIM,hover_color=RED_BTN_H,
            text_color=RED_BTN,corner_radius=22,command=self._reset
        ).grid(row=0,column=1,padx=(6,0))

        self._log=ctk.CTkTextbox(body,height=120,font=ctk.CTkFont("Consolas",10),
            fg_color=LOG_BG,text_color=TXT,corner_radius=8,state="disabled")
        self._log.grid(row=5,column=0,sticky="ew")

    def _section(self,parent,num,title,cmd,row):
        f=ctk.CTkFrame(parent,fg_color=GLASS,corner_radius=10,border_width=1,border_color=GLASS_BDR)
        f.grid(row=row,column=0,sticky="ew",pady=(0,8)); f.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(f,text=num,font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=GRN,text_color=ABSOLUTE_BG,corner_radius=50,width=28,height=28
        ).grid(row=0,column=0,padx=(10,8),pady=8)
        ctk.CTkLabel(f,text=title,font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=TXT2,fg_color="transparent").grid(row=0,column=1,sticky="w")
        ctk.CTkButton(f,text="Browse",width=86,height=28,
            font=ctk.CTkFont("Segoe UI",11,"bold"),fg_color=GRN,hover_color=GRN_H,
            text_color=ABSOLUTE_BG,corner_radius=14,command=cmd
        ).grid(row=0,column=2,padx=(0,10),pady=8)
        return f

    def _load_csv(self):
        p=filedialog.askopenfilename(title="Select CSV",filetypes=[("CSV","*.csv"),("All","*.*")])
        if p: self._do_load_csv(p)

    def _do_load_csv(self,path):
        try:
            with open(path,newline='',encoding='utf-8-sig') as f:
                reader=csv.DictReader(f)
                self.csv_rows=list(reader); self.csv_headers=list(reader.fieldnames or [])
            self.csv_path_var.set(path)
            self.csv_status.configure(text=f"✓ {len(self.csv_rows)} rows",
                fg_color=GRN_DIM,text_color=GRN)
            self._update_combos(); self._log_msg(f"✓ CSV loaded — {len(self.csv_rows)} rows")
        except Exception as e: messagebox.showerror("CSV Error",str(e),parent=self)

    def _browse_folder(self):
        p=filedialog.askdirectory(title="Select image folder",parent=self)
        if p:
            self.folder_path_var.set(p)
            self.folder_status.configure(text=f"✓ {os.path.basename(p)}",
                fg_color=GRN_DIM,text_color=GRN)

    def _update_combos(self):
        opts=["(skip)"]+self.csv_headers
        hints={"Filename":["filename","file","name","image"],"Title":["title"],
               "Keywords":["keyword","tag","kw"],"Description":["desc","caption","description"]}
        vmap={"Filename":self.col_file_var,"Title":self.col_title_var,
              "Keywords":self.col_kw_var,"Description":self.col_desc_var}
        for lbl,cb in self.col_combos.items():
            cb.configure(values=opts)
            g=next((c for h in hints.get(lbl,[]) for c in self.csv_headers if h in c.lower()),"")
            vmap[lbl].set(g or "(skip)")

    def _log_msg(self,msg):
        self._log.configure(state="normal")
        self._log.insert("end",f"{msg}\n"); self._log.see("end")
        self._log.configure(state="disabled")

    def _reset(self):
        self.csv_rows=[]; self.csv_headers=[]
        self.csv_path_var.set(""); self.folder_path_var.set("")
        self.csv_status.configure(text="No CSV loaded",fg_color=BG3,text_color=TXT3)
        self.folder_status.configure(text="No folder selected",fg_color=BG3,text_color=TXT3)
        for cb in self.col_combos.values(): cb.configure(values=["(skip)"]); cb.set("(skip)")
        self._emb_btn.configure(state="normal",text="▶  Start Embedding")
        self._log.configure(state="normal"); self._log.delete("1.0","end"); self._log.configure(state="disabled")

    def _start(self):
        if self.embed_running: return
        et=find_exiftool()
        if not et: messagebox.showerror("ExifTool","Place exiftool.exe next to this app.",parent=self); return
        if not self.csv_rows: messagebox.showerror("No CSV","Load a CSV first.",parent=self); return
        if not self.folder_path_var.get(): messagebox.showerror("No folder","Select folder.",parent=self); return
        fc=self.col_file_var.get()
        if not fc or fc=="(skip)": messagebox.showerror("Column","Select filename column.",parent=self); return
        self.embed_running=True
        self._emb_btn.configure(state="disabled",text="⟳  Processing…")
        threading.Thread(target=self._embed_thread,args=(et,),daemon=True).start()

    def _embed_thread(self,et):
        folder=self.folder_path_var.get(); col_f=self.col_file_var.get()
        col_t=self.col_title_var.get(); col_k=self.col_kw_var.get(); col_d=self.col_desc_var.get()
        use_sub=self.subfolder_var.get(); use_ext=self.match_only_var.get()
        rm_prog=self.rm_prog_var.get(); rm_copy=self.rm_copy_var.get()
        total=len(self.csv_rows); ok=skipped=errors=0
        finder=find_recursive if use_sub else find_file
        self.after(0,lambda:self._log_msg(f"▶  Started — {total} rows"))
        for i,row in enumerate(self.csv_rows):
            fn=(row.get(col_f) or "").strip()
            if not fn: skipped+=1; continue
            fp=finder(folder,fn,use_ext)
            if not fp: skipped+=1; self.after(0,lambda f=fn:self._log_msg(f"⚠  Not found: {f}")); continue
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
            if rm_copy: cmd+=['-Rights=','-Copyright=','-CopyrightNotice=','-Creator=']
            cmd.append(fp)
            try:
                flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
                res=subprocess.run(cmd,capture_output=True,text=True,timeout=30,creationflags=flags)
                actual=os.path.basename(fp)
                if res.returncode==0: ok+=1; self.after(0,lambda fn=actual:self._log_msg(f"✓  {fn}"))
                else:
                    errors+=1; err=(res.stderr or res.stdout or "Unknown").strip()
                    self.after(0,lambda fn=actual,e=err:self._log_msg(f"✗  {fn} — {e}"))
            except Exception as ex:
                errors+=1; self.after(0,lambda fn=fn,e=str(ex):self._log_msg(f"✗  {fn} — {e}"))
        summary=f"{ok} embedded · {skipped} not found · {errors} errors"
        self.after(0,lambda:(self._log_msg(f"● Done — {summary}"),
            self._emb_btn.configure(state="normal",text="▶  Start Again"),
            setattr(self,'embed_running',False)))


class ImportProgressDialog(ctk.CTkToplevel):
    def __init__(self,parent,total):
        super().__init__(parent)
        self.title("Importing Images")
        self.configure(fg_color=BG2); self.resizable(False,False)
        self.grab_set(); self.protocol("WM_DELETE_WINDOW",lambda:None)
        self.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self,text="⟳  Importing Images…",font=ctk.CTkFont("Segoe UI",14,"bold"),
            text_color=TXT,fg_color=BG2).grid(row=0,column=0,padx=24,pady=(20,8))
        self._lbl=ctk.CTkLabel(self,text=f"0 / {total} files",font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2,fg_color=BG2)
        self._lbl.grid(row=1,column=0,padx=24,pady=(0,10))
        self._bar=ctk.CTkProgressBar(self,progress_color=GRN,fg_color=BG3,
            height=10,corner_radius=5,width=320)
        self._bar.grid(row=2,column=0,padx=24,pady=(0,20)); self._bar.set(0)
        self.update_idletasks()
        w,h=380,130
        x=parent.winfo_x()+(parent.winfo_width()-w)//2
        y=parent.winfo_y()+(parent.winfo_height()-h)//2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def update_progress(self,done,total):
        self._lbl.configure(text=f"{done} / {total} files")
        self._bar.set(done/total if total else 0)

    def finish(self):
        try: self.grab_release()
        except Exception: pass
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  RESULT CARD
# ══════════════════════════════════════════════════════════════════════
class MetaResultCard(ctk.CTkFrame):
    STATUS_STYLE = {
        "waiting": ("○  Waiting",  TXT3, BG4),
        "working": ("⟳  Working…", AMB_BTN, AMB_DIM),
        "done":    ("✓  Done",     GRN, GRN_DIM),
        "failed":  ("✗  Failed",   RED_BTN, RED_DIM),
    }

    def __init__(self,master,path,result,on_redo,mode="meta",request_thumb=None,**kw):
        super().__init__(master,fg_color=GLASS,corner_radius=10,
            border_width=1,border_color=GLASS_BDR,**kw)
        self.path=path; self.result=dict(result); self.mode=mode
        self._boxes={}; self._hdr_lbls={}
        self._build(on_redo)
        if request_thumb:
            request_thumb(self.path,self._tlbl)
        else:
            threading.Thread(target=self._load_thumb,daemon=True).start()

    def _build(self,on_redo):
        self.grid_columnconfigure(0,weight=1)

        # Top: thumbnail + filename row
        top=ctk.CTkFrame(self,fg_color="transparent",corner_radius=0)
        top.grid(row=0,column=0,sticky="ew",padx=8,pady=(8,4))
        top.grid_columnconfigure(1,weight=1)

        tf=ctk.CTkFrame(top,fg_color=BG3,corner_radius=6,width=56,height=56)
        tf.grid(row=0,column=0,rowspan=2,padx=(0,8)); tf.grid_propagate(False)
        self._tlbl=ctk.CTkLabel(tf,text="🖼",font=ctk.CTkFont("Segoe UI",16),
            fg_color=BG3,text_color=TXT3,width=54,height=54,corner_radius=6)
        self._tlbl.pack()

        fname=os.path.basename(self.path)
        ctk.CTkLabel(top,text=fname[:36]+"…" if len(fname)>36 else fname,
            font=ctk.CTkFont("Segoe UI",10),text_color=TXT2,
            fg_color="transparent",anchor="w"
        ).grid(row=0,column=1,sticky="w")

        botrow=ctk.CTkFrame(top,fg_color="transparent",corner_radius=0)
        botrow.grid(row=1,column=1,sticky="w")
        self._status_lbl=ctk.CTkLabel(botrow,text="",font=ctk.CTkFont("Segoe UI",8,"bold"),
            text_color=TXT3,fg_color=BG4,corner_radius=20,padx=6,pady=2)
        self._status_lbl.pack(side="left")
        self._model_lbl=ctk.CTkLabel(botrow,text="",font=ctk.CTkFont("Segoe UI",8),
            text_color=TXT3,fg_color="transparent",padx=4)
        self._model_lbl.pack(side="left")

        # Redo button top-right (kept larger — same size for both meta and prompt cards)
        self._redo_btn=ctk.CTkButton(top,text="↺",width=40,height=40,
            font=ctk.CTkFont("Segoe UI",16,"bold"),
            fg_color=BG4,hover_color=AMB_DIM,text_color=AMB_BTN,
            corner_radius=10,command=on_redo)
        self._redo_btn.grid(row=0,column=2,rowspan=2,padx=(4,0))

        if self.mode=="prompt":
            self._build_prompt_fields()
        else:
            self._build_meta_fields()

        self._refresh_status()

    def _build_prompt_fields(self):
        prompt_val=self.result.get("prompt","")
        hdr=ctk.CTkFrame(self,fg_color="transparent",corner_radius=0)
        hdr.grid(row=1,column=0,sticky="ew",padx=8,pady=(0,2))
        hdr.grid_columnconfigure(1,weight=1)
        lbl=ctk.CTkLabel(hdr,text="Prompt  (0 words)",
            font=ctk.CTkFont("Segoe UI",9,"bold"),text_color=TXT3,
            fg_color="transparent")
        lbl.grid(row=0,column=0,sticky="w")
        self._hdr_lbls["prompt"]=("Prompt",lbl,False)
        bf=ctk.CTkFrame(hdr,fg_color="transparent",corner_radius=0)
        bf.grid(row=0,column=2,sticky="e")
        ctk.CTkButton(bf,text="⧉",width=28,height=20,font=ctk.CTkFont("Segoe UI",9),
            fg_color=BG4,hover_color=BG3,text_color=TXT3,corner_radius=10,
            command=lambda:self._copy("prompt")).pack(side="left",padx=(0,2))
        ctk.CTkButton(bf,text="⎙",width=28,height=20,font=ctk.CTkFont("Segoe UI",9),
            fg_color=BG4,hover_color=BG3,text_color=TXT3,corner_radius=10,
            command=lambda:self._paste("prompt")).pack(side="left")
        box=ctk.CTkTextbox(self,height=90,font=ctk.CTkFont("Segoe UI",10),
            fg_color=BG3,text_color=CYAN,border_color=GLASS_BDR,border_width=1,
            corner_radius=6,wrap="word")
        box.grid(row=2,column=0,sticky="ew",padx=8,pady=(0,8))
        if prompt_val: box.insert("1.0",prompt_val)
        self._boxes["prompt"]=box
        self._recount("prompt")
        def _upd(e=None):
            self.result["prompt"]=box.get("1.0","end-1c")
            self._recount("prompt")
        box.bind("<KeyRelease>",_upd)

    def _build_meta_fields(self):
        title=self.result.get("title","")
        desc=self.result.get("desc","")
        kw=self.result.get("kw","")

        fields=[("title","Title",title,CYAN,36),("desc","Desc",desc,TXT2,44),
                ("kw","Keywords",kw,GRN,52)]
        for r,(key,label,val,color,h) in enumerate(fields,1):
            hdr=ctk.CTkFrame(self,fg_color="transparent",corner_radius=0)
            hdr.grid(row=r*2-1,column=0,sticky="ew",padx=8,pady=(4 if r==1 else 2,0))
            hdr.grid_columnconfigure(1,weight=1)
            lbl=ctk.CTkLabel(hdr,text=label,font=ctk.CTkFont("Segoe UI",9,"bold"),
                text_color=TXT3,fg_color="transparent")
            lbl.grid(row=0,column=0,sticky="w")
            self._hdr_lbls[key]=(label,lbl,key=="kw")
            bf=ctk.CTkFrame(hdr,fg_color="transparent",corner_radius=0)
            bf.grid(row=0,column=2,sticky="e")
            ctk.CTkButton(bf,text="⧉",width=28,height=20,font=ctk.CTkFont("Segoe UI",9),
                fg_color=BG4,hover_color=BG3,text_color=TXT3,corner_radius=10,
                command=lambda k=key:self._copy(k)).pack(side="left",padx=(0,2))
            ctk.CTkButton(bf,text="⎙",width=28,height=20,font=ctk.CTkFont("Segoe UI",9),
                fg_color=BG4,hover_color=BG3,text_color=TXT3,corner_radius=10,
                command=lambda k=key:self._paste(k)).pack(side="left")
            box=ctk.CTkTextbox(self,height=h,font=ctk.CTkFont("Segoe UI",10),
                fg_color=BG3,text_color=color,border_color=GLASS_BDR,border_width=1,
                corner_radius=6,wrap="word")
            box.grid(row=r*2,column=0,sticky="ew",padx=8,pady=(1,0))
            if val: box.insert("1.0",val)
            self._boxes[key]=box
            self._recount(key)
            def _upd(e=None,k=key,b=box):
                self.result[k]=b.get("1.0","end-1c")
                self._recount(k)
            box.bind("<KeyRelease>",_upd)

        # bottom padding
        ctk.CTkFrame(self,fg_color="transparent",height=6,corner_radius=0).grid(
            row=8,column=0)

    def _recount(self,key):
        if key not in self._hdr_lbls or key not in self._boxes: return
        base,lbl,is_kw=self._hdr_lbls[key]
        val=self._boxes[key].get("1.0","end-1c")
        if is_kw:
            n=len([x for x in val.split(",") if x.strip()])
            lbl.configure(text=f"{base}  ({n})")
        elif key=="prompt":
            n=len(val.split()) if val.strip() else 0
            lbl.configure(text=f"{base}  ({n} words)")
        else:
            lbl.configure(text=f"{base}  ({len(val)} chars)")

    def _refresh_status(self):
        status=self.result.get("status","waiting")
        text,fg,bg=self.STATUS_STYLE.get(status,self.STATUS_STYLE["waiting"])
        self._status_lbl.configure(text=text,text_color=fg,fg_color=bg)
        err=self.result.get("error","")
        model_used=self.result.get("model_used","")
        if status=="failed" and err:
            self._model_lbl.configure(text=f"⚠ {err[:60]}",text_color=RED_BTN)
        else:
            self._model_lbl.configure(text=model_used,text_color=TXT3)
        self.configure(border_color=GLASS_BDR if status!="failed" else RED_BTN)

    def apply_result(self,result):
        """Update this card IN PLACE with a new result dict — used instead of
        destroying/recreating cards on every generation, redo, or retry."""
        self.result=dict(result)
        if self.mode=="prompt":
            box=self._boxes.get("prompt")
            if box:
                box.delete("1.0","end")
                val=self.result.get("prompt","")
                if val: box.insert("1.0",val)
                self._recount("prompt")
        else:
            for key in ("title","desc","kw"):
                box=self._boxes.get(key)
                if box:
                    box.delete("1.0","end")
                    val=self.result.get(key,"")
                    if val: box.insert("1.0",val)
                    self._recount(key)
        self._refresh_status()

    def set_waiting(self):
        self.result={"status":"waiting"}
        self._refresh_status()

    def set_working(self):
        self.result={"status":"working"}
        self._refresh_status()

    def _copy(self,key):
        val=self._boxes[key].get("1.0","end-1c") if key in self._boxes else self.result.get(key,"")
        self.clipboard_clear(); self.clipboard_append(val)

    def _paste(self,key):
        try: clip=self.clipboard_get()
        except: return
        if key in self._boxes:
            self._boxes[key].delete("1.0","end")
            self._boxes[key].insert("1.0",clip)
            self.result[key]=clip

    def get_result(self):
        for k,b in self._boxes.items():
            self.result[k]=b.get("1.0","end-1c")
        return self.result

    def _load_thumb(self):
        img=make_thumb(self.path,(54,54))
        if img:
            self.after(0,lambda:(self._tlbl.configure(image=img,text=""),
                setattr(self._tlbl,"_image",img)))


# ══════════════════════════════════════════════════════════════════════
#  DnD MIXIN
# ══════════════════════════════════════════════════════════════════════
if DND_AVAILABLE:
    class DnDCTk(ctk.CTk,TkinterDnD.DnDWrapper):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw)
            self.TkdndVersion=TkinterDnD._require(self)
else:
    DnDCTk=ctk.CTk


# ══════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════
class App(DnDCTk):
    VERSION="v1.3"

    def __init__(self):
        super().__init__()
        self.title("Meta Zone"); self.configure(fg_color=BG1)
        self.resizable(True,True)
        self.prefs=load_prefs()

        self._all_paths=[]; self._results={}
        self._thumb_queue=queue.Queue()
        self._thumb_job_queue=queue.Queue()
        self._card_by_path={}
        self.ai_running=False; self.ai_stop_flag=False
        self._ai_paused=False; self.current_mode="meta"
        self._result_cards=[]; self._source_folder=""

        # AI settings
        self.ai_title_var    =StringVar(value=str(self.prefs.get("title_len",130)))
        self.ai_desc_var     =StringVar(value=str(self.prefs.get("desc_len",200)))
        self.ai_kw_var       =StringVar(value=str(self.prefs.get("kw_count",49)))
        self.ai_words_var    =StringVar(value=str(self.prefs.get("prompt_words",60)))
        self.ai_custom_var   =StringVar(value=self.prefs.get("custom_prompt",""))
        self.ai_single_kw_var=BooleanVar(value=self.prefs.get("single_keywords",False))
        self.ai_avoid_copy_var=BooleanVar(value=self.prefs.get("avoid_copyright",False))
        self.ai_concurrency_var=IntVar(value=self.prefs.get("concurrency",3))
        self.ai_platform_var =StringVar(value=self.prefs.get("platform","Adobe Stock"))
        self.ai_prefix_on_var=BooleanVar(value=False)
        self.ai_suffix_on_var=BooleanVar(value=False)
        self.ai_prefix_text_var=StringVar(value=self.prefs.get("prefix_text",""))
        self.ai_suffix_text_var=StringVar(value=self.prefs.get("suffix_text",""))
        self._style_vars={}
        for s in ["Silhouette","White Background","Transparent","Vector","Videos"]:
            self._style_vars[s]=BooleanVar(value=False)

        self._build_ui()
        self._center(1300,900)
        self.minsize(1000,700)
        self.after(200,self._check_et)
        self.after(500,self._online_loop)
        self.after(80,self._poll_thumb_queue)
        self._start_thumb_workers()

    def _start_thumb_workers(self,n=4):
        def worker():
            while True:
                path,size,widget=self._thumb_job_queue.get()
                img=make_thumb(path,size)
                if img is not None:
                    self._thumb_queue.put((widget,img))
        for _ in range(n):
            threading.Thread(target=worker,daemon=True).start()

    def _request_thumb(self,path,widget,size=(52,52)):
        """Queue a thumbnail decode job for the bounded worker pool instead
        of spawning a fresh OS thread per image — this is what previously
        caused thread-storm freezes/races when importing many images."""
        self._thumb_job_queue.put((path,size,widget))

    def _center(self,w,h):
        self.update_idletasks()
        sw=self.winfo_screenwidth(); sh=self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def ts(self): return datetime.datetime.now().strftime("%H:%M:%S")

    # ── Online ─────────────────────────────────────────────────────
    def _online_loop(self):
        def _c():
            online=check_online()
            self.after(0,lambda:self._set_online(online))
            self.after(8000,self._online_loop)
        threading.Thread(target=_c,daemon=True).start()

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

    # ── Thumb queue ────────────────────────────────────────────────
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

    # ══════════════════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════════════════
    def _build_ui(self):
        self.grid_columnconfigure(0,weight=1)
        self.grid_rowconfigure(0,weight=0)  # title bar
        self.grid_rowconfigure(1,weight=1)  # content
        self.grid_rowconfigure(2,weight=0)  # status bar
        self._build_titlebar()
        self._build_content()
        self._build_statusbar()

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

    def _build_content(self):
        content=ctk.CTkFrame(self,fg_color=BG1,corner_radius=0)
        content.grid(row=1,column=0,sticky="nsew")
        content.grid_columnconfigure(0,weight=0)  # sidebar
        content.grid_columnconfigure(1,weight=1)  # main
        content.grid_rowconfigure(0,weight=1)
        self._sb_frame=ctk.CTkFrame(content,fg_color=BG2,corner_radius=0,width=268)
        self._sb_frame.grid(row=0,column=0,sticky="nsew"); self._sb_frame.grid_propagate(False)
        self._main=ctk.CTkFrame(content,fg_color=BG1,corner_radius=0)
        self._main.grid(row=0,column=1,sticky="nsew")
        self._main.grid_columnconfigure(0,weight=1)
        self._main.grid_rowconfigure(1,weight=0)  # upload zone
        self._main.grid_rowconfigure(2,weight=0)  # progress bar
        self._main.grid_rowconfigure(3,weight=1)  # generated section
        self._build_sidebar()
        self._build_main()

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

        # API config
        ctk.CTkButton(inner,text="🔑  API Configuration",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,
            height=38,corner_radius=8,command=self._open_api_mgr
        ).pack(fill="x",padx=10,pady=(10,3))
        self._api_lbl=ctk.CTkLabel(inner,text="",font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT3,fg_color=BG2); self._api_lbl.pack(anchor="w",padx=12,pady=(0,4))
        self._refresh_api_lbl()

        # Concurrency slider
        self._div(inner)
        cf=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        cf.pack(fill="x",padx=10,pady=(0,6)); cf.grid_columnconfigure(0,weight=1)
        top=ctk.CTkFrame(cf,fg_color=BG2,corner_radius=0); top.pack(fill="x")
        top.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(top,text="Concurrent Generations",
            font=ctk.CTkFont("Segoe UI",11),text_color=TXT2,fg_color=BG2
        ).grid(row=0,column=0,sticky="w")
        self._conc_lbl=ctk.CTkLabel(top,text=f"{self.ai_concurrency_var.get()}x",
            font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=GRN,
            fg_color=BG3,corner_radius=20,padx=7,pady=2)
        self._conc_lbl.grid(row=0,column=1)
        ctk.CTkSlider(cf,from_=1,to=4,number_of_steps=3,variable=self.ai_concurrency_var,
            progress_color=GRN,fg_color=BG3,button_color=TXT,button_hover_color="#ddffdd",height=14,
            command=lambda v:(self._conc_lbl.configure(text=f"{int(v)}x"),self._save_settings())
        ).pack(fill="x",pady=(3,0))

        # Mode switch
        self._div(inner)
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

        # Metadata settings
        self._meta_sf=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        self._meta_sf.pack(fill="x")
        msf=self._meta_sf
        self._lbl(msf,"METADATA SETTINGS")

        # Platform dropdown (styled)
        plat_row=ctk.CTkFrame(msf,fg_color=BG2,corner_radius=0)
        plat_row.pack(fill="x",padx=10,pady=(0,6)); plat_row.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(plat_row,text="Platform",font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2,fg_color=BG2).grid(row=0,column=0,sticky="w")
        self._plat_combo=ctk.CTkComboBox(msf,variable=self.ai_platform_var,
            values=list(PLATFORM_RULES.keys()),state="readonly",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,text_color=GRN,border_color=GRN_DIM,border_width=2,
            button_color=GRN,button_hover_color=GRN_H,
            dropdown_fg_color=BG4,dropdown_text_color=TXT,dropdown_hover_color=GRN_DIM,
            dropdown_font=ctk.CTkFont("Segoe UI",11),
            corner_radius=8,height=36,command=self._on_platform_change)
        self._plat_combo.pack(fill="x",padx=10,pady=(0,8))
        self._plat_combo.bind("<MouseWheel>",self._on_platform_scroll)
        self._plat_combo.bind("<Button-4>",lambda e:self._on_platform_scroll(e,-1))
        self._plat_combo.bind("<Button-5>",lambda e:self._on_platform_scroll(e,1))

        self._title_sl=self._slider(msf,"Title Length",self.ai_title_var,10,200,int(self.ai_title_var.get()))
        self._desc_sl =self._slider(msf,"Description Length",self.ai_desc_var,20,500,int(self.ai_desc_var.get()))
        self._kw_sl   =self._slider(msf,"Keywords Count",self.ai_kw_var,5,49,int(self.ai_kw_var.get()))

        # Single keyword toggle (Avoid Copyright now lives inside Advanced Options)
        rf=ctk.CTkFrame(msf,fg_color=BG2,corner_radius=0)
        rf.pack(fill="x",padx=10,pady=(1,1)); rf.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(rf,text="Single Word Keywords",font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2,fg_color="transparent").grid(row=0,column=0,sticky="w")
        ctk.CTkSwitch(rf,text="",variable=self.ai_single_kw_var,
            progress_color=GRN,button_color=TXT,fg_color=GLASS_BDR,
            onvalue=True,offvalue=False,width=46,height=24,command=self._save_settings
        ).grid(row=0,column=1,sticky="e")

        # Anchor for stable mode switch
        self._sl_anchor=ctk.CTkFrame(inner,fg_color=BG2,height=0,corner_radius=0)
        self._sl_anchor.pack(fill="x")

        # Prompt sliders (hidden initially)
        self._prompt_sf=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        self._lbl(self._prompt_sf,"PROMPT SETTINGS")
        self._words_sl=self._slider(self._prompt_sf,"Max Prompt Words",
            self.ai_words_var,10,200,int(self.ai_words_var.get()))

        # Custom system prompt — always visible, sits above Advanced Options
        self._div(inner)
        ctk.CTkLabel(inner,text="CUSTOM SYSTEM PROMPT",font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3,fg_color=BG2).pack(anchor="w",padx=12,pady=(4,2))
        self._custom_box=ctk.CTkTextbox(inner,height=68,
            font=ctk.CTkFont("Segoe UI",11),fg_color=BG3,text_color=TXT,
            border_color=GLASS_BDR,border_width=1,corner_radius=8,wrap="word")
        self._custom_box.pack(fill="x",padx=10,pady=(0,4))
        if self.ai_custom_var.get(): self._custom_box.insert("1.0",self.ai_custom_var.get())
        self._custom_box.bind("<KeyRelease>",lambda e:self._save_custom())
        ctk.CTkButton(inner,text="↺  Reset to Default",height=28,
            font=ctk.CTkFont("Segoe UI",11),fg_color="transparent",
            hover_color=BG3,text_color=CYAN,corner_radius=6,anchor="w",
            command=self._reset_defaults).pack(anchor="w",padx=10,pady=(0,10))

        # Advanced options (collapsible) — last section
        self._div(inner)
        self._adv_visible=False
        self._adv_body=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        self._adv_btn=ctk.CTkButton(inner,text="▶  Advanced Options",height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,hover_color=BG4,text_color=TXT2,
            border_width=1,border_color=GLASS_BDR,corner_radius=8,anchor="w",
            command=self._toggle_advanced)
        self._adv_btn.pack(fill="x",padx=10,pady=(0,4))

        ab=self._adv_body; ab.grid_columnconfigure(0,weight=1)

        # Content themes inside advanced
        ctk.CTkLabel(ab,text="CONTENT THEMES",font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3,fg_color=BG2).pack(anchor="w",padx=12,pady=(8,2))
        for s in ["Silhouette","White Background","Transparent","Vector","Videos"]:
            rf2=ctk.CTkFrame(ab,fg_color=BG2,corner_radius=0)
            rf2.pack(fill="x",padx=10,pady=1); rf2.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(rf2,text=s,font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT2,fg_color=BG2).grid(row=0,column=0,sticky="w")
            ctk.CTkSwitch(rf2,text="",variable=self._style_vars[s],
                progress_color=GRN,button_color=TXT,fg_color=GLASS_BDR,
                onvalue=True,offvalue=False,width=46,height=24
            ).grid(row=0,column=1,sticky="e")

        ctk.CTkFrame(ab,fg_color=GLASS_BDR,height=1,corner_radius=0).pack(fill="x",padx=8,pady=6)

        # Prefix / Suffix — entry appears directly under its own toggle
        ctk.CTkLabel(ab,text="TITLE PREFIX / SUFFIX",font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3,fg_color=BG2).pack(anchor="w",padx=12,pady=(4,2))
        for label,on_var,text_var in [
            ("Add Prefix",self.ai_prefix_on_var,self.ai_prefix_text_var),
            ("Add Suffix",self.ai_suffix_on_var,self.ai_suffix_text_var),
        ]:
            grp=ctk.CTkFrame(ab,fg_color=BG2,corner_radius=0)
            grp.pack(fill="x",padx=10,pady=(2,0)); grp.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(grp,text=label,font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT2,fg_color=BG2).grid(row=0,column=0,sticky="w")
            entry=ctk.CTkEntry(grp,textvariable=text_var,
                placeholder_text=f"Type {label.split()[1].lower()} text here…",height=30,
                font=ctk.CTkFont("Segoe UI",11),fg_color=BG3,text_color=TXT,
                border_color=GLASS_BDR,corner_radius=8)
            def _tog(ov=on_var,e=entry,g=grp):
                if ov.get(): e.grid(row=1,column=0,columnspan=2,sticky="ew",pady=(3,4))
                else: e.grid_remove()
            sw=ctk.CTkSwitch(grp,text="",variable=on_var,
                progress_color=GRN,button_color=TXT,fg_color=GLASS_BDR,
                onvalue=True,offvalue=False,width=46,height=24,command=_tog)
            sw.grid(row=0,column=1,sticky="e")

        ctk.CTkFrame(ab,fg_color=GLASS_BDR,height=1,corner_radius=0).pack(fill="x",padx=8,pady=6)

        # Avoid Copyright — moved inside Advanced Options
        rf3=ctk.CTkFrame(ab,fg_color=BG3,corner_radius=8,border_width=1,border_color=GLASS_BDR)
        rf3.pack(fill="x",padx=10,pady=(0,10)); rf3.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(rf3,text="🚫  Avoid Copyright",font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2,fg_color="transparent",padx=8,pady=4
        ).grid(row=0,column=0,sticky="w",padx=(8,0),pady=(6,6))
        ctk.CTkSwitch(rf3,text="",variable=self.ai_avoid_copy_var,
            progress_color=GRN,button_color=TXT,fg_color=GLASS_BDR,
            onvalue=True,offvalue=False,width=46,height=24,command=self._save_settings
        ).grid(row=0,column=1,sticky="e",padx=(0,8),pady=(6,6))

    def _toggle_advanced(self):
        self._adv_visible=not self._adv_visible
        if self._adv_visible:
            self._adv_body.pack(fill="x",pady=(0,4))
            self._adv_btn.configure(text="▼  Advanced Options")
        else:
            self._adv_body.pack_forget()
            self._adv_btn.configure(text="▶  Advanced Options")

    def _set_mode(self,mode):
        self.current_mode=mode
        if mode=="meta":
            self._meta_mode_btn.configure(fg_color=GRN,text_color=ABSOLUTE_BG)
            self._prompt_mode_btn.configure(fg_color="transparent",text_color=TXT3)
            self._prompt_sf.pack_forget()
            self._meta_sf.pack(fill="x",before=self._sl_anchor)
        else:
            self._prompt_mode_btn.configure(fg_color=GRN,text_color=ABSOLUTE_BG)
            self._meta_mode_btn.configure(fg_color="transparent",text_color=TXT3)
            self._meta_sf.pack_forget()
            self._prompt_sf.pack(fill="x",before=self._sl_anchor)
        self._clear_results()
        for p in self._all_paths:
            self._results[p]={"status":"waiting"}
            self._make_blank_card(p)

    def _on_platform_scroll(self,event,direction=None):
        plats=list(PLATFORM_RULES.keys())
        cur=self.ai_platform_var.get()
        idx=plats.index(cur) if cur in plats else 0
        d=direction if direction is not None else (-1 if getattr(event,"delta",0)>0 else 1)
        idx=(idx+d)%len(plats)
        new_val=plats[idx]
        self._plat_combo.set(new_val)
        self._on_platform_change(new_val)
        return "break"

    def _on_platform_change(self,val):
        rules=PLATFORM_RULES.get(val,{})
        kw_val=min(rules.get("kw",49),49)
        for var,sl,v in [(self.ai_title_var,self._title_sl,rules.get("title",130)),
                         (self.ai_desc_var,self._desc_sl,rules.get("desc",200)),
                         (self.ai_kw_var,self._kw_sl,kw_val)]:
            var.set(str(v)); sl.set(v)
            lbl=getattr(sl,"_value_label",None)
            if lbl: lbl.configure(text=str(v))
        self.ai_platform_var.set(val); self._save_settings()

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
            "platform":self.ai_platform_var.get(),
            "title_len":int(self.ai_title_var.get() or 130),
            "desc_len":int(self.ai_desc_var.get() or 200),
            "kw_count":min(int(self.ai_kw_var.get() or 49),49),
            "prompt_words":int(self.ai_words_var.get() or 60),
            "single_keywords":self.ai_single_kw_var.get(),
            "avoid_copyright":self.ai_avoid_copy_var.get(),
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

        # TOP action bar (no tab buttons — they're gone)
        topbar=ctk.CTkFrame(main,fg_color=BG2,corner_radius=0,height=50)
        topbar.grid(row=0,column=0,sticky="ew"); topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0,weight=1)

        left_f=ctk.CTkFrame(topbar,fg_color=BG2,corner_radius=0)
        left_f.grid(row=0,column=0,sticky="w",padx=8,pady=8)
        ctk.CTkLabel(left_f,text="✨  Metadata AI",font=ctk.CTkFont("Segoe UI",14,"bold"),
            text_color=TXT,fg_color=BG2).pack(side="left",padx=(0,8))

        btn_f=ctk.CTkFrame(topbar,fg_color=BG2,corner_radius=0)
        btn_f.grid(row=0,column=1,padx=8,pady=8,sticky="e")

        ctk.CTkButton(btn_f,text="🗑  Clear All",width=96,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=RED_DIM,hover_color=RED_BTN_H,text_color=RED_BTN,
            border_width=1,border_color=RED_BTN,corner_radius=8,
            command=lambda:self._clear_all(confirm=True)).pack(side="left",padx=(0,5))

        # Pause + Stop (hidden until generation starts)
        self._pause_btn=ctk.CTkButton(btn_f,text="⏸  Pause",width=86,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=AMB_DIM,hover_color=AMB_BTN_H,text_color=AMB_BTN,
            border_width=1,border_color=AMB_BTN,corner_radius=8,command=self._pause_ai)
        self._stop_btn=ctk.CTkButton(btn_f,text="■  Stop",width=82,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=RED_DIM,hover_color=RED_BTN_H,text_color=RED_BTN,
            border_width=1,border_color=RED_BTN,corner_radius=8,command=self._stop_ai_now)
        self._retry_btn=ctk.CTkButton(btn_f,text="↺  Retry Failed",width=120,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=AMB_DIM,hover_color=AMB_BTN_H,text_color=AMB_BTN,
            border_width=1,border_color=AMB_BTN,corner_radius=8,command=self._retry_failed)

        self._gen_btn=ctk.CTkButton(btn_f,text="✨  Generate (0)",width=165,height=32,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=GRN,hover_color=GRN_H,text_color=ABSOLUTE_BG,corner_radius=8,
            command=self.start_generate)
        self._gen_btn.pack(side="left",padx=(0,5))

        self._export_btn=ctk.CTkButton(btn_f,text="⬇  Export CSV",width=128,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,hover_color=BG4,text_color=TXT2,
            border_width=1,border_color=GLASS_BDR,corner_radius=8,
            command=self._export_csv)
        self._export_btn.pack(side="left",padx=(0,5))

        self._embed_btn=ctk.CTkButton(btn_f,text="📋  Embed",width=90,height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,hover_color=BG4,text_color=TXT2,
            border_width=1,border_color=GLASS_BDR,corner_radius=8,
            command=self._open_embed)
        self._embed_btn.pack(side="left")

        # UPLOAD BAR — slim text-only strip (thumbnails now live inside each
        # card, so this no longer needs to reserve grid space for them). The
        # WHOLE WINDOW is a drop zone too — see _register_drop_targets below.
        ws=ctk.CTkFrame(main,fg_color=GLASS,corner_radius=12,
            border_width=1,border_color=GLASS_BDR,height=64)
        ws.grid(row=1,column=0,sticky="ew",padx=8,pady=(6,4))
        ws.grid_columnconfigure(0,weight=1); ws.grid_propagate(False)
        self._ws_frame=ws

        self._ws_empty=ctk.CTkLabel(ws,
            text="🖼️  Drag & drop images/video anywhere in this window — or click here to browse\nJPG · PNG · GIF · WEBP · TIFF · SVG · EPS · MP4 · MOV",
            font=ctk.CTkFont("Segoe UI",12),
            text_color=TXT2,fg_color=GLASS,justify="center",anchor="center")
        self._ws_empty.place(relx=0.5,rely=0.5,anchor="center")

        for w in (ws,self._ws_empty):
            w.bind("<Button-1>",lambda e:self._browse_images())

        self._register_drop_targets([ws,self._ws_empty])

        # Progress bar
        prog=ctk.CTkFrame(main,fg_color=BG1,corner_radius=0,height=28)
        prog.grid(row=2,column=0,sticky="ew"); prog.grid_propagate(False)
        prog.grid_columnconfigure(1,weight=1)
        self._prog_lbl=ctk.CTkLabel(prog,text="● System Ready.",
            font=ctk.CTkFont("Segoe UI",10),text_color=TXT3,fg_color=BG1)
        self._prog_lbl.grid(row=0,column=0,padx=(10,8),pady=4)
        self._prog_bar=ctk.CTkProgressBar(prog,progress_color=GRN,fg_color=BG3,height=6,corner_radius=3)
        self._prog_bar.grid(row=0,column=1,sticky="ew",pady=10,padx=(0,8)); self._prog_bar.set(0)
        self._prog_pct=ctk.CTkLabel(prog,text="",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=GRN,fg_color=BG1,width=36)
        self._prog_pct.grid(row=0,column=2,padx=(0,8))

        # Generated Metadata section — 2x grid, 4 cards visible
        gen=ctk.CTkFrame(main,fg_color=GLASS,corner_radius=12,
            border_width=1,border_color=GLASS_BDR)
        gen.grid(row=3,column=0,sticky="nsew",padx=8,pady=(0,8))
        gen.grid_columnconfigure(0,weight=1); gen.grid_rowconfigure(1,weight=1)

        gen_hdr=ctk.CTkFrame(gen,fg_color="transparent",corner_radius=0,height=38)
        gen_hdr.grid(row=0,column=0,sticky="ew",padx=12,pady=(8,0))
        gen_hdr.grid_propagate(False); gen_hdr.grid_columnconfigure(0,weight=1)
        self._gen_count_lbl=ctk.CTkLabel(gen_hdr,text="Generated Metadata (0)",
            font=ctk.CTkFont("Segoe UI",12,"bold"),text_color=TXT,fg_color="transparent")
        self._gen_count_lbl.grid(row=0,column=0,sticky="w")

        self._gen_scroll=ctk.CTkScrollableFrame(gen,fg_color="transparent",
            scrollbar_button_color=BG3,scrollbar_button_hover_color=BG4,corner_radius=0)
        self._gen_scroll.grid(row=1,column=0,sticky="nsew",padx=6,pady=(4,6))
        self._gen_scroll.grid_columnconfigure(0,weight=1)
        self._gen_scroll.grid_columnconfigure(1,weight=1)

        self._gen_empty_lbl=ctk.CTkLabel(self._gen_scroll,
            text="Results will appear here after generation.",
            font=ctk.CTkFont("Segoe UI",12),text_color=TXT3,fg_color="transparent")
        self._gen_empty_lbl.grid(row=0,column=0,columnspan=2,pady=40)

        # Cover the rest of the window so dropping anywhere (not just the
        # upload bar) works — tkdnd only fires on widgets that registered.
        self._register_drop_targets([main,topbar,gen,gen_hdr,self._gen_scroll,
                                      self._gen_empty_lbl,self._sb])

    def _open_embed(self):
        # Pass the last generated CSV path (and the image folder just used)
        # if available — this is exactly what makes "generate then embed"
        # a one-click flow instead of re-browsing for everything.
        EmbedWindow(self, csv_path=getattr(self,"_last_csv_path",None),
                    folder_path=self._source_folder or None)

    # ── DnD ────────────────────────────────────────────────────────
    def _register_drop_targets(self,widgets):
        """Register every widget passed in (plus the whole window) as a
        drag-and-drop target, so dropping files ANYWHERE in the app works —
        not just inside the small upload bar."""
        if not DND_AVAILABLE: return
        for w in list(widgets)+[self]:
            try:
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<DropEnter>>",self._on_drag_enter)
                w.dnd_bind("<<DropLeave>>",self._on_drag_leave)
                w.dnd_bind("<<Drop>>",self._on_drop)
            except Exception:
                pass

    def _on_drag_enter(self,event):
        self._ws_frame.configure(border_color=GRN,fg_color=GRN_DIM)
        self._ws_empty.configure(fg_color=GRN_DIM,text_color=GRN)
        return event.action

    def _on_drag_leave(self,event):
        self._ws_frame.configure(border_color=GLASS_BDR,fg_color=GLASS)
        self._ws_empty.configure(fg_color=GLASS,text_color=TXT2)
        return event.action

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

    # ── Image import ───────────────────────────────────────────────
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
        if not self._source_folder: self._source_folder=os.path.dirname(new[0])
        if len(new)>15:
            self._import_with_progress(new)
        else:
            for p in new: self._make_blank_card(p)
            self._gen_btn.configure(text=f"✨  Generate ({len(self._all_paths)})")
            self._update_progress()

    def _import_with_progress(self,paths):
        """Create blank cards in small UI batches (so the event loop is
        never blocked for more than a few widgets at a time), with a visible
        progress dialog — thumbnails are decoded separately by the bounded
        worker pool, never on the main thread."""
        dlg=ImportProgressDialog(self,len(paths))
        total=len(paths); state={"i":0}

        def add_batch():
            BATCH=8
            end=min(state["i"]+BATCH,total)
            for idx in range(state["i"],end):
                self._make_blank_card(paths[idx])
            state["i"]=end
            dlg.update_progress(end,total)
            if end<total:
                self.after(1,add_batch)
            else:
                self._gen_btn.configure(text=f"✨  Generate ({len(self._all_paths)})")
                self._update_progress()
                dlg.finish()
        self.after(10,add_batch)

    def _make_blank_card(self,path):
        """Add path to the queue and create its (empty) card right away —
        metadata is filled in only once Generate is pressed."""
        self._all_paths.append(path)
        self._results[path]={"status":"waiting"}
        if self._gen_empty_lbl.winfo_viewable():
            self._gen_empty_lbl.grid_remove()
        idx=len(self._result_cards)
        r,c=idx//2,idx%2
        card=MetaResultCard(self._gen_scroll,path,self._results[path],
            on_redo=lambda p=path:self._redo_single(p),mode=self.current_mode,
            request_thumb=self._request_thumb)
        card.grid(row=r,column=c,sticky="ew",
            padx=(4,2) if c==0 else (2,4),pady=(0,6))
        self._result_cards.append(card)
        self._card_by_path[path]=card
        return card

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
        self._prog_bar.set(pct); self._prog_pct.configure(text=f"{int(pct*100)}%")
        self.p_ok.configure(text=f"✓  {d} done")
        self.p_err.configure(text=f"✗  {failed} failed")
        self.p_pend.configure(text=f"○  {t-d-failed} pending")
        self._gen_count_lbl.configure(text=f"Generated Metadata ({d})")

    def _clear_all(self,confirm=True):
        if self.ai_running: messagebox.showwarning("Busy","Stop generation first."); return
        if confirm and self._all_paths:
            if not messagebox.askyesno("Clear","Remove all files and results?"): return
        self._all_paths.clear(); self._results.clear(); self._source_folder=""
        self._clear_results()
        self._gen_btn.configure(text="✨  Generate (0)")
        self._update_progress()

    def _clear_results(self):
        for c in self._result_cards:
            try: c.destroy()
            except: pass
        self._result_cards=[]; self._card_by_path={}
        self._gen_count_lbl.configure(text="Generated Metadata (0)")
        self._gen_empty_lbl.grid(row=0,column=0,columnspan=2,pady=40)

    def _update_card(self,path):
        """Refresh (or, as a defensive fallback, create) the card for path
        from self._results — this is how generation results reach the UI
        now, instead of destroying/recreating cards every time."""
        card=self._card_by_path.get(path)
        if card is None:
            card=self._make_blank_card(path)
        card.apply_result(self._results.get(path,{}))

    # ── Pause / Stop ───────────────────────────────────────────────
    def _pause_ai(self):
        if not self.ai_running: return
        self._ai_paused=not self._ai_paused
        if self._ai_paused:
            self._pause_btn.configure(text="▶  Resume",fg_color=GRN_DIM,text_color=GRN)
            self.set_status("⏸  Paused",AMB_BTN)
        else:
            self._pause_btn.configure(text="⏸  Pause",fg_color=AMB_DIM,text_color=AMB_BTN)
            self.set_status("▶  Resuming…",GRN)

    def _stop_ai_now(self):
        self.ai_stop_flag=True; self._ai_paused=False
        self.set_status("■  Stopped",RED_BTN)

    def _retry_failed(self):
        if self.ai_running: return
        failed=[p for p in self._all_paths if self._results.get(p,{}).get("status")=="failed"]
        if not failed: return
        for p in failed:
            self._results[p]={"status":"waiting"}
            if p in self._card_by_path: self._card_by_path[p].set_waiting()
        try: self._retry_btn.pack_forget()
        except: pass
        self.start_generate()

    # ── Generate ───────────────────────────────────────────────────
    def start_generate(self):
        if self.ai_running: messagebox.showwarning("Busy","Already generating."); return
        if not self._all_paths: messagebox.showerror("No Images","Add images first."); return
        if not get_active_keys(self.prefs):
            messagebox.showerror("No API Keys","Open 'API Configuration'."); return
        self.ai_running=True; self.ai_stop_flag=False; self._ai_paused=False
        self._gen_btn.configure(state="disabled",text="⟳  Generating…")
        self._pause_btn.pack(side="left",padx=(0,4),before=self._gen_btn)
        self._stop_btn.pack(side="left",padx=(0,5),before=self._gen_btn)
        try: self._retry_btn.pack_forget()
        except: pass
        targets=[p for p in self._all_paths
                 if self._results.get(p,{}).get("status") in ("waiting","failed")]
        for p in targets: self._results[p]={"status":"waiting"}
        threading.Thread(target=self._gen_thread,args=(targets,),daemon=True).start()

    def _gen_thread(self,targets):
        mode=self.current_mode
        custom=self.ai_custom_var.get()
        single_kw=self.ai_single_kw_var.get()
        avoid_copyright=self.ai_avoid_copy_var.get()
        themes=", ".join(s for s,v in self._style_vars.items() if v.get())
        # Only apply prefix/suffix if their toggles are ON
        prefix=self.ai_prefix_text_var.get().strip() if self.ai_prefix_on_var.get() else ""
        suffix_title=self.ai_suffix_text_var.get().strip() if self.ai_suffix_on_var.get() else ""
        concurrency=max(1,min(4,int(self.ai_concurrency_var.get())))

        if mode=="meta":
            tc=int(self.ai_title_var.get() or 130)
            dc=int(self.ai_desc_var.get() or 200)
            kn=min(int(self.ai_kw_var.get() or 49),49)
            prompt=build_meta_prompt(tc,dc,kn,custom,single_kw,themes,prefix,suffix_title,avoid_copyright)
        else:
            mw=int(self.ai_words_var.get() or 60)
            prompt=build_prompt_prompt(mw,list(self._style_vars.keys()),custom)

        total=len(targets); done_count=0
        worker_sem=threading.Semaphore(concurrency)
        lock=threading.Lock()
        remaining=[total]; finished=threading.Event()

        def process_one(path,i):
            nonlocal done_count
            try:
                while getattr(self,"_ai_paused",False) and not self.ai_stop_flag:
                    import time; time.sleep(0.3)
                if self.ai_stop_flag: return
                fname=os.path.basename(path)
                self._results[path]={"status":"working"}
                self.after(0,lambda p=path:self._update_card(p))
                self.after(0,lambda f=fname,n=i+1,t=total:
                    self._update_progress(done=done_count,total=t,
                        msg=f"⟳  [{n}/{t}] {f}"))
                try:
                    ext=os.path.splitext(path)[1].lower()
                    if ext in VECTOR_EXTS or ext in VIDEO_EXTS:
                        raise ValueError("Vector/video: convert to JPG first")
                    raw,provider,model_id,key_idx=call_with_failover(path,prompt,self.prefs,
                        status_cb=lambda msg:self.after(0,lambda m=msg:self.set_status(f"⟳  {m}",GRN)))
                    model_used=f"⚙ {provider} · {model_label(provider,model_id)}" + \
                               (f" ({key_idx})" if key_idx else "")
                    if mode=="meta":
                        title,desc,kw=parse_meta(raw)
                        # Apply prefix ONCE — check it's not already there
                        if prefix:
                            if not title.lower().startswith(prefix.lower()):
                                title=prefix+" "+title
                        # Apply suffix ONCE — check it's not already there
                        if suffix_title:
                            if not title.lower().endswith(suffix_title.lower()):
                                title=title+" "+suffix_title
                        # Trim to char limit
                        if len(title)>tc: title=title[:tc].rsplit(" ",1)[0].strip()
                        if single_kw: kw=enforce_single_keywords(kw)
                        if avoid_copyright: kw=_strip_copyright_keywords(kw)
                        self._results[path]={
                            "status":"done","title":title,"desc":desc,
                            "kw":kw,"model_used":model_used}
                    else:
                        self._results[path]={"status":"done",
                            "prompt":raw.strip(),"model_used":model_used}
                    with lock: done_count+=1
                    self.after(0,lambda p=path:self._update_card(p))
                except Exception as e:
                    self._results[path]={"status":"failed","error":str(e)[:120]}
                    self.after(0,lambda p=path:self._update_card(p))
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
            threading.Thread(target=process_one,args=(path,i),daemon=True).start()

        finished.wait(timeout=3600)
        self.after(0,self._gen_done)

    def _gen_done(self):
        self.ai_running=False; self._ai_paused=False
        total=len(self._all_paths)
        done=sum(1 for r in self._results.values() if r.get("status")=="done")
        failed=sum(1 for r in self._results.values() if r.get("status")=="failed")
        self._gen_btn.configure(state="normal",text=f"✨  Generate ({total})")
        try: self._pause_btn.pack_forget()
        except: pass
        try: self._stop_btn.pack_forget()
        except: pass
        self._pause_btn.configure(text="⏸  Pause",fg_color=AMB_DIM,text_color=AMB_BTN)
        if failed>0:
            self._retry_btn.pack(side="left",padx=(0,5),before=self._gen_btn)
        self.set_status(f"● Done — {done} generated · {failed} failed",
                        GRN if failed==0 else AMB_BTN)
        self._update_progress(done=done,total=total)
        # Auto-save CSV
        if done>0: self._auto_save_csv()

    def _auto_save_csv(self):
        """Save CSV silently to the source folder with #foldername naming."""
        try:
            done_paths=[p for p in self._all_paths if self._results.get(p,{}).get("status")=="done"]
            if not done_paths: return
            folder_name=os.path.basename(self._source_folder) if self._source_folder else "export"
            out_path=os.path.join(self._source_folder,f"#{folder_name}.csv")
            mode=self.current_mode
            fields=["Filename","Title","Description","Keywords"] if mode=="meta" else ["Filename","Prompt"]
            def row_for(p):
                r=self._results[p]; fn=os.path.basename(p)
                if mode=="meta":
                    return {"Filename":fn,"Title":r.get("title",""),
                            "Description":r.get("desc",""),"Keywords":r.get("kw","")}
                return {"Filename":fn,"Prompt":r.get("prompt","")}
            with open(out_path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
                w.writerows(row_for(p) for p in done_paths)
            self._last_csv_path=out_path
            self.set_status(f"✓  Auto-saved → #{folder_name}.csv",GRN)
        except Exception: pass

    def _redo_single(self,path):
        if self.ai_running: return
        self._results[path]={"status":"waiting"}
        if path in self._card_by_path: self._card_by_path[path].set_waiting()
        self.ai_running=True; self.ai_stop_flag=False; self._ai_paused=False
        self._gen_btn.configure(state="disabled")
        self._pause_btn.pack(side="left",padx=(0,4),before=self._gen_btn)
        self._stop_btn.pack(side="left",padx=(0,5),before=self._gen_btn)
        threading.Thread(target=self._gen_thread,args=([path],),daemon=True).start()

    def _export_csv(self):
        done=[p for p in self._all_paths if self._results.get(p,{}).get("status")=="done"]
        if not done: messagebox.showinfo("No Results","No generated results yet."); return
        folder_name=os.path.basename(self._source_folder) if self._source_folder else "export"
        path=filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")],initialfile=f"#{folder_name}.csv")
        if not path: return
        try:
            mode=self.current_mode
            fields=["Filename","Title","Description","Keywords"] if mode=="meta" else ["Filename","Prompt"]
            def row_for(p):
                fn=os.path.basename(p)
                # Read latest from card boxes if available (user may have hand-edited them)
                r=None
                for card in self._result_cards:
                    if card.path==p: r=card.get_result(); break
                if r is None: r=self._results.get(p,{})
                if mode=="meta":
                    return {"Filename":fn,"Title":r.get("title",""),
                            "Description":r.get("desc",""),"Keywords":r.get("kw","")}
                return {"Filename":fn,"Prompt":r.get("prompt","")}
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
                w.writerows(row_for(p) for p in done)
            self._last_csv_path=path
            self.set_status(f"✓  CSV saved — {len(done)} rows",GRN)
            messagebox.showinfo("Saved",f"CSV saved:\n{path}")
        except Exception as e: messagebox.showerror("Error",str(e))

    # ── Status bar ─────────────────────────────────────────────────
    def _build_statusbar(self):
        sb=ctk.CTkFrame(self,fg_color=BG2,corner_radius=0,height=40)
        sb.grid(row=2,column=0,sticky="ew"); sb.grid_propagate(False)
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
