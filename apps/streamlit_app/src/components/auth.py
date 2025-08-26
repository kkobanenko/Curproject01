"""
Компонент аутентификации
"""
import streamlit as st
import requests
from typing import Dict, Any, Optional


class LoginForm:
    """Форма входа в систему"""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
    
    def render(self) -> Optional[Dict[str, Any]]:
        """Отображение формы входа"""
        
        # Центрированный заголовок
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h1>🔐 RAG Platform</h1>
            <p style="font-size: 1.2rem; color: #666;">Войдите в систему для доступа к платформе</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Форма входа
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.form("login_form", clear_on_submit=False):
                st.subheader("Вход в систему")
                
                username = st.text_input(
                    "Имя пользователя",
                    placeholder="Введите имя пользователя",
                    help="Используйте admin/admin123 для демо"
                )
                
                password = st.text_input(
                    "Пароль",
                    type="password",
                    placeholder="Введите пароль",
                    help="Введите ваш пароль"
                )
                
                # Дополнительные опции
                col1, col2 = st.columns(2)
                
                with col1:
                    remember_me = st.checkbox("Запомнить меня")
                
                with col2:
                    # Кнопка "Забыли пароль?" должна быть вне формы
                    pass
                
                # Кнопки
                col1, col2 = st.columns(2)
                
                with col1:
                    submitted = st.form_submit_button("🔐 Войти", use_container_width=True)
                
                with col2:
                    demo_mode = st.form_submit_button("👤 Демо режим", use_container_width=True)
                    if demo_mode:
                        username = "admin"
                        password = "admin123"
                        submitted = True
                
                # Обработка отправки
                if submitted and username and password:
                    return self._authenticate(username, password, remember_me)
        
        # Кнопка "Забыли пароль?" вне формы
        forgot_password = st.button("Забыли пароль?", type="secondary")
        if forgot_password:
            st.info("Функция восстановления пароля в разработке")
        
        return None
    
    def _authenticate(self, username: str, password: str, remember_me: bool) -> Optional[Dict[str, Any]]:
        """Аутентификация пользователя"""
        try:
            with st.spinner("Выполняется вход..."):
                response = requests.post(
                    f"{self.api_base_url}/api/v1/auth/login",
                    json={"username": username, "password": password},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Сохраняем в сессии
                    if remember_me:
                        st.session_state.remember_me = True
                    
                    st.success("✅ Вход выполнен успешно!")
                    return result
                else:
                    error_msg = response.json().get("detail", "Неизвестная ошибка")
                    st.error(f"❌ Ошибка входа: {error_msg}")
                    return None
                    
        except requests.exceptions.Timeout:
            st.error("⏱️ Превышено время ожидания. Проверьте соединение.")
            return None
        except requests.exceptions.ConnectionError:
            st.error("🔌 Ошибка соединения. Проверьте доступность API.")
            return None
        except Exception as e:
            st.error(f"❌ Неожиданная ошибка: {str(e)}")
            return None


class UserProfile:
    """Профиль пользователя"""
    
    def __init__(self, user_info: Dict[str, Any]):
        self.user_info = user_info
    
    def render_sidebar(self):
        """Отображение профиля в боковой панели"""
        st.divider()
        st.subheader("👤 Профиль")
        
        user = self.user_info
        
        if not user:
            st.warning("⚠️ Информация о пользователе недоступна")
            return
        
        # Основная информация
        st.write(f"**Имя:** {user.get('username', 'N/A')}")
        st.write(f"**Email:** {user.get('email', 'N/A')}")
        st.write(f"**Тенант:** {user.get('tenant_id', 'N/A')}")
        st.write(f"**Роль:** {user.get('role_id', 'N/A')}")
        
        # Дополнительная информация
        if user.get('created_at'):
            st.write(f"**Дата регистрации:** {user['created_at']}")
        
        if user.get('last_login'):
            st.write(f"**Последний вход:** {user['last_login']}")
        
        # Кнопки действий
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✏️ Редактировать", use_container_width=True):
                st.info("Функция редактирования профиля в разработке")
        
        with col2:
            if st.button("🔑 Сменить пароль", use_container_width=True):
                st.info("Функция смены пароля в разработке")
    
    def render_header(self):
        """Отображение профиля в заголовке"""
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.title("🔍 RAG Platform")
            st.markdown("Платформа для семантического поиска и анализа документов")
        
        with col2:
            if self.user_info:
                username = self.user_info.get('username', 'Пользователь')
                role_id = self.user_info.get('role_id', 0)
                
                # Определяем роль
                role_name = "Администратор" if role_id == 1 else "Пользователь"
                role_icon = "👑" if role_id == 1 else "👤"
                
                st.info(f"{role_icon} {username}\n**{role_name}**")
        
        with col3:
            if st.button("🚪 Выйти", use_container_width=True):
                st.session_state.clear()
                st.rerun()
    
    def render_settings_page(self):
        """Отображение страницы настроек профиля"""
        st.header("⚙️ Настройки профиля")
        
        user = self.user_info
        
        if not user:
            st.warning("⚠️ Информация о пользователе недоступна")
            return
        
        # Информация о профиле
        st.subheader("👤 Информация о профиле")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Имя пользователя:** {user.get('username', 'N/A')}")
            st.write(f"**Email:** {user.get('email', 'N/A')}")
        
        with col2:
            st.write(f"**Тенант:** {user.get('tenant_id', 'N/A')}")
            st.write(f"**Роль:** {user.get('role_id', 'N/A')}")
        
        st.divider()
        
        # Настройки безопасности
        st.subheader("🔒 Безопасность")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔑 Сменить пароль", use_container_width=True):
                st.info("Функция смены пароля в разработке")
        
        with col2:
            if st.button("🔐 Двухфакторная аутентификация", use_container_width=True):
                st.info("Функция 2FA в разработке")
        
        st.divider()
        
        # Настройки уведомлений
        st.subheader("🔔 Уведомления")
        
        email_notifications = st.checkbox("Email уведомления", value=True)
        push_notifications = st.checkbox("Push уведомления", value=False)
        
        if st.button("💾 Сохранить настройки"):
            st.success("✅ Настройки сохранены")
        
        st.divider()
        
        # Экспорт данных
        st.subheader("📤 Экспорт данных")
        
        if st.button("📊 Экспорт истории поиска"):
            st.info("Функция экспорта в разработке")
        
        if st.button("💬 Экспорт истории чата"):
            st.info("Функция экспорта в разработке")
        
        # Удаление аккаунта
        st.divider()
        st.subheader("🗑️ Удаление аккаунта")
        
        st.warning("⚠️ Это действие необратимо!")
        
        if st.button("🗑️ Удалить аккаунт", type="secondary"):
            st.error("Функция удаления аккаунта в разработке")
