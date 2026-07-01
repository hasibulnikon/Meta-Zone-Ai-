import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, BooleanVar
import csv, subprocess, os, sys, threading, datetime, json, base64, socket, queue
import urllib.request, urllib.error
from PIL import Image

# Drag-and-drop support — tkinterdnd2 must wrap the root window itself.
# Auto-install if missing so the user never has to run pip manually.
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    import subprocess as _sp
    try:
        _sp.check_call([sys.executable, "-m", "pip", "install", "tkinterdnd2",
                        "--quiet", "--break-system-packages"], timeout=60)
        from tkinterdnd2 import TkinterDnD, DND_FILES
        DND_AVAILABLE = True
    except Exception:
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

def build_meta_prompt(title_c,desc_c,kw_n,content_type,custom_prompt="",single_kw=False):
    suffix=CONTENT_SUFFIXES.get(content_type,"")
    directives=[]
    if suffix:
        directives.append(f'You MUST naturally work this phrase into the description or title: "{suffix}".')
    if single_kw:
        # Keep instruction lightweight — enforcement happens in post-processing
        directives.append(f"Keywords must be single words only (no spaces). Generate {kw_n} single-word tags.")
    if custom_prompt.strip():
        directives.append(
            f"MANDATORY COMMAND — this overrides your default judgement and MUST be reflected in the "
            f"title, description, AND keywords: \"{custom_prompt.strip()}\". "
            f"Re-read your draft before answering and rewrite anything that does not follow this command."
        )
    directive_block = ("\n\nMANDATORY INSTRUCTIONS (do not skip any of these):\n" +
        "\n".join(f"- {d}" for d in directives)) if directives else ""

    return (
        f"You are a professional stock image metadata writer.\n"
        f"Analyze this image and respond ONLY in this exact 3-line format:\n\n"
        f"TITLE: <descriptive title>\n"
        f"DESCRIPTION: <detailed scene description>\n"
        f"KEYWORDS: <comma-separated keywords, most specific first>\n\n"
        f"Hard limits — you MUST satisfy ALL of these exactly, not approximately:\n"
        f"- TITLE: between {max(title_c-15,10)} and {title_c} characters. "
        f"Add more descriptive detail if your draft is shorter than {title_c-15} chars.\n"
        f"- DESCRIPTION: between {max(desc_c-25,15)} and {desc_c} characters. "
        f"Add scene detail, mood, and use-case context to reach this length.\n"
        f"- KEYWORDS: exactly {kw_n} keywords, no more, no fewer. No duplicates, no brand names.\n"
        f"- Cover in the keywords: subject, action, setting, mood, color, style, demographic, use-case.\n"
        f"- Output ONLY the 3 lines above. No preamble, no markdown, no explanation.{directive_block}"
    )

def enforce_single_keywords(kw_string):
    """Post-process keywords to strip multi-word phrases when single-word mode is on.
    Splits each comma-separated keyword by spaces and takes only the first word,
    deduplicates, preserves comma-separated format."""
    raw = [k.strip() for k in kw_string.split(",") if k.strip()]
    seen = set()
    result = []
    for kw in raw:
        # Take first word of any multi-word keyword
        single = kw.split()[0] if kw.split() else kw
        single_lower = single.lower()
        if single_lower not in seen:
            seen.add(single_lower)
            result.append(single)
    return ", ".join(result)


def build_prompt_prompt(max_words,styles,content_type,custom_prompt=""):
    suffix=CONTENT_SUFFIXES.get(content_type,"")
    style_str=", ".join(styles) if styles else "realistic photography"
    directives=[]
    if suffix:
        directives.append(f'End the prompt with: "{suffix}".')
    if custom_prompt.strip():
        directives.append(
            f"MANDATORY COMMAND — this overrides your default judgement: \"{custom_prompt.strip()}\". "
            f"Re-read your draft and rewrite anything not following this command."
        )
    directive_block = ("\n\nMANDATORY INSTRUCTIONS:\n" + "\n".join(f"- {d}" for d in directives)) if directives else ""
    return (
        f"You are an expert AI image generation prompt writer.\n"
        f"Analyze this image and write a detailed image generation prompt.\n"
        f"Output ONLY the prompt text — no labels, no explanation, no formatting.\n\n"
        f"Rules:\n"
        f"- Maximum {max_words} words.\n"
        f"- Style: {style_str}.\n"
        f"- Include: subject details, lighting, color palette, composition, mood, camera angle.\n"
        f"- Write as a flowing, comma-separated description (professional prompt style).{directive_block}"
    )


def parse_meta(text):
    title=desc=kw=""
    lines=text.strip().splitlines(); i=0
    while i<len(lines):
        line=lines[i].strip(); upper=line.upper()
        if upper.startswith("TITLE:"): title=line[6:].strip()
        elif upper.startswith("DESCRIPTION:"):
            desc=line[12:].strip(); i+=1
            while i<len(lines):
                nxt=lines[i].strip()
                if nxt.upper().startswith("KEYWORDS:") or nxt.upper().startswith("TITLE:"): i-=1; break
                desc+=" "+nxt; i+=1
            desc=desc.strip()
        elif upper.startswith("KEYWORDS:"):
            kw=line[9:].strip(); i+=1
            while i<len(lines):
                nxt=lines[i].strip()
                if nxt.upper().startswith("TITLE:") or nxt.upper().startswith("DESCRIPTION:"): i-=1; break
                kw+=" "+nxt; i+=1
            kw=kw.strip()
        i+=1
    return title,desc,kw

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

