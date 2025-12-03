import os
import time
import re
import threading
import json
from datetime import datetime

# Путь к песочнице Avast
SANDBOX_PATH = r"E:\avast! sandbox"

# Файл для записи найденных игр
MATCHES_FILE = "found_matches.json"

class CS2MatchScanner:
    def __init__(self, ignore_old=True):
        self.log_files = {}      # {session_id: path_to_console.log}
        self.found_matches = {}  # {session_id: {match_id, timestamp, accepted}}
        self.lock = threading.Lock()
        self.session_counter = 0
        self.ignore_old = ignore_old
        self.start_time = time.time()
        self.callbacks = []  # Колбэки при нахождении общего матча
        
    def on_common_match(self, callback):
        """Регистрирует колбэк который вызывается когда найден общий матч"""
        self.callbacks.append(callback)
    
    def find_console_logs(self):
        """Ищет console.log файлы в песочнице Avast"""
        if not os.path.exists(SANDBOX_PATH):
            return
        
        for root, dirs, files in os.walk(SANDBOX_PATH):
            if "console.log" in files and "csgo" in root:
                log_path = os.path.join(root, "console.log")
                
                if log_path in [v for v in self.log_files.values()]:
                    continue
                
                try:
                    file_mtime = os.path.getmtime(log_path)
                    file_age = time.time() - file_mtime
                    
                    if file_age > 3600:
                        continue
                    
                    if self.ignore_old and file_mtime < self.start_time:
                        continue
                    
                    # Извлекаем GUID
                    guid_match = re.search(r'steam\.exe_\{([^}]+)\}', log_path)
                    if guid_match:
                        guid = guid_match.group(1)[:8]
                    else:
                        self.session_counter += 1
                        guid = f"s{self.session_counter}"
                    
                    session_id = f"ACC_{guid}"
                    
                    if session_id not in self.log_files:
                        print(f"✅ Найден лог [{session_id}]")
                        self.log_files[session_id] = log_path
                        
                        self.scan_existing_log(session_id, log_path)
                        
                        t = threading.Thread(target=self.monitor_log, args=(session_id, log_path), daemon=True)
                        t.start()
                        
                except Exception as e:
                    pass

    def scan_existing_log(self, session_id, log_path):
        """Сканирует существующий лог"""
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            matches = re.findall(r'match_id=(\d+)', content)
            if matches:
                match_id = matches[-1]
                print(f"📜 [{session_id}] В логе есть match_id: {match_id}")
                self.on_match_found(session_id, match_id)
        except:
            pass

    def monitor_log(self, session_id, log_path):
        """Следит за логом в реальном времени"""
        print(f"👁️ Мониторинг [{session_id}]...")
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, os.SEEK_END)
                
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.05)  # Быстрее реагируем
                        continue
                    
                    match = re.search(r'match_id=(\d+)', line)
                    if match:
                        self.on_match_found(session_id, match.group(1))
                    
        except Exception as e:
            print(f"❌ Ошибка [{session_id}]: {e}")
            with self.lock:
                if session_id in self.log_files:
                    del self.log_files[session_id]

    def on_match_found(self, session_id, match_id):
        """Вызывается когда найден матч"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        with self.lock:
            existing = self.found_matches.get(session_id, {})
            if existing.get("match_id") == match_id:
                return
            
            self.found_matches[session_id] = {
                "match_id": match_id,
                "timestamp": timestamp,
                "accepted": False
            }
            self.save_matches()
        
        print(f"\n{'🔥'*10}")
        print(f"⚠️ [{session_id}] МАТЧ: {match_id}")
        print(f"{'🔥'*10}\n")
        
        self.check_common_match(match_id)

    def check_common_match(self, match_id):
        """Проверяет есть ли общий матч между аккаунтами"""
        with self.lock:
            same = [sid for sid, d in self.found_matches.items() 
                   if d.get("match_id") == match_id and not d.get("accepted")]
        
        if len(same) >= 2:
            print(f"\n{'⭐'*20}")
            print(f"🎯 ОБЩИЙ МАТЧ НАЙДЕН!")
            print(f"   Match ID: {match_id}")
            print(f"   Сессии: {', '.join(same)}")
            print(f"{'⭐'*20}\n")
            
            # Вызываем колбэки
            for callback in self.callbacks:
                try:
                    callback(match_id, same)
                except Exception as e:
                    print(f"Ошибка колбэка: {e}")
            
            return same
        return []

    def mark_accepted(self, session_id):
        """Помечает что матч принят для сессии"""
        with self.lock:
            if session_id in self.found_matches:
                self.found_matches[session_id]["accepted"] = True
                self.save_matches()

    def clear_matches(self):
        """Очищает все найденные матчи"""
        with self.lock:
            self.found_matches = {}
            self.save_matches()
        print("🧹 Матчи очищены")

    def get_sessions_with_match(self, match_id):
        """Возвращает список сессий с указанным match_id"""
        with self.lock:
            return [sid for sid, d in self.found_matches.items() 
                   if d.get("match_id") == match_id]

    def save_matches(self):
        try:
            with open(MATCHES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.found_matches, f, indent=2, ensure_ascii=False)
        except:
            pass

    def print_status(self):
        print(f"\n📊 Логов: {len(self.log_files)} | Матчей: {len(self.found_matches)}")
        for sid, data in self.found_matches.items():
            status = "✅" if data.get("accepted") else "⏳"
            print(f"   {status} {sid}: {data.get('match_id', '?')}")
        print()


# Глобальный экземпляр сканера
_scanner = None

def get_scanner():
    """Возвращает глобальный экземпляр сканера"""
    global _scanner
    if _scanner is None:
        _scanner = CS2MatchScanner(ignore_old=True)
    return _scanner

def start_scanner():
    """Запускает сканер в фоновом режиме"""
    scanner = get_scanner()
    
    def scan_loop():
        while True:
            scanner.find_console_logs()
            time.sleep(3)
    
    t = threading.Thread(target=scan_loop, daemon=True)
    t.start()
    print("🚀 Сканер запущен в фоне")
    return scanner


def main():
    print("="*50)
    print("CS2 Match Scanner для Avast Sandbox")
    print("="*50)
    print(f"Путь: {SANDBOX_PATH}")
    print("Ожидаю новые запуски CS2...")
    print("="*50 + "\n")
    
    scanner = CS2MatchScanner(ignore_old=True)
    
    # Пример колбэка при нахождении общего матча
    def on_common(match_id, sessions):
        print(f">>> КОЛБЭК: Нужно принять матч {match_id} для {sessions}")
    
    scanner.on_common_match(on_common)
    
    last_status = 0
    
    while True:
        scanner.find_console_logs()
        
        if time.time() - last_status > 30:
            scanner.print_status()
            last_status = time.time()
        
        time.sleep(3)


if __name__ == "__main__":
    main()
