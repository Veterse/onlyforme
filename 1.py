import subprocess
import os
import time
import json
import pyautogui
import customtkinter as ctk
from tkinter import messagebox
import threading
import cv2
import numpy as np
import random

# Настройки CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

try:
    from steam_totp import generate_twofactor_code_for_time
except ImportError:
    print("❌ ОШИБКА: Библиотека 'steam-totp' не установлена!")
    print("Выполните: pip install steam-totp")
    exit()

try:
    import win32gui
    import win32con
except ImportError:
    print("❌ ОШИБКА: Библиотека 'pywin32' не установлена!")
    print("Выполните: pip install pywin32")
    exit()

# Проверяем наличие pyautogui
try:
    import pyautogui
    # Настройки безопасности pyautogui
    pyautogui.PAUSE = 0.5  # Пауза между действиями
    pyautogui.FAILSAFE = False
except ImportError:
    print("❌ ОШИБКА: Библиотека 'pyautogui' не установлена!")
    print("Выполните: pip install pyautogui")
    exit()

# --- НАСТРОЙКИ ---
ACCOUNTS_FILE_PATH = "accounts.txt"
MAFILES_DIR_PATH = "E:/sandbox/maFiles"
STEAM_PATH = r"C:\Program Files (x86)\Steam\steam.exe"
CSGO_APP_ID = "730"
COLORS_FILE_PATH = "account_colors.json"

class SteamLauncherGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("🎮 CS2 Multi-Account Launcher")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        self.accounts = []
        self.account_vars = []
        self.account_colors = {}  # Словарь для хранения цветов аккаунтов
        self.account_frames = []  # Список фреймов аккаунтов для изменения цвета
        self.account_color_btns = []  # Кнопки цвета
        self.is_running = False
        self.failed_accounts = []
        self.first_account_launched = False  # Флаг: был ли запущен хотя бы один аккаунт
        
        self.load_colors()  # Загружаем сохраненные цвета
        self.setup_ui()
        self.load_accounts()
    def create_csgo_autoexec(self, width, height):
        try:
            csgo_cfg_path = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\cfg\autoexec.cfg"
            
            cfg_dir = os.path.dirname(csgo_cfg_path)
            if not os.path.exists(cfg_dir):
                print(f"⚠️ Папка конфигов не найдена: {cfg_dir}")
                return False
            
            config_content = f"mat_setvideomode {width} {height} 0\nfps_max 60\n"
            
            with open(csgo_cfg_path, 'w') as f:
                f.write(config_content)
            
            print(f"✅ Создан autoexec.cfg: {width}x{height}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания конфига: {e}")
            return False
    def load_colors(self):
        """Загружает сохраненные цвета аккаунтов из JSON файла."""
        try:
            if os.path.exists(COLORS_FILE_PATH):
                with open(COLORS_FILE_PATH, 'r', encoding='utf-8') as f:
                    self.account_colors = json.load(f)
                    print(f"✅ Загружены цвета для {len(self.account_colors)} аккаунтов")
            else:
                self.account_colors = {}
                print("ℹ️ Файл цветов не найден, создается новый")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки цветов: {e}")
            self.account_colors = {}
    
    def save_colors(self):
        """Сохраняет цвета аккаунтов в JSON файл."""
        try:
            with open(COLORS_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.account_colors, f, indent=2, ensure_ascii=False)
            print(f"✅ Сохранены цвета для {len(self.account_colors)} аккаунтов")
        except Exception as e:
            print(f"❌ Ошибка сохранения цветов: {e}")
    
    def toggle_account_color(self, login, frame):
        """УСТАРЕВШИЙ МЕТОД - теперь используется цветовой чекбокс."""
        pass
    
    def get_account_color(self, login):
        """Возвращает цвет фона для аккаунта."""
        color = self.account_colors.get(login, "white")
        if color == "red":
            return "#3d1a1a"  # Тёмно-красный для dark mode
        return "#1a1a2e"  # Тёмно-синий для dark mode
    
    def find_steam_element_cv(self, template_path, confidence=0.8):
        """Находит элемент Steam используя OpenCV template matching."""
        try:
            # Делаем скриншот экрана
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)
            
            # Загружаем шаблон
            if not os.path.exists(template_path):
                print(f"⚠️ Шаблон не найден: {template_path}")
                return None
                
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            
            # Ищем совпадения
            result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= confidence:
                # Возвращаем центр найденного элемента
                h, w = template.shape
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                print(f"✅ Элемент найден в ({center_x}, {center_y}), точность: {max_val:.2f}")
                return (center_x, center_y)
            else:
                print(f"❌ Элемент не найден, лучшее совпадение: {max_val:.2f}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка поиска элемента: {e}")
            return None
    
    def find_text_field_cv(self, steam_window):
        """Находит активное текстовое поле в окне Steam."""
        try:
            # Делаем скриншот области окна Steam
            left, top, width, height = steam_window.left, steam_window.top, steam_window.width, steam_window.height
            
            # Скриншот только области Steam
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            screenshot_np = np.array(screenshot)
            screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)
            
            # Ищем прямоугольники (поля ввода) с помощью контуров
            edges = cv2.Canny(screenshot_gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Ищем прямоугольные контуры подходящего размера
            text_fields = []
            for contour in contours:
                # Аппроксимируем контур
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Проверяем что это прямоугольник
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Фильтруем по размеру (поля ввода должны быть определенного размера)
                    if 100 < w < 400 and 20 < h < 60:
                        # Переводим обратно в экранные координаты
                        screen_x = left + x + w // 2
                        screen_y = top + y + h // 2
                        text_fields.append((screen_x, screen_y, w, h))
            
            # Сортируем по Y координате (сначала верхние поля)
            text_fields.sort(key=lambda field: field[1])
            
            if text_fields:
                print(f"✅ Найдено {len(text_fields)} текстовых полей")
                return text_fields
            else:
                print("❌ Текстовые поля не найдены")
                return []
                
        except Exception as e:
            print(f"❌ Ошибка поиска текстовых полей: {e}")
            return []
        
    def setup_ui(self):
        """Создает интерфейс приложения."""
        # Главный контейнер
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # === HEADER ===
        header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        
        title_label = ctk.CTkLabel(header_frame, text="🎮 CS2 Multi-Account Launcher",
                                   font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack()
        
        subtitle = ctk.CTkLabel(header_frame, text="Запуск нескольких аккаунтов через Avast Sandbox",
                                font=ctk.CTkFont(size=12), text_color="gray")
        subtitle.pack()
        
        # === ACCOUNTS LIST ===
        accounts_container = ctk.CTkFrame(self.root)
        accounts_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        accounts_container.grid_columnconfigure(0, weight=1)
        accounts_container.grid_rowconfigure(1, weight=1)
        
        list_header = ctk.CTkLabel(accounts_container, text="📋 Аккаунты",
                                   font=ctk.CTkFont(size=14, weight="bold"))
        list_header.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))
        
        self.scrollable_frame = ctk.CTkScrollableFrame(accounts_container, fg_color="transparent")
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # === SETTINGS ===
        settings_frame = ctk.CTkFrame(self.root)
        settings_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        settings_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Смещение
        offset_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        offset_frame.grid(row=0, column=0, sticky="w", padx=15, pady=10)
        
        ctk.CTkLabel(offset_frame, text="⚙️ Уже запущено:",
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        
        self.offset_var = ctk.StringVar(value="0")
        self.offset_entry = ctk.CTkEntry(offset_frame, textvariable=self.offset_var,
                                         width=50, font=ctk.CTkFont(size=13), justify="center")
        self.offset_entry.pack(side="left")
        
        # Быстрый режим
        fast_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        fast_frame.grid(row=0, column=1, sticky="e", padx=15, pady=10)
        
        self.fast_mode_var = ctk.BooleanVar(value=False)
        self.fast_mode_switch = ctk.CTkSwitch(fast_frame, text="⚡ Быстрый режим (80 сек)",
                                              variable=self.fast_mode_var,
                                              font=ctk.CTkFont(size=12))
        self.fast_mode_switch.pack(side="right")
        
        # === BUTTONS ===
        buttons_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        buttons_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        buttons_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        
        self.select_all_btn = ctk.CTkButton(buttons_frame, text="☑️ Все",
                                            command=self.select_all_accounts,
                                            fg_color="#2d5a27", hover_color="#3d7a37",
                                            font=ctk.CTkFont(size=12), height=38)
        self.select_all_btn.grid(row=0, column=0, padx=3, sticky="ew")
        
        self.deselect_btn = ctk.CTkButton(buttons_frame, text="⬜ Снять",
                                          command=self.deselect_all_accounts,
                                          fg_color="#5a4527", hover_color="#7a5537",
                                          font=ctk.CTkFont(size=12), height=38)
        self.deselect_btn.grid(row=0, column=1, padx=3, sticky="ew")
        
        self.launch_btn = ctk.CTkButton(buttons_frame, text="🚀 ЗАПУСТИТЬ",
                                        command=self.start_launching,
                                        fg_color="#1a7f37", hover_color="#2ea44f",
                                        font=ctk.CTkFont(size=14, weight="bold"), height=42)
        self.launch_btn.grid(row=0, column=2, padx=8, sticky="ew")
        
        self.stop_btn = ctk.CTkButton(buttons_frame, text="⏹ СТОП",
                                      command=self.stop_launching,
                                      fg_color="#8b0000", hover_color="#b22222",
                                      font=ctk.CTkFont(size=12, weight="bold"), height=38,
                                      state="disabled")
        self.stop_btn.grid(row=0, column=3, padx=3, sticky="ew")
        
        self.shuffle_btn = ctk.CTkButton(buttons_frame, text="🔀 SHUFFLE",
                                         command=self.shuffle_lobbies,
                                         fg_color="#6b2d7b", hover_color="#8b3d9b",
                                         font=ctk.CTkFont(size=12, weight="bold"), height=38)
        self.shuffle_btn.grid(row=0, column=4, padx=3, sticky="ew")
        
        # === STATUS ===
        status_frame = ctk.CTkFrame(self.root)
        status_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(5, 15))
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(status_frame, text="✅ Готов к запуску",
                                         font=ctk.CTkFont(size=12), anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew", padx=15, pady=(8, 4))
        
        self.progress = ctk.CTkProgressBar(status_frame, height=6)
        self.progress.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.progress.set(0)
        
    def load_accounts(self):
        """Загружает список аккаунтов из файлов."""
        self.status_label.configure(text="⏳ Загружаю аккаунты...")
        
        try:
            if not os.path.exists(ACCOUNTS_FILE_PATH):
                messagebox.showerror("Ошибка", f"Файл аккаунтов не найден: '{ACCOUNTS_FILE_PATH}'")
                return
                
            if not os.path.isdir(MAFILES_DIR_PATH):
                messagebox.showerror("Ошибка", f"Папка с maFile не найдена: '{MAFILES_DIR_PATH}'")
                return
            
            # Читаем аккаунты
            with open(ACCOUNTS_FILE_PATH, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if ':' in line:
                        login, password = line.split(':', 1)
                        
                        # Ищем соответствующий maFile
                        mafile_found = False
                        for filename in os.listdir(MAFILES_DIR_PATH):
                            if filename.lower().endswith(".mafile"):
                                filepath = os.path.join(MAFILES_DIR_PATH, filename)
                                try:
                                    with open(filepath, 'r') as mf:
                                        mafile_data = json.load(mf)
                                        if mafile_data.get('account_name') == login:
                                            self.accounts.append({
                                                'login': login,
                                                'password': password,
                                                'shared_secret': mafile_data.get('shared_secret'),
                                                'mafile_path': filepath
                                            })
                                            mafile_found = True
                                            break
                                except Exception as e:
                                    print(f"Ошибка чтения {filename}: {e}")
                        
                        if not mafile_found:
                            print(f"⚠️ maFile для аккаунта '{login}' не найден!")
            
            # Создаем виджеты для каждого аккаунта
            for i, account in enumerate(self.accounts):
                self.create_account_widget(i, account)
            
            self.status_label.configure(text=f"✅ Загружено {len(self.accounts)} аккаунтов")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке аккаунтов: {e}")
            self.status_label.configure(text="❌ Ошибка загрузки аккаунтов")
    
    def create_account_widget(self, index, account):
        """Создает виджет для одного аккаунта."""
        login = account['login']
        is_red = self.account_colors.get(login, "white") == "red"
        
        # Фрейм аккаунта
        frame = ctk.CTkFrame(self.scrollable_frame,
                             fg_color="#3d1a1a" if is_red else "#1a1a2e",
                             corner_radius=8)
        frame.grid(row=index, column=0, sticky="ew", pady=3, padx=5)
        frame.grid_columnconfigure(1, weight=1)
        self.account_frames.append(frame)
        
        # Чекбокс выбора
        var = ctk.BooleanVar(value=False)
        self.account_vars.append(var)
        
        checkbox = ctk.CTkCheckBox(frame, text="", variable=var,
                                   width=24, checkbox_width=22, checkbox_height=22,
                                   corner_radius=5, fg_color="#1a7f37", hover_color="#2ea44f")
        checkbox.grid(row=0, column=0, padx=(12, 8), pady=10)
        
        # Имя аккаунта
        name_label = ctk.CTkLabel(frame, text=f"🎮 {login}",
                                  font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        name_label.grid(row=0, column=1, sticky="w", pady=10)
        
        # Статус maFile
        status_label = ctk.CTkLabel(frame, text="✅ maFile",
                                    font=ctk.CTkFont(size=11), text_color="#4ade80")
        status_label.grid(row=0, column=2, padx=10, pady=10)
        
        # Кнопка цвета
        color_btn = ctk.CTkButton(frame, text="🎨", width=36, height=28,
                                  fg_color="#8b0000" if is_red else "#2d2d44",
                                  hover_color="#b22222" if is_red else "#3d3d54",
                                  font=ctk.CTkFont(size=14),
                                  command=lambda l=login, idx=index: self.toggle_color(l, idx))
        color_btn.grid(row=0, column=3, padx=(5, 12), pady=10)
        self.account_color_btns.append(color_btn)
    
    def toggle_color(self, login, index):
        """Переключает цвет аккаунта."""
        current = self.account_colors.get(login, "white")
        new_color = "white" if current == "red" else "red"
        self.account_colors[login] = new_color
        
        is_red = new_color == "red"
        self.account_frames[index].configure(fg_color="#3d1a1a" if is_red else "#1a1a2e")
        self.account_color_btns[index].configure(
            fg_color="#8b0000" if is_red else "#2d2d44",
            hover_color="#b22222" if is_red else "#3d3d54"
        )
        self.save_colors()
    
    def select_all_accounts(self):
        """Выбирает все аккаунты."""
        for var in self.account_vars:
            var.set(True)
    
    def deselect_all_accounts(self):
        """Снимает выделение со всех аккаунтов."""
        for var in self.account_vars:
            var.set(False)
    def set_csgo_launch_options(self, width, height):
    
        try:
            import re
            
            steam_dir = os.path.dirname(STEAM_PATH)
            userdata_path = os.path.join(steam_dir, "userdata")
            
            if not os.path.exists(userdata_path):
                print("❌ Папка userdata не найдена")
                return False
            
            # Находим все папки пользователей
            user_dirs = [d for d in os.listdir(userdata_path) if os.path.isdir(os.path.join(userdata_path, d)) and d.isdigit()]
            
            if not user_dirs:
                print("❌ Папки пользователей не найдены")
                return False
            
            # Берем последнюю папку (последний залогиненный)
            user_dir = sorted(user_dirs, key=lambda x: os.path.getmtime(os.path.join(userdata_path, x)))[-1]
            config_path = os.path.join(userdata_path, user_dir, "config", "localconfig.vdf")
            
            if not os.path.exists(config_path):
                print(f"❌ localconfig.vdf не найден: {config_path}")
                return False
            
            # Читаем файл
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Параметры запуска
            launch_options = f"-windowed -w {width} -h {height} +fps_max 60 +exec autoexec"
            
            # Ищем секцию CS:GO (730) и обновляем LaunchOptions
            pattern = r'("730"\s*\{[^}]*?"LaunchOptions"\s*")([^"]*?)(")'
            
            if re.search(r'"730"', content):
                if re.search(pattern, content):
                    content = re.sub(pattern, r'\1' + launch_options + r'\3', content)
                else:
                    pattern_add = r'("730"\s*\{)'
                    replacement = r'\1\n\t\t\t\t"LaunchOptions"\t\t"' + launch_options + '"'
                    content = re.sub(pattern_add, replacement, content, count=1)
            else:
                apps_pattern = r'("Apps"\s*\{)'
                new_section = f'\n\t\t"730"\n\t\t{{\n\t\t\t"LaunchOptions"\t\t"{launch_options}"\n\t\t}}'
                content = re.sub(apps_pattern, r'\1' + new_section, content, count=1)
            
            # Записываем обратно
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Параметры запуска сохранены: {launch_options}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка установки параметров запуска: {e}")
            return False
    def get_offset_accounts(self):
        """Возвращает количество уже запущенных аккаунтов."""
        try:
            offset_text = self.offset_var.get().strip()
            if offset_text == "":
                return 0
            offset = int(offset_text)
            return max(0, offset)  # Не может быть отрицательным
        except ValueError:
            print("⚠️ Некорректное значение смещения, использую 0")
            return 0
    
    def get_selected_accounts(self):
        """Возвращает список выбранных аккаунтов."""
        selected = []
        for i, var in enumerate(self.account_vars):
            if var.get():
                selected.append(self.accounts[i])
        return selected
    
    def calculate_window_position(self, account_index):
        """Вычисляет позицию окна CS:GO для конкретного аккаунта с учетом смещения."""
        # Получаем смещение (количество уже запущенных аккаунтов)
        offset = self.get_offset_accounts()
        
        # Размеры окна CS:GO
        window_width = 400   # ширина окна
        window_height = 300  # высота окна
        margin_x = 20        # отступ между окнами по горизонтали
        margin_y = 50        # отступ между окнами по вертикали
        
        # Общий индекс с учетом смещения
        total_index = offset + account_index
        
        # Вычисляем позицию в сетке
        windows_per_row = 4  # количество окон в строке
        row = total_index // windows_per_row
        col = total_index % windows_per_row
        
        x = margin_x + col * (window_width + margin_x)
        y = margin_y + row * (window_height + margin_y)
        
        print(f" ОТЛАДКА: Смещение={offset}, индекс аккаунта={account_index}, общий индекс={total_index}")
        print(f" ОТЛАДКА: Сетка - строка={row}, колонка={col}, позиция=({x}, {y})")
        
        return x, y, window_width, window_height
    
    def start_launching(self):
        """Начинает процесс запуска выбранных аккаунтов."""
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы один аккаунт!")
            return
        
        # Проверяем корректность значения смещения
        try:
            offset = self.get_offset_accounts()
        except:
            messagebox.showerror("Ошибка", "Некорректное значение количества уже запущенных аккаунтов!")
            return
        
        offset_text = f"Смещение: +{offset} " if offset > 0 else ""
        result = messagebox.askyesno("Подтверждение", 
                                   f"Запустить {len(selected_accounts)} аккаунт(ов)?\n"
                                   f"{offset_text}\n"
                                   f"Процесс займет примерно {len(selected_accounts) * 4} минуты.")
        
        if result:
            self.is_running = True
            self.launch_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            
            # Запускаем в отдельном потоке
            thread = threading.Thread(target=self.launch_accounts_thread, 
                                    args=(selected_accounts,), daemon=True)
            thread.start()
    
    def stop_launching(self):
        """Останавливает процесс запуска."""
        self.is_running = False
        self.launch_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="⏹ Остановлено пользователем")
        self.progress.set(0)
    
    def launch_accounts_thread(self, selected_accounts):
        """Поток для запуска аккаунтов по очереди."""
        print(f"\n🔍 ОТЛАДКА: Начинаю launch_accounts_thread")
        print(f"🔍 ОТЛАДКА: Всего выбрано аккаунтов: {len(selected_accounts)}")
        
        for i, acc in enumerate(selected_accounts):
            print(f"🔍 ОТЛАДКА: Аккаунт {i+1}: {acc['login']}")
        
        total_accounts = len(selected_accounts)
        print(f"🔍 ОТЛАДКА: total_accounts = {total_accounts}")
        
        for i, account in enumerate(selected_accounts):
            print(f"\n🔍 ОТЛАДКА: Начинаю цикл для аккаунта {i+1}/{total_accounts}")
            print(f"🔍 ОТЛАДКА: self.is_running = {self.is_running}")
            
            if not self.is_running:
                print("🔍 ОТЛАДКА: Прерывание - self.is_running = False")
                break
                
            try:
                print(f"🔍 ОТЛАДКА: Обновляю статус для аккаунта {account['login']}")
                self.root.after(0, lambda: self.status_label.configure(
                    text=f"🚀 Запускаю {i+1}/{total_accounts}: {account['login']}"))
                
                # Вычисляем позицию окна для этого аккаунта
                window_pos = self.calculate_window_position(i)
                print(f"🔍 ОТЛАДКА: Позиция окна: {window_pos}")
                
                # Запускаем аккаунт
                print(f"🔍 ОТЛАДКА: Вызываю launch_single_account для {account['login']}")
                success = self.launch_single_account(account, window_pos, i+1)
                print(f"🔍 ОТЛАДКА: launch_single_account вернул: {success}")
                
                if success:
                    print(f"🔍 ОТЛАДКА: Аккаунт {account['login']} успешен")
                    self.root.after(0, lambda: self.status_label.configure(
                        text=f"✅ {account['login']} запущен!"))
                else:
                    print(f"🔍 ОТЛАДКА: Ошибка аккаунта {account['login']}")
                    self.failed_accounts.append(account['login'])
                    self.root.after(0, lambda: self.status_label.configure(
                        text=f"❌ Ошибка: {account['login']}"))
                
                # Обновляем прогресс
                progress_value = (i + 1) / total_accounts
                print(f"🔍 ОТЛАДКА: Прогресс: {progress_value*100}%")
                self.root.after(0, lambda pv=progress_value: self.progress.set(pv))
                
                print(f"🔍 ОТЛАДКА: Завершил аккаунт {i+1}/{total_accounts}")
                
                # Проверяем, остались ли еще аккаунты
                if i + 1 < total_accounts:
                    print(f"🔍 ОТЛАДКА: Переходим к следующему аккаунту ({i+2}/{total_accounts})")
                else:
                    print(f"🔍 ОТЛАДКА: Это был последний аккаунт")
                
            except Exception as e:
                print(f"🔍 ОТЛАДКА: Исключение в цикле: {e}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: messagebox.showerror("Ошибка", 
                                f"Ошибка при запуске {account['login']}: {e}"))
        
        print(f"🔍 ОТЛАДКА: Цикл завершен. self.is_running = {self.is_running}")
        
        # Завершение
        if self.is_running:
            print(f"🔍 ОТЛАДКА: Завершение успешное")
            
            if self.failed_accounts:
                error_msg = f"\n{'='*60}\n❌ АККАУНТЫ С ОШИБКАМИ:\n"
                for failed_login in self.failed_accounts:
                    error_msg += f"   • {failed_login}\n"
                error_msg += f"{'='*60}\n"
                print(error_msg)
            
            success_count = total_accounts - len(self.failed_accounts)
            self.root.after(0, lambda: self.status_label.configure(
                text=f"✅ Завершено! Успешно: {success_count}/{total_accounts}"))
            self.failed_accounts = []
        else:
            print(f"🔍 ОТЛАДКА: Завершение прервано")
        
        self.root.after(0, lambda: self.launch_btn.configure(state="normal"))
        self.root.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.is_running = False
        print(f"🔍 ОТЛАДКА: launch_accounts_thread завершен")
    
    def launch_single_account(self, account, window_pos, account_number):
        """Запускает один аккаунт со всеми этапами."""
        try:
            login = account['login']
            password = account['password']
            shared_secret = account['shared_secret']
            x, y, width, height = window_pos
            
            print(f"\n{'='*60}")
            print(f"🚀 ЗАПУСК АККАУНТА #{account_number}: {login}")
            print(f"📍 Позиция окна: ({x}, {y}), размер: {width}x{height}")
            print(f"{'='*60}")
            
            # 1. Запускаем Steam (Avast автоматически изолирует)
            STEAM_DIR = os.path.dirname(STEAM_PATH)
            loginusers = os.path.join(STEAM_DIR, "config", "loginusers.vdf")
            loginusers_bak = loginusers + ".bak"

            if os.path.exists(loginusers_bak):
                os.remove(loginusers_bak)

            if os.path.exists(loginusers):
                os.rename(loginusers, loginusers_bak)
            print("📝 Записываю параметры запуска в конфиг...")
            self.set_csgo_launch_options(width, height)
            time.sleep(1)
            command = [STEAM_PATH, "-reset", "-noreactlogin"]
            subprocess.Popen(command)
            print("✅ Steam запущен!")
            
            # 2. Ждем появления окна Steam
            print("🔍 ОТЛАДКА: Начинаю wait_for_steam_window...")
            if not self.wait_for_steam_window():
                print("❌ Окно Steam не появилось!")
                return False
            print("🔍 ОТЛАДКА: wait_for_steam_window завершен успешно")
            
            # 3. Ждем загрузки Steam
            print("⏳ Жду загрузки Steam (50 секунд)...")
            time.sleep(39)
            print("🔍 ОТЛАДКА: Ожидание загрузки Steam завершено")
            
            # 4. Обрабатываем экран выбора профиля или логина
            print("🔍 ОТЛАДКА: Начинаю detect_screen_type_and_handle...")
            screen_detected, screen_type = self.detect_screen_type_and_handle()
            if not screen_detected:
                print("❌ Не удалось определить тип экрана Steam")
                return False
            print(f"🔍 ОТЛАДКА: detect_screen_type_and_handle завершен: {screen_type}")
            
            if screen_type == "profile_selection":
                print("⏳ Жду загрузки экрана логина...")
                time.sleep(3)
                print("🔍 ОТЛАДКА: Ожидание экрана логина завершено")
            
            # 5. Выполняем автологин
            print("🔍 ОТЛАДКА: Начинаю auto_login_by_coordinates...")
            if not self.auto_login_by_coordinates(login, password, shared_secret):
                print("❌ Автологин не удался")
                return False
            print("🔍 ОТЛАДКА: auto_login_by_coordinates завершен успешно")

# 5.5. Создаем autoexec.cfg с нужным разрешением
            time.sleep(3)
            autoexec_path = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\cfg\autoexec.cfg"
            try:
                with open(autoexec_path, 'w') as f:
                    f.write(f'mat_setvideomode {width} {height} 0\n')
                    f.write('fps_max 60\n')
                print(f"✅ Создан autoexec.cfg с разрешением {width}x{height}")
            except Exception as e:
                print(f"⚠️ Ошибка создания autoexec.cfg: {e}")

            print("📝 Устанавливаю параметры запуска...")
            # self.set_csgo_launch_options(width, height)
            # 6. Запускаем CS:GO
            print("🎮 Запускаю CS:GO...")
            print("🔍 ОТЛАДКА: Начинаю launch_csgo...")
            if not self.launch_csgo(width, height):
                print("❌ Не удалось запустить CS:GO")
                return False
            print("🔍 ОТЛАДКА: launch_csgo завершен успешно")
            
            # 7. Ждем запуска CS:GO
            print("🔍 ОТЛАДКА: Начинаю ожидание CS:GO...")
            
            # Проверяем режим запуска
            fast_mode = self.fast_mode_var.get()
            
            if fast_mode:
                # Быстрый режим: все аккаунты по 80 секунд
                print("⚡ Быстрый режим включен: жду 80 секунд...")
                time.sleep(80)
            else:
                # Обычный режим: только самый первый аккаунт за всю сессию 130 сек
                if not self.first_account_launched:
                    print("⏳ Самый первый аккаунт сессии: жду 130 секунд...")
                    time.sleep(130)
                    self.first_account_launched = True  # Помечаем, что первый аккаунт запущен
                else:
                    print("⏳ Последующий аккаунт: жду 80 секунд...")
                    time.sleep(80)
            print("🔍 ОТЛАДКА: Ожидание CS:GO завершено")
            
            # 8. Закрываем Steam СНАЧАЛА
            print("🔄 Закрываю Steam...")
            time.sleep(5)
            print("🔍 ОТЛАДКА: Начинаю close_steam_keep_csgo...")
            self.close_steam_keep_csgo()
            print("🔍 ОТЛАДКА: close_steam_keep_csgo завершен")
            
            # 9. ПОТОМ перемещаем CS:GO (чтобы он не вернулся в центр)
            print("🔄 Перемещаю CS:GO после закрытия Steam...")
            print("🔍 ОТЛАДКА: Начинаю move_csgo_window_to_position...")
            if self.move_csgo_window_to_position(x, y, width, height):
                print(f"✅ CS:GO перемещен на позицию ({x}, {y})")
            else:
                print("⚠️ Не удалось переместить CS:GO")
            print("🔍 ОТЛАДКА: move_csgo_window_to_position завершен")
            
            # 10. Переименовываем окно CS:GO с добавлением логина аккаунта
            print(f"🏷️ Переименовываю окно CS:GO для аккаунта {login}...")
            print("🔍 ОТЛАДКА: Начинаю rename_csgo_window...")
            if self.rename_csgo_window(login):
                print(f"✅ Окно CS:GO успешно переименовано для {login}")
            else:
                print(f"⚠️ Не удалось переименовать окно CS:GO для {login}")
            print("🔍 ОТЛАДКА: rename_csgo_window завершен")
            
            print(f"🎉 Аккаунт {login} успешно запущен!")
            print("🔍 ОТЛАДКА: launch_single_account завершается с True")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при запуске аккаунта {login}: {e}")
            print(f"🔍 ОТЛАДКА: Исключение в launch_single_account: {e}")
            return False
    
    def wait_for_steam_window(self):
        """Ждет появления окна Steam."""
        max_wait = 30
        for i in range(max_wait):
            windows = pyautogui.getWindowsWithTitle('Steam')
            if windows:
                window = windows[0]
                try:
                    window.activate()
                except:
                    pass
                time.sleep(1)
                return True
            time.sleep(1)
        return False
    
    def detect_screen_type_and_handle(self):
        """Определяет тип экрана Steam."""
        try:
            steam_windows = pyautogui.getWindowsWithTitle('Steam')
            if not steam_windows:
                return False, None
                
            window = steam_windows[0]
            
            # Если окно свернуто, разворачиваем
            if window.left == -32000:
                try:
                    window.restore()
                    time.sleep(2)
                except:
                    pass
            
            # Ищем кнопку "+"
            center_x = window.left + window.width // 2
            center_y = window.top + window.height // 2
            
            search_start_x = center_x + 100
            search_end_x = window.left + window.width - 50
            search_start_y = center_y - 50
            search_end_y = center_y + 100
            
            plus_found = False
            plus_x, plus_y = 0, 0
            
            for y in range(search_start_y, search_end_y, 5):
                for x in range(search_start_x, search_end_x, 5):
                    try:
                        center_pixel = pyautogui.pixel(x, y)
                        if center_pixel[0] > 200 and center_pixel[1] > 200 and center_pixel[2] > 200:
                            cross_pixels = 0
                            for dx in [-10, -5, 5, 10]:
                                try:
                                    h_pixel = pyautogui.pixel(x + dx, y)
                                    if h_pixel[0] > 180 and h_pixel[1] > 180 and h_pixel[2] > 180:
                                        cross_pixels += 1
                                except:
                                    pass
                            
                            for dy in [-10, -5, 5, 10]:
                                try:
                                    v_pixel = pyautogui.pixel(x, y + dy)
                                    if v_pixel[0] > 180 and v_pixel[1] > 180 and v_pixel[2] > 180:
                                        cross_pixels += 1
                                except:
                                    pass
                            
                            if cross_pixels >= 4:
                                plus_x, plus_y = x, y
                                plus_found = True
                                break
                    except:
                        continue
                if plus_found:
                    break
            
            if plus_found:
                print("📱 Найдена кнопка '+', кликаю...")
                pyautogui.click(plus_x, plus_y)
                time.sleep(3)
                return True, "profile_selection"
            else:
                return True, "login_screen"
                
        except Exception as e:
            print(f"❌ Ошибка определения экрана: {e}")
            return False, None
    
    def get_totp_remaining_time(self):
        """Возвращает количество секунд до смены TOTP кода."""
        import time
        current_time = int(time.time())
        time_step = 30  # TOTP коды меняются каждые 30 секунд
        remaining = time_step - (current_time % time_step)
        return remaining
    
    def auto_login_by_coordinates(self, login, password, shared_secret):
        """Выполняет автологин."""
        try:
            steam_windows = pyautogui.getWindowsWithTitle('Steam')
            if not steam_windows:
                return False
                
            window = steam_windows[0]
            
            # Координаты полей
            login_field_x = window.left + 215
            login_field_y = window.top + 145
            password_field_x = window.left + 215
            password_field_y = window.top + 215
            sign_in_button_x = window.left + 233
            sign_in_button_y = window.top + 305
            
            # Вводим логин
            pyautogui.click(login_field_x, login_field_y)
            time.sleep(1.5)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(1.0)
            pyautogui.typewrite(login, interval=0.08)
            time.sleep(2.0)
            
            # Вводим пароль
            pyautogui.click(password_field_x, password_field_y)
            time.sleep(2.0)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(1.5)
            pyautogui.typewrite(password, interval=0.1)
            time.sleep(2.5)
            print("a")
            # Нажимаем кнопку входа
            pyautogui.click(sign_in_button_x, sign_in_button_y)
            print("b")
            # Ждем 2FA экран
            time.sleep(8)
            
            # ПРОВЕРЯЕМ ТИП 2FA ЭКРАНА ЧЕРЕЗ OpenCV
            print("🔍 Определяю тип 2FA экрана...")
            
            # Делаем скриншот всего экрана
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)
            
            # Путь к шаблону
            template_path = r"E:\sandbox\2fa_field.png"
            
            code_field_detected = False
            
            # Проверяем шаблон
            if os.path.exists(template_path):
                try:
                    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                    result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    print(f"🔍 Точность совпадения: {max_val:.2f}")
                    
                    if max_val >= 0.75:
                        code_field_detected = True
                        print("✅ Поле ввода найдено - ввожу код сразу")
                    else:
                        print("❌ Поле ввода не найдено")
                        
                except Exception as e:
                    print(f"⚠️ Ошибка проверки шаблона: {e}")
            else:
                print(f"⚠️ Шаблон не найден: {template_path}")
            
            # Если поле НЕ найдено, нажимаем "Enter a code instead"
            if not code_field_detected:
                print("🔄 Нажимаю 'Enter a code instead'...")
                enter_code_instead_x = window.left + 352
                enter_code_instead_y = window.top + 319
                pyautogui.click(enter_code_instead_x, enter_code_instead_y)
                time.sleep(15)
                print("✅ Переключился на ввод кода")
            
            # Генерируем и вводим 2FA код
            remaining_time = self.get_totp_remaining_time()
            print(f"⏱️ Оставшееся время до смены кода: {remaining_time} сек.")
            
            # Если осталось меньше 5 секунд, ждем нового кода
            if remaining_time < 5:
                wait_time = remaining_time + 1  # +1 чтобы гарантированно попасть в новое окно
                print(f"⏳ Слишком мало времени ({remaining_time} сек), жду {wait_time} сек до нового кода...")
                time.sleep(wait_time)
                remaining_time = self.get_totp_remaining_time()
                print(f"✅ Новое временное окно! Осталось {remaining_time} сек.")
            
            auth_code = generate_twofactor_code_for_time(shared_secret)
            print(f"🔐 Код: {auth_code} (действителен еще {remaining_time} сек.)")
            
            pyautogui.typewrite(auth_code, interval=0.1)
            time.sleep(1.0)
            pyautogui.press('enter')
            
            # Ждем загрузки Steam
            time.sleep(25)
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка автологина: {e}")
            return False
    
    def launch_csgo(self, width, height):
        """Запускает CS:GO через OpenCV поиск элементов Steam интерфейса."""
        try:
            print("🔍 ОТЛАДКА: Запуск CS:GO через OpenCV...")
            
            # Находим активный Steam процесс
            steam_windows = pyautogui.getWindowsWithTitle('Steam')
            if not steam_windows:
                print("❌ ОТЛАДКА: Активный Steam не найден")
                return False
            
            steam_window = steam_windows[0]
            steam_window.activate()
            time.sleep(2)
            print("🔍 ОТЛАДКА: Steam активирован")
            
            # Шаг 1: Ищем и кликаем на LIBRARY
            print("🔍 ОТЛАДКА: Ищу кнопку LIBRARY...")
            library_pos = self.find_steam_element_cv(r"E:\sandbox\library.png", confidence=0.7)
            if not library_pos:
                print("❌ ОТЛАДКА: Кнопка LIBRARY не найдена")
                return False
            
            pyautogui.click(library_pos[0], library_pos[1])
            time.sleep(3)
            print("✅ ОТЛАДКА: Кликнул на LIBRARY")
            
            # Шаг 2: Ищем и кликаем на поиск
            print("🔍 ОТЛАДКА: Ищу поле поиска...")
            search_pos = self.find_steam_element_cv(r"E:\sandbox\search.png", confidence=0.7)
            if not search_pos:
                print("❌ ОТЛАДКА: Поле поиска не найдено")
                return False
            
            pyautogui.click(search_pos[0], search_pos[1])
            time.sleep(2)
            print("✅ ОТЛАДКА: Кликнул на поиск")
            
            # Шаг 3: Вводим Counter-Strike 2
            print("🔍 ОТЛАДКА: Ввожу Counter-Strike 2...")
            pyautogui.typewrite('Counter-Strike 2', interval=0.1)
            time.sleep(3)
            print("✅ ОТЛАДКА: Текст введен")
            
            # Шаг 4: Ищем результат поиска Counter-Strike
            print("🔍 ОТЛАДКА: Ищу результат поиска...")
            counter_pos = self.find_steam_element_cv(r"E:\sandbox\counter.png", confidence=0.7)
            
                
                
            if counter_pos:
                pyautogui.click(counter_pos[0], counter_pos[1])
                time.sleep(4)
                print("✅ ОТЛАДКА: Кликнул на Counter-Strike")
                            # Шаг 4.5: Пытаемся открыть настройки

                print("🔍 ОТЛАДКА: Ищу кнопку SETTINGS...")
                settings_pos = self.find_steam_element_cv(r"E:\sandbox\settings.png", confidence=0.7)

                if settings_pos:
                    print("✅ SETTINGS найден, кликаю...")
                    pyautogui.click(settings_pos[0], settings_pos[1])
                    time.sleep(2)
                    
                    # Ищем Properties
                    print("🔍 ОТЛАДКА: Ищу PROPERTIES...")
                    properties_pos = self.find_steam_element_cv(r"E:\sandbox\properties.png", confidence=0.7)
                    if properties_pos:
                        pyautogui.click(properties_pos[0], properties_pos[1])
                        time.sleep(2)
                        print("✅ Кликнул на PROPERTIES")
                        
                        # Ищем General

                        print("🔍 ОТЛАДКА: Ищу GENERAL...")
                        general_pos = self.find_steam_element_cv(r"E:\sandbox\general.png", confidence=0.7)
                        
                        if general_pos:
                            pyautogui.click(general_pos[0], general_pos[1])
                            time.sleep(1)
                            print("✅ Кликнул на GENERAL")
                            
                            # Нажимаем 4 раза Tab, затем Backspace
                            print("🔍 ОТЛАДКА: Нажимаю Tab 4 раза...")
                            for i in range(4):
                                pyautogui.press('tab')
                                time.sleep(0.3)
                            
                            print("🔍 ОТЛАДКА: Нажимаю Backspace...")
                            pyautogui.press('backspace')
                            time.sleep(0.5)
                            print("✅ Выполнены навигационные нажатия")
                            
                            # Ищем input поле
                            print("🔍 ОТЛАДКА: Ищу INPUT...")
                            input_pos = self.find_steam_element_cv(r"E:\sandbox\input.png", confidence=0.7)
                            
                            if input_pos:
                                pyautogui.click(input_pos[0], input_pos[1])
                                time.sleep(1)
                                pyautogui.hotkey('ctrl', 'a')
                                time.sleep(0.5)
                                launch_params = f"-sw -w {width} -h {height} +fps_max 60 -nosound +volume 0 +snd_mute_losefocus 0 +snd_musicvolume 0 +voice_enable 0"
                                
                                pyautogui.typewrite(launch_params, interval=0.05)
                                print(f"✅ Ввел параметры: {launch_params}")
                                time.sleep(1)

                                # Закрываем окно Properties через Alt+F4
                                print("🔍 ОТЛАДКА: Закрываю Properties через Alt+F4...")
                                pyautogui.hotkey('alt', 'F4')
                                time.sleep(1)
                                print("✅ Закрыл окно Properties")
                            else:
                                print("⚠️ INPUT не найден")
                        else:
                            print("⚠️ GENERAL не найден")
                    else:
                        print("⚠️ PROPERTIES не найден")
                else:
                    print("⚠️ SETTINGS не найден, пропускаю")
                print("🔍 ОТЛАДКА: Ищу кнопку PLAY...")
                play_pos = self.find_steam_element_cv(r"E:\sandbox\play.png", confidence=0.7)

                if not play_pos:
                    print("🔍 ОТЛАДКА: PLAY не найден, ищу UPDATE...")
                    update_pos = self.find_steam_element_cv(r"E:\sandbox\update.png", confidence=0.7)
                    
                    if not update_pos:
                        print("🔍 ОТЛАДКА: UPDATE не найден, ищу small_play...")
                        small_play_pos = self.find_steam_element_cv(r"E:\sandbox\small_play.png", confidence=0.77)
                        
                        if not small_play_pos:
                            print("🔍 ОТЛАДКА: small_play не найден, ищу small_update...")
                            small_update_pos = self.find_steam_element_cv(r"E:\sandbox\small_update.png", confidence=0.7)
                            
                            if not small_update_pos:
                                print("❌ ОТЛАДКА: Ничего не найдено")
                                return False
                            
                            pyautogui.click(small_update_pos[0], small_update_pos[1])
                            time.sleep(7)
                            print("✅ ОТЛАДКА: Кликнул на small_update, жду...")
                            
                            small_play_pos = self.find_steam_element_cv(r"E:\sandbox\small_play.png", confidence=0.7)
                            if not small_play_pos:
                                print("❌ ОТЛАДКА: small_play не найден после small_update")
                                return False
                            
                            pyautogui.click(small_play_pos[0], small_play_pos[1])
                            time.sleep(2)
                            print("✅ ОТЛАДКА: Кликнул на small_play - CS:GO запускается!")
                        else:
                            pyautogui.click(small_play_pos[0], small_play_pos[1])
                            time.sleep(2)
                            print("✅ ОТЛАДКА: Кликнул на small_play - CS:GO запускается!")
                    else:
                        pyautogui.click(update_pos[0], update_pos[1])
                        time.sleep(10)
                        print("✅ ОТЛАДКА: Кликнул на UPDATE, жду...")
                        
                        play_pos = self.find_steam_element_cv(r"E:\sandbox\play.png", confidence=0.7)
                        if not play_pos:
                            print("⚠️ ОТЛАДКА: PLAY не найден после первого ожидания, жду еще 10 секунд...")
                            time.sleep(30)
                            play_pos = self.find_steam_element_cv(r"E:\sandbox\play.png", confidence=0.7)
                            
                            if not play_pos:
                                print("❌ ОТЛАДКА: PLAY не найден после UPDATE даже после дополнительного ожидания")
                                return False
                            pyautogui.click(play_pos[0], play_pos[1])
                            time.sleep(2)
                            print("✅ ОТЛАДКА: Кликнул на PLAY - CS:GO запускается!")
                        
                        pyautogui.click(play_pos[0], play_pos[1])
                        time.sleep(2)
                        print("✅ ОТЛАДКА: Кликнул на PLAY - CS:GO запускается!")
                else:
                    pyautogui.click(play_pos[0], play_pos[1])
                    time.sleep(2)
                    print("✅ ОТЛАДКА: Кликнул на PLAY - CS:GO запускается!")
            else:
                # counter.png не найден, проверяем update_queued_counter.png
                print("🔍 ОТЛАДКА: counter.png не найден, ищу update_queued_counter.png...")
                update_queued_pos = self.find_steam_element_cv(r"E:\sandbox\update_queued_counter.png", confidence=0.7)
                
                if not update_queued_pos:
                    print("❌ ОТЛАДКА: update_queued_counter.png тоже не найден")
                    
                    # Проверяем error_counter.png
                    print("🔍 ОТЛАДКА: Ищу error_counter.png...")
                    error_counter_pos = self.find_steam_element_cv(r"E:\sandbox\error_counter.png", confidence=0.7)
                    
                    if not error_counter_pos:
                        print("❌ ОТЛАДКА: error_counter.png тоже не найден")
                        return False
                    
                    # Кликаем на error_counter.png
                    pyautogui.click(error_counter_pos[0], error_counter_pos[1])
                    time.sleep(4)
                    print("✅ ОТЛАДКА: Кликнул на error_counter")
                else:
                    # Кликаем на update_queued_counter.png
                    pyautogui.click(update_queued_pos[0], update_queued_pos[1])
                    time.sleep(4)
                    print("✅ ОТЛАДКА: Кликнул на update_queued_counter")
                # СЮДА
