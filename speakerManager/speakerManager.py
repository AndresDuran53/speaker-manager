import time
from devices.speaker_device import SpeakerDevice
from devices.chromecast_device import ChromecastAudioDevice
from devices.speaker_interface import Speaker
from zarus_core import ConfigurationReader, CustomLogging
from services.mqtt_service import MqttService, MqttConfig
from services.spotify_service import SpotifyService
from services.librespot_service import LibreSpotService
from controllers.audio_controller import AudioController, AudioRequests, AudioConfig
from controllers.tts_controller import TextToSpeechGenerator
from controllers.room_controller import RoomController
from controllers.audio_speaker_manager import AudioSpeakerManager
from controllers.audio_process_manager import AudioProcessManager
from controllers.volume_controller import VolumeController

class SpeakerManager():
    mqtt_service: MqttService = None
    audio_controller: AudioController = None
    spotify_service: SpotifyService = None
    use_spotify_service = True
    speaker_list: list[SpeakerDevice] = []
    chromecast_list: list[ChromecastAudioDevice] = []
    sounds_folder = "sounds/"
    loggin_path = "logs/speakerManager.log"
    api_config_file = "conf/text-to-speech-api.json"
    configuration_completed = False

    CMD_SPOTIFY_EVENT = "Spotify Event"
    CMD_REPRODUCE_SOUND = "Reproduce Sound"
    CMD_STOP_SOUND = "Stop Sound"
    CMD_REPRODUCE_TTS = "Reproduce Tts"
    CMD_REPRODUCE_TTS_ES = "Reproduce Tts-Es"
    CMD_SET_VOLUME = "Set Volume"
    ASSISTANT_RECOGNITION_AUDIO_ID = "assistantRecognition"

    def __init__(self):
        CustomLogging.configure_project(project_name="speakerManager", log_file=self.loggin_path)
        self.logger: CustomLogging = CustomLogging(component_name="SpeakerManager")
        self.logger.info("Creating Speaker Manager...")
        self.update_config_values()
        self.logger.info("Speaker Manager Created")

    def update_config_values(self):
        self.logger.info("Updating configuration Values")
        config_data = ConfigurationReader.read_config_file("conf/configuration.json")
        SpeakerManager.validate_config_values(config_data)

        #Setting Mqtt config
        mqtt_config = MqttConfig.from_json(config_data)
        self.mqtt_service = MqttService(mqtt_config=mqtt_config, process_message=self.on_mqtt_message, logger=self.logger)

        #Set Audios
        self.audio_controller = AudioController(config_data, logger=self.logger)

        #Set AudioSpeakerManager
        self.audio_speaker_manager = AudioSpeakerManager(logger=self.logger)

        #Set AudioProcessManager
        self.audio_process_manager = AudioProcessManager(self.sounds_folder, logger=self.logger)

        #Set Rooms
        self.room_controller = RoomController(config_data, logger=self.logger)

        #Set Devices
        self.speaker_list = SpeakerDevice.list_from_json(config_data)

        #Set Chromecast Devices
        self.chromecast_list = ChromecastAudioDevice.list_from_json(config_data)

        #Set Spotify config
        if(self.use_spotify_service):
            self.spotify_service = SpotifyService(config_data, logger=self.logger)

        #Spotify Speaker
        self.librespot = LibreSpotService(logger=self.logger)
        
        #Set TTS generator
        self.textToSpeechGenerator = TextToSpeechGenerator(self.api_config_file, sounds_folder=self.sounds_folder, logger=self.logger)
        
        self.configuration_completed = True

    def on_mqtt_message(self, topic_recieved: str, message_recieved: str):
        if(not self.configuration_completed):
            return
        
        #If the message is a command to a speaker
        speaker_aux:SpeakerDevice = SpeakerDevice.get_by_subs_topic(self.speaker_list, topic_recieved)
        if(speaker_aux):
            self.logger.info(f"Speaker status update | topic: {topic_recieved} | message: {message_recieved}")
            speaker_aux.update_status_from_message(message_recieved)
            return

        #If the message is a command to the program
        command_name = self.mqtt_service.get_command_from_topic(topic_recieved)
        if(command_name):
            self.execute_command(command_name, topic_recieved, message_recieved)
            return

    def execute_command(self, command_name:str, topic_recieved:str, message:str):
        self.logger.info(f"Command triggered: [{command_name}] | topic: {topic_recieved} | message: {message}")
        if(self.CMD_SPOTIFY_EVENT == command_name):
            librespot_changed = self.librespot.update_status(message)
            if(librespot_changed):
                librespot_is_active = self.librespot.is_active()
                spotify_audio_id = self.librespot.get_audio_id()
                if(librespot_is_active):
                    self.wake_speakers(spotify_audio_id, self.speaker_list)
                else:
                    self.on_audio_finished(spotify_audio_id)
            return
        
        topic_recieved_split = topic_recieved.split("/")
        if(len(topic_recieved_split)<2): return
        rooms = topic_recieved_split[-2]
        
        if(self.CMD_REPRODUCE_SOUND == command_name):
            self.audio_controller.add_new_audio_request(message, rooms, stop=False)
        elif(self.CMD_STOP_SOUND == command_name):
            self.audio_controller.add_new_audio_request(message, rooms, stop=True)
        elif(self.CMD_REPRODUCE_TTS == command_name):
            self.synthesize_and_queue_tts(message, rooms, "en")
        elif(self.CMD_REPRODUCE_TTS_ES == command_name):
            self.synthesize_and_queue_tts(message, rooms, "es")
        elif(self.CMD_SET_VOLUME == command_name):
            VolumeController.set_volume(message)

    def synthesize_and_queue_tts(self, message_recieved, rooms, language="en"):
        file_generated = self.textToSpeechGenerator.generate_audio_file(message_recieved, language)
        if(file_generated):
            self.audio_controller.add_new_audio_request("tts",rooms)

    def process_next_queued_requests(self):
        next_to_reproduce = self.audio_controller.get_next_to_reproduce()
        if(next_to_reproduce!=None):
            self.handle_play_request(next_to_reproduce)
        next_to_stop = self.audio_controller.get_next_to_stop()
        if(next_to_stop!=None):
            self.handle_stop_request(next_to_stop)
    
    def get_speakers_for_rooms(self, rooms) -> list[SpeakerDevice]:
        device_list: list[Speaker] = self.speaker_list[:] + self.chromecast_list[:]
        speakers_found = []
        roomsFound = self.room_controller.get_rooms_from_topic(rooms)
        for room in roomsFound:
            for speaker_id in room.speakers:
                speaker_found = Speaker.get_by_id(device_list, speaker_id)
                if (speaker_found is None):
                    self.logger.warning(f"No speaker {speaker_id} found")
                else:
                    speakers_found.append(speaker_found)
        return speakers_found

    def handle_play_request(self, audio_requests:AudioRequests):
        # 1. Resolve speakers and audio config
        rooms = audio_requests.rooms
        audio_id = audio_requests.audioId
        speakers = self.get_speakers_for_rooms(rooms)
        audio_config = self.audio_controller.get_audio_config_by_id(audio_id)
        if(audio_config is None):
            self.logger.warning(f"No audio filename found for {audio_id}")
            return

        # 2. Wake speakers before playback begins
        self.wake_speakers(audio_id, speakers)

        # 3. Duck Spotify volume if librespot is streaming
        if(self.use_spotify_service):
            if(self.librespot.is_active()):
                self.logger.info(f"LibreSpot is playing something")
                self.spotify_service.decrease_volume_if_necessary()
            else:
                self.logger.info(f"LibreSpot is not active")

        # 4. Start audio playback
        self.start_playback(speakers, audio_config)

    def wake_speakers(self, audio_id: str, speakers_list: list[SpeakerDevice]):
        speakers_list_copy = speakers_list[:]
        self.logger.info("Turning on Speakers...")
        pending_speakers = []
        for speaker_unknow in speakers_list_copy:
            self.audio_speaker_manager.add_playing_speaker(speaker_unknow,audio_id)
            if (not speaker_unknow.get_status()):
                pending_speakers.append(speaker_unknow)
        count_tries = 0
        while (len(pending_speakers)>0) and count_tries<4:
            for speaker_aux in pending_speakers:
                if (speaker_aux.is_turn_on_requested() != None or speaker_aux.is_turn_on_requested() == False):
                    self.logger.info(f"Turn off requested for speaker: {speaker_aux.id}, value {speaker_aux.is_turn_on_requested()}, removing from pending list")
                else:
                    self.logger.info(f"Turning on speaker: {speaker_aux.id}")
                    speaker_aux.turn_on_speaker()
                    
            time.sleep(0.5 * count_tries)
            count_tries+=1
            pending_speakers = [speaker for speaker in speakers_list_copy if not speaker.get_status()]

    def reproduce_on_chromecasts(self, speakers: list[Speaker], audio_config:AudioConfig):
        self.logger.info(f"[Chromecasts] Reproducing Audio on Chromecasts: {speakers}")
        try:
            audioName = audio_config.file_name
            for speaker in speakers:
                for device_aux in self.chromecast_list:
                    if(speaker.get_id() == device_aux.get_id()):
                        device_aux.play_audio(audioName)
        except:
            self.logger.error("[Chromecast Error]: An exception occurred playing chromecast")
        self.logger.info(f"[Chromecasts] Done.")

    def handle_stop_request(self, audio_requests:AudioRequests):
        audio_id = audio_requests.audioId
        audio_config = self.audio_controller.get_audio_config_by_id(audio_id)
        if(audio_config==None): return # Close if not filename founded
        self.stop_playback(audio_config)

    def start_playback(self, speakers, audio_config:AudioConfig):
        self.logger.info(f"Reproducing Audio: {audio_config.file_name}")
        audio_id = audio_config.id
        try:
            if(self.audio_controller.is_audio_playing(audio_id)):
                self.logger.info("Audio already executing")
                self.stop_playback(audio_config)
            #self.reproduce_on_chromecasts(speakers,audio_config)
            sub_process_aux = self.audio_process_manager.execute_audio_process(audio_config)
            self.audio_controller.link_process_with_audio(audio_id,sub_process_aux)
            time.sleep(0.5)
        except:
            self.logger.error("[Aplay Error]: An exception occurred using Aplay")

    def stop_playback(self, audioConfig:AudioConfig):
        audio_id = audioConfig.id
        self.logger.info(f"Stopping Audio file: {audio_id}...")
        try:
            self.audio_process_manager.kill_audio_process(audio_id)
            self.logger.info(f"Stopped")
        except:
            self.logger.error(f"Unable to kill audio file: {audio_id}")

    def update_playback_state(self):
        queue_files_playing = self.audio_controller.get_queue_files_playing()
        for audio_id, sub_process_aux in list(queue_files_playing.items()):
            if self.audio_process_manager.subprocess_ended(audio_id):
                self.on_audio_finished(audio_id)
        if (self.use_spotify_service and not queue_files_playing and self.spotify_service.has_to_restore_volume()):
            self.spotify_service.restore_volume()

    def on_audio_finished(self, audio_id:str):
        self.audio_controller.remove_playing_audio(audio_id)
        removed_audio_speakers = self.audio_speaker_manager.remove_audio_from_all_speakers(audio_id)
        empty_speakers = self.audio_speaker_manager.get_empty_speakers()
        speakers_to_turn_off = [speaker_aux for speaker_aux in removed_audio_speakers if speaker_aux in empty_speakers]
        self.logger.info(f"Audio finished: [{audio_id}] | affected speakers: {[s.id for s in removed_audio_speakers]} | empty speakers: {[s.id for s in empty_speakers]} | to turn off: {[s.id for s in speakers_to_turn_off]}")
        for speaker_aux in speakers_to_turn_off:
            if(audio_id != self.ASSISTANT_RECOGNITION_AUDIO_ID):
                self.logger.info(f"Turning off {speaker_aux.id}")
                speaker_aux.turn_off_if_apply()
            else:
                self.logger.info(f"Speakers will remain on due to Audio ID equals: {self.ASSISTANT_RECOGNITION_AUDIO_ID}")

    def check_librespot_timeout(self):
        spotify_audio_id = self.librespot.get_audio_id()
        spotify_timed_out = self.librespot.activity_status_timed_out()
        if(spotify_timed_out):
            self.on_audio_finished(spotify_audio_id)

    def run_loop(self):
        self.logger.info("Executing reproduceThreadLoop")
        while True:
            self.process_next_queued_requests()
            self.update_playback_state()
            self.check_librespot_timeout()
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