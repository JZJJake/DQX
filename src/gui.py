import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging

class GUI(tk.Tk):
    def __init__(self, add_files_cb, save_cb, remove_queue_cb):
        super().__init__()
        self.title("Document Processor")
        self.geometry("1000x700")

        self.add_files_cb = add_files_cb
        self.save_cb = save_cb
        self.remove_queue_cb = remove_queue_cb

        self.pending_items = [] # list of dicts: {'filepath':, 'title':, 'text':, 'original_name':}
        self.current_preview_index = None

        self._build_ui()

    def _build_ui(self):
        # Settings Frame (Top)
        settings_frame = ttk.LabelFrame(self, text="Settings")
        settings_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(settings_frame, text="DeepSeek API Key:").pack(side="left", padx=5, pady=5)
        self.api_key_var = tk.StringVar()
        api_entry = ttk.Entry(settings_frame, textvariable=self.api_key_var, width=40, show="*")
        api_entry.pack(side="left", padx=5)
        api_entry.bind("<FocusOut>", self._save_config)

        ttk.Label(settings_frame, text="Output Directory:").pack(side="left", padx=5, pady=5)
        self.out_dir_var = tk.StringVar()
        out_entry = ttk.Entry(settings_frame, textvariable=self.out_dir_var, width=30)
        out_entry.pack(side="left", padx=5)
        out_entry.bind("<FocusOut>", self._save_config)
        ttk.Button(settings_frame, text="Browse", command=self._browse_out_dir).pack(side="left", padx=5)

        # Also save on app exit
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._load_config()

        # Main Content area (PanedWindow)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        # Left Panel: Queues
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=1)

        # Upload Queue
        queue_frame = ttk.LabelFrame(left_panel, text="Processing Queue")
        queue_frame.pack(fill="both", expand=True, pady=(0, 5))

        btn_frame = ttk.Frame(queue_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="Add Files", command=self._add_files).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear Queue", command=self._clear_queue).pack(side="left", padx=2)

        self.queue_listbox = tk.Listbox(queue_frame)
        self.queue_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        # Pending Verification Queue
        pending_frame = ttk.LabelFrame(left_panel, text="Pending Verification (Click to Edit)")
        pending_frame.pack(fill="both", expand=True, pady=(5, 0))

        self.pending_listbox = tk.Listbox(pending_frame)
        self.pending_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.pending_listbox.bind('<<ListboxSelect>>', self._on_pending_select)

        # Right Panel: Editor & Logs
        right_panel = ttk.PanedWindow(paned, orient=tk.VERTICAL)
        paned.add(right_panel, weight=2)

        # Editor
        editor_frame = ttk.LabelFrame(right_panel, text="Verification Editor")
        right_panel.add(editor_frame, weight=3)

        title_frame = ttk.Frame(editor_frame)
        title_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(title_frame, text="Title:").pack(side="left")
        self.title_var = tk.StringVar()
        ttk.Entry(title_frame, textvariable=self.title_var).pack(side="left", fill="x", expand=True, padx=5)

        self.text_editor = tk.Text(editor_frame, wrap="word")
        self.text_editor.pack(fill="both", expand=True, padx=5, pady=5)

        ttk.Button(editor_frame, text="Verify & Save to Disk", command=self._verify_and_save).pack(pady=5)

        # Log Console
        log_frame = ttk.LabelFrame(right_panel, text="System Log")
        right_panel.add(log_frame, weight=1)

        self.log_text = tk.Text(log_frame, state='disabled', height=8)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def _load_config(self):
        try:
            import json, os
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    self.api_key_var.set(config.get('api_key', ''))
                    self.out_dir_var.set(config.get('out_dir', ''))
        except Exception:
            pass

    def _save_config(self, *args):
        try:
            import json
            config = {
                'api_key': self.api_key_var.get(),
                'out_dir': self.out_dir_var.get()
            }
            with open('config.json', 'w') as f:
                json.dump(config, f)
        except Exception:
            pass

    def _on_close(self):
        self._save_config()
        self.destroy()

    def _browse_out_dir(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.out_dir_var.set(dir_path)

    def _add_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[
                ("All Supported", "*.txt *.md *.docx *.doc *.wps *.pdf"),
                ("Text Files", "*.txt *.md"),
                ("Word Documents", "*.docx *.doc *.wps"),
                ("PDF Files", "*.pdf")
            ]
        )
        if files:
            for f in files:
                self.queue_listbox.insert(tk.END, f)
            if self.add_files_cb:
                self.add_files_cb(files)

    def _clear_queue(self):
        self.queue_listbox.delete(0, tk.END)
        if self.remove_queue_cb:
            self.remove_queue_cb()

    def update_queue_list(self, files):
        self.queue_listbox.delete(0, tk.END)
        for f in files:
            self.queue_listbox.insert(tk.END, f)

    def add_to_pending(self, filepath, title, text):
        item = {
            'filepath': filepath,
            'title': title,
            'text': text,
            'original_name': filepath.split('/')[-1].split('\\')[-1]
        }
        self.pending_items.append(item)
        self.pending_listbox.insert(tk.END, f"[Ready] {item['original_name']}")

        # Select automatically if nothing is selected
        if self.current_preview_index is None:
            self.pending_listbox.selection_set(0)
            self._on_pending_select(None)

    def _on_pending_select(self, event):
        selection = self.pending_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        self.current_preview_index = idx
        item = self.pending_items[idx]

        self.title_var.set(item['title'])
        self.text_editor.delete(1.0, tk.END)
        self.text_editor.insert(tk.END, item['text'])

    def _verify_and_save(self):
        if self.current_preview_index is None:
            return

        if not self.out_dir_var.get():
            messagebox.showwarning("Warning", "Please select an Output Directory first.")
            return

        title = self.title_var.get().strip()
        text = self.text_editor.get(1.0, tk.END).strip()

        if not title:
            messagebox.showwarning("Warning", "Title cannot be empty.")
            return

        # Callback to save
        if self.save_cb:
            self.save_cb(title, text, self.out_dir_var.get())

        # Remove from pending
        self.pending_listbox.delete(self.current_preview_index)
        self.pending_items.pop(self.current_preview_index)

        self.current_preview_index = None
        self.title_var.set("")
        self.text_editor.delete(1.0, tk.END)

        # Select next if available
        if self.pending_items:
            self.pending_listbox.selection_set(0)
            self._on_pending_select(None)

    def log(self, msg):
        def _update_log():
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
            self.update_idletasks()
        self.after(0, _update_log)

class GUILoggingHandler(logging.Handler):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

    def emit(self, record):
        msg = self.format(record)
        self.gui.log(msg)
