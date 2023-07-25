class Speaker():
    id: str

    def __init__(self,id): self.id = id
        
    def get_id(self) -> str: return id

    def get_status(self) -> bool: return True

    def turn_on_speaker(self): return None

    def turn_off_if_apply(self): return None

    @classmethod
    def get_by_id(cls,speaker_list,speaker_id): 
        for device in speaker_list:
            if device.id == speaker_id:
                return device
        return None