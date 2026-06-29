import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, BooleanVar, IntVar
import csv, subprocess, os, sys, threading, datetime, json, base64, socket, math
import urllib.request, urllib.error
from PIL import Image

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# ── Palette ────────────────────────────────────────────────────────────
BG    = "#000214"; BG2 = "#03061c"; BG3 = "#090b1f"; BG4 = "#0b0c1c"
CARD  = "#001205"; BDR = "#021206"; BDR2 = "#081209"
TXT   = "#e8e8f4"; TXT2 = "#9a9ab8"; TXT3 = "#4a4a68"
GRN   = "#4dbe62"; GRN2 = "#2a7834"; GRN3 = "#0a1f10"
RED   = "#f07878"; RED2 = "#1e0d0d"
AMB   = "#f5c842"; AMB2 = "#1e1800"
BLU   = "#5b9ef5"; BLU2 = "#1a2a4a"; BLU3 = "#2563eb"
PRP   = "#8b6be8"; PRP2 = "#5c3db5"; PRP3 = "#1e1535"
CYAN  = "#3dd9c4"; LOG_BG = "#030416"

# ── Providers ──────────────────────────────────────────────────────────
AI_PROVIDERS = {
    "OpenRouter": {
        "models": ["qwen/qwen2.5-vl-72b-instruct:free","qwen/qwen2.5-vl-32b-instruct:free",
                   "google/gemini-2.0-flash-exp:free","meta-llama/llama-4-maverick:free",
                   "meta-llama/llama-4-scout:free","mistralai/mistral-small-3.1-24b-instruct:free"],
        "key_url": "https://openrouter.ai/keys","key_hint": "Get free key → openrouter.ai"},
    "Gemini": {
        "models": ["gemini-2.5-flash-preview-05-20","gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash","gemini-1.5-pro"],
        "key_url": "https://aistudio.google.com/app/apikey","key_hint": "Get free key → aistudio.google.com"},
    "Mistral": {
        "models": ["pixtral-12b-2409","pixtral-large-2411"],
        "key_url": "https://console.mistral.ai/api-keys/","key_hint": "Get key → console.mistral.ai"},
    "Groq": {
        "models": ["meta-llama/llama-4-scout-17b-16e-instruct","meta-llama/llama-4-maverick-17b-128e-instruct"],
        "key_url": "https://console.groq.com/keys","key_hint": "Get free key → console.groq.com"},
    "OpenAI": {
        "models": ["gpt-4o","gpt-4o-mini","gpt-4.1-nano"],
        "key_url": "https://platform.openai.com/api-keys","key_hint": "Get key → platform.openai.com"},
    "Claude": {
        "models": ["claude-haiku-4-5-20251001","claude-sonnet-4-6"],
        "key_url": "https://console.anthropic.com/settings/keys","key_hint": "Get key → console.anthropic.com"},
}

PLATFORM_RULES = {
    "General":{"kw":49,"title":150,"desc":250},
    "Adobe Stock":{"kw":49,"title":150,"desc":250},
    "Shutterstock":{"kw":50,"title":200,"desc":200},
    "Getty Images":{"kw":50,"title":200,"desc":500},
    "Freepik":{"kw":30,"title":150,"desc":200},
    "Pond5":{"kw":50,"title":200,"desc":500},
    "iStock":{"kw":50,"title":200,"desc":200},
}

# Content type → smart suffix appended to metadata/prompt
CONTENT_SUFFIXES = {
    "Auto Detect":    "",
    "JPG":            "",
    "Vector":         "This is a vector illustration.",
    "Transparent PNG":"isolated on transparent background",
    "White Background":"isolated on solid white background",
}

IMAGE_EXTS = {'.jpg','.jpeg','.png','.gif','.webp','.tiff','.tif'}

# ── Prefs ──────────────────────────────────────────────────────────────
def prefs_path():
    base = os.path.dirname(sys.executable if getattr(sys,'frozen',False)
                           else os.path.abspath(__file__))
    return os.path.join(base,'prefs.json')

def load_prefs():
    try:
        with open(prefs_path()) as f: return json.load(f)
    except: return {}

def save_prefs(p):
    try:
        with open(prefs_path(),'w') as f: json.dump(p,f,indent=2)
    except: pass

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

def get_active_keys(prefs):
    seq=[]
    for provider,cfg in AI_PROVIDERS.items():
        keys=prefs.get("ai_keys",{}).get(provider,[])
        model=prefs.get("ai_models",{}).get(provider,cfg["models"][0])
        for k in keys:
            if k.get("active") and k.get("key"):
                seq.append((provider,k["key"],model))
    return seq

def call_with_failover(path,prompt,prefs,status_cb=None):
    seq=get_active_keys(prefs)
    if not seq: raise RuntimeError("No active API keys. Open 'Add API Keys'.")
    last_err=""
    for provider,key,model in seq:
        try:
            if status_cb: status_cb(f"Trying {provider} · {model.split('/')[-1]}…")
            raw=CALLERS[provider](key,model,path,prompt)
            return raw,provider
        except Exception as e:
            last_err=f"{provider}: {str(e)[:120]}"
    raise RuntimeError(f"All keys failed. Last: {last_err}")

def build_meta_prompt(title_c,desc_c,kw_n,content_type,custom_prompt=""):
    suffix=CONTENT_SUFFIXES.get(content_type,"")
    extra=""
    if suffix: extra=f"\n- Append this phrase naturally: \"{suffix}\""
    if custom_prompt.strip(): extra+=f"\n- Additional instruction: {custom_prompt.strip()}"
    return (
        f"You are a professional stock image metadata writer.\n"
        f"Analyze this image and respond ONLY in this exact 3-line format:\n\n"
        f"TITLE: <descriptive title, max {title_c} characters>\n"
        f"DESCRIPTION: <detailed scene description, max {desc_c} characters>\n"
        f"KEYWORDS: <exactly {kw_n} comma-separated keywords, most specific first>\n\n"
        f"Rules:\n"
        f"- Output ONLY the 3 lines. Nothing else.\n"
        f"- Exactly {kw_n} keywords. No duplicates, no brand names.\n"
        f"- Cover: subject, action, setting, mood, color, style, use-case.{extra}"
    )

def build_prompt_prompt(max_words,styles,content_type,custom_prompt=""):
    suffix=CONTENT_SUFFIXES.get(content_type,"")
    style_str=", ".join(styles) if styles else "realistic photography"
    extra=""
    if suffix: extra=f"\n- End the prompt with: \"{suffix}\""
    if custom_prompt.strip(): extra+=f"\n- Additional instruction: {custom_prompt.strip()}"
    return (
        f"You are an expert AI image generation prompt writer.\n"
        f"Analyze this image and write a detailed image generation prompt.\n"
        f"Output ONLY the prompt text — no labels, no explanation, no formatting.\n\n"
        f"Rules:\n"
        f"- Maximum {max_words} words.\n"
        f"- Style: {style_str}.\n"
        f"- Include: subject details, lighting, color palette, composition, mood, camera angle.\n"
        f"- Write as a flowing, comma-separated description (professional prompt style).{extra}"
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

def make_thumb(path,size=(120,85)):
    try:
        img=Image.open(path).convert("RGB"); img.thumbnail(size,Image.LANCZOS)
        return ctk.CTkImage(img,size=img.size)
    except: return None

def check_online():
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET,socket.SOCK_STREAM).connect(("8.8.8.8",53))
        return True
    except: return False

