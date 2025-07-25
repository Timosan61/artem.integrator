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
                response = requests.get("https://artemintegrator-nahdj.ondigitalocean.app/debug/current-prompt", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "error" not in data:
                        st.success("✅ Промпт успешно загружен")
                        
                        # Красивое отображение информации о промпте
                        st.markdown("### 📄 Информация о промпте")
                        
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.metric("Последнее обновление", data.get("last_updated", "Неизвестно"))
                            st.metric("Системная инструкция", f"{data.get('system_instruction_length', 0)} символов")
                        
                        with col_info2:
                            st.metric("Приветственное сообщение", f"{data.get('welcome_message_length', 0)} символов")
                            st.metric("Файл существует", "✅" if data.get("exists", False) else "❌")
                        
                        # Показываем детали
                        with st.expander("🔍 Детали"):
                            st.json(data)
                    else:
                        st.error(f"❌ Ошибка: {data['error']}")
                        if st.checkbox("Показать детали ошибки"):
                            st.json(data)
                else:
                    st.error(f"❌ HTTP {response.status_code}")
            except Exception as e:
                st.error(f"❌ Не удается подключиться к боту: {e}")
    
    with col2:
        if st.button("🔄 Перезагрузить промпт", use_container_width=True):
            try:
                import requests
                
                # Получаем админский токен из secrets
                admin_token = st.secrets.get("ADMIN_TOKEN", "secure-admin-token")
                
                headers = {
                    "X-Admin-Token": admin_token,
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    "https://artemintegrator-nahdj.ondigitalocean.app/admin/reload-prompt", 
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("changed"):
                        st.success(f"✅ Промпт обновлен")
                        st.info(f"📅 Старое обновление: {data.get('old_updated', 'Неизвестно')}")
                        st.info(f"📅 Новое обновление: {data.get('new_updated', 'Неизвестно')}")
                    else:
                        st.info("📝 Промпт перезагружен (без изменений)")
                        
                    # Показываем детали успешного ответа
                    with st.expander("🔍 Детали ответа"):
                        st.json(data)
                        
                elif response.status_code == 403:
                    st.error("❌ Ошибка аутентификации: неверный админский токен")
                    st.info("🔑 Проверьте настройку ADMIN_TOKEN в secrets")
                elif response.status_code == 404:
                    st.error("❌ Админские endpoints отключены")
                    st.info("⚙️ Убедитесь, что на сервере настроены администраторы")
                else:
                    st.error(f"❌ HTTP {response.status_code}")
                    try:
                        error_data = response.json()
                        st.error(f"Детали: {error_data.get('detail', 'Неизвестная ошибка')}")
                    except:
                        st.error(f"Ответ сервера: {response.text[:200]}")
                        
            except Exception as e:
                st.error(f"❌ Ошибка перезагрузки: {e}")
                st.info("🌐 Проверьте подключение к серверу")
    
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