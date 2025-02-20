#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "faster-whisper",
#     "soundfile"
# ]
# ///

import tkinter as tk
from tkinter import ttk
import threading
import queue
import subprocess
import os
import time
from faster_whisper import WhisperModel

RECORDING_PATH = "/tmp/recordings"
RECORDING_FILE = os.path.join(RECORDING_PATH, "recording.wav")
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
        
        self.setup_gui()
        self.start_background_threads()
        
    def setup_gui(self):
        # Control frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill='x', padx=5, pady=5)
        
        self.record_button = ttk.Button(
            control_frame,
            text="Record",
            command=self.toggle_recording
        )
        self.record_button.pack(side='left', padx=5)
        
        self.queue_label = ttk.Label(
            control_frame,
            text="Queue: 0"
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
            width=self.canvas.winfo_reqwidth()  # Make frame fill canvas width
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
        self.record_button.configure(text="Stop")
        
        try:
            self.sox_process = subprocess.Popen(
                ["sox", "-d", "-r", "16000", "-c", "1", "-b", "16", RECORDING_FILE],
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            self.stop_recording()
    
    def stop_recording(self):
        if self.sox_process and self.sox_process.poll() is None:
            self.sox_process.terminate()
        
        self.is_recording = False
        self.record_button.configure(text="Record")
        
        # Add recording to transcription queue
        self.transcription_queue.put(RECORDING_FILE)
        self.update_queue_count()
    
    def check_transcriptions(self):
        while True:  # Run continuously
            try:
                # Use blocking get with timeout to avoid busy loop
                transcription = self.result_queue.get(timeout=0.1)
                self.root.after(0, self.add_new_transcription, transcription)
                self.update_queue_count()
            except queue.Empty:
                continue
    
    def start_background_threads(self):
        # Start transcription checker thread
        check_thread = threading.Thread(target=self.check_transcriptions)
        check_thread.daemon = True
        check_thread.start()
        
        # Start transcription worker thread
        def transcribe_audio():
            while True:
                audio_file = self.transcription_queue.get()
                if audio_file is None:
                    break
                
                segments, info = self.model.transcribe(
                    audio_file,
                    beam_size=2,
                    language="en",
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                
                transcription = " ".join([segment.text.strip() for segment in segments])
                transcription = transcription.strip()
                
                self.result_queue.put(transcription)
                self.transcription_queue.task_done()
        
        thread = threading.Thread(target=transcribe_audio)
        thread.daemon = True
        thread.start()
    
    def add_new_transcription(self, transcription):
        # This method should only be called from the main thread
        var = tk.BooleanVar()
        
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(fill='x', padx=5, pady=2)
        
        checkbox = ttk.Checkbutton(
            frame,
            variable=var
        )
        checkbox.pack(side='left')
        
        label = ttk.Label(
            frame,
            text=transcription,
            wraplength=self.canvas.winfo_width() - 50  # Account for checkbox and padding
        )
        label.pack(side='left', fill='x', expand=True)
        
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
        self.queue_label.configure(text=f"Queue: {count}")
    
    def run(self):
        # Just start the mainloop, transcriptions are added via check_transcriptions
        self.root.mainloop()
        
        # Cleanup on exit
        self.transcription_queue.put(None)  # Signal transcription thread to exit
        if self.sox_process and self.sox_process.poll() is None:
            self.sox_process.terminate()

if __name__ == "__main__":
    app = TranscribeGUI()
    app.run()
