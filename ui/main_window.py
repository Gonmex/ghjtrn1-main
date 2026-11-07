import sys
import os
import json
import sqlite3
import yt_dlp
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QInputDialog, QMessageBox, QListWidgetItem, QMenu, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import QUrl, Qt, QRect
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import services.core as core


class MDPayer(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("maket.ui", self)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.player.setVideoOutput(self.video_widget)
        self.video_widget.hide()
        self.download_widget.hide()
        self.slider_progress.hide()
        self.slider_volume.hide()
        self.widget_settings.hide()
        self.table_stats.hide()
        self.search_line.textChanged.connect(self.filter_videos)

        self.btn_new.clicked.connect(self.new_video_parameters)
        self.btn_new_video.clicked.connect(self.new_video)
        self.btn_new_collection.clicked.connect(self.create_new_collection)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_stats.clicked.connect(self.open_stats_screen)

        self.colections_list.itemClicked.connect(self.collections_double_click)
        self.folders_list.itemDoubleClicked.connect(self.video_double_click)
        
        self.folders_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folders_list.customContextMenuRequested.connect(self.show_context_menu)

        self.colections_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.colections_list.customContextMenuRequested.connect(self.show_collection_context_menu)

        self.btn_new.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_settings.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.colections_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.folders_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.download_dir = os.path.join(os.getcwd(), "downloads")
        self.current_dir = self.download_dir
        
        self.slider_volume.valueChanged.connect(self.change_volume)
        self.slider_volume.setValue(67) 

        self.player.positionChanged.connect(self.video_position_changed)
        self.player.durationChanged.connect(self.video_duration_changed)
        self.slider_progress.sliderMoved.connect(self.set_video_position)

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

        self.app_color = "Тёмная"
        self.download_dir = os.path.join(os.getcwd(), "downloads")

        if not os.path.exists("settings.txt"):
            try:
                with open("settings.txt", "w", encoding="utf-8") as f:
                    f.write("Тёмная\n")
                    f.write(os.path.join(os.getcwd(), "downloads"))
            except Exception:
                pass

        if os.path.exists("settings.txt"):
            try:
                with open("settings.txt", "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                    self.app_color = lines[0]
                    self.download_dir = lines[1]
            except Exception:
                pass

        if not os.path.exists("videos_info.txt"):
            try:
                with open("videos_info.txt", "w", encoding="utf-8") as f:
                    pass
            except Exception:
                pass

        self.selected_collection = None
        self.menu_bar_create()
        self.load_downloaded_videos()
        self.load_collections_from_db()

        self.setStyleSheet(self.get_color(self.app_color))

    def resizeEvent(self, _):
        width = self.width()
        height = self.height()

        self.colections_list.setGeometry(10, 50, 260, height - 140)
        self.folders_list.setGeometry(290, 55, width - 300, height - 80)
        self.btn_settings.setGeometry(10, height - 90, 40, 40)
        self.btn_stats.setGeometry(55, height - 90, 40, 40)
        self.btn_new_collection.setGeometry(30, height - 125, 220, 22)
        self.search_line.setGeometry(290, 10, width - 300, 35)
        self.btn_new.setGeometry(width - 70, height - 100, 50, 50)
        self.video_widget.setGeometry(0, 0, width, height - 90)

        self.line_url.setGeometry(30, 60, width - 60, 30)
        self.line_set_name.setGeometry(30, 110, width - 60, 30)
        self.label_format.setGeometry(30, 170, 100, 20)
        self.label_collections.setGeometry(200, 170, width - 230, 20)
        self.verticalLayout.setGeometry(QRect(30, 200, 120, height - 240))
        self.list_set_colections.setGeometry(240, 200, width - 260, height - 250)
        self.btn_new_video.setGeometry(width - 120, height - 80, 100, 30)
        self.download_widget.setGeometry(0, 0, width, height)

        self.widget_settings.setGeometry(0, 0, width, height)

        self.slider_progress.setGeometry(20, height - 70, width - 150, 20)
        self.slider_volume.setGeometry(width - 120, height - 70, 100, 20)
        
        self.table_stats.setGeometry(0, 0, width, height)

    def change_volume(self, value):
        vol_float = value / 100.0
        self.audio_output.setVolume(vol_float)

    def video_position_changed(self, position):
        if not self.slider_progress.isSliderDown():
            self.slider_progress.setValue(position)

    def video_duration_changed(self, duration):
        self.slider_progress.setMaximum(duration)

    def set_video_position(self, position):
        self.player.setPosition(position)

    def create_new_collection(self):
        name, ok = QInputDialog.getText(self, "Новая коллекция", "Введите название коллекции:")
        if ok and name:
            try:
                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO collections_list (name) VALUES (?)", (name,))
                conn.commit()
                conn.close()
                
                self.load_collections_from_db()
            except Exception as error:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать коллекцию: {error}")

    def load_collections_from_db(self):
        self.colections_list.clear()
        self.list_set_colections.clear()
        all_item = QListWidgetItem("Показать всё")
        all_item.setData(Qt.ItemDataRole.UserRole, "all")
        self.colections_list.addItem(all_item)
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM collections_list")
        rows = cursor.fetchall()

        for i in rows:
            coll_name = i[0]
            self.colections_list.addItem(coll_name)
            self.list_set_colections.addItem(coll_name)

        conn.close()

    def collections_double_click(self, item):
        if item.text() == "Показать всё":
            self.selected_collection = None
        else:
            self.selected_collection = item.text()

        self.current_dir = self.download_dir
        self.load_downloaded_videos()

    def menu_bar_create(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("Файл")
        exit_action = file_menu.addAction("Выход")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        nav_menu = menu_bar.addMenu("Управление")
        refresh_action = nav_menu.addAction("Обновить список")
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.load_downloaded_videos)
        refresh_action.triggered.connect(self.load_collections_from_db)
        root_action = nav_menu.addAction("На главную")
        root_action.triggered.connect(self.go_to_root_dir)

        help_menu = menu_bar.addMenu("Справка")
        about_action = help_menu.addAction("О программе")
        about_action.triggered.connect(self.show_about_dialog)

    def go_to_root_dir(self):
        self.current_dir = self.download_dir
        self.load_downloaded_videos()

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "О программе",
            "<h3>MDPlayer (Media Downloader & Player)</h3>"
            "<p>Универсальная программа для скачивания и просмотра видео.</p>"
            "<p><b>Версия:</b> 1.0<br>"
            "<b>Базируется на:</b> PyQt6, yt-dlp, FFmpeg<br>"
            "<b>Создатель:</b> Сергей Кондратьев</p>"
        )

    def new_video_parameters(self):
        self.download_widget.show()
        self.colections_list.hide()
        self.btn_settings.hide()
        self.search_line.hide()
        self.btn_new.hide()
        self.folders_list.hide()
        self.video_widget.hide()
        self.btn_new_collection.hide()
        self.btn_stats.hide()

    def foramt_parameters(self):
        if self.btn_form_aud.isChecked():
            return "audio", "bestaudio/best"
        elif self.btn_form_360.isChecked():
            return "video", "bestvideo[height<=360]+bestaudio/best[height<=360]"
        elif self.btn_form_480.isChecked():
            return "video", "bestvideo[height<=480]+bestaudio/best[height<=480]"
        elif self.btn_form_720.isChecked():
            return "video", "bestvideo[height<=720]+bestaudio/best[height<=720]"
        elif self.btn_form_1080.isChecked():
            return "video", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        elif self.btn_form_2k.isChecked():
            return "video", "bestvideo[height<=1440]+bestaudio/best[height<=1440]"
        elif self.btn_form_4k.isChecked():
            return "video", "bestvideo[height<=2160]+bestaudio/best[height<=2160]"
        return "video", "bestvideo+bestaudio/best"

    def new_video(self):
        video_name = self.line_set_name.text().strip()
        url = self.line_url.text().strip()

        if url:
            try:
                format, format_str = self.foramt_parameters()
                if format == "audio":
                    final_format = format_str  
                else:
                    final_format = f"{format_str}/best"

                ydl_opts_info = {"extract_flat": "in_playlist"}
                with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                    info_dict = ydl.extract_info(url, download=False)

                playlist_num_str = False

                if "entries" in info_dict:
                    is_noplaylist = False
                    choice = QMessageBox.question(
                        self, "Обнаружен сериал", 
                        "Скачать весь сериал целиком?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    
                    if choice == QMessageBox.StandardButton.No:
                        episode_num, ok = QInputDialog.getInt(
                            self, "Выбор серии", 
                            "Введите номер серии:", 
                            value=1, min=1, max=526742993
                        )
                        if ok:
                            playlist_num_str = str(episode_num)
                            is_noplaylist = True
                        else:
                            return
                    if video_name:
                        filename = video_name
                    else:
                        filename = info_dict.get("title", "Сериал")
                    outtmpl_path = os.path.join(os.path.join(self.download_dir, filename), "%(playlist_index)s - %(title)s.%(ext)s")

                    if playlist_num_str:
                        outtmpl_path = os.path.join(self.download_dir, f"{filename} Серия {playlist_num_str}.%(ext)s")
                    else:
                        outtmpl_path = os.path.join(os.path.join(self.download_dir, filename), "%(playlist_index)s - %(title)s.%(ext)s")
                else:
                    is_noplaylist = True
                    if video_name:
                        filename = f"{video_name}.%(ext)s"
                    else:
                        filename = "%(title)s.%(ext)s"
                    outtmpl_path = os.path.join(self.download_dir, filename)  

                ydl_opts = {
                    "format": final_format,
                    "outtmpl": outtmpl_path,
                    "merge_output_format": "mp4",
                    "ffmpeg_location": os.getcwd(),
                    "format_sort": ["vcodec:avc", "ext:mp4", "res"],
                    "noplaylist": is_noplaylist,
                    "ignoreerrors": True,
                }

                if playlist_num_str:
                    ydl_opts["playlist_items"] = playlist_num_str

                core.downloading(url, ydl_opts)

                try:
                    site = info_dict.get("extractor_key", "YouTube")
                    format_type, _ = self.foramt_parameters()
                    if format_type == "audio":
                        format_str = "Аудио"
                        quality_val = info_dict.get("abr", 128)
                        if quality_val:
                            quality_str = f"{int(quality_val)} kbps"
                        else:
                            quality_str = "High Quality"
                    else:
                        format_str = "Видео"
                        quality_val = info_dict.get("height")
                        if quality_val:
                            quality_str = f"{quality_val}p"
                        else:
                            quality_str = "High Quality"
                    if video_name:
                        name_str = video_name
                    else:
                        name_str = info_dict.get("title", "Видео")
                    if format_type == "audio":
                        clean_path = outtmpl_path.replace(".%(ext)s", ".m4a")
                    else:
                        clean_path = outtmpl_path.replace(".%(ext)s", ".mp4")
                    with open("videos_info.txt", "a", encoding="utf-8") as f:
                        f.write(f"VideO_inFO|||{name_str}|||{site}|||{format_str}|||{quality_str}|||{clean_path}\n")
                except Exception:
                    pass

                self.line_url.clear()
                self.line_set_name.clear()
                self.download_widget.hide()
                self.colections_list.show()
                self.folders_list.show()
                self.search_line.show()
                self.btn_new.show()
                self.btn_new_collection.show()
                self.btn_settings.show()
                self.btn_stats.show()
                self.current_dir = self.download_dir
                self.load_downloaded_videos()
                QMessageBox.information(self, "Ура", "Скачивание успешно завершено!")
            except Exception as error:
                QMessageBox.critical(self, "Ошибка", f"Не удалось скачать: {error}")

    def load_downloaded_videos(self):
        self.folders_list.clear()
        if self.current_dir != self.download_dir:
            back_item = QListWidgetItem("<- Вернуться назад")
            back_item.setData(Qt.ItemDataRole.UserRole, "back")
            self.folders_list.addItem(back_item)
            
        allowed_paths = []
        if self.selected_collection:
            try:
                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()
                cursor.execute("SELECT file_path FROM video_collections WHERE collection_name = ?", (self.selected_collection,))
                for i in cursor.fetchall():
                    allowed_paths.append(os.path.abspath(i[0]))
                conn.close()
            except Exception:
                pass
                
        if os.path.exists(self.current_dir):
            for file_name in os.listdir(self.current_dir):
                full_path = os.path.abspath(os.path.join(self.current_dir, file_name))
                if self.selected_collection and (full_path not in allowed_paths):
                    continue
                if os.path.isdir(full_path):
                    item = QListWidgetItem(file_name)
                    item.setData(Qt.ItemDataRole.UserRole, full_path)
                    self.folders_list.addItem(item)
                elif file_name.endswith(".mp4") or file_name.endswith(".m4a"):
                    video_title, _ = os.path.splitext(file_name)
                    item = QListWidgetItem(video_title)
                    item.setData(Qt.ItemDataRole.UserRole, full_path)
                    self.folders_list.addItem(item)

    def video_double_click(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path == "back":
            self.current_dir = self.download_dir
            self.load_downloaded_videos()
        elif path and os.path.isdir(path):
            self.current_dir = path
            self.load_downloaded_videos()
        elif path and os.path.exists(path):
            self.play_video(path)

    def show_collection_context_menu(self, position):
        item = self.colections_list.itemAt(position)
        if item is not None and item.data(Qt.ItemDataRole.UserRole) != "all":
            menu = QMenu(self)
            delete_action = menu.addAction("Удалить")
            action = menu.exec(self.colections_list.mapToGlobal(position))
            if action == delete_action:
                self.delete_collection(item)

    def show_context_menu(self, position):
        item = self.folders_list.itemAt(position)
        if item != None:
            path = item.data(Qt.ItemDataRole.UserRole)
            if path == "back":
                return
            menu = QMenu(self)
            delete_do = menu.addAction("Удалить")
            collection_menu = menu.addMenu("добавить в коллекцию")
            
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            rows = cursor.execute("SELECT name FROM collections_list").fetchall()
            conn.close()
            
            for i in rows:
                coll_name = i[0]
                action = collection_menu.addAction(coll_name)
                action.setData(coll_name)
            if not collection_menu.actions():
                no_col_action = collection_menu.addAction("Нет созданных коллекций")
                no_col_action.setEnabled(False)
                
            do = menu.exec(self.folders_list.mapToGlobal(position))
            if do == delete_do:
                self.delete_item(item)
            elif do in collection_menu.actions():
                self.add_to_collection_from_menu(path, do.data())

    def add_to_collection_from_menu(self, path, name):
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO video_collections (file_path, collection_name) VALUES (?, ?)", (path, name))
            conn.commit()
            conn.close()
            self.load_downloaded_videos()
            QMessageBox.information(self, "Ура", f"Видео успешно добавлено в коллекцию '{name}'")
        except Exception as error:
            QMessageBox.critical(self, "Ошибка", f"Не удалось привязать к коллекции: {error}")

    def delete_item(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        title = item.text()
        if QMessageBox.question(self, "Удаление", f"Удалить '{title}' с компьютера?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                self.player.stop()
                self.player.setSource(QUrl())
                if path and os.path.exists(path):
                    if os.path.isdir(path):
                        for file_name in os.listdir(path):
                            os.remove(os.path.join(path, file_name))
                        os.rmdir(path)
                    else:
                        os.remove(path)
                self.load_downloaded_videos()
                QMessageBox.information(self, "Успешно", "Удалено")
            except Exception as error:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить: {error}")
    def delete_collection(self, item):
        name = item.text()
        if QMessageBox.question(self, "Удаление коллекции", f"Вы уверены, что хотите удалить коллекцию '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM collections_list WHERE name = ?", (name,))
                cursor.execute("DELETE FROM video_collections WHERE collection_name = ?", (name,))
                conn.commit()
                conn.close()
                if self.selected_collection == name:
                    self.selected_collection = None
                self.load_collections_from_db()
                self.load_downloaded_videos()
                QMessageBox.information(self, "Успешно", f"Коллекция '{name}' удалена.")
            except Exception as error:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить коллекцию: {error}")

    def play_video(self, file_path):
        self.colections_list.hide()
        self.btn_settings.hide()
        self.search_line.hide()
        self.btn_new.hide()
        self.folders_list.hide()
        self.btn_new_collection.hide()
        self.btn_stats.hide()
        self.video_widget.show()
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.slider_volume.setValue(67)
        self.player.play()
        self.setFocus()
        self.slider_progress.show()
        self.slider_volume.show()
        self.slider_progress.raise_()
        self.slider_volume.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.video_widget.isVisible() or self.download_widget.isVisible() or self.widget_settings.isVisible() or self.table_stats.isVisible():
                self.player.stop()
                self.video_widget.hide()
                self.download_widget.hide()
                self.slider_progress.hide()
                self.slider_volume.hide()
                self.table_stats.hide()
                if self.widget_settings.isVisible():
                    self.save_settings()
                self.widget_settings.hide()
                self.colections_list.show()
                self.folders_list.show()
                self.search_line.show()
                self.btn_new.show()
                self.btn_settings.show()
                self.btn_new_collection.show()
                self.btn_stats.show()
            elif self.current_dir != self.download_dir:
                self.current_dir = self.download_dir
                self.load_downloaded_videos()
        if event.key() == Qt.Key.Key_Space and self.video_widget.isVisible():
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()

    def filter_videos(self, text):
        search_text = text.lower()
        for i in range(self.folders_list.count()):
            item = self.folders_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) != "back":
                item.setHidden(search_text not in item.text().lower())

    def open_settings(self):
        self.widget_settings.show()
        self.download_widget.hide()
        self.colections_list.hide()
        self.btn_settings.hide()
        self.search_line.hide()
        self.btn_new.hide()
        self.folders_list.hide()
        self.video_widget.hide()
        self.btn_new_collection.hide()
        self.btn_stats.hide()
        self.combo_box_color.setCurrentText(self.app_color)
        self.line_path.setText(self.download_dir)

    def get_color(self, color_name):
        try:
            with open("stiles.json", "r", encoding="utf-8") as file:
                return json.load(file).get(color_name)
        except Exception as error:
            QMessageBox.critical(self, "Ошибка", f"Поставлена тема 'Тёмная' т.к. ошибка чтения stiles.json: {error}")
            return "Тёмная"

    def save_settings(self):
        self.app_color = self.combo_box_color.currentText()
        self.download_dir = self.line_path.text()
        try:
            with open("settings.txt", "w", encoding="utf-8") as f:
                f.write(f"{self.app_color}\n{self.download_dir}")
            self.current_dir = self.download_dir
            self.setStyleSheet(self.get_color(self.app_color))
        except Exception as error:
            QMessageBox.critical(self, "Ошибка", error)

    def open_stats_screen(self):
        self.table_stats.show()
        self.colections_list.hide()
        self.folders_list.hide()
        self.search_line.hide()
        self.btn_new.hide()
        self.btn_settings.hide()
        self.btn_new_collection.hide()
        self.btn_stats.hide()
        self.table_stats.setColumnCount(5)
        self.table_stats.setHorizontalHeaderLabels(["Название", "Сайт", "Формат", "Качество", "Путь на ПК"])
        self.table_stats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_stats.setRowCount(0)


        if os.path.exists("videos_info.txt"):
            try:
                with open("videos_info.txt", "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                video_rows = []
                for line in lines:
                    if line.startswith("VideO_inFO|||"):
                        parts = line.split("|||")
                        if len(parts) >= 5:
                            video_rows.append([parts[1], parts[2], parts[3], parts[4], parts[5]])
                self.table_stats.setRowCount(len(video_rows))
                for row_index, data in enumerate(video_rows):
                    for col_index, text in enumerate(data):
                        self.table_stats.setItem(row_index, col_index, QTableWidgetItem(text))
            except Exception:
                pass