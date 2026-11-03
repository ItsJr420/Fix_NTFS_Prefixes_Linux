#!/usr/bin/env python3
"""

Run:  python3 fix_ntfs_prefixes_gui.py
Needs tkinter (Debian/Ubuntu: sudo apt install python3-tk, Fedora: sudo dnf install python3-tkinter,
Arch: sudo pacman -S tk).

"""

import queue
import threading
import tkinter as tk
from contextlib import redirect_stdout
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import fix_ntfs_prefixes as core


class QueueWriter:
    

    def __init__(self, q):
        self.q = q

    def write(self, s):
        if s:
            self.q.put(s)

    def flush(self):
        pass


class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.master = master
        self.q = queue.Queue()
        self.busy = False
        self.libraries = []

        self.target = tk.StringVar(value=str(Path.home() / "steam-compatdata"))
        self.only_foreign = tk.BooleanVar(value=False)
        self.dry_run = tk.BooleanVar(value=True)

        self._build()
        self.pack(fill="both", expand=True)
        self.after(100, self._poll)

    # ---------- UI ----------
    def _build(self):
        self.master.title("Move Proton Prefixes off NTFS")
        self.master.geometry("760x640")
        self.master.minsize(620, 520)

        # Libraries
        lib = ttk.LabelFrame(self, text="Steam libraries (steamapps/compatdata folders)", padding=8)
        lib.pack(fill="x")

        row = ttk.Frame(lib)
        row.pack(fill="x")
        self.listbox = tk.Listbox(row, height=5, selectmode="extended", activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(row, orient="vertical", command=self.listbox.yview)
        sb.pack(side="left", fill="y")
        self.listbox.config(yscrollcommand=sb.set)

        btns = ttk.Frame(lib)
        btns.pack(fill="x", pady=(6, 0))
        self.detect_btn = ttk.Button(btns, text="Auto-detect NTFS libraries", command=self.detect)
        self.detect_btn.pack(side="left")
        ttk.Button(btns, text="Add folder…", command=self.add_folder).pack(side="left", padx=6)
        ttk.Button(btns, text="Remove selected", command=self.remove_selected).pack(side="left")

        # Options
        opt = ttk.LabelFrame(self, text="Options", padding=8)
        opt.pack(fill="x", pady=10)

        trow = ttk.Frame(opt)
        trow.pack(fill="x")
        ttk.Label(trow, text="Store prefixes in:").pack(side="left")
        ttk.Entry(trow, textvariable=self.target).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(trow, text="Browse…", command=self.browse_target).pack(side="left")

        ttk.Checkbutton(opt, text="Only move prefixes not owned by my user",
                        variable=self.only_foreign).pack(anchor="w", pady=(8, 0))
        ttk.Checkbutton(opt, text="Dry run (show what would happen, change nothing)",
                        variable=self.dry_run).pack(anchor="w")

        # Run
        runrow = ttk.Frame(self)
        runrow.pack(fill="x")
        self.run_btn = ttk.Button(runrow, text="Run", command=self.run)
        self.run_btn.pack(side="left")
        self.status = ttk.Label(runrow, text="Close Steam before running.")
        self.status.pack(side="left", padx=10)
        ttk.Button(runrow, text="Clear log", command=self.clear_log).pack(side="right")

        # Log
        logf = ttk.Frame(self)
        logf.pack(fill="both", expand=True, pady=(10, 0))
        self.log = tk.Text(logf, state="disabled", wrap="none", height=14)
        self.log.pack(side="left", fill="both", expand=True)
        lsb = ttk.Scrollbar(logf, orient="vertical", command=self.log.yview)
        lsb.pack(side="left", fill="y")
        self.log.config(yscrollcommand=lsb.set)

    # ---------- helpers ----------
    def write_log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def set_busy(self, busy, msg=None):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.run_btn.config(state=state)
        self.detect_btn.config(state=state)
        if msg is not None:
            self.status.config(text=msg)

    def add_library(self, path):
        path = Path(path)
        if path not in self.libraries:
            self.libraries.append(path)
            self.listbox.insert("end", str(path))

    def _poll(self):
        try:
            while True:
                self.write_log(self.q.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._poll)

    # ---------- actions ----------
    def browse_target(self):
        d = filedialog.askdirectory(title="Choose where to store prefixes",
                                    initialdir=str(Path.home()))
        if d:
            self.target.set(d)

    def add_folder(self):
        d = filedialog.askdirectory(title="Select a steamapps/compatdata folder")
        if d:
            self.add_library(d)

    def remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)
            del self.libraries[i]

    def detect(self):
        if self.busy:
            return
        self.set_busy(True, "Searching NTFS mounts…")
        self.q.put("Searching NTFS mounts for Steam libraries...\n")

        def work():
            found = []
            try:
                for m in core.ntfs_mounts():
                    found.extend(core.find_compatdata_dirs(m))
            except Exception as e:
                self.q.put(f"Search error: {e}\n")
            self.master.after(0, lambda: self._detect_done(found))

        threading.Thread(target=work, daemon=True).start()

    def _detect_done(self, found):
        for f in found:
            self.add_library(f)
        self.q.put(f"Found {len(found)} compatdata folder(s).\n")
        self.set_busy(False, "Ready.")

    def run(self):
        if self.busy:
            return
        if core.steam_running():
            messagebox.showerror("Steam is running",
                                 "Close Steam completely and try again.")
            return
        libs = [l for l in self.libraries if l.is_dir()]
        if not libs:
            messagebox.showwarning("No libraries",
                                   "Add or auto-detect at least one compatdata folder.")
            return

        dry = self.dry_run.get()
        target = Path(self.target.get()).expanduser()
        only_foreign = self.only_foreign.get()

        if not dry:
            if not messagebox.askyesno(
                    "Confirm",
                    f"This will move prefixes from {len(libs)} librar{'y' if len(libs) == 1 else 'ies'} "
                    f"to:\n\n{target}\n\nand leave symlinks behind. Continue?"):
                return

        self.set_busy(True, "Running…")

        def work():
            failed = 0
            try:
                with redirect_stdout(QueueWriter(self.q)):
                    if not dry:
                        target.mkdir(parents=True, exist_ok=True)
                    for lib in libs:
                        failed += core.migrate(lib, target, dry, only_foreign)
            except Exception as e:
                self.q.put(f"\nError: {e}\n")
                failed += 1
            self.q.put("\nFinished" + (f" with {failed} failure(s).\n" if failed else " successfully.\n"))
            self.master.after(0, lambda: self.set_busy(False, "Done." if not failed else "Done with errors."))

        threading.Thread(target=work, daemon=True).start()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
