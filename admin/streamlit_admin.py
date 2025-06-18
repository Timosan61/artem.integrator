import streamlit as st
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import INSTRUCTION_FILE


def load_instruction():
    try:
        with open(INSTRUCTION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "system_instruction": "",
            "welcome_message": "",
            "last_updated": datetime.now().isoformat()
        }


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
        page_title="Textil PRO Bot Admin",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 Textil PRO Bot - Админ панель")
    st.markdown("---")
    
    if not os.path.exists(INSTRUCTION_FILE):
        st.warning("⚠️ Файл инструкций не найден. Создайте новые инструкции.")
    
    instruction_data = load_instruction()
    
    st.header("📝 Управление инструкциями бота")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Системная инструкция")
        st.markdown("*Основные инструкции для AI-агента*")
        
        system_instruction = st.text_area(
            "Системная инструкция:",
            value=instruction_data.get("system_instruction", ""),
            height=300,
            help="Это основная инструкция, которая определяет поведение бота"
        )
        
        st.subheader("Приветственное сообщение")
        st.markdown("*Сообщение, которое видят пользователи при команде /start*")
        
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
        
        if st.button("📥 Экспорт в JSON", use_container_width=True):
            st.download_button(
                label="💾 Скачать JSON",
                data=json.dumps(instruction_data, ensure_ascii=False, indent=2),
                file_name=f"textil_pro_instructions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    st.markdown("---")
    
    col_save, col_preview = st.columns([1, 1])
    
    with col_save:
        if st.button("💾 Сохранить изменения", type="primary", use_container_width=True):
            new_instruction_data = {
                "system_instruction": system_instruction,
                "welcome_message": welcome_message,
                "last_updated": datetime.now().isoformat()
            }
            
            if save_instruction(new_instruction_data):
                st.success("✅ Инструкции успешно сохранены!")
                st.balloons()
            else:
                st.error("❌ Ошибка при сохранении инструкций")
    
    with col_preview:
        if st.button("👁️ Предварительный просмотр", use_container_width=True):
            st.markdown("### 🔍 Предварительный просмотр")
            
            with st.expander("Системная инструкция", expanded=True):
                st.markdown(f"```\n{system_instruction}\n```")
            
            with st.expander("Приветственное сообщение", expanded=True):
                st.markdown(welcome_message)
    
    st.markdown("---")
    st.markdown("### 📖 Инструкция по использованию")
    
    with st.expander("Как пользоваться админ панелью"):
        st.markdown("""
        1. **Системная инструкция** - основные правила поведения бота
        2. **Приветственное сообщение** - текст для команды /start
        3. **Сохранить изменения** - применить новые настройки
        4. **Предварительный просмотр** - посмотреть как будет выглядеть
        5. После сохранения используйте команду `/reload` в боте для применения изменений
        """)
    
    with st.expander("Команды бота"):
        st.markdown("""
        - `/start` - Запуск бота и приветствие
        - `/help` - Справка по командам
        - `/reload` - Перезагрузка инструкций
        """)


if __name__ == "__main__":
    main()