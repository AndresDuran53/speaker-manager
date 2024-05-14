from datetime import datetime
from utils.custom_logging import CustomLogging

class LibreSpotService:
    _audio_id: str = "spotifyPlaying"
    _status: bool
    _is_active: bool
    _last_modified: datetime

    def __init__(self, status = "stop", is_active = False, logger=CustomLogging("logs/librespot.log")) -> None:
        self.logger = logger
        self.logger.info("Creating LibreSpot Service...")
        self._status = status
        self._is_active = is_active
        self._last_modified = datetime.now()

    def update_status(self, message_recieved: str) -> bool:
        new_active_state = None
        self._status = message_recieved
        if(message_recieved=="stop"):
            new_active_state = False
        elif(message_recieved == "start" or message_recieved == "play" or message_recieved == "pause" or message_recieved == "change"):
            new_active_state = True

        if(new_active_state is not None and new_active_state != self._is_active):
            self._is_active = new_active_state
            self._last_modified = datetime.now()
            self.logger.info(f"New LibreSpot Status: {new_active_state}")
            return True
        return False
    
    def get_audio_id(self) -> str:
        return self._audio_id

    def get_status(self) -> bool:
        return self._status
    
    def is_active(self) -> bool:
        return self._is_active
    
    def get_last_modified(self) -> datetime:
        return self._last_modified
    
    def activity_status_timed_out(self) -> bool:
        if(self._is_active and self._status != "start" and self._status != "play"):
            current_time = datetime.now()
            time_difference = current_time - self._last_modified
            if time_difference.total_seconds() >= 3600:
                self.execute_time_out()
                return True
        return False
    
    def execute_time_out(self):
        self._status = "stop"
        self._is_active = False