# ══════════════════════════════════════════════════════════════════════
#  API KEY MANAGER
# ══════════════════════════════════════════════════════════════════════
class APIManagerWindow(ctk.CTkToplevel):
    def __init__(self,parent,prefs,on_close=None):
        super().__init__(parent)
        self.title("API Secrets Management"); self.configure(fg_color=BG2)
        self.resizable(False,False); self.grab_set()
        self.prefs=prefs; self.on_close=on_close
        self._cur=list(AI_PROVIDERS.keys())[0]
        self._build(); self._center(720,560)
        self.protocol("WM_DELETE_WINDOW",self._done)

    def _center(self,w,h):
        self.update_idletasks()
        x=self.master.winfo_x()+(self.master.winfo_width()-w)//2
        y=self.master.winfo_y()+(self.master.winfo_height()-h)//2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(2,weight=1)
        # Title bar
        hdr=ctk.CTkFrame(self,fg_color=BG4,corner_radius=0,height=48)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(hdr,text="API Secrets Management",
            font=ctk.CTkFont("Segoe UI",14,"bold"),text_color=TXT,fg_color=BG4
        ).grid(row=0,column=0,sticky="w",padx=16,pady=12)
        ctk.CTkButton(hdr,text="✕",width=32,height=32,fg_color="transparent",
            hover_color=RED2,text_color=TXT3,corner_radius=6,
            command=self._done).grid(row=0,column=1,padx=10)
        # Tab bar
        tab_bar=ctk.CTkFrame(self,fg_color=BG4,corner_radius=0,height=48)
        tab_bar.grid(row=1,column=0,sticky="ew"); tab_bar.grid_propagate(False)
        self._tab_btns={}
        for p in AI_PROVIDERS:
            btn=ctk.CTkButton(tab_bar,text=p,width=100,height=34,
                font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=BLU3 if p==self._cur else "transparent",
                hover_color=BLU2,
                text_color=TXT if p==self._cur else TXT2,corner_radius=8,
                command=lambda pv=p:self._switch(pv))
            btn.pack(side="left",padx=(8 if p==list(AI_PROVIDERS.keys())[0] else 2,0),pady=7)
            self._tab_btns[p]=btn
        # Body
        body=ctk.CTkFrame(self,fg_color=BG2,corner_radius=0)
        body.grid(row=2,column=0,sticky="nsew")
        body.grid_columnconfigure(0,weight=0); body.grid_columnconfigure(1,weight=1)
        body.grid_rowconfigure(0,weight=1)
        self._lp=ctk.CTkFrame(body,fg_color=BG3,corner_radius=0,width=300)
        self._lp.grid(row=0,column=0,sticky="nsew"); self._lp.grid_propagate(False)
        self._rp=ctk.CTkFrame(body,fg_color=BG2,corner_radius=0)
        self._rp.grid(row=0,column=1,sticky="nsew",padx=(1,0))
        self._rp.grid_columnconfigure(0,weight=1); self._rp.grid_rowconfigure(1,weight=1)
        # Footer
        ftr=ctk.CTkFrame(self,fg_color=BG4,corner_radius=0,height=48)
        ftr.grid(row=3,column=0,sticky="ew"); ftr.grid_propagate(False)
        ctk.CTkButton(ftr,text="Done",width=90,height=32,
            fg_color=BLU3,hover_color=BLU2,text_color="white",corner_radius=8,
            command=self._done).pack(side="right",padx=14,pady=8)
        self._render()

    def _switch(self,p):
        self._cur=p
        for pv,btn in self._tab_btns.items():
            btn.configure(fg_color=BLU3 if pv==p else "transparent",
                          text_color=TXT if pv==p else TXT2)
        self._render()

    def _render(self):
        for w in self._lp.winfo_children(): w.destroy()
        for w in self._rp.winfo_children(): w.destroy()
        p=self._cur; cfg=AI_PROVIDERS[p]
        keys=self.prefs.setdefault("ai_keys",{}).setdefault(p,[])
        models=cfg["models"]
        cur_model=self.prefs.setdefault("ai_models",{}).get(p,models[0])
        # LEFT
        ctk.CTkLabel(self._lp,text="CONFIGURATION",
            font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=BLU,fg_color=BG3
        ).pack(anchor="w",padx=16,pady=(16,10))
        ctk.CTkLabel(self._lp,text="Model Selection",
            font=ctk.CTkFont("Segoe UI",11),text_color=TXT2,fg_color=BG3
        ).pack(anchor="w",padx=16,pady=(0,4))
        mv=StringVar(value=cur_model)
        ctk.CTkComboBox(self._lp,variable=mv,values=models,state="readonly",
            font=ctk.CTkFont("Segoe UI",11),fg_color=BG4,text_color=TXT,
            border_color=BDR,button_color=BLU3,button_hover_color=BLU2,
            dropdown_fg_color=BG4,dropdown_text_color=TXT,dropdown_hover_color=BLU2,
            corner_radius=6,height=36,command=lambda v:self._save_model(p,v)
        ).pack(fill="x",padx=16,pady=(0,16))
        ctk.CTkFrame(self._lp,fg_color=BDR,height=1,corner_radius=0).pack(fill="x")
        ctk.CTkLabel(self._lp,text="Add New API Key",
            font=ctk.CTkFont("Segoe UI",11),text_color=TXT2,fg_color=BG3
        ).pack(anchor="w",padx=16,pady=(14,4))
        nkv=StringVar()
        er=ctk.CTkFrame(self._lp,fg_color=BG3,corner_radius=0)
        er.pack(fill="x",padx=16,pady=(0,10)); er.grid_columnconfigure(0,weight=1)
        entry=ctk.CTkEntry(er,textvariable=nkv,placeholder_text="sk-or-v1-...",show="•",
            font=ctk.CTkFont("Segoe UI",11),fg_color=BG4,text_color=TXT,
            border_color=BDR,corner_radius=6,height=36)
        entry.grid(row=0,column=0,sticky="ew")
        ctk.CTkButton(er,text="Save",width=70,height=36,fg_color=BLU3,hover_color=BLU2,
            text_color="white",corner_radius=6,
            command=lambda:self._add_key(p,nkv.get().strip())
        ).grid(row=0,column=1,padx=(6,0))
        ctk.CTkButton(self._lp,text=f"🔑  Get API Key from {p}",
            fg_color=BG4,hover_color=BDR,text_color=TXT2,border_width=1,
            border_color=BDR,height=36,corner_radius=6,
            command=lambda:self._open_url(cfg["key_url"])
        ).pack(fill="x",padx=16,pady=(0,14))
        # RIGHT
        ctk.CTkLabel(self._rp,text="STORED KEYS",
            font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=TXT2,fg_color=BG2
        ).pack(anchor="w",padx=16,pady=(16,10))
        ks=ctk.CTkScrollableFrame(self._rp,fg_color=BG2,corner_radius=0,
            scrollbar_button_color=BG3)
        ks.pack(fill="both",expand=True)
        ks.grid_columnconfigure(0,weight=1)
        if not keys:
            ctk.CTkLabel(ks,text="No keys added yet.",font=ctk.CTkFont("Segoe UI",11),
                text_color=TXT3,fg_color=BG2).pack(pady=30)
            return
        for i,k in enumerate(keys):
            is_active=k.get("active",False)
            kv=k.get("key","")
            key_short=kv[:10]+"..." if len(kv)>10 else kv
            key_id="ID: "+kv[-4:] if len(kv)>=4 else ""
            bdr_col=BLU3 if is_active else BDR
            card=ctk.CTkFrame(ks,fg_color=BLU2 if is_active else BG3,
                corner_radius=10,border_width=1,border_color=bdr_col)
            card.pack(fill="x",padx=12,pady=(0,8)); card.grid_columnconfigure(1,weight=1)
            ctk.CTkLabel(card,text="🔑",font=ctk.CTkFont("Segoe UI",14),
                fg_color="transparent",text_color=TXT2
            ).grid(row=0,column=0,padx=(12,8),pady=(10,4),sticky="w")
            kf=ctk.CTkFrame(card,fg_color="transparent",corner_radius=0)
            kf.grid(row=0,column=1,sticky="ew",pady=(10,4))
            ctk.CTkLabel(kf,text=key_short,font=ctk.CTkFont("Consolas",11,"bold"),
                text_color=TXT,fg_color="transparent",anchor="w").pack(anchor="w")
            ctk.CTkLabel(kf,text=key_id,font=ctk.CTkFont("Segoe UI",10),
                text_color=TXT3,fg_color="transparent",anchor="w").pack(anchor="w")
            if is_active:
                ctk.CTkLabel(card,text="● Active",font=ctk.CTkFont("Segoe UI",10,"bold"),
                    fg_color=GRN3,text_color=GRN,corner_radius=20,padx=10,pady=3
                ).grid(row=0,column=2,padx=(0,10),pady=(10,4),sticky="e")
            af=ctk.CTkFrame(card,fg_color="transparent",corner_radius=0)
            af.grid(row=1,column=0,columnspan=3,sticky="ew",padx=10,pady=(0,8))
            ctk.CTkButton(af,text="👁",width=32,height=28,fg_color="transparent",
                hover_color=BDR,text_color=TXT3,corner_radius=6,
                command=lambda kv2=kv,lb=kf:self._toggle_show(kv2,lb)
            ).pack(side="left",padx=(0,4))
            ctk.CTkButton(af,text="⧉",width=32,height=28,fg_color="transparent",
                hover_color=BDR,text_color=TXT3,corner_radius=6,
                command=lambda kv2=kv:self._copy(kv2)
            ).pack(side="left",padx=(0,4))
            if not is_active:
                ctk.CTkButton(af,text="Activate",width=80,height=28,
                    fg_color=BG4,hover_color=BLU2,text_color=TXT2,
                    border_width=1,border_color=BDR,corner_radius=6,
                    command=lambda i2=i:self._toggle(p,i2)
                ).pack(side="left",padx=(0,4))
            ctk.CTkButton(af,text="🗑",width=32,height=28,fg_color="transparent",
                hover_color=RED2,text_color=TXT3,corner_radius=6,
                command=lambda i2=i:self._del(p,i2)
            ).pack(side="right")

    def _toggle_show(self,kv,lf):
        ch=lf.winfo_children()
        if ch:
            cur=ch[0].cget("text")
            ch[0].configure(text=kv if "..." in cur else (kv[:10]+"..." if len(kv)>10 else kv))

    def _copy(self,kv): self.clipboard_clear(); self.clipboard_append(kv)
    def _toggle(self,p,idx):
        keys=self.prefs["ai_keys"][p]
        for i,k in enumerate(keys): k["active"]=(i==idx)
        save_prefs(self.prefs); self._render()
    def _del(self,p,idx):
        if not messagebox.askyesno("Delete","Delete this key?",parent=self): return
        self.prefs["ai_keys"][p].pop(idx); save_prefs(self.prefs); self._render()
    def _add_key(self,p,key):
        if not key: messagebox.showwarning("Empty","Paste a key first.",parent=self); return
        keys=self.prefs["ai_keys"][p]
        if any(k["key"]==key for k in keys):
            messagebox.showinfo("Duplicate","Already saved.",parent=self); return
        for k in keys: k["active"]=False
        keys.append({"key":key,"active":True})
        save_prefs(self.prefs); self._render()
    def _save_model(self,p,m): self.prefs.setdefault("ai_models",{})[p]=m; save_prefs(self.prefs)
    def _open_url(self,url):
        import webbrowser; webbrowser.open(url)
    def _done(self):
        if self.on_close: self.on_close()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  IMAGE CARD — METADATA MODE
