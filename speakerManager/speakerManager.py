import subprocess
import time
from devices.SpeakerDevice import SpeakerDevice
from devices.chromecast_device import ChromecastAudioDevice
from devices.speaker_interface import Speaker
from utils.ConfigurationReader import ConfigurationReader
from utils.custom_logging import CustomLogging
from services.mqtt_service import MqttService, MqttConfig
from services.spotify_service import SpotifyService, SpotifyConfig
from controllers.audio_controller import AudioController, AudioRequests, AudioConfig
from controllers.tts_controller import TextToSpeechGenerator
from controllers.room_controller import RoomController

class SpeakerManager():
    mqtt_service: MqttService
    audio_controller: AudioController
    spotify_service: SpotifyService
    raspotify_status: bool
    audios_list: list
    speaker_list: list[SpeakerDevice]
    device_list: list[Speaker]
    chromecast_list: list[ChromecastAudioDevice]
    turned_on_speakers: list[SpeakerDevice]
    queue_files_playing: dict
    sounds_folder = "sounds/"
    loggin_path = "data/speakerManager.log"
    api_config_file = "data/text-to-speech-api.json"
    audio_output_filename = "output.wav"

    def __init__(self):
        self.raspotify_status = False
        self.queue_files_playing = {}
        self.turned_on_speakers = []
        self.logger = CustomLogging(self.loggin_path)
        self.logger.info("Creating Speaker Manager...")
        self.update_config_values()
        self.logger.info("Speaker Manager Created")

    def update_config_values(self):
        self.logger.info("Updating configuration Values")
        config_data = ConfigurationReader().read_config_file()
        SpeakerManager.validate_config_values(config_data)
        #Setting Mqtt config
        self.logger.info("Creating Mqtt Service...")
        mqtt_config = MqttConfig.from_json(config_data)
        self.mqtt_service = MqttService.get_instance(mqtt_config,self.on_message)
        #Set Audios
        self.logger.info("Creating Audio Controller...")
        self.audio_controller = AudioController()
        self.audios_list = AudioConfig.list_from_json(config_data)
        #Set Rooms
        self.logger.info("Creating Room Controller...")
        self.room_controller = RoomController()
        self.room_controller.add_rooms_from_json(config_data)
        #Set Devices
        self.speaker_list = SpeakerDevice.list_from_json(config_data)
        #Set Chromecast Devices
        self.chromecast_list = ChromecastAudioDevice.list_from_json(config_data)
        self.device_list = self.speaker_list[:] + self.chromecast_list[:]
        #Set Spotify config
        config = SpotifyConfig.from_json(config_data)
        self.spotify_service = SpotifyService(config)
        #Set TTS generator
        self.textToSpeechGenerator = TextToSpeechGenerator(self.api_config_file)

    def on_message(self,client, userdata, message):
        topicRecieved, messageRecieved = MqttService.extract_topic_and_payload(message)
        self.logger.debug(f"[Topic]: {topicRecieved} [Message Recieved]: {messageRecieved}")

        if(MqttService.is_raspotify_topic(topicRecieved)):
            self.update_raspotify_status(messageRecieved)
            return
        
        for speaker in self.speaker_list:
            if(topicRecieved == speaker.get_subscribe_topic()):
                speaker.update_status_from_message(messageRecieved)
                return
        
        rooms = topicRecieved.split("/")[-2]
        if(MqttService.is_reproduce_topic(topicRecieved)):
            self.audio_controller.add_new_audio_request(messageRecieved, rooms, stop=False)
        elif(MqttService.is_stop_topic(topicRecieved)):
            self.audio_controller.add_new_audio_request(messageRecieved, rooms, stop=True)
        elif(MqttService.is_tts_topic(topicRecieved)):
            self.generate_tts_audio(messageRecieved, rooms, "en")
        elif(MqttService.is_tts_spanish_topic(topicRecieved)):
            self.generate_tts_audio(messageRecieved, rooms, "es")

    def generate_tts_audio(self, messageRecieved, rooms, language="en"):
        audioGeneratedName = f"{self.sounds_folder}/{self.audio_output_filename}"
        file_generated = self.textToSpeechGenerator.generate_audio_file(messageRecieved, audioGeneratedName, language)
        if(file_generated):
            self.audio_controller.add_new_audio_request("tts",rooms)

    def update_raspotify_status(self,messageRecieved):        
        if(messageRecieved=="stopped"):
            self.raspotify_status = False
            self.logger.info(f"New Raspotify Status: {self.raspotify_status}")
        elif(messageRecieved == "playing" or messageRecieved == "paused" or messageRecieved == "changed"):
            self.raspotify_status = True
            self.logger.info(f"New Raspotify Status: {self.raspotify_status}")
        else:
            return #Do not change anything

    def check_next_message(self):
        next_to_reproduce = self.audio_controller.get_next_to_reproduce()
        if(next_to_reproduce!=None):
            self.reproduce_message(next_to_reproduce)
        next_to_stop = self.audio_controller.get_next_to_stop()
        if(next_to_stop!=None):
            self.stop_message(next_to_stop)
    
    def find_audio_config(self, audio_id) -> AudioConfig:
        audio_config = AudioConfig.get_by_id(self.audios_list, audio_id)
        if (audio_config is None):
            self.logger.warning(f"No audio filename found for {audio_id}")
            return None
        return audio_config
    
    def find_speakers(self, rooms) -> list[SpeakerDevice]:
        speakers_found = []
        roomsFound = self.room_controller.get_rooms_from_topic(rooms)
        for room in roomsFound:
            for speaker_id in room.speakers:
                speaker_found = Speaker.get_by_id(self.device_list, speaker_id)
                if (speaker_found is None):
                    self.logger.warning(f"No speaker {speaker_id} found")
                else:
                    speakers_found.append(speaker_found)
        return speakers_found

    def reproduce_message(self, audio_requests:AudioRequests):
        rooms = audio_requests.rooms
        audio_id = audio_requests.audioId
        speakers=self.find_speakers(rooms)
        audio_config = self.find_audio_config(audio_id)
        if(audio_config is None): return

        self.logger.info(f"Reproducing Audio: {audio_config.file_name}")
        self.try_to_turn_on_speakers(speakers)
        self.spotify_service.pause_song_if_necessary()
        #time.sleep(2)
        self.executeAplay(speakers,audio_config)

    def try_to_turn_on_speakers(self,speakers_list: list[SpeakerDevice]):
        pending_speakers = [speaker for speaker in speakers_list if not speaker.get_status()]
        count_tries = 0
        while (len(pending_speakers)>0) and count_tries<4:
            for speaker_aux in pending_speakers:
                self.logger.info(f"Turning on speaker: {speaker_aux.id}")
                speaker_aux.turn_on_speaker()
                if speaker_aux not in self.turned_on_speakers:
                    self.turned_on_speakers.append(speaker_aux)
            time.sleep(0.5)
            count_tries+=1
            pending_speakers = [speaker for speaker in speakers_list if not speaker.get_status()]

    def reproduce_on_chromecasts(self, speakers: list[Speaker], audio_config:AudioConfig):
        try:
            audioName = audio_config.file_name
            for speaker in speakers:
                for device_aux in self.chromecast_list:
                    if(speaker.get_id() == device_aux.get_id()):
                        device_aux.play_audio(audioName)
        except:
            self.logger.error("[Chromecast Error]: An exception occurred playing chromecast")

    def stop_message(self,audio_requests:AudioRequests):
        audio_id = audio_requests.audioId
        audioConfig = AudioConfig.get_by_id(self.audios_list,audio_id)
        if(audioConfig==None): return # Close if not filename founded
        self.killAplayProcess(audioConfig)

    def executeAplay(self,speakers,audio_config:AudioConfig):
        audio_id = audio_config.id
        try:
            if(self.queue_files_playing.get(audio_id)!=None):
                self.logger.info("Audio already executing")
                self.killAplayProcess(audio_config)
            self.reproduce_on_chromecasts(speakers,audio_config)
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
        count_tries = 0
        while audio_id in self.queue_files_playing and count_tries<10:
            del self.queue_files_playing[audio_id]
            count_tries+=1
            time.sleep(0.2)
        while (len(self.turned_on_speakers)>0):
            speakerDevice = self.turned_on_speakers.pop(-1)
            self.logger.info(f"Turning off {speakerDevice.id}")
            speakerDevice.turn_off_if_apply()

    def run_loop(self):
        self.logger.info("Executing reproduceThreadLoop")
        while True:
            self.check_next_message()
            self.checkPlayingFiles()
            time.sleep(0.2)

    @classmethod
    def validate_config_values(cls,config_data):
        if ('mqtt' not in config_data):
            raise ValueError('MQTT configuration data not found in configuration file')
        if ('devices' not in config_data):
            raise ValueError('Device configuration data not found in configuration file')
        if ('audios' not in config_data):
            raise ValueError('Audios configuration data not found in configuration file')

def main():
    speaker_manager = SpeakerManager()
    speaker_manager.run_loop()

if __name__ == "__main__":
    main()