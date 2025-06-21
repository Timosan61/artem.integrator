import streamlit as st
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.config import INSTRUCTION_FILE, DEFAULT_INSTRUCTION, STREAMLIT_CONFIG
from admin.auth import check_password
from admin.deploy_integration import DeployManager


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
    st.title("🤖 Textil PRO Bot - Админ панель")
    
    deploy_manager = DeployManager()
    
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