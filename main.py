from tkinter import Tk
from ui_sakura import build_ui  # Импорт интерфейса
import os
import sys

def main():
    root = Tk()
    root.title("Sakura Downloader 🌸")
    # Установка иконки приложения (для окна и панели задач)
    try:
        import ctypes
        icon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
        root.iconbitmap(icon_path)
        # Для панели задач:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'sakura.downloader')
    except Exception as e:
        print(f"Не удалось установить иконку: {e}")
    build_ui(root)
    root.mainloop()

if __name__ == "__main__":
    main()
