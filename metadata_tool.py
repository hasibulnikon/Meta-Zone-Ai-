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
BLU   = "#5b9ef5"
PRP   = "#8b6be8"; PRP2 = "#5c3db5"; PRP3 = "#1e1535"
CYAN  = "#3dd9c4"
LOG_BG= "#030416"

# ── AI Providers ───────────────────────────────────────────────────────
AI_PROVIDERS = {
    "OpenRouter": {
        "models": [
            "qwen/qwen2.5-vl-72b-instruct:free",
            "qwen/qwen2.5-vl-32b-instruct:free",
            "meta-llama/llama-4-maverick:free",
            "meta-llama/llama-3.2-11b-vision-instruct:free",
            "mistralai/mistral-small-3.1-24b-instruct:free",
            "moonshotai/kimi-vl-a3b-thinking:free",
        ],
        "key_url": "https://openrouter.ai/keys",
        "key_hint": "Get free key → openrouter.ai",
    },
    "Gemini": {
        "models": [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
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
        "models": ["gpt-4o", "gpt-4o-mini"],
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
    "Adobe Stock":  {"kw": 49,  "title": 150, "desc": 250},
    "Shutterstock": {"kw": 50,  "title": 200, "desc": 200},
    "Getty Images": {"kw": 50,  "title": 200, "desc": 500},
    "Freepik":      {"kw": 30,  "title": 150, "desc": 200},
    "Pond5":        {"kw": 50,  "title": 200, "desc": 500},
    "iStock":       {"kw": 50,  "title": 200, "desc": 200},
    "General":      {"kw": 49,  "title": 150, "desc": 250},
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
        for f in os.listdir(folder):
            if os.path.splitext(f)[0].lower() == base.lower():
                return os.path.join(folder, f)
    return None

def find_recursive(folder, name, match_ext):
    r = find_file(folder, name, match_ext)
    if r: return r
    for root, dirs, files in os.walk(folder):
        if root == folder: continue
        r = find_file(root, name, match_ext)
        if r: return r
    return None

# ── AI Engine ──────────────────────────────────────────────────────────
def img_to_b64(path):
    with open(path,'rb') as f: data = f.read()
    ext = os.path.splitext(path)[1].lower()
    mime = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png',
            '.gif':'image/gif','.webp':'image/webp',
            '.tiff':'image/tiff','.tif':'image/tiff'}.get(ext,'image/jpeg')
    return base64.b64encode(data).decode(), mime

def _post(url, body, headers, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode(errors='replace')
            msg = json.loads(raw).get("error",{}).get("message") or raw[:200]
        except: msg = str(e)
        raise RuntimeError(f"HTTP {e.code}: {msg}")

def call_gemini(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        {"contents":[{"parts":[{"inline_data":{"mime_type":mime,"data":b64}},{"text":prompt}]}],
         "generationConfig":{"temperature":0.4,"maxOutputTokens":800}},
        {"Content-Type":"application/json"})
    return r["candidates"][0]["content"]["parts"][0]["text"]

def call_openrouter(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://openrouter.ai/api/v1/chat/completions",
        {"model":model,"max_tokens":800,
         "messages":[{"role":"user","content":[
             {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}",
         "HTTP-Referer":"https://metazone.app","X-Title":"Meta Zone"})
    return r["choices"][0]["message"]["content"]

def call_claude(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://api.anthropic.com/v1/messages",
        {"model":model,"max_tokens":800,
         "messages":[{"role":"user","content":[
             {"type":"image","source":{"type":"base64","media_type":mime,"data":b64}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"})
    return r["content"][0]["text"]

def call_openai(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://api.openai.com/v1/chat/completions",
        {"model":model,"max_tokens":800,
         "messages":[{"role":"user","content":[
             {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    return r["choices"][0]["message"]["content"]

def call_groq(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://api.groq.com/openai/v1/chat/completions",
        {"model":model,"max_tokens":800,
         "messages":[{"role":"user","content":[
             {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    return r["choices"][0]["message"]["content"]

def call_mistral(key, model, path, prompt):
    b64, mime = img_to_b64(path)
    r = _post("https://api.mistral.ai/v1/chat/completions",
        {"model":model,"max_tokens":800,
         "messages":[{"role":"user","content":[
             {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
             {"type":"text","text":prompt}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    return r["choices"][0]["message"]["content"]

CALLERS = {
    "Gemini": call_gemini, "OpenRouter": call_openrouter,
    "Claude": call_claude, "OpenAI": call_openai,
    "Groq": call_groq, "Mistral": call_mistral,
}

def build_prompt(title_words, desc_words, kw_count):
    return (
        f"You are a professional stock image metadata writer.\n"
        f"Analyze this image carefully, then respond ONLY in this exact 3-line format — "
        f"no extra text, no markdown, no preamble:\n\n"
        f"TITLE: <concise descriptive sentence, max {title_words} words>\n"
        f"DESCRIPTION: <detailed scene description with mood and commercial context, max {desc_words} words>\n"
        f"KEYWORDS: <exactly {kw_count} comma-separated tags, most specific first>\n\n"
        f"Rules:\n"
        f"- All three lines are REQUIRED. Never skip any line.\n"
        f"- Keywords must be exactly {kw_count} unique tags, no duplicates.\n"
        f"- No brand names, no copyrighted terms.\n"
        f"- Keywords should cover: subject, action, setting, mood, color, style, demographic, use-case."
    )

def parse_response(text):
    title = desc = kw = ""
    for line in text.strip().splitlines():
        l = line.strip()
        if l.upper().startswith("TITLE:"):       title = l[6:].strip()
        elif l.upper().startswith("DESCRIPTION:"): desc  = l[12:].strip()
        elif l.upper().startswith("KEYWORDS:"):   kw    = l[9:].strip()
    return title, desc, kw

def get_active_key_sequence(prefs):
    """Return list of (provider, key, model) tuples for all active keys across all providers."""
    seq = []
    for provider, cfg in AI_PROVIDERS.items():
        keys = prefs.get("ai_keys", {}).get(provider, [])
        model = prefs.get("ai_models", {}).get(provider, cfg["models"][0])
        for k in keys:
            if k.get("active") and k.get("key"):
                seq.append((provider, k["key"], model))
    return seq

def call_with_failover(path, prompt, prefs, status_cb=None):
    """Try all active keys in order. Returns (title, desc, kw, used_provider) or raises."""
    seq = get_active_key_sequence(prefs)
    if not seq:
        raise RuntimeError("No active API keys found. Open API Key Manager to add keys.")
    last_err = ""
    for provider, key, model in seq:
        try:
            if status_cb: status_cb(f"Trying {provider}…")
            raw = CALLERS[provider](key, model, path, prompt)
            title, desc, kw = parse_response(raw)
            if title or kw:
                return title, desc, kw, provider
            raise ValueError("Empty response — no title or keywords parsed")
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
#  API KEY MANAGER POPUP
# ══════════════════════════════════════════════════════════════════════
class APIManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent, prefs, on_close=None):
        super().__init__(parent)
        self.title("API Key Manager")
        self.configure(fg_color=BG2)
        self.resizable(False, False)
        self.grab_set()
        self.prefs = prefs
        self.on_close = on_close
        self._cur_provider = list(AI_PROVIDERS.keys())[0]
        self._build()
        self._center(560, 480)
        self.protocol("WM_DELETE_WINDOW", self._done)

    def _center(self, w, h):
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width()  - w) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=46)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🔑  API Key Manager",
            font=ctk.CTkFont("Segoe UI",14,"bold"),
            text_color=TXT, fg_color=BG4).pack(side="left", padx=16, pady=10)

        # Provider tab buttons
        tab_frame = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=40)
        tab_frame.grid(row=1, column=0, sticky="ew")
        tab_frame.grid_propagate(False)

        self._tab_btns = {}
        for p in AI_PROVIDERS:
            keys = self.prefs.get("ai_keys",{}).get(p,[])
            count = sum(1 for k in keys if k.get("active"))
            label = f"{p}  {count}" if count else p
            btn = ctk.CTkButton(tab_frame, text=label, width=80, height=32,
                font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=PRP if p==self._cur_provider else BG3,
                hover_color=PRP2, text_color=TXT,
                corner_radius=8,
                command=lambda pv=p: self._switch_tab(pv))
            btn.pack(side="left", padx=(8 if p==list(AI_PROVIDERS.keys())[0] else 2, 0), pady=4)
            self._tab_btns[p] = btn

        # Body
        self._body = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0)
        self._body.grid(row=2, column=0, sticky="nsew", padx=14, pady=(10,0))
        self._body.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Footer
        ftr = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=46)
        ftr.grid(row=3, column=0, sticky="ew")
        ftr.grid_propagate(False)
        ctk.CTkButton(ftr, text="Done", width=100, height=30,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=PRP, hover_color=PRP2, text_color="white",
            corner_radius=8, command=self._done).pack(side="right", padx=14, pady=8)

        self._render_body()

    def _switch_tab(self, provider):
        self._cur_provider = provider
        for p, btn in self._tab_btns.items():
            btn.configure(fg_color=PRP if p==provider else BG3)
        self._render_body()

    def _render_body(self):
        for w in self._body.winfo_children(): w.destroy()
        p = self._cur_provider
        cfg = AI_PROVIDERS[p]
        keys = self.prefs.setdefault("ai_keys",{}).setdefault(p,[])
        models = cfg["models"]
        cur_model = self.prefs.setdefault("ai_models",{}).get(p, models[0])

        # Model
        ctk.CTkLabel(self._body, text="MODEL",
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3, fg_color=BG2).pack(anchor="w", pady=(0,4))
        model_var = StringVar(value=cur_model)
        ctk.CTkComboBox(self._body, variable=model_var, values=models,
            state="readonly", font=ctk.CTkFont("Segoe UI",11),
            fg_color=BG3, text_color=TXT, border_color=BDR,
            button_color=PRP, button_hover_color=PRP2,
            dropdown_fg_color=BG4, dropdown_text_color=TXT,
            dropdown_hover_color=PRP2, corner_radius=8, height=34,
            command=lambda v: self._save_model(p, v)).pack(fill="x", pady=(0,12))

        # Keys list label
        active_count = sum(1 for k in keys if k.get("active"))
        ctk.CTkLabel(self._body,
            text=f"STORED KEYS — {len(keys)} key{'s' if len(keys)!=1 else ''}  ·  {active_count} active",
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3, fg_color=BG2).pack(anchor="w", pady=(0,6))

        self._keys_frame = ctk.CTkScrollableFrame(self._body,
            fg_color=BG2, corner_radius=0, height=140,
            scrollbar_button_color=BG3)
        self._keys_frame.pack(fill="x", pady=(0,12))
        self._keys_frame.grid_columnconfigure(0, weight=1)
        self._render_keys(p)

        # Add new key
        ctk.CTkLabel(self._body, text="ADD NEW KEY",
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3, fg_color=BG2).pack(anchor="w", pady=(0,4))
        row = ctk.CTkFrame(self._body, fg_color=BG2, corner_radius=0)
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=1)
        new_key_var = StringVar()
        ctk.CTkEntry(row, textvariable=new_key_var,
            placeholder_text="Paste API key here...",
            font=ctk.CTkFont("Segoe UI",11), show="",
            fg_color=BG3, text_color=TXT, border_color=BDR,
            corner_radius=8, height=34).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(row, text="+ Add", width=80, height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=PRP, hover_color=PRP2, text_color="white",
            corner_radius=8,
            command=lambda: self._add_key(p, new_key_var.get().strip())
        ).grid(row=0, column=1, padx=(8,0))

        ctk.CTkLabel(self._body, text=cfg["key_hint"],
            font=ctk.CTkFont("Segoe UI",10),
            text_color=BLU, fg_color=BG2, cursor="hand2").pack(anchor="w", pady=(6,0))

    def _render_keys(self, provider):
        for w in self._keys_frame.winfo_children(): w.destroy()
        keys = self.prefs.get("ai_keys",{}).get(provider,[])
        if not keys:
            ctk.CTkLabel(self._keys_frame, text="No keys added yet.",
                font=ctk.CTkFont("Segoe UI",11), text_color=TXT3,
                fg_color=BG2).pack(pady=10)
            return
        for i, k in enumerate(keys):
            is_active = k.get("active", False)
            row_bg = GRN3 if is_active else BG3
            row_bdr = GRN2 if is_active else BDR
            row = ctk.CTkFrame(self._keys_frame,
                fg_color=row_bg, corner_radius=8,
                border_width=1, border_color=row_bdr)
            row.pack(fill="x", pady=(0,5))
            row.grid_columnconfigure(1, weight=1)

            dot_color = GRN if is_active else TXT3
            ctk.CTkLabel(row, text="●", font=ctk.CTkFont("Segoe UI",10),
                text_color=dot_color, fg_color=row_bg,
                width=20).grid(row=0, column=0, padx=(10,4), pady=8)

            key_text = k["key"]
            if len(key_text) > 32:
                key_text = key_text[:16] + "..." + key_text[-8:]
            ctk.CTkLabel(row, text=key_text,
                font=ctk.CTkFont("Consolas",10),
                text_color=TXT2, fg_color=row_bg).grid(row=0, column=1, sticky="w")

            if is_active:
                ctk.CTkButton(row, text="ACTIVE", width=72, height=24,
                    font=ctk.CTkFont("Segoe UI",9,"bold"),
                    fg_color=GRN2, hover_color=GRN2, text_color=GRN,
                    corner_radius=20,
                    command=lambda idx=i: self._toggle_key(provider, idx)
                ).grid(row=0, column=2, padx=4)
            else:
                ctk.CTkButton(row, text="Activate", width=72, height=24,
                    font=ctk.CTkFont("Segoe UI",9,"bold"),
                    fg_color=BG4, hover_color=BDR, text_color=TXT3,
                    corner_radius=20,
                    command=lambda idx=i: self._toggle_key(provider, idx)
                ).grid(row=0, column=2, padx=4)

            ctk.CTkButton(row, text="✕", width=28, height=24,
                font=ctk.CTkFont("Segoe UI",10),
                fg_color=BG4, hover_color=RED2, text_color=TXT3,
                corner_radius=8,
                command=lambda idx=i: self._del_key(provider, idx)
            ).grid(row=0, column=3, padx=(0,8))

    def _toggle_key(self, provider, idx):
        keys = self.prefs["ai_keys"][provider]
        keys[idx]["active"] = not keys[idx].get("active", False)
        save_prefs(self.prefs)
        self._update_tab_label(provider)
        self._render_keys(provider)

    def _del_key(self, provider, idx):
        self.prefs["ai_keys"][provider].pop(idx)
        save_prefs(self.prefs)
        self._update_tab_label(provider)
        self._render_keys(provider)

    def _add_key(self, provider, key):
        if not key:
            messagebox.showwarning("Empty Key", "Please paste an API key.", parent=self)
            return
        keys = self.prefs["ai_keys"][provider]
        if any(k["key"] == key for k in keys):
            messagebox.showinfo("Duplicate", "This key is already saved.", parent=self)
            return
        keys.append({"key": key, "active": True})
        save_prefs(self.prefs)
        self._update_tab_label(provider)
        self._render_body()

    def _save_model(self, provider, model):
        self.prefs.setdefault("ai_models",{})[provider] = model
        save_prefs(self.prefs)

    def _update_tab_label(self, provider):
        keys = self.prefs.get("ai_keys",{}).get(provider,[])
        count = sum(1 for k in keys if k.get("active"))
        label = f"{provider}  {count}" if count else provider
        self._tab_btns[provider].configure(text=label)

    def _done(self):
        if self.on_close: self.on_close()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  IMAGE CARD WIDGET
# ══════════════════════════════════════════════════════════════════════
class ImageCard(ctk.CTkFrame):
    """A single image card: thumbnail left, metadata fields right."""
    STATUS_COLORS = {
        "waiting":  (BG3,    TXT3,  BDR),
        "working":  (PRP3,   PRP,   PRP2),
        "done":     (GRN3,   GRN,   GRN2),
        "failed":   (RED2,   RED,   "#5a1a1a"),
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
        left = ctk.CTkFrame(self, fg_color=BG3, corner_radius=0,
                            width=150)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,0))
        left.grid_propagate(False)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Thumb area with delete btn
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

        # Filename + size
        fname = os.path.basename(self.path)
        fname_short = fname if len(fname)<=22 else fname[:20]+"…"
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

        self._title_entry = self._field(right, 0, "Ħ  Title", self._title_var, 1)
        self._desc_entry  = self._field(right, 1, "≡  Description", self._desc_var, 3)
        self._kw_entry    = self._field(right, 2, "🏷  Keywords", self._kw_var, 3, is_kw=True)

        # Footer row
        ftr = ctk.CTkFrame(right, fg_color=CARD, corner_radius=0)
        ftr.grid(row=3, column=0, sticky="ew", pady=(6,0))
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

    def _field(self, parent, row, label, var, lines, is_kw=False):
        hdr = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=0)
        hdr.grid(row=row*2, column=0, sticky="ew", pady=(0,2))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text=label,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TXT3, fg_color=CARD).grid(row=0, column=0, sticky="w")

        self_chars = ctk.CTkLabel(hdr, text="0 chars",
            font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT3, fg_color=CARD)
        self_chars.grid(row=0, column=1, sticky="e")

        copy_btn = ctk.CTkButton(hdr, text="Copy", width=48, height=20,
            font=ctk.CTkFont("Segoe UI",9),
            fg_color=BG3, hover_color=BDR, text_color=TXT3,
            corner_radius=20,
            command=lambda v=var: self._copy(v.get()))
        copy_btn.grid(row=0, column=2, padx=(6,0))

        txt_color = CYAN if is_kw else TXT
        box = ctk.CTkTextbox(parent,
            font=ctk.CTkFont("Segoe UI",11),
            fg_color=BG3, text_color=txt_color,
            border_color=BDR, border_width=1,
            corner_radius=8, wrap="word",
            height=24*lines)
        box.grid(row=row*2+1, column=0, sticky="ew", pady=(0,6))

        def _on_change(event=None):
            content = box.get("1.0","end").strip()
            var.set(content)
            self_chars.configure(text=f"{len(content)} chars")

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
        self._status_lbl.configure(text=labels.get(status,""), fg_color=bg, text_color=fg)

        if status == "failed" and fail_msg:
            self._fail_lbl.configure(text=f"⚠ {fail_msg}")
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
            "Filename": os.path.basename(self.path),
            "Title":    self._title_var.get(),
            "Description": self._desc_var.get(),
            "Keywords": self._kw_var.get(),
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
        self.cards = []          # list of ImageCard
        self.ai_running = False
        self.ai_stop_flag = False

        # Embed tab state
        self.csv_rows    = []
        self.csv_headers = []
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
        self.ai_platform_var  = StringVar(value=self.prefs.get("platform","Adobe Stock"))
        self.ai_title_var     = StringVar(value=str(self.prefs.get("title_len",70)))
        self.ai_desc_var      = StringVar(value=str(self.prefs.get("desc_len",160)))
        self.ai_kw_var        = StringVar(value=str(self.prefs.get("kw_count",49)))
        self.sidebar_visible  = True

        self._build_ui()
        self._center(1080, 820)
        self.minsize(720, 600)
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
        self.grid_rowconfigure(1, weight=1)
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
            corner_radius=8, width=30, height=30).grid(row=0, column=0, padx=(16,10), pady=11)

        ctk.CTkLabel(tb, text="Meta Zone",
            font=ctk.CTkFont("Segoe UI",18,"bold"),
            text_color=TXT, fg_color=BG4).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(tb, text="v1.0 Beta",
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=PRP, fg_color=PRP3,
            corner_radius=20, padx=8, pady=2).grid(row=0, column=2, sticky="w", padx=(8,0))

        cr = ctk.CTkFrame(tb, fg_color=BG4, corner_radius=0)
        cr.grid(row=0, column=3, padx=(0,18), sticky="e")
        ctk.CTkLabel(cr, text="All Rights Reserved By",
            font=ctk.CTkFont("Segoe UI",9), text_color=TXT3, fg_color=BG4).pack(anchor="e")
        ctk.CTkLabel(cr, text="© HASIBNIKON",
            font=ctk.CTkFont("Segoe UI",12,"bold"), text_color=TXT2, fg_color=BG4).pack(anchor="e")

    def _build_tabs(self):
        """Custom tab bar + content frame."""
        # Tab bar
        tab_bar = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=48)
        tab_bar.grid(row=1, column=0, sticky="ew")
        tab_bar.grid_propagate(False)
        tab_bar.grid_columnconfigure(2, weight=1)

        self._ai_tab_btn = ctk.CTkButton(tab_bar,
            text="✨  AI Generate",
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=PRP, hover_color=PRP2,
            text_color="white",
            width=180, height=36,
            corner_radius=20,
            command=lambda: self._switch_tab("ai"))
        self._ai_tab_btn.grid(row=0, column=0, padx=(14,4), pady=6)

        self._embed_tab_btn = ctk.CTkButton(tab_bar,
            text="📋  Embed Metadata",
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=BG3, hover_color=BDR,
            text_color=TXT3,
            width=190, height=36,
            corner_radius=20,
            command=lambda: self._switch_tab("embed"))
        self._embed_tab_btn.grid(row=0, column=1, padx=4, pady=6)

        # Content area
        self._content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._content.grid(row=2, column=0, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

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
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # Sidebar
        self._sidebar = ctk.CTkFrame(parent, fg_color=BG2,
            corner_radius=0, width=220)
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)
        self._sidebar.grid_rowconfigure(99, weight=1)

        # Main area
        self._ai_main = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        self._ai_main.grid(row=0, column=1, sticky="nsew")
        self._ai_main.grid_columnconfigure(0, weight=1)
        self._ai_main.grid_rowconfigure(1, weight=1)

        self._build_sidebar()
        self._build_ai_main()

    def _build_sidebar(self):
        sb = self._sidebar
        pad = {"padx": 12}

        # Header + collapse button
        hdr = ctk.CTkFrame(sb, fg_color=BG4, corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="SETTINGS",
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3, fg_color=BG4).grid(row=0, column=0, sticky="w", padx=12)
        ctk.CTkButton(hdr, text="‹", width=28, height=28,
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT3,
            corner_radius=8,
            command=self._toggle_sidebar).grid(row=0, column=1, padx=8)

        self._sb_inner = ctk.CTkScrollableFrame(sb, fg_color=BG2,
            scrollbar_button_color=BG3, corner_radius=0)
        self._sb_inner.pack(fill="both", expand=True)
        self._sb_inner.grid_columnconfigure(0, weight=1)

        inner = self._sb_inner

        # API Key Manager button
        ctk.CTkButton(inner, text="🔑  API Key Manager",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=PRP3, hover_color=PRP2,
            text_color=PRP, height=38,
            border_width=1, border_color=PRP2,
            corner_radius=10,
            command=self._open_api_manager).pack(fill="x", padx=12, pady=(12,0))

        # Active keys count
        self._api_active_lbl = ctk.CTkLabel(inner, text="",
            font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT3, fg_color=BG2)
        self._api_active_lbl.pack(anchor="w", padx=14, pady=(4,8))
        self._refresh_api_lbl()

        self._divider(inner)

        # Platform
        self._sb_label(inner, "PLATFORM")
        ctk.CTkComboBox(inner,
            variable=self.ai_platform_var,
            values=list(PLATFORM_RULES.keys()),
            state="readonly",
            font=ctk.CTkFont("Segoe UI",11),
            fg_color=BG3, text_color=TXT, border_color=BDR,
            button_color=PRP, button_hover_color=PRP2,
            dropdown_fg_color=BG4, dropdown_text_color=TXT,
            dropdown_hover_color=PRP2, corner_radius=8, height=34,
            command=lambda v: self._save_settings()
        ).pack(fill="x", padx=12, pady=(4,10))

        self._divider(inner)

        # Sliders
        self._sb_label(inner, "METADATA SETTINGS")
        self._title_slider = self._slider(inner, "Title Length",
            self.ai_title_var, 10, 150,
            int(self.prefs.get("title_len",70)))
        self._desc_slider  = self._slider(inner, "Description",
            self.ai_desc_var, 20, 250,
            int(self.prefs.get("desc_len",160)))
        self._kw_slider    = self._slider(inner, "Keywords Count",
            self.ai_kw_var, 5, 49,
            int(self.prefs.get("kw_count",49)))

        self._divider(inner)

        # Prompt Style
        self._sb_label(inner, "PROMPT STYLE")
        self._sil_var = BooleanVar(value=False)
        self._wbg_var = BooleanVar(value=False)
        self._dart_var= BooleanVar(value=False)
        for text, var in [("Silhouette", self._sil_var),
                          ("White Background", self._wbg_var),
                          ("Digital Art", self._dart_var)]:
            row = ctk.CTkFrame(inner, fg_color=BG2, corner_radius=0)
            row.pack(fill="x", padx=12, pady=2)
            ctk.CTkCheckBox(row, text=text, variable=var,
                font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT2, fg_color=BG2,
                checkmark_color="white",
                border_color=BDR,
                hover_color=PRP2,
                checkbox_width=15, checkbox_height=15).pack(anchor="w")

        self._divider(inner)

        # Failover note
        note = ctk.CTkFrame(inner, fg_color=BG3,
            corner_radius=8, border_width=1, border_color=BDR)
        note.pack(fill="x", padx=12, pady=(0,12))
        ctk.CTkLabel(note,
            text="⚡  Auto Failover ON\n\nOn failure, retries with\nnext active API key.\nFailed images move\nto top of queue.",
            font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT3, fg_color=BG3,
            justify="left").pack(padx=10, pady=10, anchor="w")

    def _toggle_sidebar(self):
        if self.sidebar_visible:
            self._sidebar.configure(width=0)
            self._sidebar.grid_remove()
            self.sidebar_visible = False
            self._show_btn.grid()
        else:
            self._sidebar.configure(width=220)
            self._sidebar.grid()
            self.sidebar_visible = True
            self._show_btn.grid_remove()

    def _build_ai_main(self):
        main = self._ai_main

        # Show sidebar button (hidden by default)
        self._show_btn = ctk.CTkButton(main,
            text="›", width=28, height=28,
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT3,
            corner_radius=8,
            command=self._toggle_sidebar)
        self._show_btn.grid(row=0, column=0, sticky="nw", padx=6, pady=6)
        self._show_btn.grid_remove()

        # Top action bar
        topbar = ctk.CTkFrame(main, fg_color=BG2, corner_radius=0, height=46)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)

        # Stats
        self._stats_lbl = ctk.CTkLabel(topbar,
            text="Files: 0  |  Done: 0  |  Failed: 0  |  Pending: 0",
            font=ctk.CTkFont("Segoe UI",11), text_color=TXT3, fg_color=BG2)
        self._stats_lbl.grid(row=0, column=0, sticky="w", padx=12)

        btn_frame = ctk.CTkFrame(topbar, fg_color=BG2, corner_radius=0)
        btn_frame.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkButton(btn_frame, text="🗑  Clear",
            width=90, height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT3,
            corner_radius=8,
            command=self._clear_queue).pack(side="left", padx=(0,6))

        self._gen_btn = ctk.CTkButton(btn_frame,
            text="✨  Generate Batch",
            width=160, height=34,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=PRP, hover_color=PRP2, text_color="white",
            corner_radius=8,
            command=self.start_generate)
        self._gen_btn.pack(side="left", padx=(0,6))

        self._stop_btn = ctk.CTkButton(btn_frame, text="■  Stop",
            width=90, height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=RED2, hover_color="#3d1515", text_color=RED,
            corner_radius=8,
            command=self._stop_ai)
        self._stop_btn.pack(side="left", padx=(0,6))

        self._csv_btn = ctk.CTkButton(btn_frame, text="⬇  Download CSV",
            width=140, height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=GRN2, hover_color="#1f5a26", text_color=GRN,
            corner_radius=8,
            command=self._export_csv)
        self._csv_btn.pack(side="left", padx=(0,6))

        self._retry_btn = ctk.CTkButton(btn_frame, text="↺  Retry Failed",
            width=120, height=34,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=AMB2, hover_color="#3a2e00", text_color=AMB,
            corner_radius=8,
            command=self._retry_failed)
        self._retry_btn.pack(side="left")
        self._retry_btn.pack_forget()

        # Drop zone
        self._drop_frame = ctk.CTkFrame(main,
            fg_color=CARD, corner_radius=12,
            border_width=2, border_color=BDR)
        self._drop_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(8,0))

        self._drop_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._drop_frame,
            text="🖼️  🎬  📄  🎨",
            font=ctk.CTkFont("Segoe UI",22),
            fg_color=CARD, text_color=TXT3).grid(row=0, column=0, pady=(14,4))
        ctk.CTkLabel(self._drop_frame,
            text="Drag & drop images here, or click Browse",
            font=ctk.CTkFont("Segoe UI",12),
            fg_color=CARD, text_color=TXT2).grid(row=1, column=0)
        ctk.CTkLabel(self._drop_frame,
            text="Supported: JPG · PNG · WEBP · GIF · TIFF",
            font=ctk.CTkFont("Segoe UI",10),
            fg_color=CARD, text_color=TXT3).grid(row=2, column=0, pady=(2,8))
        ctk.CTkButton(self._drop_frame, text="Browse Files",
            width=120, height=32,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=PRP3, hover_color=PRP2, text_color=PRP,
            border_width=1, border_color=PRP2,
            corner_radius=8,
            command=self._browse_images).grid(row=3, column=0, pady=(0,14))

        # Cards grid scroll area
        self._cards_outer = ctk.CTkScrollableFrame(main,
            fg_color=BG,
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BDR,
            corner_radius=0)
        self._cards_outer.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        self._cards_outer.grid_columnconfigure(0, weight=1)
        self._cards_outer.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(2, weight=1)

    # ── Sidebar helpers ────────────────────────────────────────────────
    def _sb_label(self, parent, text):
        ctk.CTkLabel(parent, text=text,
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3, fg_color=BG2).pack(anchor="w", padx=14, pady=(8,2))

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
            font=ctk.CTkFont("Segoe UI",11), text_color=TXT2,
            fg_color=BG2).grid(row=0, column=0, sticky="w")
        val_lbl = ctk.CTkLabel(top, text=str(init_val),
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=PRP, fg_color=PRP3,
            corner_radius=20, padx=7, pady=1)
        val_lbl.grid(row=0, column=1)

        sl = ctk.CTkSlider(frame, from_=from_, to=to,
            number_of_steps=to-from_,
            progress_color=PRP, fg_color=BG3,
            button_color="white", button_hover_color="#ddddff",
            height=16)
        sl.set(init_val)
        sl.pack(fill="x", pady=(4,0))

        def _update(v):
            iv = int(v)
            var.set(str(iv))
            val_lbl.configure(text=str(iv))
            self._save_settings()

        sl.configure(command=_update)
        return sl

    def _save_settings(self):
        self.prefs["platform"]  = self.ai_platform_var.get()
        self.prefs["title_len"] = int(self.ai_title_var.get() or 70)
        self.prefs["desc_len"]  = int(self.ai_desc_var.get() or 160)
        self.prefs["kw_count"]  = int(self.ai_kw_var.get() or 49)
        save_prefs(self.prefs)

    def _refresh_api_lbl(self):
        seq = get_active_key_sequence(self.prefs)
        total = len(seq)
        providers = list(dict.fromkeys(p for p,_,_ in seq))
        if total:
            txt = f"✓  {total} active key{'s' if total!=1 else ''} across {len(providers)} provider{'s' if len(providers)!=1 else ''}"
            color = GRN
        else:
            txt = "⚠  No active keys — open API Key Manager"
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
        new_paths = [p for p in paths
                     if p not in existing
                     and os.path.splitext(p)[1].lower() in IMAGE_EXTS]
        for path in new_paths:
            self._add_card(path)
        self._update_stats()

    def _add_card(self, path, prepend=False):
        idx = len(self.cards)
        row = idx // 2
        col = idx % 2
        card = ImageCard(
            self._cards_outer, path,
            on_delete=lambda c=None, p=path: self._del_card(p),
            on_regenerate=lambda p=path: self._regen_single(p))
        card.grid(row=row, column=col, sticky="ew", padx=(0 if col else 0, 4 if col==0 else 0), pady=(0,8))
        if prepend:
            self.cards.insert(0, card)
        else:
            self.cards.append(card)
        return card

    def _del_card(self, path):
        for c in self.cards:
            if c.path == path:
                c.destroy()
                self.cards.remove(c)
                break
        self._regrid_cards()
        self._update_stats()

    def _regrid_cards(self):
        for i, card in enumerate(self.cards):
            card.grid(row=i//2, column=i%2,
                sticky="ew", padx=(0,4) if i%2==0 else (4,0), pady=(0,8))

    def _clear_queue(self):
        if self.ai_running:
            messagebox.showwarning("Busy","Stop generation first."); return
        for c in self.cards: c.destroy()
        self.cards.clear()
        self._update_stats()
        self._retry_btn.pack_forget()

    def _update_stats(self):
        total   = len(self.cards)
        done    = sum(1 for c in self.cards if c.status=="done")
        failed  = sum(1 for c in self.cards if c.status=="failed")
        pending = sum(1 for c in self.cards if c.status=="waiting")

        self._stats_lbl.configure(
            text=f"Files: {total}  |  Done: {done}  |  Failed: {failed}  |  Pending: {pending}")
        self.p_ok.configure(text=f"✓  {done} done")
        self.p_err.configure(text=f"✗  {failed} failed")
        self.p_pend.configure(text=f"○  {pending} pending")

    # ── Generate ───────────────────────────────────────────────────────
    def start_generate(self):
        if self.ai_running:
            messagebox.showwarning("Busy","Already generating."); return
        if not self.cards:
            messagebox.showerror("No Images","Add images first."); return
        if not get_active_key_sequence(self.prefs):
            messagebox.showerror("No API Keys",
                "No active API keys found.\nOpen API Key Manager to add keys."); return

        self.ai_running = True
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
        title_w = int(self.ai_title_var.get() or 70)
        desc_w  = int(self.ai_desc_var.get() or 160)
        kw_n    = int(self.ai_kw_var.get() or 49)
        prompt  = build_prompt(title_w, desc_w, kw_n)

        # Extra style hints
        style_parts = []
        if self._sil_var.get():  style_parts.append("silhouette style")
        if self._wbg_var.get():  style_parts.append("white background")
        if self._dart_var.get(): style_parts.append("digital art")
        if style_parts:
            prompt += f"\n- Style note: {', '.join(style_parts)}"

        failed_cards = []
        total = len(targets)

        for i, card in enumerate(targets):
            if self.ai_stop_flag: break
            fname = os.path.basename(card.path)
            self.after(0, lambda c=card: c.set_status("working"))
            self.after(0, lambda c=card: c.set_working_text())
            self.after(0, lambda f=fname, n=i+1, t=total:
                self.set_status(f"⟳  [{n}/{t}] {f}", PRP))

            try:
                title, desc, kw, provider = call_with_failover(
                    card.path, prompt, self.prefs,
                    status_cb=lambda msg, f=fname:
                        self.after(0, lambda m=msg: self.set_status(f"⟳  {f} · {m}", PRP)))
                self.after(0, lambda c=card, t=title, d=desc, k=kw:
                    (c.set_result(t, d, k), c.set_status("done")))
            except Exception as e:
                err = str(e)[:80]
                self.after(0, lambda c=card, e=err:
                    (c.set_status("failed", e), failed_cards.append(c)))

            self.after(0, self._update_stats)

        self.after(0, lambda fc=list(failed_cards): self._gen_done(fc))

    def _gen_done(self, failed_cards):
        self.ai_running = False
        self._gen_btn.configure(state="normal", text="✨  Generate Batch")

        # Move failed cards to top
        if failed_cards:
            for c in failed_cards:
                c.destroy()
                self.cards.remove(c)
            for c in failed_cards:
                self.cards.insert(0, c)
                c = ImageCard(
                    self._cards_outer, c.path,
                    on_delete=lambda p=c.path: self._del_card(p),
                    on_regenerate=lambda p=c.path: self._regen_single(p))
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
            messagebox.showwarning("Busy","Wait for current batch to finish."); return
        card.set_status("waiting")
        card.clear_fields()
        self.ai_running = True
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
        self.ai_running = True
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
    #  EMBED TAB (unchanged from v0.5)
    # ══════════════════════════════════════════════════════════════════
    def _build_embed_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(parent, fg_color=BG,
            scrollbar_button_color=BG3, scrollbar_button_hover_color=BDR,
            corner_radius=0)
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
            corner_radius=50, width=36, height=36).grid(row=0, column=0, padx=(14,10), pady=7)
        ctk.CTkLabel(hdr, text=title,
            font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=TXT2, fg_color=BG3).grid(row=0, column=1, sticky="w")
        if browse_cmd:
            ctk.CTkButton(hdr, text="Browse", width=95, height=32,
                font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=GRN2, hover_color=GRN3, text_color="white",
                corner_radius=20, command=browse_cmd).grid(row=0, column=2, padx=(0,12), pady=9)

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
            fg_color=GRN2, hover_color=GRN3,
            text_color="white", height=54,
            corner_radius=27, command=self.start_embed)
        self.embed_btn.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(row, text="↺", width=54, height=54,
            font=ctk.CTkFont("Segoe UI",20,"bold"),
            fg_color=RED2, hover_color="#3d1515", text_color=RED,
            corner_radius=27, command=self.reset_embed).grid(row=0, column=1, padx=(8,0))
        ctk.CTkButton(row, text="💾  Save Log", width=130, height=54,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BG3, hover_color=BDR, text_color=TXT2,
            corner_radius=27, command=self.export_log).grid(row=0, column=2, padx=(8,0))

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
        self._emb_switch(row, "Match Filename Only", self.match_only_var).grid(
            row=0, column=1, sticky="e", padx=(10,0))

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
        self._emb_switch(row, "Include Sub-Folders", self.subfolder_var).grid(
            row=0, column=1, sticky="e", padx=(10,0))

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
            r = (i//2)+1; c = i%2
            cell = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
            cell.grid(row=r, column=c, sticky="ew", padx=(0 if c==0 else 8,0), pady=5)
            cell.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(cell, text=lbl, font=ctk.CTkFont("Segoe UI",10,"bold"),
                text_color=TXT3, fg_color=BG2).pack(anchor="w")
            cb = ctk.CTkComboBox(cell, variable=var, values=["(skip)"],
                state="readonly", font=ctk.CTkFont("Segoe UI",12),
                fg_color=BG3, text_color=TXT, border_color=BDR,
                button_color=GRN2, button_hover_color=GRN3,
                dropdown_fg_color=BG4, dropdown_text_color=TXT,
                dropdown_hover_color=GRN3,
                corner_radius=20, height=38,
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
            font=ctk.CTkFont("Segoe UI",11), text_color=TXT3, fg_color=BG3).pack(anchor="w")
        self._emb_switch(rm, "On", self.rm_prog_var).grid(row=0, column=1, padx=(0,14), pady=12)

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
            corner_radius=20, command=self.clear_log).grid(row=0, column=1, padx=(0,8))
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
                self.csv_rows = list(reader)
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
        opts = ["(skip)"] + self.csv_headers
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
            if finder(folder,(row.get(col_f) or "").strip(), self.match_only_var.get()))
        total = len(self.csv_rows)
        color = GRN if matched==total else AMB if matched>0 else RED
        bg    = GRN3 if matched==total else AMB2
        self.folder_badge.configure(
            text=f"📁  {matched} of {total} matched", fg_color=bg, text_color=color)

    def reset_embed(self):
        if self.embed_running:
            messagebox.showwarning("Busy","Wait for current job."); return
        if not messagebox.askyesno("Reset","Clear everything and start fresh?"): return
        self.csv_path_var.set(""); self.folder_path_var.set("")
        for v in [self.col_file_var,self.col_title_var,self.col_kw_var,self.col_desc_var]:
            v.set("(skip)")
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
        self.after(0,lambda:self.log(f"▶  Batch started — {total} rows"))
        for i,row in enumerate(self.csv_rows):
            fn=(row.get(col_f) or "").strip()
            if not fn: skipped+=1; continue
            fp=finder(folder,fn,use_ext)
            if not fp:
                skipped+=1
                self.after(0,lambda f=fn:self.log(f"⚠  Not found: {f}"))
                continue
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
        self.sb_prog.set(pct)
        self.sb_pct.configure(text=f"{int(pct*100)}%")
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
