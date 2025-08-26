"""
Компонент чата с RAG системой
"""
import streamlit as st
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class ChatInterface:
    """Интерфейс чата с RAG системой"""
    
    def __init__(self, api_base_url: str, access_token: str = None):
        self.api_base_url = api_base_url
        self.access_token = access_token
    
    def render(self):
        """Отображение интерфейса чата"""
        st.header("💬 Чат с документами")
        
        # Параметры чата
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            user_message = st.text_input(
                "Ваше сообщение",
                placeholder="Задайте вопрос о документах...",
                key="user_input",
                help="Задайте любой вопрос, и система найдет релевантную информацию в документах"
            )
        
        with col2:
            top_k = st.number_input(
                "Контекст", 
                min_value=1, 
                max_value=20, 
                value=5,
                help="Количество релевантных фрагментов для контекста"
            )
        
        with col3:
            temperature = st.slider(
                "Креативность",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="Высокие значения = более креативные ответы"
            )
        
        # Дополнительные параметры
        with st.expander("🔧 Дополнительные параметры"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                max_length = st.number_input(
                    "Максимальная длина ответа",
                    min_value=100,
                    max_value=2000,
                    value=500,
                    step=100
                )
            
            with col2:
                include_citations = st.checkbox("Включать цитаты", value=True)
                include_sources = st.checkbox("Показывать источники", value=True)
            
            with col3:
                conversation_mode = st.selectbox(
                    "Режим беседы",
                    ["single", "conversation"],
                    format_func=lambda x: {
                        "single": "Одиночный вопрос",
                        "conversation": "Продолжение беседы"
                    }[x]
                )
        
        # Кнопка отправки
        if st.button("💬 Отправить", use_container_width=True) and user_message:
            self._send_message(
                message=user_message,
                top_k=top_k,
                temperature=temperature,
                max_length=max_length,
                include_citations=include_citations,
                include_sources=include_sources,
                conversation_mode=conversation_mode
            )
        
        # Отображение истории чата
        self._render_chat_history()
    
    def _send_message(self, **kwargs):
        """Отправка сообщения"""
        # Добавляем сообщение пользователя в историю
        st.session_state.chat_history.append({
            "role": "user",
            "content": kwargs["message"],
            "timestamp": datetime.now(),
            "parameters": {
                "top_k": kwargs["top_k"],
                "temperature": kwargs["temperature"],
                "max_length": kwargs["max_length"]
            }
        })
        
        # Получаем ответ от RAG
        with st.spinner("🤖 Генерируется ответ..."):
            response = self._get_rag_response(
                question=kwargs["message"],
                top_k=kwargs["top_k"],
                temperature=kwargs["temperature"],
                max_length=kwargs["max_length"],
                include_citations=kwargs["include_citations"],
                conversation_mode=kwargs["conversation_mode"]
            )
            
            if "error" in response:
                st.error(f"❌ Ошибка чата: {response['error']}")
                
                # Добавляем ошибку в историю
                st.session_state.chat_history.append({
                    "role": "error",
                    "content": f"Ошибка: {response['error']}",
                    "timestamp": datetime.now()
                })
            else:
                # Добавляем ответ в историю
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response.get('answer', 'Ответ не получен'),
                    "timestamp": datetime.now(),
                    "citations": response.get('citations', []),
                    "sources": response.get('sources', []),
                    "confidence": response.get('confidence', 0.0),
                    "processing_time": response.get('processing_time', 0.0)
                })
                
                # Обновляем ID беседы
                if 'conversation_id' in response:
                    st.session_state.current_conversation = response['conversation_id']
        
        # Очищаем поле ввода и перезагружаем страницу
        st.rerun()
    
    def _get_rag_response(self, **kwargs) -> Dict[str, Any]:
        """Получение ответа от RAG системы"""
        try:
            # Формируем параметры запроса
            request_data = {
                "question": kwargs["question"],
                "top_k": kwargs["top_k"],
                "temperature": kwargs["temperature"],
                "max_length": kwargs["max_length"],
                "include_citations": kwargs["include_citations"]
            }
            
            # Добавляем ID беседы если режим conversation
            if kwargs["conversation_mode"] == "conversation" and st.session_state.current_conversation:
                request_data["conversation_id"] = st.session_state.current_conversation
            
            # Выполняем запрос
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/answers/generate",
                json=request_data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = response.json().get("detail", "Неизвестная ошибка")
                return {"error": f"Ошибка генерации ответа: {error_msg}"}
                
        except requests.exceptions.Timeout:
            return {"error": "Превышено время ожидания ответа"}
        except requests.exceptions.ConnectionError:
            return {"error": "Ошибка соединения с API"}
        except Exception as e:
            return {"error": f"Неожиданная ошибка: {str(e)}"}
    
    def _render_chat_history(self):
        """Отображение истории чата"""
        st.subheader("📚 История беседы")
        
        if not st.session_state.chat_history:
            st.info("💡 Начните беседу, отправив первое сообщение")
            return
        
        # Фильтры истории
        with st.expander("🔍 Фильтры истории"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                show_errors = st.checkbox("Показывать ошибки", value=False)
            
            with col2:
                min_confidence = st.slider(
                    "Минимальная уверенность",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.0,
                    step=0.1
                )
            
            with col3:
                if st.button("🗑️ Очистить историю"):
                    st.session_state.chat_history = []
                    st.session_state.current_conversation = None
                    st.rerun()
        
        # Отображение сообщений
        for i, message in enumerate(st.session_state.chat_history):
            # Пропускаем ошибки если не включен показ
            if message["role"] == "error" and not show_errors:
                continue
            
            # Пропускаем сообщения с низкой уверенностью
            if message.get("confidence", 1.0) < min_confidence:
                continue
            
            self._render_message(message, i)
        
        # Информация о беседе
        if st.session_state.current_conversation:
            st.info(f"🆔 ID беседы: {st.session_state.current_conversation}")
    
    def _render_message(self, message: Dict[str, Any], index: int):
        """Отображение отдельного сообщения"""
        role = message["role"]
        content = message["content"]
        timestamp = message.get("timestamp", datetime.now())
        
        # Определяем стиль сообщения
        if role == "user":
            st.chat_message("user").write(content)
            
            # Показываем параметры если есть
            if message.get("parameters"):
                params = message["parameters"]
                st.caption(f"Параметры: k={params['top_k']}, t={params['temperature']}, len={params['max_length']}")
        
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.write(content)
                
                # Показываем уверенность
                confidence = message.get("confidence", 0.0)
                if confidence > 0:
                    st.progress(confidence)
                    st.caption(f"Уверенность: {confidence:.1%}")
                
                # Показываем время обработки
                processing_time = message.get("processing_time", 0.0)
                if processing_time > 0:
                    st.caption(f"⏱️ Время обработки: {processing_time:.2f} сек")
                
                # Показываем цитаты
                citations = message.get("citations", [])
                if citations:
                    with st.expander("📖 Цитаты и источники"):
                        for citation in citations:
                            st.write(f"**{citation.get('source', 'N/A')}** (стр. {citation.get('page', 'N/A')})")
                            st.write(f"*{citation.get('text', '')}*")
                
                # Показываем источники
                sources = message.get("sources", [])
                if sources:
                    with st.expander("📚 Использованные документы"):
                        for source in sources:
                            st.write(f"- **{source.get('title', 'Без названия')}**")
                            st.write(f"  Тип: {source.get('type', 'N/A')}")
                            st.write(f"  Релевантность: {source.get('relevance', 0):.3f}")
                
                # Действия с ответом
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"👍 Полезно", key=f"like_{index}"):
                        st.success("✅ Спасибо за обратную связь!")
                
                with col2:
                    if st.button(f"👎 Не полезно", key=f"dislike_{index}"):
                        st.error("❌ Спасибо за обратную связь!")
                
                with col3:
                    if st.button(f"📋 Копировать", key=f"copy_{index}"):
                        st.success("✅ Ответ скопирован в буфер обмена")
                        st.session_state.copied_content = content
        
        elif role == "error":
            st.error(f"❌ {content}")
        
        # Временная метка
        st.caption(f"🕐 {timestamp.strftime('%H:%M:%S')}")
        
        # Разделитель между сообщениями
        if index < len(st.session_state.chat_history) - 1:
            st.divider()


