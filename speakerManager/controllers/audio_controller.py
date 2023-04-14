class AudioController:
    queueFilesToReproduce = []
    queueFilesToStop = []

    def get_next_to_reproduce(self):
        if(len(self.queueFilesToReproduce)>0):
            return self.queueFilesToReproduce.pop(0)
        return None
        
    def get_next_to_stop(self):
        if(len(self.queueFilesToStop)>0):
            return self.queueFilesToStop.pop(0)
        return None
    
    def add_next_to_reproduce(self,audioRequests):
        self.queueFilesToReproduce.append(audioRequests)
        
    def add_next_to_stop(self,audioRequests):
        self.queueFilesToStop.append(audioRequests)


class AudioRequests():
    def __init__(self,audioId,rooms):
        self.audioId = audioId
        self.rooms = rooms

class AudioConfig:
    def __init__(self, id=None, file_name=None):
        self.id = id
        self.file_name = file_name

    @classmethod
    def from_json(cls, audio_data):
        audio_config = AudioConfig(
            id=audio_data['id'],
            file_name=audio_data['file_name']
        )
        return audio_config
    
    @classmethod
    def get_by_id(cls, audio_configs, audio_id):
        for audio_config in audio_configs:
            if audio_config.id == audio_id:
                return audio_config
        return None