# ══════════════════════════════════════════════════════════════════════
class MetaCard(ctk.CTkFrame):
    STATUS_COLORS={"waiting":(BG3,TXT3,BDR),"working":(PRP3,PRP,PRP2),
                   "done":(GRN3,GRN,GRN2),"failed":(RED2,RED,"#5a1a1a")}

    def __init__(self,master,path,on_delete,on_regen,**kw):
        super().__init__(master,fg_color=CARD,corner_radius=10,
                         border_width=1,border_color=BDR,**kw)
        self.path=path; self.on_delete=on_delete; self.on_regen=on_regen
        self.status="waiting"; self._build()

    def _build(self):
        self.grid_columnconfigure(1,weight=1)
        # LEFT PANEL
        lp=ctk.CTkFrame(self,fg_color=BG3,corner_radius=0,width=138)
        lp.grid(row=0,column=0,sticky="nsew"); lp.grid_propagate(False)
        lp.grid_columnconfigure(0,weight=1)

        # Thumbnail
        tf=ctk.CTkFrame(lp,fg_color=BG3,corner_radius=0,height=80)
        tf.grid(row=0,column=0,sticky="ew",padx=6,pady=(6,2)); tf.grid_propagate(False)
        tf.grid_columnconfigure(0,weight=1)
        self._thumb=ctk.CTkLabel(tf,text="🖼",font=ctk.CTkFont("Segoe UI",18),
            fg_color=BG2,text_color=TXT3,corner_radius=6,width=126,height=74)
        self._thumb.grid(row=0,column=0)
        del_btn=ctk.CTkButton(tf,text="✕",width=20,height=20,
            font=ctk.CTkFont("Segoe UI",8,"bold"),
            fg_color=RED,hover_color="#c04040",text_color="white",corner_radius=10,
            command=self.on_delete)
        del_btn.place(relx=1.0,rely=0.0,anchor="ne",x=-1,y=1)

        # Filename (close under image)
        fname=os.path.basename(self.path)
        fname_short=fname if len(fname)<=20 else fname[:18]+"…"
        ctk.CTkLabel(lp,text=fname_short,font=ctk.CTkFont("Segoe UI",8),
            text_color=TXT2,fg_color=BG3,wraplength=126
        ).grid(row=1,column=0,padx=6,pady=(2,0),sticky="ew")

        # File size (under filename)
        try: sz=f"{os.path.getsize(self.path)/1024:,.1f} KB"
        except: sz=""
        ctk.CTkLabel(lp,text=sz,font=ctk.CTkFont("Segoe UI",8),
            text_color=TXT3,fg_color=BG3
        ).grid(row=2,column=0,padx=6,pady=(0,4))

        # Regen button
        self._regen_btn=ctk.CTkButton(lp,text="↺ Retry",height=24,
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            fg_color=BG3,hover_color=BDR,text_color=TXT3,
            corner_radius=6,border_width=1,border_color=BDR,
            command=self.on_regen)
        self._regen_btn.grid(row=3,column=0,padx=6,pady=(0,4),sticky="ew")

        # Status
        self._status_lbl=ctk.CTkLabel(lp,text="○  WAITING",
            font=ctk.CTkFont("Segoe UI",8,"bold"),
            fg_color=BG3,text_color=TXT3,corner_radius=20,height=22)
        self._status_lbl.grid(row=4,column=0,padx=6,pady=(0,6),sticky="ew")

        # RIGHT PANEL
        rp=ctk.CTkFrame(self,fg_color=CARD,corner_radius=0)
        rp.grid(row=0,column=1,sticky="nsew",padx=(6,8),pady=8)
        rp.grid_columnconfigure(0,weight=1)

        self._title_var=StringVar(); self._desc_var=StringVar(); self._kw_var=StringVar()
        self._title_box=self._field(rp,0,"Ħ  Title",    self._title_var,2)
        self._desc_box =self._field(rp,1,"≡  Description",self._desc_var,3)
        self._kw_box   =self._field(rp,2,"🏷  Keywords", self._kw_var,   3,is_kw=True)

        # Error label
        self._err_lbl=ctk.CTkLabel(rp,text="",font=ctk.CTkFont("Segoe UI",8),
            fg_color=RED2,text_color=RED,corner_radius=6,padx=6,pady=2)

        # Load thumbnail in thread
        threading.Thread(target=self._load_thumb,daemon=True).start()

    def _field(self,parent,idx,label,var,lines,is_kw=False):
        hdr=ctk.CTkFrame(parent,fg_color=CARD,corner_radius=0)
        hdr.grid(row=idx*2,column=0,sticky="ew",pady=(0,1))
        hdr.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(hdr,text=label,font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3,fg_color=CARD).grid(row=0,column=0,sticky="w")
        cnt_lbl=ctk.CTkLabel(hdr,text="(0) Chars  (0) Words",
            font=ctk.CTkFont("Segoe UI",8),text_color=TXT3,fg_color=CARD)
        cnt_lbl.grid(row=0,column=1,sticky="e")
        ctk.CTkButton(hdr,text="Copy",width=42,height=18,
            font=ctk.CTkFont("Segoe UI",8),fg_color=BG3,hover_color=BDR,
            text_color=TXT3,corner_radius=20,
            command=lambda v=var:self._copy(v.get())
        ).grid(row=0,column=2,padx=(4,0))
        box=ctk.CTkTextbox(parent,font=ctk.CTkFont("Segoe UI",10),
            fg_color=BG3,text_color=CYAN if is_kw else TXT,
            border_color=BDR,border_width=1,corner_radius=6,
            wrap="word",height=20*lines)
        box.grid(row=idx*2+1,column=0,sticky="ew",pady=(0,4))
        def _upd(e=None):
            c=box.get("1.0","end").strip(); var.set(c)
            w=len(c.split()) if c else 0
            cnt_lbl.configure(text=f"({len(c)}) Chars  ({w}) Words")
        box.bind("<KeyRelease>",_upd)
        return box

    def _copy(self,t): self.clipboard_clear(); self.clipboard_append(t)

    def _load_thumb(self):
        th=make_thumb(self.path,(126,74))
        if th:
            self._thumb.after(0,lambda:self._thumb.configure(image=th,text=""))
            self._thumb._image=th

    def set_status(self,status,fail_msg=""):
        self.status=status
        bg,fg,bdr=self.STATUS_COLORS.get(status,(BG3,TXT3,BDR))
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
            self._regen_btn.configure(fg_color=BG3,text_color=TXT3,border_color=BDR)

    def set_working(self):
        self._title_box.configure(state="normal"); self._title_box.delete("1.0","end")
        self._title_box.insert("1.0","⟳ AI is analyzing…"); self._title_box.configure(state="disabled")
        for b in [self._desc_box,self._kw_box]:
            b.configure(state="normal"); b.delete("1.0","end")

    def set_result(self,title,desc,kw):
        for box,val,var in [(self._title_box,title,self._title_var),
                            (self._desc_box,desc,self._desc_var),
                            (self._kw_box,kw,self._kw_var)]:
            box.configure(state="normal"); box.delete("1.0","end"); box.insert("1.0",val)
            var.set(val)
        # Update char/word counters
        for box in [self._title_box,self._desc_box,self._kw_box]:
            box.event_generate("<KeyRelease>")

    def clear(self):
        for box in [self._title_box,self._desc_box,self._kw_box]:
            box.configure(state="normal"); box.delete("1.0","end")

    def get_result(self):
        return {"Filename":os.path.basename(self.path),
                "Title":self._title_var.get(),
                "Description":self._desc_var.get(),
                "Keywords":self._kw_var.get()}


