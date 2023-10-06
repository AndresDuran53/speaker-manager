import subprocess
import time
from devices.speaker_device import SpeakerDevice
from devices.chromecast_device import ChromecastAudioDevice
from devices.speaker_interface import Speaker
from utils.ConfigurationReader import ConfigurationReader
from utils.custom_logging import CustomLogging
from services.mqtt_service import MqttService, MqttConfig
from services.spotify_service import SpotifyService, SpotifyConfig
from controllers.audio_controller import AudioController, AudioRequests, AudioConfig
from controllers.tts_controller import TextToSpeechGenerator
from controllers.room_controller import RoomController
from controllers.audio_speaker_manager import AudioSpeakerManager
from controllers.audio_process_manager import AudioProcessManager

class SpeakerManager():
    mqtt_service: MqttService
    audio_controller: AudioController
    spotify_service: SpotifyService
    raspotify_status: bool
    audios_list: list
    speaker_list: list[SpeakerDevice]
    device_list: list[Speaker]
    chromecast_list: list[ChromecastAudioDevice]
    sounds_folder = "sounds/"
    loggin_path = "data/speakerManager.log"
    api_config_file = "data/text-to-speech-api.json"
    audio_output_filename = "output.wav"

    def __init__(self):
        self.raspotify_status = False
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
        #
        self.audio_speaker_manager = AudioSpeakerManager()
        #
        self.audio_process_manager = AudioProcessManager()
        self.audio_process_manager.set_sounds_folder(self.sounds_folder)
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
        self.try_to_turn_on_speakers(audio_id,speakers)
        self.spotify_service.pause_song_if_necessary()
        #time.sleep(2)
        self.executeAplay(speakers,audio_config)

    def try_to_turn_on_speakers(self, audio_id: str, speakers_list: list[SpeakerDevice]):
        pending_speakers = []
        for speaker_unknow in speakers_list:
            if (not speaker_unknow.get_status()):
                self.audio_speaker_manager.add_playing_speaker(speaker_unknow,audio_id)
                pending_speakers.append(speaker_unknow)
        count_tries = 0
        while (len(pending_speakers)>0) and count_tries<4:
            for speaker_aux in pending_speakers:
                self.logger.info(f"Turning on speaker: {speaker_aux.id}")
                speaker_aux.turn_on_speaker()
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
            if(self.audio_controller.is_audio_playing(audio_id)):
                self.logger.info("Audio already executing")
                self.killAplayProcess(audio_config)
            self.reproduce_on_chromecasts(speakers,audio_config)
            sub_process_aux = self.audio_process_manager.execute_audio_process(audio_config)
            self.audio_controller.link_process_with_audio(audio_id,sub_process_aux)
            time.sleep(0.5)
        except:
            self.logger.error("[Aplay Error]: An exception occurred using Aplay")

    def killAplayProcess(self,audioConfig):
        audio_id = audioConfig.id
        self.logger.info(f"Stopping Audio file: {audio_id}...")
        try:
            self.audio_process_manager.kill_audio_process(audio_id)
            self.logger.info(f"Stopped")
        except:
            self.logger.error(f"Unable to kill audio file: {audio_id}")

    def check_playing_files(self):
        queue_files_playing = self.audio_controller.get_queue_files_playing()
        for audio_id, sub_process_aux in list(queue_files_playing.items()):
            if self.audio_process_manager.subprocess_ended(audio_id):
                self.remove_playing_file(audio_id)
        if not queue_files_playing and self.raspotify_status:
            self.spotify_service.play_song()

    def remove_playing_file(self,audio_id):
        self.audio_controller.remove_playing_audio(audio_id)
        empty_speakers = self.audio_speaker_manager.remove_audio_from_all_speakers(audio_id)
        #empty_speakers = self.audio_speaker_manager.get_empty_speakers()
        for speaker_aux in empty_speakers:
            if(audio_id!='assistantRecognition'):
                self.logger.info(f"Turning off {speaker_aux.id}")
                speaker_aux.turn_off_if_apply()
            else:
                self.logger.info(f"Speakers will remain on due to Audio ID equals: assistantRecognition")

    def run_loop(self):
        self.logger.info("Executing reproduceThreadLoop")
        while True:
            self.check_next_message()
            self.check_playing_files()
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