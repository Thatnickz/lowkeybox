# --- IMPORTS FOR PYINSTALLER ---
try:
    import win32gui, win32con, win32api, win32ui
    import tkinter.scrolledtext
    import google.api_core.bidi
    import grpc._cython.cygrpc
    import PIL.Image, PIL.ImageEnhance, PIL.ImageOps
    import keyboard
except ImportError:
    pass

# --- PYARMOR INITIALIZATION ---
try:
    from pytransform import pyarmor_runtime
    pyarmor_runtime()
except ImportError:
    pass

# --- STANDARD IMPORTS ---
import os
import time
import threading
import logging
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageEnhance, ImageOps
import io
import google.generativeai as genai

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION WITH HARDCODED KEY ---
_CFG = {
    'key': 'AIzaSyBkZu4-yLorlwp5Vd3enzY66yvDXfYO5nc',
    'mdl': 'gemini-2.5-pro'
}

class OverlayWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Assistant")
        self.root.geometry("400x80")
        self.root.configure(bg='white') # CHANGED to white
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.85)
        self.root.overrideredirect(True)
        screen_width = self.root.winfo_screenwidth()
        self.root.geometry(f"400x80+{(screen_width - 400)//2}+{50}")

        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.on_move)
        self.root.bind('<Button-3>', self.close_app)

        self.text_frame = tk.Frame(self.root, bg='white') # CHANGED to white
        self.text_frame.pack(padx=8, pady=8, fill='both', expand=True)

        self.answer_text = scrolledtext.ScrolledText(
            self.text_frame, height=4, bg='white', fg='black', # CHANGED to white
            font=('Arial', 10), wrap='word', relief='flat'
        )
        self.answer_text.pack(fill='both', expand=True)
        self.update_answer("") # CHANGED to empty

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def on_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    def update_answer(self, text):
        self.answer_text.config(state='normal')
        self.answer_text.delete(1.0, tk.END)
        self.answer_text.insert(tk.END, text)
        self.answer_text.config(state='disabled')

    def show(self):
        self.root.deiconify()
        self.root.lift()

    def hide(self):
        self.root.withdraw()

    def close_app(self, event):
        self.root.destroy()

class ScreenProcessor:
    def __init__(self):
        self.overlay = OverlayWindow()
        self.root = self.overlay.root
        keyboard.add_hotkey('ctrl+u', self.manual_capture)

        try:
            genai.configure(api_key=_CFG['key'])
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}")
            self.overlay.update_answer(f"[Error: Invalid Gemini API Key: {e}]")
            return

        self.overlay.show()

    def capture_screen(self):
        try:
            width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            hwin = win32gui.GetDesktopWindow()
            hwindc = win32gui.GetWindowDC(hwin)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, width, height)
            memdc.SelectObject(bmp)
            memdc.BitBlt((0, 0), (width, height), srcdc, (0, 0), win32con.SRCCOPY)
            
            bmp_info = bmp.GetInfo()
            bmp_str = bmp.GetBitmapBits(True)
            img = Image.frombuffer('RGB', (bmp_info['bmWidth'], bmp_info['bmHeight']),
                                   bmp_str, 'raw', 'BGRX', 0, 1)
            
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)
            return img
        except Exception as e:
            logger.error(f"Failed to capture screen: {e}")
            return None

    def get_answer_from_ai(self, image, prompt):
        try:
            model = genai.GenerativeModel(_CFG['mdl'])
            response = model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            return f"[Error contacting Gemini API: {e}]"

    def process_cycle(self):
        logger.info("Starting capture and analysis...")
        self.overlay.update_answer("Processing...") # Temporary message while working
        image = self.capture_screen()
        if image is None:
            self.overlay.update_answer("[Error: Screen capture failed.]")
            return

        self.overlay.update_answer("Analyzing question...")
        # UPDATED prompt for SAT questions
        prompt = (
            "You are an expert SAT tutor. Analyze the following screenshot of an SAT question. "
            "Provide the correct answer choice and a step-by-step explanation of how to arrive at the solution. "
            "Be clear and concise."
        )
        answer = self.get_answer_from_ai(image, prompt)
        self.overlay.update_answer(answer)

    def manual_capture(self):
        threading.Thread(target=self.process_cycle, daemon=True).start()

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = ScreenProcessor()
    app.run()