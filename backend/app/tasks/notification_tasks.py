import logging
from ..extensions import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
def send_queue_called_task(self, queue_entry_id: str, customer_name: str,
                           customer_phone: str, restaurant_name: str) -> None:
    try:
        from ..services.notifications.mock_provider import MockProvider
        provider = MockProvider()
        message = (
            f"Olá, {customer_name}! "
            f"Sua mesa está pronta no {restaurant_name}. "
            "Dirija-se à recepção."
        )
        provider.send(customer_phone, message)
        logger.info("Notification sent for queue entry %s", queue_entry_id)
    except Exception as exc:
        logger.exception("Failed to send notification for %s", queue_entry_id)
        raise self.retry(exc=exc)
