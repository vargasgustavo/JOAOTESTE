import os
from app import create_app
from app.extensions import celery

app = create_app(os.environ.get("FLASK_ENV", "development"))
app.app_context().push()
