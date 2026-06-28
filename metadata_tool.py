import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, BooleanVar
import csv, subprocess, os, sys, threading, datetime, json, base64
import urllib.request, urllib.error
from PIL import Image, ImageTk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# ── Palette ────────────────────────────────────────────────────────────
BG    = "#050724"; BG2 = "#090b1c"; BG3 = "#0f1128"; BG4 = "#030518"
CARD  = "#0d0f24"; BDR = "#1a1d3a"
TXT   = "#e8e8f4"; TXT2 = "#9a9ab8"; TXT3 = "#4a4a68"
GRN   = "#4dbe62"; GRN2 = "#2a7834"; GRN3 = "#0a1f10"
RED   = "#f07878"; RED2 = "#1e0d0d"
AMB   = "#f5c842"; AMB2 = "#1e1800"
BLU   = "#5b9ef5"; BLU2 = "#1a2a4a"; BLU3 = "#2563eb"
PRP   = "#8b6be8"; PRP2 = "#5c3db5"; PRP3 = "#1e1535"
CYAN  = "#3dd9c4"
LOG_BG= "#030416"

# ── AI Providers ───────────────────────────────────────────────────────
AI_PROVIDERS = {
    "OpenRouter": {
        "models": [
            "qwen/qwen2.5-vl-72b-instruct:free",
            "qwen/qwen2.5-vl-32b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-4-maverick:free",
            "meta-llama/llama-4-scout:free",
            "mistralai/mistral-small-3.1-24b-instruct:free",
        ],
        "key_url": "https://openrouter.ai/keys",
        "key_hint": "Get free key → openrouter.ai",
    },
    "Gemini": {
        "models": [
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
        "key_url": "https://aistudio.google.com/app/apikey",
        "key_hint": "Get free key → aistudio.google.com",
    },
    "Mistral": {
        "models": ["pixtral-12b-2409", "pixtral-large-2411"],
        "key_url": "https://console.mistral.ai/api-keys/",
        "key_hint": "Get key → console.mistral.ai",
    },
    "Groq": {
        "models": [
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
        ],
        "key_url": "https://console.groq.com/keys",
        "key_hint": "Get free key → console.groq.com",
    },
    "OpenAI": {
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1-nano"],
        "key_url": "https://platform.openai.com/api-keys",
        "key_hint": "Get key → platform.openai.com",
    },
    "Claude": {
        "models": ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"],
        "key_url": "https://console.anthropic.com/settings/keys",
        "key_hint": "Get key → console.anthropic.com",
    },
}

PLATFORM_RULES = {
    "General":      {"kw": 49,  "title": 150, "desc": 250},
    "Adobe Stock":  {"kw": 49,  "title": 150, "desc": 250},
    "Shutterstock": {"kw": 50,  "title": 200, "desc": 200},
    "Getty Images": {"kw": 50,  "title": 200, "desc": 500},
    "Freepik":      {"kw": 30,  "title": 150, "desc": 200},
    "Pond5":        {"kw": 50,  "title": 200, "desc": 500},
    "iStock":       {"kw": 50,  "title": 200, "desc": 200},
}

IMAGE_EXTS = {'.jpg','.jpeg','.png','.gif','.webp','.tiff','.tif'}
SKIP_EXTS  = {'.svg','.eps','.ai','.pdf','.mp4','.mov'}

# ── Prefs ──────────────────────────────────────────────────────────────
def prefs_path():
    base = os.path.dirname(sys.executable) if getattr(sys,'frozen',False) \
        else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'prefs.json')

def load_prefs():
    try:
        with open(prefs_path()) as f: return json.load(f)
    except: return {}

def save_prefs(p):
    try:
        with open(prefs_path(),'w') as f: json.dump(p, f, indent=2)
    except: pass

# ── ExifTool ───────────────────────────────────────────────────────────
def find_exiftool():
    if getattr(sys,'frozen',False):
        b = os.path.join(sys._MEIPASS,'exiftool_pkg','exiftool.exe')
        if os.path.exists(b): return b
    base = os.path.dirname(sys.executable if getattr(sys,'frozen',False)
                           else os.path.abspath(__file__))
    for n in ['exiftool.exe','exiftool']:
        p = os.path.join(base, n)
        if os.path.exists(p): return p
    for d in os.environ.get('PATH','').split(os.pathsep):
        for n in ['exiftool.exe','exiftool']:
            p = os.path.join(d, n)
            if os.path.exists(p): return p
    return None

def find_file(folder, name, match_ext):
    exact = os.path.join(folder, name)
    if os.path.exists(exact): return exact
    if match_ext:
        base = os.path.splitext(name)[0]
        try:
            for f in os.listdir(folder):
                if os.path.splitext(f)[0].lower() == base.lower():
                    return os.path.join(folder, f)
        except: pass
    return None

def find_recursive(folder, name, match_ext):
    r = find_file(folder, name, match_ext)
    if r: return r
    try:
        for root, dirs, files in os.walk(folder):
            if root == folder: continue
            r = find_file(root, name, match_ext)
            if r: return r
    except: pass
    return None

# ── AI Engine ──────────────────────────────────────────────────────────
def img_to_b64(path):
    with open(path,'rb') as f: data = f.read()
    ext = os.path.splitext(path)[1].lower()
    mime = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png',
            '.gif':'image/gif','.webp':'image/webp',
            '.tiff':'image/tiff','.tif':'image/tiff'}.get(ext,'image/jpeg')
    return base64.b64encode(data).decode(), mime