def check_online():
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════
#  API KEY MANAGER
# ══════════════════════════════════════════════════════════════════════
class APIManagerWindow(ctk.CTkToplevel):
    def __init__(self,parent,prefs,on_close=None):
        super().__init__(parent)
        self.title("API Configuration"); self.configure(fg_color=META_BG2)
        self.resizable(False,False); self.grab_set()
        self.prefs=prefs; self.on_close=on_close
        self._cur=list(AI_PROVIDERS.keys())[0]
        self._validate_cache = {}   # key -> (ok,msg)
        self._build(); self._center(840,600)
        self.protocol("WM_DELETE_WINDOW",self._done)

    def _center(self,w,h):
        self.update_idletasks()
        x=self.master.winfo_x()+(self.master.winfo_width()-w)//2
        y=self.master.winfo_y()+(self.master.winfo_height()-h)//2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(2,weight=1)
        hdr=ctk.CTkFrame(self,fg_color=META_BG,corner_radius=0,height=50)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(hdr,text="API Configuration",
            font=ctk.CTkFont("Segoe UI",15,"bold"),text_color=TXT,fg_color=META_BG
        ).grid(row=0,column=0,sticky="w",padx=16,pady=12)
        ctk.CTkButton(hdr,text="✕",width=32,height=32,fg_color="transparent",
            hover_color=RED2,text_color=TXT3,corner_radius=6,
            command=self._done).grid(row=0,column=1,padx=10)
        tab_bar=ctk.CTkFrame(self,fg_color=META_BG,corner_radius=0,height=50)
        tab_bar.grid(row=1,column=0,sticky="ew"); tab_bar.grid_propagate(False)
        self._tab_btns={}
        for p in AI_PROVIDERS:
            btn=ctk.CTkButton(tab_bar,text=self._tab_text(p),width=108,height=34,
                font=ctk.CTkFont("Segoe UI",12,"bold"),
                fg_color=META_ACC if p==self._cur else "transparent",
                hover_color=META_ACC2,
                text_color=TXT if p==self._cur else TXT2,corner_radius=8,
                command=lambda pv=p:self._switch(pv))
            btn.pack(side="left",padx=(8 if p==list(AI_PROVIDERS.keys())[0] else 2,0),pady=8)
            self._tab_btns[p]=btn
        body=ctk.CTkFrame(self,fg_color=META_BG2,corner_radius=0)
        body.grid(row=2,column=0,sticky="nsew")
        body.grid_columnconfigure(0,weight=0); body.grid_columnconfigure(1,weight=1)
        body.grid_rowconfigure(0,weight=1)
        self._lp=ctk.CTkFrame(body,fg_color=META_BG3,corner_radius=0,width=400)
        self._lp.grid(row=0,column=0,sticky="nsew"); self._lp.grid_propagate(False)
        self._rp=ctk.CTkFrame(body,fg_color=META_BG2,corner_radius=0,width=300)
        self._rp.grid(row=0,column=1,sticky="nsew",padx=(1,0))
        self._rp.grid_propagate(False)
        self._rp.grid_columnconfigure(0,weight=1); self._rp.grid_rowconfigure(1,weight=1)
        ftr=ctk.CTkFrame(self,fg_color=META_BG,corner_radius=0,height=50)
        ftr.grid(row=3,column=0,sticky="ew"); ftr.grid_propagate(False)
        ctk.CTkButton(ftr,text="Done",width=96,height=34,
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=META_ACC,hover_color=META_ACC2,text_color="white",corner_radius=8,
            command=self._done).pack(side="right",padx=14,pady=8)
        self._render()

    def _tab_text(self,p):
        n=sum(1 for k in self.prefs.get("ai_keys",{}).get(p,[]) if k.get("active"))
        return f"{p}" + (f"  ●{n}" if n else "")

    def _switch(self,p):
        self._cur=p
        for pv,btn in self._tab_btns.items():
            btn.configure(text=self._tab_text(pv),
                fg_color=META_ACC if pv==p else "transparent",
                text_color=TXT if pv==p else TXT2)
        self._render()

    def _render(self):
        for w in self._lp.winfo_children(): w.destroy()
        for w in self._rp.winfo_children(): w.destroy()
        p=self._cur; cfg=AI_PROVIDERS[p]
        keys=self.prefs.setdefault("ai_keys",{}).setdefault(p,[])
        models=cfg["models"]
        cur_model_id=self.prefs.setdefault("ai_models",{}).get(p,models[0][1])
        cur_label=model_label(p,cur_model_id)
        labels=[m[0] for m in models]

        ctk.CTkLabel(self._lp,text="CONFIGURATION",
            font=ctk.CTkFont("Segoe UI",11,"bold"),text_color=META_ACC,fg_color=META_BG3
        ).pack(anchor="w",padx=16,pady=(18,10))
        ctk.CTkLabel(self._lp,text="Model Selection",
            font=ctk.CTkFont("Segoe UI",12),text_color=TXT2,fg_color=META_BG3
        ).pack(anchor="w",padx=16,pady=(0,4))
        mv=StringVar(value=cur_label)
        ctk.CTkComboBox(self._lp,variable=mv,values=labels,state="readonly",
            font=ctk.CTkFont("Segoe UI",12),fg_color=META_BG,text_color=TXT,
            border_color=META_BDR,button_color=META_ACC,button_hover_color=META_ACC2,
            dropdown_fg_color=META_BG,dropdown_text_color=TXT,dropdown_hover_color=META_ACC2,
            corner_radius=6,height=38,command=lambda v:self._save_model(p,v)
        ).pack(fill="x",padx=16,pady=(0,16))
        ctk.CTkFrame(self._lp,fg_color=META_BDR,height=1,corner_radius=0).pack(fill="x")

        ctk.CTkLabel(self._lp,text="Add New API Key",
            font=ctk.CTkFont("Segoe UI",12),text_color=TXT2,fg_color=META_BG3
        ).pack(anchor="w",padx=16,pady=(14,4))
        nkv=StringVar()
        er=ctk.CTkFrame(self._lp,fg_color=META_BG3,corner_radius=0)
        er.pack(fill="x",padx=16,pady=(0,4)); er.grid_columnconfigure(0,weight=1)
        entry=ctk.CTkEntry(er,textvariable=nkv,placeholder_text="sk-or-v1-...",show="•",
            font=ctk.CTkFont("Segoe UI",12),fg_color=META_BG,text_color=TXT,
            border_color=META_BDR,corner_radius=6,height=38)
        entry.grid(row=0,column=0,sticky="ew")
        ctk.CTkButton(er,text="Save",width=72,height=38,fg_color=META_ACC,hover_color=META_ACC2,
            text_color="white",corner_radius=6,
            command=lambda:self._add_key(p,nkv.get().strip(),validate_lbl)
        ).grid(row=0,column=1,padx=(6,0))

        validate_lbl=ctk.CTkLabel(self._lp,text="",
            font=ctk.CTkFont("Segoe UI",11),text_color=TXT3,fg_color=META_BG3)
        validate_lbl.pack(anchor="w",padx=16,pady=(2,10))

        def _live_validate(event=None):
            kv=nkv.get().strip()
            if len(kv) < 8:
                validate_lbl.configure(text="",text_color=TXT3); return
            validate_lbl.configure(text="⟳ Checking…",text_color=AMB)
            def _run():
                ok,msg=validate_key(p,kv)
                self.after(0,lambda:validate_lbl.configure(
                    text=("✓ "+msg) if ok else ("✗ "+msg),
                    text_color=GRN if ok else RED))
            threading.Thread(target=_run,daemon=True).start()
        entry.bind("<FocusOut>",_live_validate)
        entry.bind("<Return>",_live_validate)

        ctk.CTkButton(self._lp,text=f"🔑  Get API Key from {p}",
            fg_color=META_BG,hover_color=META_BDR,text_color=TXT2,border_width=1,
            border_color=META_BDR,height=38,corner_radius=6,
            command=lambda:self._open_url(cfg["key_url"])
        ).pack(fill="x",padx=16,pady=(0,14))

        # RIGHT — stored keys
        ctk.CTkLabel(self._rp,text="STORED KEYS",
            font=ctk.CTkFont("Segoe UI",11,"bold"),text_color=TXT2,fg_color=META_BG2
        ).pack(anchor="w",padx=16,pady=(18,10))
        ks=ctk.CTkScrollableFrame(self._rp,fg_color=META_BG2,corner_radius=0,
            scrollbar_button_color=META_BG3)
        ks.pack(fill="both",expand=True)
        ks.grid_columnconfigure(0,weight=1)
        if not keys:
            ctk.CTkLabel(ks,text="No keys added yet.",font=ctk.CTkFont("Segoe UI",12),
                text_color=TXT3,fg_color=META_BG2).pack(pady=30)
            return
        for i,k in enumerate(keys):
            self._render_key_card(ks,p,i,k)

    def _render_key_card(self,parent,provider,idx,k):
        is_active=k.get("active",False)
        kv=k.get("key","")
        key_short="..."+kv[-10:] if len(kv)>10 else kv
        key_id=""
        bdr_col=META_ACC if is_active else META_BDR
        card=ctk.CTkFrame(parent,fg_color=META_ACC3 if is_active else META_BG3,
            corner_radius=10,border_width=1,border_color=bdr_col)
        card.pack(fill="x",padx=12,pady=(0,8)); card.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(card,text="🔑",font=ctk.CTkFont("Segoe UI",15),
            fg_color="transparent",text_color=TXT2
        ).grid(row=0,column=0,padx=(12,8),pady=(10,4),sticky="w")
        kf=ctk.CTkFrame(card,fg_color="transparent",corner_radius=0)
        kf.grid(row=0,column=1,sticky="ew",pady=(10,4))
        ctk.CTkLabel(kf,text=key_short,font=ctk.CTkFont("Consolas",12,"bold"),
            text_color=TXT,fg_color="transparent",anchor="w").pack(anchor="w")
        ctk.CTkLabel(kf,text=key_id,font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT3,fg_color="transparent",anchor="w").pack(anchor="w")
        if is_active:
            ctk.CTkLabel(card,text="● Active",font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=GRN3,text_color=GRN,corner_radius=20,padx=10,pady=3
            ).grid(row=0,column=2,padx=(0,10),pady=(10,4),sticky="e")
        af=ctk.CTkFrame(card,fg_color="transparent",corner_radius=0)
        af.grid(row=1,column=0,columnspan=3,sticky="ew",padx=10,pady=(0,8))
        ctk.CTkButton(af,text="👁",width=34,height=30,fg_color="transparent",
            hover_color=META_BDR,text_color=TXT3,corner_radius=6,
            command=lambda kv2=kv,lb=kf:self._toggle_show(kv2,lb)
        ).pack(side="left",padx=(0,4))
        ctk.CTkButton(af,text="⧉",width=34,height=30,fg_color="transparent",
            hover_color=META_BDR,text_color=TXT3,corner_radius=6,
            command=lambda kv2=kv:self._copy(kv2)
        ).pack(side="left",padx=(0,4))

        # Validity status icon (right of copy)
        status_lbl=ctk.CTkLabel(af,text="? Test",font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color="transparent",hover_color=META_BDR,text_color=TXT3,
            corner_radius=6,padx=6,pady=4,cursor="hand2")
        status_lbl.pack(side="left",padx=(2,4))
        def _do_validate(e=None,kv2=kv,lbl=status_lbl):
            lbl.configure(text="⟳ …",text_color=AMB)
            def _run():
                ok,msg=validate_key(provider,kv2)
                self.after(0,lambda:lbl.configure(
                    text=("✓ OK" if ok else "✗ Bad"),
                    text_color=GRN if ok else RED))
            threading.Thread(target=_run,daemon=True).start()
        status_lbl.bind("<Button-1>",_do_validate)

        if not is_active:
            ctk.CTkButton(af,text="Activate",width=84,height=30,
                font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=META_BG,hover_color=META_ACC2,text_color=TXT2,
                border_width=1,border_color=META_BDR,corner_radius=6,
                command=lambda i2=idx:self._toggle(provider,i2)
            ).pack(side="left",padx=(2,4))
        else:
            ctk.CTkButton(af,text="Deactivate",width=84,height=30,
                font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=META_BG,hover_color=RED2,text_color=TXT2,
                border_width=1,border_color=META_BDR,corner_radius=6,
                command=lambda i2=idx:self._deactivate(provider,i2)
            ).pack(side="left",padx=(2,4))
        ctk.CTkButton(af,text="🗑",width=34,height=30,fg_color="transparent",
            hover_color=RED2,text_color=TXT3,corner_radius=6,
            command=lambda i2=idx:self._del(provider,i2)
        ).pack(side="right")

    def _toggle_show(self,kv,lf):
        ch=lf.winfo_children()
        if ch:
            cur=ch[0].cget("text")
            short="..."+kv[-10:] if len(kv)>10 else kv
            ch[0].configure(text=kv if cur==short else short)

    def _copy(self,kv): self.clipboard_clear(); self.clipboard_append(kv)

    def _toggle(self,p,idx):
        keys=self.prefs["ai_keys"][p]
        # Multiple keys per provider can be active simultaneously (failover chain)
        keys[idx]["active"]=True
        save_prefs(self.prefs)
        self._tab_btns[p].configure(text=self._tab_text(p))
        self._render()

    def _deactivate(self,p,idx):
        keys=self.prefs["ai_keys"][p]
        keys[idx]["active"]=False
        save_prefs(self.prefs)
        self._tab_btns[p].configure(text=self._tab_text(p))
        self._render()

    def _del(self,p,idx):
        if not messagebox.askyesno("Delete","Delete this key?",parent=self): return
        self.prefs["ai_keys"][p].pop(idx); save_prefs(self.prefs)
        self._tab_btns[p].configure(text=self._tab_text(p))
        self._render()

    def _add_key(self,p,key,validate_lbl=None):
        if not key:
            messagebox.showwarning("Empty","Paste a key first.",parent=self); return
        keys=self.prefs["ai_keys"][p]
        if any(k["key"]==key for k in keys):
            messagebox.showinfo("Duplicate","Already saved.",parent=self); return
        keys.append({"key":key,"active":True})
        save_prefs(self.prefs)
        self._tab_btns[p].configure(text=self._tab_text(p))
        self._render()

    def _save_model(self,p,label):
        mid=model_id_from_label(p,label)
        self.prefs.setdefault("ai_models",{})[p]=mid; save_prefs(self.prefs)

    def _open_url(self,url):
        import webbrowser; webbrowser.open(url)

    def _done(self):
        if self.on_close: self.on_close()
        self.destroy()

# ══════════════════════════════════════════════════════════════════════
#  IMAGE CARD — METADATA MODE
# ══════════════════════════════════════════════════════════════════════
class MetaCard(ctk.CTkFrame):
    STATUS_COLORS={"waiting":(META_BG3,TXT3,META_BDR),"working":(META_ACC3,BLU,META_ACC2),
                   "done":(GRN3,GRN,GRN2),"failed":(RED2,RED,"#5a1a1a")}

    def __init__(self,master,path,on_delete,on_regen,**kw):
        super().__init__(master,fg_color=META_CARD,corner_radius=10,
                         border_width=1,border_color=META_BDR,**kw)
        self.path=path; self.on_delete=on_delete; self.on_regen=on_regen
        self.status="waiting"; self._build()

    def _build(self):
        self.grid_columnconfigure(1,weight=1)
        lp=ctk.CTkFrame(self,fg_color=META_BG3,corner_radius=0,width=150)
        lp.grid(row=0,column=0,sticky="nsew"); lp.grid_propagate(False)
        lp.grid_columnconfigure(0,weight=1)

        tf=ctk.CTkFrame(lp,fg_color=META_BG3,corner_radius=0,height=86)
        tf.grid(row=0,column=0,sticky="ew",padx=6,pady=(6,2)); tf.grid_propagate(False)
        tf.grid_columnconfigure(0,weight=1)
        self._thumb=ctk.CTkLabel(tf,text="🖼",font=ctk.CTkFont("Segoe UI",20),
            fg_color=META_BG,text_color=TXT3,corner_radius=6,width=138,height=80)
        self._thumb.grid(row=0,column=0)
        del_btn=ctk.CTkButton(tf,text="✕",width=16,height=16,
            font=ctk.CTkFont("Segoe UI",7,"bold"),
            fg_color=RED,hover_color="#c04040",text_color="white",corner_radius=8,
            command=self.on_delete)
        del_btn.place(relx=1.0,rely=0.0,anchor="ne",x=0,y=0)

        fname=os.path.basename(self.path)
        fname_short=fname if len(fname)<=20 else fname[:18]+"…"
        ctk.CTkLabel(lp,text=fname_short,font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT2,fg_color=META_BG3,wraplength=136
        ).grid(row=1,column=0,padx=6,pady=(2,0),sticky="ew")
        try: sz=f"{os.path.getsize(self.path)/1024:,.1f} KB"
        except: sz=""
        ctk.CTkLabel(lp,text=sz,font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT3,fg_color=META_BG3
        ).grid(row=2,column=0,padx=6,pady=(0,4))

        self._regen_btn=ctk.CTkButton(lp,text="↺ Retry",height=26,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=META_BG,hover_color=META_BDR,text_color=TXT3,
            corner_radius=6,border_width=1,border_color=META_BDR,
            command=self.on_regen)
        self._regen_btn.grid(row=3,column=0,padx=6,pady=(0,4),sticky="ew")

        self._status_lbl=ctk.CTkLabel(lp,text="○  WAITING",
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            fg_color=META_BG,text_color=TXT3,corner_radius=20,height=24)
        self._status_lbl.grid(row=4,column=0,padx=6,pady=(0,2),sticky="ew")

        self._model_lbl=ctk.CTkLabel(lp,text="",
            font=ctk.CTkFont("Segoe UI",8),
            text_color=TXT3,fg_color=META_BG3,wraplength=136)
        self._model_lbl.grid(row=5,column=0,padx=6,pady=(0,6),sticky="ew")

        rp=ctk.CTkFrame(self,fg_color=META_CARD,corner_radius=0)
        rp.grid(row=0,column=1,sticky="nsew",padx=(6,8),pady=8)
        rp.grid_columnconfigure(0,weight=1)

        self._title_var=StringVar(); self._desc_var=StringVar(); self._kw_var=StringVar()
        self._title_box=self._field(rp,0,"Ħ  Title",      self._title_var,2)
        self._desc_box =self._field(rp,1,"≡  Description",self._desc_var,3)
        self._kw_box   =self._field(rp,2,"🏷  Keywords",   self._kw_var,  3,is_kw=True)

        self._err_lbl=ctk.CTkLabel(rp,text="",font=ctk.CTkFont("Segoe UI",9),
            fg_color=RED2,text_color=RED,corner_radius=6,padx=6,pady=2)

    def _field(self,parent,idx,label,var,lines,is_kw=False):
        hdr=ctk.CTkFrame(parent,fg_color=META_CARD,corner_radius=0)
        hdr.grid(row=idx*2,column=0,sticky="ew",pady=(0,1))
        hdr.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(hdr,text=label,font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT3,fg_color=META_CARD).grid(row=0,column=0,sticky="w")
        cnt_lbl=ctk.CTkLabel(hdr,text="0 Keywords" if is_kw else "0 Chars · 0 Words",
            font=ctk.CTkFont("Segoe UI",9),text_color=TXT3,fg_color=META_CARD)
        cnt_lbl.grid(row=0,column=1,sticky="e")
        ctk.CTkButton(hdr,text="Copy",width=46,height=20,
            font=ctk.CTkFont("Segoe UI",9),fg_color=META_BG3,hover_color=META_BDR,
            text_color=TXT3,corner_radius=20,
            command=lambda v=var:self._copy(v.get())
        ).grid(row=0,column=2,padx=(4,0))
        box=ctk.CTkTextbox(parent,font=ctk.CTkFont("Segoe UI",11),
            fg_color=META_BG3,text_color=CYAN if is_kw else TXT,
            border_color=META_BDR,border_width=1,corner_radius=6,
            wrap="word",height=21*lines)
        box.grid(row=idx*2+1,column=0,sticky="ew",pady=(0,4))

        def _recount():
            c=box.get("1.0","end-1c")
            var.set(c.strip())
            if is_kw:
                kw_count=len([k for k in c.split(",") if k.strip()]) if c.strip() else 0
                cnt_lbl.configure(text=f"{kw_count} Keywords")
            else:
                chars=len(c.strip())
                words=len(c.split()) if c.strip() else 0
                cnt_lbl.configure(text=f"{chars} Chars · {words} Words")

        # Bind to every key release AND a periodic poll fallback (covers paste, etc.)
        box.bind("<KeyRelease>", lambda e: _recount())
        box.bind("<<Paste>>", lambda e: box.after(10, _recount))
        box._recount = _recount
        return box

    def _copy(self,t): self.clipboard_clear(); self.clipboard_append(t)

    def apply_thumb(self, ctk_image):
        if ctk_image is not None:
            self._thumb.configure(image=ctk_image, text="")
            self._thumb._image = ctk_image  # keep reference
        else:
            ext = os.path.splitext(self.path)[1].lower()
            icon = "🎬" if ext in VIDEO_EXTS else ("✦" if ext in VECTOR_EXTS else "🖼")
            self._thumb.configure(text=icon)

    def set_status(self,status,fail_msg=""):
        self.status=status
        bg,fg,bdr=self.STATUS_COLORS.get(status,(META_BG3,TXT3,META_BDR))
        self.configure(border_color=bdr)
        labels={"waiting":"○  WAITING","working":"⟳  WORKING…","done":"✓  DONE","failed":"✗  FAILED"}
        self._status_lbl.configure(text=labels.get(status,""),fg_color=bg,text_color=fg)
        if status=="failed" and fail_msg:
            self._err_lbl.configure(text=f"⚠ {fail_msg[:70]}")
            self._err_lbl.grid(row=6,column=0,sticky="ew",pady=(2,0))
            self._regen_btn.configure(fg_color=RED2,text_color=RED,border_color="#5a1a1a")
        else:
            try: self._err_lbl.grid_remove()
            except: pass
            self._regen_btn.configure(fg_color=META_BG,text_color=TXT3,border_color=META_BDR)

    def set_working(self):
        self._title_box.configure(state="normal"); self._title_box.delete("1.0","end")
        self._title_box.insert("1.0","⟳ AI is analyzing…"); self._title_box.configure(state="disabled")
        for b in [self._desc_box,self._kw_box]:
            b.configure(state="normal"); b.delete("1.0","end")
            b._recount()
        self.clear_model_used()

    def set_result(self,title,desc,kw):
        self._title_box.configure(state="normal")
        for box,val,var in [(self._title_box,title,self._title_var),
                            (self._desc_box,desc,self._desc_var),
                            (self._kw_box,kw,self._kw_var)]:
            box.configure(state="normal"); box.delete("1.0","end"); box.insert("1.0",val)
            var.set(val)
            box._recount()

    def set_model_used(self, provider, model_id, key_index=None):
        label = model_label(provider, model_id)
        idx_str = f" ({key_index})" if key_index else ""
        self._model_lbl.configure(text=f"⚙ {provider} · {label}{idx_str}")
        self._model_used = f"{provider} · {label}{idx_str}"

    def clear_model_used(self):
        self._model_lbl.configure(text="")
        self._model_used = ""

    def clear(self):
        self._title_box.configure(state="normal")
        for box in [self._title_box,self._desc_box,self._kw_box]:
            box.configure(state="normal"); box.delete("1.0","end")
            box._recount()

    def get_result(self):
        return {"Filename":os.path.basename(self.path),
                "Title":self._title_var.get(),
                "Description":self._desc_var.get(),
                "Keywords":self._kw_var.get(),
                "Model":getattr(self,"_model_used","")}


