from flask import Flask

from app.controllers import auth, health, queue, restaurants, tables


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(restaurants.bp)
    app.register_blueprint(tables.restaurant_tables_bp)
    app.register_blueprint(tables.tables_bp)
    app.register_blueprint(queue.restaurant_queue_bp)
    app.register_blueprint(queue.queue_bp)


__all__ = ["register_blueprints"]
