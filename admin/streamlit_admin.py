import streamlit as st
import json
import os
import sys
from datetime import datetime
from streamlit_ace import st_ace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.config import INSTRUCTION_FILE, DEFAULT_INSTRUCTION, STREAMLIT_CONFIG
from admin.auth import check_password, show_auth_info
from admin.deploy_integration import show_deploy_status, DeployManager


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
        instruction_data["last_updated"] = datetime.now().isoformat()
        with open(INSTRUCTION_FILE, 'w', encoding='utf-8') as f:
            json.dump(instruction_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Ошибка при сохранении: {e}")
        return False


def main():
    st.set_page_config(
        page_title=STREAMLIT_CONFIG['page_title'],
        page_icon=STREAMLIT_CONFIG['page_icon'],
        layout=STREAMLIT_CONFIG['layout'],
        initial_sidebar_state="expanded"
    )
    
    # Проверка авторизации
    if not check_password():
        return
    
    # Заголовок и боковая панель
    st.title("🤖 Textil PRO Bot - Админ панель")
    
    # Показываем информацию об авторизации и деплое в боковой панели
    show_auth_info()
    deploy_manager = show_deploy_status()
    
    # Основной интерфейс
    tab1, tab2, tab3 = st.tabs(["📝 Редактор", "🔍 Предпросмотр", "📊 Статистика"])
    
    if not os.path.exists(INSTRUCTION_FILE):
        st.warning("⚠️ Файл инструкций не найден. Создайте новые инструкции.")
    
    instruction_data = load_instruction()
    
    with tab1:
        st.header("📝 Управление инструкциями бота")
        
        # Выбор режима редактирования
        edit_mode = st.radio(
            "Режим редактирования:",
            ["🖊️ Обычный редактор", "⚡ Код-редактор"],
            horizontal=True
        )
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Системная инструкция")
            st.markdown("*Основные инструкции для AI-агента*")
            
            if edit_mode == "⚡ Код-редактор":
                system_instruction = st_ace(
                    value=instruction_data.get("system_instruction", ""),
                    language='text',
                    theme='github',
                    height=400,
                    key="system_instruction_ace",
                    auto_update=True
                )
            else:
                system_instruction = st.text_area(
                    "Системная инструкция:",
                    value=instruction_data.get("system_instruction", ""),
                    height=400,
                    help="Это основная инструкция, которая определяет поведение бота"
                )
            
            st.subheader("Приветственное сообщение")
            st.markdown("*Сообщение, которое видят пользователи при команде /start*")
            
            if edit_mode == "⚡ Код-редактор":
                welcome_message = st_ace(
                    value=instruction_data.get("welcome_message", ""),
                    language='text',
                    theme='github',
                    height=150,
                    key="welcome_message_ace",
                    auto_update=True
                )
            else:
                welcome_message = st.text_area(
                    "Приветственное сообщение:",
                    value=instruction_data.get("welcome_message", ""),
                    height=150,
                    help="Это сообщение отправляется пользователям при первом запуске бота"
                )
        
        with col2:
            st.subheader("📊 Информация")
            
            if instruction_data.get("last_updated"):
                st.info(f"**Последнее обновление:**\n{instruction_data['last_updated']}")
            
            st.markdown("### 🔧 Статус")
            if os.path.exists(INSTRUCTION_FILE):
                st.success("✅ Файл инструкций найден")
            else:
                st.error("❌ Файл инструкций не найден")
            
            st.markdown("### 📋 Быстрые действия")
            
            if st.button("🔄 Обновить данные", use_container_width=True):
                st.rerun()
            
            st.download_button(
                label="📥 Экспорт в JSON",
                data=json.dumps(instruction_data, ensure_ascii=False, indent=2),
                file_name=f"textil_pro_instructions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
            
            # Импорт JSON
            uploaded_file = st.file_uploader(
                "📤 Импорт инструкций",
                type=['json'],
                help="Загрузите JSON файл с инструкциями"
            )
            
            if uploaded_file is not None:
                try:
                    imported_data = json.load(uploaded_file)
                    if st.button("🔄 Применить импорт", use_container_width=True):
                        if save_instruction(imported_data):
                            st.success("✅ Инструкции импортированы!")
                            st.rerun()
                except json.JSONDecodeError:
                    st.error("❌ Ошибка: некорректный JSON файл")
        
        st.markdown("---")
        
        # Кнопки сохранения
        col_save, col_deploy, col_preview = st.columns([1, 1, 1])
        
        with col_save:
            if st.button("💾 Сохранить локально", use_container_width=True):
                new_instruction_data = {
                    "system_instruction": system_instruction,
                    "welcome_message": welcome_message,
                    "last_updated": datetime.now().isoformat()
                }
                
                if save_instruction(new_instruction_data):
                    st.success("✅ Инструкции сохранены локально!")
                else:
                    st.error("❌ Ошибка при сохранении")
        
        with col_deploy:
            if st.button("🚀 Сохранить и задеплоить", type="primary", use_container_width=True):
                new_instruction_data = {
                    "system_instruction": system_instruction,
                    "welcome_message": welcome_message,
                    "last_updated": datetime.now().isoformat()
                }
                
                if save_instruction(new_instruction_data):
                    st.success("✅ Инструкции сохранены!")
                    
                    # Автоматический деплой
                    commit_message = f"Update bot instructions via admin panel\n\n- Modified system instruction\n- Updated welcome message\n- Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
                    
                    if deploy_manager.auto_deploy_changes(commit_message):
                        st.balloons()
                    
                else:
                    st.error("❌ Ошибка при сохранении")
        
        with col_preview:
            if st.button("👁️ Предпросмотр", use_container_width=True):
                st.session_state["show_preview"] = True
    
    with tab2:
        st.header("🔍 Предварительный просмотр")
        
        if st.session_state.get("show_preview", False):
            current_system = instruction_data.get("system_instruction", "")
            current_welcome = instruction_data.get("welcome_message", "")
        else:
            current_system = instruction_data.get("system_instruction", "")
            current_welcome = instruction_data.get("welcome_message", "")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📜 Системная инструкция")
            with st.container():
                st.markdown(f"```\n{current_system}\n```")
        
        with col2:
            st.subheader("👋 Приветственное сообщение")
            with st.container():
                st.markdown(current_welcome)
    
    with tab3:
        st.header("📊 Статистика и информация")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📖 Инструкция по использованию")
            st.markdown("""
            1. **Системная инструкция** - основные правила поведения бота
            2. **Приветственное сообщение** - текст для команды /start  
            3. **Сохранить локально** - сохранить без деплоя
            4. **Сохранить и задеплоить** - автоматический деплой на Railway
            5. **Предварительный просмотр** - посмотреть как будет выглядеть
            """)
            
            st.subheader("🔧 Доступные режимы")
            st.markdown("""
            - **Обычный редактор** - простое текстовое поле
            - **Код-редактор** - расширенный редактор с подсветкой
            """)
        
        with col2:
            st.subheader("🤖 Команды бота")
            st.markdown("""
            - `/start` - Запуск бота и приветствие
            - `/help` - Справка по командам
            - `/reload` - Перезагрузка инструкций (если поддерживается)
            """)
            
            st.subheader("🚀 Информация о деплое")
            st.markdown("""
            - Изменения автоматически применяются на Railway
            - Процесс деплоя занимает 2-3 минуты
            - Статус деплоя отображается в боковой панели
            """)


if __name__ == "__main__":
    main()