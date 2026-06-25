"""Tkinter desktop UI for the CROUS accommodation notifier.

Lets a non-technical user fill in the Mailjet + CROUS settings, manage the
important / blacklisted dorm lists, and run/stop the watcher while watching its
output in an embedded terminal-like panel. Reads and writes the json config
files next to the executable (see crous_notifier.app_dir).
"""

import json
import os
import queue
import threading
import webbrowser

import tkinter as tk
from tkinter import ttk, messagebox

from crous_notifier import run_notifier, app_dir

CROUS_SITE = "https://trouverunlogement.lescrous.fr/"

# Catppuccin Mocha palette — modern, easy on the eyes in the dark.
C = {
    "bg": "#1e1e2e",
    "panel": "#181825",
    "entry": "#313244",
    "border": "#45475a",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "blue": "#89b4fa",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
    "dark_text": "#11111b",
}

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_MONO = ("Consolas", 10)


def config_path(name):
    return os.path.join(app_dir(), name)


def read_config(name):
    """Load a config dict, falling back to its .example template, then {}."""
    candidates = [config_path(name),
                  config_path(name.replace(".json", ".example.json"))]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
    return {}


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable frame so the config fits on low-res screens."""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.body = ttk.Frame(self.canvas, style="Card.TFrame")
        self._win = self.canvas.create_window((0, 0), window=self.body,
                                              anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))
        # Only grab the wheel while the pointer is over this area.
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all(
            "<MouseWheel>"))

    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")


class ListManager(ttk.Frame):
    """A labelled listbox with add / edit / remove controls."""

    def __init__(self, master, title, hint=""):
        super().__init__(master, style="Card.TFrame")
        ttk.Label(self, text=title, style="Section.TLabel").pack(
            anchor="w", pady=(0, 2))
        if hint:
            ttk.Label(self, text=hint, style="Hint.TLabel").pack(
                anchor="w", pady=(0, 4))

        self.listbox = tk.Listbox(
            self, height=4, bg=C["entry"], fg=C["text"],
            selectbackground=C["blue"], selectforeground=C["dark_text"],
            highlightthickness=1, highlightbackground=C["border"],
            relief="flat", font=FONT, activestyle="none")
        self.listbox.pack(fill="x")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        row = ttk.Frame(self, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        self.entry = ttk.Entry(row)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self._add())
        ttk.Button(row, text="Add", width=7,
                   command=self._add).pack(side="left", padx=(6, 0))
        ttk.Button(row, text="Edit", width=7,
                   command=self._edit).pack(side="left", padx=(6, 0))
        ttk.Button(row, text="Remove", width=8,
                   command=self._remove).pack(side="left", padx=(6, 0))

    def _on_select(self, _event):
        sel = self.listbox.curselection()
        if sel:
            self.entry.delete(0, "end")
            self.entry.insert(0, self.listbox.get(sel[0]))

    def _add(self):
        value = self.entry.get().strip()
        if value:
            self.listbox.insert("end", value)
            self.entry.delete(0, "end")

    def _edit(self):
        sel = self.listbox.curselection()
        value = self.entry.get().strip()
        if sel and value:
            idx = sel[0]
            self.listbox.delete(idx)
            self.listbox.insert(idx, value)
            self.listbox.selection_set(idx)

    def _remove(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.delete(sel[0])
            self.entry.delete(0, "end")

    def set_items(self, items):
        self.listbox.delete(0, "end")
        for item in items or []:
            self.listbox.insert("end", item)

    def get_items(self):
        return list(self.listbox.get(0, "end"))


class NotifierApp:
    def __init__(self, root):
        self.root = root
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = None
        self.running = False

        root.title("CROUS Accommodation Notifier")
        root.geometry("980x620")
        root.minsize(640, 460)
        root.configure(bg=C["bg"])

        self._build_styles()
        self._build_layout()
        self._load_into_form()
        self.root.after(100, self._poll_log)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- theming -----------------------------------------------------------
    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=C["bg"], foreground=C["text"],
                        font=FONT)
        style.configure("TFrame", background=C["bg"])
        style.configure("Card.TFrame", background=C["bg"])
        style.configure("TLabel", background=C["bg"], foreground=C["text"])
        style.configure("Title.TLabel", background=C["bg"], foreground=C["blue"],
                        font=FONT_TITLE)
        style.configure("Section.TLabel", background=C["bg"],
                        foreground=C["yellow"], font=FONT_BOLD)
        style.configure("Hint.TLabel", background=C["bg"],
                        foreground=C["subtext"], font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=C["panel"],
                        foreground=C["subtext"])

        style.configure("TEntry", fieldbackground=C["entry"],
                        foreground=C["text"], insertcolor=C["text"],
                        bordercolor=C["border"], lightcolor=C["border"],
                        darkcolor=C["border"])
        style.map("TEntry", fieldbackground=[("focus", C["entry"])],
                  bordercolor=[("focus", C["blue"])])

        style.configure("TButton", background=C["border"], foreground=C["text"],
                        bordercolor=C["border"], focusthickness=0, padding=5)
        style.map("TButton", background=[("active", C["blue"]),
                                         ("disabled", C["panel"])],
                  foreground=[("active", C["dark_text"]),
                              ("disabled", C["subtext"])])

        style.configure("Run.TButton", background=C["green"],
                        foreground=C["dark_text"], font=FONT_BOLD, padding=7)
        style.map("Run.TButton", background=[("active", "#94d3a2"),
                                             ("disabled", C["panel"])],
                  foreground=[("disabled", C["subtext"])])
        style.configure("Stop.TButton", background=C["red"],
                        foreground=C["dark_text"], font=FONT_BOLD, padding=7)
        style.map("Stop.TButton", background=[("active", "#eb6f84"),
                                              ("disabled", C["panel"])],
                  foreground=[("disabled", C["subtext"])])
        style.configure("Accent.TButton", background=C["blue"],
                        foreground=C["dark_text"])
        style.map("Accent.TButton", background=[("active", "#a6c8ff")])

        style.configure("Vertical.TScrollbar", background=C["border"],
                        troughcolor=C["panel"], bordercolor=C["bg"],
                        arrowcolor=C["text"])
        style.configure("TPanedwindow", background=C["bg"])

    # ---- layout ------------------------------------------------------------
    def _build_layout(self):
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=14, pady=(12, 6))
        ttk.Label(header, text="CROUS Accommodation Notifier",
                  style="Title.TLabel").pack(side="left")

        paned = ttk.PanedWindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=14, pady=6)

        # --- left: configuration (scrollable) ---
        left = ScrollableFrame(paned)
        paned.add(left, weight=3)
        cfg = left.body
        for c in range(2):
            cfg.columnconfigure(c, weight=1)
        pad = {"padx": 10, "pady": 4}

        self.fields = {}

        def add_field(parent, label, key, show=None):
            ttk.Label(parent, text=label).pack(anchor="w")
            entry = ttk.Entry(parent, show=show)
            entry.pack(fill="x", pady=(0, 6))
            self.fields[key] = entry

        # Mailjet section
        ttk.Label(cfg, text="Email settings (Mailjet)",
                  style="Section.TLabel").pack(anchor="w", **pad)
        mail = ttk.Frame(cfg, style="Card.TFrame")
        mail.pack(fill="x", padx=10)
        add_field(mail, "Mailjet API key (public)", "mailjet_api_public_key")
        add_field(mail, "Mailjet secret key", "mailjet_api_secret_key",
                  show="•")
        add_field(mail, "Sender email (your Mailjet account)", "email_sender")
        add_field(mail, "Receiver email (where alerts arrive)", "email_receiver")
        add_field(mail, "Second receiver (optional)", "email_receiver2")

        # CROUS section
        ttk.Label(cfg, text="CROUS search region",
                  style="Section.TLabel").pack(anchor="w", **pad)
        crous = ttk.Frame(cfg, style="Card.TFrame")
        crous.pack(fill="x", padx=10)
        ttk.Label(crous, text="1) Open the CROUS site, zoom the map on your "
                  "area, then copy the URL\nfrom the address bar and paste it "
                  "below.", style="Hint.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Button(crous, text="Open CROUS site ↗", style="Accent.TButton",
                   command=lambda: webbrowser.open(CROUS_SITE)).pack(
            anchor="w", pady=(0, 6))
        ttk.Label(crous, text="Region search URL").pack(anchor="w")
        url_entry = ttk.Entry(crous)
        url_entry.pack(fill="x", pady=(0, 6))
        self.fields["crous_map_location_url"] = url_entry

        # Lists
        lists = ttk.Frame(cfg, style="Card.TFrame")
        lists.pack(fill="x", padx=10, pady=(6, 4))
        self.important_list = ListManager(
            lists, "Important places",
            "Alerts mentioning these get an IMPORTANT subject.")
        self.important_list.pack(fill="x", pady=(0, 8))
        self.blacklist = ListManager(
            lists, "Blacklisted places",
            "If every found place is here, no email is sent.")
        self.blacklist.pack(fill="x")

        # --- right: terminal-like output ---
        right = ttk.Frame(paned)
        paned.add(right, weight=2)
        ttk.Label(right, text="Output", style="Section.TLabel").pack(
            anchor="w", pady=(0, 4))
        term = ttk.Frame(right)
        term.pack(fill="both", expand=True)
        self.output = tk.Text(term, bg=C["panel"], fg=C["green"],
                              insertbackground=C["text"], relief="flat",
                              font=FONT_MONO, wrap="word", state="disabled",
                              highlightthickness=1,
                              highlightbackground=C["border"])
        out_sb = ttk.Scrollbar(term, orient="vertical",
                               command=self.output.yview)
        self.output.configure(yscrollcommand=out_sb.set)
        out_sb.pack(side="right", fill="y")
        self.output.pack(side="left", fill="both", expand=True)

        # --- bottom bar ---
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=14, pady=(6, 12))
        ttk.Button(bar, text="Save settings",
                   command=self._save_config).pack(side="left")
        self.run_btn = ttk.Button(bar, text="▶  Run", style="Run.TButton",
                                  command=self._start)
        self.run_btn.pack(side="right")
        self.stop_btn = ttk.Button(bar, text="■  Stop", style="Stop.TButton",
                                   command=self._stop, state="disabled")
        self.stop_btn.pack(side="right", padx=(0, 8))
        self.status = ttk.Label(bar, text="Idle", style="Status.TLabel")
        self.status.pack(side="left", padx=12)

    # ---- config <-> form ---------------------------------------------------
    def _load_into_form(self):
        crous = read_config("crous_config.json")
        mail = read_config("mailjet_config.json")
        for key in ("mailjet_api_public_key", "mailjet_api_secret_key",
                    "email_sender", "email_receiver", "email_receiver2"):
            self.fields[key].insert(0, str(mail.get(key, "")))
        self.fields["crous_map_location_url"].insert(
            0, str(crous.get("crous_map_location_url", "")))
        self.important_list.set_items(crous.get("important_crous_list", []))
        self.blacklist.set_items(crous.get("blacklisted_crous_list", []))

    def _collect_crous(self):
        return {
            "crous_map_location_url":
                self.fields["crous_map_location_url"].get().strip(),
            "important_crous_list": self.important_list.get_items(),
            "blacklisted_crous_list": self.blacklist.get_items(),
        }

    def _collect_mailjet(self):
        return {key: self.fields[key].get().strip() for key in (
            "mailjet_api_public_key", "mailjet_api_secret_key",
            "email_sender", "email_receiver", "email_receiver2")}

    def _save_config(self, silent=False):
        try:
            with open(config_path("crous_config.json"), "w") as f:
                json.dump(self._collect_crous(), f, indent=2)
            with open(config_path("mailjet_config.json"), "w") as f:
                json.dump(self._collect_mailjet(), f, indent=2)
        except OSError as e:
            messagebox.showerror("Save failed", str(e))
            return False
        if not silent:
            self._set_status("Settings saved")
        return True

    # ---- run / stop --------------------------------------------------------
    def _start(self):
        if self.running:
            return
        if not self._save_config(silent=True):
            return
        crous_cfg = self._collect_crous()
        mail_cfg = self._collect_mailjet()
        if not crous_cfg["crous_map_location_url"] or \
                "put here" in crous_cfg["crous_map_location_url"]:
            messagebox.showwarning(
                "Missing URL", "Please paste your CROUS region search URL "
                "first (use the 'Open CROUS site' button).")
            return
        if "@" not in mail_cfg["email_receiver"]:
            if not messagebox.askyesno(
                    "Email not set",
                    "The receiver email looks unset, so notifications can't be "
                    "sent. Run anyway?"):
                return

        self.stop_event.clear()
        self.running = True
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._set_status("Running")
        self.thread = threading.Thread(
            target=self._run_thread, args=(crous_cfg, mail_cfg), daemon=True)
        self.thread.start()

    def _run_thread(self, crous_cfg, mail_cfg):
        try:
            run_notifier(crous_cfg, mail_cfg, log=self.log_queue.put,
                         should_stop=self.stop_event.is_set)
        except SystemExit as e:
            self.log_queue.put(str(e))
        except Exception as e:  # surface any startup/driver failure
            self.log_queue.put(f"Fatal error: {e}")

    def _stop(self):
        if self.running:
            self.stop_event.set()
            self.stop_btn.configure(state="disabled")
            self._set_status("Stopping…")
            self.log_queue.put("Stopping… (finishing current step)")

    # ---- log pump ----------------------------------------------------------
    def _append(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def _poll_log(self):
        try:
            while True:
                self._append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        if self.running and self.thread and not self.thread.is_alive():
            self.running = False
            self.run_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self._set_status("Idle")
        self.root.after(100, self._poll_log)

    def _set_status(self, text):
        self.status.configure(text=text)

    def _on_close(self):
        if self.running:
            if not messagebox.askokcancel(
                    "Quit", "The notifier is still running. Stop and quit?"):
                return
            self.stop_event.set()
        self.root.destroy()


def main():
    root = tk.Tk()
    NotifierApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
