#!/usr/bin/env python3
# /// script
# requires-python = "==3.12"
# dependencies = [
#     "faster-whisper"
# ]
# ///

# How to run:
# export TCL_LIBRARY=~/.local/share/uv/python/cpython-3.12.0-linux-x86_64-gnu/lib/tcl8.6
# uv run --python 3.12 transcribe_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import subprocess
import os
import time
import glob
import traceback
from datetime import datetime
from faster_whisper import WhisperModel

RECORDING_PATH = "/tmp/recordings"
os.makedirs(RECORDING_PATH, exist_ok=True)

class TranscribeGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WhisperNow")
        self.root.geometry("600x800")
        
        # Initialize queues
        self.transcription_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # Initialize model
        model_size = "distil-small.en"
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        # Recording state
        self.sox_process = None
        self.is_recording = False
        self.transcriptions = []  # List of (checkbox_var, text) tuples
        self.current_recording = None
        self.is_transcribing = False
        
        # Thread control
        self.transcription_thread = None
        self.should_stop = False
        
        self.setup_gui()
        self.start_background_threads()
        
    def setup_gui(self):
        # Control frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill='x', padx=5, pady=5)
        
        # Style for red text
        style = ttk.Style()
        style.configure(
            "Record.TButton",
            padding=(20, 10),
            font=("TkDefaultFont", 14, "bold")  # Increased font size
        )
        style.configure(
            "Recording.TButton",
            padding=(20, 10),
            font=("TkDefaultFont", 14, "bold"),  # Increased font size
            foreground="red"
        )
        style.configure(
            "Queue.TLabel",
            foreground="black"
        )
        style.configure(
            "QueueActive.TLabel",
            foreground="green"
        )
        
        self.record_button = ttk.Button(
            control_frame,
            text="Record (Space)",
            command=self.toggle_recording,
            style="Record.TButton",
            width=20  # Make button wider
        )
        self.record_button.pack(side='left', padx=5, pady=10)  # Added vertical padding
        
        # Bind spacebar to record button
        self.root.bind("<space>", lambda e: self.toggle_recording())
        
        self.queue_label = ttk.Label(
            control_frame,
            text="Queue: 0",
            style="Queue.TLabel"
        )
        self.queue_label.pack(side='right', padx=5)
        
        # Transcription frame
        transcription_frame = ttk.Frame(self.root)
        transcription_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Scrollable area for transcriptions
        self.canvas = tk.Canvas(transcription_frame)
        scrollbar = ttk.Scrollbar(
            transcription_frame,
            orient="vertical",
            command=self.canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling with mousewheel
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Make sure the frame expands to fill canvas
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        # Create window that expands with canvas
        self.canvas.create_window(
            (0, 0), 
            window=self.scrollable_frame, 
            anchor="nw",
            width=self.canvas.winfo_reqwidth()
        )
        
        # Configure canvas to expand with window
        self.canvas.configure(yscrollcommand=scrollbar.set)
        transcription_frame.grid_rowconfigure(0, weight=1)
        transcription_frame.grid_columnconfigure(0, weight=1)
        
        # Pack scrollbar and canvas with proper fill
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Update canvas width when window resizes
        def _on_frame_configure(event):
            # Update the width to fit the frame
            self.canvas.itemconfig(
                self.canvas.find_withtag("all")[0],
                width=event.width
            )
        self.canvas.bind("<Configure>", _on_frame_configure)
        
        # Copy button frame at bottom
        copy_frame = ttk.Frame(self.root)
        copy_frame.pack(fill='x', padx=5, pady=5)
        
        copy_button = ttk.Button(
            copy_frame,
            text="Copy Selected",
            command=self.copy_selected
        )
        copy_button.pack(side='right', padx=5)
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        self.is_recording = True
        self.record_button.configure(
            text="Stop (Space)",
            style="Recording.TButton"
        )
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_recording = os.path.join(RECORDING_PATH, f"recording_{timestamp}.wav")
        
        try:
            self.sox_process = subprocess.Popen(
                ["sox", "-d", "-r", "16000", "-c", "1", "-b", "16", self.current_recording],
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            self.stop_recording()
    
    def stop_recording(self):
        if self.sox_process and self.sox_process.poll() is None:
            self.sox_process.terminate()
        
        self.is_recording = False
        self.record_button.configure(
            text="Record (Space)",
            style="Record.TButton"
        )
        
        # Add recording to transcription queue
        if self.current_recording:
            self.transcription_queue.put(self.current_recording)
            self.update_queue_count()
    
    def check_transcriptions(self):
        while True:  # Run continuously
            try:
                # Use blocking get with timeout to avoid busy loop
                file_path, transcription = self.result_queue.get(timeout=0.1)
                # Auto-copy new transcription if not empty
                if transcription.strip():
                    subprocess.run(["wl-copy", transcription])
                    self.root.after(0, self.add_new_transcription, file_path, transcription)
                self.root.after(0, self.update_queue_count)
            except queue.Empty:
                continue
    
    def transcribe_audio(self):
        while not self.should_stop:
            try:
                audio_file = self.transcription_queue.get(timeout=0.5)
                if audio_file is None:
                    break
                
                self.is_transcribing = True
                self.root.after(0, self.update_queue_count)
                
                segments, info = self.model.transcribe(
                    audio_file,
                    beam_size=2,
                    language="en",
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                
                transcription = " ".join([segment.text.strip() for segment in segments])
                transcription = transcription.strip()
                
                # Always send result
                self.result_queue.put((audio_file, transcription))
                self.transcription_queue.task_done()
                self.is_transcribing = False
                
            except queue.Empty:
                continue
            except Exception as e:
                self.is_transcribing = False
                error_msg = f"Transcription error: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)  # For debugging
                
                # Notify user of error in GUI
                self.root.after(0, messagebox.showwarning, 
                              "Transcription Error",
                              "Transcription thread crashed. Restarting...")
                
                # Put the failed audio file back in queue if it exists
                if 'audio_file' in locals():
                    self.transcription_queue.put(audio_file)
                
                # Restart thread
                time.sleep(1)  # Brief pause before restart
                continue
    
    def start_background_threads(self):
        # Start transcription checker thread
        check_thread = threading.Thread(target=self.check_transcriptions)
        check_thread.daemon = True
        check_thread.start()
        
        # Start transcription worker thread
        self.should_stop = False
        self.transcription_thread = threading.Thread(target=self.transcribe_audio)
        self.transcription_thread.daemon = True
        self.transcription_thread.start()
    
    def add_new_transcription(self, file_path, transcription):
        # Only add non-empty transcriptions
        if not transcription.strip():
            return
            
        var = tk.BooleanVar()
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(fill='x', padx=5, pady=2)
        
        # Left side: checkbox
        checkbox = ttk.Checkbutton(
            frame,
            variable=var
        )
        checkbox.pack(side='left')
        
        # Middle: label with transcription
        label = ttk.Label(
            frame,
            text=transcription,
            wraplength=self.canvas.winfo_width() - 120  # Account for checkbox, button and padding
        )
        label.pack(side='left', fill='x', expand=True)
        
        # Right side: copy button
        copy_btn = ttk.Button(
            frame,
            text="Copy",
            width=8,
            command=lambda t=transcription: subprocess.run(["wl-copy", t])
        )
        copy_btn.pack(side='right', padx=5)
        
        self.transcriptions.append((var, transcription))
        
        # Ensure new transcription is visible
        self.canvas.yview_moveto(1.0)
    
    def copy_selected(self):
        selected_texts = [
            text for var, text in self.transcriptions 
            if var.get()
        ]
        if selected_texts:
            combined_text = "\n".join(selected_texts)
            subprocess.run(["wl-copy", combined_text])
    
    def update_queue_count(self):
        count = self.transcription_queue.qsize()
        if self.is_transcribing:
            count += 1
        self.queue_label.configure(
            text=f"Queue: {count}",
            style="QueueActive.TLabel" if count > 0 else "Queue.TLabel"
        )
    
    def cleanup(self):
        # Clean up recording files
        for f in glob.glob(os.path.join(RECORDING_PATH, "recording_*.wav")):
            try:
                os.remove(f)
            except OSError:
                pass
    
    def run(self):
        try:
            self.root.mainloop()
        finally:
            # Cleanup on exit
            self.should_stop = True  # Signal thread to stop gracefully
            self.transcription_queue.put(None)  # Signal transcription thread to exit
            if self.sox_process and self.sox_process.poll() is None:
                self.sox_process.terminate()
            self.cleanup()  # Clean up recording files

if __name__ == "__main__":
    app = TranscribeGUI()
    app.start_recording()  # Start recording immediately
    app.run()