# ══════════════════════════════════════════════════════════════════════
#  IMAGE CARD — PROMPT MODE
# ══════════════════════════════════════════════════════════════════════
class PromptCard(ctk.CTkFrame):
    STATUS_COLORS={"waiting":(META_BG3,TXT3,META_BDR),"working":(META_ACC3,BLU,META_ACC2),
                   "done":(GRN3,GRN,GRN2),"failed":(RED2,RED,"#5a1a1a")}

    def __init__(self,master,path,on_delete,on_regen,**kw):
        super().__init__(master,fg_color=META_CARD,corner_radius=10,
                         border_width=1,border_color=META_BDR,**kw)
        self.path=path; self.on_delete=on_delete; self.on_regen=on_regen
        self.status="waiting"; self._prompt_var=StringVar()
        self._build()

    def _build(self):
        self.grid_columnconfigure(1,weight=1)
        lp=ctk.CTkFrame(self,fg_color=META_BG3,corner_radius=0,width=150)
        lp.grid(row=0,column=0,sticky="nsew"); lp.grid_propagate(False)
        lp.grid_columnconfigure(0,weight=1)
        tf=ctk.CTkFrame(lp,fg_color=META_BG3,corner_radius=0,height=86)
        tf.grid(row=0,column=0,sticky="ew",padx=6,pady=(6,2)); tf.grid_propagate(False)
        tf.grid_columnconfigure(0,weight=1)
        self._thumb=ctk.CTkLabel(tf,text="🖼",font=ctk.CTkFont("Segoe UI",20),
            fg_color=META_BG,text_color=TXT3,corner_radius=6,width=138,height=80)
        self._thumb.grid(row=0,column=0)
        del_btn=ctk.CTkButton(tf,text="✕",width=16,height=16,
            font=ctk.CTkFont("Segoe UI",7,"bold"),
            fg_color=RED,hover_color="#c04040",text_color="white",corner_radius=8,
            command=self.on_delete)
        del_btn.place(relx=1.0,rely=0.0,anchor="ne",x=0,y=0)
        fname=os.path.basename(self.path)
        fname_short=fname if len(fname)<=20 else fname[:18]+"…"
        ctk.CTkLabel(lp,text=fname_short,font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT2,fg_color=META_BG3,wraplength=136
        ).grid(row=1,column=0,padx=6,pady=(2,0),sticky="ew")
        try: sz=f"{os.path.getsize(self.path)/1024:,.1f} KB"
        except: sz=""
        ctk.CTkLabel(lp,text=sz,font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT3,fg_color=META_BG3).grid(row=2,column=0,padx=6,pady=(0,4))
        self._regen_btn=ctk.CTkButton(lp,text="↺ Retry",height=26,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=META_BG,hover_color=META_BDR,text_color=TXT3,
            corner_radius=6,border_width=1,border_color=META_BDR,command=self.on_regen)
        self._regen_btn.grid(row=3,column=0,padx=6,pady=(0,4),sticky="ew")
        self._status_lbl=ctk.CTkLabel(lp,text="○  WAITING",
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            fg_color=META_BG,text_color=TXT3,corner_radius=20,height=24)
        self._status_lbl.grid(row=4,column=0,padx=6,pady=(0,2),sticky="ew")

        self._model_lbl=ctk.CTkLabel(lp,text="",
            font=ctk.CTkFont("Segoe UI",8),
            text_color=TXT3,fg_color=META_BG3,wraplength=136)
        self._model_lbl.grid(row=5,column=0,padx=6,pady=(0,6),sticky="ew")

        rp=ctk.CTkFrame(self,fg_color=META_CARD,corner_radius=0)
        rp.grid(row=0,column=1,sticky="nsew",padx=(6,8),pady=8)
        rp.grid_columnconfigure(0,weight=1)
        rp.grid_rowconfigure(1,weight=1)

        hdr=ctk.CTkFrame(rp,fg_color=META_CARD,corner_radius=0)
        hdr.grid(row=0,column=0,sticky="ew",pady=(0,4))
        hdr.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(hdr,text="≡  Generated Prompt",
            font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=TXT3,fg_color=META_CARD
        ).grid(row=0,column=0,sticky="w")
        self._cnt_lbl=ctk.CTkLabel(hdr,text="0 Chars · 0 Words",
            font=ctk.CTkFont("Segoe UI",9),text_color=TXT3,fg_color=META_CARD)
        self._cnt_lbl.grid(row=0,column=1,sticky="e")
        ctk.CTkButton(hdr,text="Copy",width=46,height=20,
            font=ctk.CTkFont("Segoe UI",9),fg_color=META_BG3,hover_color=META_BDR,
            text_color=TXT3,corner_radius=20,
            command=lambda:self._copy(self._prompt_var.get())
        ).grid(row=0,column=2,padx=(4,0))

        self._prompt_box=ctk.CTkTextbox(rp,font=ctk.CTkFont("Segoe UI",11),
            fg_color=META_BG3,text_color=CYAN,border_color=META_BDR,border_width=1,
            corner_radius=6,wrap="word",height=128)
        self._prompt_box.grid(row=1,column=0,sticky="nsew")

        self._err_lbl=ctk.CTkLabel(rp,text="",font=ctk.CTkFont("Segoe UI",9),
            fg_color=RED2,text_color=RED,corner_radius=6,padx=6,pady=2)

        def _recount():
            c=self._prompt_box.get("1.0","end-1c")
            self._prompt_var.set(c.strip())
            chars=len(c.strip()); words=len(c.split()) if c.strip() else 0
            self._cnt_lbl.configure(text=f"{chars} Chars · {words} Words")
        self._prompt_box.bind("<KeyRelease>", lambda e: _recount())
        self._prompt_box.bind("<<Paste>>", lambda e: self._prompt_box.after(10,_recount))
        self._prompt_box._recount = _recount

    def _copy(self,t): self.clipboard_clear(); self.clipboard_append(t)

    def apply_thumb(self, ctk_image):
        if ctk_image is not None:
            self._thumb.configure(image=ctk_image, text="")
            self._thumb._image = ctk_image
        else:
            ext = os.path.splitext(self.path)[1].lower()
            icon = "🎬" if ext in VIDEO_EXTS else ("✦" if ext in VECTOR_EXTS else "🖼")
            self._thumb.configure(text=icon)

    def set_status(self,status,fail_msg=""):
        self.status=status
        bg,fg,bdr=self.STATUS_COLORS.get(status,(META_BG3,TXT3,META_BDR))
        self.configure(border_color=bdr)
        labels={"waiting":"○  WAITING","working":"⟳  WORKING…","done":"✓  DONE","failed":"✗  FAILED"}
        self._status_lbl.configure(text=labels.get(status,""),fg_color=bg,text_color=fg)
        if status=="failed" and fail_msg:
            self._err_lbl.configure(text=f"⚠ {fail_msg[:70]}")
            self._err_lbl.grid(row=2,column=0,sticky="ew",pady=(2,0))
            self._regen_btn.configure(fg_color=RED2,text_color=RED,border_color="#5a1a1a")
        else:
            try: self._err_lbl.grid_remove()
            except: pass
            self._regen_btn.configure(fg_color=META_BG,text_color=TXT3,border_color=META_BDR)

    def set_working(self):
        self._prompt_box.configure(state="normal"); self._prompt_box.delete("1.0","end")
        self._prompt_box.insert("1.0","⟳ AI is analyzing…")
        self._prompt_box.configure(state="disabled")
        self.clear_model_used()

    def set_result(self,prompt):
        self._prompt_box.configure(state="normal")
        self._prompt_box.delete("1.0","end")
        self._prompt_box.insert("1.0",prompt)
        self._prompt_var.set(prompt)
        self._prompt_box._recount()

    def set_model_used(self, provider, model_id, key_index=None):
        label = model_label(provider, model_id)
        idx_str = f" ({key_index})" if key_index else ""
        self._model_lbl.configure(text=f"⚙ {provider} · {label}{idx_str}")
        self._model_used = f"{provider} · {label}{idx_str}"

    def clear_model_used(self):
        self._model_lbl.configure(text="")
        self._model_used = ""

    def clear(self):
        self._prompt_box.configure(state="normal"); self._prompt_box.delete("1.0","end")
        self._prompt_box._recount()

    def get_result(self):
        return {"Filename":os.path.basename(self.path),"Prompt":self._prompt_var.get(),
                "Model":getattr(self,"_model_used","")}

