import threading
from subprocess import Popen

class AudioConfig:
    def __init__(self, id=None, file_name=None):
        self.id = id
        self.file_name = file_name

class AudioProcessManager():
    _instance = None
    subprocess_playing: dict
    subprocess_queue: list[AudioConfig]
    lock: threading.Lock
    sounds_folder: str

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.subprocess_playing = {}
            cls._instance.subprocess_queue = []
            cls._instance.lock = threading.Lock()
            cls._instance.sounds_folder = ""
        return cls._instance

    def _play_audio(self, audio_config: AudioConfig):
        while audio_config:
            file_path = self.sounds_folder + audio_config.file_name
            audio_subprocess = Popen(['aplay', file_path])
            with self.lock:
                self.subprocess_playing[audio_config.id] = audio_subprocess
                
            audio_subprocess.wait()

            with self.lock:
                self.subprocess_playing.pop(audio_config.id, None)
                if self.subprocess_queue:
                    audio_config = self.subprocess_queue.pop(0)
                else:
                    audio_config = None

    def set_sounds_folder(self,sounds_folder):
        self.sounds_folder = sounds_folder

    def execute_audio_process(self, audio_config: AudioConfig):
        with self.lock:
            if not self.subprocess_playing:
                threading.Thread(target=self._play_audio, args=(audio_config,)).start()
            else:
                self.subprocess_queue.append(audio_config)

    def kill_audio_process(self, audio_id: str):
        with self.lock:
            if audio_id in self.subprocess_playing:
                self.subprocess_playing[audio_id].kill()
                self.subprocess_playing.pop(audio_id, None)
            else:
                for audio_config in self.subprocess_queue:
                    if audio_config.id == audio_id:
                        self.subprocess_queue.remove(audio_config)
                        break

    def subprocess_ended(self, audio_id: str) -> bool:
        subprocess_playing_aux = self.subprocess_playing
        subprocess_queue_aux = self.subprocess_queue[:]
        if audio_id in subprocess_playing_aux:
            return False
        else:
            for audio_config in subprocess_queue_aux:
                if audio_config.id == audio_id:
                    return False
            return True
