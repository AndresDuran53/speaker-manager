from devices.speaker_device import SpeakerDevice
from utils.custom_logging import CustomLogging

class SpeakerAudioQueue():
    speaker: SpeakerDevice
    audios_pending: list[str]

    def __init__(self, speaker: SpeakerDevice, audios_pending: list[str]):
        self.speaker = speaker
        self.audios_pending = audios_pending

    def get_speaker(self):
        return self.speaker
        
    def get_speaker_id(self):
        return self.speaker.get_id()
    
    def add_new_audio(self, audio_id: str):
        self.audios_pending.append(audio_id)

    def remove_audio(self, audio_id: str):
        if(self.is_audio_pending(audio_id)):
            self.audios_pending.remove(audio_id)

    def get_remaining_audios(self) -> list:
        return self.audios_pending
    
    def is_audio_pending(self,audio_id) -> bool:
        return audio_id in self.audios_pending


class AudioSpeakerManager():
    _instance = None
    playing_speakers: list[SpeakerAudioQueue]

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.playing_speakers = []
        return cls._instance
    
    def __init__(self, logger:CustomLogging) -> None:
        self.logger = logger
        self.logger.info("Creating AudioSpeaker Manager...")
    
    def get_empty_speakers(self):
        empty_speakers = [speaker_queue_aux.get_speaker() for speaker_queue_aux in self.playing_speakers if len(speaker_queue_aux.get_remaining_audios())==0]
        return empty_speakers
    
    def add_playing_speaker(self,speaker: SpeakerDevice, audio_id: str) -> bool:
        for speaker_queue_aux in self.playing_speakers:
            if speaker_queue_aux.get_speaker_id() == speaker.get_id():
                if audio_id in speaker_queue_aux.get_remaining_audios():
                    return False
                else:
                    speaker_queue_aux.add_new_audio(audio_id)
                    return True
        self.playing_speakers.append(SpeakerAudioQueue(speaker,[audio_id]))
        return True
    
    def remove_audio_from_all_speakers(self,audio_id):
        speaker_list: list[SpeakerDevice] = []
        for speaker_queue_aux in self.playing_speakers:
            if audio_id in speaker_queue_aux.get_remaining_audios():
                speaker_queue_aux.remove_audio(audio_id)
                speaker_list.append(speaker_queue_aux.get_speaker())
        return speaker_list

    
    