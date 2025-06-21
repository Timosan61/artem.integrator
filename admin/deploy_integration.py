import streamlit as st
import git
import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any

class DeployManager:
    def __init__(self):
        self.repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.railway_token = st.secrets.get("RAILWAY_TOKEN", os.getenv("RAILWAY_TOKEN"))
        self.railway_project_id = st.secrets.get("RAILWAY_PROJECT_ID", os.getenv("RAILWAY_PROJECT_ID"))
        self.railway_service_id = st.secrets.get("RAILWAY_SERVICE_ID", os.getenv("RAILWAY_SERVICE_ID"))
        
    def get_git_status(self) -> Dict[str, Any]:
        """Получает статус Git репозитория"""
        try:
            repo = git.Repo(self.repo_path)
            
            # Проверяем, есть ли uncommitted изменения
            is_dirty = repo.is_dirty()
            untracked_files = repo.untracked_files
            
            # Получаем последний коммит
            last_commit = repo.head.commit
            
            return {
                "is_dirty": is_dirty,
                "untracked_files": untracked_files,
                "last_commit_sha": last_commit.hexsha[:8],
                "last_commit_message": last_commit.message.strip(),
                "last_commit_date": datetime.fromtimestamp(last_commit.committed_date),
                "current_branch": repo.active_branch.name,
                "status": "clean" if not is_dirty and not untracked_files else "dirty"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def commit_and_push_changes(self, commit_message: str) -> bool:
        """Коммитит и пушит изменения в GitHub"""
        try:
            repo = git.Repo(self.repo_path)
            
            # Добавляем все изменения
            repo.git.add('data/instruction.json')
            
            # Проверяем, есть ли что коммитить
            if not repo.is_dirty():
                st.info("Нет изменений для коммита")
                return True
            
            # Создаем коммит
            repo.index.commit(commit_message)
            
            # Пушим в remote
            origin = repo.remote(name='origin')
            origin.push()
            
            return True
            
        except Exception as e:
            st.error(f"Ошибка при работе с Git: {e}")
            return False
    
    def trigger_railway_deploy(self) -> bool:
        """Запускает деплой на Railway через API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.railway_token}",
                "Content-Type": "application/json"
            }
            
            # GraphQL запрос для редеплоя
            query = """
            mutation {
                serviceInstanceRedeploy(
                    serviceId: "%s"
                ) {
                    id
                }
            }
            """ % self.railway_service_id
            
            response = requests.post(
                "https://backboard.railway.com/graphql/v2",
                headers=headers,
                json={"query": query}
            )
            
            if response.status_code == 200:
                result = response.json()
                if "errors" not in result:
                    return True
                else:
                    st.error(f"Ошибка Railway API: {result['errors']}")
                    return False
            else:
                st.error(f"Ошибка HTTP: {response.status_code}")
                return False
                
        except Exception as e:
            st.error(f"Ошибка при обращении к Railway API: {e}")
            return False
    
    def auto_deploy_changes(self, commit_message: str) -> bool:
        """Автоматический деплой: коммит + пуш + редеплой"""
        
        with st.spinner("Коммит изменений в Git..."):
            if not self.commit_and_push_changes(commit_message):
                return False
        
        st.success("✅ Изменения отправлены в GitHub")
        
        # Railway автоматически подтянет изменения, но можем принудительно перезапустить
        with st.spinner("Запуск деплоя на Railway..."):
            if self.trigger_railway_deploy():
                st.success("✅ Деплой запущен на Railway")
                st.info("🚀 Изменения будут применены в течение 2-3 минут")
                return True
            else:
                st.warning("⚠️ Деплой не запустился, но изменения в GitHub сохранены")
                return False

def show_deploy_status():
    """Показывает статус деплоя в боковой панели"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🚀 Статус деплоя")
    
    deploy_manager = DeployManager()
    git_status = deploy_manager.get_git_status()
    
    if "error" in git_status:
        st.sidebar.error(f"❌ Ошибка Git: {git_status['error']}")
        return
    
    # Показываем статус Git
    if git_status["status"] == "clean":
        st.sidebar.success("✅ Git: все изменения сохранены")
    else:
        st.sidebar.warning("⚠️ Git: есть несохраненные изменения")
    
    # Информация о последнем коммите
    st.sidebar.info(f"""
    **Последний коммит:**
    `{git_status['last_commit_sha']}`
    
    **Сообщение:**
    {git_status['last_commit_message'][:50]}...
    
    **Дата:**
    {git_status['last_commit_date'].strftime('%d.%m.%Y %H:%M')}
    """)
    
    return deploy_manager