from .event_service import EventService


class WaitTimeService:
    def __init__(self, session=None):
        self._event_service = EventService(session)

    def estimate_wait(self, position: int) -> int:
        avg_turn = self._event_service.get_avg_turn_time_minutes()
        return max(1, round(position * avg_turn))