# ══════════════════════════════════════════════════════════════════════
#  IMAGE CARD — PROMPT MODE
# ══════════════════════════════════════════════════════════════════════
class PromptCard(ctk.CTkFrame):
    STATUS_COLORS={"waiting":(BG3,TXT3,BDR),"working":(PRP3,PRP,PRP2),
                   "done":(GRN3,GRN,GRN2),"failed":(RED2,RED,"#5a1a1a")}

    def __init__(self,master,path,on_delete,on_regen,**kw):
        super().__init__(master,fg_color=CARD,corner_radius=10,
                         border_width=1,border_color=BDR,**kw)
        self.path=path; self.on_delete=on_delete; self.on_regen=on_regen
        self.status="waiting"; self._prompt_var=StringVar()
        self._build()

    def _build(self):
        self.grid_columnconfigure(1,weight=1)
        # LEFT
        lp=ctk.CTkFrame(self,fg_color=BG3,corner_radius=0,width=138)
        lp.grid(row=0,column=0,sticky="nsew"); lp.grid_propagate(False)
        lp.grid_columnconfigure(0,weight=1)
        tf=ctk.CTkFrame(lp,fg_color=BG3,corner_radius=0,height=80)
        tf.grid(row=0,column=0,sticky="ew",padx=6,pady=(6,2)); tf.grid_propagate(False)
        tf.grid_columnconfigure(0,weight=1)
        self._thumb=ctk.CTkLabel(tf,text="🖼",font=ctk.CTkFont("Segoe UI",18),
            fg_color=BG2,text_color=TXT3,corner_radius=6,width=126,height=74)
        self._thumb.grid(row=0,column=0)
        del_btn=ctk.CTkButton(tf,text="✕",width=20,height=20,
            font=ctk.CTkFont("Segoe UI",8,"bold"),
            fg_color=RED,hover_color="#c04040",text_color="white",corner_radius=10,
            command=self.on_delete)
        del_btn.place(relx=1.0,rely=0.0,anchor="ne",x=-1,y=1)
        fname=os.path.basename(self.path)
        fname_short=fname if len(fname)<=20 else fname[:18]+"…"
        ctk.CTkLabel(lp,text=fname_short,font=ctk.CTkFont("Segoe UI",8),
            text_color=TXT2,fg_color=BG3,wraplength=126
        ).grid(row=1,column=0,padx=6,pady=(2,0),sticky="ew")
        try: sz=f"{os.path.getsize(self.path)/1024:,.1f} KB"
        except: sz=""
        ctk.CTkLabel(lp,text=sz,font=ctk.CTkFont("Segoe UI",8),
            text_color=TXT3,fg_color=BG3).grid(row=2,column=0,padx=6,pady=(0,4))
        self._regen_btn=ctk.CTkButton(lp,text="↺ Retry",height=24,
            font=ctk.CTkFont("Segoe UI",9,"bold"),
            fg_color=BG3,hover_color=BDR,text_color=TXT3,
            corner_radius=6,border_width=1,border_color=BDR,command=self.on_regen)
        self._regen_btn.grid(row=3,column=0,padx=6,pady=(0,4),sticky="ew")
        self._status_lbl=ctk.CTkLabel(lp,text="○  WAITING",
            font=ctk.CTkFont("Segoe UI",8,"bold"),
            fg_color=BG3,text_color=TXT3,corner_radius=20,height=22)
        self._status_lbl.grid(row=4,column=0,padx=6,pady=(0,6),sticky="ew")

        # RIGHT — single prompt box
        rp=ctk.CTkFrame(self,fg_color=CARD,corner_radius=0)
        rp.grid(row=0,column=1,sticky="nsew",padx=(6,8),pady=8)
        rp.grid_columnconfigure(0,weight=1)
        rp.grid_rowconfigure(1,weight=1)

        hdr=ctk.CTkFrame(rp,fg_color=CARD,corner_radius=0)
        hdr.grid(row=0,column=0,sticky="ew",pady=(0,4))
        hdr.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(hdr,text="≡  Generated Prompt",
            font=ctk.CTkFont("Segoe UI",9,"bold"),text_color=TXT3,fg_color=CARD
        ).grid(row=0,column=0,sticky="w")
        self._cnt_lbl=ctk.CTkLabel(hdr,text="(0) Chars  (0) Words",
            font=ctk.CTkFont("Segoe UI",8),text_color=TXT3,fg_color=CARD)
        self._cnt_lbl.grid(row=0,column=1,sticky="e")
        ctk.CTkButton(hdr,text="Copy",width=42,height=18,
            font=ctk.CTkFont("Segoe UI",8),fg_color=BG3,hover_color=BDR,
            text_color=TXT3,corner_radius=20,
            command=lambda:self._copy(self._prompt_var.get())
        ).grid(row=0,column=2,padx=(4,0))

        self._prompt_box=ctk.CTkTextbox(rp,font=ctk.CTkFont("Segoe UI",10),
            fg_color=BG3,text_color=CYAN,border_color=BDR,border_width=1,
            corner_radius=6,wrap="word",height=120)
        self._prompt_box.grid(row=1,column=0,sticky="nsew")

        self._err_lbl=ctk.CTkLabel(rp,text="",font=ctk.CTkFont("Segoe UI",8),
            fg_color=RED2,text_color=RED,corner_radius=6,padx=6,pady=2)

        def _upd(e=None):
            c=self._prompt_box.get("1.0","end").strip()
            self._prompt_var.set(c)
            w=len(c.split()) if c else 0
            self._cnt_lbl.configure(text=f"({len(c)}) Chars  ({w}) Words")
        self._prompt_box.bind("<KeyRelease>",_upd)
        threading.Thread(target=self._load_thumb,daemon=True).start()

    def _copy(self,t): self.clipboard_clear(); self.clipboard_append(t)
    def _load_thumb(self):
        th=make_thumb(self.path,(126,74))
        if th:
            self._thumb.after(0,lambda:self._thumb.configure(image=th,text=""))
            self._thumb._image=th

    def set_status(self,status,fail_msg=""):
        self.status=status
        bg,fg,bdr=self.STATUS_COLORS.get(status,(BG3,TXT3,BDR))
        self.configure(border_color=bdr)
        labels={"waiting":"○  WAITING","working":"⟳  WORKING…","done":"✓  DONE","failed":"✗  FAILED"}
        self._status_lbl.configure(text=labels.get(status,""),fg_color=bg,text_color=fg)
        if status=="failed" and fail_msg:
            self._err_lbl.configure(text=f"⚠ {fail_msg[:70]}")
            self._err_lbl.grid(row=2,column=0,sticky="ew",pady=(2,0))
        else:
            try: self._err_lbl.grid_remove()
            except: pass
            self._regen_btn.configure(fg_color=BG3,text_color=TXT3,border_color=BDR)

    def set_working(self):
        self._prompt_box.configure(state="normal"); self._prompt_box.delete("1.0","end")
        self._prompt_box.insert("1.0","⟳ AI is analyzing…")
        self._prompt_box.configure(state="disabled")

    def set_result(self,prompt):
        self._prompt_box.configure(state="normal")
        self._prompt_box.delete("1.0","end")
        self._prompt_box.insert("1.0",prompt)
        self._prompt_var.set(prompt)
        c=len(prompt); w=len(prompt.split()) if prompt else 0
        self._cnt_lbl.configure(text=f"({c}) Chars  ({w}) Words")

    def clear(self):
        self._prompt_box.configure(state="normal"); self._prompt_box.delete("1.0","end")

    def get_result(self):
        return {"Filename":os.path.basename(self.path),"Prompt":self._prompt_var.get()}


