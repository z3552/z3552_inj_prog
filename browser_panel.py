import tkinter as tk
import webview
from tkinterweb import HtmlFrame

# Это класс панели браузера, которую можно встроить в tkinter-приложение.
class BrowserPanel(tk.Frame):
    def __init__(self, master, width=900, height=700, url="https://www.youtube.com/"):
        super().__init__(master, width=width, height=height)
        self.url = url

        # Кнопка "Закрыть" — убирает панель браузера
        close_btn = tk.Button(self, text="Закрыть", command=self.close)
        close_btn.pack(anchor="ne", padx=5, pady=5)

        # HtmlFrame — это виджет для отображения веб-страниц прямо в tkinter
        self.html = HtmlFrame(self, horizontal_scrollbar="auto")
        self.html.pack(fill="both", expand=True)
        self.html.load_website(self.url)  # Загружаем сайт

    def show(self):
        # Показываем панель браузера в окне (позиция фиксированная)
        self.place(x=50, y=30)

    def hide(self):
        # Просто убираем панель с экрана, но не уничтожаем
        self.place_forget()

    def close(self):
        # Скрываем и полностью уничтожаем панель
        self.hide()
        self.destroy()
        # Если у родителя был атрибут _browser_panel — удаляем его (чтобы не было "висящей" ссылки)
        if hasattr(self.master, "_browser_panel"):
            delattr(self.master, "_browser_panel")

# Эта функция открывает отдельное окно браузера через pywebview (не внутри tkinter)
def show_browser(root=None):
    webview.create_window(
        "Браузер",
        "https://www.youtube.com/",
        width=900,
        height=700,
        # icon='favicon.ico'  # Работает только на некоторых платформах
    )
    webview.start()