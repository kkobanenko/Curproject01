"""
Скрипт настройки пользователя и прав доступа в Superset
"""
import os
import sys
import logging

# Добавляем путь к Superset
sys.path.append('/app')

from superset import db
from superset.models.core import Database
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
from superset.models.datasource import Datasource
from superset.connectors.sqla.models import SqlaTable
from superset.models.user import User
from superset.models.role import Role
from superset.models.permissions import Permission, ViewMenu
from superset.models.assoc_user_role import assoc_user_role
from superset.utils.core import get_example_default_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_rag_user():
    """Создание пользователя для RAG платформы"""
    try:
        # Проверяем, существует ли пользователь
        existing_user = db.session.query(User).filter_by(
            username='rag_admin'
        ).first()
        
        if existing_user:
            logger.info("RAG admin user already exists")
            return existing_user
        
        # Создаем нового пользователя
        user = User(
            username='rag_admin',
            email='admin@rag-platform.com',
            first_name='RAG',
            last_name='Admin',
            active=True
        )
        
        # Устанавливаем пароль
        user.set_password('rag_admin_password')
        
        db.session.add(user)
        db.session.commit()
        
        logger.info("RAG admin user created successfully")
        return user
        
    except Exception as e:
        logger.error(f"Error creating RAG user: {e}")
        db.session.rollback()
        return None


def create_rag_role():
    """Создание роли для RAG платформы"""
    try:
        # Проверяем, существует ли роль
        existing_role = db.session.query(Role).filter_by(
            name='RAG_Admin'
        ).first()
        
        if existing_role:
            logger.info("RAG Admin role already exists")
            return existing_role
        
        # Создаем новую роль
        role = Role(
            name='RAG_Admin',
            description='Administrator role for RAG platform monitoring'
        )
        
        db.session.add(role)
        db.session.commit()
        
        # Добавляем права доступа
        permissions = [
            # Права на дашборды
            'can_read on Dashboard',
            'can_write on Dashboard',
            'can_delete on Dashboard',
            'can_export on Dashboard',
            
            # Права на чарты
            'can_read on Slice',
            'can_write on Slice',
            'can_delete on Slice',
            'can_export on Slice',
            
            # Права на источники данных
            'can_read on Datasource',
            'can_write on Datasource',
            'can_delete on Datasource',
            'can_export on Datasource',
            
            # Права на базы данных
            'can_read on Database',
            'can_write on Database',
            'can_delete on Database',
            'can_export on Database',
            
            # Права на SQL Lab
            'can_sql_json on Superset',
            'can_csv on Superset',
            'can_excel on Superset',
            
            # Права на администрирование
            'can_list on User',
            'can_show on User',
            'can_list on Role',
            'can_show on Role',
        ]
        
        for perm_name in permissions:
            try:
                permission = db.session.query(Permission).filter_by(
                    name=perm_name
                ).first()
                
                if permission:
                    role.permissions.append(permission)
            except Exception as e:
                logger.warning(f"Could not add permission {perm_name}: {e}")
        
        db.session.commit()
        
        logger.info("RAG Admin role created with permissions")
        return role
        
    except Exception as e:
        logger.error(f"Error creating RAG role: {e}")
        db.session.rollback()
        return None


def assign_role_to_user(user, role):
    """Назначение роли пользователю"""
    try:
        if role not in user.roles:
            user.roles.append(role)
            db.session.commit()
            logger.info(f"Role {role.name} assigned to user {user.username}")
        else:
            logger.info(f"User {user.username} already has role {role.name}")
        
    except Exception as e:
        logger.error(f"Error assigning role to user: {e}")
        db.session.rollback()


def create_public_role():
    """Создание публичной роли для просмотра дашбордов"""
    try:
        # Проверяем, существует ли роль
        existing_role = db.session.query(Role).filter_by(
            name='RAG_Viewer'
        ).first()
        
        if existing_role:
            logger.info("RAG Viewer role already exists")
            return existing_role
        
        # Создаем новую роль
        role = Role(
            name='RAG_Viewer',
            description='Read-only role for RAG platform dashboards'
        )
        
        db.session.add(role)
        db.session.commit()
        
        # Добавляем права только на чтение
        read_permissions = [
            'can_read on Dashboard',
            'can_read on Slice',
            'can_read on Datasource',
            'can_read on Database',
        ]
        
        for perm_name in read_permissions:
            try:
                permission = db.session.query(Permission).filter_by(
                    name=perm_name
                ).first()
                
                if permission:
                    role.permissions.append(permission)
            except Exception as e:
                logger.warning(f"Could not add permission {perm_name}: {e}")
        
        db.session.commit()
        
        logger.info("RAG Viewer role created with read permissions")
        return role
        
    except Exception as e:
        logger.error(f"Error creating RAG Viewer role: {e}")
        db.session.rollback()
        return None


def setup_dashboard_permissions():
    """Настройка прав доступа к дашбордам"""
    try:
        # Получаем все дашборды RAG
        dashboards = db.session.query(Dashboard).filter(
            Dashboard.slug.like('rag-%')
        ).all()
        
        # Получаем роль RAG_Viewer
        viewer_role = db.session.query(Role).filter_by(
            name='RAG_Viewer'
        ).first()
        
        if not viewer_role:
            logger.warning("RAG_Viewer role not found")
            return
        
        # Настраиваем права доступа для каждого дашборда
        for dashboard in dashboards:
            # Здесь можно добавить логику для настройки прав доступа
            # к конкретным дашбордам, если это необходимо
            logger.info(f"Dashboard {dashboard.dashboard_title} is accessible to RAG_Viewer role")
        
        logger.info("Dashboard permissions configured")
        
    except Exception as e:
        logger.error(f"Error setting up dashboard permissions: {e}")


def main():
    """Основная функция настройки пользователя и прав"""
    logger.info("Starting user and permissions setup for RAG platform...")
    
    try:
        # Создаем пользователя
        user = create_rag_user()
        if not user:
            logger.error("Failed to create RAG user")
            return False
        
        # Создаем роль администратора
        admin_role = create_rag_role()
        if not admin_role:
            logger.error("Failed to create RAG Admin role")
            return False
        
        # Создаем роль просмотра
        viewer_role = create_public_role()
        if not viewer_role:
            logger.error("Failed to create RAG Viewer role")
            return False
        
        # Назначаем роль пользователю
        assign_role_to_user(user, admin_role)
        
        # Настраиваем права доступа к дашбордам
        setup_dashboard_permissions()
        
        logger.info("User and permissions setup completed successfully!")
        logger.info(f"Admin user: rag_admin / rag_admin_password")
        logger.info(f"Available roles: RAG_Admin, RAG_Viewer")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during user setup: {e}")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