# ══════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Meta Zone"); self.configure(fg_color=BG)
        self.resizable(True,True)
        self.prefs=load_prefs()

        # AI state
        self.cards=[]           # list of MetaCard or PromptCard
        self.ai_running=False; self.ai_stop_flag=False
        self.current_mode="meta"   # "meta" or "prompt"

        # Embed state
        self.csv_rows=[]; self.csv_headers=[]; self.embed_running=False
        self.csv_path_var=StringVar(); self.folder_path_var=StringVar()
        self.col_file_var=StringVar(value="(skip)"); self.col_title_var=StringVar(value="(skip)")
        self.col_kw_var=StringVar(value="(skip)"); self.col_desc_var=StringVar(value="(skip)")
        self.match_only_var=BooleanVar(value=True); self.subfolder_var=BooleanVar(value=True)
        self.rm_prog_var=BooleanVar(value=True)

        # AI settings
        self.ai_platform_var=StringVar(value=self.prefs.get("platform","Adobe Stock"))
        self.ai_title_var=StringVar(value=str(self.prefs.get("title_len",120)))
        self.ai_desc_var=StringVar(value=str(self.prefs.get("desc_len",200)))
        self.ai_kw_var=StringVar(value=str(self.prefs.get("kw_count",49)))
        self.ai_words_var=StringVar(value=str(self.prefs.get("prompt_words",60)))
        self.ai_content_var=StringVar(value=self.prefs.get("content_type","Auto Detect"))
        self.ai_custom_var=StringVar(value=self.prefs.get("custom_prompt",""))
        # Style toggles
        self._style_vars={}
        for s in ["Silhouette","White Background","Transparent Background","Digital Art",
                  "Vector","Auto Detect"]:
            self._style_vars[s]=BooleanVar(value=False)

        self._build_ui()
        self._center(1200,860)
        self.minsize(900,640)
        self.after(200,self._check_et)
        self.after(500,self._online_loop)

    def _center(self,w,h):
        self.update_idletasks()
        sw=self.winfo_screenwidth(); sh=self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def ts(self): return datetime.datetime.now().strftime("%H:%M:%S")

    # ── Build ──────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0,weight=1)
        self.grid_rowconfigure(0,weight=0)  # titlebar
        self.grid_rowconfigure(1,weight=0)  # tabbar
        self.grid_rowconfigure(2,weight=1)  # content
        self.grid_rowconfigure(3,weight=0)  # statusbar
        self._build_titlebar()
        self._build_tabs()
        self._build_statusbar()

    def _build_titlebar(self):
        tb=ctk.CTkFrame(self,fg_color=BG4,corner_radius=0,height=50)
        tb.grid(row=0,column=0,sticky="ew"); tb.grid_propagate(False)
        tb.grid_columnconfigure(2,weight=1)
        ctk.CTkLabel(tb,text="✦",font=ctk.CTkFont("Segoe UI",15,"bold"),
            fg_color=PRP2,text_color="white",corner_radius=8,width=28,height=28
        ).grid(row=0,column=0,padx=(14,8),pady=11)
        ctk.CTkLabel(tb,text="Meta Zone",font=ctk.CTkFont("Segoe UI",17,"bold"),
            text_color=TXT,fg_color=BG4).grid(row=0,column=1,sticky="w")
        ctk.CTkLabel(tb,text="v1.0 Beta",font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=PRP,fg_color=PRP3,corner_radius=20,padx=7,pady=2
        ).grid(row=0,column=2,sticky="w",padx=(6,0))
        # Online indicator
        self._online_dot=ctk.CTkLabel(tb,text="●",
            font=ctk.CTkFont("Segoe UI",11),text_color=GRN,fg_color=BG4)
        self._online_dot.grid(row=0,column=3,padx=(0,4))
        self._online_lbl=ctk.CTkLabel(tb,text="Online",
            font=ctk.CTkFont("Segoe UI",10),text_color=TXT3,fg_color=BG4)
        self._online_lbl.grid(row=0,column=4,padx=(0,14))
        # Copyright
        cr=ctk.CTkFrame(tb,fg_color=BG4,corner_radius=0)
        cr.grid(row=0,column=5,padx=(0,16),sticky="e")
        ctk.CTkLabel(cr,text="All Rights Reserved By",font=ctk.CTkFont("Segoe UI",8),
            text_color=TXT3,fg_color=BG4).pack(anchor="e")
        ctk.CTkLabel(cr,text="© HASIBNIKON",font=ctk.CTkFont("Segoe UI",11,"bold"),
            text_color=TXT2,fg_color=BG4).pack(anchor="e")

    def _online_loop(self):
        def _check():
            online=check_online()
            self.after(0,lambda:self._set_online(online))
            self.after(5000,self._online_loop)
        threading.Thread(target=_check,daemon=True).start()

    def _set_online(self,online):
        if online:
            self._online_dot.configure(text_color=GRN); self._online_lbl.configure(text="Online")
        else:
            self._online_dot.configure(text_color=RED); self._online_lbl.configure(text="Offline")
        # Blink
        self._blink_dot()

    def _blink_dot(self,count=0):
        if count<6:
            vis=TXT3 if count%2==0 else (GRN if self._online_lbl.cget("text")=="Online" else RED)
            self._online_dot.configure(text_color=vis)
            self.after(300,lambda:self._blink_dot(count+1))

    def _build_tabs(self):
        tab_bar=ctk.CTkFrame(self,fg_color=BG4,corner_radius=0,height=44)
        tab_bar.grid(row=1,column=0,sticky="ew"); tab_bar.grid_propagate(False)
        tab_bar.grid_columnconfigure(2,weight=1)
        self._ai_tab_btn=ctk.CTkButton(tab_bar,text="✨  Metadata AI",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=PRP,hover_color=PRP2,text_color="white",
            width=160,height=30,corner_radius=15,
            command=lambda:self._switch_tab("ai"))
        self._ai_tab_btn.grid(row=0,column=0,padx=(12,4),pady=7)
        self._emb_tab_btn=ctk.CTkButton(tab_bar,text="📋  Embed Metadata",
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BG3,hover_color=BDR,text_color=TXT3,
            width=170,height=30,corner_radius=15,
            command=lambda:self._switch_tab("embed"))
        self._emb_tab_btn.grid(row=0,column=1,padx=4,pady=7)
        self._content=ctk.CTkFrame(self,fg_color=BG,corner_radius=0)
        self._content.grid(row=2,column=0,sticky="nsew")
        self._content.grid_columnconfigure(0,weight=1); self._content.grid_rowconfigure(0,weight=1)
        self._ai_frame=ctk.CTkFrame(self._content,fg_color=BG,corner_radius=0)
        self._emb_frame=ctk.CTkFrame(self._content,fg_color=BG,corner_radius=0)
        self._ai_frame.grid(row=0,column=0,sticky="nsew")
        self._emb_frame.grid(row=0,column=0,sticky="nsew")
        self._build_ai_tab(self._ai_frame)
        self._build_embed_tab(self._emb_frame)
        self._switch_tab("ai")

    def _switch_tab(self,which):
        if which=="ai":
            self._ai_frame.tkraise()
            self._ai_tab_btn.configure(fg_color=PRP,text_color="white")
            self._emb_tab_btn.configure(fg_color=BG3,text_color=TXT3)
        else:
            self._emb_frame.tkraise()
            self._emb_tab_btn.configure(fg_color=PRP,text_color="white")
            self._ai_tab_btn.configure(fg_color=BG3,text_color=TXT3)

    # ══════════════════════════════════════════════════════════════════
    #  AI TAB
    # ══════════════════════════════════════════════════════════════════
    def _build_ai_tab(self,parent):
        parent.grid_columnconfigure(0,weight=0)   # sidebar fixed
        parent.grid_columnconfigure(1,weight=1)   # main
        parent.grid_rowconfigure(0,weight=1)
        # Sidebar always visible
        self._sidebar=ctk.CTkFrame(parent,fg_color=BG2,corner_radius=0,width=240)
        self._sidebar.grid(row=0,column=0,sticky="nsew"); self._sidebar.grid_propagate(False)
        self._ai_main=ctk.CTkFrame(parent,fg_color=BG,corner_radius=0)
        self._ai_main.grid(row=0,column=1,sticky="nsew")
        self._ai_main.grid_columnconfigure(0,weight=1)
        self._ai_main.grid_rowconfigure(2,weight=1)
        self._build_sidebar()
        self._build_ai_main()

    # ── SIDEBAR ────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sb=self._sidebar; sb.grid_rowconfigure(1,weight=1); sb.grid_columnconfigure(0,weight=1)
        hdr=ctk.CTkFrame(sb,fg_color=BG4,corner_radius=0,height=38)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False)
        ctk.CTkLabel(hdr,text="CONFIGURATION",
            font=ctk.CTkFont("Segoe UI",9,"bold"),text_color=TXT3,fg_color=BG4
        ).pack(side="left",padx=12,pady=10)
        inner=ctk.CTkScrollableFrame(sb,fg_color=BG2,scrollbar_button_color=BG3,corner_radius=0)
        inner.grid(row=1,column=0,sticky="nsew"); inner.grid_columnconfigure(0,weight=1)
        self._sb=inner

        # API Key button
        ctk.CTkButton(inner,text="🔑  Add API Keys",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BLU3,hover_color=BLU2,text_color="white",
            height=36,corner_radius=8,command=self._open_api_mgr
        ).pack(fill="x",padx=10,pady=(10,3))
        self._api_lbl=ctk.CTkLabel(inner,text="",font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT3,fg_color=BG2); self._api_lbl.pack(anchor="w",padx=12,pady=(0,6))
        self._refresh_api_lbl()

        # Mode switch: METADATA | PROMPT
        self._div(inner)
        mode_frame=ctk.CTkFrame(inner,fg_color=BG3,corner_radius=8)
        mode_frame.pack(fill="x",padx=10,pady=(4,8))
        mode_frame.grid_columnconfigure(0,weight=1); mode_frame.grid_columnconfigure(1,weight=1)
        self._meta_mode_btn=ctk.CTkButton(mode_frame,text="≡  METADATA",height=32,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=BLU3,hover_color=BLU2,text_color="white",corner_radius=6,
            command=lambda:self._set_mode("meta"))
        self._meta_mode_btn.grid(row=0,column=0,sticky="ew",padx=(4,2),pady=4)
        self._prompt_mode_btn=ctk.CTkButton(mode_frame,text="✨  PROMPT",height=32,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color="transparent",hover_color=BLU2,text_color=TXT3,corner_radius=6,
            command=lambda:self._set_mode("prompt"))
        self._prompt_mode_btn.grid(row=0,column=1,sticky="ew",padx=(2,4),pady=4)

        # Meta-only: title/desc/kw sliders (frame for show/hide)
        self._meta_sliders_frame=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        self._meta_sliders_frame.pack(fill="x")
        msf=self._meta_sliders_frame
        self._lbl(msf,"METADATA SETTINGS")
        self._title_sl=self._slider(msf,"Title Length",self.ai_title_var,10,200,int(self.ai_title_var.get()))
        self._desc_sl =self._slider(msf,"Description Length",self.ai_desc_var,20,500,int(self.ai_desc_var.get()))
        self._kw_sl   =self._slider(msf,"Keywords Count",self.ai_kw_var,5,50,int(self.ai_kw_var.get()))

        # Prompt-only: word count slider (frame for show/hide)
        self._prompt_sliders_frame=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        self._prompt_sliders_frame.pack(fill="x")
        psf=self._prompt_sliders_frame
        self._lbl(psf,"PROMPT SETTINGS")
        self._words_sl=self._slider(psf,"Max Prompt Words",self.ai_words_var,10,200,int(self.ai_words_var.get()))
        self._prompt_sliders_frame.pack_forget()  # hidden initially

        # Prompt Styles (shown in both modes)
        self._div(inner)
        self._lbl(inner,"PROMPT STYLES")
        styles=["Silhouette","White Background","Transparent Background","Digital Art"]
        for s in styles:
            rf=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
            rf.pack(fill="x",padx=10,pady=1); rf.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(rf,text=s,font=ctk.CTkFont("Segoe UI",10),
                text_color=TXT2,fg_color=BG2).grid(row=0,column=0,sticky="w")
            ctk.CTkSwitch(rf,text="",variable=self._style_vars[s],
                progress_color=BLU3,button_color=TXT,text_color=TXT2,
                fg_color=BDR,onvalue=True,offvalue=False,width=44,height=22
            ).grid(row=0,column=1,sticky="e")

        # Content Type
        self._div(inner)
        self._lbl(inner,"CONTENT TYPE")
        self._ct_combo=ctk.CTkComboBox(inner,variable=self.ai_content_var,
            values=list(CONTENT_SUFFIXES.keys()),state="readonly",
            font=ctk.CTkFont("Segoe UI",10),fg_color=BG3,text_color=TXT,
            border_color=BDR,button_color=BLU3,button_hover_color=BLU2,
            dropdown_fg_color=BG4,dropdown_text_color=TXT,dropdown_hover_color=BLU2,
            corner_radius=6,height=32,command=lambda v:self._save_settings())
        self._ct_combo.pack(fill="x",padx=10,pady=(2,8))

        # Custom System Prompt
        self._div(inner)
        cp_hdr=ctk.CTkFrame(inner,fg_color=BG2,corner_radius=0)
        cp_hdr.pack(fill="x",padx=10)
        cp_hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(cp_hdr,text="Custom System Prompt",
            font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=TXT2,fg_color=BG2
        ).grid(row=0,column=0,sticky="w")
        ctk.CTkLabel(cp_hdr,text="Auto-Saved",
            font=ctk.CTkFont("Segoe UI",8),text_color=TXT3,fg_color=BG3,
            corner_radius=20,padx=6,pady=2).grid(row=0,column=1,sticky="e")
        self._custom_box=ctk.CTkTextbox(inner,height=70,
            font=ctk.CTkFont("Segoe UI",10),fg_color=BG3,text_color=TXT,
            border_color=BDR,border_width=1,corner_radius=6,wrap="word")
        self._custom_box.pack(fill="x",padx=10,pady=(4,4))
        if self.ai_custom_var.get():
            self._custom_box.insert("1.0",self.ai_custom_var.get())
        self._custom_box.bind("<KeyRelease>",lambda e:self._save_custom())

        # Reset to Default
        ctk.CTkButton(inner,text="↺  Reset to Default",height=28,
            font=ctk.CTkFont("Segoe UI",10),fg_color="transparent",
            hover_color=BDR,text_color=BLU,corner_radius=6,anchor="w",
            command=self._reset_defaults
        ).pack(anchor="w",padx=10,pady=(0,16))

    def _set_mode(self,mode):
        self.current_mode=mode
        if mode=="meta":
            self._meta_mode_btn.configure(fg_color=BLU3,text_color="white")
            self._prompt_mode_btn.configure(fg_color="transparent",text_color=TXT3)
            self._meta_sliders_frame.pack(fill="x")
            self._prompt_sliders_frame.pack_forget()
        else:
            self._prompt_mode_btn.configure(fg_color=BLU3,text_color="white")
            self._meta_mode_btn.configure(fg_color="transparent",text_color=TXT3)
            self._prompt_sliders_frame.pack(fill="x")
            self._meta_sliders_frame.pack_forget()
        # Rebuild existing cards if any
        self._clear_queue(confirm=False)

    def _reset_defaults(self):
        self.ai_title_var.set("120"); self._title_sl.set(120)
        self.ai_desc_var.set("200"); self._desc_sl.set(200)
        self.ai_kw_var.set("49"); self._kw_sl.set(49)
        self.ai_words_var.set("60"); self._words_sl.set(60)
        self.ai_content_var.set("Auto Detect")
        self._custom_box.delete("1.0","end")
        self.ai_custom_var.set("")
        for v in self._style_vars.values(): v.set(False)
        self._save_settings()

    # ── SIDEBAR HELPERS ────────────────────────────────────────────────
    def _div(self,parent):
        ctk.CTkFrame(parent,fg_color=BDR,height=1,corner_radius=0
        ).pack(fill="x",padx=8,pady=6)

    def _lbl(self,parent,text):
        ctk.CTkLabel(parent,text=text,font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=TXT3,fg_color=BG2).pack(anchor="w",padx=12,pady=(2,2))

    def _slider(self,parent,label,var,from_,to,init):
        fr=ctk.CTkFrame(parent,fg_color=BG2,corner_radius=0)
        fr.pack(fill="x",padx=10,pady=(0,6))
        fr.grid_columnconfigure(0,weight=1)
        top=ctk.CTkFrame(fr,fg_color=BG2,corner_radius=0); top.pack(fill="x")
        top.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(top,text=label,font=ctk.CTkFont("Segoe UI",10),
            text_color=TXT2,fg_color=BG2).grid(row=0,column=0,sticky="w")
        vl=ctk.CTkLabel(top,text=str(init),font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=BLU,fg_color=BG3,corner_radius=20,padx=6,pady=1)
        vl.grid(row=0,column=1)
        sl=ctk.CTkSlider(fr,from_=from_,to=to,number_of_steps=to-from_,
            progress_color=BLU3,fg_color=BG3,button_color="white",
            button_hover_color="#ddddff",height=14)
        sl.set(init); sl.pack(fill="x",pady=(2,0))
        def _upd(v): iv=int(v); var.set(str(iv)); vl.configure(text=str(iv)); self._save_settings()
        sl.configure(command=_upd)
        return sl

    def _save_settings(self):
        self.prefs.update({
            "platform":self.ai_platform_var.get(),
            "title_len":int(self.ai_title_var.get() or 120),
            "desc_len":int(self.ai_desc_var.get() or 200),
            "kw_count":int(self.ai_kw_var.get() or 49),
            "prompt_words":int(self.ai_words_var.get() or 60),
            "content_type":self.ai_content_var.get(),
        })
        save_prefs(self.prefs)

    def _save_custom(self):
        v=self._custom_box.get("1.0","end").strip()
        self.ai_custom_var.set(v); self.prefs["custom_prompt"]=v; save_prefs(self.prefs)

    def _refresh_api_lbl(self):
        seq=get_active_keys(self.prefs); total=len(seq)
        providers=list(dict.fromkeys(p for p,_,_ in seq))
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

        # TOP: platform tabs + action buttons
        topbar=ctk.CTkFrame(main,fg_color=BG2,corner_radius=0,height=50)
        topbar.grid(row=0,column=0,sticky="ew"); topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0,weight=1)

        plat_f=ctk.CTkFrame(topbar,fg_color=BG2,corner_radius=0)
        plat_f.grid(row=0,column=0,sticky="w",padx=8,pady=8)
        self._plat_btns={}
        for plat in PLATFORM_RULES.keys():
            short=plat.replace(" Stock","").replace(" Images","")[:8]
            btn=ctk.CTkButton(plat_f,text=short,width=70,height=28,
                font=ctk.CTkFont("Segoe UI",9,"bold"),
                fg_color=BLU3 if plat==self.ai_platform_var.get() else BG3,
                hover_color=BLU2,
                text_color="white" if plat==self.ai_platform_var.get() else TXT2,
                border_width=1,
                border_color=BLU3 if plat==self.ai_platform_var.get() else BDR,
                corner_radius=6,command=lambda p=plat:self._sel_platform(p))
            btn.pack(side="left",padx=(0,3))
            self._plat_btns[plat]=btn

        # Action buttons on right: Clear | [Stop/Download CSV] | Generate Batch
        btn_f=ctk.CTkFrame(topbar,fg_color=BG2,corner_radius=0)
        btn_f.grid(row=0,column=1,padx=8,pady=8,sticky="e")

        ctk.CTkButton(btn_f,text="🗑  Clear",width=80,height=30,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=BG3,hover_color=BDR,text_color=TXT3,corner_radius=8,
            command=lambda:self._clear_queue(confirm=True)
        ).pack(side="left",padx=(0,6))

        # Stop / Download CSV toggle
        self._stop_btn=ctk.CTkButton(btn_f,text="■  Stop",width=110,height=30,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=RED2,hover_color="#3d1515",text_color=RED,corner_radius=8,
            command=self._stop_ai)
        self._csv_btn=ctk.CTkButton(btn_f,text="⬇  Download CSV",width=140,height=30,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=GRN2,hover_color=GRN3,text_color=GRN,corner_radius=8,
            command=self._export_csv)
        # Show Download CSV by default, Stop during generation
        self._csv_btn.pack(side="left",padx=(0,6))

        self._retry_btn=ctk.CTkButton(btn_f,text="↺  Retry Failed",width=110,height=30,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=AMB2,hover_color="#3a2e00",text_color=AMB,corner_radius=8,
            command=self._retry_failed)
        # Hidden until failures exist

        self._gen_btn=ctk.CTkButton(btn_f,text="✨  Generate Batch",width=160,height=30,
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BLU3,hover_color=BLU2,text_color="white",corner_radius=8,
            command=self.start_generate)
        self._gen_btn.pack(side="left")

        # UPLOAD WORKSPACE (taller, with drop zone box)
        ws=ctk.CTkFrame(main,fg_color=CARD,corner_radius=0,
            border_width=1,border_color=BDR)
        ws.grid(row=1,column=0,sticky="ew")
        ws.grid_columnconfigure(1,weight=1)

        # Left: label + browse button stacked
        ws_left=ctk.CTkFrame(ws,fg_color=CARD,corner_radius=0,width=180)
        ws_left.grid(row=0,column=0,sticky="nsew",padx=14,pady=12)
        ws_left.grid_propagate(False)
        ctk.CTkLabel(ws_left,text="☁  Upload Workspace",
            font=ctk.CTkFont("Segoe UI",11,"bold"),text_color=TXT2,fg_color=CARD
        ).pack(anchor="w",pady=(4,8))
        ctk.CTkButton(ws_left,text="Browse Files",height=30,
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=BG3,hover_color=BDR,text_color=TXT2,
            border_width=1,border_color=BDR,corner_radius=8,
            command=self._browse_images
        ).pack(fill="x")

        # Right: dashed drop zone
        drop_box=ctk.CTkFrame(ws,fg_color=BG3,corner_radius=12,
            border_width=2,border_color=BDR2)
        drop_box.grid(row=0,column=1,sticky="ew",padx=(0,14),pady=12)
        drop_box.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(drop_box,text="🖼️  🎬  📄  🎨",
            font=ctk.CTkFont("Segoe UI",20),
            fg_color=BG3,text_color=TXT3).grid(row=0,column=0,pady=(16,4))
        ctk.CTkLabel(drop_box,
            text="Drag and drop files here or click Browse",
            font=ctk.CTkFont("Segoe UI",10,"bold"),
            fg_color=BG3,text_color=TXT3).grid(row=1,column=0)
        ctk.CTkLabel(drop_box,
            text="Supported: JPG, PNG, GIF, WEBP, TIFF",
            font=ctk.CTkFont("Segoe UI",9),
            fg_color=BG3,text_color=TXT3).grid(row=2,column=0,pady=(2,16))

        # Enable tkinterdnd2 drag-and-drop if available
        try:
            drop_box.drop_target_register("DND_Files")  # type: ignore
            drop_box.dnd_bind("<<Drop>>",self._on_drop)  # type: ignore
        except: pass

        # STATUS ROW (no gap — row 2 = cards directly)
        self._stats_bar=ctk.CTkFrame(main,fg_color=BG3,corner_radius=0,height=28)
        self._stats_bar.grid(row=2,column=0,sticky="ew"); self._stats_bar.grid_propagate(False)
        self._stats_bar.grid_columnconfigure(1,weight=1)
        self._status_dot2=ctk.CTkLabel(self._stats_bar,text="●",
            font=ctk.CTkFont("Segoe UI",10),text_color=GRN,fg_color=BG3,width=16)
        self._status_dot2.grid(row=0,column=0,padx=(10,4),pady=4)
        self._stats_lbl=ctk.CTkLabel(self._stats_bar,text="System Ready.",
            font=ctk.CTkFont("Segoe UI",9),text_color=TXT3,fg_color=BG3)
        self._stats_lbl.grid(row=0,column=1,sticky="w")

        # CARDS GRID — inside a bordered container, row 3
        main.grid_rowconfigure(3,weight=1)
        cards_border=ctk.CTkFrame(main,fg_color=BG2,corner_radius=0,
            border_width=1,border_color=BDR)
        cards_border.grid(row=3,column=0,sticky="nsew",padx=6,pady=6)
        cards_border.grid_columnconfigure(0,weight=1); cards_border.grid_rowconfigure(0,weight=1)

        self._cards_outer=ctk.CTkScrollableFrame(cards_border,fg_color=BG,
            scrollbar_button_color=BG3,scrollbar_button_hover_color=BDR,corner_radius=0)
        self._cards_outer.grid(row=0,column=0,sticky="nsew",padx=6,pady=6)
        self._cards_outer.grid_columnconfigure(0,weight=1)
        self._cards_outer.grid_columnconfigure(1,weight=1)

        self._empty_lbl=ctk.CTkLabel(self._cards_outer,
            text="No files in queue. Upload files to start.",
            font=ctk.CTkFont("Segoe UI",12),text_color=TXT3,fg_color=BG)
        self._empty_lbl.grid(row=0,column=0,columnspan=2,pady=40)

    def _sel_platform(self,plat):
        self.ai_platform_var.set(plat)
        rules=PLATFORM_RULES.get(plat,{})
        self._title_sl.set(rules.get("title",120)); self.ai_title_var.set(str(rules.get("title",120)))
        self._desc_sl.set(rules.get("desc",200));   self.ai_desc_var.set(str(rules.get("desc",200)))
        self._kw_sl.set(rules.get("kw",49));         self.ai_kw_var.set(str(rules.get("kw",49)))
        for p,btn in self._plat_btns.items():
            btn.configure(fg_color=BLU3 if p==plat else BG3,
                          text_color="white" if p==plat else TXT2,
                          border_color=BLU3 if p==plat else BDR)
        self._save_settings()

    def _on_drop(self,event):
        raw=event.data
        if '{' in raw:
            paths=[p.strip('{}') for p in raw.split()]
        else:
            paths=raw.split()
        self._add_images(paths)

    # ── Queue management ───────────────────────────────────────────────
    def _browse_images(self):
        paths=filedialog.askopenfilenames(title="Select images",
            filetypes=[("Images","*.jpg *.jpeg *.png *.webp *.gif *.tiff *.tif"),("All","*.*")])
        if paths: self._add_images(list(paths))

    def _add_images(self,paths):
        existing={c.path for c in self.cards}
        new=[p for p in paths if p not in existing
             and os.path.splitext(p)[1].lower() in IMAGE_EXTS]
        for path in new: self._add_card(path)
        self._update_stats()

    def _add_card(self,path):
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

    def _del_card(self,path):
        for c in self.cards:
            if c.path==path: c.destroy(); self.cards.remove(c); break
        self._regrid(); self._update_stats()
        if not self.cards: self._empty_lbl.grid(row=0,column=0,columnspan=2,pady=40)

    def _regrid(self):
        for i,card in enumerate(self.cards):
            r,c=i//2,i%2
            card.grid(row=r,column=c,sticky="ew",
                      padx=(4,2) if c==0 else (2,4),pady=(0,6))

    def _clear_queue(self,confirm=True):
        if self.ai_running: messagebox.showwarning("Busy","Stop generation first."); return
        if confirm and self.cards:
            if not messagebox.askyesno("Clear","Remove all images from queue?"): return
        for c in self.cards: c.destroy()
        self.cards.clear(); self._update_stats()
        try: self._retry_btn.pack_forget()
        except: pass
        self._empty_lbl.grid(row=0,column=0,columnspan=2,pady=40)

    def _update_stats(self):
        total=len(self.cards); done=sum(1 for c in self.cards if c.status=="done")
        failed=sum(1 for c in self.cards if c.status=="failed")
        pending=sum(1 for c in self.cards if c.status=="waiting")
        self._stats_lbl.configure(
            text=f"System Ready.   Files: {total}  |  Done: {done}  |  Failed: {failed}  |  Pending: {pending}"
            if total else "System Ready.")
        self.p_ok.configure(text=f"✓  {done} done")
        self.p_err.configure(text=f"✗  {failed} failed")
        self.p_pend.configure(text=f"○  {pending} pending")

    # ── Generate ───────────────────────────────────────────────────────
    def start_generate(self):
        if self.ai_running: messagebox.showwarning("Busy","Already generating."); return
        if not self.cards: messagebox.showerror("No Images","Add images first."); return
        if not get_active_keys(self.prefs):
            messagebox.showerror("No API Keys","Open 'Add API Keys' to add keys."); return
        self.ai_running=True; self.ai_stop_flag=False
        self._gen_btn.configure(state="disabled",text="⟳  Generating…")
        # Swap to Stop button
        self._csv_btn.pack_forget()
        self._stop_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        try: self._retry_btn.pack_forget()
        except: pass
        targets=[c for c in self.cards if c.status in ("waiting","failed")]
        for c in targets: c.set_status("waiting"); c.clear()
        threading.Thread(target=self._gen_thread,args=(targets,),daemon=True).start()

    def _stop_ai(self):
        self.ai_stop_flag=True; self.set_status("■  Stopping…",AMB)

    def _gen_thread(self,targets):
        mode=self.current_mode
        custom=self.ai_custom_var.get()
        ct=self.ai_content_var.get()
        styles=[s for s,v in self._style_vars.items() if v.get()]
        failed_paths=[]

        if mode=="meta":
            tc=int(self.ai_title_var.get() or 120)
            dc=int(self.ai_desc_var.get() or 200)
            kn=int(self.ai_kw_var.get() or 49)
            prompt=build_meta_prompt(tc,dc,kn,ct,custom)
        else:
            mw=int(self.ai_words_var.get() or 60)
            prompt=build_prompt_prompt(mw,styles,ct,custom)

        total=len(targets)
        for i,card in enumerate(targets):
            if self.ai_stop_flag: break
            fname=os.path.basename(card.path)
            self.after(0,lambda c=card:c.set_status("working"))
            self.after(0,lambda c=card:c.set_working())
            self.after(0,lambda f=fname,n=i+1,t=total:
                self.set_status(f"⟳  [{n}/{t}] {f}",BLU))
            try:
                raw,provider=call_with_failover(card.path,prompt,self.prefs,
                    status_cb=lambda msg:self.after(0,lambda m=msg:self.set_status(f"⟳  {m}",BLU)))
                if mode=="meta":
                    title,desc,kw=parse_meta(raw)
                    if not title and not kw: raise ValueError(f"Could not parse: {raw[:80]}")
                    self.after(0,lambda c=card,t=title,d=desc,k=kw:
                        (c.set_result(t,d,k),c.set_status("done")))
                else:
                    prompt_text=raw.strip()
                    self.after(0,lambda c=card,pt=prompt_text:
                        (c.set_result(pt),c.set_status("done")))
            except Exception as e:
                err=str(e)[:100]; failed_paths.append(card.path)
                self.after(0,lambda c=card,e=err:c.set_status("failed",e))
            self.after(0,self._update_stats)

        self.after(0,lambda fp=list(failed_paths):self._gen_done(fp))

    def _gen_done(self,failed_paths):
        self.ai_running=False
        self._gen_btn.configure(state="normal",text="✨  Generate Batch")
        # Swap Stop → Download CSV
        self._stop_btn.pack_forget()
        self._csv_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        if failed_paths:
            fset=set(failed_paths)
            failed_cards=[c for c in self.cards if c.path in fset]
            ok_cards=[c for c in self.cards if c.path not in fset]
            self.cards=failed_cards+ok_cards; self._regrid()
            self._retry_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        done=sum(1 for c in self.cards if c.status=="done")
        failed=sum(1 for c in self.cards if c.status=="failed")
        self.set_status(f"● Done — {done} done · {failed} failed",GRN if failed==0 else AMB)
        self._update_stats()

    def _regen_single(self,path):
        card=next((c for c in self.cards if c.path==path),None)
        if not card or self.ai_running: return
        card.set_status("waiting"); card.clear()
        self.ai_running=True; self.ai_stop_flag=False
        self._gen_btn.configure(state="disabled")
        self._csv_btn.pack_forget()
        self._stop_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        threading.Thread(target=self._gen_thread,args=([card],),daemon=True).start()

    def _retry_failed(self):
        failed=[c for c in self.cards if c.status=="failed"]
        if not failed: return
        for c in failed: c.set_status("waiting"); c.clear()
        try: self._retry_btn.pack_forget()
        except: pass
        self.ai_running=True; self.ai_stop_flag=False
        self._gen_btn.configure(state="disabled",text="⟳  Generating…")
        self._csv_btn.pack_forget()
        self._stop_btn.pack(side="left",padx=(0,6),before=self._gen_btn)
        threading.Thread(target=self._gen_thread,args=(failed,),daemon=True).start()

    def _export_csv(self):
        done=[c for c in self.cards if c.status=="done"]
        if not done: messagebox.showinfo("No Results","No generated results yet."); return
        ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        mode=self.current_mode
        path=filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            initialfile=f"metazone_{mode}_{ts}.csv")
        if not path: return
        try:
            fields=["Filename","Title","Description","Keywords"] if mode=="meta" else ["Filename","Prompt"]
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
                w.writerows(c.get_result() for c in done)
            self.set_status(f"✓  CSV saved — {len(done)} rows",GRN)
            messagebox.showinfo("Saved",f"CSV saved:\n{path}")
        except Exception as e: messagebox.showerror("Error",str(e))

    # ══════════════════════════════════════════════════════════════════
    #  EMBED TAB
    # ══════════════════════════════════════════════════════════════════
    def _build_embed_tab(self,parent):
        parent.grid_columnconfigure(0,weight=1); parent.grid_columnconfigure(1,weight=0)
        parent.grid_rowconfigure(0,weight=1)
        left=ctk.CTkScrollableFrame(parent,fg_color=BG,
            scrollbar_button_color=BG3,corner_radius=0)
        left.grid(row=0,column=0,sticky="nsew",padx=(14,6),pady=12)
        left.grid_columnconfigure(0,weight=1)
        self._el=left
        log_outer=ctk.CTkFrame(parent,fg_color=BG2,corner_radius=20,
            border_width=1,border_color=BDR,width=210)
        log_outer.grid(row=0,column=1,sticky="nsew",padx=(0,10),pady=10)
        log_outer.grid_propagate(False); log_outer.grid_rowconfigure(1,weight=1)
        log_outer.grid_columnconfigure(0,weight=1)
        self._build_embed_log(log_outer)
        self._build_emb_actions(); self._build_csv_card()
        self._build_folder_card(); self._build_map_card()

    def _ec(self):
        f=ctk.CTkFrame(self._el,fg_color=BG2,corner_radius=20,border_width=1,border_color=BDR)
        f.pack(fill="x",pady=(0,10)); f.grid_columnconfigure(0,weight=1); return f

    def _ech(self,p,num,title,bcmd=None):
        h=ctk.CTkFrame(p,fg_color=BG3,corner_radius=20,height=50)
        h.pack(fill="x"); h.grid_propagate(False); h.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(h,text=str(num),font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=GRN2,text_color="white",corner_radius=50,width=36,height=36
        ).grid(row=0,column=0,padx=(14,10),pady=7)
        ctk.CTkLabel(h,text=title,font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=TXT2,fg_color=BG3).grid(row=0,column=1,sticky="w")
        if bcmd:
            ctk.CTkButton(h,text="Browse",width=95,height=32,
                font=ctk.CTkFont("Segoe UI",11,"bold"),
                fg_color=GRN2,hover_color=GRN3,text_color="white",corner_radius=20,
                command=bcmd).grid(row=0,column=2,padx=(0,12),pady=9)

    def _esw(self,p,t,v):
        return ctk.CTkSwitch(p,text=t,variable=v,
            font=ctk.CTkFont("Segoe UI",12),progress_color=GRN2,
            button_color=TXT,text_color=TXT2,fg_color=BDR,
            onvalue=True,offvalue=False,width=56,height=28)

    def _build_emb_actions(self):
        row=ctk.CTkFrame(self._el,fg_color=BG,corner_radius=0)
        row.pack(fill="x",pady=(0,10)); row.grid_columnconfigure(0,weight=1)
        self.embed_btn=ctk.CTkButton(row,text="▶  Start Embedding",
            font=ctk.CTkFont("Segoe UI",15,"bold"),
            fg_color=GRN2,hover_color=GRN3,text_color="white",
            height=54,corner_radius=27,command=self.start_embed)
        self.embed_btn.grid(row=0,column=0,sticky="ew")
        ctk.CTkButton(row,text="↺",width=54,height=54,
            font=ctk.CTkFont("Segoe UI",20,"bold"),
            fg_color=RED2,hover_color="#3d1515",text_color=RED,
            corner_radius=27,command=self.reset_embed
        ).grid(row=0,column=1,padx=(8,0))
        ctk.CTkButton(row,text="💾  Save Log",width=130,height=54,
            font=ctk.CTkFont("Segoe UI",12,"bold"),
            fg_color=BG3,hover_color=BDR,text_color=TXT2,
            corner_radius=27,command=self.export_log
        ).grid(row=0,column=2,padx=(8,0))

    def _build_csv_card(self):
        c=self._ec(); self._ech(c,"1","Load CSV",self.load_csv)
        body=ctk.CTkFrame(c,fg_color=BG2,corner_radius=0)
        body.pack(fill="x",padx=14,pady=(10,12)); body.grid_columnconfigure(0,weight=1)
        ctk.CTkEntry(body,textvariable=self.csv_path_var,state="readonly",height=40,
            font=ctk.CTkFont("Segoe UI",12),fg_color=BG3,text_color=TXT,
            border_color=BDR,corner_radius=20).pack(fill="x",pady=(0,10))
        row=ctk.CTkFrame(body,fg_color=BG2,corner_radius=0); row.pack(fill="x")
        row.grid_columnconfigure(0,weight=1)
        self.csv_badge=ctk.CTkLabel(row,text="No CSV loaded",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,text_color=TXT3,corner_radius=20,padx=12,pady=5)
        self.csv_badge.grid(row=0,column=0,sticky="w")
        self._esw(row,"Match Filename Only",self.match_only_var).grid(row=0,column=1,sticky="e",padx=(10,0))

    def _build_folder_card(self):
        c=self._ec(); self._ech(c,"2","Image Folder",self.browse_embed_folder)
        body=ctk.CTkFrame(c,fg_color=BG2,corner_radius=0)
        body.pack(fill="x",padx=14,pady=(10,12)); body.grid_columnconfigure(0,weight=1)
        ctk.CTkEntry(body,textvariable=self.folder_path_var,state="readonly",height=40,
            font=ctk.CTkFont("Segoe UI",12),fg_color=BG3,text_color=TXT,
            border_color=BDR,corner_radius=20).pack(fill="x",pady=(0,10))
        row=ctk.CTkFrame(body,fg_color=BG2,corner_radius=0); row.pack(fill="x")
        row.grid_columnconfigure(0,weight=1)
        self.folder_badge=ctk.CTkLabel(row,text="No folder selected",
            font=ctk.CTkFont("Segoe UI",11,"bold"),
            fg_color=BG3,text_color=TXT3,corner_radius=20,padx=12,pady=5)
        self.folder_badge.grid(row=0,column=0,sticky="w")
        self._esw(row,"Include Sub-Folders",self.subfolder_var).grid(row=0,column=1,sticky="e",padx=(10,0))

    def _build_map_card(self):
        c=self._ec(); self._ech(c,"3","Map Columns")
        body=ctk.CTkFrame(c,fg_color=BG2,corner_radius=0)
        body.pack(fill="x",padx=14,pady=(10,12))
        body.grid_columnconfigure(0,weight=1); body.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(body,text="Auto-detected from column names.",
            font=ctk.CTkFont("Segoe UI",11),text_color=TXT3,fg_color=BG2
        ).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,10))
        self.col_combos={}
        fields=[("FILENAME",self.col_file_var),("TITLE",self.col_title_var),
                ("KEYWORDS",self.col_kw_var),("DESCRIPTION",self.col_desc_var)]
        for i,(lbl,var) in enumerate(fields):
            r=(i//2)+1; col=i%2
            cell=ctk.CTkFrame(body,fg_color=BG2,corner_radius=0)
            cell.grid(row=r,column=col,sticky="ew",padx=(0 if col==0 else 8,0),pady=5)
            cell.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(cell,text=lbl,font=ctk.CTkFont("Segoe UI",10,"bold"),
                text_color=TXT3,fg_color=BG2).pack(anchor="w")
            cb=ctk.CTkComboBox(cell,variable=var,values=["(skip)"],state="readonly",
                font=ctk.CTkFont("Segoe UI",12),fg_color=BG3,text_color=TXT,
                border_color=BDR,button_color=GRN2,button_hover_color=GRN3,
                dropdown_fg_color=BG4,dropdown_text_color=TXT,dropdown_hover_color=GRN3,
                corner_radius=20,height=38,command=lambda v:self._update_match())
            cb.pack(fill="x",pady=(4,0)); self.col_combos[lbl]=cb
        ctk.CTkFrame(body,fg_color=BDR,height=1,corner_radius=0).grid(
            row=3,column=0,columnspan=2,sticky="ew",pady=(14,10))
        rm=ctk.CTkFrame(body,fg_color=BG3,corner_radius=20)
        rm.grid(row=4,column=0,columnspan=2,sticky="ew",pady=(0,4))
        rm.grid_columnconfigure(0,weight=1)
        info=ctk.CTkFrame(rm,fg_color=BG3,corner_radius=0)
        info.grid(row=0,column=0,sticky="w",padx=14,pady=12)
        ctk.CTkLabel(info,text="Remove Program Name",
            font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=TXT2,fg_color=BG3).pack(anchor="w")
        ctk.CTkLabel(info,text="Clears upscaler/software name from metadata",
            font=ctk.CTkFont("Segoe UI",11),text_color=TXT3,fg_color=BG3).pack(anchor="w")
        self._esw(rm,"On",self.rm_prog_var).grid(row=0,column=1,padx=(0,14),pady=12)

    def _build_embed_log(self,parent):
        hdr=ctk.CTkFrame(parent,fg_color=BG3,corner_radius=20,height=44)
        hdr.grid(row=0,column=0,sticky="ew",padx=8,pady=(8,4)); hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(hdr,text="ACTIVITY LOG",font=ctk.CTkFont("Segoe UI",11,"bold"),
            text_color=TXT3,fg_color=BG3).grid(row=0,column=0,sticky="w",padx=12)
        ctk.CTkButton(hdr,text="Clear",width=58,height=28,fg_color=BG4,hover_color=BDR,
            text_color=TXT3,corner_radius=20,command=self.clear_log
        ).grid(row=0,column=1,padx=(0,8))
        self.log_text=ctk.CTkTextbox(parent,font=ctk.CTkFont("Consolas",11),
            fg_color=LOG_BG,text_color=TXT,corner_radius=20,wrap="word",state="disabled",
            scrollbar_button_color=BG3,scrollbar_button_hover_color=BDR)
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
        self.csv_badge.configure(text="No CSV loaded",fg_color=BG3,text_color=TXT3)
        self.folder_badge.configure(text="No folder selected",fg_color=BG3,text_color=TXT3)
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
        sb=ctk.CTkFrame(self,fg_color=BG4,corner_radius=0,height=38)
        sb.grid(row=3,column=0,sticky="ew"); sb.grid_propagate(False)
        sb.grid_columnconfigure(4,weight=1)
        self.p_ok=ctk.CTkLabel(sb,text="✓  0 done",font=ctk.CTkFont("Segoe UI",9,"bold"),
            fg_color=GRN3,text_color=GRN,corner_radius=20,padx=10,pady=3)
        self.p_ok.grid(row=0,column=0,padx=(10,4),pady=7)
        self.p_err=ctk.CTkLabel(sb,text="✗  0 failed",font=ctk.CTkFont("Segoe UI",9,"bold"),
            fg_color=RED2,text_color=RED,corner_radius=20,padx=10,pady=3)
        self.p_err.grid(row=0,column=1,padx=4,pady=7)
        self.p_pend=ctk.CTkLabel(sb,text="○  0 pending",font=ctk.CTkFont("Segoe UI",9,"bold"),
            fg_color=AMB2,text_color=AMB,corner_radius=20,padx=10,pady=3)
        self.p_pend.grid(row=0,column=2,padx=4,pady=7)
        self.sb_status=ctk.CTkLabel(sb,text="",font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color=BLU,fg_color=BG4)
        self.sb_status.grid(row=0,column=3,padx=(8,0),sticky="w")
        self.sb_prog=ctk.CTkProgressBar(sb,progress_color=GRN,fg_color=BG3,
            height=5,corner_radius=3,width=80)
        self.sb_prog.grid(row=0,column=5,padx=(0,4)); self.sb_prog.set(0)
        self.sb_pct=ctk.CTkLabel(sb,text="",font=ctk.CTkFont("Segoe UI",9),
            text_color=TXT2,fg_color=BG4); self.sb_pct.grid(row=0,column=6,padx=(0,6))
        self.sb_et=ctk.CTkLabel(sb,text="ExifTool · checking…",
            font=ctk.CTkFont("Segoe UI",9),text_color=TXT3,fg_color=BG4)
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
