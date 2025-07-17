"""
MCP Admin Panel - Streamlit интерфейс для управления MCP

Предоставляет удобный веб-интерфейс для:
- Мониторинга состояния MCP серверов
- Выполнения SQL запросов в Supabase
- Управления DigitalOcean приложениями
- Поиска документации через Context7
- Просмотра метрик и логов
"""

import streamlit as st
import asyncio
import json
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional
import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Проверяем доступность MCP
try:
    from bot.mcp_agent import MCPAgent
    from bot.mcp_manager import MCPManager
    from bot.services.mcp_service import MCPServiceFactory
    from bot.config import MCP_ENABLED, ANTHROPIC_API_KEY, OPENAI_API_KEY
    from bot.config import MCP_SUPABASE_ENABLED, MCP_DIGITALOCEAN_ENABLED, MCP_CONTEXT7_ENABLED
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    MCP_ENABLED = False
    st.error(f"❌ Ошибка импорта MCP модулей: {e}")

# Настройка страницы
st.set_page_config(
    page_title="🔌 MCP Admin Panel",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS стили
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .stButton > button {
        width: 100%;
        background-color: #007bff;
        color: white;
        border: none;
        padding: 10px;
        border-radius: 5px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .stButton > button:hover {
        background-color: #0056b3;
    }
</style>
""", unsafe_allow_html=True)

# Инициализация session state
if 'mcp_manager' not in st.session_state:
    st.session_state.mcp_manager = None
    st.session_state.mcp_agent = None
    st.session_state.service_factory = None
    st.session_state.initialized = False
    st.session_state.sql_history = []
    st.session_state.deployment_history = []
    st.session_state.current_project = None
    st.session_state.current_app = None

async def initialize_mcp():
    """Инициализация MCP компонентов"""
    if not MCP_AVAILABLE or not MCP_ENABLED:
        return False
    
    try:
        # Создаем MCP Manager
        mcp_manager = MCPManager()
        await mcp_manager.initialize()
        
        # Создаем MCP Agent
        mcp_agent = MCPAgent(
            openai_key=OPENAI_API_KEY,
            anthropic_key=ANTHROPIC_API_KEY,
            mcp_manager=mcp_manager
        )
        
        # Создаем Service Factory
        service_factory = MCPServiceFactory(mcp_manager)
        
        # Сохраняем в session state
        st.session_state.mcp_manager = mcp_manager
        st.session_state.mcp_agent = mcp_agent
        st.session_state.service_factory = service_factory
        st.session_state.initialized = True
        
        return True
    except Exception as e:
        st.error(f"❌ Ошибка инициализации MCP: {e}")
        return False

def format_time_ago(timestamp: datetime) -> str:
    """Форматирует время в человекочитаемый формат"""
    now = datetime.now()
    diff = now - timestamp
    
    if diff < timedelta(minutes=1):
        return "только что"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} мин. назад"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} ч. назад"
    else:
        days = diff.days
        return f"{days} дн. назад"

def display_server_status(status: Dict[str, Any]):
    """Отображает статус MCP серверов"""
    st.header("📊 Статус MCP серверов")
    
    if not status.get("mcp_enabled"):
        st.error("❌ MCP отключен в конфигурации")
        return
    
    servers = status.get("servers", {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        supabase_status = servers.get("supabase", {})
        if supabase_status.get("enabled"):
            st.success("✅ Supabase")
            st.metric("Функций", supabase_status.get("functions_count", 0))
        else:
            st.error("❌ Supabase отключен")
    
    with col2:
        do_status = servers.get("digitalocean", {})
        if do_status.get("enabled"):
            st.success("✅ DigitalOcean")
            st.metric("Функций", do_status.get("functions_count", 0))
        else:
            st.error("❌ DigitalOcean отключен")
    
    with col3:
        ctx7_status = servers.get("context7", {})
        if ctx7_status.get("enabled"):
            st.success("✅ Context7")
            st.metric("Функций", ctx7_status.get("functions_count", 0))
        else:
            st.error("❌ Context7 отключен")

def display_metrics(metrics: Dict[str, Any]):
    """Отображает метрики использования MCP"""
    st.header("📈 Метрики использования")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Всего вызовов", metrics.get("total_calls", 0))
    
    with col2:
        successful = metrics.get("total_successful", 0)
        st.metric("Успешных", successful, delta=None)
    
    with col3:
        failed = metrics.get("total_failed", 0)
        st.metric("Ошибок", failed, delta=None)
    
    with col4:
        avg_time = metrics.get("average_execution_time", 0)
        st.metric("Среднее время", f"{avg_time:.2f}с")
    
    # График по серверам
    servers_data = metrics.get("servers", {})
    if servers_data:
        st.subheader("📊 Статистика по серверам")
        
        # Подготовка данных для графика
        server_names = []
        calls_count = []
        
        for server_name, server_metrics in servers_data.items():
            server_names.append(server_name.capitalize())
            calls_count.append(server_metrics.get("total_calls", 0))
        
        # Создаем график
        fig = px.bar(
            x=server_names,
            y=calls_count,
            labels={'x': 'Сервер', 'y': 'Количество вызовов'},
            title="Использование серверов"
        )
        st.plotly_chart(fig)

async def supabase_tab():
    """Вкладка для работы с Supabase"""
    st.header("🗄️ Supabase Manager")
    
    if not MCP_SUPABASE_ENABLED:
        st.warning("⚠️ Supabase не включен в конфигурации")
        return
    
    supabase_service = st.session_state.service_factory.get_supabase_service()
    
    # Выбор проекта
    st.subheader("📂 Проекты")
    
    if st.button("🔄 Обновить список проектов"):
        with st.spinner("Загрузка проектов..."):
            result = await supabase_service.list_projects()
            if result["success"]:
                projects = result["projects"]
                st.session_state.projects = projects
                st.success(f"✅ Загружено {len(projects)} проектов")
            else:
                st.error(result["message"])
    
    # Отображение проектов
    if hasattr(st.session_state, 'projects'):
        project_names = [p["name"] for p in st.session_state.projects]
        selected_project = st.selectbox(
            "Выберите проект",
            options=range(len(project_names)),
            format_func=lambda x: project_names[x]
        )
        
        if selected_project is not None:
            project = st.session_state.projects[selected_project]
            st.session_state.current_project = project["id"]
            
            # Информация о проекте
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**ID:** `{project['id']}`")
            with col2:
                st.info(f"**Регион:** {project.get('region', 'неизвестно')}")
    
    # SQL запросы
    if st.session_state.current_project:
        st.subheader("🔍 SQL запросы")
        
        # SQL редактор
        sql_query = st.text_area(
            "SQL запрос",
            height=150,
            placeholder="SELECT * FROM users LIMIT 10;"
        )
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("▶️ Выполнить запрос", type="primary"):
                if sql_query:
                    with st.spinner("Выполнение запроса..."):
                        result = await supabase_service.execute_sql(
                            st.session_state.current_project,
                            sql_query
                        )
                        
                        if result["success"]:
                            # Сохраняем в историю
                            st.session_state.sql_history.append({
                                "query": sql_query,
                                "timestamp": datetime.now(),
                                "rows_count": len(result.get("rows", [])),
                                "execution_time": result.get("execution_time", 0)
                            })
                            
                            # Отображаем результаты
                            st.success(f"✅ Запрос выполнен за {result['execution_time']:.2f}с")
                            
                            rows = result.get("rows", [])
                            if rows:
                                df = pd.DataFrame(rows)
                                st.dataframe(df, use_container_width=True)
                            else:
                                st.info("Запрос не вернул данных")
                            
                            if result.get("affected_rows"):
                                st.info(f"Затронуто строк: {result['affected_rows']}")
                        else:
                            st.error(result["message"])
                else:
                    st.warning("Введите SQL запрос")
        
        with col2:
            # История запросов
            if st.button("📜 История"):
                if st.session_state.sql_history:
                    st.subheader("История запросов")
                    for item in reversed(st.session_state.sql_history[-10:]):
                        with st.expander(
                            f"{format_time_ago(item['timestamp'])} - {item['rows_count']} строк"
                        ):
                            st.code(item['query'], language='sql')
                            st.caption(f"Время выполнения: {item['execution_time']:.2f}с")
                else:
                    st.info("История пуста")
        
        # Таблицы
        st.subheader("📊 Таблицы")
        
        if st.button("🔄 Загрузить список таблиц"):
            with st.spinner("Загрузка таблиц..."):
                result = await supabase_service.list_tables(
                    st.session_state.current_project,
                    schemas=["public"]
                )
                
                if result["success"]:
                    tables = result["tables"]
                    if tables:
                        df = pd.DataFrame(tables)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Таблицы не найдены")
                else:
                    st.error(result["message"])

async def digitalocean_tab():
    """Вкладка для работы с DigitalOcean"""
    st.header("🌊 DigitalOcean Manager")
    
    if not MCP_DIGITALOCEAN_ENABLED:
        st.warning("⚠️ DigitalOcean не включен в конфигурации")
        return
    
    do_service = st.session_state.service_factory.get_digitalocean_service()
    
    # Список приложений
    st.subheader("🚀 Приложения")
    
    if st.button("🔄 Обновить список приложений"):
        with st.spinner("Загрузка приложений..."):
            result = await do_service.list_apps()
            if result["success"]:
                apps = result["apps"]
                st.session_state.apps = apps
                st.success(f"✅ Загружено {len(apps)} приложений")
            else:
                st.error(result["message"])
    
    # Отображение приложений
    if hasattr(st.session_state, 'apps'):
        for app in st.session_state.apps:
            status_emoji = {
                "active": "🟢",
                "deploying": "🚀",
                "error": "🔴",
                "building": "🔨"
            }.get(app.get("status", ""), "⚪")
            
            with st.expander(f"{status_emoji} {app['name']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"**ID:** `{app['id']}`")
                    st.info(f"**Статус:** {app.get('status', 'неизвестно')}")
                
                with col2:
                    # Кнопки действий
                    if st.button(f"🚀 Деплой", key=f"deploy_{app['id']}"):
                        with st.spinner("Запуск деплоя..."):
                            result = await do_service.create_deployment(app['id'])
                            if result["success"]:
                                st.success(result["message"])
                                st.session_state.deployment_history.append({
                                    "app_id": app['id'],
                                    "app_name": app['name'],
                                    "deployment_id": result["deployment_id"],
                                    "timestamp": datetime.now()
                                })
                            else:
                                st.error(result["message"])
                    
                    if st.button(f"📋 Логи", key=f"logs_{app['id']}"):
                        st.session_state.current_app = app['id']
                        st.session_state.show_logs = True
    
    # Отображение логов
    if hasattr(st.session_state, 'show_logs') and st.session_state.show_logs:
        st.subheader("📋 Логи приложения")
        
        log_type = st.selectbox(
            "Тип логов",
            options=["RUN", "BUILD", "DEPLOY"],
            index=0
        )
        
        if st.button("🔄 Загрузить логи"):
            with st.spinner("Загрузка логов..."):
                result = await do_service.get_app_logs(
                    st.session_state.current_app,
                    log_type
                )
                
                if result["success"]:
                    logs = result["logs"]
                    if logs:
                        st.text_area(
                            f"Логи {log_type}",
                            value=logs,
                            height=400
                        )
                    else:
                        st.info("Логи пусты")
                else:
                    st.error(result["message"])
        
        if st.button("❌ Закрыть логи"):
            st.session_state.show_logs = False
            st.rerun()
    
    # История деплоев
    if st.session_state.deployment_history:
        st.subheader("📜 История деплоев")
        
        for item in reversed(st.session_state.deployment_history[-5:]):
            st.info(
                f"🚀 {item['app_name']} - "
                f"{format_time_ago(item['timestamp'])} - "
                f"ID: `{item['deployment_id']}`"
            )

async def context7_tab():
    """Вкладка для работы с Context7"""
    st.header("📚 Context7 Documentation")
    
    if not MCP_CONTEXT7_ENABLED:
        st.warning("⚠️ Context7 не включен в конфигурации")
        return
    
    ctx7_service = st.session_state.service_factory.get_context7_service()
    
    # Поиск документации
    st.subheader("🔍 Поиск документации")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        library_name = st.text_input(
            "Библиотека",
            placeholder="react, nextjs, supabase..."
        )
    
    with col2:
        search_query = st.text_input(
            "Запрос",
            placeholder="hooks, routing, auth..."
        )
    
    if st.button("🔍 Искать", type="primary"):
        if library_name and search_query:
            with st.spinner("Поиск документации..."):
                result = await ctx7_service.search_docs(
                    library_name,
                    search_query,
                    limit=10
                )
                
                if result["success"]:
                    results = result["results"]
                    st.success(f"✅ Найдено {len(results)} результатов")
                    
                    for i, doc in enumerate(results, 1):
                        with st.expander(f"{i}. {doc.get('title', 'Без названия')}"):
                            if doc.get("snippet"):
                                st.markdown(doc["snippet"])
                            
                            if doc.get("url"):
                                st.markdown(f"[🔗 Читать полностью]({doc['url']})")
                else:
                    st.error(result["message"])
        else:
            st.warning("Заполните все поля")
    
    # Примеры кода
    st.subheader("💻 Примеры кода")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        example_library = st.text_input(
            "Библиотека для примеров",
            placeholder="react, vue, express..."
        )
    
    with col2:
        example_topic = st.text_input(
            "Тема",
            placeholder="authentication, routing..."
        )
    
    with col3:
        language = st.selectbox(
            "Язык",
            options=["javascript", "typescript", "python", "go"],
            index=0
        )
    
    if st.button("💻 Получить примеры"):
        if example_library and example_topic:
            with st.spinner("Загрузка примеров..."):
                result = await ctx7_service.get_code_examples(
                    example_library,
                    example_topic,
                    language
                )
                
                if result["success"]:
                    examples = result["examples"]
                    if examples:
                        for example in examples:
                            with st.expander(example.get("title", "Пример")):
                                if example.get("description"):
                                    st.markdown(example["description"])
                                
                                if example.get("code"):
                                    st.code(
                                        example["code"],
                                        language=example.get("language", "javascript")
                                    )
                    else:
                        st.info("Примеры не найдены")
                else:
                    st.error(result["message"])
        else:
            st.warning("Заполните все поля")

async def monitoring_tab():
    """Вкладка мониторинга и диагностики"""
    st.header("🔍 Мониторинг и диагностика")
    
    # Обновление статуса
    if st.button("🔄 Обновить статус", type="primary"):
        if st.session_state.mcp_agent:
            with st.spinner("Обновление статуса..."):
                status = await st.session_state.mcp_agent.get_status()
                metrics = st.session_state.mcp_manager.get_metrics()
                
                display_server_status(status)
                display_metrics(metrics)
        else:
            st.error("MCP Agent не инициализирован")
    
    # Health Check
    st.subheader("🏥 Health Check")
    
    if st.button("🏥 Проверить здоровье серверов"):
        if st.session_state.mcp_manager:
            with st.spinner("Проверка серверов..."):
                col1, col2, col3 = st.columns(3)
                
                # Проверяем каждый сервер
                servers = ["supabase", "digitalocean", "context7"]
                for i, server in enumerate(servers):
                    connection = st.session_state.mcp_manager._get_connection(server)
                    if connection:
                        is_healthy = await connection.health_check()
                        
                        with [col1, col2, col3][i]:
                            if is_healthy:
                                st.success(f"✅ {server.capitalize()}")
                            else:
                                st.error(f"❌ {server.capitalize()}")
                    else:
                        with [col1, col2, col3][i]:
                            st.warning(f"⚠️ {server.capitalize()} не подключен")
    
    # Кэш статистика
    st.subheader("💾 Статистика кэша")
    
    if st.session_state.mcp_manager:
        cache_stats = st.session_state.mcp_manager._cache_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Размер кэша", cache_stats["size"])
        
        with col2:
            st.metric("Попаданий", cache_stats["hits"])
        
        with col3:
            st.metric("Промахов", cache_stats["misses"])
        
        if cache_stats["size"] > 0:
            hit_rate = (cache_stats["hits"] / (cache_stats["hits"] + cache_stats["misses"])) * 100
            st.info(f"📊 Hit Rate: {hit_rate:.1f}%")
        
        if st.button("🗑️ Очистить кэш"):
            st.session_state.mcp_manager._clear_cache()
            st.success("✅ Кэш очищен")

# Главная функция
async def main():
    st.title("🔌 MCP Admin Panel")
    st.markdown("Управление Model Context Protocol серверами")
    
    # Проверка доступности MCP
    if not MCP_AVAILABLE:
        st.error("❌ MCP модули не доступны. Проверьте установку зависимостей.")
        return
    
    if not MCP_ENABLED:
        st.warning("⚠️ MCP отключен в конфигурации (MCP_ENABLED=false)")
        return
    
    # Инициализация MCP если еще не инициализирован
    if not st.session_state.initialized:
        with st.spinner("Инициализация MCP..."):
            success = await initialize_mcp()
            if not success:
                st.error("❌ Не удалось инициализировать MCP")
                return
    
    # Боковое меню
    with st.sidebar:
        st.header("🔌 MCP Control Panel")
        
        # Статус подключения
        if st.session_state.initialized:
            st.success("✅ MCP подключен")
        else:
            st.error("❌ MCP не подключен")
        
        # Информация о конфигурации
        st.subheader("⚙️ Конфигурация")
        st.info(f"**Anthropic API:** {'✅' if ANTHROPIC_API_KEY else '❌'}")
        st.info(f"**OpenAI API:** {'✅' if OPENAI_API_KEY else '❌'}")
        
        # Навигация
        st.subheader("📍 Навигация")
        page = st.radio(
            "Выберите раздел",
            options=[
                "🔍 Мониторинг",
                "🗄️ Supabase",
                "🌊 DigitalOcean",
                "📚 Context7"
            ],
            index=0
        )
    
    # Отображение выбранной страницы
    if page == "🔍 Мониторинг":
        await monitoring_tab()
    elif page == "🗄️ Supabase":
        await supabase_tab()
    elif page == "🌊 DigitalOcean":
        await digitalocean_tab()
    elif page == "📚 Context7":
        await context7_tab()
    
    # Footer
    st.markdown("---")
    st.caption("🤖 Artem Integrator MCP Admin Panel v1.0")

# Запуск приложения
if __name__ == "__main__":
    # Запускаем асинхронное приложение
    asyncio.run(main())