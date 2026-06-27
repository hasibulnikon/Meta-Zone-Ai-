import customtkinter as ctk
from tkinter import filedialog, messagebox
import csv, subprocess, os, sys, threading, datetime, json, base64, urllib.request, urllib.error

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# ── Colors ─────────────────────────────────────────────────────────────
BG   = "#050724"
BG2  = "#090b1c"
BG3  = "#1b1b29"
BG4  = "#030518"
TXT  = "#e8e8f4"
TXT2 = "#9a9ab8"
TXT3 = "#4a4a68"
GRN  = "#4dbe62"
GBNB = "#369641"
GBNB2= "#2a7834"
RED  = "#f07878"
RED2 = "#1e0d0d"
AMB  = "#f5c842"
AMB2 = "#1e1800"
BLU  = "#5b9ef5"
BDR  = "#141638"
LOG_BG = "#030416"
PRP  = "#8b6be8"
PRP2 = "#5c3db5"

# ── Helpers ────────────────────────────────────────────────────────────
def find_exiftool():
    if getattr(sys,'frozen',False):
        base = sys._MEIPASS
        b = os.path.join(base,'exiftool_pkg','exiftool.exe')
        if os.path.exists(b): return b
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    for n in ['exiftool.exe','exiftool']:
        p = os.path.join(base,n)
        if os.path.exists(p): return p
    for d in os.environ.get('PATH','').split(os.pathsep):
        for n in ['exiftool.exe','exiftool']:
            p = os.path.join(d,n)
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

def prefs_path():
    base = os.path.dirname(sys.executable) if getattr(sys,'frozen',False) \
        else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base,'prefs.json')

def load_prefs():
    try:
        with open(prefs_path()) as f: return json.load(f)
    except: return {'csv':[],'folders':[]}

def save_prefs(p):
    try:
        with open(prefs_path(),'w') as f: json.dump(p,f,indent=2)
    except: pass

def add_recent(prefs, key, val, limit=5):
    lst = prefs.get(key,[])
    if val in lst: lst.remove(val)
    lst.insert(0,val); prefs[key]=lst[:limit]; save_prefs(prefs)

# ── AI Provider Configs ────────────────────────────────────────────────
AI_PROVIDERS = {
    "Gemini": {
        "models": [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
        "key_url": "https://aistudio.google.com/app/apikey",
        "key_hint": "Get free key → aistudio.google.com",
    },
    "OpenRouter": {
        "models": [
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-4-scout:free",
            "mistralai/mistral-small-3.2-24b-instruct:free",
            "google/gemma-3-27b-it:free",
        ],
        "key_url": "https://openrouter.ai/keys",
        "key_hint": "Get free key → openrouter.ai",
    },
    "Claude": {
        "models": [
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-6",
        ],
        "key_url": "https://console.anthropic.com/settings/keys",
        "key_hint": "Get key → console.anthropic.com",
    },
    "Groq": {
        "models": [
            "llama-4-scout-17b-16e-instruct",
            "llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ],
        "key_url": "https://console.groq.com/keys",
        "key_hint": "Get free key → console.groq.com",
    },
    "Mistral": {
        "models": [
            "pixtral-12b-2409",
            "mistral-large-latest",
        ],
        "key_url": "https://console.mistral.ai/api-keys/",
        "key_hint": "Get key → console.mistral.ai",
    },
}

PLATFORM_RULES = {
    "Adobe Stock":   {"kw_count": 49,  "title_max": 200, "desc_max": 200},
    "Shutterstock":  {"kw_count": 50,  "title_max": 200, "desc_max": 200},
    "Getty Images":  {"kw_count": 50,  "title_max": 200, "desc_max": 500},
    "Freepik":       {"kw_count": 30,  "title_max": 150, "desc_max": 200},
    "Pond5":         {"kw_count": 50,  "title_max": 200, "desc_max": 500},
    "iStock":        {"kw_count": 50,  "title_max": 200, "desc_max": 200},
    "Vecteezy":      {"kw_count": 50,  "title_max": 200, "desc_max": 200},
}

IMAGE_EXTS = {'.jpg','.jpeg','.png','.gif','.webp','.tiff','.tif',
              '.svg','.eps','.ai','.pdf','.mp4','.mov'}

def build_prompt(platform):
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["Adobe Stock"])
    kw = rules["kw_count"]
    tmax = rules["title_max"]
    dmax = rules["desc_max"]
    return (
        f"You are a professional stock metadata writer for {platform}. "
        f"Analyze this image carefully and generate optimized metadata.\n\n"
        f"Rules:\n"
        f"- Title: natural language sentence, max {tmax} chars, NO keyword stuffing\n"
        f"- Description: detailed, max {dmax} chars, include mood/use-case/context\n"
        f"- Keywords: exactly {kw} unique comma-separated tags, sorted by relevance (most specific first)\n"
        f"- No duplicate words, no brand names, no copyrighted terms\n"
        f"- Include: subject, action, setting, mood, demographic, color, style, use-case, conceptual keywords\n\n"
        f"Respond ONLY in this exact format (no extra text):\n"
        f"TITLE: <title here>\n"
        f"DESCRIPTION: <description here>\n"
        f"KEYWORDS: <kw1, kw2, kw3, ...>"
    )

def parse_ai_response(text):
    title = desc = kw = ""
    for line in text.strip().splitlines():
        line = line.strip()
        if line.upper().startswith("TITLE:"):
            title = line[6:].strip()
        elif line.upper().startswith("DESCRIPTION:"):
            desc = line[12:].strip()
        elif line.upper().startswith("KEYWORDS:"):
            kw = line[9:].strip()
    return title, desc, kw

def img_to_b64(path):
    with open(path, 'rb') as f:
        data = f.read()
    ext = os.path.splitext(path)[1].lower()
    mime_map = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png',  '.gif': 'image/gif',
        '.webp': 'image/webp', '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
    }
    mime = mime_map.get(ext, 'image/jpeg')
    return base64.b64encode(data).decode(), mime

def call_gemini(api_key, model, image_path, prompt):
    b64, mime = img_to_b64(image_path)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = json.dumps({
        "contents": [{"parts": [
            {"inline_data": {"mime_type": mime, "data": b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600}
    }).encode()
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    return resp["candidates"][0]["content"]["parts"][0]["text"]

def call_openrouter(api_key, model, image_path, prompt):
    b64, mime = img_to_b64(image_path)
    url = "https://openrouter.ai/api/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "max_tokens": 600,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": prompt}
        ]}]
    }).encode()
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}",
                 "HTTP-Referer": "https://metazone.app"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"]["content"]

