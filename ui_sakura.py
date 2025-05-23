# 📦 Импорт нужных классов и функций из tkinter (графический интерфейс)
from tkinter import (
    Label, Entry, Button, StringVar, OptionMenu, filedialog,
    Text, Frame, Toplevel, Canvas, Scrollbar, Listbox, SINGLE, END
)

# 📦 Импорт сторонних и стандартных библиотек
import os
import sys
import json
import requests
from PIL import Image, ImageTk
from io import BytesIO
import yt_dlp
import threading
import subprocess

# ДО класса SakuraDownloader:
ffmpeg_dir = r"D:\github\z3552_inj_prog\ffmpeg\bin"
if ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "history", "history.json")

class HistoryManager:
    def __init__(self, path=HISTORY_PATH, max_items=10):
        self.path = path
        self.max_items = max_items
        self.history = self.load_history()

    def load_history(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_history(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.history[:self.max_items], f, ensure_ascii=False, indent=2)

    def add(self, url, thumb_url):
        # Удалить дубликаты
        self.history = [h for h in self.history if h["url"] != url]
        self.history.insert(0, {"url": url, "thumb_url": thumb_url})
        self.save_history()

class YTDLLogger:
    def __init__(self, log_func):
        self.log_func = log_func
    def debug(self, msg):
        pass
    def warning(self, msg):
        self.log_func(f"[yt-dlp] WARNING: {msg}")
    def error(self, msg):
        self.log_func(f"[yt-dlp] ERROR: {msg}")

def ytdl_hook(d, log_func):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '').strip()
        speed = d.get('_speed_str', '').strip()
        eta = d.get('_eta_str', '').strip()
        line = f"[download] {percent} of {d.get('total_bytes_str','?')} at {speed} ETA {eta}"
        log_func(line)
    elif d['status'] == 'finished':
        log_func(f"[download] Done: {d.get('filename','')}")

