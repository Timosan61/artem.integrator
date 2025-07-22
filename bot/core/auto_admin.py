"""
Автоматическое управление администраторами
"""

import json
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AutoAdminManager:
    """Управляет автоматическим добавлением администраторов"""
    
    def __init__(self, admin_file: str = "data/auto_admins.json"):
        """
        Инициализация менеджера
        
        Args:
            admin_file: Путь к файлу с администраторами
        """
        self.admin_file = admin_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Создает файл если не существует"""
        os.makedirs(os.path.dirname(self.admin_file), exist_ok=True)
        if not os.path.exists(self.admin_file):
            with open(self.admin_file, 'w') as f:
                json.dump({"admins": []}, f)
    
    def _load_admins(self) -> List[Dict]:
        """Загружает список администраторов"""
        try:
            with open(self.admin_file, 'r') as f:
                data = json.load(f)
                return data.get("admins", [])
        except Exception as e:
            logger.error(f"Ошибка загрузки админов: {e}")
            return []
    
    def _save_admins(self, admins: List[Dict]):
        """Сохраняет список администраторов"""
        try:
            with open(self.admin_file, 'w') as f:
                json.dump({"admins": admins}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения админов: {e}")
    
    def is_first_run(self) -> bool:
        """Проверяет, первый ли это запуск (нет админов)"""
        admins = self._load_admins()
        return len(admins) == 0
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        admins = self._load_admins()
        return any(admin["user_id"] == user_id for admin in admins)
    
    def add_admin(self, user_id: int, username: Optional[str] = None, 
                  first_name: Optional[str] = None) -> bool:
        """
        Добавляет администратора
        
        Args:
            user_id: ID пользователя
            username: Username пользователя
            first_name: Имя пользователя
            
        Returns:
            bool: True если добавлен, False если уже существует
        """
        admins = self._load_admins()
        
        # Проверяем, не существует ли уже
        if self.is_admin(user_id):
            return False
        
        # Добавляем нового админа
        admins.append({
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "added_at": os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip()
        })
        
        self._save_admins(admins)
        
        # Обновляем .env файл
        self._update_env_admins(admins)
        
        logger.info(f"Добавлен администратор: {user_id} ({username})")
        return True
    
    def remove_admin(self, user_id: int) -> bool:
        """
        Удаляет администратора
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если удален, False если не найден
        """
        admins = self._load_admins()
        initial_count = len(admins)
        
        admins = [admin for admin in admins if admin["user_id"] != user_id]
        
        if len(admins) < initial_count:
            self._save_admins(admins)
            self._update_env_admins(admins)
            logger.info(f"Удален администратор: {user_id}")
            return True
        
        return False
    
    def get_all_admins(self) -> List[Dict]:
        """Возвращает всех администраторов"""
        return self._load_admins()
    
    def _update_env_admins(self, admins: List[Dict]):
        """Обновляет список админов в .env файле"""
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            
            # Собираем ID админов
            admin_ids = [str(admin["user_id"]) for admin in admins]
            admin_ids_str = ",".join(admin_ids)
            
            # Читаем .env файл
            lines = []
            admin_line_found = False
            
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('ADMIN_TELEGRAM_IDS='):
                            lines.append(f'ADMIN_TELEGRAM_IDS={admin_ids_str}\n')
                            admin_line_found = True
                        else:
                            lines.append(line)
            
            # Если строки не было, добавляем
            if not admin_line_found and admin_ids:
                lines.append(f'\n# Auto-managed admin IDs\nADMIN_TELEGRAM_IDS={admin_ids_str}\n')
            
            # Записываем обратно
            with open(env_path, 'w') as f:
                f.writelines(lines)
                
        except Exception as e:
            logger.error(f"Ошибка обновления .env: {e}")


# Создаем глобальный экземпляр
auto_admin_manager = AutoAdminManager()