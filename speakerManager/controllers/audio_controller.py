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

    def add_new_audio_request(self, audioId, rooms, stop=False):
        audio_requests = AudioRequests(audioId, rooms)
        if(stop):
            self.add_next_to_stop(audio_requests)    
        else:
            self.add_next_to_reproduce(audio_requests)

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
    def list_from_json(cls,config_data):
        audios = []
        for audio_data in config_data['audios']:
            audio_config = cls.from_json(audio_data)
            audios.append(audio_config)
        return audios
    
    @classmethod
    def get_by_id(cls, audio_configs, audio_id):
        for audio_config in audio_configs:
            if audio_config.id == audio_id:
                return audio_config
        return None
