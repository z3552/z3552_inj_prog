from tkinter import Tk
from ui_sakura import build_ui  # Импорт красивого интерфейса
import os
import sys

# yt_dlp и другие импорты, если нужно — перенеси в ui_sakura

def main():
    root = Tk()
    root.title("Sakura Downloader 🌸")
    build_ui(root)
    root.mainloop()

if __name__ == "__main__":
    main()