def call_claude(api_key, model, image_path, prompt):
    b64, mime = img_to_b64(image_path)
    url = "https://api.anthropic.com/v1/messages"
    body = json.dumps({
        "model": model,
        "max_tokens": 600,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
            {"type": "text", "text": prompt}
        ]}]
    }).encode()
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": "application/json",
                 "x-api-key": api_key,
                 "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    return resp["content"][0]["text"]

def call_groq(api_key, model, image_path, prompt):
    b64, mime = img_to_b64(image_path)
    url = "https://api.groq.com/openai/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "max_tokens": 600,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": prompt}
        ]}]
    }).encode()
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"]["content"]

def call_mistral(api_key, model, image_path, prompt):
    b64, mime = img_to_b64(image_path)
    url = "https://api.mistral.ai/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "max_tokens": 600,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": prompt}
        ]}]
    }).encode()
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"]["content"]

def call_ai(provider, api_key, model, image_path, prompt):
    fn = {
        "Gemini":     call_gemini,
        "OpenRouter": call_openrouter,
        "Claude":     call_claude,
        "Groq":       call_groq,
        "Mistral":    call_mistral,
    }.get(provider)
    if not fn:
        raise ValueError(f"Unknown provider: {provider}")
    return fn(api_key, model, image_path, prompt)

