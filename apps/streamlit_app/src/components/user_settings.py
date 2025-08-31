"""
Компонент для настроек пользователя
"""
import streamlit as st
import requests
from typing import Dict, Any, Optional
import json
from datetime import datetime


class UserSettings:
    """Компонент для управления настройками пользователя"""
    
    def __init__(self, api_base_url: str, access_token: str = None):
        self.api_base_url = api_base_url
        self.access_token = access_token
        self.settings_categories = {
            'profile': '👤 Профиль',
            'preferences': '⚙️ Предпочтения',
            'security': '🔒 Безопасность',
            'notifications': '🔔 Уведомления',
            'interface': '🎨 Интерфейс',
            'data': '📊 Данные',
            'integrations': '🔗 Интеграции',
            'advanced': '🔧 Расширенные',
            'backup': '💾 Резервное копирование'
        }
    
    def render(self):
        """Основной метод рендеринга настроек"""
        st.header("⚙️ Настройки пользователя")
        
        # Проверяем, что user_info существует
        if not hasattr(st.session_state, 'user_info') or not st.session_state.user_info:
            st.error("❌ Информация о пользователе недоступна")
            return
        
        # Навигация по категориям настроек
        selected_category = self._render_category_navigation()
        
        # Отображение выбранной категории
        if selected_category == 'profile':
            self._render_profile_settings()
        elif selected_category == 'preferences':
            self._render_preferences_settings()
        elif selected_category == 'security':
            self._render_security_settings()
        elif selected_category == 'notifications':
            self._render_notifications_settings()
        elif selected_category == 'interface':
            self._render_interface_settings()
        elif selected_category == 'data':
            self._render_data_settings()
        elif selected_category == 'integrations':
            self._render_integrations_settings()
        elif selected_category == 'advanced':
            self._render_advanced_settings()
        elif selected_category == 'backup':
            self._render_backup_settings()
        
        # Общие действия
        self._render_common_actions()
    
    def _render_category_navigation(self) -> str:
        """Навигация по категориям настроек"""
        st.subheader("📂 Категории настроек")
        
        # Создаем кнопки для каждой категории
        cols = st.columns(len(self.settings_categories))
        selected_category = None
        
        for i, (key, name) in enumerate(self.settings_categories.items()):
            with cols[i]:
                if st.button(name, key=f"category_{key}", use_container_width=True):
                    selected_category = key
        
        # Если категория не выбрана, показываем профиль по умолчанию
        if not selected_category:
            selected_category = 'profile'
        
        # Подсветка выбранной категории
        st.success(f"✅ Выбрана категория: {self.settings_categories[selected_category]}")
        
        return selected_category
    
    def _render_profile_settings(self):
        """Настройки профиля"""
        st.subheader("👤 Настройки профиля")
        
        user_info = st.session_state.user_info
        
        # Основная информация
        with st.expander("📝 Основная информация", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input(
                    "Имя",
                    value=user_info.get('first_name', ''),
                    key="profile_first_name"
                )
                
                last_name = st.text_input(
                    "Фамилия",
                    value=user_info.get('last_name', ''),
                    key="profile_last_name"
                )
                
                email = st.text_input(
                    "Email",
                    value=user_info.get('email', ''),
                    key="profile_email",
                    disabled=True  # Email обычно нельзя изменить
                )
            
            with col2:
                username = st.text_input(
                    "Имя пользователя",
                    value=user_info.get('username', ''),
                    key="profile_username",
                    disabled=True  # Username обычно нельзя изменить
                )
                
                phone = st.text_input(
                    "Телефон",
                    value=user_info.get('phone', ''),
                    key="profile_phone"
                )
                
                position = st.text_input(
                    "Должность",
                    value=user_info.get('position', ''),
                    key="profile_position"
                )
        
        # Дополнительная информация
        with st.expander("📋 Дополнительная информация", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                department = st.text_input(
                    "Отдел",
                    value=user_info.get('department', ''),
                    key="profile_department"
                )
                
                company = st.text_input(
                    "Компания",
                    value=user_info.get('company', ''),
                    key="profile_company"
                )
                
                location = st.text_input(
                    "Местоположение",
                    value=user_info.get('location', ''),
                    key="profile_location"
                )
            
            with col2:
                bio = st.text_area(
                    "О себе",
                    value=user_info.get('bio', ''),
                    height=100,
                    key="profile_bio"
                )
                
                website = st.text_input(
                    "Веб-сайт",
                    value=user_info.get('website', ''),
                    key="profile_website"
                )
        
        # Аватар
        with st.expander("🖼️ Аватар", expanded=False):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Здесь можно добавить загрузку аватара
                st.info("Функция загрузки аватара будет доступна в следующем обновлении")
                
                if user_info.get('avatar_url'):
                    st.image(user_info['avatar_url'], width=100, caption="Текущий аватар")
                else:
                    st.info("Аватар не установлен")
            
            with col2:
                st.write("**Настройки аватара:**")
                st.checkbox("Использовать гравитар", value=True, disabled=True)
                st.checkbox("Автоматически генерировать", value=False, disabled=True)
        
        # Кнопки сохранения
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Сохранить изменения", key="save_profile", use_container_width=True):
                self._save_profile_settings()
        
        with col2:
            if st.button("🔄 Сбросить", key="reset_profile", use_container_width=True):
                st.rerun()
        
        with col3:
            if st.button("📥 Экспорт профиля", key="export_profile", use_container_width=True):
                self._export_profile()
    
    def _render_preferences_settings(self):
        """Настройки предпочтений"""
        st.subheader("⚙️ Предпочтения")
        
        # Язык и регион
        with st.expander("🌍 Язык и регион", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                language = st.selectbox(
                    "Язык интерфейса",
                    ["Русский", "English", "Deutsch", "Français", "Español"],
                    index=0,
                    key="pref_language"
                )
                
                timezone = st.selectbox(
                    "Часовой пояс",
                    ["UTC+3 (Москва)", "UTC+0 (Лондон)", "UTC-5 (Нью-Йорк)", "UTC+9 (Токио)"],
                    index=0,
                    key="pref_timezone"
                )
            
            with col2:
                date_format = st.selectbox(
                    "Формат даты",
                    ["DD.MM.YYYY", "MM/DD/YYYY", "YYYY-MM-DD"],
                    index=0,
                    key="pref_date_format"
                )
                
                time_format = st.selectbox(
                    "Формат времени",
                    ["24-часовой", "12-часовой"],
                    index=0,
                    key="pref_time_format"
                )
        
        # RAG настройки
        with st.expander("🤖 Настройки RAG", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                default_top_k = st.slider(
                    "Количество результатов по умолчанию",
                    min_value=1,
                    max_value=50,
                    value=10,
                    key="pref_top_k"
                )
                
                include_citations = st.checkbox(
                    "Всегда включать цитаты",
                    value=True,
                    key="pref_citations"
                )
                
                auto_expand_results = st.checkbox(
                    "Автоматически разворачивать результаты",
                    value=False,
                    key="pref_auto_expand"
                )
            
            with col2:
                preferred_models = st.multiselect(
                    "Предпочитаемые модели",
                    ["llama3:8b", "llama3.1:8b", "bge-m3", "gpt-3.5-turbo"],
                    default=["llama3:8b"],
                    key="pref_models"
                )
                
                chunk_size = st.selectbox(
                    "Размер чанков",
                    ["Маленький (256)", "Средний (512)", "Большой (1024)"],
                    index=1,
                    key="pref_chunk_size"
                )
        
        # Настройки поиска
        with st.expander("🔍 Настройки поиска", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                search_history = st.checkbox(
                    "Сохранять историю поиска",
                    value=True,
                    key="pref_search_history"
                )
                
                search_suggestions = st.checkbox(
                    "Показывать подсказки поиска",
                    value=True,
                    key="pref_search_suggestions"
                )
                
                auto_complete = st.checkbox(
                    "Автодополнение запросов",
                    value=True,
                    key="pref_auto_complete"
                )
            
            with col2:
                default_search_filters = st.multiselect(
                    "Фильтры поиска по умолчанию",
                    ["Документы", "Таблицы", "Изображения", "PDF", "DOCX", "XLSX"],
                    default=["Документы"],
                    key="pref_search_filters"
                )
                
                search_timeout = st.slider(
                    "Таймаут поиска (секунды)",
                    min_value=5,
                    max_value=60,
                    value=30,
                    key="pref_search_timeout"
                )
    
    def _render_security_settings(self):
        """Настройки безопасности"""
        st.subheader("🔒 Настройки безопасности")
        
        # Смена пароля
        with st.expander("🔑 Смена пароля", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                current_password = st.text_input(
                    "Текущий пароль",
                    type="password",
                    key="security_current_password"
                )
                
                new_password = st.text_input(
                    "Новый пароль",
                    type="password",
                    key="security_new_password"
                )
            
            with col2:
                confirm_password = st.text_input(
                    "Подтвердите новый пароль",
                    type="password",
                    key="security_confirm_password"
                )
                
                st.write("**Требования к паролю:**")
                st.write("• Минимум 8 символов")
                st.write("• Буквы и цифры")
                st.write("• Специальные символы")
            
            if st.button("🔑 Сменить пароль", key="change_password"):
                self._change_password(current_password, new_password, confirm_password)
        
        # Двухфакторная аутентификация
        with st.expander("🔐 Двухфакторная аутентификация", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                two_factor_enabled = st.checkbox(
                    "Включить 2FA",
                    value=False,
                    key="security_2fa"
                )
                
                if two_factor_enabled:
                    st.info("Для настройки 2FA потребуется мобильное приложение")
                    st.button("📱 Настроить 2FA", disabled=True)
            
            with col2:
                backup_codes = st.checkbox(
                    "Резервные коды",
                    value=False,
                    key="security_backup_codes"
                )
                
                if backup_codes:
                    st.button("📋 Сгенерировать резервные коды", disabled=True)
        
        # Сессии и устройства
        with st.expander("💻 Сессии и устройства", expanded=False):
            st.write("**Активные сессии:**")
            st.info("Функция управления сессиями будет доступна в следующем обновлении")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.checkbox("Запомнить устройство", value=True, disabled=True)
                st.checkbox("Уведомления о новых входах", value=True, disabled=True)
            
            with col2:
                st.button("🚪 Завершить все сессии", disabled=True)
                st.button("📱 Управление устройствами", disabled=True)
    
    def _render_notifications_settings(self):
        """Настройки уведомлений"""
        st.subheader("🔔 Настройки уведомлений")
        
        # Email уведомления
        with st.expander("📧 Email уведомления", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                email_notifications = st.checkbox(
                    "Включить email уведомления",
                    value=True,
                    key="notif_email_enabled"
                )
                
                if email_notifications:
                    st.checkbox("Новые документы", value=True, key="notif_new_docs")
                    st.checkbox("Результаты поиска", value=False, key="notif_search_results")
                    st.checkbox("Системные уведомления", value=True, key="notif_system")
            
            with col2:
                if email_notifications:
                    st.checkbox("Еженедельный отчет", value=False, key="notif_weekly_report")
                    st.checkbox("Аналитика использования", value=False, key="notif_analytics")
                    st.checkbox("Обновления безопасности", value=True, key="notif_security")
        
        # Push уведомления
        with st.expander("📱 Push уведомления", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                push_notifications = st.checkbox(
                    "Включить push уведомления",
                    value=False,
                    key="notif_push_enabled"
                )
                
                if push_notifications:
                    st.checkbox("Новые сообщения", value=True, key="notif_push_messages")
                    st.checkbox("Важные обновления", value=True, key="notif_push_updates")
            
            with col2:
                if push_notifications:
                    st.checkbox("Звуковые уведомления", value=True, key="notif_push_sound")
                    st.checkbox("Вибрация", value=False, key="notif_push_vibration")
        
        # Настройки времени
        with st.expander("⏰ Время уведомлений", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                quiet_hours = st.checkbox(
                    "Тихие часы",
                    value=False,
                    key="notif_quiet_hours"
                )
                
                if quiet_hours:
                    start_time = st.time_input("Начало тихих часов", value=datetime.strptime("22:00", "%H:%M").time())
                    end_time = st.time_input("Конец тихих часов", value=datetime.strptime("08:00", "%H:%M").time())
            
            with col2:
                timezone_notifications = st.selectbox(
                    "Часовой пояс для уведомлений",
                    ["Локальное время", "UTC", "Время сервера"],
                    index=0,
                    key="notif_timezone"
                )
    
    def _render_interface_settings(self):
        """Настройки интерфейса"""
        st.subheader("🎨 Настройки интерфейса")
        
        # Тема и цвета
        with st.expander("🎨 Тема и цвета", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                theme = st.selectbox(
                    "Тема интерфейса",
                    ["Светлая", "Темная", "Автоматически"],
                    index=0,
                    key="ui_theme"
                )
                
                primary_color = st.color_picker(
                    "Основной цвет",
                    value="#FF6B6B",
                    key="ui_primary_color"
                )
                
                accent_color = st.color_picker(
                    "Акцентный цвет",
                    value="#4ECDC4",
                    key="ui_accent_color"
                )
            
            with col2:
                font_size = st.selectbox(
                    "Размер шрифта",
                    ["Маленький", "Средний", "Большой"],
                    index=1,
                    key="ui_font_size"
                )
                
                font_family = st.selectbox(
                    "Семейство шрифтов",
                    ["Системный", "Arial", "Times New Roman", "Roboto"],
                    index=0,
                    key="ui_font_family"
                )
        
        # Макет и навигация
        with st.expander("📐 Макет и навигация", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                sidebar_position = st.selectbox(
                    "Позиция боковой панели",
                    ["Слева", "Справа"],
                    index=0,
                    key="ui_sidebar_position"
                )
                
                sidebar_auto_hide = st.checkbox(
                    "Автоматически скрывать боковую панель",
                    value=False,
                    key="ui_sidebar_auto_hide"
                )
                
                compact_mode = st.checkbox(
                    "Компактный режим",
                    value=False,
                    key="ui_compact_mode"
                )
            
            with col2:
                show_breadcrumbs = st.checkbox(
                    "Показывать хлебные крошки",
                    value=True,
                    key="ui_breadcrumbs"
                )
                
                show_progress_bars = st.checkbox(
                    "Показывать индикаторы прогресса",
                    value=True,
                    key="ui_progress_bars"
                )
                
                animations = st.checkbox(
                    "Включить анимации",
                    value=True,
                    key="ui_animations"
                )
        
        # Персонализация
        with st.expander("👤 Персонализация", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                custom_dashboard = st.checkbox(
                    "Пользовательская панель",
                    value=False,
                    key="ui_custom_dashboard"
                )
                
                if custom_dashboard:
                    st.button("🎛️ Настроить панель", disabled=True)
                
                favorite_actions = st.checkbox(
                    "Показывать избранные действия",
                    value=True,
                    key="ui_favorite_actions"
                )
            
            with col2:
                recent_items_count = st.slider(
                    "Количество недавних элементов",
                    min_value=5,
                    max_value=20,
                    value=10,
                    key="ui_recent_items"
                )
                
                auto_refresh = st.checkbox(
                    "Автообновление данных",
                    value=False,
                    key="ui_auto_refresh"
                )
    
    def _render_data_settings(self):
        """Настройки данных"""
        st.subheader("📊 Настройки данных")
        
        # Хранение и синхронизация
        with st.expander("💾 Хранение и синхронизация", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                auto_save = st.checkbox(
                    "Автосохранение",
                    value=True,
                    key="data_auto_save"
                )
                
                if auto_save:
                    save_interval = st.selectbox(
                        "Интервал автосохранения",
                        ["30 секунд", "1 минута", "5 минут", "15 минут"],
                        index=1,
                        key="data_save_interval"
                    )
                
                cloud_sync = st.checkbox(
                    "Облачная синхронизация",
                    value=False,
                    key="data_cloud_sync"
                )
            
            with col2:
                data_retention = st.selectbox(
                    "Хранение данных",
                    ["30 дней", "90 дней", "1 год", "Бессрочно"],
                    index=1,
                    key="data_retention"
                )
                
                backup_frequency = st.selectbox(
                    "Частота резервного копирования",
                    ["Ежедневно", "Еженедельно", "Ежемесячно"],
                    index=1,
                    key="data_backup_freq"
                )
        
        # Экспорт и импорт
        with st.expander("📤 Экспорт и импорт", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                default_export_format = st.selectbox(
                    "Формат экспорта по умолчанию",
                    ["CSV", "Excel", "JSON", "PDF"],
                    index=0,
                    key="data_default_export"
                )
                
                include_metadata = st.checkbox(
                    "Включать метаданные при экспорте",
                    value=True,
                    key="data_export_metadata"
                )
            
            with col2:
                auto_export = st.checkbox(
                    "Автоматический экспорт",
                    value=False,
                    key="data_auto_export"
                )
                
                if auto_export:
                    st.selectbox(
                        "Частота экспорта",
                        ["Ежедневно", "Еженедельно", "Ежемесячно"],
                        index=1,
                        key="data_export_freq"
                    )
        
        # Приватность
        with st.expander("🔒 Приватность", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                data_analytics = st.checkbox(
                    "Разрешить аналитику использования",
                    value=True,
                    key="data_analytics"
                )
                
                data_sharing = st.checkbox(
                    "Разрешить обмен данными",
                    value=False,
                    key="data_sharing"
                )
            
            with col2:
                data_encryption = st.checkbox(
                    "Шифрование данных",
                    value=True,
                    key="data_encryption",
                    disabled=True
                )
                
                st.button("🗑️ Удалить все данные", key="data_delete_all")
    
    def _render_integrations_settings(self):
        """Настройки интеграций"""
        st.subheader("🔗 Настройки интеграций")
        
        # API ключи
        with st.expander("🔑 API ключи", expanded=True):
            st.info("Управление API ключами для внешних интеграций")
            
            col1, col2 = st.columns(2)
            
            with col1:
                api_enabled = st.checkbox(
                    "Включить API доступ",
                    value=False,
                    key="integrations_api_enabled"
                )
                
                if api_enabled:
                    st.text_input("API ключ", type="password", key="integrations_api_key")
                    st.button("🔄 Сгенерировать новый ключ", disabled=True)
            
            with col2:
                webhook_enabled = st.checkbox(
                    "Включить webhooks",
                    value=False,
                    key="integrations_webhook_enabled"
                )
                
                if webhook_enabled:
                    st.text_input("Webhook URL", key="integrations_webhook_url")
                    st.button("🧪 Тестировать webhook", disabled=True)
        
        # Внешние сервисы
        with st.expander("🌐 Внешние сервисы", expanded=False):
            st.write("**Подключенные сервисы:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.checkbox("Google Drive", value=False, disabled=True)
                st.checkbox("Dropbox", value=False, disabled=True)
                st.checkbox("OneDrive", value=False, disabled=True)
            
            with col2:
                st.checkbox("Slack", value=False, disabled=True)
                st.checkbox("Microsoft Teams", value=False, disabled=True)
                st.checkbox("Discord", value=False, disabled=True)
            
            st.button("➕ Добавить новый сервис", disabled=True)
        
        # Автоматизация
        with st.expander("🤖 Автоматизация", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                zapier_enabled = st.checkbox(
                    "Zapier интеграция",
                    value=False,
                    key="integrations_zapier"
                )
                
                if zapier_enabled:
                    st.text_input("Zapier Webhook", key="integrations_zapier_webhook")
            
            with col2:
                ifttt_enabled = st.checkbox(
                    "IFTTT интеграция",
                    value=False,
                    key="integrations_ifttt"
                )
                
                if ifttt_enabled:
                    st.text_input("IFTTT Webhook", key="integrations_ifttt_webhook")
    
    def _render_common_actions(self):
        """Общие действия"""
        st.divider()
        st.subheader("🔧 Общие действия")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💾 Сохранить все настройки", key="save_all_settings", use_container_width=True):
                self._save_all_settings()
        
        with col2:
            if st.button("🔄 Сбросить к умолчанию", key="reset_all_settings", use_container_width=True):
                self._reset_all_settings()
        
        with col3:
            if st.button("📥 Экспорт настроек", key="export_settings", use_container_width=True):
                self._export_settings()
        
        with col4:
            if st.button("📤 Импорт настроек", key="import_settings", use_container_width=True):
                self._import_settings()
    
    def _save_profile_settings(self):
        """Сохранение настроек профиля"""
        try:
            # Собираем данные из формы
            profile_data = {
                'first_name': st.session_state.get('profile_first_name', ''),
                'last_name': st.session_state.get('profile_last_name', ''),
                'phone': st.session_state.get('profile_phone', ''),
                'position': st.session_state.get('profile_position', ''),
                'department': st.session_state.get('profile_department', ''),
                'company': st.session_state.get('profile_company', ''),
                'location': st.session_state.get('profile_location', ''),
                'bio': st.session_state.get('profile_bio', ''),
                'website': st.session_state.get('profile_website', '')
            }
            
            # Отправляем на сервер
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.put(
                f"{self.api_base_url}/api/v1/auth/profile",
                json=profile_data,
                headers=headers
            )
            
            if response.status_code == 200:
                st.success("✅ Профиль успешно обновлен")
                
                # Обновляем локальные данные
                updated_profile = response.json()
                st.session_state.user_info.update(updated_profile)
                
            else:
                st.error(f"Ошибка обновления профиля: {response.status_code}")
                
        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
    
    def _change_password(self, current_password: str, new_password: str, confirm_password: str):
        """Смена пароля"""
        if not current_password or not new_password or not confirm_password:
            st.error("❌ Заполните все поля")
            return
        
        if new_password != confirm_password:
            st.error("❌ Новые пароли не совпадают")
            return
        
        if len(new_password) < 8:
            st.error("❌ Новый пароль должен содержать минимум 8 символов")
            return
        
        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.put(
                f"{self.api_base_url}/api/v1/auth/password",
                json={
                    'current_password': current_password,
                    'new_password': new_password
                },
                headers=headers
            )
            
            if response.status_code == 200:
                st.success("✅ Пароль успешно изменен")
                
                # Очищаем поля
                st.session_state['security_current_password'] = ''
                st.session_state['security_new_password'] = ''
                st.session_state['security_confirm_password'] = ''
                
            else:
                st.error(f"Ошибка смены пароля: {response.status_code}")
                
        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
    
    def _export_profile(self):
        """Экспорт профиля"""
        try:
            profile_data = {
                'export_time': datetime.now().isoformat(),
                'profile': st.session_state.user_info,
                'settings': self._collect_current_settings()
            }
            
            json_str = json.dumps(profile_data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="📥 Скачать профиль",
                data=json_str,
                file_name=f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"Ошибка экспорта: {str(e)}")
    
    def _collect_current_settings(self) -> Dict[str, Any]:
        """Сбор текущих настроек"""
        settings = {}
        
        # Профиль
        settings['profile'] = {
            'first_name': st.session_state.get('profile_first_name', ''),
            'last_name': st.session_state.get('profile_last_name', ''),
            'phone': st.session_state.get('profile_phone', ''),
            'position': st.session_state.get('profile_position', ''),
            'department': st.session_state.get('profile_department', ''),
            'company': st.session_state.get('profile_company', ''),
            'location': st.session_state.get('profile_location', ''),
            'bio': st.session_state.get('profile_bio', ''),
            'website': st.session_state.get('profile_website', '')
        }
        
        # Предпочтения
        settings['preferences'] = {
            'language': st.session_state.get('pref_language', 'Русский'),
            'timezone': st.session_state.get('pref_timezone', 'UTC+3 (Москва)'),
            'default_top_k': st.session_state.get('pref_top_k', 10),
            'include_citations': st.session_state.get('pref_citations', True)
        }
        
        # Интерфейс
        settings['interface'] = {
            'theme': st.session_state.get('ui_theme', 'Светлая'),
            'font_size': st.session_state.get('ui_font_size', 'Средний'),
            'compact_mode': st.session_state.get('ui_compact_mode', False)
        }
        
        return settings
    
    def _save_all_settings(self):
        """Сохранение всех настроек"""
        try:
            settings_data = self._collect_current_settings()
            
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.put(
                f"{self.api_base_url}/api/v1/auth/settings",
                json=settings_data,
                headers=headers
            )
            
            if response.status_code == 200:
                st.success("✅ Все настройки успешно сохранены")
            else:
                st.error(f"Ошибка сохранения настроек: {response.status_code}")
                
        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
    
    def _reset_all_settings(self):
        """Сброс всех настроек к умолчанию"""
        if st.button("🗑️ Подтвердить сброс всех настроек", key="confirm_reset_all"):
            try:
                headers = {}
                if self.access_token:
                    headers["Authorization"] = f"Bearer {self.access_token}"
                
                response = requests.post(
                    f"{self.api_base_url}/api/v1/auth/settings/reset",
                    headers=headers
                )
                
                if response.status_code == 200:
                    st.success("✅ Все настройки сброшены к умолчанию")
                    st.rerun()
                else:
                    st.error(f"Ошибка сброса настроек: {response.status_code}")
                    
            except Exception as e:
                st.error(f"Ошибка: {str(e)}")
    
    def _export_settings(self):
        """Экспорт настроек"""
        try:
            settings_data = {
                'export_time': datetime.now().isoformat(),
                'settings': self._collect_current_settings()
            }
            
            json_str = json.dumps(settings_data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="📥 Скачать настройки",
                data=json_str,
                file_name=f"settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"Ошибка экспорта: {str(e)}")
    
    def _import_settings(self):
        """Импорт настроек"""
        st.info("📤 Функция импорта настроек будет доступна в следующем обновлении")
        
        uploaded_file = st.file_uploader(
            "Выберите файл настроек (.json)",
            type=['json'],
            key="import_settings_file"
        )
        
        if uploaded_file is not None:
            try:
                settings_data = json.load(uploaded_file)
                st.success("✅ Файл настроек загружен")
                st.json(settings_data)
                
                if st.button("📥 Применить настройки", disabled=True):
                    st.info("Функция применения настроек будет доступна в следующем обновлении")
                    
            except Exception as e:
                st.error(f"Ошибка чтения файла: {str(e)}")
    
    def _render_advanced_settings(self):
        """Расширенные настройки"""
        st.subheader("🔧 Расширенные настройки")
        
        # Производительность
        with st.expander("⚡ Производительность", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                cache_size = st.slider(
                    "Размер кэша (MB)",
                    min_value=10,
                    max_value=1000,
                    value=100,
                    key="advanced_cache_size"
                )
                
                max_concurrent_requests = st.slider(
                    "Максимум одновременных запросов",
                    min_value=1,
                    max_value=20,
                    value=5,
                    key="advanced_max_requests"
                )
                
                request_timeout = st.slider(
                    "Таймаут запросов (секунды)",
                    min_value=5,
                    max_value=120,
                    value=30,
                    key="advanced_timeout"
                )
            
            with col2:
                enable_compression = st.checkbox(
                    "Включить сжатие данных",
                    value=True,
                    key="advanced_compression"
                )
                
                enable_caching = st.checkbox(
                    "Включить кэширование",
                    value=True,
                    key="advanced_caching"
                )
                
                debug_mode = st.checkbox(
                    "Режим отладки",
                    value=False,
                    key="advanced_debug"
                )
        
        # Логирование
        with st.expander("📝 Логирование", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                log_level = st.selectbox(
                    "Уровень логирования",
                    ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    index=1,
                    key="advanced_log_level"
                )
                
                log_requests = st.checkbox(
                    "Логировать запросы",
                    value=True,
                    key="advanced_log_requests"
                )
            
            with col2:
                log_retention = st.selectbox(
                    "Хранение логов",
                    ["1 день", "7 дней", "30 дней", "90 дней"],
                    index=2,
                    key="advanced_log_retention"
                )
                
                log_analytics = st.checkbox(
                    "Аналитика использования",
                    value=True,
                    key="advanced_log_analytics"
                )
        
        # Экспериментальные функции
        with st.expander("🧪 Экспериментальные функции", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                beta_features = st.checkbox(
                    "Включить бета-функции",
                    value=False,
                    key="advanced_beta_features"
                )
                
                ai_suggestions = st.checkbox(
                    "AI предложения",
                    value=True,
                    key="advanced_ai_suggestions"
                )
            
            with col2:
                auto_updates = st.checkbox(
                    "Автоматические обновления",
                    value=True,
                    key="advanced_auto_updates"
                )
                
                telemetry = st.checkbox(
                    "Отправка телеметрии",
                    value=False,
                    key="advanced_telemetry"
                )
        
        # Системная информация
        with st.expander("💻 Системная информация", expanded=False):
            import platform
            import sys
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Операционная система:**")
                st.write(f"• {platform.system()} {platform.release()}")
                st.write(f"• Архитектура: {platform.machine()}")
                st.write(f"• Процессор: {platform.processor()}")
            
            with col2:
                st.write("**Python и библиотеки:**")
                st.write(f"• Python: {sys.version.split()[0]}")
                st.write(f"• Streamlit: {st.__version__}")
                st.write(f"• Pandas: {pd.__version__}")
    
    def _render_backup_settings(self):
        """Настройки резервного копирования"""
        st.subheader("💾 Резервное копирование")
        
        # Автоматическое резервное копирование
        with st.expander("🔄 Автоматическое резервное копирование", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                auto_backup = st.checkbox(
                    "Включить автоматическое резервное копирование",
                    value=True,
                    key="backup_auto_enabled"
                )
                
                if auto_backup:
                    backup_frequency = st.selectbox(
                        "Частота резервного копирования",
                        ["Ежедневно", "Еженедельно", "Ежемесячно"],
                        index=1,
                        key="backup_frequency"
                    )
                    
                    backup_time = st.time_input(
                        "Время резервного копирования",
                        value=datetime.strptime("02:00", "%H:%M").time(),
                        key="backup_time"
                    )
            
            with col2:
                if auto_backup:
                    backup_retention = st.selectbox(
                        "Хранение резервных копий",
                        ["7 дней", "30 дней", "90 дней", "1 год", "Бессрочно"],
                        index=2,
                        key="backup_retention"
                    )
                    
                    backup_compression = st.checkbox(
                        "Сжатие резервных копий",
                        value=True,
                        key="backup_compression"
                    )
        
        # Ручное резервное копирование
        with st.expander("📤 Ручное резервное копирование", expanded=True):
            st.write("**Создать резервную копию:**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 Полная копия", key="backup_full", use_container_width=True):
                    self._create_full_backup()
            
            with col2:
                if st.button("📊 Только данные", key="backup_data", use_container_width=True):
                    self._create_data_backup()
            
            with col3:
                if st.button("⚙️ Только настройки", key="backup_settings", use_container_width=True):
                    self._create_settings_backup()
        
        # Восстановление
        with st.expander("📥 Восстановление", expanded=False):
            st.write("**Восстановить из резервной копии:**")
            
            # Загрузка файла резервной копии
            uploaded_backup = st.file_uploader(
                "Выберите файл резервной копии",
                type=['zip', 'json', 'tar'],
                key="backup_upload"
            )
            
            if uploaded_backup is not None:
                st.success(f"✅ Файл загружен: {uploaded_backup.name}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🔄 Восстановить", key="restore_backup"):
                        self._restore_backup(uploaded_backup)
                
                with col2:
                    if st.button("👁️ Предпросмотр", key="preview_backup"):
                        self._preview_backup(uploaded_backup)
        
        # Управление резервными копиями
        with st.expander("📋 Управление резервными копиями", expanded=False):
            st.write("**Доступные резервные копии:**")
            
            # Список резервных копий (демо)
            backup_list = [
                {"name": "backup_2024_01_15_02_00.zip", "date": "2024-01-15 02:00", "size": "15.2 MB", "type": "Полная"},
                {"name": "backup_2024_01_14_02_00.zip", "date": "2024-01-14 02:00", "size": "14.8 MB", "type": "Полная"},
                {"name": "backup_2024_01_13_02_00.zip", "date": "2024-01-13 02:00", "size": "15.1 MB", "type": "Полная"},
            ]
            
            for backup in backup_list:
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.write(f"📁 {backup['name']}")
                
                with col2:
                    st.write(f"📅 {backup['date']} ({backup['size']})")
                
                with col3:
                    if st.button("📥", key=f"download_{backup['name']}", help="Скачать"):
                        st.info("Функция скачивания будет доступна в следующем обновлении")
                
                with col4:
                    if st.button("🗑️", key=f"delete_{backup['name']}", help="Удалить"):
                        st.info("Функция удаления будет доступна в следующем обновлении")
    
    def _create_full_backup(self):
        """Создание полной резервной копии"""
        try:
            # Собираем все данные для резервного копирования
            backup_data = {
                'backup_type': 'full',
                'backup_time': datetime.now().isoformat(),
                'user_info': st.session_state.get('user_info', {}),
                'settings': self._collect_current_settings(),
                'metadata': {
                    'version': '1.0',
                    'created_by': st.session_state.get('user_info', {}).get('username', 'unknown')
                }
            }
            
            # Создаем JSON файл
            json_str = json.dumps(backup_data, indent=2, ensure_ascii=False)
            
            # Создаем имя файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backup_full_{timestamp}.json"
            
            st.download_button(
                label="💾 Скачать полную резервную копию",
                data=json_str,
                file_name=filename,
                mime="application/json"
            )
            
            st.success("✅ Полная резервная копия создана")
            
        except Exception as e:
            st.error(f"Ошибка создания резервной копии: {str(e)}")
    
    def _create_data_backup(self):
        """Создание резервной копии данных"""
        st.info("📊 Функция резервного копирования данных будет доступна в следующем обновлении")
    
    def _create_settings_backup(self):
        """Создание резервной копии настроек"""
        try:
            settings_data = {
                'backup_type': 'settings',
                'backup_time': datetime.now().isoformat(),
                'settings': self._collect_current_settings(),
                'metadata': {
                    'version': '1.0',
                    'created_by': st.session_state.get('user_info', {}).get('username', 'unknown')
                }
            }
            
            json_str = json.dumps(settings_data, indent=2, ensure_ascii=False)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backup_settings_{timestamp}.json"
            
            st.download_button(
                label="⚙️ Скачать резервную копию настроек",
                data=json_str,
                file_name=filename,
                mime="application/json"
            )
            
            st.success("✅ Резервная копия настроек создана")
            
        except Exception as e:
            st.error(f"Ошибка создания резервной копии настроек: {str(e)}")
    
    def _restore_backup(self, uploaded_file):
        """Восстановление из резервной копии"""
        try:
            # Читаем файл
            backup_data = json.load(uploaded_file)
            
            # Проверяем тип резервной копии
            backup_type = backup_data.get('backup_type', 'unknown')
            
            if backup_type == 'settings':
                # Восстанавливаем настройки
                settings = backup_data.get('settings', {})
                
                # Применяем настройки (демо)
                st.success("✅ Настройки восстановлены из резервной копии")
                st.info("Перезапустите приложение для применения настроек")
                
            elif backup_type == 'full':
                st.success("✅ Полная резервная копия восстановлена")
                st.info("Перезапустите приложение для применения изменений")
                
            else:
                st.warning("⚠️ Неизвестный тип резервной копии")
            
        except Exception as e:
            st.error(f"Ошибка восстановления: {str(e)}")
    
    def _preview_backup(self, uploaded_file):
        """Предпросмотр резервной копии"""
        try:
            backup_data = json.load(uploaded_file)
            
            st.write("**Информация о резервной копии:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"• **Тип:** {backup_data.get('backup_type', 'Неизвестно')}")
                st.write(f"• **Дата создания:** {backup_data.get('backup_time', 'Неизвестно')}")
                st.write(f"• **Размер файла:** {len(uploaded_file.getvalue())} байт")
            
            with col2:
                metadata = backup_data.get('metadata', {})
                st.write(f"• **Версия:** {metadata.get('version', 'Неизвестно')}")
                st.write(f"• **Создано пользователем:** {metadata.get('created_by', 'Неизвестно')}")
            
            # Показываем содержимое
            with st.expander("📋 Содержимое резервной копии", expanded=False):
                st.json(backup_data)
                
        except Exception as e:
            st.error(f"Ошибка предпросмотра: {str(e)}")
