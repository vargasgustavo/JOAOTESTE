from .auth_controller import auth_bp
from .dashboard_controller import dashboard_bp
from .queue_controller import queue_bp
from .restaurant_controller import restaurant_bp
from .table_controller import table_bp

__all__ = ["auth_bp", "restaurant_bp", "table_bp", "queue_bp", "dashboard_bp"]