# ── App ────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Meta Zone")
        self.configure(fg_color=BG)
        self.resizable(True, True)

        self.csv_rows     = []
        self.csv_headers  = []
        self.running      = False
        self.ai_running   = False
        self.last_summary = ""
        self.last_folder  = ""
        self.prefs        = load_prefs()

        self.csv_path_var    = ctk.StringVar()
        self.folder_path_var = ctk.StringVar()
        self.col_file_var    = ctk.StringVar(value="(skip)")
        self.col_title_var   = ctk.StringVar(value="(skip)")
        self.col_kw_var      = ctk.StringVar(value="(skip)")
        self.col_desc_var    = ctk.StringVar(value="(skip)")
        self.match_only_var  = ctk.BooleanVar(value=True)
        self.subfolder_var   = ctk.BooleanVar(value=True)
        self.rm_prog_var     = ctk.BooleanVar(value=True)

        # AI tab state
        self.ai_folder_var    = ctk.StringVar()
        self.ai_provider_var  = ctk.StringVar(value="Gemini")
        self.ai_model_var     = ctk.StringVar()
        self.ai_platform_var  = ctk.StringVar(value="Adobe Stock")
        self.ai_subfolder_var = ctk.BooleanVar(value=True)
        self.ai_key_var       = ctk.StringVar()
        self.ai_results       = []  # list of dicts: filename,title,desc,keywords

        self._load_icon()
        self._build_ui()
        self._center(980, 940)
        self.minsize(680, 680)
        self.after(200, self._check_et)
        self._load_ai_prefs()

    def _load_icon(self):
        self._icon_ctk = None
        base = sys._MEIPASS if getattr(sys,'frozen',False) \
            else os.path.dirname(os.path.abspath(__file__))
        for n in ['icon.png','icon.ico']:
            p = os.path.join(base,n)
            if os.path.exists(p):
                try: self.iconbitmap(p)
                except: pass
                try:
                    from PIL import Image
                    img = Image.open(p).convert("RGBA").resize((32,32))
                    self._icon_ctk = ctk.CTkImage(img, size=(32,32))
                except: pass
                break

    def _center(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def ts(self):
        return datetime.datetime.now().strftime("%H:%M:%S")

    # ── UI BUILD ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_titlebar()
        self._build_tabview()
        self._build_statusbar()

    def _build_titlebar(self):
        tb = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=64)
        tb.grid(row=0, column=0, sticky="ew")
        tb.grid_propagate(False)
        tb.grid_columnconfigure(2, weight=1)

        if self._icon_ctk:
            ctk.CTkLabel(tb, image=self._icon_ctk, text="",
                fg_color=BG4).grid(row=0, column=0, padx=(16,10), pady=16)
        else:
            ctk.CTkLabel(tb, text=" M ",
                font=ctk.CTkFont("Segoe UI", 14, "bold"),
                fg_color=GBNB, text_color="white",
                corner_radius=8).grid(row=0, column=0, padx=(16,10), pady=16)

        ctk.CTkLabel(tb, text="Meta Zone",
            font=ctk.CTkFont("Segoe UI", 20, "bold"),
            text_color=TXT, fg_color=BG4).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(tb, text="v1.0 Beta",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=PRP, fg_color=BG4).grid(
            row=0, column=2, sticky="w", padx=(8,0))

        cr = ctk.CTkFrame(tb, fg_color=BG4, corner_radius=0)
        cr.grid(row=0, column=3, padx=(0,18), pady=10, sticky="e")
        ctk.CTkLabel(cr, text="All Rights Reserved By",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=TXT3, fg_color=BG4).pack(anchor="e")
        ctk.CTkLabel(cr, text="© HASIBNIKON",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color=TXT2, fg_color=BG4).pack(anchor="e")

    def _build_tabview(self):
        self.tabview = ctk.CTkTabview(self,
            fg_color=BG,
            segmented_button_fg_color=BG4,
            segmented_button_selected_color=GBNB,
            segmented_button_selected_hover_color=GBNB2,
            segmented_button_unselected_color=BG4,
            segmented_button_unselected_hover_color=BG3,
            text_color=TXT,
            corner_radius=0,
            border_width=0)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.tabview.grid_columnconfigure(0, weight=1)

        self.tabview.add("  📋  Embed Metadata  ")
        self.tabview.add("  ✨  AI Generate  ")

        self._build_embed_tab(self.tabview.tab("  📋  Embed Metadata  "))
        self._build_ai_tab(self.tabview.tab("  ✨  AI Generate  "))

    # ── EMBED TAB ──────────────────────────────────────────────────────
    def _build_embed_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_rowconfigure(0, weight=1)

        self._left = ctk.CTkScrollableFrame(parent,
            fg_color=BG,
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BDR,
            corner_radius=0)
        self._left.grid(row=0, column=0, sticky="nsew", padx=(14,6), pady=12)
        self._left.grid_columnconfigure(0, weight=1)

        self._build_action_row()
        self._build_csv_card()
        self._build_folder_card()
        self._build_map_card()

        log_outer = ctk.CTkFrame(parent, fg_color=BG2,
            corner_radius=20, border_width=1,
            border_color=BDR, width=210)
        log_outer.grid(row=0, column=1, sticky="nsew", padx=(0,10), pady=10)
        log_outer.grid_propagate(False)
        log_outer.grid_rowconfigure(1, weight=1)
        log_outer.grid_columnconfigure(0, weight=1)
        self._build_log_panel(log_outer)

    # ── AI TAB ─────────────────────────────────────────────────────────
    def _build_ai_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_rowconfigure(0, weight=1)

        # Left scrollable
        left = ctk.CTkScrollableFrame(parent,
            fg_color=BG,
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BDR,
            corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew", padx=(14,6), pady=12)
        left.grid_columnconfigure(0, weight=1)
        self._ai_left = left

        # Right log panel
        ai_log_outer = ctk.CTkFrame(parent, fg_color=BG2,
            corner_radius=20, border_width=1,
            border_color=BDR, width=210)
        ai_log_outer.grid(row=0, column=1, sticky="nsew", padx=(0,10), pady=10)
        ai_log_outer.grid_propagate(False)
        ai_log_outer.grid_rowconfigure(1, weight=1)
        ai_log_outer.grid_columnconfigure(0, weight=1)
        self._build_ai_log_panel(ai_log_outer)

        self._build_ai_action_row()
        self._build_ai_provider_card()
        self._build_ai_folder_card()
        self._build_ai_platform_card()
        self._build_ai_results_card()

    def _build_ai_action_row(self):
        row = ctk.CTkFrame(self._ai_left, fg_color=BG, corner_radius=0)
        row.pack(fill="x", pady=(0,10))
        row.grid_columnconfigure(0, weight=1)

        self.ai_gen_btn = ctk.CTkButton(row,
            text="✨  Generate Metadata with AI",
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            fg_color=PRP, hover_color=PRP2,
            text_color="white", height=54,
            corner_radius=27, command=self.start_ai_generate)
        self.ai_gen_btn.grid(row=0, column=0, sticky="ew")

        self.ai_stop_btn = ctk.CTkButton(row,
            text="■", width=54, height=54,
            font=ctk.CTkFont("Segoe UI", 18, "bold"),
            fg_color=RED2, hover_color="#3d1515",
            text_color=RED, corner_radius=27,
            command=self.stop_ai)
        self.ai_stop_btn.grid(row=0, column=1, padx=(8,0))

        self.ai_csv_btn = ctk.CTkButton(row,
            text="💾  Save CSV", width=130, height=54,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=BG3, hover_color=BDR,
            text_color=TXT2, corner_radius=27,
            command=self.ai_export_csv)
        self.ai_csv_btn.grid(row=0, column=2, padx=(8,0))

    def _build_ai_provider_card(self):
        card = self._ai_card_frame()
        self._ai_card_header(card, "1", "AI Provider & API Key")

        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,14))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        # Provider selector
        prov_f = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        prov_f.grid(row=0, column=0, sticky="ew", padx=(0,8), pady=(0,10))
        prov_f.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(prov_f, text="PROVIDER",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=TXT3, fg_color=BG2).pack(anchor="w")
        self.ai_prov_combo = ctk.CTkComboBox(prov_f,
            variable=self.ai_provider_var,
            values=list(AI_PROVIDERS.keys()),
            state="readonly",
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG3, text_color=TXT, border_color=BDR,
            button_color=PRP, button_hover_color=PRP2,
            dropdown_fg_color=BG4, dropdown_text_color=TXT,
            dropdown_hover_color=PRP2,
            corner_radius=20, height=38,
            command=self._on_provider_change)
        self.ai_prov_combo.pack(fill="x", pady=(4,0))

        # Model selector
        model_f = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        model_f.grid(row=0, column=1, sticky="ew", pady=(0,10))
        model_f.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(model_f, text="MODEL",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=TXT3, fg_color=BG2).pack(anchor="w")
        self.ai_model_combo = ctk.CTkComboBox(model_f,
            variable=self.ai_model_var,
            values=AI_PROVIDERS["Gemini"]["models"],
            state="readonly",
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color=BG3, text_color=TXT, border_color=BDR,
            button_color=PRP, button_hover_color=PRP2,
            dropdown_fg_color=BG4, dropdown_text_color=TXT,
            dropdown_hover_color=PRP2,
            corner_radius=20, height=38)
        self.ai_model_combo.pack(fill="x", pady=(4,0))
        self.ai_model_var.set(AI_PROVIDERS["Gemini"]["models"][0])

        # API Key
        key_f = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        key_f.grid(row=1, column=0, columnspan=2, sticky="ew")
        key_f.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(key_f, text="API KEY",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=TXT3, fg_color=BG2).pack(anchor="w")

        key_row = ctk.CTkFrame(key_f, fg_color=BG2, corner_radius=0)
        key_row.pack(fill="x", pady=(4,0))
        key_row.grid_columnconfigure(0, weight=1)

        self.ai_key_entry = ctk.CTkEntry(key_row,
            textvariable=self.ai_key_var,
            show="•", height=38,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG3, text_color=TXT,
            border_color=BDR, corner_radius=20,
            placeholder_text="Paste your API key here...")
        self.ai_key_entry.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(key_row, text="Save",
            width=80, height=38,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=GBNB, hover_color=GBNB2,
            text_color="white", corner_radius=20,
            command=self._save_ai_key).grid(row=0, column=1, padx=(8,0))

        self.ai_key_hint = ctk.CTkLabel(key_f,
            text=AI_PROVIDERS["Gemini"]["key_hint"],
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=BLU, fg_color=BG2, cursor="hand2")
        self.ai_key_hint.pack(anchor="w", pady=(6,0))
        self.ai_key_hint.bind("<Button-1>", self._open_key_url)

    def _build_ai_folder_card(self):
        card = self._ai_card_frame()
        self._ai_card_header(card, "2", "Image Folder", self.ai_browse_folder)

        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,12))
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(body,
            textvariable=self.ai_folder_var,
            state="readonly", height=40,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG3, text_color=TXT,
            border_color=BDR, corner_radius=20).pack(fill="x", pady=(0,10))

        row = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=1)

        self.ai_folder_badge = ctk.CTkLabel(row,
            text="No folder selected",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=BG3, text_color=TXT3,
            corner_radius=20, padx=12, pady=5)
        self.ai_folder_badge.grid(row=0, column=0, sticky="w")

        self._ai_switch(row, "Include Sub-Folders",
            self.ai_subfolder_var).grid(
            row=0, column=1, sticky="e", padx=(10,0))

    def _build_ai_platform_card(self):
        card = self._ai_card_frame()
        self._ai_card_header(card, "3", "Target Platform")

        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,12))
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(body, text="Metadata rules are auto-applied for each platform.",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TXT3, fg_color=BG2).pack(anchor="w", pady=(0,10))

        plat_row = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        plat_row.pack(fill="x")
        plat_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(plat_row, text="PLATFORM",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=TXT3, fg_color=BG2).grid(row=0, column=0, sticky="w")

        self.ai_plat_combo = ctk.CTkComboBox(plat_row,
            variable=self.ai_platform_var,
            values=list(PLATFORM_RULES.keys()),
            state="readonly",
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG3, text_color=TXT, border_color=BDR,
            button_color=PRP, button_hover_color=PRP2,
            dropdown_fg_color=BG4, dropdown_text_color=TXT,
            dropdown_hover_color=PRP2,
            corner_radius=20, height=38)
        self.ai_plat_combo.grid(row=1, column=0, sticky="ew", pady=(4,0))

        # Platform info badge
        info_row = ctk.CTkFrame(body, fg_color=BG3, corner_radius=12)
        info_row.pack(fill="x", pady=(12,0))
        info_row.grid_columnconfigure(0, weight=1)
        info_row.grid_columnconfigure(1, weight=1)
        info_row.grid_columnconfigure(2, weight=1)

        self.plat_kw_lbl = ctk.CTkLabel(info_row,
            text="49 keywords",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=PRP, fg_color=BG3)
        self.plat_kw_lbl.grid(row=0, column=0, padx=10, pady=8)

        ctk.CTkLabel(info_row, text="|",
            text_color=TXT3, fg_color=BG3).grid(row=0, column=1)

        self.plat_title_lbl = ctk.CTkLabel(info_row,
            text="Title ≤ 200 chars",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TXT2, fg_color=BG3)
        self.plat_title_lbl.grid(row=0, column=2, padx=10, pady=8)

        self.ai_plat_combo.configure(command=self._on_platform_change)

    def _build_ai_results_card(self):
        card = self._ai_card_frame()
        self._ai_card_header(card, "4", "Generated Results")

        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,12))
        body.grid_columnconfigure(0, weight=1)

        # Progress bar
        prog_row = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        prog_row.pack(fill="x", pady=(0,10))
        prog_row.grid_columnconfigure(0, weight=1)

        self.ai_prog = ctk.CTkProgressBar(prog_row,
            progress_color=PRP, fg_color=BG3,
            height=7, corner_radius=4)
        self.ai_prog.grid(row=0, column=0, sticky="ew")
        self.ai_prog.set(0)

        self.ai_prog_lbl = ctk.CTkLabel(prog_row, text="",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TXT2, fg_color=BG2)
        self.ai_prog_lbl.grid(row=0, column=1, padx=(10,0))

        # Results textbox (scrollable preview)
        self.ai_results_box = ctk.CTkTextbox(body,
            font=ctk.CTkFont("Consolas", 10),
            fg_color=LOG_BG, text_color=TXT,
            corner_radius=16, wrap="word",
            state="disabled",
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BDR,
            height=220)
        self.ai_results_box.pack(fill="x")

        # Stats row
        stats = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        stats.pack(fill="x", pady=(10,0))

        self.ai_stat_ok = ctk.CTkLabel(stats,
            text="✓  0 generated",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color="#0d2018", text_color=GRN,
            corner_radius=20, padx=12, pady=4)
        self.ai_stat_ok.pack(side="left", padx=(0,8))

        self.ai_stat_err = ctk.CTkLabel(stats,
            text="✗  0 errors",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=RED2, text_color=RED,
            corner_radius=20, padx=12, pady=4)
        self.ai_stat_err.pack(side="left")

        # Send to Embed button
        ctk.CTkButton(body,
            text="📋  Send CSV to Embed Tab",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=GBNB, hover_color=GBNB2,
            text_color="white", height=42,
            corner_radius=20, command=self.ai_send_to_embed).pack(
            fill="x", pady=(14,0))

    def _ai_card_frame(self):
        f = ctk.CTkFrame(self._ai_left, fg_color=BG2,
            corner_radius=20, border_width=1, border_color=BDR)
        f.pack(fill="x", pady=(0,10))
        f.grid_columnconfigure(0, weight=1)
        return f

    def _ai_card_header(self, parent, num, title, browse_cmd=None):
        hdr = ctk.CTkFrame(parent, fg_color=BG3, corner_radius=20, height=50)
        hdr.pack(fill="x")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text=str(num),
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=PRP, text_color="white",
            corner_radius=50, width=36, height=36).grid(
            row=0, column=0, padx=(14,10), pady=7)

        ctk.CTkLabel(hdr, text=title,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=TXT2, fg_color=BG3).grid(
            row=0, column=1, sticky="w")

        if browse_cmd:
            ctk.CTkButton(hdr, text="Browse",
                width=95, height=32,
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                fg_color=PRP, hover_color=PRP2,
                text_color="white", corner_radius=20,
                command=browse_cmd).grid(
                row=0, column=2, padx=(0,12), pady=9)

    def _ai_switch(self, parent, text, var):
        return ctk.CTkSwitch(parent,
            text=text, variable=var,
            font=ctk.CTkFont("Segoe UI", 12),
            progress_color=PRP,
            button_color=TXT,
            button_hover_color="#ccccff",
            text_color=TXT2, fg_color=BDR,
            onvalue=True, offvalue=False,
            width=56, height=28)

    def _build_ai_log_panel(self, parent):
        hdr = ctk.CTkFrame(parent, fg_color=BG3,
            corner_radius=20, height=44)
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,4))
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="AI LOG",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=TXT3, fg_color=BG3).grid(
            row=0, column=0, sticky="w", padx=12)

        ctk.CTkButton(hdr, text="Clear",
            width=58, height=28,
            font=ctk.CTkFont("Segoe UI", 10),
            fg_color=BG4, hover_color=BDR,
            text_color=TXT3, corner_radius=20,
            command=self.clear_ai_log).grid(
            row=0, column=1, padx=(0,8))

        self.ai_log_text = ctk.CTkTextbox(parent,
            font=ctk.CTkFont("Consolas", 11),
            fg_color=LOG_BG, text_color=TXT,
            corner_radius=20, wrap="word",
            state="disabled",
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BDR)
        self.ai_log_text.grid(row=1, column=0, sticky="nsew",
            padx=8, pady=(0,8))

    def ai_log(self, msg):
        self.ai_log_text.configure(state="normal")
        self.ai_log_text.insert("end", f"{self.ts()}   {msg}\n")
        self.ai_log_text.see("end")
        self.ai_log_text.configure(state="disabled")

    def clear_ai_log(self):
        self.ai_log_text.configure(state="normal")
        self.ai_log_text.delete("1.0", "end")
        self.ai_log_text.configure(state="disabled")

    def ai_results_log(self, msg):
        self.ai_results_box.configure(state="normal")
        self.ai_results_box.insert("end", msg + "\n")
        self.ai_results_box.see("end")
        self.ai_results_box.configure(state="disabled")

    def clear_ai_results(self):
        self.ai_results_box.configure(state="normal")
        self.ai_results_box.delete("1.0", "end")
        self.ai_results_box.configure(state="disabled")

    # ── AI Provider logic ──────────────────────────────────────────────
    def _on_provider_change(self, value):
        cfg = AI_PROVIDERS.get(value, {})
        models = cfg.get("models", [])
        self.ai_model_combo.configure(values=models)
        self.ai_model_var.set(models[0] if models else "")
        hint = cfg.get("key_hint", "")
        self.ai_key_hint.configure(text=hint)
        # Load saved key for this provider
        saved = self.prefs.get("ai_keys", {}).get(value, "")
        self.ai_key_var.set(saved)

    def _on_platform_change(self, value):
        rules = PLATFORM_RULES.get(value, {})
        self.plat_kw_lbl.configure(text=f"{rules.get('kw_count',49)} keywords")
        self.plat_title_lbl.configure(text=f"Title ≤ {rules.get('title_max',200)} chars")

    def _open_key_url(self, event=None):
        import webbrowser
        provider = self.ai_provider_var.get()
        url = AI_PROVIDERS.get(provider, {}).get("key_url", "")
        if url:
            webbrowser.open(url)

    def _save_ai_key(self):
        provider = self.ai_provider_var.get()
        key = self.ai_key_var.get().strip()
        if not key:
            messagebox.showwarning("API Key", "Please paste an API key first.")
            return
        if "ai_keys" not in self.prefs:
            self.prefs["ai_keys"] = {}
        self.prefs["ai_keys"][provider] = key
        save_prefs(self.prefs)
        self.ai_log(f"✓  API key saved for {provider}")

    def _load_ai_prefs(self):
        keys = self.prefs.get("ai_keys", {})
        provider = self.ai_provider_var.get()
        saved = keys.get(provider, "")
        if saved:
            self.ai_key_var.set(saved)

    # ── AI Folder ──────────────────────────────────────────────────────
    def ai_browse_folder(self):
        p = filedialog.askdirectory(title="Select image folder for AI generation")
        if not p: return
        self.ai_folder_var.set(p)
        exts = IMAGE_EXTS
        use_sub = self.ai_subfolder_var.get()
        files = []
        if use_sub:
            for root, dirs, fnames in os.walk(p):
                for fn in fnames:
                    if os.path.splitext(fn)[1].lower() in exts:
                        files.append(os.path.join(root, fn))
        else:
            for fn in os.listdir(p):
                if os.path.splitext(fn)[1].lower() in exts:
                    files.append(os.path.join(p, fn))
        count = len(files)
        color = GRN if count > 0 else RED
        self.ai_folder_badge.configure(
            text=f"📁  {count} images found",
            fg_color=GBNB2 if count > 0 else RED2,
            text_color=color)
        self.ai_log(f"✓  Folder set — {count} images found")

    def _collect_images(self):
        folder = self.ai_folder_var.get()
        if not folder: return []
        use_sub = self.ai_subfolder_var.get()
        files = []
        if use_sub:
            for root, dirs, fnames in os.walk(folder):
                for fn in fnames:
                    if os.path.splitext(fn)[1].lower() in IMAGE_EXTS:
                        files.append(os.path.join(root, fn))
        else:
            for fn in os.listdir(folder):
                if os.path.splitext(fn)[1].lower() in IMAGE_EXTS:
                    files.append(os.path.join(folder, fn))
        return sorted(files)

    # ── AI Generate ────────────────────────────────────────────────────
    def start_ai_generate(self):
        if self.ai_running:
            messagebox.showwarning("Busy", "AI generation already running.")
            return
        provider = self.ai_provider_var.get()
        model    = self.ai_model_var.get()
        api_key  = self.ai_key_var.get().strip()
        platform = self.ai_platform_var.get()
        folder   = self.ai_folder_var.get()

        if not api_key:
            messagebox.showerror("API Key Missing",
                f"Please paste your {provider} API key and click Save.")
            return
        if not folder:
            messagebox.showerror("No Folder",
                "Please select an image folder first.")
            return

        images = self._collect_images()
        if not images:
            messagebox.showerror("No Images",
                "No supported image files found in the selected folder.")
            return

        # Warn about non-vision models
        no_vision = {"groq": ["llama-4"]}
        if provider == "Groq":
            messagebox.showinfo("Note",
                "Groq's Llama 4 models have limited vision support.\n"
                "Gemini or OpenRouter free models are recommended for best results.")

        self.ai_running = True
        self.ai_stop_flag = False
        self.ai_results = []
        self.clear_ai_results()
        self.ai_gen_btn.configure(state="disabled", text="⟳  Generating...")
        self.ai_prog.set(0)
        self.ai_prog_lbl.configure(text="")
        self.ai_stat_ok.configure(text="✓  0 generated")
        self.ai_stat_err.configure(text="✗  0 errors")
        self.ai_log(f"▶  Starting — {len(images)} images · {provider} · {platform}")

        threading.Thread(
            target=self._ai_thread,
            args=(provider, model, api_key, platform, images),
            daemon=True).start()

    def stop_ai(self):
        if self.ai_running:
            self.ai_stop_flag = True
            self.ai_log("■  Stop requested...")

    def _ai_thread(self, provider, model, api_key, platform, images):
        prompt = build_prompt(platform)
        total  = len(images)
        ok = errors = 0

        for i, path in enumerate(images):
            if getattr(self, 'ai_stop_flag', False):
                self.after(0, lambda: self.ai_log("■  Stopped by user"))
                break

            fname = os.path.basename(path)
            self.after(0, lambda n=i+1, t=total, f=fname:
                self.ai_log(f"⟳  [{n}/{t}] {f}"))

            try:
                # Skip non-vision-compatible formats by sending a note
                ext = os.path.splitext(path)[1].lower()
                if ext in {'.eps', '.ai', '.svg', '.pdf', '.mp4', '.mov'}:
                    self.after(0, lambda f=fname:
                        self.ai_log(f"⚠  {f} — vector/video, skipped (use JPG preview)"))
                    errors += 1
                else:
                    raw = call_ai(provider, api_key, model, path, prompt)
                    title, desc, kw = parse_ai_response(raw)
                    if not title and not kw:
                        raise ValueError("Could not parse AI response")

                    result = {
                        "Filename": fname,
                        "Title": title,
                        "Description": desc,
                        "Keywords": kw,
                    }
                    self.ai_results.append(result)
                    ok += 1

                    preview = f"── {fname}\n   T: {title[:80]}...\n   K: {kw[:80]}...\n"
                    self.after(0, lambda p=preview: self.ai_results_log(p))
                    self.after(0, lambda f=fname:
                        self.ai_log(f"✓  {f}"))

            except Exception as e:
                errors += 1
                err_msg = str(e)
                if len(err_msg) > 80:
                    err_msg = err_msg[:80] + "..."
                self.after(0, lambda f=fname, e=err_msg:
                    self.ai_log(f"✗  {f} — {e}"))

            pct = (i + 1) / total
            o, er = ok, errors
            self.after(0, lambda p=pct, n=i+1, t=total, o=o, er=er:
                self._ai_prog_update(p, n, t, o, er))

        final_ok, final_err = ok, errors
        self.after(0, lambda o=final_ok, e=final_err: self._ai_done(o, e))

    def _ai_prog_update(self, pct, n, total, ok, errors):
        self.ai_prog.set(pct)
        self.ai_prog_lbl.configure(text=f"{int(pct*100)}%  ({n}/{total})")
        self.ai_stat_ok.configure(text=f"✓  {ok} generated")
        self.ai_stat_err.configure(text=f"✗  {errors} errors")

    def _ai_done(self, ok, errors):
        self.ai_running = False
        self.ai_gen_btn.configure(state="normal", text="✨  Generate Metadata with AI")
        summary = f"{ok} generated · {errors} errors"
        self.ai_log(f"● Done — {summary}")
        self.set_status(f"AI Done — {summary}", PRP)
        if ok > 0:
            self.ai_log(f"💾  Click 'Save CSV' or 'Send to Embed Tab'")

    # ── AI Export ──────────────────────────────────────────────────────
    def ai_export_csv(self):
        if not self.ai_results:
            messagebox.showinfo("No Results", "Generate metadata first.")
            return
        platform = self.ai_platform_var.get()
        safe_plat = platform.replace(" ", "_").replace("/", "-")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"metazone_ai_{safe_plat}_{ts}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=default_name)
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f,
                    fieldnames=["Filename", "Title", "Description", "Keywords"])
                writer.writeheader()
                writer.writerows(self.ai_results)
            self.ai_log(f"✓  CSV saved → {os.path.basename(path)}")
            messagebox.showinfo("Saved", f"CSV saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def ai_send_to_embed(self):
        if not self.ai_results:
            messagebox.showinfo("No Results", "Generate metadata first.")
            return
        # Write temp CSV and auto-load into embed tab
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False,
            encoding='utf-8-sig', newline='')
        writer = csv.DictWriter(tmp,
            fieldnames=["Filename", "Title", "Description", "Keywords"])
        writer.writeheader()
        writer.writerows(self.ai_results)
        tmp.close()
        self._do_load_csv(tmp.name)
        self.tabview.set("  📋  Embed Metadata  ")
        self.log(f"✓  AI results loaded — {len(self.ai_results)} rows")
        self.ai_log(f"✓  Sent to Embed tab — {len(self.ai_results)} rows")

    # ── EMBED TAB UI (same as v0.5) ────────────────────────────────────
    def _build_action_row(self):
        row = ctk.CTkFrame(self._left, fg_color=BG, corner_radius=0)
        row.pack(fill="x", pady=(0,10))
        row.grid_columnconfigure(0, weight=1)

        self.embed_btn = ctk.CTkButton(row,
            text="▶  Start Embedding",
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            fg_color=GBNB, hover_color=GBNB2,
            text_color="white", height=54,
            corner_radius=27, command=self.start_embed)
        self.embed_btn.grid(row=0, column=0, sticky="ew")

        self.reset_btn = ctk.CTkButton(row,
            text="↺", width=54, height=54,
            font=ctk.CTkFont("Segoe UI", 20, "bold"),
            fg_color=RED2, hover_color="#3d1515",
            text_color=RED, corner_radius=27,
            command=self.reset_all)
        self.reset_btn.grid(row=0, column=1, padx=(8,0))

        self.save_log_btn = ctk.CTkButton(row,
            text="💾  Save Log", width=130, height=54,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=BG3, hover_color=BDR,
            text_color=TXT2, corner_radius=27,
            command=self.export_log)
        self.save_log_btn.grid(row=0, column=2, padx=(8,0))

    def _card_frame(self):
        f = ctk.CTkFrame(self._left, fg_color=BG2,
            corner_radius=20, border_width=1, border_color=BDR)
        f.pack(fill="x", pady=(0,10))
        f.grid_columnconfigure(0, weight=1)
        return f

    def _card_header(self, parent, num, title, browse_cmd=None):
        hdr = ctk.CTkFrame(parent, fg_color=BG3, corner_radius=20, height=50)
        hdr.pack(fill="x")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text=str(num),
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=GBNB, text_color="white",
            corner_radius=50, width=36, height=36).grid(
            row=0, column=0, padx=(14,10), pady=7)

        ctk.CTkLabel(hdr, text=title,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=TXT2, fg_color=BG3).grid(
            row=0, column=1, sticky="w")

        if browse_cmd:
            ctk.CTkButton(hdr, text="Browse",
                width=95, height=32,
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                fg_color=GBNB, hover_color=GBNB2,
                text_color="white", corner_radius=20,
                command=browse_cmd).grid(
                row=0, column=2, padx=(0,12), pady=9)

    def _switch(self, parent, text, var):
        return ctk.CTkSwitch(parent,
            text=text, variable=var,
            font=ctk.CTkFont("Segoe UI", 12),
            progress_color=GBNB,
            button_color=TXT,
            button_hover_color="#ccccff",
            text_color=GRN, fg_color=BDR,
            onvalue=True, offvalue=False,
            width=56, height=28)

    def _build_csv_card(self):
        card = self._card_frame()
        self._card_header(card, "1", "Load CSV", self.load_csv)
        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,12))
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(body,
            textvariable=self.csv_path_var,
            state="readonly", height=40,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG3, text_color=TXT,
            border_color=BDR, corner_radius=20).pack(fill="x", pady=(0,10))
        row = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=1)
        self.csv_badge = ctk.CTkLabel(row,
            text="No CSV loaded",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=BG3, text_color=TXT3,
            corner_radius=20, padx=12, pady=5)
        self.csv_badge.grid(row=0, column=0, sticky="w")
        self._switch(row, "Match Filename Only",
            self.match_only_var).grid(row=0, column=1, sticky="e", padx=(10,0))

    def _build_folder_card(self):
        card = self._card_frame()
        self._card_header(card, "2", "Image Folder", self.browse_folder)
        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,12))
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(body,
            textvariable=self.folder_path_var,
            state="readonly", height=40,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG3, text_color=TXT,
            border_color=BDR, corner_radius=20).pack(fill="x", pady=(0,10))
        row = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=1)
        self.folder_badge = ctk.CTkLabel(row,
            text="No folder selected",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=BG3, text_color=TXT3,
            corner_radius=20, padx=12, pady=5)
        self.folder_badge.grid(row=0, column=0, sticky="w")
        self._switch(row, "Include Sub-Folders",
            self.subfolder_var).grid(row=0, column=1, sticky="e", padx=(10,0))

    def _build_map_card(self):
        card = self._card_frame()
        self._card_header(card, "3", "Map Columns")
        body = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
        body.pack(fill="x", padx=14, pady=(10,12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(body,
            text="Auto-detected from column names.",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TXT3, fg_color=BG2).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0,10))
        self.col_combos = {}
        fields = [
            ("FILENAME", self.col_file_var),
            ("TITLE",    self.col_title_var),
            ("KEYWORDS", self.col_kw_var),
            ("DESCRIPTION", self.col_desc_var),
        ]
        for i, (lbl, var) in enumerate(fields):
            r = (i // 2) + 1
            c = i % 2
            cell = ctk.CTkFrame(body, fg_color=BG2, corner_radius=0)
            cell.grid(row=r, column=c, sticky="ew",
                padx=(0 if c==0 else 8, 0), pady=5)
            cell.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(cell, text=lbl,
                font=ctk.CTkFont("Segoe UI", 10, "bold"),
                text_color=TXT3, fg_color=BG2).pack(anchor="w")
            cb = ctk.CTkComboBox(cell,
                variable=var, values=["(skip)"], state="readonly",
                font=ctk.CTkFont("Segoe UI", 12),
                fg_color=BG3, text_color=TXT, border_color=BDR,
                button_color=GBNB, button_hover_color=GBNB2,
                dropdown_fg_color=BG4, dropdown_text_color=TXT,
                dropdown_hover_color=GBNB2,
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
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=TXT2, fg_color=BG3).pack(anchor="w")
        ctk.CTkLabel(info,
            text="Clears upscaler/software name from metadata",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TXT3, fg_color=BG3).pack(anchor="w")
        self._switch(rm, "On", self.rm_prog_var).grid(
            row=0, column=1, padx=(0,14), pady=12)

    def _build_log_panel(self, parent):
        hdr = ctk.CTkFrame(parent, fg_color=BG3, corner_radius=20, height=44)
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,4))
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="ACTIVITY LOG",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=TXT3, fg_color=BG3).grid(
            row=0, column=0, sticky="w", padx=12)
        ctk.CTkButton(hdr, text="Clear",
            width=58, height=28,
            font=ctk.CTkFont("Segoe UI", 10),
            fg_color=BG4, hover_color=BDR,
            text_color=TXT3, corner_radius=20,
            command=self.clear_log).grid(row=0, column=1, padx=(0,8))
        self.log_text = ctk.CTkTextbox(parent,
            font=ctk.CTkFont("Consolas", 11),
            fg_color=LOG_BG, text_color=TXT,
            corner_radius=20, wrap="word", state="disabled",
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BDR)
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))

    def _build_statusbar(self):
        sb = ctk.CTkFrame(self, fg_color=BG4, corner_radius=0, height=46)
        sb.grid(row=2, column=0, sticky="ew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(4, weight=1)
        self.p_ok = ctk.CTkLabel(sb,
            text="✓  0 embedded",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color="#0d2018", text_color=GRN,
            corner_radius=20, padx=12, pady=4)
        self.p_ok.grid(row=0, column=0, padx=(14,6), pady=10)
        self.p_warn = ctk.CTkLabel(sb,
            text="⚠  0 not found",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=AMB2, text_color=AMB,
            corner_radius=20, padx=12, pady=4)
        self.p_warn.grid(row=0, column=1, padx=6, pady=10)
        self.p_err = ctk.CTkLabel(sb,
            text="✗  0 errors",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=RED2, text_color=RED,
            corner_radius=20, padx=12, pady=4)
        self.p_err.grid(row=0, column=2, padx=6, pady=10)
        self.sb_status = ctk.CTkLabel(sb, text="",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=BLU, fg_color=BG4)
        self.sb_status.grid(row=0, column=3, padx=(10,0), sticky="w")
        self.sb_prog = ctk.CTkProgressBar(sb,
            progress_color=GRN, fg_color=BG3,
            height=7, corner_radius=4, width=110)
        self.sb_prog.grid(row=0, column=5, padx=(0,6))
        self.sb_prog.set(0)
        self.sb_pct = ctk.CTkLabel(sb, text="",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TXT2, fg_color=BG4)
        self.sb_pct.grid(row=0, column=6, padx=(0,10))
        self.sb_et = ctk.CTkLabel(sb,
            text="ExifTool · checking…",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TXT3, fg_color=BG4)
        self.sb_et.grid(row=0, column=7, padx=(0,16))

    # ── Log (embed tab) ────────────────────────────────────────────────
    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{self.ts()}   {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def export_log(self):
        content = self.log_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Save Log", "Log is empty.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text","*.txt")],
            initialfile=f"metazone_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if path:
            with open(path,'w',encoding='utf-8') as f: f.write(content)
            self.log(f"✓  Log saved → {os.path.basename(path)}")

    def set_status(self, msg, color=None):
        self.sb_status.configure(text=msg, text_color=color or TXT3)

    def _check_et(self):
        et = find_exiftool()
        if et:
            self.log("✓  ExifTool ready")
            self.sb_et.configure(text="ExifTool · ready", text_color=GRN)
        else:
            self.log("⚠  ExifTool not found — place exiftool.exe next to this app")
            self.sb_et.configure(text="ExifTool · missing", text_color=RED)

    # ── CSV (embed tab) ────────────────────────────────────────────────
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
                fg_color=GBNB2, text_color=GRN)
            self.log(f"✓  CSV — {len(self.csv_rows)} rows · {os.path.basename(path)}")
            self.set_status(f"CSV: {len(self.csv_rows)} rows", GRN)
            add_recent(self.prefs,'csv',path)
            self._update_combos()
            self._update_match()
        except Exception as e:
            messagebox.showerror("CSV Error", str(e))

    def _update_combos(self):
        opts = ["(skip)"] + self.csv_headers
        hints = {
            "FILENAME":    ["filename","file","name","image"],
            "TITLE":       ["title"],
            "KEYWORDS":    ["keyword","tag","kw"],
            "DESCRIPTION": ["desc","caption","description"],
        }
        vmap = {
            "FILENAME":    self.col_file_var,
            "TITLE":       self.col_title_var,
            "KEYWORDS":    self.col_kw_var,
            "DESCRIPTION": self.col_desc_var,
        }
        for lbl, cb in self.col_combos.items():
            cb.configure(values=opts)
            g = next((c for h in hints.get(lbl,[])
                for c in self.csv_headers if h in c.lower()), "")
            vmap[lbl].set(g or "(skip)")

    def browse_folder(self):
        p = filedialog.askdirectory(title="Select image folder")
        if p: self._do_set_folder(p)

    def _do_set_folder(self, path):
        self.folder_path_var.set(path)
        self.last_folder = path
        add_recent(self.prefs,'folders',path)
        self._update_match()
        self.log(f"✓  Folder set — {path}")

    def _update_match(self):
        folder = self.folder_path_var.get()
        col_f  = self.col_file_var.get()
        if not folder or not self.csv_rows or not col_f or col_f == "(skip)":
            return
        finder = find_recursive if self.subfolder_var.get() else find_file
        matched = sum(1 for row in self.csv_rows
            if finder(folder, (row.get(col_f) or "").strip(),
                self.match_only_var.get()))
        total = len(self.csv_rows)
        color = GRN if matched == total else AMB if matched > 0 else RED
        bg    = GBNB2 if matched == total else AMB2
        self.folder_badge.configure(
            text=f"📁  {matched} of {total} matched",
            fg_color=bg, text_color=color)
        self.set_status(f"{matched}/{total} files matched", color)

    def reset_all(self):
        if self.running:
            messagebox.showwarning("Busy", "Wait for current job to finish.")
            return
        if not messagebox.askyesno("Reset", "Clear everything and start fresh?"):
            return
        self.csv_path_var.set("")
        self.folder_path_var.set("")
        for v in [self.col_file_var, self.col_title_var,
                  self.col_kw_var, self.col_desc_var]:
            v.set("(skip)")
        self.csv_rows = []; self.csv_headers = []
        self.csv_badge.configure(text="No CSV loaded", fg_color=BG3, text_color=TXT3)
        self.folder_badge.configure(text="No folder selected", fg_color=BG3, text_color=TXT3)
        for cb in self.col_combos.values():
            cb.configure(values=["(skip)"])
        self.sb_prog.set(0); self.sb_pct.configure(text="")
        self.p_ok.configure(text="✓  0 embedded")
        self.p_warn.configure(text="⚠  0 not found")
        self.p_err.configure(text="✗  0 errors")
        self.embed_btn.configure(text="▶   Embed Metadata Now", state="normal")
        self.clear_log()
        self.log("↺  Reset — ready for new batch")
        self.set_status(f"Last: {self.last_summary}" if self.last_summary else "", TXT3)

    # ── Embed ──────────────────────────────────────────────────────────
    def start_embed(self):
        if self.running: return
        et = find_exiftool()
        if not et:
            messagebox.showerror("ExifTool not found",
                "Place exiftool.exe next to this app.\nhttps://exiftool.org")
            return
        if not self.csv_rows:
            messagebox.showerror("No CSV","Load a CSV first."); return
        if not self.folder_path_var.get():
            messagebox.showerror("No folder","Select image folder."); return
        fc = self.col_file_var.get()
        if not fc or fc == "(skip)":
            messagebox.showerror("Column missing","Select the filename column."); return
        self.running = True
        self.embed_btn.configure(state="disabled", text="⟳   Processing...")
        threading.Thread(target=self._embed_thread, args=(et,), daemon=True).start()

    def _embed_thread(self, et):
        folder  = self.folder_path_var.get()
        col_f   = self.col_file_var.get()
        col_t   = self.col_title_var.get()
        col_k   = self.col_kw_var.get()
        col_d   = self.col_desc_var.get()
        use_sub = self.subfolder_var.get()
        use_ext = self.match_only_var.get()
        rm_prog = self.rm_prog_var.get()
        total   = len(self.csv_rows)
        ok = skipped = errors = 0
        finder  = find_recursive if use_sub else find_file

        self.after(0, lambda: self.log(f"▶  Batch started — {total} rows"))

        for i, row in enumerate(self.csv_rows):
            fn = (row.get(col_f) or "").strip()
            if not fn:
                skipped += 1
                self.after(0, lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                    self._prog(n,t,o,s,e))
                continue

            fp = finder(folder, fn, use_ext)
            if not fp:
                skipped += 1
                self.after(0, lambda f=fn: self.log(f"⚠  Not found: {f}"))
                self.after(0, lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                    self._prog(n,t,o,s,e))
                continue

            cmd = [et,'-overwrite_original','-codedcharacterset=UTF8']
            title  = (row.get(col_t) or "").strip() if col_t and col_t!="(skip)" else ""
            kw_raw = (row.get(col_k) or "").strip() if col_k and col_k!="(skip)" else ""
            desc   = (row.get(col_d) or "").strip() if col_d and col_d!="(skip)" else ""

            if title:
                cmd += [f'-Title={title}',f'-ObjectName={title}',f'-Headline={title}']
            if kw_raw:
                for kw in [k.strip() for k in
                           kw_raw.replace(';',',').split(',') if k.strip()]:
                    cmd += [f'-Keywords={kw}',f'-Subject={kw}']
            if desc:
                cmd += [f'-Description={desc}',f'-Caption-Abstract={desc}']
            if rm_prog:
                cmd += ['-Software=','-CreatorTool=','-HistorySoftwareAgent=']
            cmd.append(fp)

            try:
                flags = subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
                res = subprocess.run(cmd, capture_output=True, text=True,
                    timeout=30, creationflags=flags)
                actual = os.path.basename(fp)
                if res.returncode == 0:
                    ok += 1
                    self.after(0, lambda fn=actual: self.log(f"✓  {fn}"))
                else:
                    errors += 1
                    err = (res.stderr or res.stdout or "Unknown").strip()
                    self.after(0, lambda fn=actual, e=err:
                        self.log(f"✗  {fn} — {e}"))
            except Exception as ex:
                errors += 1
                self.after(0, lambda fn=fn, e=str(ex): self.log(f"✗  {fn} — {e}"))

            self.after(0, lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                self._prog(n,t,o,s,e))

        summary = f"{ok} embedded · {skipped} not found · {errors} errors"
        self.last_summary = summary
        self.after(0, lambda: (
            self.log(f"● Done — {summary}"),
            self.set_status(f"Done — {summary}", GRN),
            self.embed_btn.configure(state="normal", text="▶  Start Again"),
            setattr(self,'running',False)
        ))

    def _prog(self, n, t, ok, skipped, errors):
        pct = n / t if t else 0
        self.sb_prog.set(pct)
        self.sb_pct.configure(text=f"{int(pct*100)}%")
        self.set_status(f"Processing {n} of {t}...", BLU)
        self.p_ok.configure(text=f"✓  {ok} embedded")
        self.p_warn.configure(text=f"⚠  {skipped} not found")
        self.p_err.configure(text=f"✗  {errors} errors")

if __name__ == '__main__':
    app = App()
    app.mainloop()
