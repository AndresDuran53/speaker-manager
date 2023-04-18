import subprocess
import time
from devices.SpeakerDevice import SpeakerDevice
from utils.ConfigurationReader import ConfigurationReader
from utils.custom_logging import CustomLogging
from services.mqtt_service import MqttService, MqttConfig
from services.spotify_service import SpotifyService, SpotifyConfig
from controllers.audio_controller import AudioController, AudioRequests, AudioConfig
from controllers.tts_controller import TextToSpeechGenerator

class SpeakerManager():
    mqtt_service: MqttService
    audio_controller: AudioController
    spotify_service: SpotifyService
    raspotify_status: bool
    audios_list: list
    devices_list: list
    queue_files_playing: dict
    sounds_folder = "sounds/"
    loggin_path = "data/speakerManager.log"
    api_config_file = "data/text-to-speech-api.json"
    audio_output_filename = "sounds/output.wav"

    def __init__(self):
        self.raspotify_status = False
        self.queue_files_playing = {}
        self.logger = CustomLogging(self.loggin_path)
        self.logger.info("Creating Speaker Manager...")
        self.update_config_values()
        self.logger.info("Speaker Manager Created")

    def update_config_values(self):
        self.logger.info("Updating configuration Values")
        config_data = ConfigurationReader().read_config_file()
        SpeakerManager.validate_config_values(config_data)
        #Set Audios
        self.audio_controller = AudioController()
        self.audios_list = AudioConfig.list_from_json(config_data)
        #Set Devices
        self.devices_list = SpeakerDevice.list_from_json(config_data)
        #Setting Mqtt config
        mqtt_config = MqttConfig.from_json(config_data)
        self.mqtt_service = MqttService(mqtt_config,self.on_message)
        #Set Spotify config
        config = SpotifyConfig.from_json(config_data)
        self.spotify_service = SpotifyService(config)
        #Set TTS generator
        self.textToSpeechGenerator = TextToSpeechGenerator(self.api_config_file)

    def generate_tts_audio(self, messageRecieved, speaker_id, language="en"):
        file_generated = self.textToSpeechGenerator.generate_audio_file(messageRecieved, self.audio_output_filename, language)
        if(file_generated):
            self.audio_controller.add_new_audio_request("tts",speaker_id)
    
    def on_message(self,client, userdata, message):
        topicRecieved, messageRecieved = MqttService.extract_topic_and_payload(message)
        self.logger.debug(f"[Topic]: {topicRecieved} [Message Recieved]: {messageRecieved}")

        if(MqttService.is_raspotify_topic(topicRecieved)):
            self.update_raspotify_status(messageRecieved)
            return
        
        speaker_id = topicRecieved.split("/")[-2]

        if(MqttService.is_reproduce_topic(topicRecieved)):
            self.audio_controller.add_new_audio_request(messageRecieved, speaker_id, stop=False)
        elif(MqttService.is_stop_topic(topicRecieved)):
            self.audio_controller.add_new_audio_request(messageRecieved, speaker_id, stop=True)
        elif(MqttService.is_tts_topic(topicRecieved)):
            self.generate_tts_audio(messageRecieved, speaker_id, "en")
        elif(MqttService.is_tts_spanish_topic(topicRecieved)):
            self.generate_tts_audio(messageRecieved, speaker_id, "es")

    def update_raspotify_status(self,messageRecieved):        
        if(messageRecieved=="stopped"):
            self.raspotify_status = False
            self.logger.info(f"New Raspotify Status: {self.raspotify_status}")
        elif(messageRecieved == "playing" or messageRecieved == "paused" or messageRecieved == "changed"):
            self.raspotify_status = True
            self.logger.info(f"New Raspotify Status: {self.raspotify_status}")
        else:
            return #Do not change anything

    def check_add_next_message(self):
        next_to_reproduce = self.audio_controller.get_next_to_reproduce()
        if(next_to_reproduce!=None):
            self.reproduce_message(next_to_reproduce)
        next_to_stop = self.audio_controller.get_next_to_stop()
        if(next_to_stop!=None):
            self.stop_message(next_to_stop)

    def find_speakers(self, speaker_id) -> list[SpeakerDevice]:
        if speaker_id == "all": return self.devices_list[:]
        speaker_found = SpeakerDevice.get_by_id(self.devices_list, speaker_id)
        if (speaker_found is None):
            self.logger.warning(f"No speaker {speaker_id} found")
            return []
        return [speaker_found]
    
    def find_audio_config(self, audio_id) -> AudioConfig:
        audio_config = AudioConfig.get_by_id(self.audios_list, audio_id)
        if (audio_config is None):
            self.logger.warning(f"No audio filename found for {audio_id}")
            return None
        return audio_config

    def reproduce_message(self, audio_requests:AudioRequests):
        speaker_id = audio_requests.rooms
        audio_id = audio_requests.audioId
        
        speakers=self.find_speakers(speaker_id)
        if(len(speakers)==0): return
        
        audio_config = self.find_audio_config(audio_id)
        if(audio_config is None): return

        self.logger.info(f"Reproducing Audio: {audio_config.file_name}")
        for speaker_aux in speakers:
            speaker_aux.add_audio(audio_id)
            self.sendMessageToSpeaker(speaker_aux.id,"1")
        self.spotify_service.pause_song_if_necessary()
        self.executeAplay(audio_config)
        

    def stop_message(self,audio_requests:AudioRequests):
        audio_id = audio_requests.audioId
        audioConfig = AudioConfig.get_by_id(self.audios_list,audio_id)
        if(audioConfig==None): return # Close if not filename founded
        self.killAplayProcess(audioConfig)

    def sendMessageToSpeaker(self,speaker_id,status):
        try:
            speakerAux = SpeakerDevice.get_by_id(self.devices_list,speaker_id)
            speakerPublishTopic = speakerAux.get_publish_topic()
            message = speakerAux.get_parsed_message(status)
            self.mqtt_service.send_message(speakerPublishTopic,message)
        except:
            self.logger.error(f"[Switch Speaker Error]: An exception occurred switching Speaker [id: {speaker_id}] status")

    def executeAplay(self,audio_config:AudioConfig):
        time.sleep(1.5)
        audio_id = audio_config.id
        try:
            if(self.queue_files_playing.get(audio_id)!=None):
                self.logger.info("Audio already executing")
                self.killAplayProcess(audio_config)
            sub_process_aux = subprocess.Popen(['aplay', self.sounds_folder+audio_config.file_name])
            self.queue_files_playing[audio_id]=sub_process_aux
            time.sleep(0.5)
        except:
            self.logger.error("[Aplay Error]: An exception occurred using Aplay")

    def killAplayProcess(self,audioConfig):
        audio_id = audioConfig.id
        self.logger.info(f"Stopping Audio file: {audio_id}...")
        try:
            sub_process_aux = self.queue_files_playing[audio_id]
            sub_process_aux.kill()
            self.logger.info(f"Stopped")
        except:
            self.logger.error(f"Unable to kill audio file: {audio_id}")

    def checkPlayingFiles(self):
        if(len(list(self.queue_files_playing.keys()))>0):
            for audio_id in list(self.queue_files_playing.keys()):
                sub_process_aux = self.queue_files_playing[audio_id]
                if sub_process_aux.poll() is not None:
                    self.remove_playing_file(audio_id)
            if(len(list(self.queue_files_playing.keys()))==0 and self.raspotify_status):
                self.spotify_service.play_song()


    def remove_playing_file(self,audio_id):
        if audio_id in self.queue_files_playing:
            del self.queue_files_playing[audio_id]
            for speakerDevice in self.devices_list:
                is_empty = speakerDevice.remove_audio(audio_id)
                if(is_empty and (not self.raspotify_status)):
                    self.sendMessageToSpeaker(speakerDevice.id,"0")

    def runLoop(self):
        self.logger.info("Executing reproduceThreadLoop")
        while True:
            self.check_add_next_message()
            self.checkPlayingFiles()

    @classmethod
    def validate_config_values(cls,config_data):
        if ('mqtt' not in config_data):
            raise ValueError('MQTT configuration data not found in configuration file')
        if ('devices' not in config_data):
            raise ValueError('Device configuration data not found in configuration file')

def main():
    speakerManager = SpeakerManager()
    speakerManager.runLoop()

main()