# ══════════════════════════════════════════════════════════════════════
#  IMPORT PROGRESS DIALOG
# ══════════════════════════════════════════════════════════════════════
class ImportProgressDialog(ctk.CTkToplevel):
    def __init__(self, parent, total):
        super().__init__(parent)
        self.title("Loading Files")
        self.configure(fg_color=META_BG2)
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # block close
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="⟳  Loading Images…",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color=TXT, fg_color=META_BG2).grid(row=0, column=0, padx=24, pady=(20,8))

        self._lbl = ctk.CTkLabel(self, text=f"0 / {total} files",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TXT2, fg_color=META_BG2)
        self._lbl.grid(row=1, column=0, padx=24, pady=(0,10))

        self._bar = ctk.CTkProgressBar(self, progress_color=META_ACC,
            fg_color=META_BG3, height=10, corner_radius=5, width=320)
        self._bar.grid(row=2, column=0, padx=24, pady=(0,20))
        self._bar.set(0)

        self.update_idletasks()
        w, h = 380, 130
        x = parent.winfo_x() + (parent.winfo_width()-w)//2
        y = parent.winfo_y() + (parent.winfo_height()-h)//2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def update_progress(self, done, total):
        self._lbl.configure(text=f"{done} / {total} files")
        self._bar.set(done/total if total else 0)

    def finish(self):
        self.grab_release()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════
