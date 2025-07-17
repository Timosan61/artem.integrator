import streamlit as st
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.config import INSTRUCTION_FILE, DEFAULT_INSTRUCTION, STREAMLIT_CONFIG
from admin.auth import check_password
from admin.deploy_integration import DeployManager, show_deploy_status


def load_instruction():
    try:
        with open(INSTRUCTION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        default_data = DEFAULT_INSTRUCTION.copy()
        default_data["last_updated"] = datetime.now().isoformat()
        return default_data


def save_instruction(instruction_data):
    try:
        # Валидация данных
        if not isinstance(instruction_data, dict):
            raise ValueError("Данные должны быть словарем")
        
        required_fields = ['system_instruction', 'welcome_message']
        for field in required_fields:
            if field not in instruction_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
            if not isinstance(instruction_data[field], str):
                raise ValueError(f"Поле {field} должно быть строкой")
        
        # Проверка длины полей
        if len(instruction_data['system_instruction']) < 10:
            raise ValueError("Системная инструкция слишком короткая (минимум 10 символов)")
        if len(instruction_data['welcome_message']) < 5:
            raise ValueError("Приветственное сообщение слишком короткое (минимум 5 символов)")
        
        instruction_data["last_updated"] = datetime.now().isoformat()
        
        # Проверяем, что JSON валидный
        json_str = json.dumps(instruction_data, ensure_ascii=False, indent=2)
        json.loads(json_str)  # Проверяем, что можно десериализовать
        
        with open(INSTRUCTION_FILE, 'w', encoding='utf-8') as f:
            f.write(json_str)
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")
        return False


def main():
    st.set_page_config(
        page_title=STREAMLIT_CONFIG['page_title'],
        page_icon=STREAMLIT_CONFIG['page_icon'],
        layout=STREAMLIT_CONFIG['layout']
    )
    
    # Проверка авторизации
    if not check_password():
        return
    
    # Заголовок  
    st.title("🤖 Artyom Integrator - Админ панель")
    
    # Показываем статус деплоя в боковой панели
    deploy_manager = show_deploy_status()
    
    if not os.path.exists(INSTRUCTION_FILE):
        st.warning("⚠️ Файл инструкций не найден. Создайте новые инструкции.")
    
    instruction_data = load_instruction()
    
    system_instruction = st.text_area(
        "Системная инструкция:",
        value=instruction_data.get("system_instruction", ""),
        height=400
    )
    
    welcome_message = st.text_area(
        "Приветственное сообщение:",
        value=instruction_data.get("welcome_message", ""),
        height=150
    )
    
    st.markdown("---")
    
    # Статус текущего промпта в боте
    st.subheader("📊 Статус бота")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Проверить текущий промпт", use_container_width=True):
            try:
                import requests
                response = requests.get("https://web-production-84d8.up.railway.app/debug/prompt", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "error" not in data:
                        st.success("✅ Связь с ботом установлена")
                        st.json(data)
                    else:
                        st.error(f"❌ Ошибка бота: {data['error']}")
                else:
                    st.error(f"❌ HTTP {response.status_code}")
            except Exception as e:
                st.error(f"❌ Не удается подключиться к боту: {e}")
    
    with col2:
        if st.button("🔄 Перезагрузить промпт", use_container_width=True):
            try:
                import requests
                response = requests.post("https://web-production-84d8.up.railway.app/admin/reload-prompt", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("changed"):
                        st.success(f"✅ Промпт обновлен: {data['old_updated']} → {data['new_updated']}")
                    else:
                        st.info("📝 Промпт перезагружен (без изменений)")
                else:
                    st.error(f"❌ HTTP {response.status_code}")
            except Exception as e:
                st.error(f"❌ Ошибка перезагрузки: {e}")
    
    st.markdown("---")
    
    if st.button("🚀 Сохранить", type="primary", use_container_width=True):
        new_instruction_data = {
            "system_instruction": system_instruction,
            "welcome_message": welcome_message,
            "last_updated": datetime.now().isoformat()
        }
        
        if save_instruction(new_instruction_data):
            # Автоматический деплой через GitHub API
            commit_message = f"Update bot instructions via admin panel\n\n- Modified system instruction\n- Updated welcome message\n- Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
            
            # Конвертируем данные в JSON для передачи в GitHub API
            instruction_json = json.dumps(new_instruction_data, ensure_ascii=False, indent=2)
            
            deploy_manager.auto_deploy_changes(commit_message, instruction_json)
            st.balloons()


if __name__ == "__main__":
    main()