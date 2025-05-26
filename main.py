from tkinter import Tk, Button
from ui_sakura import build_ui  # Импорт основного интерфейса
from browser_panel import show_browser  # Импорт функции для браузера
import os

def main():
    # Создаём главное окно приложения
    root = Tk()
    root.title("Sakura Downloader 🌸")
    # Устанавливаем иконку приложения (если есть)
    try:
        import ctypes
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "favicon.ico")
        root.iconbitmap(icon_path)
        # Для панели задач Windows
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'sakura.downloader')
    except Exception as e:
        print(f"Не удалось установить иконку: {e}")

    # Строим основной UI
    build_ui(root)

    # Кнопка для запуска браузера (стилизована под общий стиль)
    Button(
        root,
        text="Браузер",
        command=show_browser,
        bg="#ffe6f0",
        fg="#800040",
        activebackground="#ffb3d9",
        activeforeground="#d63384",
        font=("Helvetica", 10, "bold"),
        borderwidth=2,
        relief="groove"
    ).place(x=900, y=10)

    # Запускаем главный цикл приложения
    root.mainloop()

if __name__ == "__main__":
    main()