if DND_AVAILABLE:
    class DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
        """CTk root window with tkinterdnd2 drag-and-drop support mixed in.
        This is required because plain ctk.CTk() / tkinter.Tk() does not
        initialize the Tcl 'tkdnd' package — drop_target_register() on any
        child widget will silently do nothing without this."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    DnDCTk = ctk.CTk


class App(DnDCTk):
    def __init__(self):
        super().__init__()
        self.title("Meta Zone"); self.configure(fg_color=META_BG)
        self.resizable(True,True)
        self.prefs=load_prefs()

        self.cards=[]            # widgets for the CURRENTLY VISIBLE page only
        self._results = {}       # path -> {"status":..., "title":..., "desc":..., "kw":..., "prompt":..., "model_used":..., "error":...}
        self._all_paths = []     # full ordered list of every queued path (no widget limit)
        self.ai_running=False; self.ai_stop_flag=False
        self.current_mode="meta"
        self._thumb_queue = queue.Queue()

        self.csv_rows=[]; self.csv_headers=[]; self.embed_running=False
        self.csv_path_var=StringVar(); self.folder_path_var=StringVar()
        self.col_file_var=StringVar(value="(skip)"); self.col_title_var=StringVar(value="(skip)")
        self.col_kw_var=StringVar(value="(skip)"); self.col_desc_var=StringVar(value="(skip)")
        self.match_only_var=BooleanVar(value=True); self.subfolder_var=BooleanVar(value=True)
        self.rm_prog_var=BooleanVar(value=True)

        self.ai_platform_var=StringVar(value=self.prefs.get("platform","Adobe Stock"))
        self.ai_title_var=StringVar(value=str(self.prefs.get("title_len",120)))
        self.ai_desc_var=StringVar(value=str(self.prefs.get("desc_len",200)))
        self.ai_kw_var=StringVar(value=str(self.prefs.get("kw_count",49)))
        self.ai_words_var=StringVar(value=str(self.prefs.get("prompt_words",60)))
        self.ai_content_var=StringVar(value=self.prefs.get("content_type","Auto Detect"))
        self.ai_custom_var=StringVar(value=self.prefs.get("custom_prompt",""))
        self.ai_single_kw_var=BooleanVar(value=self.prefs.get("single_keywords",False))
        self._style_vars={}
        for s in ["Silhouette","White Background","Transparent Background","Digital Art"]:
            self._style_vars[s]=BooleanVar(value=False)

        self._build_ui()
        self._center(1240,880)
        self.minsize(940,660)
        self.after(200,self._check_et)
        self.after(500,self._online_loop)
        self.after(100, self._poll_thumb_queue)

    def _center(self,w,h):
        self.update_idletasks()
        sw=self.winfo_screenwidth(); sh=self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def ts(self): return datetime.datetime.now().strftime("%H:%M:%S")

    # ── Build ──────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0,weight=1)
        self.grid_rowconfigure(0,weight=0)
        self.grid_rowconfigure(1,weight=0)
        self.grid_rowconfigure(2,weight=1)
        self.grid_rowconfigure(3,weight=0)
        self._build_titlebar()
        self._build_tabs()
        self._build_statusbar()

    def _build_titlebar(self):
        tb=ctk.CTkFrame(self,fg_color=META_BG,corner_radius=0,height=58)
        tb.grid(row=0,column=0,sticky="ew"); tb.grid_propagate(False)
        tb.grid_columnconfigure(2,weight=1)
        self._titlebar = tb

        ctk.CTkLabel(tb,text="✦",font=ctk.CTkFont("Segoe UI",17,"bold"),
            fg_color=META_ACC2,text_color="white",corner_radius=8,width=30,height=30
        ).grid(row=0,column=0,padx=(16,8),pady=14)

        ctk.CTkLabel(tb,text="Meta Zone",font=ctk.CTkFont("Segoe UI",19,"bold"),
            text_color=TXT,fg_color=META_BG).grid(row=0,column=1,sticky="w")

        ctk.CTkLabel(tb,text="v1.0 Beta",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=BLU,fg_color=META_ACC3,corner_radius=20,padx=8,pady=3
        ).grid(row=0,column=2,sticky="w",padx=(8,0))

        # Online indicator — far right, bigger, beside version
        online_f = ctk.CTkFrame(tb, fg_color=META_BG3, corner_radius=20)
        online_f.grid(row=0, column=3, padx=(0,18), pady=12)
        self._online_dot=ctk.CTkLabel(online_f,text="●",
            font=ctk.CTkFont("Segoe UI",18),text_color=GRN,fg_color=META_BG3)
        self._online_dot.pack(side="left",padx=(12,4),pady=4)
        self._online_lbl=ctk.CTkLabel(online_f,text="Online",
            font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=TXT2,fg_color=META_BG3)
        self._online_lbl.pack(side="left",padx=(0,12),pady=4)

        # Copyright — bigger and more visible
        cr=ctk.CTkFrame(tb,fg_color=META_BG,corner_radius=0)
        cr.grid(row=0,column=4,padx=(0,18),sticky="e")
        ctk.CTkLabel(cr,text="All Rights Reserved By",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT2,fg_color=META_BG).pack(anchor="e")
        ctk.CTkLabel(cr,text="© HASIBNIKON",font=ctk.CTkFont("Segoe UI",14,"bold"),
            text_color=TXT,fg_color=META_BG).pack(anchor="e")

    def _online_loop(self):
        def _check():
            online=check_online()
            self.after(0,lambda:self._set_online(online))
            self.after(8000,self._online_loop)
        threading.Thread(target=_check,daemon=True).start()

    def _set_online(self,online):
        self._is_online = online
        if online:
            self._online_dot.configure(text_color=GRN); self._online_lbl.configure(text="Online",text_color=TXT2)
        else:
            self._online_dot.configure(text_color=RED); self._online_lbl.configure(text="Offline",text_color=RED)
        self._blink_dot(0)

    def _blink_dot(self,count=0):
        if count<6:
            base = GRN if getattr(self,'_is_online',True) else RED
            vis = TXT3 if count%2==0 else base
            self._online_dot.configure(text_color=vis)
            self.after(350,lambda:self._blink_dot(count+1))

    def _poll_thumb_queue(self):
        """Drain thumbnail results from worker threads onto the UI thread in small batches."""
        processed = 0
        try:
            while processed < 12:
                card, img = self._thumb_queue.get_nowait()
                try:
                    if card.winfo_exists():
                        card.apply_thumb(img)
                except Exception:
                    pass
                processed += 1
        except queue.Empty:
            pass
        self.after(40, self._poll_thumb_queue)

    def _build_tabs(self):
        tab_bar=ctk.CTkFrame(self,fg_color=META_BG,corner_radius=0,height=48)
        tab_bar.grid(row=1,column=0,sticky="ew"); tab_bar.grid_propagate(False)
        tab_bar.grid_columnconfigure(2,weight=1)
        self._ai_tab_btn=ctk.CTkButton(tab_bar,text="✨  Metadata AI",
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=META_ACC,hover_color=META_ACC2,text_color="white",
            width=170,height=32,corner_radius=16,
            command=lambda:self._switch_tab("ai"))
        self._ai_tab_btn.grid(row=0,column=0,padx=(12,4),pady=8)
        self._emb_tab_btn=ctk.CTkButton(tab_bar,text="📋  Embed Metadata",
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=EMB_BG3,hover_color=EMB_BDR2,text_color=TXT3,
            width=180,height=32,corner_radius=16,
            command=lambda:self._switch_tab("embed"))
        self._emb_tab_btn.grid(row=0,column=1,padx=4,pady=8)

        self._content=ctk.CTkFrame(self,fg_color=META_BG,corner_radius=0)
        self._content.grid(row=2,column=0,sticky="nsew")
        self._content.grid_columnconfigure(0,weight=1); self._content.grid_rowconfigure(0,weight=1)
        self._ai_frame=ctk.CTkFrame(self._content,fg_color=META_BG,corner_radius=0)
        self._emb_frame=ctk.CTkFrame(self._content,fg_color=EMB_BG,corner_radius=0)
        self._ai_frame.grid(row=0,column=0,sticky="nsew")
        self._emb_frame.grid(row=0,column=0,sticky="nsew")
        self._build_ai_tab(self._ai_frame)
        self._build_embed_tab(self._emb_frame)
        self._switch_tab("ai")

    def _switch_tab(self,which):
        if which=="ai":
            self._ai_frame.tkraise()
            self._ai_tab_btn.configure(fg_color=META_ACC,text_color="white")
            self._emb_tab_btn.configure(fg_color=EMB_BG3,text_color=TXT3)
            self.configure(fg_color=META_BG)
            self._titlebar.configure(fg_color=META_BG)
        else:
            self._emb_frame.tkraise()
            self._emb_tab_btn.configure(fg_color=EMB_ACC,text_color="white")
            self._ai_tab_btn.configure(fg_color=META_BG3,text_color=TXT3)

    # ══════════════════════════════════════════════════════════════════
    #  AI TAB
    # ══════════════════════════════════════════════════════════════════
    def _build_ai_tab(self,parent):
        parent.grid_columnconfigure(0,weight=0)
        parent.grid_columnconfigure(1,weight=1)
        parent.grid_rowconfigure(0,weight=1)
        self._sidebar=ctk.CTkFrame(parent,fg_color=META_BG2,corner_radius=0,width=250)
        self._sidebar.grid(row=0,column=0,sticky="nsew"); self._sidebar.grid_propagate(False)
        self._ai_main=ctk.CTkFrame(parent,fg_color=META_BG,corner_radius=0)
        self._ai_main.grid(row=0,column=1,sticky="nsew")
        self._ai_main.grid_columnconfigure(0,weight=1)
        self._build_sidebar()
        self._build_ai_main()

    # ── SIDEBAR ────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sb=self._sidebar; sb.grid_rowconfigure(1,weight=1); sb.grid_columnconfigure(0,weight=1)
        hdr=ctk.CTkFrame(sb,fg_color=META_BG,corner_radius=0,height=40)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False)
        ctk.CTkLabel(hdr,text="CONTROL PANEL",
            font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=TXT2,fg_color=META_BG
        ).pack(side="left",padx=12,pady=10)
        inner=ctk.CTkScrollableFrame(sb,fg_color=META_BG2,scrollbar_button_color=META_BG3,corner_radius=0)
        inner.grid(row=1,column=0,sticky="nsew"); inner.grid_columnconfigure(0,weight=1)
        self._sb=inner

        ctk.CTkButton(inner,text="🔑  API Configuration",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=META_ACC,hover_color=META_ACC2,text_color="white",
            height=38,corner_radius=8,command=self._open_api_mgr
        ).pack(fill="x",padx=10,pady=(10,3))
        self._api_lbl=ctk.CTkLabel(inner,text="",font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT3,fg_color=META_BG2); self._api_lbl.pack(anchor="w",padx=12,pady=(0,6))
        self._refresh_api_lbl()

        self._div(inner)
        mode_frame=ctk.CTkFrame(inner,fg_color=META_BG3,corner_radius=8)
        mode_frame.pack(fill="x",padx=10,pady=(4,8))
        mode_frame.grid_columnconfigure(0,weight=1); mode_frame.grid_columnconfigure(1,weight=1)
        self._meta_mode_btn=ctk.CTkButton(mode_frame,text="≡  METADATA",height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=META_ACC,hover_color=META_ACC2,text_color="white",corner_radius=6,
            command=lambda:self._set_mode("meta"))
        self._meta_mode_btn.grid(row=0,column=0,sticky="ew",padx=(4,2),pady=4)
        self._prompt_mode_btn=ctk.CTkButton(mode_frame,text="✨  PROMPT",height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color="transparent",hover_color=META_ACC2,text_color=TXT3,corner_radius=6,
            command=lambda:self._set_mode("prompt"))
        self._prompt_mode_btn.grid(row=0,column=1,sticky="ew",padx=(2,4),pady=4)

        self._meta_sliders_frame=ctk.CTkFrame(inner,fg_color=META_BG2,corner_radius=0)
        self._meta_sliders_frame.pack(fill="x")
        msf=self._meta_sliders_frame
        self._lbl(msf,"METADATA SETTINGS")
        self._title_sl=self._slider(msf,"Title Length",self.ai_title_var,10,200,int(self.ai_title_var.get()))
        self._desc_sl =self._slider(msf,"Description Length",self.ai_desc_var,20,500,int(self.ai_desc_var.get()))
        self._kw_sl   =self._slider(msf,"Keywords Count",self.ai_kw_var,5,49,int(min(int(self.ai_kw_var.get()),49)))

        sk_row=ctk.CTkFrame(msf,fg_color=META_BG2,corner_radius=0)
        sk_row.pack(fill="x",padx=10,pady=(2,8)); sk_row.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(sk_row,text="Single Word Keywords",font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2,fg_color=META_BG2).grid(row=0,column=0,sticky="w")
        ctk.CTkSwitch(sk_row,text="",variable=self.ai_single_kw_var,
            progress_color=META_ACC,button_color=TXT,text_color=TXT2,
            fg_color=META_BDR,onvalue=True,offvalue=False,width=46,height=24,
            command=self._save_settings
        ).grid(row=0,column=1,sticky="e")

        # Anchor placeholder marks where the slider frames live in the pack order
        self._slider_anchor = ctk.CTkFrame(inner, fg_color=META_BG2, height=0, corner_radius=0)
        self._slider_anchor.pack(fill="x")

        self._prompt_sliders_frame=ctk.CTkFrame(inner,fg_color=META_BG2,corner_radius=0)
        psf=self._prompt_sliders_frame
        self._lbl(psf,"PROMPT SETTINGS")
        self._words_sl=self._slider(psf,"Max Prompt Words",self.ai_words_var,10,200,int(self.ai_words_var.get()))
        # Not packed initially — meta mode is default

        self._div(inner)
        self._lbl(inner,"PROMPT STYLES")
        styles=["Silhouette","White Background","Transparent Background","Digital Art"]
        for s in styles:
            rf=ctk.CTkFrame(inner,fg_color=META_BG2,corner_radius=0)
            rf.pack(fill="x",padx=10,pady=1); rf.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(rf,text=s,font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT2,fg_color=META_BG2).grid(row=0,column=0,sticky="w")
            ctk.CTkSwitch(rf,text="",variable=self._style_vars[s],
                progress_color=META_ACC,button_color=TXT,text_color=TXT2,
                fg_color=META_BDR,onvalue=True,offvalue=False,width=46,height=24
            ).grid(row=0,column=1,sticky="e")

        self._div(inner)
        self._lbl(inner,"CONTENT TYPE")
        self._ct_combo=ctk.CTkComboBox(inner,variable=self.ai_content_var,
            values=list(CONTENT_SUFFIXES.keys()),state="readonly",
            font=ctk.CTkFont("Segoe UI",11),fg_color=META_BG3,text_color=TXT,
            border_color=META_BDR,button_color=META_ACC,button_hover_color=META_ACC2,
            dropdown_fg_color=META_BG,dropdown_text_color=TXT,dropdown_hover_color=META_ACC2,
            corner_radius=6,height=34,command=lambda v:self._save_settings())
        self._ct_combo.pack(fill="x",padx=10,pady=(2,8))

        self._div(inner)
        cp_hdr=ctk.CTkFrame(inner,fg_color=META_BG2,corner_radius=0)
        cp_hdr.pack(fill="x",padx=10)
        cp_hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(cp_hdr,text="Custom System Prompt",
            font=ctk.CTkFont("Segoe UI",11,"bold"),text_color=TXT2,fg_color=META_BG2
        ).grid(row=0,column=0,sticky="w")
        ctk.CTkLabel(cp_hdr,text="Auto-Saved",
            font=ctk.CTkFont("Segoe UI",9),text_color=TXT3,fg_color=META_BG3,
            corner_radius=20,padx=6,pady=2).grid(row=0,column=1,sticky="e")
        self._custom_box=ctk.CTkTextbox(inner,height=72,
            font=ctk.CTkFont("Segoe UI",11),fg_color=META_BG3,text_color=TXT,
            border_color=META_BDR,border_width=1,corner_radius=6,wrap="word")
        self._custom_box.pack(fill="x",padx=10,pady=(4,4))
        if self.ai_custom_var.get():
            self._custom_box.insert("1.0",self.ai_custom_var.get())
        self._custom_box.bind("<KeyRelease>",lambda e:self._save_custom())

        ctk.CTkButton(inner,text="↺  Reset to Default",height=30,
            font=ctk.CTkFont("Segoe UI",11),fg_color="transparent",
            hover_color=META_BDR,text_color=BLU,corner_radius=6,anchor="w",
            command=self._reset_defaults
        ).pack(anchor="w",padx=10,pady=(0,16))

    def _set_mode(self,mode):
        self.current_mode=mode
        if mode=="meta":
            self._meta_mode_btn.configure(fg_color=META_ACC,text_color="white")
            self._prompt_mode_btn.configure(fg_color="transparent",text_color=TXT3)
            self._prompt_sliders_frame.pack_forget()
            self._meta_sliders_frame.pack(fill="x", before=self._slider_anchor)
        else:
            self._prompt_mode_btn.configure(fg_color=META_ACC,text_color="white")
            self._meta_mode_btn.configure(fg_color="transparent",text_color=TXT3)
            self._meta_sliders_frame.pack_forget()
            self._prompt_sliders_frame.pack(fill="x", before=self._slider_anchor)
        self._clear_queue(confirm=False)

    def _reset_defaults(self):
        self.ai_title_var.set("120"); self._title_sl.set(120)
        self.ai_desc_var.set("200"); self._desc_sl.set(200)
        self.ai_kw_var.set("49"); self._kw_sl.set(49)
        self.ai_words_var.set("60"); self._words_sl.set(60)
        # Force-refresh slider value labels since .set() doesn't fire the command callback
        self._refresh_slider_label(self._title_sl, self.ai_title_var, 120)
        self._refresh_slider_label(self._desc_sl, self.ai_desc_var, 200)
        self._refresh_slider_label(self._kw_sl, self.ai_kw_var, 49)
        self._refresh_slider_label(self._words_sl, self.ai_words_var, 60)
        self.ai_content_var.set("Auto Detect")
        self._custom_box.delete("1.0","end")
        self.ai_custom_var.set("")
        for v in self._style_vars.values(): v.set(False)
        self._save_settings()

    def _refresh_slider_label(self, slider, var, value):
        var.set(str(value))
        lbl = getattr(slider, "_value_label", None)
        if lbl is not None:
            lbl.configure(text=str(value))
        self._save_settings()

    def _div(self,parent):
        ctk.CTkFrame(parent,fg_color=META_BDR,height=1,corner_radius=0
        ).pack(fill="x",padx=8,pady=6)

    def _lbl(self,parent,text):
        ctk.CTkLabel(parent,text=text,font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT3,fg_color=META_BG2).pack(anchor="w",padx=12,pady=(2,2))

    def _slider(self,parent,label,var,from_,to,init):
        fr=ctk.CTkFrame(parent,fg_color=META_BG2,corner_radius=0)
        fr.pack(fill="x",padx=10,pady=(0,6))
        fr.grid_columnconfigure(0,weight=1)
        top=ctk.CTkFrame(fr,fg_color=META_BG2,corner_radius=0); top.pack(fill="x")
        top.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(top,text=label,font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2,fg_color=META_BG2).grid(row=0,column=0,sticky="w")
        vl=ctk.CTkLabel(top,text=str(init),font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=BLU,fg_color=META_BG3,corner_radius=20,padx=7,pady=2)
        vl.grid(row=0,column=1)
        sl=ctk.CTkSlider(fr,from_=from_,to=to,number_of_steps=to-from_,
            progress_color=META_ACC,fg_color=META_BG3,button_color="white",
            button_hover_color="#ddddff",height=15)
        sl.set(init); sl.pack(fill="x",pady=(3,0))
        sl._value_label = vl
        def _upd(v): iv=int(v); var.set(str(iv)); vl.configure(text=str(iv)); self._save_settings()
        sl.configure(command=_upd)
        return sl

    def _save_settings(self):
        self.prefs.update({
            "platform":self.ai_platform_var.get(),
            "title_len":int(self.ai_title_var.get() or 120),
            "desc_len":int(self.ai_desc_var.get() or 200),
            "kw_count":min(int(self.ai_kw_var.get() or 49),49),
            "prompt_words":int(self.ai_words_var.get() or 60),
            "content_type":self.ai_content_var.get(),
            "single_keywords":self.ai_single_kw_var.get(),
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
            self._api_lbl.configure(text="⚠ No active keys",text_color=RED)

    def _open_api_mgr(self):
        APIManagerWindow(self,self.prefs,on_close=self._refresh_api_lbl)

    # ── AI MAIN ────────────────────────────────────────────────────────
    def _build_ai_main(self):
        main=self._ai_main
        main.grid_rowconfigure(2,weight=1)

        topbar=ctk.CTkFrame(main,fg_color=META_BG2,corner_radius=0,height=54)
        topbar.grid(row=0,column=0,sticky="ew"); topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0,weight=1)

        plat_f=ctk.CTkFrame(topbar,fg_color=META_BG2,corner_radius=0)
        plat_f.grid(row=0,column=0,sticky="w",padx=8,pady=8)
        self._plat_btns={}
        for plat in PLATFORM_RULES.keys():
            short=plat.replace(" Stock","").replace(" Images","")[:8]
            btn=ctk.CTkButton(plat_f,text=short,width=78,height=32,
                font=ctk.CTkFont("Segoe UI",10,"bold"),
                fg_color=META_ACC if plat==self.ai_platform_var.get() else META_BG3,
                hover_color=META_ACC2,
                text_color="white" if plat==self.ai_platform_var.get() else TXT2,
                border_width=1,
                border_color=META_ACC if plat==self.ai_platform_var.get() else META_BDR,
                corner_radius=6,command=lambda p=plat:self._sel_platform(p))
            btn.pack(side="left",padx=(0,3))
            self._plat_btns[plat]=btn

        btn_f=ctk.CTkFrame(topbar,fg_color=META_BG2,corner_radius=0)
        btn_f.grid(row=0,column=1,padx=8,pady=8,sticky="e")

        ctk.CTkButton(btn_f,text="🗑  Clear",width=86,height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=META_BG3,hover_color=META_BDR,text_color=TXT3,corner_radius=8,
            command=lambda:self._clear_queue(confirm=True)
        ).pack(side="left",padx=(0,6))

        self._stop_btn=ctk.CTkButton(btn_f,text="■  Stop",width=110,height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=RED2,hover_color="#3d1515",text_color=RED,corner_radius=8,
            command=self._stop_ai)
        self._csv_btn=ctk.CTkButton(btn_f,text="⬇  Download CSV",width=150,height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=GRN2,hover_color=GRN3,text_color=GRN,corner_radius=8,
            command=self._export_csv)
        self._csv_btn.pack(side="left",padx=(0,6))

        self._retry_btn=ctk.CTkButton(btn_f,text="↺  Retry Failed",width=120,height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=AMB2,hover_color="#3a2e00",text_color=AMB,corner_radius=8,
            command=self._retry_failed)

        self._gen_btn=ctk.CTkButton(btn_f,text="✨  Generate Batch",width=170,height=34,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=META_ACC,hover_color=META_ACC2,text_color="white",corner_radius=8,
            command=self.start_generate)
        self._gen_btn.pack(side="left")

        # ── UNIFIED DROP ZONE / BROWSE AREA (bigger, whole box clickable) ──
        ws = ctk.CTkFrame(main, fg_color=META_CARD, corner_radius=14,
            border_width=2, border_color=META_BDR2, height=150)
        ws.grid(row=1, column=0, sticky="ew", padx=6, pady=(6,4))
        ws.grid_propagate(False)
        ws.grid_columnconfigure(0, weight=1)
        ws.grid_rowconfigure(0, weight=1)

        click_area = ctk.CTkFrame(ws, fg_color=META_CARD, corner_radius=12, cursor="hand2")
        click_area.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        click_area.grid_columnconfigure(0, weight=1)
        click_area.grid_rowconfigure(0, weight=1)

        inner_lbl = ctk.CTkLabel(click_area,
            text="☁  Upload Workspace\n\n🖼️  🎬  📄  ✦\n\nDrag & drop files here or click to browse\nSupported: JPG · PNG · GIF · WEBP · TIFF · SVG · EPS · MP4 · MOV",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=TXT2, fg_color=META_CARD, justify="center")
        inner_lbl.grid(row=0, column=0, sticky="nsew")

        self._ws_box = ws
        self._ws_click_area = click_area
        self._ws_inner_lbl = inner_lbl

        # Whole box acts as both browse trigger and drop target
        for widget in (ws, click_area, inner_lbl):
            widget.bind("<Button-1>", lambda e: self._browse_images())

        if DND_AVAILABLE:
            # Registration must happen on the actual Tk widget path; CTkFrame
            # exposes itself directly so this works on the frame and label.
            for widget in (click_area, inner_lbl):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<DropEnter>>", self._on_drag_enter)
                widget.dnd_bind("<<DropLeave>>", self._on_drag_leave)
                widget.dnd_bind("<<Drop>>", self._on_drop)
        else:
            inner_lbl.configure(
                text="☁  Upload Workspace\n\n🖼️  🎬  📄  ✦\n\nClick to browse (drag & drop unavailable — install tkinterdnd2)\nSupported: JPG · PNG · GIF · WEBP · TIFF · SVG · EPS · MP4 · MOV")


        # STATUS ROW — directly above cards, zero gap
        self._stats_bar=ctk.CTkFrame(main,fg_color=META_BG3,corner_radius=0,height=30)
        self._stats_bar.grid(row=2,column=0,sticky="new"); self._stats_bar.grid_propagate(False)
        main.grid_rowconfigure(2,weight=0)
        self._stats_bar.grid_columnconfigure(1,weight=1)
        self._status_dot2=ctk.CTkLabel(self._stats_bar,text="●",
            font=ctk.CTkFont("Segoe UI",11),text_color=GRN,fg_color=META_BG3,width=16)
        self._status_dot2.grid(row=0,column=0,padx=(10,4),pady=5)
        self._stats_lbl=ctk.CTkLabel(self._stats_bar,text="System Ready.",
            font=ctk.CTkFont("Segoe UI",10),text_color=TXT3,fg_color=META_BG3)
        self._stats_lbl.grid(row=0,column=1,sticky="w")

        # CARDS GRID
        main.grid_rowconfigure(3,weight=1)
        cards_border=ctk.CTkFrame(main,fg_color=META_BG2,corner_radius=0,
            border_width=1,border_color=META_BDR)
        cards_border.grid(row=3,column=0,sticky="nsew",padx=6,pady=(2,6))
        cards_border.grid_columnconfigure(0,weight=1); cards_border.grid_rowconfigure(0,weight=1)

        self._cards_outer=ctk.CTkScrollableFrame(cards_border,fg_color=META_BG,
            scrollbar_button_color=META_BG3,scrollbar_button_hover_color=META_BDR,corner_radius=0)
        self._cards_outer.grid(row=0,column=0,sticky="nsew",padx=6,pady=6)
        self._cards_outer.grid_columnconfigure(0,weight=1)
        self._cards_outer.grid_columnconfigure(1,weight=1)

        self._empty_lbl=ctk.CTkLabel(self._cards_outer,
            text="No files in queue. Upload files to start.",
            font=ctk.CTkFont("Segoe UI",13),text_color=TXT3,fg_color=META_BG)
        self._empty_lbl.grid(row=0,column=0,columnspan=2,pady=40)

        # PAGINATION — large queues (1000+ files) render in pages so Tkinter
        # never has to manage more than PAGE_SIZE live widgets at once. This
        # is what actually fixes the freeze: building 1000+ CTkTextbox-heavy
        # cards in one scroll container makes grid layout itself slow,
        # independent of how the cards were created.
        self.PAGE_SIZE = 40
        self._cur_page = 0
        self._all_paths = []   # full ordered list of every queued path

        pager = ctk.CTkFrame(main, fg_color=META_BG2, corner_radius=0, height=36)
        pager.grid(row=4, column=0, sticky="ew", padx=6, pady=(0,6))
        pager.grid_propagate(False)
        pager.grid_columnconfigure(1, weight=1)

        self._pg_prev = ctk.CTkButton(pager, text="‹ Prev", width=70, height=26,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=META_BG3, hover_color=META_BDR, text_color=TXT2,
            corner_radius=6, command=lambda: self._go_page(-1))
        self._pg_prev.grid(row=0, column=0, padx=(8,4), pady=5)

        self._pg_lbl = ctk.CTkLabel(pager, text="Page 1 / 1",
            font=ctk.CTkFont("Segoe UI",10,"bold"), text_color=TXT2, fg_color=META_BG2)
        self._pg_lbl.grid(row=0, column=1)

        self._pg_next = ctk.CTkButton(pager, text="Next ›", width=70, height=26,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=META_BG3, hover_color=META_BDR, text_color=TXT2,
            corner_radius=6, command=lambda: self._go_page(1))
        self._pg_next.grid(row=0, column=2, padx=(4,8), pady=5)

    def _total_pages(self):
        return max(1, (len(self._all_paths) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)

    def _go_page(self, delta):
        new_page = self._cur_page + delta
        new_page = max(0, min(new_page, self._total_pages()-1))
        if new_page != self._cur_page:
            self._cur_page = new_page
            self._render_current_page()

    def _render_current_page(self):
        """Destroy current page's widgets and build only this page's cards."""
        for c in self.cards: c.destroy()
        self.cards = []
        start = self._cur_page * self.PAGE_SIZE
        end = min(start + self.PAGE_SIZE, len(self._all_paths))
        page_paths = self._all_paths[start:end]
        for path in page_paths:
            self._add_card(path, queue_thumb=True)
        total_pages = self._total_pages()
        self._pg_lbl.configure(text=f"Page {self._cur_page+1} / {total_pages}  "
                                     f"({len(self._all_paths)} files total)")
        self._pg_prev.configure(state="normal" if self._cur_page>0 else "disabled")
        self._pg_next.configure(state="normal" if self._cur_page<total_pages-1 else "disabled")
        if not self._all_paths:
            self._empty_lbl.grid(row=0,column=0,columnspan=2,pady=40)
        else:
            self._empty_lbl.grid_remove()
        self._update_stats()


    def _sel_platform(self,plat):
        self.ai_platform_var.set(plat)
        rules=PLATFORM_RULES.get(plat,{})
        kw_val = min(rules.get("kw",49), 49)
        self._title_sl.set(rules.get("title",120)); self.ai_title_var.set(str(rules.get("title",120)))
        self._desc_sl.set(rules.get("desc",200));   self.ai_desc_var.set(str(rules.get("desc",200)))
        self._kw_sl.set(kw_val);         self.ai_kw_var.set(str(kw_val))
        self._refresh_slider_label(self._title_sl, self.ai_title_var, rules.get("title",120))
        self._refresh_slider_label(self._desc_sl, self.ai_desc_var, rules.get("desc",200))
        self._refresh_slider_label(self._kw_sl, self.ai_kw_var, kw_val)
        for p,btn in self._plat_btns.items():
            btn.configure(fg_color=META_ACC if p==plat else META_BG3,
                          text_color="white" if p==plat else TXT2,
                          border_color=META_ACC if p==plat else META_BDR)
        self._save_settings()

    def _on_drag_enter(self, event):
        # Visual "drop ready" highlight, matching the reference screenshot
        self._ws_box.configure(border_color=META_ACC, fg_color=META_ACC3)
        self._ws_click_area.configure(fg_color=META_ACC3)
        self._ws_inner_lbl.configure(fg_color=META_ACC3, text_color=TXT)
        return event.action

    def _on_drag_leave(self, event):
        self._ws_box.configure(border_color=META_BDR2, fg_color=META_CARD)
        self._ws_click_area.configure(fg_color=META_CARD)
        self._ws_inner_lbl.configure(fg_color=META_CARD, text_color=TXT2)
        return event.action

    def _on_drop(self,event):
        self._on_drag_leave(event)
        raw=event.data
        if '{' in raw:
            paths=[p.strip('{}') for p in raw.split('} {')]
            paths=[p.strip('{}') for p in paths]
        else:
            paths=raw.split()
        # Only existing files (folders dropped get expanded one level)
        expanded=[]
        for p in paths:
            if os.path.isdir(p):
                try:
                    for fn in os.listdir(p):
                        fp=os.path.join(p,fn)
                        if os.path.isfile(fp): expanded.append(fp)
                except Exception: pass
            elif os.path.isfile(p):
                expanded.append(p)
        self._add_images(expanded)

    # ── Queue management (PERFORMANCE-CRITICAL — batched + async) ──────
    def _browse_images(self):
        paths=filedialog.askopenfilenames(title="Select images",
            filetypes=[("Supported files",
                        "*.jpg *.jpeg *.png *.webp *.gif *.tiff *.tif *.svg *.eps *.mp4 *.mov"),
                       ("All","*.*")])
        if paths: self._add_images(list(paths))

    def _add_images(self,paths):
        existing=set(self._all_paths)
        new=[p for p in paths if p not in existing
             and os.path.splitext(p)[1].lower() in ALL_SUPPORTED_EXTS]
        if not new: return

        if len(new) > 15:
            self._import_with_progress(new)
        else:
            for path in new:
                self._all_paths.append(path)
                self._results[path] = {"status":"waiting"}
            self._render_current_page()

    def _import_with_progress(self, paths):
        """Register paths in small batches (cheap — just appending to a list,
        no widgets created) so the UI thread is never blocked. Only the
        current page's worth of cards get built; thumbnails for the visible
        page are generated by a small bounded worker pool."""
        dlg = ImportProgressDialog(self, len(paths))
        total = len(paths)
        state = {"i": 0}

        def add_batch():
            BATCH = 200   # cheap — just list/dict appends, no widgets
            end = min(state["i"] + BATCH, total)
            for idx in range(state["i"], end):
                p = paths[idx]
                self._all_paths.append(p)
                self._results[p] = {"status":"waiting"}
            state["i"] = end
            dlg.update_progress(end, total)
            if end < total:
                self.after(1, add_batch)
            else:
                self._render_current_page()
                dlg.finish()

        self.after(10, add_batch)

    def _add_card(self,path,queue_thumb=True):
        idx=len(self.cards)
        CardClass=MetaCard if self.current_mode=="meta" else PromptCard
        card=CardClass(self._cards_outer,path,
            on_delete=lambda p=path:self._del_card(p),
            on_regen=lambda p=path:self._regen_single(p))
        r,c=idx//2,idx%2
        card.grid(row=r,column=c,sticky="ew",
                  padx=(4,2) if c==0 else (2,4),pady=(0,6))
        self.cards.append(card)
        self._empty_lbl.grid_remove()
        # Restore any existing result/status for this path onto the new widget
        res = self._results.get(path, {})
        status = res.get("status","waiting")
        if status == "done":
            if self.current_mode=="meta":
                card.set_result(res.get("title",""),res.get("desc",""),res.get("kw",""))
            else:
                card.set_result(res.get("prompt",""))
            if res.get("model_used"):
                card._model_lbl.configure(text=res["model_used"])
                card._model_used = res["model_used"]
            card.set_status("done")
        elif status == "failed":
            card.set_status("failed", res.get("error",""))
        if queue_thumb:
            self._request_thumb(card)
        return card

    def _request_thumb(self, card):
        threading.Thread(target=lambda:
            self._thumb_queue.put((card, make_thumb(card.path,(138,80)))),
            daemon=True).start()

    def _del_card(self,path):
        if path in self._all_paths:
            self._all_paths.remove(path)
        self._results.pop(path, None)
        # Clamp current page if it no longer exists
        self._cur_page = min(self._cur_page, self._total_pages()-1)
        self._render_current_page()

    def _regrid(self):
        for i,card in enumerate(self.cards):
            r,c=i//2,i%2
            card.grid(row=r,column=c,sticky="ew",
                      padx=(4,2) if c==0 else (2,4),pady=(0,6))

    def _clear_queue(self,confirm=True):
        if self.ai_running: messagebox.showwarning("Busy","Stop generation first."); return
        if confirm and self._all_paths:
            if not messagebox.askyesno("Clear","Remove all images from queue?"): return
        for c in self.cards: c.destroy()
        self.cards.clear()
        self._all_paths.clear()
        self._results.clear()
        self._cur_page = 0
        try: self._retry_btn.pack_forget()
        except: pass
        self._render_current_page()

    def _update_stats(self):
        total=len(self._all_paths)
        done=sum(1 for r in self._results.values() if r.get("status")=="done")
        failed=sum(1 for r in self._results.values() if r.get("status")=="failed")
        pending=sum(1 for r in self._results.values() if r.get("status")=="waiting")
        self._stats_lbl.configure(
            text=f"System Ready.   Files: {total}  |  Done: {done}  |  Failed: {failed}  |  Pending: {pending}"
            if total else "System Ready.")
        self.p_ok.configure(text=f"✓  {done} done")
        self.p_err.configure(text=f"✗  {failed} failed")
        self.p_pend.configure(text=f"○  {pending} pending")

    def _card_for_path(self, path):
        """Returns the live widget for this path if it's on the current
        page, else None. Generation must work even when the card isn't
        currently rendered."""
        for c in self.cards:
            if c.path == path: return c
        return None

    # ── Generate ───────────────────────────────────────────────────────
    def start_generate(self):
        if self.ai_running: messagebox.showwarning("Busy","Already generating."); return
        if not self._all_paths: messagebox.showerror("No Images","Add images first."); return
        if not get_active_keys(self.prefs):
            messagebox.showerror("No API Keys","Open 'API Configuration' to add keys."); return
        self.ai_running=True; self.ai_stop_flag=False
        self._gen_btn.configure(state="disabled",text="⟳  Generating…")
        self._csv_btn.pack_forget()
        self._stop_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        try: self._retry_btn.pack_forget()
        except: pass
        targets=[p for p in self._all_paths
                 if self._results.get(p,{}).get("status") in ("waiting","failed")]
        for p in targets: self._results[p]={"status":"waiting"}
        self._refresh_visible_statuses()
        self._gen_progress_lbl_show(0, len(targets))
        threading.Thread(target=self._gen_thread,args=(targets,),daemon=True).start()

    def _refresh_visible_statuses(self):
        for c in self.cards:
            res=self._results.get(c.path,{})
            st=res.get("status","waiting")
            if st=="waiting": c.clear(); c.set_status("waiting")

    def _gen_progress_lbl_show(self, done, total):
        self._stats_lbl.configure(text=f"Generating…   {done} / {total} processed")

    def _stop_ai(self):
        self.ai_stop_flag=True; self.set_status("■  Stopping…",AMB)

    def _gen_thread(self,targets):
        mode=self.current_mode
        custom=self.ai_custom_var.get()
        ct=self.ai_content_var.get()
        styles=[s for s,v in self._style_vars.items() if v.get()]
        single_kw=self.ai_single_kw_var.get()
        failed_paths=[]

        if mode=="meta":
            tc=int(self.ai_title_var.get() or 120)
            dc=int(self.ai_desc_var.get() or 200)
            kn=min(int(self.ai_kw_var.get() or 49),49)
            prompt=build_meta_prompt(tc,dc,kn,ct,custom,single_kw=single_kw)
        else:
            mw=int(self.ai_words_var.get() or 60)
            prompt=build_prompt_prompt(mw,styles,ct,custom)

        total=len(targets)
        for i,path in enumerate(targets):
            if self.ai_stop_flag: break
            fname=os.path.basename(path)
            self._results[path]={"status":"working"}
            self.after(0,lambda p=path: self._on_card_working(p))
            self.after(0,lambda f=fname,n=i+1,t=total:
                self.set_status(f"⟳  [{n}/{t}] {f}",BLU))
            self.after(0,lambda n=i+1,t=total: self._gen_progress_lbl_show(n,t))
            try:
                ext = os.path.splitext(path)[1].lower()
                if ext in VECTOR_EXTS or ext in VIDEO_EXTS:
                    raise ValueError("Vector/video files need a rendered preview — convert to JPG first")
                raw,provider,model_id,key_idx=call_with_failover(path,prompt,self.prefs,
                    status_cb=lambda msg:self.after(0,lambda m=msg:self.set_status(f"⟳  {m}",BLU)))
                model_used = f"⚙ {provider} · {model_label(provider,model_id)}" + (f" ({key_idx})" if key_idx else "")
                if mode=="meta":
                    title,desc,kw=parse_meta(raw)
                    if not title and not kw: raise ValueError(f"Could not parse: {raw[:80]}")
                    if single_kw: kw=enforce_single_keywords(kw)
                    self._results[path]={"status":"done","title":title,"desc":desc,"kw":kw,"model_used":model_used}
                else:
                    prompt_text=raw.strip()
                    self._results[path]={"status":"done","prompt":prompt_text,"model_used":model_used}
                self.after(0,lambda p=path: self._on_card_done(p))
            except Exception as e:
                err=str(e)[:100]; failed_paths.append(path)
                self._results[path]={"status":"failed","error":err}
                self.after(0,lambda p=path,e=err: self._on_card_failed(p,e))
            self.after(0,self._update_stats)

        self.after(0,lambda fp=list(failed_paths):self._gen_done(fp))

    def _on_card_working(self, path):
        c=self._card_for_path(path)
        if c: c.set_status("working"); c.set_working()

    def _on_card_done(self, path):
        c=self._card_for_path(path)
        if not c: return
        res=self._results.get(path,{})
        if self.current_mode=="meta":
            c.set_result(res.get("title",""),res.get("desc",""),res.get("kw",""))
        else:
            c.set_result(res.get("prompt",""))
        if res.get("model_used"):
            c._model_lbl.configure(text=res["model_used"]); c._model_used=res["model_used"]
        c.set_status("done")

    def _on_card_failed(self, path, err):
        c=self._card_for_path(path)
        if c: c.set_status("failed", err)

    def _gen_done(self,failed_paths):
        self.ai_running=False
        self._gen_btn.configure(state="normal",text="✨  Generate Batch")
        self._stop_btn.pack_forget()
        self._csv_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        if failed_paths:
            self._retry_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        done=sum(1 for r in self._results.values() if r.get("status")=="done")
        failed=sum(1 for r in self._results.values() if r.get("status")=="failed")
        self.set_status(f"● Done — {done} done · {failed} failed",GRN if failed==0 else AMB)
        self._update_stats()

    def _regen_single(self,path):
        if self.ai_running: return
        c=self._card_for_path(path)
        if c: c.set_status("waiting"); c.clear()
        self._results[path]={"status":"waiting"}
        self.ai_running=True; self.ai_stop_flag=False
        self._gen_btn.configure(state="disabled")
        self._csv_btn.pack_forget()
        self._stop_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        threading.Thread(target=self._gen_thread,args=([path],),daemon=True).start()

    def _retry_failed(self):
        failed=[p for p in self._all_paths if self._results.get(p,{}).get("status")=="failed"]
        if not failed: return
        for p in failed:
            self._results[p]={"status":"waiting"}
            c=self._card_for_path(p)
            if c: c.set_status("waiting"); c.clear()
        try: self._retry_btn.pack_forget()
        except: pass
        self.ai_running=True; self.ai_stop_flag=False
        self._gen_btn.configure(state="disabled",text="⟳  Generating…")
        self._csv_btn.pack_forget()
        self._stop_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        threading.Thread(target=self._gen_thread,args=(failed,),daemon=True).start()

    def _export_csv(self):
        done_paths=[p for p in self._all_paths if self._results.get(p,{}).get("status")=="done"]
        if not done_paths: messagebox.showinfo("No Results","No generated results yet."); return
        ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        mode=self.current_mode
        path=filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            initialfile=f"metazone_{mode}_{ts}.csv")
        if not path: return
        try:
            fields=["Filename","Title","Description","Keywords"] if mode=="meta" else ["Filename","Prompt"]
            def row_for(p):
                r=self._results[p]
                fn=os.path.basename(p)
                if mode=="meta":
                    return {"Filename":fn,"Title":r.get("title",""),
                            "Description":r.get("desc",""),"Keywords":r.get("kw","")}
                else:
                    return {"Filename":fn,"Prompt":r.get("prompt","")}
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
                w.writerows(row_for(p) for p in done_paths)
            self.set_status(f"✓  CSV saved — {len(done_paths)} rows",GRN)
            messagebox.showinfo("Saved",f"CSV saved:\n{path}")
        except Exception as e: messagebox.showerror("Error",str(e))


    # ══════════════════════════════════════════════════════════════════
    #  EMBED TAB (deep green theme)
    # ══════════════════════════════════════════════════════════════════
    def _build_embed_tab(self,parent):
        parent.grid_columnconfigure(0,weight=1); parent.grid_columnconfigure(1,weight=0)
        parent.grid_rowconfigure(0,weight=1)
        left=ctk.CTkScrollableFrame(parent,fg_color=EMB_BG,
            scrollbar_button_color=EMB_BG3,corner_radius=0)
        left.grid(row=0,column=0,sticky="nsew",padx=(14,6),pady=12)
        left.grid_columnconfigure(0,weight=1)
        self._el=left
        log_outer=ctk.CTkFrame(parent,fg_color=EMB_BG2,corner_radius=20,
            border_width=1,border_color=EMB_BDR,width=220)
        log_outer.grid(row=0,column=1,sticky="nsew",padx=(0,10),pady=10)
        log_outer.grid_propagate(False); log_outer.grid_rowconfigure(1,weight=1)
        log_outer.grid_columnconfigure(0,weight=1)
        self._build_embed_log(log_outer)
        self._build_emb_actions(); self._build_csv_card()
        self._build_folder_card(); self._build_map_card()

    def _ec(self):
        f=ctk.CTkFrame(self._el,fg_color=EMB_BG2,corner_radius=20,border_width=1,border_color=EMB_BDR)
        f.pack(fill="x",pady=(0,10)); f.grid_columnconfigure(0,weight=1); return f

    def _ech(self,p,num,title,bcmd=None):
        h=ctk.CTkFrame(p,fg_color=EMB_BG3,corner_radius=20,height=52)
        h.pack(fill="x"); h.grid_propagate(False); h.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(h,text=str(num),font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=EMB_ACC2,text_color="white",corner_radius=50,width=38,height=38
        ).grid(row=0,column=0,padx=(14,10),pady=7)
        ctk.CTkLabel(h,text=title,font=ctk.CTkFont("Segoe UI",14,"bold"),
            text_color=TXT2,fg_color=EMB_BG3).grid(row=0,column=1,sticky="w")
        if bcmd:
            ctk.CTkButton(h,text="Browse",width=98,height=34,
                font=ctk.CTkFont("Segoe UI",12,"bold"),
                fg_color=EMB_ACC2,hover_color=EMB_ACC,text_color="white",corner_radius=20,
                command=bcmd).grid(row=0,column=2,padx=(0,12),pady=9)

    def _esw(self,p,t,v):
        return ctk.CTkSwitch(p,text=t,variable=v,
            font=ctk.CTkFont("Segoe UI",13),progress_color=EMB_ACC2,
            button_color=TXT,text_color=TXT2,fg_color=EMB_BDR,
            onvalue=True,offvalue=False,width=58,height=30)

    def _build_emb_actions(self):
        row=ctk.CTkFrame(self._el,fg_color=EMB_BG,corner_radius=0)
        row.pack(fill="x",pady=(0,10)); row.grid_columnconfigure(0,weight=1)
        self.embed_btn=ctk.CTkButton(row,text="▶  Start Embedding",
            font=ctk.CTkFont("Segoe UI",16,"bold"),
            fg_color=EMB_ACC2,hover_color=EMB_ACC,text_color="white",
            height=56,corner_radius=28,command=self.start_embed)
        self.embed_btn.grid(row=0,column=0,sticky="ew")
        ctk.CTkButton(row,text="↺",width=56,height=56,
            font=ctk.CTkFont("Segoe UI",21,"bold"),
            fg_color=RED2,hover_color="#3d1515",text_color=RED,
            corner_radius=28,command=self.reset_embed
        ).grid(row=0,column=1,padx=(8,0))
        ctk.CTkButton(row,text="💾  Save Log",width=136,height=56,
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=EMB_BG3,hover_color=EMB_BDR,text_color=TXT2,
            corner_radius=28,command=self.export_log
        ).grid(row=0,column=2,padx=(8,0))

    def _build_csv_card(self):
        c=self._ec(); self._ech(c,"1","Load CSV",self.load_csv)
        body=ctk.CTkFrame(c,fg_color=EMB_BG2,corner_radius=0)
        body.pack(fill="x",padx=14,pady=(10,12)); body.grid_columnconfigure(0,weight=1)
        ctk.CTkEntry(body,textvariable=self.csv_path_var,state="readonly",height=42,
            font=ctk.CTkFont("Segoe UI",13),fg_color=EMB_BG3,text_color=TXT,
            border_color=EMB_BDR,corner_radius=20).pack(fill="x",pady=(0,10))
        row=ctk.CTkFrame(body,fg_color=EMB_BG2,corner_radius=0); row.pack(fill="x")
        row.grid_columnconfigure(0,weight=1)
        self.csv_badge=ctk.CTkLabel(row,text="No CSV loaded",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=EMB_BG3,text_color=TXT3,corner_radius=20,padx=12,pady=6)
        self.csv_badge.grid(row=0,column=0,sticky="w")
        self._esw(row,"Match Filename Only",self.match_only_var).grid(row=0,column=1,sticky="e",padx=(10,0))

    def _build_folder_card(self):
        c=self._ec(); self._ech(c,"2","Image Folder",self.browse_embed_folder)
        body=ctk.CTkFrame(c,fg_color=EMB_BG2,corner_radius=0)
        body.pack(fill="x",padx=14,pady=(10,12)); body.grid_columnconfigure(0,weight=1)
        ctk.CTkEntry(body,textvariable=self.folder_path_var,state="readonly",height=42,
            font=ctk.CTkFont("Segoe UI",13),fg_color=EMB_BG3,text_color=TXT,
            border_color=EMB_BDR,corner_radius=20).pack(fill="x",pady=(0,10))
        row=ctk.CTkFrame(body,fg_color=EMB_BG2,corner_radius=0); row.pack(fill="x")
        row.grid_columnconfigure(0,weight=1)
        self.folder_badge=ctk.CTkLabel(row,text="No folder selected",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=EMB_BG3,text_color=TXT3,corner_radius=20,padx=12,pady=6)
        self.folder_badge.grid(row=0,column=0,sticky="w")
        self._esw(row,"Include Sub-Folders",self.subfolder_var).grid(row=0,column=1,sticky="e",padx=(10,0))

    def _build_map_card(self):
        c=self._ec(); self._ech(c,"3","Map Columns")
        body=ctk.CTkFrame(c,fg_color=EMB_BG2,corner_radius=0)
        body.pack(fill="x",padx=14,pady=(10,12))
        body.grid_columnconfigure(0,weight=1); body.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(body,text="Auto-detected from column names.",
            font=ctk.CTkFont("Segoe UI",12),text_color=TXT3,fg_color=EMB_BG2
        ).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,10))
        self.col_combos={}
        fields=[("FILENAME",self.col_file_var),("TITLE",self.col_title_var),
                ("KEYWORDS",self.col_kw_var),("DESCRIPTION",self.col_desc_var)]
        for i,(lbl,var) in enumerate(fields):
            r=(i//2)+1; col=i%2
            cell=ctk.CTkFrame(body,fg_color=EMB_BG2,corner_radius=0)
            cell.grid(row=r,column=col,sticky="ew",padx=(0 if col==0 else 8,0),pady=5)
            cell.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(cell,text=lbl,font=ctk.CTkFont("Segoe UI",11,"bold"),
                text_color=TXT3,fg_color=EMB_BG2).pack(anchor="w")
            cb=ctk.CTkComboBox(cell,variable=var,values=["(skip)"],state="readonly",
                font=ctk.CTkFont("Segoe UI",13),fg_color=EMB_BG3,text_color=TXT,
                border_color=EMB_BDR,button_color=EMB_ACC2,button_hover_color=EMB_ACC,
                dropdown_fg_color=EMB_BG,dropdown_text_color=TXT,dropdown_hover_color=EMB_ACC,
                corner_radius=20,height=40,command=lambda v:self._update_match())
            cb.pack(fill="x",pady=(4,0)); self.col_combos[lbl]=cb
        ctk.CTkFrame(body,fg_color=EMB_BDR,height=1,corner_radius=0).grid(
            row=3,column=0,columnspan=2,sticky="ew",pady=(14,10))
        rm=ctk.CTkFrame(body,fg_color=EMB_BG3,corner_radius=20)
        rm.grid(row=4,column=0,columnspan=2,sticky="ew",pady=(0,4))
        rm.grid_columnconfigure(0,weight=1)
        info=ctk.CTkFrame(rm,fg_color=EMB_BG3,corner_radius=0)
        info.grid(row=0,column=0,sticky="w",padx=14,pady=12)
        ctk.CTkLabel(info,text="Remove Program Name",
            font=ctk.CTkFont("Segoe UI",14,"bold"),text_color=TXT2,fg_color=EMB_BG3).pack(anchor="w")
        ctk.CTkLabel(info,text="Clears upscaler/software name from metadata",
            font=ctk.CTkFont("Segoe UI",12),text_color=TXT3,fg_color=EMB_BG3).pack(anchor="w")
        self._esw(rm,"On",self.rm_prog_var).grid(row=0,column=1,padx=(0,14),pady=12)

    def _build_embed_log(self,parent):
        hdr=ctk.CTkFrame(parent,fg_color=EMB_BG3,corner_radius=20,height=46)
        hdr.grid(row=0,column=0,sticky="ew",padx=8,pady=(8,4)); hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(hdr,text="ACTIVITY LOG",font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=TXT3,fg_color=EMB_BG3).grid(row=0,column=0,sticky="w",padx=12)
        ctk.CTkButton(hdr,text="Clear",width=62,height=30,fg_color=EMB_BG,hover_color=EMB_BDR,
            text_color=TXT3,corner_radius=20,command=self.clear_log
        ).grid(row=0,column=1,padx=(0,8))
        self.log_text=ctk.CTkTextbox(parent,font=ctk.CTkFont("Consolas",12),
            fg_color=LOG_BG,text_color=TXT,corner_radius=20,wrap="word",state="disabled",
            scrollbar_button_color=EMB_BG3,scrollbar_button_hover_color=EMB_BDR)
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
        if not content: messagebox.showinfo("Save Log","Log is empty."); return
        path=filedialog.asksaveasfilename(defaultextension=".txt",
            filetypes=[("Text","*.txt")],
            initialfile=f"metazone_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if path:
            with open(path,'w',encoding='utf-8') as f: f.write(content)
            self.log(f"✓  Log saved → {os.path.basename(path)}")

    def load_csv(self):
        p=filedialog.askopenfilename(title="Select CSV",
            filetypes=[("CSV","*.csv"),("All","*.*")])
        if p: self._do_load_csv(p)

    def _do_load_csv(self,path):
        try:
            with open(path,newline='',encoding='utf-8-sig') as f:
                reader=csv.DictReader(f)
                self.csv_rows=list(reader); self.csv_headers=list(reader.fieldnames or [])
            self.csv_path_var.set(path)
            self.csv_badge.configure(
                text=f"🗂  {len(self.csv_rows)} rows · {len(self.csv_headers)} columns",
                fg_color=GRN3,text_color=GRN)
            self.log(f"✓  CSV — {len(self.csv_rows)} rows · {os.path.basename(path)}")
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
        p=filedialog.askdirectory(title="Select image folder")
        if p: self.folder_path_var.set(p); self._update_match(); self.log(f"✓  Folder — {p}")

    def _update_match(self):
        folder=self.folder_path_var.get(); col_f=self.col_file_var.get()
        if not folder or not self.csv_rows or not col_f or col_f=="(skip)": return
        finder=find_recursive if self.subfolder_var.get() else find_file
        matched=sum(1 for row in self.csv_rows
            if finder(folder,(row.get(col_f) or "").strip(),self.match_only_var.get()))
        total=len(self.csv_rows)
        color=GRN if matched==total else AMB if matched>0 else RED
        bg=GRN3 if matched==total else AMB2
        self.folder_badge.configure(text=f"📁  {matched} of {total} matched",fg_color=bg,text_color=color)

    def reset_embed(self):
        if self.embed_running: messagebox.showwarning("Busy","Wait for current job."); return
        if not messagebox.askyesno("Reset","Clear everything?"): return
        self.csv_path_var.set(""); self.folder_path_var.set("")
        for v in [self.col_file_var,self.col_title_var,self.col_kw_var,self.col_desc_var]: v.set("(skip)")
        self.csv_rows=[]; self.csv_headers=[]
        self.csv_badge.configure(text="No CSV loaded",fg_color=EMB_BG3,text_color=TXT3)
        self.folder_badge.configure(text="No folder selected",fg_color=EMB_BG3,text_color=TXT3)
        for cb in self.col_combos.values(): cb.configure(values=["(skip)"])
        self.embed_btn.configure(text="▶  Start Embedding",state="normal")
        self.clear_log(); self.log("↺  Reset — ready")

    def start_embed(self):
        if self.embed_running: return
        et=find_exiftool()
        if not et: messagebox.showerror("ExifTool not found","Place exiftool.exe next to this app.\nhttps://exiftool.org"); return
        if not self.csv_rows: messagebox.showerror("No CSV","Load a CSV first."); return
        if not self.folder_path_var.get(): messagebox.showerror("No folder","Select image folder."); return
        fc=self.col_file_var.get()
        if not fc or fc=="(skip)": messagebox.showerror("Column missing","Select the filename column."); return
        self.embed_running=True; self.embed_btn.configure(state="disabled",text="⟳  Processing…")
        threading.Thread(target=self._embed_thread,args=(et,),daemon=True).start()

    def _embed_thread(self,et):
        folder=self.folder_path_var.get(); col_f=self.col_file_var.get()
        col_t=self.col_title_var.get(); col_k=self.col_kw_var.get(); col_d=self.col_desc_var.get()
        use_sub=self.subfolder_var.get(); use_ext=self.match_only_var.get(); rm_prog=self.rm_prog_var.get()
        total=len(self.csv_rows); ok=skipped=errors=0
        finder=find_recursive if use_sub else find_file
        self.after(0,lambda:self.log(f"▶  Batch started — {total} rows"))
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
            self.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:self._emb_prog(n,t,o,s,e))
        summary=f"{ok} embedded · {skipped} not found · {errors} errors"
        self.after(0,lambda:(
            self.log(f"● Done — {summary}"),self.set_status(f"Done — {summary}",GRN),
            self.embed_btn.configure(state="normal",text="▶  Start Again"),
            setattr(self,'embed_running',False)))

    def _emb_prog(self,n,t,ok,skipped,errors):
        pct=n/t if t else 0; self.sb_prog.set(pct); self.sb_pct.configure(text=f"{int(pct*100)}%")
        self.set_status(f"Processing {n} of {t}…",BLU)
        self.p_ok.configure(text=f"✓  {ok} done"); self.p_err.configure(text=f"✗  {errors} failed")
        self.p_pend.configure(text=f"○  {t-n} pending")

    # ── Status bar ─────────────────────────────────────────────────────
    def _build_statusbar(self):
        sb=ctk.CTkFrame(self,fg_color=META_BG,corner_radius=0,height=42)
        sb.grid(row=3,column=0,sticky="ew"); sb.grid_propagate(False)
        sb.grid_columnconfigure(4,weight=1)
        self.p_ok=ctk.CTkLabel(sb,text="✓  0 done",font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=GRN3,text_color=GRN,corner_radius=20,padx=10,pady=4)
        self.p_ok.grid(row=0,column=0,padx=(10,4),pady=8)
        self.p_err=ctk.CTkLabel(sb,text="✗  0 failed",font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=RED2,text_color=RED,corner_radius=20,padx=10,pady=4)
        self.p_err.grid(row=0,column=1,padx=4,pady=8)
        self.p_pend=ctk.CTkLabel(sb,text="○  0 pending",font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=AMB2,text_color=AMB,corner_radius=20,padx=10,pady=4)
        self.p_pend.grid(row=0,column=2,padx=4,pady=8)
        self.sb_status=ctk.CTkLabel(sb,text="",font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=BLU,fg_color=META_BG)
        self.sb_status.grid(row=0,column=3,padx=(8,0),sticky="w")
        self.sb_prog=ctk.CTkProgressBar(sb,progress_color=GRN,fg_color=META_BG3,
            height=6,corner_radius=3,width=90)
        self.sb_prog.grid(row=0,column=5,padx=(0,4)); self.sb_prog.set(0)
        self.sb_pct=ctk.CTkLabel(sb,text="",font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT2,fg_color=META_BG); self.sb_pct.grid(row=0,column=6,padx=(0,6))
        self.sb_et=ctk.CTkLabel(sb,text="ExifTool · checking…",
            font=ctk.CTkFont("Segoe UI",10),text_color=TXT3,fg_color=META_BG)
        self.sb_et.grid(row=0,column=7,padx=(0,12))

    def set_status(self,msg,color=None):
        self.sb_status.configure(text=msg,text_color=color or TXT3)

    def _check_et(self):
        et=find_exiftool()
        if et: self.sb_et.configure(text="ExifTool · ready",text_color=GRN)
        else:
            self.sb_et.configure(text="ExifTool · missing",text_color=RED)
            self.log("⚠  ExifTool not found")

if __name__=='__main__':
    app=App(); app.mainloop()
