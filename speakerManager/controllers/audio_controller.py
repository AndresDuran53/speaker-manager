from utils.custom_logging import CustomLogging

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


class AudioController:
    _instance = None
    audios_list: list[AudioConfig]
    queueFilesToReproduce: list
    queueFilesToStop: list
    queue_files_playing: dict
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.audios_list = []
            cls._instance.queueFilesToReproduce = []
            cls._instance.queueFilesToStop = []
            cls._instance.queue_files_playing = {}
        return cls._instance
    
    def __init__(self, config_data, logger:CustomLogging) -> None:
        self.logger = logger
        self.logger.info("Creating Audio Controller...")
        self.audios_list = AudioConfig.list_from_json(config_data)

    def get_next_to_reproduce(self):
        if(len(self.queueFilesToReproduce)>0):
            return self.queueFilesToReproduce.pop(0)
        return None
        
    def get_next_to_stop(self):
        if(len(self.queueFilesToStop)>0):
            return self.queueFilesToStop.pop(0)
        return None
    
    def add_next_to_reproduce(self, audioRequests: AudioRequests):
        self.logger.info(f"Adding new audio to reproduce in queue: [{audioRequests.audioId}] to rooms: [{audioRequests.rooms}]")
        self.queueFilesToReproduce.append(audioRequests)
        
    def add_next_to_stop(self, audioRequests: AudioRequests):
        self.logger.info(f"Adding new audio to stop: [{audioRequests.audioId}] to rooms: [{audioRequests.rooms}]")
        self.queueFilesToStop.append(audioRequests)

    def add_new_audio_request(self, audioId, rooms, stop=False):
        audio_requests = AudioRequests(audioId, rooms)
        if(stop):
            self.add_next_to_stop(audio_requests)    
        else:
            self.add_next_to_reproduce(audio_requests)
    
    def get_queue_files_playing(self):
        return self.queue_files_playing

    def is_audio_playing(self, audio_id:str):
        return self.queue_files_playing.get(audio_id)!=None
    
    def link_process_with_audio(self, audio_id, sub_process):
        self.queue_files_playing[audio_id]=sub_process

    def remove_playing_audio(self, audio_id:str):
        if (audio_id in self.queue_files_playing):
            del self.queue_files_playing[audio_id]

    def get_audio_config_by_id(self, audio_id):
        for audio_config in self.audios_list:
            if audio_config.id == audio_id:
                return audio_config
        return None