def _post(url, body, headers, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode(errors='replace')
            try: msg = json.loads(raw).get("error",{}).get("message") or raw[:300]
            except: msg = raw[:300]
        except: msg = str(e)
        raise RuntimeError(f"HTTP {e.code}: {msg}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {str(e.reason)}")

def call_gemini(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        {"contents":[{"parts":[
            {"inline_data":{"mime_type":mime,"data":b64}},
            {"text":prompt}
        ]}],
         "generationConfig":{"temperature":0.3,"maxOutputTokens":1200}},
        {"Content-Type":"application/json"})
    try:
        return r["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Gemini response: {str(r)[:200]}")

def call_openrouter(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://openrouter.ai/api/v1/chat/completions",
        {"model":model,"max_tokens":1200,
         "messages":[{"role":"user","content":[
             {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}",
         "HTTP-Referer":"https://metazone.app","X-Title":"Meta Zone"})
    try:
        return r["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected OpenRouter response: {str(r)[:200]}")

def call_claude(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://api.anthropic.com/v1/messages",
        {"model":model,"max_tokens":1200,
         "messages":[{"role":"user","content":[
             {"type":"image","source":{"type":"base64","media_type":mime,"data":b64}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"})
    try:
        return r["content"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Claude response: {str(r)[:200]}")

def call_openai(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://api.openai.com/v1/chat/completions",
        {"model":model,"max_tokens":1200,
         "messages":[{"role":"user","content":[
             {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    try:
        return r["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected OpenAI response: {str(r)[:200]}")

def call_groq(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://api.groq.com/openai/v1/chat/completions",
        {"model":model,"max_tokens":1200,
         "messages":[{"role":"user","content":[
             {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    try:
        return r["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Groq response: {str(r)[:200]}")

def call_mistral(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://api.mistral.ai/v1/chat/completions",
        {"model":model,"max_tokens":1200,
         "messages":[{"role":"user","content":[
             {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    try:
        return r["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Mistral response: {str(r)[:200]}")

CALLERS = {
    "Gemini": call_gemini, "OpenRouter": call_openrouter,
    "Claude": call_claude, "OpenAI": call_openai,
    "Groq": call_groq, "Mistral": call_mistral,
}

def build_prompt(title_chars, desc_chars, kw_count):
    return (
        f"You are a professional stock image metadata writer.\n"
        f"Analyze this image and respond ONLY in this exact 3-line format — "
        f"no extra text, no markdown, no explanation:\n\n"
        f"TITLE: <descriptive title, max {title_chars} characters>\n"
        f"DESCRIPTION: <detailed scene description with mood and context, max {desc_chars} characters>\n"
        f"KEYWORDS: <exactly {kw_count} comma-separated keywords, most specific first>\n\n"
        f"Critical rules:\n"
        f"- Output ONLY the 3 lines above. Nothing else before or after.\n"
        f"- TITLE line must start with exactly 'TITLE: '\n"
        f"- DESCRIPTION line must start with exactly 'DESCRIPTION: '\n"
        f"- KEYWORDS line must start with exactly 'KEYWORDS: '\n"
        f"- Keywords: exactly {kw_count} unique tags, no duplicates, no brand names.\n"
        f"- Cover: subject, action, setting, mood, color, style, demographic, use-case."
    )

def parse_response(text):
    """Robust parser — handles multi-line descriptions and loose formatting."""
    title = desc = kw = ""
    lines = text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        upper = line.upper()
        if upper.startswith("TITLE:"):
            title = line[6:].strip()
        elif upper.startswith("DESCRIPTION:"):
            desc = line[12:].strip()
            # absorb continuation lines until next key
            i += 1
            while i < len(lines):
                nxt = lines[i].strip()
                if nxt.upper().startswith("KEYWORDS:") or nxt.upper().startswith("TITLE:"):
                    i -= 1; break
                desc += " " + nxt
                i += 1
            desc = desc.strip()
        elif upper.startswith("KEYWORDS:"):
            kw = line[9:].strip()
            # absorb continuation lines
            i += 1
            while i < len(lines):
                nxt = lines[i].strip()
                if nxt.upper().startswith("TITLE:") or nxt.upper().startswith("DESCRIPTION:"):
                    i -= 1; break
                kw += " " + nxt
                i += 1
            kw = kw.strip()
        i += 1
    return title, desc, kw

def get_active_key_sequence(prefs):
    seq = []
    for provider, cfg in AI_PROVIDERS.items():
        keys = prefs.get("ai_keys", {}).get(provider, [])
        model = prefs.get("ai_models", {}).get(provider, cfg["models"][0])
        for k in keys:
            if k.get("active") and k.get("key"):
                seq.append((provider, k["key"], model))
    return seq

def call_with_failover(path, prompt, prefs, status_cb=None):
    seq = get_active_key_sequence(prefs)
    if not seq:
        raise RuntimeError("No active API keys. Open API Key Manager to add keys.")
    last_err = ""
    for provider, key, model in seq:
        try:
            if status_cb: status_cb(f"Trying {provider} / {model.split('/')[-1]}…")
            raw = CALLERS[provider](key, model, path, prompt)
            title, desc, kw = parse_response(raw)
            if title or kw:
                return title, desc, kw, provider
            raise ValueError(f"Could not parse response. Raw: {raw[:150]}")
        except Exception as e:
            last_err = f"{provider}: {str(e)[:120]}"
            continue
    raise RuntimeError(f"All keys failed. Last error: {last_err}")

# ── Thumbnail helper ───────────────────────────────────────────────────
def make_thumb(path, size=(120, 85)):
    try:
        img = Image.open(path).convert("RGB")
        img.thumbnail(size, Image.LANCZOS)
        return ctk.CTkImage(img, size=img.size)
    except:
        return None

# ══════════════════════════════════════════════════════════════════════
#  API KEY MANAGER POPUP  (freemetadata.com style)
# ══════════════════════════════════════════════════════════════════════
class APIManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent, prefs, on_close=None):
        super().__init__(parent)
        self.title("API Secrets Management")
        self.configure(fg_color=BG2)
        self.resizable(False, False)
        self.grab_set()
        self.prefs = prefs
        self.on_close = on_close
        self._cur_provider = list(AI_PROVIDERS.keys())[0]
        self._show_key_vars = {}   # idx -> BooleanVar for show/hide
        self._build()
        self._center(720, 560)
        self.protocol("WM_DELETE_WINDOW", self._done)

    def _center(self, w, h):
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width()  - w) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Title bar ──
        hdr = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=48)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="API Secrets Management",
            font=ctk.CTkFont("Segoe UI",14,"bold"),
            text_color=TXT, fg_color=BG4).grid(row=0, column=0, sticky="w", padx=16, pady=12)
        ctk.CTkButton(hdr, text="✕", width=32, height=32,
            font=ctk.CTkFont("Segoe UI",12),
            fg_color="transparent", hover_color=RED2, text_color=TXT3,
            corner_radius=6,
            command=self._done).grid(row=0, column=1, padx=10)

        # ── Provider tab bar ──
        tab_bar = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=48)
        tab_bar.grid(row=1, column=0, sticky="ew")
        tab_bar.grid_propagate(False)

        self._tab_btns = {}
        for p in AI_PROVIDERS:
            keys = self.prefs.get("ai_keys",{}).get(p,[])
            active = sum(1 for k in keys if k.get("active"))
            lbl = p
            btn = ctk.CTkButton(tab_bar, text=lbl,
                width=100, height=34,
                font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=BLU3 if p==self._cur_provider else "transparent",
                hover_color=BLU2,
                text_color=TXT if p==self._cur_provider else TXT2,
                corner_radius=8,
                command=lambda pv=p: self._switch_tab(pv))
            btn.pack(in_=tab_bar, side="left",
                     padx=(10 if p==list(AI_PROVIDERS.keys())[0] else 2, 0), pady=7)
            self._tab_btns[p] = btn

        # ── Body: left config + right stored keys ──
        body = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0)
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # LEFT CONFIG PANEL
        self._left_panel = ctk.CTkFrame(body, fg_color=BG3,
            corner_radius=0, width=300)
        self._left_panel.grid(row=0, column=0, sticky="nsew")
        self._left_panel.grid_propagate(False)
        self._left_panel.grid_columnconfigure(0, weight=1)

        # RIGHT STORED KEYS PANEL
        self._right_panel = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        self._right_panel.grid(row=0, column=1, sticky="nsew", padx=(1,0))
        self._right_panel.grid_columnconfigure(0, weight=1)
        self._right_panel.grid_rowconfigure(1, weight=1)

        # ── Footer ──
        ftr = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=48)
        ftr.grid(row=3, column=0, sticky="ew")
        ftr.grid_propagate(False)
        ctk.CTkButton(ftr, text="Done", width=90, height=32,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BLU3, hover_color=BLU2, text_color="white",
            corner_radius=8, command=self._done).pack(side="right", padx=14, pady=8)

        self._render_panel()

    def _switch_tab(self, provider):
        self._cur_provider = provider
        for p, btn in self._tab_btns.items():
            btn.configure(
                fg_color=BLU3 if p==provider else "transparent",
                text_color=TXT if p==provider else TXT2)
        self._render_panel()

    def _render_panel(self):
        # Clear both panels
        for w in self._left_panel.winfo_children(): w.destroy()
        for w in self._right_panel.winfo_children(): w.destroy()
        self._show_key_vars = {}

        p = self._cur_provider
        cfg = AI_PROVIDERS[p]
        keys = self.prefs.setdefault("ai_keys",{}).setdefault(p,[])
        models = cfg["models"]
        cur_model = self.prefs.setdefault("ai_models",{}).get(p, models[0])

        # ── LEFT: CONFIGURATION ──
        ctk.CTkLabel(self._left_panel, text="CONFIGURATION",
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=BLU, fg_color=BG3).pack(anchor="w", padx=16, pady=(16,10))

        # Model selection
        ctk.CTkLabel(self._left_panel, text="Model Selection",
            font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2, fg_color=BG3).pack(anchor="w", padx=16, pady=(0,4))

        model_var = StringVar(value=cur_model)
        ctk.CTkComboBox(self._left_panel,
            variable=model_var, values=models,
            state="readonly",
            font=ctk.CTkFont("Segoe UI",11),
            fg_color=BG4, text_color=TXT, border_color=BDR,
            button_color=BLU3, button_hover_color=BLU2,
            dropdown_fg_color=BG4, dropdown_text_color=TXT,
            dropdown_hover_color=BLU2, corner_radius=6, height=36,
            command=lambda v: self._save_model(p, v)
        ).pack(fill="x", padx=16, pady=(0,16))

        # Divider
        ctk.CTkFrame(self._left_panel, fg_color=BDR, height=1,
            corner_radius=0).pack(fill="x", padx=0)

        # Add new key
        ctk.CTkLabel(self._left_panel, text="Add New API Key",
            font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2, fg_color=BG3).pack(anchor="w", padx=16, pady=(14,4))

        new_key_var = StringVar()
        entry_row = ctk.CTkFrame(self._left_panel, fg_color=BG3, corner_radius=0)
        entry_row.pack(fill="x", padx=16, pady=(0,10))
        entry_row.grid_columnconfigure(0, weight=1)

        entry = ctk.CTkEntry(entry_row, textvariable=new_key_var,
            placeholder_text="sk-or-v1-...",
            show="•",
            font=ctk.CTkFont("Segoe UI",11),
            fg_color=BG4, text_color=TXT, border_color=BDR,
            corner_radius=6, height=36)
        entry.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(entry_row, text="Save", width=70, height=36,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BLU3, hover_color=BLU2, text_color="white",
            corner_radius=6,
            command=lambda: self._add_key(p, new_key_var.get().strip())
        ).grid(row=0, column=1, padx=(6,0))

        # Get API key button
        ctk.CTkButton(self._left_panel,
            text=f"🔑  Get API Key from {p}",
            font=ctk.CTkFont("Segoe UI",11),
            fg_color=BG4, hover_color=BDR, text_color=TXT2,
            border_width=1, border_color=BDR,
            height=36, corner_radius=6,
            command=lambda: self._open_url(cfg["key_url"])
        ).pack(fill="x", padx=16, pady=(0,14))

        # ── RIGHT: STORED KEYS ──
        ctk.CTkLabel(self._right_panel, text="STORED KEYS",
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT2, fg_color=BG2).pack(anchor="w", padx=16, pady=(16,10))

        # Scrollable keys list
        keys_scroll = ctk.CTkScrollableFrame(self._right_panel,
            fg_color=BG2, corner_radius=0,
            scrollbar_button_color=BG3)
        keys_scroll.pack(fill="both", expand=True, padx=0, pady=0)
        keys_scroll.grid_columnconfigure(0, weight=1)

        if not keys:
            ctk.CTkLabel(keys_scroll, text="No keys added yet.\nAdd a key on the left.",
                font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT3, fg_color=BG2, justify="center").pack(pady=30)
            return

        for i, k in enumerate(keys):
            is_active = k.get("active", False)
            self._show_key_vars[i] = BooleanVar(value=False)
            self._render_key_card(keys_scroll, p, i, k, is_active)

    def _render_key_card(self, parent, provider, idx, k, is_active):
        border_color = BLU3 if is_active else BDR
        card_bg = BLU2 if is_active else BG3

        card = ctk.CTkFrame(parent,
            fg_color=card_bg, corner_radius=10,
            border_width=1, border_color=border_color)
        card.pack(fill="x", padx=12, pady=(0,8))
        card.grid_columnconfigure(1, weight=1)

        # Key icon + truncated key
        icon_f = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        icon_f.grid(row=0, column=0, padx=(12,8), pady=(10,4), sticky="w")
        ctk.CTkLabel(icon_f, text="🔑",
            font=ctk.CTkFont("Segoe UI",14),
            fg_color="transparent", text_color=TXT2).pack()

        key_val = k.get("key","")
        key_show = key_val[:10] + "..." if len(key_val) > 10 else key_val
        key_id   = "ID: " + key_val[-4:] if len(key_val) >= 4 else ""

        key_f = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        key_f.grid(row=0, column=1, sticky="ew", pady=(10,4))

        ctk.CTkLabel(key_f, text=key_show,
            font=ctk.CTkFont("Consolas",11,"bold"),
            text_color=TXT, fg_color="transparent",
            anchor="w").pack(anchor="w")
        ctk.CTkLabel(key_f, text=key_id,
            font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT3, fg_color="transparent",
            anchor="w").pack(anchor="w")

        # Active badge (top right)
        if is_active:
            ctk.CTkLabel(card, text="● Active",
                font=ctk.CTkFont("Segoe UI",10,"bold"),
                fg_color=GRN3, text_color=GRN,
                corner_radius=20, padx=10, pady=3
            ).grid(row=0, column=2, padx=(0,10), pady=(10,4), sticky="e")

        # Action row: eye | copy | [activate] | trash
        act_f = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        act_f.grid(row=1, column=0, columnspan=3, sticky="ew",
                   padx=10, pady=(0,8))

        # Show/hide key
        show_var = self._show_key_vars.get(idx, BooleanVar(value=False))
        eye_btn = ctk.CTkButton(act_f, text="👁", width=32, height=28,
            font=ctk.CTkFont("Segoe UI",12),
            fg_color="transparent", hover_color=BDR, text_color=TXT3,
            corner_radius=6,
            command=lambda kv=key_val, lb=key_f: self._toggle_show(kv, lb))
        eye_btn.pack(side="left", padx=(0,4))

        # Copy key
        ctk.CTkButton(act_f, text="⧉", width=32, height=28,
            font=ctk.CTkFont("Segoe UI",12),
            fg_color="transparent", hover_color=BDR, text_color=TXT3,
            corner_radius=6,
            command=lambda kv=key_val: self._copy_key(kv)
        ).pack(side="left", padx=(0,4))

        # Activate / Deactivate
        if not is_active:
            ctk.CTkButton(act_f, text="Activate", width=80, height=28,
                font=ctk.CTkFont("Segoe UI",10,"bold"),
                fg_color=BG4, hover_color=BLU2, text_color=TXT2,
                border_width=1, border_color=BDR,
                corner_radius=6,
                command=lambda i=idx: self._toggle_key(provider, i)
            ).pack(side="left", padx=(0,4))

        # Trash
        ctk.CTkButton(act_f, text="🗑", width=32, height=28,
            font=ctk.CTkFont("Segoe UI",12),
            fg_color="transparent", hover_color=RED2, text_color=TXT3,
            corner_radius=6,
            command=lambda i=idx: self._del_key(provider, i)
        ).pack(side="right")

    def _toggle_show(self, key_val, label_frame):
        children = label_frame.winfo_children()
        if children:
            current = children[0].cget("text")
            if "..." in current:
                # Show full key
                children[0].configure(text=key_val)
            else:
                # Hide again
                key_show = key_val[:10] + "..." if len(key_val) > 10 else key_val
                children[0].configure(text=key_show)

    def _copy_key(self, key_val):
        self.clipboard_clear()
        self.clipboard_append(key_val)

    def _toggle_key(self, provider, idx):
        keys = self.prefs["ai_keys"][provider]
        # Deactivate all others, activate this one
        for i, k in enumerate(keys):
            k["active"] = (i == idx)
        save_prefs(self.prefs)
        self._update_tab_label(provider)
        self._render_panel()

    def _del_key(self, provider, idx):
        if not messagebox.askyesno("Delete Key",
            "Delete this API key?", parent=self): return
        self.prefs["ai_keys"][provider].pop(idx)
        save_prefs(self.prefs)
        self._update_tab_label(provider)
        self._render_panel()

    def _add_key(self, provider, key):
        if not key:
            messagebox.showwarning("Empty Key","Please paste an API key.", parent=self)
            return
        keys = self.prefs["ai_keys"][provider]
        if any(k["key"] == key for k in keys):
            messagebox.showinfo("Duplicate","This key is already saved.", parent=self)
            return
        keys.append({"key": key, "active": True})
        # Deactivate others
        for k in keys[:-1]: k["active"] = False
        save_prefs(self.prefs)
        self._update_tab_label(provider)
        self._render_panel()

    def _save_model(self, provider, model):
        self.prefs.setdefault("ai_models",{})[provider] = model
        save_prefs(self.prefs)

    def _update_tab_label(self, provider):
        keys = self.prefs.get("ai_keys",{}).get(provider,[])
        count = sum(1 for k in keys if k.get("active"))
        self._tab_btns[provider].configure(
            text=f"{provider}" + (f"  ✓{count}" if count else ""))

    def _open_url(self, url):
        import webbrowser; webbrowser.open(url)

    def _done(self):
        if self.on_close: self.on_close()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  IMAGE CARD WIDGET
# ══════════════════════════════════════════════════════════════════════
class ImageCard(ctk.CTkFrame):
    STATUS_COLORS = {
        "waiting": (BG3,  TXT3, BDR),
        "working": (PRP3, PRP,  PRP2),
        "done":    (GRN3, GRN,  GRN2),
        "failed":  (RED2, RED,  "#5a1a1a"),
    }

    def __init__(self, master, path, on_delete, on_regenerate, **kwargs):
        super().__init__(master, fg_color=CARD, corner_radius=12,
                         border_width=1, border_color=BDR, **kwargs)
        self.path = path
        self.on_delete = on_delete
        self.on_regenerate = on_regenerate
        self.status = "waiting"
        self._build()
        self._load_thumb()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)

        # ── LEFT: thumbnail panel ──
        left = ctk.CTkFrame(self, fg_color=BG3, corner_radius=0, width=150)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        thumb_frame = ctk.CTkFrame(left, fg_color=BG3, corner_radius=0, height=95)
        thumb_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,4))
        thumb_frame.grid_propagate(False)
        thumb_frame.grid_columnconfigure(0, weight=1)

        self._thumb_lbl = ctk.CTkLabel(thumb_frame, text="🖼",
            font=ctk.CTkFont("Segoe UI",22),
            fg_color=BG2, text_color=TXT3,
            corner_radius=7, width=134, height=90)
        self._thumb_lbl.grid(row=0, column=0)

        del_btn = ctk.CTkButton(thumb_frame, text="✕", width=22, height=22,
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            fg_color=RED, hover_color="#c04040",
            text_color="white", corner_radius=11,
            command=self.on_delete)
        del_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-2, y=2)

        fname = os.path.basename(self.path)
        fname_short = fname if len(fname) <= 22 else fname[:20]+"…"
        ctk.CTkLabel(left, text=fname_short,
            font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT2, fg_color=BG3,
            wraplength=130).grid(row=1, column=0, padx=8, sticky="ew")

        try:
            size_kb = os.path.getsize(self.path)/1024
            size_str = f"{size_kb:,.1f} KB"
        except: size_str = ""
        ctk.CTkLabel(left, text=size_str,
            font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT3, fg_color=BG3).grid(row=2, column=0, padx=8)

        self._status_lbl = ctk.CTkLabel(left, text="○  WAITING",
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            fg_color=BG3, text_color=TXT3,
            corner_radius=20, height=24)
        self._status_lbl.grid(row=3, column=0, padx=8, pady=(4,8), sticky="ew")

        # ── RIGHT: metadata fields ──
        right = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right.grid_columnconfigure(0, weight=1)

        self._title_var = StringVar()
        self._desc_var  = StringVar()
        self._kw_var    = StringVar()

        self._title_entry = self._field(right, 0, "Ħ  Title",       self._title_var, 1)
        self._desc_entry  = self._field(right, 1, "≡  Description", self._desc_var, 3)
        self._kw_entry    = self._field(right, 2, "🏷  Keywords",    self._kw_var,   3, is_kw=True)

        ftr = ctk.CTkFrame(right, fg_color=CARD, corner_radius=0)
        ftr.grid(row=6, column=0, sticky="ew", pady=(6,0))
        ftr.grid_columnconfigure(0, weight=1)

        self._fail_lbl = ctk.CTkLabel(ftr, text="",
            font=ctk.CTkFont("Segoe UI",9),
            fg_color=RED2, text_color=RED,
            corner_radius=6, padx=8, pady=3)

        self._regen_btn = ctk.CTkButton(ftr,
            text="↺  Regenerate", width=120, height=28,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT3,
            corner_radius=8,
            command=self.on_regenerate)
        self._regen_btn.grid(row=0, column=1)

    def _field(self, parent, row_idx, label, var, lines, is_kw=False):
        hdr = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=0)
        hdr.grid(row=row_idx*2, column=0, sticky="ew", pady=(0,2))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text=label,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT3, fg_color=CARD).grid(row=0, column=0, sticky="w")

        chars_lbl = ctk.CTkLabel(hdr, text="0 chars",
            font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT3, fg_color=CARD)
        chars_lbl.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(hdr, text="Copy", width=48, height=20,
            font=ctk.CTkFont("Segoe UI",9),
            fg_color=BG3, hover_color=BDR, text_color=TXT3,
            corner_radius=20,
            command=lambda v=var: self._copy(v.get())
        ).grid(row=0, column=2, padx=(6,0))

        txt_color = CYAN if is_kw else TXT
        box = ctk.CTkTextbox(parent,
            font=ctk.CTkFont("Segoe UI",11),
            fg_color=BG3, text_color=txt_color,
            border_color=BDR, border_width=1,
            corner_radius=8, wrap="word",
            height=24*lines)
        box.grid(row=row_idx*2+1, column=0, sticky="ew", pady=(0,6))

        def _on_change(event=None):
            content = box.get("1.0","end").strip()
            var.set(content)
            chars_lbl.configure(text=f"{len(content)} chars")

        box.bind("<KeyRelease>", _on_change)
        return box

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _load_thumb(self):
        thumb = make_thumb(self.path, (134, 90))
        if thumb:
            self._thumb_lbl.configure(image=thumb, text="")
            self._thumb_lbl._image = thumb

    def set_status(self, status, fail_msg=""):
        self.status = status
        bg, fg, bdr = self.STATUS_COLORS.get(status, (BG3, TXT3, BDR))
        self.configure(border_color=bdr)
        labels = {
            "waiting": "○  WAITING",
            "working": "⟳  WORKING…",
            "done":    "✓  DONE",
            "failed":  "✗  FAILED",
        }
        self._status_lbl.configure(text=labels.get(status,""),
                                    fg_color=bg, text_color=fg)
        if status == "failed" and fail_msg:
            self._fail_lbl.configure(text=f"⚠ {fail_msg[:80]}")
            self._fail_lbl.grid(row=0, column=0, sticky="w")
            self._regen_btn.configure(fg_color=RED2, text_color=RED,
                                      hover_color="#3d1515")
        else:
            self._fail_lbl.grid_remove()
            self._regen_btn.configure(fg_color=BG3, text_color=TXT3,
                                      hover_color=BDR)

    def set_working_text(self):
        for box in [self._title_entry, self._desc_entry, self._kw_entry]:
            box.configure(state="normal")
            box.delete("1.0","end")
        self._title_entry.insert("1.0","⟳ AI is analyzing image…")
        self._title_entry.configure(state="disabled")

    def set_result(self, title, desc, kw):
        for box, val in [(self._title_entry, title),
                         (self._desc_entry, desc),
                         (self._kw_entry, kw)]:
            box.configure(state="normal")
            box.delete("1.0","end")
            box.insert("1.0", val)
        self._title_var.set(title)
        self._desc_var.set(desc)
        self._kw_var.set(kw)

    def clear_fields(self):
        for box in [self._title_entry, self._desc_entry, self._kw_entry]:
            box.configure(state="normal")
            box.delete("1.0","end")

    def get_result(self):
        return {
            "Filename":    os.path.basename(self.path),
            "Title":       self._title_var.get(),
            "Description": self._desc_var.get(),
            "Keywords":    self._kw_var.get(),
        }


# ══════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Meta Zone")
        self.configure(fg_color=BG)
        self.resizable(True, True)

        self.prefs = load_prefs()
        self.cards = []
        self.ai_running   = False
        self.ai_stop_flag = False

        # Embed tab state
        self.csv_rows     = []
        self.csv_headers  = []
        self.embed_running = False
        self.last_summary  = ""

        self.csv_path_var    = StringVar()
        self.folder_path_var = StringVar()
        self.col_file_var    = StringVar(value="(skip)")
        self.col_title_var   = StringVar(value="(skip)")
        self.col_kw_var      = StringVar(value="(skip)")
        self.col_desc_var    = StringVar(value="(skip)")
        self.match_only_var  = BooleanVar(value=True)
        self.subfolder_var   = BooleanVar(value=True)
        self.rm_prog_var     = BooleanVar(value=True)

        # AI settings vars
        self.ai_platform_var = StringVar(value=self.prefs.get("platform","Adobe Stock"))
        self.ai_title_var    = StringVar(value=str(self.prefs.get("title_len",120)))
        self.ai_desc_var     = StringVar(value=str(self.prefs.get("desc_len",200)))
        self.ai_kw_var       = StringVar(value=str(self.prefs.get("kw_count",49)))
        self.sidebar_visible = True

        self._build_ui()
        self._center(1100, 820)
        self.minsize(800, 600)
        self.after(200, self._check_et)

    def _center(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def ts(self):
        return datetime.datetime.now().strftime("%H:%M:%S")

    # ── Build UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)   # title bar
        self.grid_rowconfigure(1, weight=0)   # tab bar  ← fixed: weight=0 not 1
        self.grid_rowconfigure(2, weight=1)   # content  ← weight=1 here
        self.grid_rowconfigure(3, weight=0)   # status bar
        self._build_titlebar()
        self._build_tabs()
        self._build_statusbar()

    def _build_titlebar(self):
        tb = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=52)
        tb.grid(row=0, column=0, sticky="ew")
        tb.grid_propagate(False)
        tb.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(tb, text="✦",
            font=ctk.CTkFont("Segoe UI",16,"bold"),
            fg_color=PRP2, text_color="white",
            corner_radius=8, width=30, height=30
        ).grid(row=0, column=0, padx=(16,10), pady=11)

        ctk.CTkLabel(tb, text="Meta Zone",
            font=ctk.CTkFont("Segoe UI",18,"bold"),
            text_color=TXT, fg_color=BG4).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(tb, text="v1.0 Beta",
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=PRP, fg_color=PRP3,
            corner_radius=20, padx=8, pady=2
        ).grid(row=0, column=2, sticky="w", padx=(8,0))

        cr = ctk.CTkFrame(tb, fg_color=BG4, corner_radius=0)
        cr.grid(row=0, column=3, padx=(0,18), sticky="e")
        ctk.CTkLabel(cr, text="All Rights Reserved By",
            font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT3, fg_color=BG4).pack(anchor="e")
        ctk.CTkLabel(cr, text="© HASIBNIKON",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=TXT2, fg_color=BG4).pack(anchor="e")

    def _build_tabs(self):
        # Tab bar — fixed height, weight=0
        tab_bar = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=46)
        tab_bar.grid(row=1, column=0, sticky="ew")
        tab_bar.grid_propagate(False)
        tab_bar.grid_columnconfigure(2, weight=1)

        self._ai_tab_btn = ctk.CTkButton(tab_bar,
            text="✨  AI Generate",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=PRP, hover_color=PRP2, text_color="white",
            width=170, height=32, corner_radius=16,
            command=lambda: self._switch_tab("ai"))
        self._ai_tab_btn.grid(row=0, column=0, padx=(14,4), pady=7)

        self._embed_tab_btn = ctk.CTkButton(tab_bar,
            text="📋  Embed Metadata",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT3,
            width=180, height=32, corner_radius=16,
            command=lambda: self._switch_tab("embed"))
        self._embed_tab_btn.grid(row=0, column=1, padx=4, pady=7)

        # Content area
        self._content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._content.grid(row=2, column=0, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._ai_frame    = ctk.CTkFrame(self._content, fg_color=BG, corner_radius=0)
        self._embed_frame = ctk.CTkFrame(self._content, fg_color=BG, corner_radius=0)
        self._ai_frame.grid(row=0, column=0, sticky="nsew")
        self._embed_frame.grid(row=0, column=0, sticky="nsew")

        self._build_ai_tab(self._ai_frame)
        self._build_embed_tab(self._embed_frame)
        self._switch_tab("ai")

    def _switch_tab(self, which):
        if which == "ai":
            self._ai_frame.tkraise()
            self._ai_tab_btn.configure(fg_color=PRP, text_color="white")
            self._embed_tab_btn.configure(fg_color=BG3, text_color=TXT3)
        else:
            self._embed_frame.tkraise()
            self._embed_tab_btn.configure(fg_color=PRP, text_color="white")
            self._ai_tab_btn.configure(fg_color=BG3, text_color=TXT3)

    # ══════════════════════════════════════════════════════════════════
    #  AI GENERATE TAB
    # ══════════════════════════════════════════════════════════════════
    def _build_ai_tab(self, parent):
        parent.grid_columnconfigure(0, weight=0)   # sidebar
        parent.grid_columnconfigure(1, weight=1)   # main
        parent.grid_rowconfigure(0, weight=1)

        # Sidebar
        self._sidebar = ctk.CTkFrame(parent, fg_color=BG2,
            corner_radius=0, width=230)
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)

        # Main area
        self._ai_main = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        self._ai_main.grid(row=0, column=1, sticky="nsew")
        self._ai_main.grid_columnconfigure(0, weight=1)
        self._ai_main.grid_rowconfigure(2, weight=1)

        self._build_sidebar()
        self._build_ai_main()

    def _build_sidebar(self):
        sb = self._sidebar
        sb.grid_rowconfigure(1, weight=1)
        sb.grid_columnconfigure(0, weight=1)

        # Header row with collapse button
        hdr = ctk.CTkFrame(sb, fg_color=BG4, corner_radius=0, height=40)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="CONFIGURATION",
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3, fg_color=BG4
        ).grid(row=0, column=0, sticky="w", padx=12)

        self._collapse_btn = ctk.CTkButton(hdr, text="‹", width=28, height=28,
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT2,
            corner_radius=6,
            command=self._toggle_sidebar)
        self._collapse_btn.grid(row=0, column=1, padx=8)

        # Scrollable inner content
        self._sb_inner = ctk.CTkScrollableFrame(sb, fg_color=BG2,
            scrollbar_button_color=BG3, corner_radius=0)
        self._sb_inner.grid(row=1, column=0, sticky="nsew")
        self._sb_inner.grid_columnconfigure(0, weight=1)
        inner = self._sb_inner

        # API Key Manager button
        ctk.CTkButton(inner, text="🔑  Add API Keys",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BLU3, hover_color=BLU2,
            text_color="white", height=38,
            corner_radius=8,
            command=self._open_api_manager
        ).pack(fill="x", padx=12, pady=(12,4))

        self._api_active_lbl = ctk.CTkLabel(inner, text="",
            font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT3, fg_color=BG2)
        self._api_active_lbl.pack(anchor="w", padx=14, pady=(2,8))
        self._refresh_api_lbl()

        self._divider(inner)
        self._sb_label(inner, "METADATA")

        self._title_slider = self._slider(inner, "Title Length",
            self.ai_title_var, 10, 200, int(self.prefs.get("title_len",120)))
        self._desc_slider  = self._slider(inner, "Description Length",
            self.ai_desc_var, 20, 500, int(self.prefs.get("desc_len",200)))
        self._kw_slider    = self._slider(inner, "Keywords Count",
            self.ai_kw_var, 5, 50, int(self.prefs.get("kw_count",49)))

        self._divider(inner)
        self._sb_label(inner, "PLATFORM")

        ctk.CTkComboBox(inner,
            variable=self.ai_platform_var,
            values=list(PLATFORM_RULES.keys()),
            state="readonly",
            font=ctk.CTkFont("Segoe UI",11),
            fg_color=BG3, text_color=TXT, border_color=BDR,
            button_color=BLU3, button_hover_color=BLU2,
            dropdown_fg_color=BG4, dropdown_text_color=TXT,
            dropdown_hover_color=BLU2, corner_radius=8, height=34,
            command=lambda v: self._on_platform_change(v)
        ).pack(fill="x", padx=12, pady=(4,10))

        self._divider(inner)
        self._sb_label(inner, "PROMPT STYLE")

        self._sil_var  = BooleanVar(value=False)
        self._wbg_var  = BooleanVar(value=False)
        self._dart_var = BooleanVar(value=False)
        for text, var in [("Silhouette", self._sil_var),
                          ("White Background", self._wbg_var),
                          ("Digital Art", self._dart_var)]:
            row = ctk.CTkFrame(inner, fg_color=BG2, corner_radius=0)
            row.pack(fill="x", padx=12, pady=2)
            ctk.CTkCheckBox(row, text=text, variable=var,
                font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT2, fg_color=BG2,
                checkmark_color="white", border_color=BDR,
                hover_color=BLU2,
                checkbox_width=15, checkbox_height=15).pack(anchor="w")

        self._divider(inner)

        note = ctk.CTkFrame(inner, fg_color=BG3,
            corner_radius=8, border_width=1, border_color=BDR)
        note.pack(fill="x", padx=12, pady=(0,16))
        ctk.CTkLabel(note,
            text="⚡  Auto Failover ON\n\nOn API failure, retries\nwith next active key.\nFailed images move\nto top of queue.",
            font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT3, fg_color=BG3,
            justify="left").pack(padx=10, pady=10, anchor="w")

    def _toggle_sidebar(self):
        if self.sidebar_visible:
            # Hide sidebar, show expand button in main area
            self._sidebar.grid_remove()
            self.sidebar_visible = False
            self._expand_btn.grid()
        else:
            # Show sidebar, hide expand button
            self._sidebar.grid()
            self.sidebar_visible = True
            self._expand_btn.grid_remove()

    def _build_ai_main(self):
        main = self._ai_main

        # ── Expand button (visible when sidebar collapsed) ──
        # Place it in row=0 as an overlay-style fixed widget
        self._expand_btn = ctk.CTkButton(main,
            text="›", width=28, height=56,
            font=ctk.CTkFont("Segoe UI",14,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT2,
            corner_radius=0,
            command=self._toggle_sidebar)
        self._expand_btn.grid(row=0, column=0, rowspan=3, sticky="nw")
        self._expand_btn.grid_remove()  # hidden by default

        # ── Top bar: platform tabs + action buttons ──
        topbar = ctk.CTkFrame(main, fg_color=BG2, corner_radius=0, height=54)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)

        # Platform quick-select tabs (like freemetadata)
        plat_f = ctk.CTkFrame(topbar, fg_color=BG2, corner_radius=0)
        plat_f.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        self._plat_btns = {}
        for plat in PLATFORM_RULES.keys():
            short = plat.replace(" Stock","").replace(" Images","")[:8]
            btn = ctk.CTkButton(plat_f, text=short,
                width=72, height=32,
                font=ctk.CTkFont("Segoe UI",10,"bold"),
                fg_color=BG3 if plat != self.ai_platform_var.get() else BLU3,
                hover_color=BLU2,
                text_color=TXT2 if plat != self.ai_platform_var.get() else "white",
                border_width=1,
                border_color=BLU3 if plat == self.ai_platform_var.get() else BDR,
                corner_radius=6,
                command=lambda p=plat: self._select_platform(p))
            btn.pack(side="left", padx=(0,4))
            self._plat_btns[plat] = btn

        # Action buttons
        btn_f = ctk.CTkFrame(topbar, fg_color=BG2, corner_radius=0)
        btn_f.grid(row=0, column=1, padx=10, pady=8, sticky="e")

        ctk.CTkButton(btn_f, text="🗑  Clear",
            width=90, height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT3,
            corner_radius=8,
            command=self._clear_queue).pack(side="left", padx=(0,6))

        self._gen_btn = ctk.CTkButton(btn_f,
            text="✨  Generate Batch",
            width=160, height=34,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BLU3, hover_color=BLU2, text_color="white",
            corner_radius=8,
            command=self.start_generate)
        self._gen_btn.pack(side="left", padx=(0,6))

        self._stop_btn = ctk.CTkButton(btn_f, text="■  Stop",
            width=90, height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=RED2, hover_color="#3d1515", text_color=RED,
            corner_radius=8,
            command=self._stop_ai)
        self._stop_btn.pack(side="left", padx=(0,6))

        self._csv_btn = ctk.CTkButton(btn_f, text="⬇  Download CSV",
            width=140, height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=GRN2, hover_color=GRN3, text_color=GRN,
            corner_radius=8,
            command=self._export_csv)
        self._csv_btn.pack(side="left", padx=(0,6))

        self._retry_btn = ctk.CTkButton(btn_f, text="↺  Retry Failed",
            width=120, height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=AMB2, hover_color="#3a2e00", text_color=AMB,
            corner_radius=8,
            command=self._retry_failed)
        self._retry_btn.pack(side="left")
        self._retry_btn.pack_forget()

        # ── Upload workspace / drop zone ──
        self._drop_frame = ctk.CTkFrame(main,
            fg_color=CARD, corner_radius=0,
            border_width=1, border_color=BDR)
        self._drop_frame.grid(row=1, column=0, sticky="ew")
        self._drop_frame.grid_columnconfigure(1, weight=1)

        # Left label
        ctk.CTkLabel(self._drop_frame,
            text="☁  Upload Workspace",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=CARD, text_color=TXT2
        ).grid(row=0, column=0, padx=(14,16), pady=14)

        # File type icons
        icons_f = ctk.CTkFrame(self._drop_frame, fg_color=CARD, corner_radius=0)
        icons_f.grid(row=0, column=1, sticky="ew", pady=12)

        ctk.CTkLabel(icons_f, text="🖼️  🎬  📄  🎨",
            font=ctk.CTkFont("Segoe UI",16),
            fg_color=CARD, text_color=TXT3).pack(side="left", padx=(0,8))

        ctk.CTkLabel(icons_f,
            text="Supported: JPG, PNG, GIF, WEBP, TIFF\nDrag files here or click Browse",
            font=ctk.CTkFont("Segoe UI",10),
            fg_color=CARD, text_color=TXT3, justify="left").pack(side="left")

        # Browse button
        ctk.CTkButton(self._drop_frame, text="Browse",
            width=100, height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT2,
            border_width=1, border_color=BDR,
            corner_radius=8,
            command=self._browse_images
        ).grid(row=0, column=2, padx=14, pady=12)

        # Status line
        self._status_row = ctk.CTkFrame(main, fg_color=BG3, corner_radius=0, height=30)
        self._status_row.grid(row=2, column=0, sticky="ew")
        self._status_row.grid_propagate(False)
        self._status_row.grid_columnconfigure(1, weight=1)

        self._status_dot = ctk.CTkLabel(self._status_row, text="●",
            font=ctk.CTkFont("Segoe UI",10),
            text_color=GRN, fg_color=BG3, width=20)
        self._status_dot.grid(row=0, column=0, padx=(10,4), pady=5)

        self._stats_lbl = ctk.CTkLabel(self._status_row,
            text="System Ready.",
            font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT3, fg_color=BG3)
        self._stats_lbl.grid(row=0, column=1, sticky="w")

        # ── Cards scroll area ──
        self._cards_outer = ctk.CTkScrollableFrame(main,
            fg_color=BG,
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BDR,
            corner_radius=0)
        self._cards_outer.grid(row=3, column=0, sticky="nsew")
        self._cards_outer.grid_columnconfigure(0, weight=1)
        self._cards_outer.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(3, weight=1)

        # Empty queue label
        self._empty_lbl = ctk.CTkLabel(self._cards_outer,
            text="No files in queue. Upload files to start.",
            font=ctk.CTkFont("Segoe UI",12),
            text_color=TXT3, fg_color=BG)
        self._empty_lbl.grid(row=0, column=0, columnspan=2, pady=40)

    def _select_platform(self, plat):
        self.ai_platform_var.set(plat)
        self._on_platform_change(plat)
        # Sync sliders
        rules = PLATFORM_RULES.get(plat, {})
        if hasattr(self, '_title_slider'):
            kw = rules.get("kw", 49)
            title = rules.get("title", 150)
            desc  = rules.get("desc", 250)
            self._title_slider.set(title); self.ai_title_var.set(str(title))
            self._desc_slider.set(desc);   self.ai_desc_var.set(str(desc))
            self._kw_slider.set(kw);       self.ai_kw_var.set(str(kw))
        self._save_settings()

    def _on_platform_change(self, plat):
        for p, btn in self._plat_btns.items():
            is_sel = (p == plat)
            btn.configure(
                fg_color=BLU3 if is_sel else BG3,
                text_color="white" if is_sel else TXT2,
                border_color=BLU3 if is_sel else BDR)

    # ── Sidebar helpers ────────────────────────────────────────────────
    def _sb_label(self, parent, text):
        ctk.CTkLabel(parent, text=text,
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3, fg_color=BG2
        ).pack(anchor="w", padx=14, pady=(8,2))

    def _divider(self, parent):
        ctk.CTkFrame(parent, fg_color=BDR, height=1,
            corner_radius=0).pack(fill="x", padx=12, pady=6)

    def _slider(self, parent, label, var, from_, to, init_val):
        frame = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0)
        frame.pack(fill="x", padx=12, pady=(0,8))
        frame.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(frame, fg_color=BG2, corner_radius=0)
        top.pack(fill="x")
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=label,
            font=ctk.CTkFont("Segoe UI",11),
            text_color=TXT2, fg_color=BG2).grid(row=0, column=0, sticky="w")
        val_lbl = ctk.CTkLabel(top, text=str(init_val),
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=BLU, fg_color=BG3,
            corner_radius=20, padx=7, pady=1)
        val_lbl.grid(row=0, column=1)

        sl = ctk.CTkSlider(frame, from_=from_, to=to,
            number_of_steps=to-from_,
            progress_color=BLU3, fg_color=BG3,
            button_color="white", button_hover_color="#ddddff",
            height=16)
        sl.set(init_val)
        sl.pack(fill="x", pady=(4,0))

        def _update(v):
            iv = int(v); var.set(str(iv)); val_lbl.configure(text=str(iv))
            self._save_settings()
        sl.configure(command=_update)
        return sl

    def _save_settings(self):
        self.prefs["platform"]  = self.ai_platform_var.get()
        self.prefs["title_len"] = int(self.ai_title_var.get() or 120)
        self.prefs["desc_len"]  = int(self.ai_desc_var.get() or 200)
        self.prefs["kw_count"]  = int(self.ai_kw_var.get() or 49)
        save_prefs(self.prefs)

    def _refresh_api_lbl(self):
        seq = get_active_key_sequence(self.prefs)
        total = len(seq)
        providers = list(dict.fromkeys(p for p,_,_ in seq))
        if total:
            txt = f"✓  {total} active key{'s' if total!=1 else ''} · {len(providers)} provider{'s' if len(providers)!=1 else ''}"
            color = GRN
        else:
            txt = "⚠  No active keys"
            color = RED
        self._api_active_lbl.configure(text=txt, text_color=color)

    def _open_api_manager(self):
        APIManagerWindow(self, self.prefs, on_close=self._refresh_api_lbl)

    # ── Image queue ────────────────────────────────────────────────────
    def _browse_images(self):
        paths = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[("Images","*.jpg *.jpeg *.png *.webp *.gif *.tiff *.tif"),
                       ("All","*.*")])
        if paths: self._add_images(list(paths))

    def _add_images(self, paths):
        existing = {c.path for c in self.cards}
        new = [p for p in paths
               if p not in existing
               and os.path.splitext(p)[1].lower() in IMAGE_EXTS]
        for path in new:
            self._add_card(path)
        self._update_stats()

    def _add_card(self, path):
        idx = len(self.cards)
        card = ImageCard(
            self._cards_outer, path,
            on_delete=lambda p=path: self._del_card(p),
            on_regenerate=lambda p=path: self._regen_single(p))
        r, c = idx // 2, idx % 2
        card.grid(row=r, column=c,
            sticky="ew",
            padx=(0,4) if c==0 else (4,0),
            pady=(0,8))
        self.cards.append(card)
        # Hide empty label
        self._empty_lbl.grid_remove()
        return card

    def _del_card(self, path):
        for c in self.cards:
            if c.path == path:
                c.destroy()
                self.cards.remove(c)
                break
        self._regrid_cards()
        self._update_stats()
        if not self.cards:
            self._empty_lbl.grid(row=0, column=0, columnspan=2, pady=40)

    def _regrid_cards(self):
        for i, card in enumerate(self.cards):
            r, c = i//2, i%2
            card.grid(row=r, column=c,
                sticky="ew",
                padx=(0,4) if c==0 else (4,0),
                pady=(0,8))

    def _clear_queue(self):
        if self.ai_running:
            messagebox.showwarning("Busy","Stop generation first."); return
        for c in self.cards: c.destroy()
        self.cards.clear()
        self._update_stats()
        self._retry_btn.pack_forget()
        self._empty_lbl.grid(row=0, column=0, columnspan=2, pady=40)

    def _update_stats(self):
        total   = len(self.cards)
        done    = sum(1 for c in self.cards if c.status=="done")
        failed  = sum(1 for c in self.cards if c.status=="failed")
        pending = sum(1 for c in self.cards if c.status=="waiting")
        self._stats_lbl.configure(
            text=f"System Ready.   Files: {total}  |  Done: {done}  |  Failed: {failed}  |  Pending: {pending}"
            if total else "System Ready.")
        self.p_ok.configure(text=f"✓  {done} done")
        self.p_err.configure(text=f"✗  {failed} failed")
        self.p_pend.configure(text=f"○  {pending} pending")

    # ── Generate ───────────────────────────────────────────────────────
    def start_generate(self):
        if self.ai_running:
            messagebox.showwarning("Busy","Already generating."); return
        if not self.cards:
            messagebox.showerror("No Images","Add images to the queue first."); return
        if not get_active_key_sequence(self.prefs):
            messagebox.showerror("No API Keys",
                "No active API keys found.\nOpen 'Add API Keys' to add keys."); return

        self.ai_running   = True
        self.ai_stop_flag = False
        self._gen_btn.configure(state="disabled", text="⟳  Generating…")
        self._retry_btn.pack_forget()

        targets = [c for c in self.cards if c.status in ("waiting","failed")]
        for c in targets:
            c.set_status("waiting")
            c.clear_fields()

        threading.Thread(target=self._gen_thread, args=(targets,), daemon=True).start()

    def _stop_ai(self):
        self.ai_stop_flag = True
        self.set_status("■  Stopping…", AMB)

    def _gen_thread(self, targets):
        title_c = int(self.ai_title_var.get() or 120)
        desc_c  = int(self.ai_desc_var.get() or 200)
        kw_n    = int(self.ai_kw_var.get() or 49)
        prompt  = build_prompt(title_c, desc_c, kw_n)

        style_parts = []
        if self._sil_var.get():  style_parts.append("silhouette style")
        if self._wbg_var.get():  style_parts.append("white background")
        if self._dart_var.get(): style_parts.append("digital art")
        if style_parts:
            prompt += f"\n- Style note: {', '.join(style_parts)}"

        failed_paths = []
        total = len(targets)

        for i, card in enumerate(targets):
            if self.ai_stop_flag: break
            fname = os.path.basename(card.path)
            path  = card.path

            self.after(0, lambda c=card: c.set_status("working"))
            self.after(0, lambda c=card: c.set_working_text())
            self.after(0, lambda f=fname, n=i+1, t=total:
                self.set_status(f"⟳  [{n}/{t}] {f}", BLU))

            try:
                title, desc, kw, provider = call_with_failover(
                    path, prompt, self.prefs,
                    status_cb=lambda msg: self.after(0, lambda m=msg:
                        self.set_status(f"⟳  {m}", BLU)))
                self.after(0, lambda c=card, t=title, d=desc, k=kw:
                    (c.set_result(t, d, k), c.set_status("done")))
            except Exception as e:
                err = str(e)[:100]
                failed_paths.append(path)
                self.after(0, lambda c=card, e=err: c.set_status("failed", e))

            self.after(0, self._update_stats)

        self.after(0, lambda fp=list(failed_paths): self._gen_done(fp))

    def _gen_done(self, failed_paths):
        self.ai_running = False
        self._gen_btn.configure(state="normal", text="✨  Generate Batch")

        # Move failed cards to top by re-ordering self.cards list
        if failed_paths:
            failed_cards = [c for c in self.cards if c.path in failed_paths]
            ok_cards     = [c for c in self.cards if c.path not in failed_paths]
            self.cards   = failed_cards + ok_cards
            self._regrid_cards()
            self._retry_btn.pack(side="left")

        done   = sum(1 for c in self.cards if c.status=="done")
        failed = sum(1 for c in self.cards if c.status=="failed")
        color  = GRN if failed==0 else AMB
        self.set_status(f"● Done — {done} generated · {failed} failed", color)
        self._update_stats()

    def _regen_single(self, path):
        card = next((c for c in self.cards if c.path==path), None)
        if not card: return
        if self.ai_running:
            messagebox.showwarning("Busy","Wait for current batch."); return
        card.set_status("waiting")
        card.clear_fields()
        self.ai_running   = True
        self.ai_stop_flag = False
        self._gen_btn.configure(state="disabled")
        threading.Thread(target=self._gen_thread, args=([card],), daemon=True).start()

    def _retry_failed(self):
        failed = [c for c in self.cards if c.status=="failed"]
        if not failed: return
        for c in failed:
            c.set_status("waiting")
            c.clear_fields()
        self._retry_btn.pack_forget()
        self.ai_running   = True
        self.ai_stop_flag = False
        self._gen_btn.configure(state="disabled", text="⟳  Generating…")
        threading.Thread(target=self._gen_thread, args=(failed,), daemon=True).start()

    def _export_csv(self):
        done = [c for c in self.cards if c.status=="done"]
        if not done:
            messagebox.showinfo("No Results","No successfully generated images yet."); return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            initialfile=f"metazone_ai_{ts}.csv")
        if not path: return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=["Filename","Title","Description","Keywords"])
                w.writeheader()
                w.writerows(c.get_result() for c in done)
            self.set_status(f"✓  CSV saved — {len(done)} rows", GRN)
            messagebox.showinfo("Saved", f"CSV saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════
    #  EMBED TAB
    # ══════════════════════════════════════════════════════════════════
    def _build_embed_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(parent, fg_color=BG,
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BDR, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew", padx=(14,6), pady=12)
        left.grid_columnconfigure(0, weight=1)
        self._emb_left = left

        log_outer = ctk.CTkFrame(parent, fg_color=BG2,
            corner_radius=20, border_width=1, border_color=BDR, width=210)
        log_outer.grid(row=0, column=1, sticky="nsew", padx=(0,10), pady=10)
        log_outer.grid_propagate(False)
        log_outer.grid_rowconfigure(1, weight=1)
        log_outer.grid_columnconfigure(0, weight=1)
        self._build_embed_log(log_outer)

        self._build_embed_actions()
        self._build_csv_card()
        self._build_folder_card()
        self._build_map_card()

    def _emb_card(self):
        f = ctk.CTkFrame(self._emb_left, fg_color=BG2,
            corner_radius=20, border_width=1, border_color=BDR)
        f.pack(fill="x", pady=(0,10))
        f.grid_columnconfigure(0, weight=1)
        return f

    def _emb_card_hdr(self, parent, num, title, browse_cmd=None):
        hdr = ctk.CTkFrame(parent, fg_color=BG3, corner_radius=20, height=50)
        hdr.pack(fill="x")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text=str(num),
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=GRN2, text_color="white",
            corner_radius=50, width=36, height=36
        ).grid(row=0, column=0, padx=(14,10), pady=7)
        ctk.CTkLabel(hdr, text=title,
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=TXT2, fg_color=BG3).grid(row=0, column=1, sticky="w")
        if browse_cmd:
            ctk.CTkButton(hdr, text="Browse", width=95, height=32,
                font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=GRN2, hover_color=GRN3, text_color="white",
                corner_radius=20, command=browse_cmd
            ).grid(row=0, column=2, padx=(0,12), pady=9)

    def _emb_switch(self, parent, text, var):
        return ctk.CTkSwitch(parent, text=text, variable=var,
            font=ctk.CTkFont("Segoe UI",12),
            progress_color=GRN2, button_color=TXT,
            text_color=TXT2, fg_color=BDR,
            onvalue=True, offvalue=False, width=56, height=28)

    def _build_embed_actions(self):
        row = ctk.CTkFrame(self._emb_left, fg_color=BG, corner_radius=0)
        row.pack(fill="x", pady=(0,10))
        row.grid_columnconfigure(0, weight=1)
        self.embed_btn = ctk.CTkButton(row,
            text="▶  Start Embedding",
            font=ctk.CTkFont("Segoe UI",15,"bold"),
            fg_color=GRN2, hover_color=GRN3, text_color="white",
            height=54, corner_radius=27, command=self.start_embed)
        self.embed_btn.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(row, text="↺", width=54, height=54,
            font=ctk.CTkFont("Segoe UI",20,"bold"),
            fg_color=RED2, hover_color="#3d1515", text_color=RED,
            corner_radius=27, command=self.reset_embed
        ).grid(row=0, column=1, padx=(8,0))
        ctk.CTkButton(row, text="💾  Save Log", width=130, height=54,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT2,
            corner_radius=27, command=self.export_log
        ).grid(row=0, column=2, padx=(8,0))

    def _build_csv_card(self):
        card = self._emb_card()
        self._emb_card_hdr(card, "1", "Load CSV", self.load_csv)
        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,12))
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(body, textvariable=self.csv_path_var, state="readonly",
            height=40, font=ctk.CTkFont("Segoe UI",12),
            fg_color=BG3, text_color=TXT, border_color=BDR,
            corner_radius=20).pack(fill="x", pady=(0,10))
        row = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        row.pack(fill="x"); row.grid_columnconfigure(0, weight=1)
        self.csv_badge = ctk.CTkLabel(row, text="No CSV loaded",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3, text_color=TXT3, corner_radius=20, padx=12, pady=5)
        self.csv_badge.grid(row=0, column=0, sticky="w")
        self._emb_switch(row, "Match Filename Only",
            self.match_only_var).grid(row=0, column=1, sticky="e", padx=(10,0))

    def _build_folder_card(self):
        card = self._emb_card()
        self._emb_card_hdr(card, "2", "Image Folder", self.browse_embed_folder)
        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,12))
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(body, textvariable=self.folder_path_var, state="readonly",
            height=40, font=ctk.CTkFont("Segoe UI",12),
            fg_color=BG3, text_color=TXT, border_color=BDR,
            corner_radius=20).pack(fill="x", pady=(0,10))
        row = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        row.pack(fill="x"); row.grid_columnconfigure(0, weight=1)
        self.folder_badge = ctk.CTkLabel(row, text="No folder selected",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3, text_color=TXT3, corner_radius=20, padx=12, pady=5)
        self.folder_badge.grid(row=0, column=0, sticky="w")
        self._emb_switch(row, "Include Sub-Folders",
            self.subfolder_var).grid(row=0, column=1, sticky="e", padx=(10,0))

    def _build_map_card(self):
        card = self._emb_card()
        self._emb_card_hdr(card, "3", "Map Columns")
        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(body, text="Auto-detected from column names.",
            font=ctk.CTkFont("Segoe UI",11), text_color=TXT3,
            fg_color=BG2).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,10))
        self.col_combos = {}
        fields = [("FILENAME",self.col_file_var),("TITLE",self.col_title_var),
                  ("KEYWORDS",self.col_kw_var),("DESCRIPTION",self.col_desc_var)]
        for i,(lbl,var) in enumerate(fields):
            r=(i//2)+1; c=i%2
            cell = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
            cell.grid(row=r, column=c, sticky="ew",
                      padx=(0 if c==0 else 8,0), pady=5)
            cell.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(cell, text=lbl,
                font=ctk.CTkFont("Segoe UI",10,"bold"),
                text_color=TXT3, fg_color=BG2).pack(anchor="w")
            cb = ctk.CTkComboBox(cell, variable=var, values=["(skip)"],
                state="readonly", font=ctk.CTkFont("Segoe UI",12),
                fg_color=BG3, text_color=TXT, border_color=BDR,
                button_color=GRN2, button_hover_color=GRN3,
                dropdown_fg_color=BG4, dropdown_text_color=TXT,
                dropdown_hover_color=GRN3, corner_radius=20, height=38,
                command=lambda v: self._update_match())
            cb.pack(fill="x", pady=(4,0))
            self.col_combos[lbl] = cb
        ctk.CTkFrame(body, fg_color=BDR, height=1, corner_radius=0).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(14,10))
        rm = ctk.CTkFrame(body, fg_color=BG3, corner_radius=20)
        rm.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0,4))
        rm.grid_columnconfigure(0, weight=1)
        info = ctk.CTkFrame(rm, fg_color=BG3, corner_radius=0)
        info.grid(row=0, column=0, sticky="w", padx=14, pady=12)
        ctk.CTkLabel(info, text="Remove Program Name",
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=TXT2, fg_color=BG3).pack(anchor="w")
        ctk.CTkLabel(info, text="Clears upscaler/software name from metadata",
            font=ctk.CTkFont("Segoe UI",11), text_color=TXT3,
            fg_color=BG3).pack(anchor="w")
        self._emb_switch(rm, "On", self.rm_prog_var).grid(
            row=0, column=1, padx=(0,14), pady=12)

    def _build_embed_log(self, parent):
        hdr = ctk.CTkFrame(parent, fg_color=BG3, corner_radius=20, height=44)
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,4))
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="ACTIVITY LOG",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            text_color=TXT3, fg_color=BG3).grid(row=0, column=0, sticky="w", padx=12)
        ctk.CTkButton(hdr, text="Clear", width=58, height=28,
            font=ctk.CTkFont("Segoe UI",10),
            fg_color=BG4, hover_color=BDR, text_color=TXT3,
            corner_radius=20, command=self.clear_log
        ).grid(row=0, column=1, padx=(0,8))
        self.log_text = ctk.CTkTextbox(parent,
            font=ctk.CTkFont("Consolas",11),
            fg_color=LOG_BG, text_color=TXT,
            corner_radius=20, wrap="word", state="disabled",
            scrollbar_button_color=BG3, scrollbar_button_hover_color=BDR)
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))

    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{self.ts()}   {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0","end")
        self.log_text.configure(state="disabled")

    def export_log(self):
        content = self.log_text.get("1.0","end").strip()
        if not content:
            messagebox.showinfo("Save Log","Log is empty."); return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text","*.txt")],
            initialfile=f"metazone_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if path:
            with open(path,'w',encoding='utf-8') as f: f.write(content)
            self.log(f"✓  Log saved → {os.path.basename(path)}")

    def load_csv(self):
        p = filedialog.askopenfilename(title="Select CSV",
            filetypes=[("CSV","*.csv"),("All","*.*")])
        if p: self._do_load_csv(p)

    def _do_load_csv(self, path):
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.csv_rows    = list(reader)
                self.csv_headers = list(reader.fieldnames or [])
            self.csv_path_var.set(path)
            self.csv_badge.configure(
                text=f"🗂  {len(self.csv_rows)} rows · {len(self.csv_headers)} columns",
                fg_color=GRN3, text_color=GRN)
            self.log(f"✓  CSV — {len(self.csv_rows)} rows · {os.path.basename(path)}")
            self._update_combos()
            self._update_match()
        except Exception as e:
            messagebox.showerror("CSV Error", str(e))

    def _update_combos(self):
        opts  = ["(skip)"] + self.csv_headers
        hints = {"FILENAME":["filename","file","name","image"],
                 "TITLE":["title"],"KEYWORDS":["keyword","tag","kw"],
                 "DESCRIPTION":["desc","caption","description"]}
        vmap  = {"FILENAME":self.col_file_var,"TITLE":self.col_title_var,
                 "KEYWORDS":self.col_kw_var,"DESCRIPTION":self.col_desc_var}
        for lbl,cb in self.col_combos.items():
            cb.configure(values=opts)
            g = next((c for h in hints.get(lbl,[])
                      for c in self.csv_headers if h in c.lower()), "")
            vmap[lbl].set(g or "(skip)")

    def browse_embed_folder(self):
        p = filedialog.askdirectory(title="Select image folder")
        if p:
            self.folder_path_var.set(p)
            self._update_match()
            self.log(f"✓  Folder set — {p}")

    def _update_match(self):
        folder = self.folder_path_var.get()
        col_f  = self.col_file_var.get()
        if not folder or not self.csv_rows or not col_f or col_f=="(skip)": return
        finder = find_recursive if self.subfolder_var.get() else find_file
        matched = sum(1 for row in self.csv_rows
            if finder(folder,(row.get(col_f) or "").strip(),self.match_only_var.get()))
        total = len(self.csv_rows)
        color = GRN if matched==total else AMB if matched>0 else RED
        bg    = GRN3 if matched==total else AMB2
        self.folder_badge.configure(
            text=f"📁  {matched} of {total} matched",
            fg_color=bg, text_color=color)

    def reset_embed(self):
        if self.embed_running:
            messagebox.showwarning("Busy","Wait for current job."); return
        if not messagebox.askyesno("Reset","Clear everything and start fresh?"): return
        self.csv_path_var.set(""); self.folder_path_var.set("")
        for v in [self.col_file_var,self.col_title_var,
                  self.col_kw_var,self.col_desc_var]: v.set("(skip)")
        self.csv_rows=[]; self.csv_headers=[]
        self.csv_badge.configure(text="No CSV loaded",fg_color=BG3,text_color=TXT3)
        self.folder_badge.configure(text="No folder selected",fg_color=BG3,text_color=TXT3)
        for cb in self.col_combos.values(): cb.configure(values=["(skip)"])
        self.embed_btn.configure(text="▶  Start Embedding",state="normal")
        self.clear_log()
        self.log("↺  Reset — ready")

    def start_embed(self):
        if self.embed_running: return
        et = find_exiftool()
        if not et:
            messagebox.showerror("ExifTool not found",
                "Place exiftool.exe next to this app.\nhttps://exiftool.org"); return
        if not self.csv_rows:
            messagebox.showerror("No CSV","Load a CSV first."); return
        if not self.folder_path_var.get():
            messagebox.showerror("No folder","Select image folder."); return
        fc = self.col_file_var.get()
        if not fc or fc=="(skip)":
            messagebox.showerror("Column missing","Select the filename column."); return
        self.embed_running = True
        self.embed_btn.configure(state="disabled", text="⟳  Processing…")
        threading.Thread(target=self._embed_thread, args=(et,), daemon=True).start()

    def _embed_thread(self, et):
        folder=self.folder_path_var.get(); col_f=self.col_file_var.get()
        col_t=self.col_title_var.get(); col_k=self.col_kw_var.get()
        col_d=self.col_desc_var.get(); use_sub=self.subfolder_var.get()
        use_ext=self.match_only_var.get(); rm_prog=self.rm_prog_var.get()
        total=len(self.csv_rows); ok=skipped=errors=0
        finder=find_recursive if use_sub else find_file
        self.after(0, lambda: self.log(f"▶  Batch started — {total} rows"))
        for i,row in enumerate(self.csv_rows):
            fn=(row.get(col_f) or "").strip()
            if not fn: skipped+=1; continue
            fp=finder(folder,fn,use_ext)
            if not fp:
                skipped+=1
                self.after(0,lambda f=fn:self.log(f"⚠  Not found: {f}")); continue
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
                res=subprocess.run(cmd,capture_output=True,text=True,
                                   timeout=30,creationflags=flags)
                actual=os.path.basename(fp)
                if res.returncode==0:
                    ok+=1
                    self.after(0,lambda fn=actual:self.log(f"✓  {fn}"))
                else:
                    errors+=1
                    err=(res.stderr or res.stdout or "Unknown").strip()
                    self.after(0,lambda fn=actual,e=err:self.log(f"✗  {fn} — {e}"))
            except Exception as ex:
                errors+=1
                self.after(0,lambda fn=fn,e=str(ex):self.log(f"✗  {fn} — {e}"))
            self.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                self._emb_prog(n,t,o,s,e))
        summary=f"{ok} embedded · {skipped} not found · {errors} errors"
        self.last_summary=summary
        self.after(0,lambda:(
            self.log(f"● Done — {summary}"),
            self.set_status(f"Done — {summary}",GRN),
            self.embed_btn.configure(state="normal",text="▶  Start Again"),
            setattr(self,'embed_running',False)
        ))

    def _emb_prog(self,n,t,ok,skipped,errors):
        pct=n/t if t else 0
        self.sb_prog.set(pct); self.sb_pct.configure(text=f"{int(pct*100)}%")
        self.set_status(f"Processing {n} of {t}…",BLU)
        self.p_ok.configure(text=f"✓  {ok} done")
        self.p_err.configure(text=f"✗  {errors} failed")
        self.p_pend.configure(text=f"○  {t-n} pending")

    # ── Status bar ─────────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=40)
        sb.grid(row=3, column=0, sticky="ew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(4, weight=1)

        self.p_ok = ctk.CTkLabel(sb, text="✓  0 done",
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=GRN3, text_color=GRN, corner_radius=20, padx=10, pady=3)
        self.p_ok.grid(row=0, column=0, padx=(12,5), pady=8)

        self.p_err = ctk.CTkLabel(sb, text="✗  0 failed",
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=RED2, text_color=RED, corner_radius=20, padx=10, pady=3)
        self.p_err.grid(row=0, column=1, padx=5, pady=8)

        self.p_pend = ctk.CTkLabel(sb, text="○  0 pending",
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=AMB2, text_color=AMB, corner_radius=20, padx=10, pady=3)
        self.p_pend.grid(row=0, column=2, padx=5, pady=8)

        self.sb_status = ctk.CTkLabel(sb, text="",
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=BLU, fg_color=BG4)
        self.sb_status.grid(row=0, column=3, padx=(8,0), sticky="w")

        self.sb_prog = ctk.CTkProgressBar(sb,
            progress_color=GRN, fg_color=BG3, height=5, corner_radius=3, width=90)
        self.sb_prog.grid(row=0, column=5, padx=(0,4))
        self.sb_prog.set(0)

        self.sb_pct = ctk.CTkLabel(sb, text="",
            font=ctk.CTkFont("Segoe UI",10), text_color=TXT2, fg_color=BG4)
        self.sb_pct.grid(row=0, column=6, padx=(0,8))

        self.sb_et = ctk.CTkLabel(sb, text="ExifTool · checking…",
            font=ctk.CTkFont("Segoe UI",10), text_color=TXT3, fg_color=BG4)
        self.sb_et.grid(row=0, column=7, padx=(0,14))

    def set_status(self, msg, color=None):
        self.sb_status.configure(text=msg, text_color=color or TXT3)

    def _check_et(self):
        et = find_exiftool()
        if et:
            self.sb_et.configure(text="ExifTool · ready", text_color=GRN)
        else:
            self.sb_et.configure(text="ExifTool · missing", text_color=RED)
            self.log("⚠  ExifTool not found — place exiftool.exe next to this app")

if __name__ == '__main__':
    app = App()
    app.mainloop()
