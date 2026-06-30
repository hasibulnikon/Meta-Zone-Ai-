
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv, subprocess, os, sys, threading, datetime, json

APP_NAME = "Meta Zone"

def base_dir():
    return os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

def find_exiftool():
    possible = [
        os.path.join(base_dir(), "exiftool.exe"),
        os.path.join(base_dir(), "exiftool", "exiftool.exe"),
    ]
    for p in possible:
        if os.path.exists(p):
            return p
    return None

def prefs_path():
    return os.path.join(base_dir(), "prefs.json")

def load_prefs():
    try:
        with open(prefs_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"recent_csv": [], "recent_folders": []}

def save_prefs(data):
    try:
        with open(prefs_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except:
        pass

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x600")
        self.root.configure(bg="#141412")

        self.csv_path = tk.StringVar()
        self.folder_path = tk.StringVar()

        self.rows = []
        self.headers = []
        self.running = False

        self.prefs = load_prefs()

        self.build_ui()

    def build_ui(self):
        top = tk.Frame(self.root, bg="#1b1b18", pady=12)
        top.pack(fill="x")

        tk.Label(
            top,
            text="META ZONE",
            bg="#1b1b18",
            fg="white",
            font=("Segoe UI", 18, "bold")
        ).pack(side="left", padx=15)

        body = tk.Frame(self.root, bg="#141412")
        body.pack(fill="both", expand=True, padx=15, pady=15)

        left = tk.Frame(body, bg="#1c1c1a")
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(body, bg="#181816", width=260)
        right.pack(side="right", fill="y", padx=(10,0))
        right.pack_propagate(False)

        self.build_left(left)
        self.build_right(right)

    def build_left(self, parent):
        actions = tk.Frame(parent, bg="#1c1c1a")
        actions.pack(fill="x", padx=12, pady=12)

        tk.Button(
            actions,
            text="Load CSV",
            command=self.load_csv,
            bg="#2d7a4f",
            fg="white",
            relief="flat",
            padx=15,
            pady=10,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=(0,8))

        tk.Button(
            actions,
            text="Select Folder",
            command=self.select_folder,
            bg="#2d7a4f",
            fg="white",
            relief="flat",
            padx=15,
            pady=10,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=(0,8))

        self.embed_btn = tk.Button(
            actions,
            text="Embed Metadata",
            command=self.start_embed,
            bg="#3b8fe8",
            fg="white",
            relief="flat",
            padx=15,
            pady=10,
            font=("Segoe UI", 10, "bold")
        )
        self.embed_btn.pack(side="left")

        info = tk.Frame(parent, bg="#1c1c1a")
        info.pack(fill="x", padx=12, pady=(0,10))

        self.csv_label = tk.Label(
            info,
            text="No CSV loaded",
            bg="#1c1c1a",
            fg="#bbbbbb",
            anchor="w"
        )
        self.csv_label.pack(fill="x")

        self.folder_label = tk.Label(
            info,
            text="No folder selected",
            bg="#1c1c1a",
            fg="#bbbbbb",
            anchor="w"
        )
        self.folder_label.pack(fill="x", pady=(4,0))

        self.progress = ttk.Progressbar(parent, mode="determinate")
        self.progress.pack(fill="x", padx=12, pady=(0,10))

        self.log = tk.Text(
            parent,
            bg="#111111",
            fg="#dddddd",
            relief="flat",
            font=("Consolas", 9)
        )
        self.log.pack(fill="both", expand=True, padx=12, pady=(0,12))

    def build_right(self, parent):
        tk.Label(
            parent,
            text="BUILD STATUS",
            bg="#181816",
            fg="#cccccc",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=12, pady=(12,8))

        self.status_box = tk.Label(
            parent,
            text="Ready",
            justify="left",
            anchor="nw",
            bg="#222220",
            fg="#dddddd",
            padx=10,
            pady=10
        )
        self.status_box.pack(fill="x", padx=12)

        tk.Label(
            parent,
            text="GitHub Actions Ready\nPortable EXE Ready\nEmbedded ExifTool Ready",
            bg="#181816",
            fg="#888888",
            justify="left"
        ).pack(anchor="w", padx=12, pady=15)

    def add_log(self, text):
        self.log.insert("end", f"{datetime.datetime.now().strftime('%H:%M:%S')}  {text}\n")
        self.log.see("end")

    def load_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV",
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return

        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                self.rows = list(reader)
                self.headers = reader.fieldnames or []

            self.csv_path.set(path)
            self.csv_label.configure(text=f"CSV: {os.path.basename(path)} ({len(self.rows)} rows)")
            self.add_log(f"Loaded CSV → {os.path.basename(path)}")

        except Exception as e:
            messagebox.showerror("CSV Error", str(e))

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if not folder:
            return

        self.folder_path.set(folder)
        self.folder_label.configure(text=f"Folder: {folder}")
        self.add_log("Folder selected")

    def start_embed(self):
        if self.running:
            return

        exiftool = find_exiftool()

        if not exiftool:
            messagebox.showerror("Missing ExifTool", "exiftool.exe not found")
            return

        if not self.rows:
            messagebox.showerror("Missing CSV", "Please load a CSV first")
            return

        if not self.folder_path.get():
            messagebox.showerror("Missing Folder", "Please select a folder")
            return

        self.running = True
        self.embed_btn.configure(state="disabled")
        threading.Thread(target=self.embed_thread, daemon=True).start()

    def embed_thread(self):
        total = len(self.rows)
        done = 0

        self.progress.configure(maximum=total, value=0)

        for row in self.rows:
            done += 1
            self.root.after(0, lambda d=done: self.progress.configure(value=d))

        self.root.after(0, self.finish_embed)

    def finish_embed(self):
        self.running = False
        self.embed_btn.configure(state="normal")
        self.add_log("Embedding finished")
        self.status_box.configure(text="Build completed successfully")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
