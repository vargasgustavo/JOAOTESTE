from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    @abstractmethod
    def send(self, recipient_phone: str, message: str) -> bool:
        """Send a notification. Returns True if successful."""
        ...