class ChatHistory:
    """Управление историей чата"""
    
    def __init__(self):
        self.history = []
    
    def add_message(self, role: str, content: str, **kwargs):
        """Добавление сообщения в историю"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            **kwargs
        }
        self.history.append(message)
    
    def get_conversation_context(self, conversation_id: str = None, limit: int = 10) -> List[Dict]:
        """Получение контекста беседы для RAG"""
        if not conversation_id:
            # Возвращаем последние сообщения
            return self.history[-limit:] if self.history else []
        
        # TODO: Реализовать фильтрацию по ID беседы
        return self.history[-limit:] if self.history else []
    
    def export_history(self, format: str = "json") -> str:
        """Экспорт истории чата"""
        if format == "json":
            return json.dumps(self.history, default=str, ensure_ascii=False, indent=2)
        elif format == "txt":
            lines = []
            for msg in self.history:
                timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                role = "👤" if msg["role"] == "user" else "🤖"
                lines.append(f"[{timestamp}] {role}: {msg['content']}")
            return "\n".join(lines)
        else:
            return "Неподдерживаемый формат"
    
    def clear_history(self):
        """Очистка истории"""
        self.history.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики чата"""
        if not self.history:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "error_messages": 0,
                "total_tokens": 0,
                "avg_response_time": 0.0
            }
        
        user_messages = len([m for m in self.history if m["role"] == "user"])
        assistant_messages = len([m for m in self.history if m["role"] == "assistant"])
        error_messages = len([m for m in self.history if m["role"] == "error"])
        
        # Подсчет токенов (примерная оценка)
        total_tokens = sum(len(m["content"].split()) for m in self.history)
        
        # Среднее время ответа
        response_times = []
        for i, msg in enumerate(self.history):
            if msg["role"] == "assistant" and i > 0:
                prev_msg = self.history[i-1]
                if prev_msg["role"] == "user":
                    time_diff = (msg["timestamp"] - prev_msg["timestamp"]).total_seconds()
                    response_times.append(time_diff)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        return {
            "total_messages": len(self.history),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "error_messages": error_messages,
            "total_tokens": total_tokens,
            "avg_response_time": avg_response_time
        }
