import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import time
import threading

class CompressionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Aura Pro - World Class Compression Engine")
        self.root.geometry("600x550")
        self.root.configure(bg="#0f172a")  # Dark Slate Blue/Black
        
        # Style Configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TProgressbar", thickness=15, troughcolor="#1e293b", background="#3b82f6")
        
        # Colors
        self.bg_color = "#0f172a"
        self.accent_color = "#3b82f6"  # Bright Blue
        self.text_color = "#f1f5f9"
        self.secondary_bg = "#1e293b"
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=self.bg_color, pady=20)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="AURA COMPRESSOR PRO", font=("Inter", 24, "bold"), fg=self.accent_color, bg=self.bg_color).pack()
        tk.Label(header_frame, text="Powered by Zstandard Engine v2.0 (World Class)", font=("Inter", 10), fg="#64748b", bg=self.bg_color).pack()
        tk.Label(header_frame, text="[ Multi-Threaded | Long Distance Matching | Advanced I/O Buffering ]", font=("Inter", 9, "bold"), fg="#10b981", bg=self.bg_color).pack(pady=(5, 0))

        # Selection Frame
        selection_frame = tk.Frame(self.root, bg=self.secondary_bg, padx=30, pady=30, highlightthickness=1, highlightbackground="#334155")
        selection_frame.pack(pady=10, padx=40, fill="x")

        self.file_path = tk.StringVar(value="No file selected")
        tk.Label(selection_frame, text="Select Source File", font=("Inter", 11, "bold"), fg=self.text_color, bg=self.secondary_bg).pack(anchor="w")
        
        file_entry_frame = tk.Frame(selection_frame, bg=self.secondary_bg)
        file_entry_frame.pack(fill="x", pady=(5, 10))
        
        tk.Entry(file_entry_frame, textvariable=self.file_path, font=("Inter", 10), bg="#0f172a", fg=self.text_color, borderwidth=0, relief="flat", width=40).pack(side="left", padx=5, pady=5)
        
        browse_btn = tk.Button(file_entry_frame, text="Browse", command=self.browse_file, bg=self.accent_color, fg="white", font=("Inter", 9, "bold"), relief="flat", activebackground="#2563eb", cursor="hand2", padx=10)
        browse_btn.pack(side="right")

        # Compression Level
        tk.Label(selection_frame, text="Compression Intensity (1-22)", font=("Inter", 11, "bold"), fg=self.text_color, bg=self.secondary_bg).pack(anchor="w", pady=(10, 0))
        self.level_slider = tk.Scale(selection_frame, from_=1, to_=22, orient="horizontal", bg=self.secondary_bg, fg=self.text_color, highlightthickness=0, troughcolor="#0f172a")
        self.level_slider.set(3)
        self.level_slider.pack(fill="x", pady=5)

        # Action Buttons
        btn_frame = tk.Frame(self.root, bg=self.bg_color)
        btn_frame.pack(pady=20)

        self.compress_btn = tk.Button(btn_frame, text="COMPRESS NOW", command=self.start_compression, bg="#10b981", fg="white", font=("Inter", 12, "bold"), relief="flat", padx=20, pady=10, cursor="hand2")
        self.compress_btn.pack(side="left", padx=10)

        self.decompress_btn = tk.Button(btn_frame, text="DECOMPRESS", command=self.start_decompression, bg="#f59e0b", fg="white", font=("Inter", 12, "bold"), relief="flat", padx=20, pady=10, cursor="hand2")
        self.decompress_btn.pack(side="left", padx=10)

        # Progress & Status
        self.progress_bar = ttk.Progressbar(self.root, mode="determinate", style="TProgressbar", length=400)
        self.progress_bar.pack(pady=10)

        self.status_label = tk.Label(self.root, text="Ready", font=("Inter", 10), fg="#64748b", bg=self.bg_color)
        self.status_label.pack()

    def browse_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.file_path.set(filename)

    def update_status(self, text, color="#64748b"):
        self.status_label.config(text=text, fg=color)
        self.root.update_idletasks()

    def run_engine(self, mode, input_file, output_file, level=3):
        try:
            # Command: ./zstd_engine_pro <mode> <input> <output> <level>
            engine_path = "./zstd_engine_pro"
            cmd = [engine_path, mode, input_file, output_file, str(level)]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            
            if "SUCCESS" in output:
                # Format: SUCCESS|time
                parts = output.split("|")
                time_taken = parts[1] if len(parts) > 1 else "Unknown"
                return True, time_taken
            return False, "Engine Error"
        except Exception as e:
            return False, str(e)

    def start_compression(self):
        input_f = self.file_path.get()
        if not os.path.exists(input_f):
            messagebox.showerror("Error", "Selected file does not exist.")
            return

        output_f = input_f + ".aura"
        level = self.level_slider.get()
        
        self.compress_btn.config(state="disabled")
        self.progress_bar.start()
        self.update_status(f"Compressing with level {level}...", self.accent_color)
        
        def task():
            success, result_msg = self.run_engine("c", input_f, output_f, level)
            self.root.after(0, lambda: self.finish_task(success, result_msg, "Compressed", input_f, output_f))

        threading.Thread(target=task).start()

    def start_decompression(self):
        input_f = self.file_path.get()
        if not input_f.endswith(".aura"):
            messagebox.showerror("Error", "Please select an .aura file to decompress.")
            return

        output_f = input_f.replace(".aura", "_restored")
        
        self.decompress_btn.config(state="disabled")
        self.progress_bar.start()
        self.update_status("Decompressing...", self.accent_color)
        
        def task():
            success, result_msg = self.run_engine("d", input_f, output_f)
            self.root.after(0, lambda: self.finish_task(success, result_msg, "Decompressed", input_f, output_f))

        threading.Thread(target=task).start()

    def finish_task(self, success, result_msg, task_name, in_f, out_f):
        self.progress_bar.stop()
        self.compress_btn.config(state="normal")
        self.decompress_btn.config(state="normal")
        
        if success:
            orig_size = os.path.getsize(in_f)
            new_size = os.path.getsize(out_f)
            ratio = (1 - (new_size / orig_size)) * 100 if orig_size > 0 else 0
            
            msg = f"{task_name} successfully!\nTime: {result_msg}s\nSavings: {ratio:.1f}%"
            messagebox.showinfo("Success", msg)
            self.update_status("Operation Complete", "#10b981")
        else:
            messagebox.showerror("Operation Failed", result_msg)
            self.update_status("Failed", "#ef4444")

if __name__ == "__main__":
    root = tk.Tk()
    app = CompressionApp(root)
    root.mainloop()