class SakuraDownloader:
    def __init__(self, root):
        self.root = root
        self.url = StringVar()
        self.output_path = StringVar()
        self.thumb_resolution = StringVar(value="maxresdefault")
        self.selected_item = None
        self.download_items = []
        self.history_manager = HistoryManager()
        self.log_output = None
        self.build_ui()

    def build_ui(self):
        self.root.geometry("1000x700")
        self.root.resizable(False, False)
        self.root.configure(bg="#ffe6f0")
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        frame = Frame(self.root, bg="#fff0f5", padx=15, pady=15, bd=3, relief="ridge")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Заголовок
        Label(frame, text="🌸 Сакура Загрузчик", bg="#fff0f5", fg="#d63384", font=("Helvetica", 18, "bold")).grid(row=0, column=0, columnspan=6, pady=10, sticky="ew")

        # Ссылка и кнопки
        Label(frame, text="Ссылка:", bg="#fff0f5").grid(row=1, column=0, sticky="w")
        Entry(frame, textvariable=self.url, width=60).grid(row=1, column=1, columnspan=3, sticky="ew")
        Button(frame, text="➕ Добавить", command=self.add_to_list, bg="#ffe6f0").grid(row=1, column=4, sticky="ew")
        Button(frame, text="История", command=self.show_history, bg="#ffe6f0").grid(row=1, column=5, sticky="ew")

        # Список роликов с прокруткой
        self.vid_canvas = Canvas(frame, bg="#fff0f5", highlightthickness=0)
        self.vid_scrollbar = Scrollbar(frame, orient="vertical", command=self.vid_canvas.yview)
        self.vid_canvas.configure(yscrollcommand=self.vid_scrollbar.set)
        self.vid_canvas.grid(row=2, column=0, columnspan=6, sticky="nsew")
        self.vid_scrollbar.grid(row=2, column=6, sticky="ns")
        self.items_frame = Frame(self.vid_canvas, bg="#fff0f5")
        self.vid_canvas.create_window((0, 0), window=self.items_frame, anchor="nw")
        self.items_frame.bind("<Configure>", lambda e: self.vid_canvas.configure(scrollregion=self.vid_canvas.bbox("all")))
        self.vid_canvas.bind("<Enter>", lambda e: self.vid_canvas.bind_all("<MouseWheel>", self._on_mousewheel_vid))
        self.vid_canvas.bind("<Leave>", lambda e: self.vid_canvas.unbind_all("<MouseWheel>"))

        # Кнопки групповой загрузки
        groupf = Frame(frame, bg="#fff0f5")
        groupf.grid(row=3, column=0, columnspan=6, sticky="ew", pady=5)
        Button(groupf, text="Скачать все субтитры", command=self.download_all_subs, bg="#ffe6f0").pack(side="left", padx=2)
        Button(groupf, text="Скачать все превью", command=self.download_all_previews, bg="#ffe6f0").pack(side="left", padx=2)
        Button(groupf, text="Скачать все ролики", command=self.download_all_videos, bg="#ffe6f0").pack(side="left", padx=2)
        Button(groupf, text="Скачать всё", command=self.download_everything, bg="#ff99cc").pack(side="left", padx=2)

        # Логи с отдельной прокруткой
        Label(frame, text="Лог:", bg="#fff0f5").grid(row=4, column=0, sticky="w")
        self.log_canvas = Canvas(frame, bg="#fff0f5", height=120, highlightthickness=0)
        self.log_scrollbar = Scrollbar(frame, orient="vertical", command=self.log_canvas.yview)
        self.log_canvas.configure(yscrollcommand=self.log_scrollbar.set)
        self.log_canvas.grid(row=5, column=0, columnspan=6, sticky="nsew")
        self.log_scrollbar.grid(row=5, column=6, sticky="ns")
        self.log_frame = Frame(self.log_canvas, bg="#fff0f5")
        self.log_canvas.create_window((0, 0), window=self.log_frame, anchor="nw")
        self.log_frame.bind("<Configure>", lambda e: self.log_canvas.configure(scrollregion=self.log_canvas.bbox("all")))
        self.log_canvas.bind("<Enter>", lambda e: self.log_canvas.bind_all("<MouseWheel>", self._on_mousewheel_log))
        self.log_canvas.bind("<Leave>", lambda e: self.log_canvas.unbind_all("<MouseWheel>"))
        self.log_output = Text(self.log_frame, height=7, wrap="word", bg="#fff0f5", fg="#800040", state="disabled")
        self.log_output.pack(fill="both", expand=True)

        self.render_download_items()

    def _on_mousewheel_vid(self, event):
        self.vid_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_mousewheel_log(self, event):
        self.log_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def add_to_list(self):
        url = self.url.get().strip()
        if not url or url in [item["url"] for item in self.download_items]:
            return

        def worker():
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                title = info.get("title", url)
                video_id = info.get("id")
                thumb_base = f"https://img.youtube.com/vi/{video_id}/"
                preview_options = [
                    ("1920x1080", "maxresdefault.jpg"),
                    ("1280x720", "sddefault.jpg"),
                    ("640x480", "hqdefault.jpg"),
                    ("320x180", "mqdefault.jpg"),
                    ("120x90", "default.jpg"),
                ]
                available_previews = []
                for res, fname in preview_options:
                    try:
                        resp = requests.get(thumb_base + fname, timeout=3)
                        if resp.status_code == 200 and resp.content[:3] != b'\x00\x00\x00':
                            available_previews.append((res, thumb_base + fname))
                    except Exception:
                        pass

                # Форматы: показывать ВСЁ, что есть (и с аудио, и без)
                formats = info.get("formats", [])
                format_choices = []
                format_map = {}
                for f in formats:
                    note = f.get('format_note', '')
                    ext = f.get('ext', '')
                    acodec = f.get('acodec')
                    vcodec = f.get('vcodec')
                    height = f.get('height')
                    fps = f.get('fps')
                    label = f"{ext}"
                    if note:
                        label += f" {note}"
                    if height:
                        label += f" {height}p"
                    if fps:
                        label += f" {fps}fps"
                    if vcodec and vcodec != 'none':
                        label += f" {vcodec}"
                    if acodec and acodec != 'none':
                        label += f" audio"
                    format_choices.append(label)
                    format_map[label] = f["format_id"]

                dubbed_audio_tracks = []
                for f in formats:
                    note = f.get('format_note', '')
                    ext = f.get('ext', '')
                    acodec = f.get('acodec')
                    vcodec = f.get('vcodec')
                    lang = f.get("language") or ""
                    # Оригинальные видео (не дубляж)
                    if not ("dubbed" in note.lower() or "дубляж" in note.lower()):
                        # Только с видео и аудио
                        if vcodec != 'none' and acodec != 'none':
                            label = f"{ext}"
                            if note:
                                label += f" {note}"
                            if height:
                                label += f" {height}p"
                            if fps:
                                label += f" {fps}fps"
                            if vcodec and vcodec != 'none':
                                label += f" {vcodec}"
                            if acodec and acodec != 'none':
                                label += f" audio"
                            if acodec == 'none':
                                label += " (без звука)"
                            format_choices.append(label)
                            format_map[label] = f["format_id"]
                    else:
                        # Сохраняем дубляжные аудиодорожки
                        dubbed_audio_tracks.append({
                            "lang": lang,
                            "label": f"{LANG_NATIVE.get(lang, lang)} (dubbed)",
                            "format_id": f["format_id"],
                            "ext": ext
                        })

                subtitles = info.get("subtitles", {})
                subtitle_choices = []
                subtitle_map = {}
                for lang, tracks in subtitles.items():
                    for track in tracks:
                        ext = track.get("ext", "vtt")
                        name = f"{lang} ({ext})"
                        subtitle_choices.append(name)
                        subtitle_map[name] = {"lang": lang, "ext": ext}

                item = {
                    "url": url,
                    "title_base": title,
                    "title": title,
                    "thumb_url": available_previews[0][1] if available_previews else "",
                    "formats": formats,
                    "format_choices": format_choices,
                    "format_map": format_map,
                    "format_var": StringVar(value=format_choices[0]),
                    "preview_choices": available_previews,
                    "preview_var": StringVar(value=available_previews[0][0] if available_previews else ""),
                    "subtitle_choices": subtitle_choices,
                    "subtitle_map": subtitle_map,
                    "subtitle_var": StringVar(value=subtitle_choices[0] if subtitle_choices else ""),
                    "dubbed_audio_tracks": dubbed_audio_tracks,
                    "dub_choices": [track["label"] for track in dubbed_audio_tracks],
                    "dub_var": StringVar(value=dubbed_audio_tracks[0]["label"] if dubbed_audio_tracks else ""),
                }
                self.download_items.insert(0, item)
                self.history_manager.add(url, item["thumb_url"])
                self.root.after(0, self.render_download_items)
            except Exception as e:
                self.log(f"Ошибка: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def extract_video_id(self, url):
        import re
        m = re.search(r"(?:v=|be/)([A-Za-z0-9_-]{11})", url)
        return m.group(1) if m else "dQw4w9WgXcQ"

    def render_download_items(self):
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        for idx, item in enumerate(self.download_items):
            frm = Frame(self.items_frame, bg="#ffe6f0", bd=2, relief="groove", padx=8, pady=8)
            frm.pack(fill="x", pady=6, padx=6)
            # Миниатюра слева
            left = Frame(frm, bg="#ffe6f0")
            left.pack(side="left", padx=4)
            try:
                response = requests.get(item["thumb_url"], timeout=3)
                img = Image.open(BytesIO(response.content)).resize((120, 90))
                thumb = ImageTk.PhotoImage(img)
                lbl = Label(left, image=thumb, bg="#ffe6f0")
                lbl.image = thumb
                lbl.pack()
            except Exception:
                Label(left, text="нет превью", bg="#ffe6f0", fg="#888").pack()
            # Инфо справа
            right = Frame(frm, bg="#ffe6f0")
            right.pack(side="left", fill="x", expand=True, padx=8)
            Label(right, text=item.get("title", ""), bg="#ffe6f0", fg="#cc3366", font=("Helvetica", 13, "bold"), anchor="w", justify="left", wraplength=500).pack(anchor="w")
            rowf = Frame(right, bg="#ffe6f0")
            rowf.pack(anchor="w", pady=2)
            Label(rowf, text="Формат:", bg="#ffe6f0").pack(side="left")
            # Привязка StringVar и обновление названия
            fvar = item["format_var"]
            OptionMenu(rowf, item["format_var"], *item["format_choices"]).pack(side="left", padx=4)
            Label(rowf, text="Качество превью:", bg="#ffe6f0").pack(side="left", padx=8)
            OptionMenu(
                rowf,
                item["preview_var"],
                *[res for res, url in item["preview_choices"]],
                command=lambda res, i=item: self.save_preview_dialog(i, res)
            ).pack(side="left")
            # Субтитры
            if item["subtitle_choices"]:
                rowf2 = Frame(right, bg="#ffe6f0")
                rowf2.pack(anchor="w", pady=2)
                Label(rowf2, text="Субтитры:", bg="#ffe6f0").pack(side="left")
                OptionMenu(rowf2, item["subtitle_var"], *item["subtitle_choices"]).pack(side="left", padx=4)
                Button(rowf2, text="⬇️", command=lambda i=item: self.download_subs(i), bg="#fff0f5").pack(side="left", padx=2)
            else:
                Label(right, text="Субтитры не найдены", bg="#ffe6f0", fg="#888").pack(anchor="w", pady=2)
            # Дубляж
            if item["dub_choices"]:
                Label(rowf, text="Дубляж:", bg="#ffe6f0").pack(side="left", padx=8)
                OptionMenu(rowf, item["dub_var"], *item["dub_choices"]).pack(side="left")
            # Кнопки
            btnf = Frame(right, bg="#ffe6f0")
            btnf.pack(anchor="w", pady=2)
            Button(btnf, text="⬇️ Скачать", command=lambda i=item: self.download_video(i), bg="#fff0f5").pack(side="left", padx=2)
            Button(btnf, text="🗑", command=lambda i=item: self.remove_item(i), bg="#ffe6f0").pack(side="left", padx=2)

        # Скрыть preview если ничего не выбрано
        # if self.selected_item is None:
        #     self.preview_frame.grid_remove()

    def remove_item(self, item):
        self.download_items.remove(item)
        self.selected_item = None
        self.render_download_items()

    def load_item_to_main(self, item):
        self.selected_item = item
        self.preview_frame.grid()
        self.build_preview_block(item)

    def build_preview_block(self, item):
        for w in self.preview_frame.winfo_children():
            w.destroy()
        # Ссылка
        Entry(self.preview_frame, width=50, state="readonly", readonlybackground="#fff0f5", fg="#333", borderwidth=0, relief="flat", font=("Arial", 10), justify="left").grid(row=0, column=0, columnspan=3, sticky="w")
        # Миниатюра и название
        try:
            response = requests.get(item["thumb_url"])
            img = Image.open(BytesIO(response.content)).resize((120, 90))
            self.preview_thumb = ImageTk.PhotoImage(img)
            preview_thumb_label = Label(self.preview_frame, image=self.preview_thumb, bg="#fff0f5")
            preview_thumb_label.grid(row=1, column=0, rowspan=3)
        except Exception:
            Label(self.preview_frame, text="(нет превью)", bg="#fff0f5").grid(row=1, column=0, rowspan=3)
        Label(self.preview_frame, text=item.get("title", ""), bg="#fff0f5", fg="#cc3366", font=("Helvetica", 12, "bold")).grid(row=1, column=1, sticky="w")
        # Формат
        Label(self.preview_frame, text="Формат:", bg="#fff0f5").grid(row=2, column=1, sticky="w")
        OptionMenu(self.preview_frame, StringVar(value="best"), "best").grid(row=2, column=2)
        # Качество превью
        Label(self.preview_frame, text="Качество превью:", bg="#fff0f5").grid(row=3, column=1, sticky="w")
        OptionMenu(self.preview_frame, self.thumb_resolution, "maxresdefault", "mqdefault").grid(row=3, column=2)
        # Субтитры
        Label(self.preview_frame, text="Субтитры:", bg="#fff0f5").grid(row=4, column=1, sticky="w")
        OptionMenu(self.preview_frame, StringVar(value="live_chat"), "live_chat").grid(row=4, column=2)
        Button(self.preview_frame, text="Скачать субтитры", command=self.dummy, bg="#ffe6f0").grid(row=4, column=3)
        # Кнопки
        Button(self.preview_frame, text="Превью", command=self.dummy, bg="#ffe6f0").grid(row=5, column=1)
        Button(self.preview_frame, text="⬇️ Скачать", command=self.dummy, bg="#ffe6f0").grid(row=5, column=2)

    def dummy(self):
        self.log("Заглушка: функция не реализована.")

    def download_all(self):
        self.log("Заглушка: скачивание всех роликов.")

    def download_all_subs(self):
        for item in self.download_items:
            self.download_subs(item)

    def download_all_previews(self):
        folder = filedialog.askdirectory(title="Выберите папку для всех превью")
        if not folder:
            return
        for item in self.download_items:
            res = item["preview_var"].get()
            url = ""
            for r, u in item["preview_choices"]:
                if r == res:
                    url = u
                    break
            if url:
                try:
                    response = requests.get(url)
                    if response.status_code == 200:
                        filename = f"{item['title']}_{res}.jpg".replace("/", "_").replace("\\", "_")
                        path = os.path.join(folder, filename)
                        with open(path, "wb") as f:
                            f.write(response.content)
                        self.log(f"Сохранено превью для '{item['title']}' в разрешении {res} в папку {folder}")
                    else:
                        self.log(f"Ошибка загрузки превью для {item['title']}")
                except Exception as e:
                    self.log(f"Ошибка: {e}")


    def download_all_videos(self):
        out_dir = filedialog.askdirectory(title="Выберите папку для всех видео")
        if not out_dir:
            return
        for item in self.download_items:
            fmt = item["format_var"].get()
            ydl_opts = {
                'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s'),
                'format': item["format_map"][fmt],
                'quiet': False,
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([item["url"]])
                    self.log(f"Скачано видео: {item['title']}")
                except Exception as e:
                    self.log(f"Ошибка скачивания: {e}")

    def download_everything(self):
        self.download_all_subs()
        self.download_all_previews()
        self.download_all_videos()

    def show_history(self):
        win = Toplevel(self.root)
        win.title("История загрузок")
        win.configure(bg="#fff0f5")
        for idx, item in enumerate(self.history_manager.history):
            frm = Frame(win, bg="#fff0f5", bd=1, relief="solid", padx=2, pady=2)
            frm.grid(row=idx, column=0, sticky="ew", pady=2)
            # Миниатюра
            try:
                response = requests.get(item["thumb_url"])
                img = Image.open(BytesIO(response.content)).resize((60, 45))
                thumb = ImageTk.PhotoImage(img)
                lbl = Label(frm, image=thumb, bg="#fff0f5")
                lbl.image = thumb
                lbl.pack(side="left")
            except Exception:
                Label(frm, text="(нет превью)", bg="#fff0f5").pack(side="left")
            # Ссылка
            url_entry = Entry(frm, width=40)
            url_entry.insert(0, item["url"])
            url_entry.pack(side="left", padx=5)
            # Кнопка вставить
            Button(frm, text="⏎", command=lambda u=item["url"]: self.url.set(u), bg="#e0e0e0").pack(side="left", padx=2)
            # Кнопка удалить
            Button(frm, text="🗑", command=lambda i=idx: self.remove_history_item(i, win), bg="#ffe6f0").pack(side="left", padx=2)
        Button(win, text="Очистить историю", command=lambda: self.clear_history(win), bg="#ffb3d9").grid(row=999, column=0, pady=5)

    def remove_history_item(self, idx, win):
        del self.history_manager.history[idx]
        self.history_manager.save_history()
        win.destroy()
        self.show_history()

    def clear_history(self, win):
        self.history_manager.history.clear()
        self.history_manager.save_history()
        win.destroy()
        self.show_history()

    def log(self, msg):
        if self.log_output:
            self.log_output.config(state="normal")
            self.log_output.insert("end", msg + "\n")
            self.log_output.see("end")
            self.log_output.config(state="disabled")
        else:
            print(msg)

    def save_preview_dialog(self, item, resolution):
        # Найти ссылку по resolution
        url = ""
        for res, u in item["preview_choices"]:
            if res == resolution:
                url = u
                break
        if not url:
            self.log("Не удалось найти превью для выбранного разрешения.")
            return
        folder = filedialog.askdirectory(title="Выберите папку для сохранения превью")
        if not folder:
            return
        try:
            response = requests.get(url)
            if response.status_code == 200:
                filename = f"{item['title']}_{resolution}.jpg".replace("/", "_").replace("\\", "_")
                path = os.path.join(folder, filename)
                with open(path, "wb") as f:
                    f.write(response.content)
                self.log(f"Сохранено превью для '{item['title']}' в разрешении {resolution} в папку {folder}")
            else:
                self.log("Ошибка загрузки превью.")
        except Exception as e:
            self.log(f"Ошибка: {e}")

    def merge_video_with_dub(self, orig_path, dub_path, out_path):
        # Проверяем, есть ли видео-дорожка в оригинале
        import subprocess
        import json

        # Получаем информацию о дорожках
        def has_video(path):
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v",
                "-show_entries", "stream=codec_type", "-of", "json", path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            info = json.loads(result.stdout)
            return bool(info.get("streams"))

        if has_video(orig_path):
            # Оригинал содержит видео — объединяем видео + дубляж
            cmd = [
                "ffmpeg", "-y",
                "-i", orig_path,
                "-i", dub_path,
                "-c:v", "copy",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                out_path
            ]
        else:
            # Оригинал — только аудио, просто копируем дубляж
            cmd = [
                "ffmpeg", "-y",
                "-i", dub_path,
                "-c", "copy",
                out_path
            ]
        subprocess.run(cmd, check=True)

    def download_video(self, item):
        def worker():
            out_dir = filedialog.askdirectory(title="Выберите папку для видео")
            if not out_dir:
                return

            # Ищем лучший видеопоток
            best_video = None
            best_height = -1
            for f in item["formats"]:
                if f.get("vcodec") != "none" and f.get("acodec") == "none":
                    h = f.get("height") or 0
                    if h > best_height:
                        best_height = h
                        best_video = f

            # Ищем лучший аудиопоток
            best_audio = None
            best_abr = -1
            for f in item["formats"]:
                if f.get("acodec") != "none" and f.get("vcodec") == "none":
                    abr = f.get("abr") or 0
                    if abr > best_abr:
                        best_abr = abr
                        best_audio = f

            orig_path = os.path.join(out_dir, f"{item['title_base']}_orig.mp4")
            out_path = os.path.join(out_dir, f"{item['title_base']}.mp4")

            if best_video and best_audio:
                video_path = os.path.join(out_dir, f"{item['title_base']}_video.mp4")
                audio_path = os.path.join(out_dir, f"{item['title_base']}_audio.m4a")

                # Скачиваем видео
                ydl_opts_video = {
                    'outtmpl': video_path,
                    'format': best_video["format_id"],
                    'quiet': False,
                    'noplaylist': True,
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                    ydl.download([item["url"]])

                # Скачиваем аудио
                ydl_opts_audio = {
                    'outtmpl': audio_path,
                    'format': best_audio["format_id"],
                    'quiet': False,
                    'noplaylist': True,
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                    ydl.download([item["url"]])

                # Объединяем
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-c", "copy",
                    orig_path
                ]
                subprocess.run(cmd, check=True)
            else:
                self.log("Не удалось найти подходящие видео и аудио потоки.")
                return

            # Дальше — объединение с дубляжом, как у вас реализовано
            if item.get("dubbed_audio_tracks"):
                # Найти выбранный формат дубляжа
                selected_dub = item["dub_var"].get()
                dub = None
                for track in item["dubbed_audio_tracks"]:
                    if track["label"] == selected_dub:
                        dub = track
                        break
                if not dub:
                    dub = item["dubbed_audio_tracks"][0]  # fallback

                dub_path = os.path.join(out_dir, f"{item['title_base']}_dub.{dub['ext']}")
                ydl_opts_dub = {
                    'outtmpl': dub_path,
                    'format': dub["format_id"],
                    'quiet': False,
                    'noplaylist': True,
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts_dub) as ydl:
                    ydl.download([item["url"]])
                self.merge_video_with_dub(orig_path, dub_path, out_path)
                # Удаляем временные файлы
                for f in [video_path, audio_path, orig_path, dub_path]:
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                    except Exception:
                        pass
            else:
                os.rename(orig_path, out_path)

        threading.Thread(target=worker, daemon=True).start()

    def download_subs(self, item):
        if not item["subtitle_choices"]:
            self.log(f"Субтитры не найдены для: {item['title']}")
            return
        lang_ext = item["subtitle_var"].get()
        sub_info = item["subtitle_map"].get(lang_ext)
        if not sub_info:
            self.log("Не выбран язык субтитров.")
            return
        out_dir = filedialog.askdirectory(title="Выберите папку для субтитров")
        if not out_dir:
            return
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'subtitleslangs': [sub_info["lang"]],
            'subtitlesformat': sub_info["ext"],
            'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
        }
        def worker():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([item["url"]])
                    self.log(f"Скачаны субтитры ({lang_ext}) для: {item['title']}")
                except Exception as e:
                    self.log(f"Ошибка скачивания субтитров: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def show_format_selector(self, item):
        win = Toplevel(self.root)
        win.title("Выберите формат")
        win.geometry("400x320")  # Ограниченная высота
        frame = Frame(win)
        frame.pack(fill="both", expand=True)
        scrollbar = Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        listbox = Listbox(frame, selectmode=SINGLE, yscrollcommand=scrollbar.set, height=15)  # Ограничить высоту
        for fmt in item["format_choices"]:
            listbox.insert(END, fmt)
        listbox.pack(fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def on_select(event):
            idx = listbox.curselection()
            if idx:
                fmt = item["format_choices"][idx[0]]
                if "дубляж" in fmt:
                    for lang in LANG_NATIVE.values():
                        if lang in fmt:
                            item["title"] = f"{item['title_base']} [{lang}]"
                            break
                else:
                    item["title"] = item["title_base"]
                item["format_var"].set(fmt)
                win.destroy()
                self.render_download_items()
        listbox.bind("<<ListboxSelect>>", on_select)

LANG_NATIVE = {
    "ru": "Русский",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "ja": "日本語",
    "ko": "한국어",
    "hi": "हिन्दी",
    "pt": "Português",
    "it": "Italiano",
    "tr": "Türkçe",
    "vi": "Tiếng Việt",
    "zh": "中文",
    "ar": "العربية",
    # ...добавьте остальные языки по необходимости...
}

def build_ui(root):
    SakuraDownloader(root)