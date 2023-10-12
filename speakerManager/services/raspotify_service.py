class RaspotifyService:
    _status: bool
    _is_active: bool

    def __init__(self, status = False, is_active = False) -> None:
        self._status = status
        self._is_active = is_active

    def update_status(self,message_recieved) -> bool:
        new_active_state = None
        self._status = message_recieved
        if(message_recieved=="stopped"):
            new_active_state = False
        elif(message_recieved == "started" or message_recieved == "playing" or message_recieved == "paused" or message_recieved == "changed"):
            new_active_state = True

        if(new_active_state is not None and new_active_state != self._is_active):
            self._is_active = new_active_state
            return True
        return False

    def get_status(self) -> bool:
        return self._status
    
    def is_active(self) -> bool:
        return self._is_active