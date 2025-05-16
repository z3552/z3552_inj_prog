from tkinter import (
    Label, Entry, Button, StringVar, OptionMenu, filedialog,
    Text, Scrollbar, Frame
)
import yt_dlp
import os
import threading
import requests
from PIL import Image, ImageTk
from io import BytesIO
import re
import random
import string

FFMPEG_PATH = os.path.join(os.path.dirname(__file__), "ffmpeg", "bin", "ffmpeg.exe")

def generate_random_filename(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# 🧠 Логгер для отображения сообщений yt_dlp в логах GUI
class YTDLogger:
    def __init__(self, log_func):
        self.log_func = log_func

    def debug(self, msg):
        if msg.strip():
            self.log_func(msg)

    def warning(self, msg):
        self.log_func(f"⚠️ {msg}")

    def error(self, msg):
        self.log_func(f"❌ {msg}")

class SakuraDownloader:
    def __init__(self, root):
        self.root = root
        self.url = StringVar()
        self.quality = StringVar()
        self.download_type = StringVar(value="Видео + Аудио")
        self.output_path = StringVar()
        self.video_title = StringVar()
        self.thumb_url_map = {}
        self.thumb_resolution = StringVar(value="maxresdefault")
        self.formats = []

        self.thumbnail = None
        self.log_output = None

        self.build_ui()

    def build_ui(self):
        self.root.configure(bg="#ffe6f0")

        frame = Frame(self.root, bg="#fff0f5", padx=15, pady=15, bd=3, relief="ridge")
        frame.pack(padx=10, pady=10)

        row = 0
        Label(frame, text="🌸 Сакура Загрузчик", bg="#fff0f5", fg="#d63384", font=("Helvetica", 16, "bold")).grid(row=row, column=0, columnspan=3, pady=10)

        row += 1
        Label(frame, text="Ссылка на видео:", bg="#fff0f5").grid(row=row, column=0, sticky="w")
        Entry(frame, textvariable=self.url, width=50).grid(row=row, column=1)
        Button(frame, text="🔍", command=self.refresh_video_info, bg="#ffcce5").grid(row=row, column=2)

        row += 1
        self.thumb_label = Label(frame, bg="#fff0f5")
        self.thumb_label.grid(row=row, column=0, columnspan=1)
        Label(frame, textvariable=self.video_title, wraplength=400, bg="#fff0f5", fg="#cc3366").grid(row=row, column=1, columnspan=2)

        row += 1
        Label(frame, text="Качество:", bg="#fff0f5").grid(row=row, column=0, sticky="w")
        self.quality_menu = OptionMenu(frame, self.quality, "")
        self.quality_menu.grid(row=row, column=1)

        row += 1
        Label(frame, text="Тип загрузки:", bg="#fff0f5").grid(row=row, column=0, sticky="w")
        OptionMenu(frame, self.download_type, "Видео", "Аудио", "Видео + Аудио").grid(row=row, column=1)

        row += 1
        Label(frame, text="Папка сохранения:", bg="#fff0f5").grid(row=row, column=0, sticky="w")
        Entry(frame, textvariable=self.output_path, width=30).grid(row=row, column=1)
        Button(frame, text="📂", command=self.choose_output_folder, bg="#ffcce5").grid(row=row, column=2)

        row += 1
        Label(frame, text="Превью разрешение:", bg="#fff0f5").grid(row=row, column=0, sticky="w")
        OptionMenu(frame, self.thumb_resolution, "maxresdefault", "sddefault", "hqdefault", "mqdefault", "default").grid(row=row, column=1)
        Button(frame, text="💾 Сохранить превью", command=self.save_thumbnail, bg="#ffb3d9").grid(row=row, column=2)

        row += 1
        Label(frame, text="Лог:", bg="#fff0f5").grid(row=row, column=0, sticky="w")

        row += 1
        self.log_output = Text(frame, height=8, wrap="word", bg="#fff0f5", fg="#800040")
        self.log_output.grid(row=row, column=0, columnspan=3)
        scrollbar = Scrollbar(frame, command=self.log_output.yview)
        scrollbar.grid(row=row, column=3, sticky="ns")
        self.log_output.config(yscrollcommand=scrollbar.set)

        row += 1
        Button(frame, text="⬇️ Скачать", command=self.download_video, bg="#ff99cc").grid(row=row, column=1, pady=10)

    def choose_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.set(folder)

    def refresh_video_info(self):
        url = self.url.get().strip()
        if not url:
            return

        def task():
            self.log("Получение информации о видео...")
            try:
                ydl_opts = {"quiet": True, "skip_download": True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    self.video_title.set(info.get("title", ""))
                    self.formats = info.get("formats", [])

                    self.quality_menu['menu'].delete(0, 'end')
                    for fmt in self.formats:
                        label = f"{fmt.get('format_id')} - {fmt.get('format_note', '')} - {fmt.get('ext', '')}"
                        self.quality_menu['menu'].add_command(label=label,
                                                              command=lambda v=fmt.get("format_id"): self.quality.set(v))
                    if self.formats:
                        self.quality.set(self.formats[0]['format_id'])

                    video_id = info.get("id")
                    if video_id:
                        resolutions = ["maxresdefault", "sddefault", "hqdefault", "mqdefault", "default"]
                        self.thumb_url_map = {res: f"https://img.youtube.com/vi/{video_id}/{res}.jpg" for res in resolutions}
                        chosen = self.thumb_url_map[self.thumb_resolution.get()]
                        response = requests.get(chosen)
                        img = Image.open(BytesIO(response.content)).resize((120, 90))
                        self.thumbnail = ImageTk.PhotoImage(img)
                        self.thumb_label.configure(image=self.thumbnail)

            except Exception as e:
                self.log(f"Ошибка: {e}")

        threading.Thread(target=task).start()

    def save_thumbnail(self):
        if not self.thumb_url_map:
            self.log("Нет превью для сохранения.")
            return

        url = self.thumb_url_map.get(self.thumb_resolution.get())
        if not url:
            return

        folder = filedialog.askdirectory()
        if not folder:
            return

        try:
            response = requests.get(url)
            title = self.video_title.get()
            if re.search(r'[\\/*?:"<>|]', title):
                filename = generate_random_filename()
                self.log("Недопустимые символы. Название заменено.")
            else:
                filename = title.replace(" ", "_")

            filepath = os.path.join(folder, f"{filename}_{self.thumb_resolution.get()}.jpg")
            with open(filepath, "wb") as f:
                f.write(response.content)
            self.log(f"Превью сохранено: {filepath}")
        except Exception as e:
            self.log(f"Ошибка: {e}")

    def download_video(self):
        def task():
            path = self.output_path.get() or "output"
            os.makedirs(path, exist_ok=True)
            url = self.url.get().strip()
            mode = self.download_type.get()

            try:
                format_id = self.quality.get()
                ydl_opts = {
                    "format": format_id if mode != "Видео + Аудио" else "bestvideo+bestaudio",
                    "outtmpl": os.path.join(path, "%(title)s.%(ext)s"),
                    "ffmpeg_location": FFMPEG_PATH,
                    "postprocessors": [],
                    "logger": YTDLogger(self.log)  # 🔥 Главное добавление
                }
                if mode == "Аудио":
                    ydl_opts["postprocessors"].append({
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    })

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                self.log("✅ Загрузка завершена.")
            except Exception as e:
                self.log(f"❌ Ошибка при загрузке: {e}")

        threading.Thread(target=task).start()

    def log(self, msg):
        self.log_output.insert("end", msg + "\n")
        self.log_output.see("end")


def build_ui(root):
    SakuraDownloader(root)