# Шаг 4.5: Пытаемся открыть настройки
                print("🔍 ОТЛАДКА: Ищу кнопку SETTINGS...")
                settings_pos = self.find_steam_element_cv(r"E:\sandbox\settings.png", confidence=0.7)
                
                if settings_pos:
                    print("✅ SETTINGS найден, кликаю...")
                    pyautogui.click(settings_pos[0], settings_pos[1])
                    time.sleep(2)
                    
                    # Ищем Properties
                    print("🔍 ОТЛАДКА: Ищу PROPERTIES...")
                    properties_pos = self.find_steam_element_cv(r"E:\sandbox\properties.png", confidence=0.7)
                    if properties_pos:
                        pyautogui.click(properties_pos[0], properties_pos[1])
                        time.sleep(2)
                        print("✅ Кликнул на PROPERTIES")
                        
                        # Ищем General
                        print("🔍 ОТЛАДКА: Ищу GENERAL...")
                        general_pos = self.find_steam_element_cv(r"E:\sandbox\general.png", confidence=0.7)
                        
                        if general_pos:
                            pyautogui.click(general_pos[0], general_pos[1])
                            time.sleep(1)
                            print("✅ Кликнул на GENERAL")
                            
                            # Нажимаем 4 раза Tab, затем Backspace
                            print("🔍 ОТЛАДКА: Нажимаю Tab 4 раза...")
                            for i in range(4):
                                pyautogui.press('tab')
                                time.sleep(0.3)
                            
                            print("🔍 ОТЛАДКА: Нажимаю Backspace...")
                            pyautogui.press('backspace')
                            time.sleep(0.5)
                            print("✅ Выполнены навигационные нажатия")
                            
                            # Ищем input поле
                            print("🔍 ОТЛАДКА: Ищу INPUT...")
                            input_pos = self.find_steam_element_cv(r"E:\sandbox\input.png", confidence=0.7)
                            
                            if input_pos:
                                pyautogui.click(input_pos[0], input_pos[1])
                                time.sleep(1)
                                pyautogui.hotkey('ctrl', 'a')
                                time.sleep(0.5)
                                launch_params = f"-sw -w {width} -h {height} +fps_max 60 -nosound +volume 0 +snd_mute_losefocus 0 +snd_musicvolume 0 +voice_enable 0"
                                
                                pyautogui.typewrite(launch_params, interval=0.05)
                                print(f"✅ Ввел параметры: {launch_params}")
                                time.sleep(1)
                                
                                # Закрываем окно Properties через Alt+F4
                                print("🔍 ОТЛАДКА: Закрываю Properties через Alt+F4...")
                                pyautogui.hotkey('alt', 'F4')
                                time.sleep(1)
                                print("✅ Закрыл окно Properties")
                            else:
                                print("⚠️ INPUT не найден")
                        else:
                            print("⚠️ GENERAL не найден")
                    else:
                        print("⚠️ PROPERTIES не найден")
                else:
                    print("⚠️ SETTINGS не найден, пропускаю")
                # Ищем и кликаем на update.png
               
                print("🔍 ОТЛАДКА: Ищу кнопку UPDATE...")
                update_pos = self.find_steam_element_cv(r"E:\sandbox\update.png", confidence=0.7)
                
                if not update_pos:
                    print("🔍 ОТЛАДКА: UPDATE не найден, ищу small_update...")
                    small_update_pos = self.find_steam_element_cv(r"E:\sandbox\small_update.png", confidence=0.7)
                    
                    if not small_update_pos:
                        print("❌ ОТЛАДКА: Ни UPDATE, ни small_update не найдены")
                        return False
                    
                    pyautogui.click(small_update_pos[0], small_update_pos[1])
                    time.sleep(7)
                    print("✅ ОТЛАДКА: Кликнул на small_update, жду...")
                else:
                    pyautogui.click(update_pos[0], update_pos[1])
                    time.sleep(7)
                    print("✅ ОТЛАДКА: Кликнул на UPDATE, жду...")
                
                print("✅ ОТЛАДКА: Кликнул на UPDATE, жду завершения...")
                
                # Теперь ищем кнопку PLAY
                # Теперь ищем кнопку PLAY
                print("🔍 ОТЛАДКА: Ищу кнопку PLAY после обновления...")
                play_pos = self.find_steam_element_cv(r"E:\sandbox\play.png", confidence=0.7)
                
                if not play_pos:
                    print("🔍 ОТЛАДКА: PLAY не найден, ищу small_play...")
                    small_play_pos = self.find_steam_element_cv(r"E:\sandbox\small_play.png", confidence=0.7)
                    
                    if not small_play_pos:
                        print("❌ ОТЛАДКА: Ни PLAY, ни small_play не найдены после обновления")
                        return False
                    
                    pyautogui.click(small_play_pos[0], small_play_pos[1])
                    time.sleep(2)
                    print("✅ ОТЛАДКА: Кликнул на small_play после обновления - CS:GO запускается!")
                else:
                    pyautogui.click(play_pos[0], play_pos[1])
                    time.sleep(2)
                    print("✅ ОТЛАДКА: Кликнул на PLAY после обновления - CS:GO запускается!")
            
            # Проверка play_anyway.png после нажатия PLAY
            print("⏳ Жду 5 секунд для проверки play_anyway.png...")
            time.sleep(5)
            
            print("🔍 ОТЛАДКА: Проверяю наличие play_anyway.png...")
            play_anyway_pos = self.find_steam_element_cv(r"E:\sandbox\play_anyway.png", confidence=0.7)
            
            if play_anyway_pos:
                print("✅ ОТЛАДКА: play_anyway.png найден, кликаю...")
                pyautogui.click(play_anyway_pos[0], play_anyway_pos[1])
                time.sleep(2)
                print("✅ ОТЛАДКА: Кликнул на play_anyway.png")
            else:
                print("ℹ️ ОТЛАДКА: play_anyway.png не найден, продолжаю без действий")
            
            # Проверка local.png после нажатия PLAY
            print("⏳ Жду 5 секунд для проверки local.png...")
            time.sleep(5)
            
            print("🔍 ОТЛАДКА: Проверяю наличие local.png...")
            local_pos = self.find_steam_element_cv(r"E:\sandbox\local.png", confidence=0.7)
            
            if local_pos:
                print("✅ ОТЛАДКА: local.png найден, кликаю...")
                pyautogui.click(local_pos[0], local_pos[1])
                time.sleep(5)
                
                print("🔍 ОТЛАДКА: Ищу continue.png...")
                continue_pos = self.find_steam_element_cv(r"E:\sandbox\continue.png", confidence=0.7)
                
                if continue_pos:
                    print("✅ ОТЛАДКА: continue.png найден, кликаю...")
                    pyautogui.click(continue_pos[0], continue_pos[1])
                    time.sleep(2)
                    print("✅ ОТЛАДКА: Кликнул на continue.png")
                else:
                    print("⚠️ ОТЛАДКА: continue.png не найден")
            else:
                print("ℹ️ ОТЛАДКА: local.png не найден, продолжаю без действий")
            
            return True
            
        except Exception as e:
            print(f"❌ ОТЛАДКА: Ошибка OpenCV запуска CS:GO: {e}")
            return False
    
    def move_csgo_window_to_position(self, x, y, width, height):
        """Перемещает окно CS:GO в указанную позицию."""
        max_attempts = 30
        
        for attempt in range(max_attempts):
            try:
                # Получаем все окна, которые могут быть CS:GO (включая переименованные)
                all_windows = pyautogui.getAllWindows()
                
                csgo_window = None
                for window in all_windows:
                    # Проверяем, содержит ли название окна ключевые слова CS:GO
                    if any(keyword in window.title for keyword in ['Counter-Strike 2', 'Counter-Strike: Global Offensive', 'CS:GO', 'CS2']):
                        csgo_window = window
                        break
                
                if csgo_window:
                    try:
                        csgo_window.moveTo(x, y)
                        csgo_window.resizeTo(width, height)
                        return True
                    except Exception as e:
                        # Пробуем выйти из полноэкранного режима
                        try:
                            csgo_window.activate()
                            time.sleep(1)
                            pyautogui.keyDown('alt')
                            pyautogui.press('enter')
                            pyautogui.keyUp('alt')
                            time.sleep(2)
                            csgo_window.moveTo(x, y)
                            csgo_window.resizeTo(width, height)
                            return True
                        except:
                            return False
                
                time.sleep(2)
                
            except Exception as e:
                time.sleep(2)
        
        return False
    
    def shuffle_lobbies(self):
        """Случайно перемешивает позиции всех запущенных окон CS:GO."""
        try:
            print("\n" + "="*60)
            print("🔀 SHUFFLE LOBBIES - Перемешивание окон CS:GO")
            print("="*60)
            
            # Находим все окна CS:GO
            def enum_windows_callback(hwnd, windows_list):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    windows_list.append((hwnd, window_title))
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            # Фильтруем только окна CS:GO (с логинами аккаунтов)
            csgo_windows = []
            csgo_keywords = ['Counter-Strike 2', 'Counter-Strike: Global Offensive', 'CS:GO', 'CS2']
            
            for hwnd, title in windows:
                if any(keyword in title for keyword in csgo_keywords):
                    try:
                        # Получаем текущую позицию окна
                        rect = win32gui.GetWindowRect(hwnd)
                        x, y, right, bottom = rect
                        width = right - x
                        height = bottom - y
                        
                        csgo_windows.append({
                            'hwnd': hwnd,
                            'title': title,
                            'x': x,
                            'y': y,
                            'width': width,
                            'height': height
                        })
                        print(f"✅ Найдено окно: {title} at ({x}, {y})")
                    except Exception as e:
                        print(f"⚠️ Ошибка получения позиции окна {title}: {e}")
            
            if len(csgo_windows) < 2:
                messagebox.showinfo("Информация", 
                                  f"Найдено {len(csgo_windows)} окон CS:GO.\n"
                                  "Для перемешивания нужно минимум 2 окна!")
                print("⚠️ Недостаточно окон для перемешивания")
                return
            
            # Собираем все позиции (x, y, width, height)
            positions = [(w['x'], w['y'], w['width'], w['height']) for w in csgo_windows]
            
            # Перемешиваем позиции случайным образом
            # Гарантируем что порядок изменится (не останется тем же)
            shuffled_positions = positions.copy()
            max_shuffle_attempts = 10
            
            for attempt in range(max_shuffle_attempts):
                random.shuffle(shuffled_positions)
                # Проверяем что хотя бы одна позиция изменилась
                if shuffled_positions != positions:
                    break
                print(f"🔄 Попытка {attempt+1}: позиции совпали, перемешиваю еще раз...")
            
            print(f"\n🎲 Перемешивание {len(csgo_windows)} окон...")
            
            # Перемещаем каждое окно на новую позицию
            for i, window in enumerate(csgo_windows):
                new_x, new_y, new_width, new_height = shuffled_positions[i]
                
                try:
                    # Перемещаем окно
                    win32gui.SetWindowPos(
                        window['hwnd'],
                        win32con.HWND_TOP,
                        new_x, new_y,
                        new_width, new_height,
                        win32con.SWP_SHOWWINDOW
                    )
                    print(f"✅ {window['title']}: ({window['x']}, {window['y']}) → ({new_x}, {new_y})")
                except Exception as e:
                    print(f"❌ Ошибка перемещения {window['title']}: {e}")
            
            print("="*60)
            print("✅ Перемешивание завершено!")
            print("="*60 + "\n")
            
            messagebox.showinfo("Успех", 
                              f"✅ Перемешано {len(csgo_windows)} окон CS:GO!\n\n"
                              "Окна перемещены на случайные позиции.")
            
        except Exception as e:
            error_msg = f"Ошибка при перемешивании окон: {e}"
            print(f"❌ {error_msg}")
            messagebox.showerror("Ошибка", error_msg)
    
    def rename_csgo_window(self, account_login):
        """Переименовывает окно CS:GO, добавляя логин аккаунта."""
        max_attempts = 20
        
        for attempt in range(max_attempts):
            try:
                def enum_windows_callback(hwnd, windows_list):
                    """Callback функция для перебора всех окон."""
                    if win32gui.IsWindowVisible(hwnd):
                        window_title = win32gui.GetWindowText(hwnd)
                        windows_list.append((hwnd, window_title))
                
                # Собираем все видимые окна
                windows = []
                win32gui.EnumWindows(enum_windows_callback, windows)
                
                # Ищем окна CS:GO
                csgo_titles = [
                    'Counter-Strike 2',
                    'Counter-Strike: Global Offensive',
                    'CS:GO',
                    'CS2'
                ]
                
                for hwnd, title in windows:
                    # Проверяем, является ли это окном CS:GO без добавленного логина
                    if any(csgo_title in title for csgo_title in csgo_titles):
                        # Проверяем, не добавлен ли уже логин (чтобы не переименовывать дважды)
                        if f" - {account_login}" not in title:
                            # Создаем новое название с логином
                            new_title = f"{title} - {account_login}"
                            
                            # Переименовываем окно
                            win32gui.SetWindowText(hwnd, new_title)
                            print(f"✅ Окно CS:GO переименовано: '{new_title}'")
                            return True
                
                # Если не нашли, ждем и повторяем попытку
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ Попытка {attempt + 1}/{max_attempts} переименования окна: {e}")
                time.sleep(2)
        
        print(f"❌ Не удалось переименовать окно CS:GO для аккаунта {account_login}")
        return False
    
    def close_steam_keep_csgo(self):
        """Сворачивает окна Steam и Special Offers, не закрывая процессы."""
        try:
            # Сворачиваем основное окно Steam
            steam_windows = pyautogui.getWindowsWithTitle('Steam')
            for window in steam_windows:
                try:
                    print(f"🔍 Сворачиваю окно Steam: {window.title}")
                    window.minimize()
                    print("✅ Окно Steam свернуто")
                except Exception as e:
                    print(f"⚠️ Не удалось свернуть окно Steam: {e}")
            
            # Сворачиваем окно Special Offers
            time.sleep(0.5)  # Небольшая пауза
            special_offers_windows = pyautogui.getWindowsWithTitle('Special Offers')
            for window in special_offers_windows:
                try:
                    print(f"🔍 Сворачиваю окно Special Offers: {window.title}")
                    window.minimize()
                    print("✅ Окно Special Offers свернуто")
                except Exception as e:
                    print(f"⚠️ Не удалось свернуть окно Special Offers: {e}")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка при сворачивании окон: {e}")
            return False
    
    def run(self):
        """Запускает GUI."""
        # Сохраняем цвета при закрытии приложения
        def on_closing():
            self.save_colors()
            self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()

def main():
    app = SteamLauncherGUI()
    app.run()

if __name__ == "__main__":
    main()