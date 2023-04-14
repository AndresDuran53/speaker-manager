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
    mqttController = None
    audioController = None
    raspotifyStatus = False
    spotifyController = None
    audiosList = []
    devicesList = []
    queueFilesPlaying = {}
    soundsFolder = "sounds/"
    logginPath = "data/speakerManager.log"
    api_config_file = "data/text-to-speech-api.json"
    audio_output_filename = "sounds/output.wav"

    def __init__(self):
        self.logger = CustomLogging(self.logginPath)
        self.logger.info("Creating Speaker Manager...")
        self.update_config_values()
        self.logger.info("Speaker Manager Created")

    def update_config_values(self):
        self.logger.info("Updating configuration Values")
        config_data = ConfigurationReader().read_config_file()
        SpeakerManager.validate_config_values(config_data)
        #Set Audios
        self.audioController = AudioController()
        self.audiosList = AudioConfig.list_from_json(config_data)
        #Set Devices
        self.devicesList = SpeakerDevice.list_from_json(config_data)
        #Setting Mqtt config
        mqtt_config = MqttConfig.from_json(config_data)
        self.mqttController = MqttService(mqtt_config,self.on_message)
        #Set Spotify config
        config = SpotifyConfig.from_json(config_data)
        self.spotifyController = SpotifyService(config)
        #Set TTS generator
        self.textToSpeechGenerator = TextToSpeechGenerator(self.api_config_file)

    def generate_tts_audio(self, messageRecieved, speakerId, language="en"):
        self.textToSpeechGenerator.generate_audio_file(messageRecieved, self.audio_output_filename, language)
        self.audioController.add_new_audio_request("tts",speakerId)
    
    def on_message(self,client, userdata, message):
        topicRecieved, messageRecieved = MqttService.extract_topic_and_payload(message)
        self.logger.debug("[Topic]:",topicRecieved,"[Message Recieved]:",messageRecieved)

        if(MqttService.is_raspotify_topic(topicRecieved)):
            self.update_raspotify_status(messageRecieved)
            return
        
        speakerId = topicRecieved.split("/")[-2]

        if(MqttService.is_reproduce_topic(topicRecieved)):
            self.audioController.add_new_audio_request(messageRecieved, speakerId, stop=False)
        elif(MqttService.is_stop_topic(topicRecieved)):
            self.audioController.add_new_audio_request(messageRecieved, speakerId, stop=True)
        elif(MqttService.is_tts_topic(topicRecieved)):
            self.generate_tts_audio(messageRecieved, speakerId, "en")
        elif(MqttService.is_tts_spanish_topic(topicRecieved)):
            self.generate_tts_audio(messageRecieved, speakerId, "es")

    def update_raspotify_status(self,messageRecieved):        
        if(messageRecieved=="stopped"):
            self.raspotifyStatus = False
            self.logger.info("New Raspotify Status:",self.raspotifyStatus)
        elif(messageRecieved == "playing" or messageRecieved == "paused" or messageRecieved == "changed"):
            self.raspotifyStatus = True
            self.logger.info("New Raspotify Status:",self.raspotifyStatus)
        else:
            return #Do not change anything

    def check_add_next_message(self):
        next_to_reproduce = self.audioController.get_next_to_reproduce()
        if(next_to_reproduce!=None):
            self.reproduce_message(next_to_reproduce)

        next_to_stop = self.audioController.get_next_to_stop()
        if(next_to_stop!=None):
            self.stop_message(next_to_stop)

    def reproduce_message(self,audio_requests):
        speaker_id = audio_requests.rooms
        audio_id = audio_requests.audioId

        speakers=[]
        if(speaker_id=="all"):
            speakers = self.devicesList[:]
            
        else:
            speaker_found = SpeakerDevice.get_by_id(self.devicesList,speaker_id)
            if(speaker_found==None): 
                self.logger.warning(f"No speaker {speaker_id} found")
                return # Close if not speaker founded
            else:
                speakers = [speaker_found]
        
        audioConfig = AudioConfig.get_by_id(self.audiosList,audio_id)
        if(audioConfig==None): 
            self.logger.warning(f"No filename {audio_id} found")
            return # Close if not filename founded
        self.logger.info(f"Reproducing Audio: {audioConfig.file_name}")

        for speaker_aux in speakers:
            speaker_aux.add_audio(audio_id)
            self.sendMessageToSpeaker(speaker_aux.id,"1")

        #Pause the Raspotify
        self.spotifyController.pause_song_if_necessary()

        time.sleep(1.5)
        self.executeAplay(audioConfig)
        time.sleep(0.5)

    def stop_message(self,audio_requests):
        audio_id = audio_requests.audioId
        audioConfig = AudioConfig.get_by_id(self.audiosList,audio_id)
        if(audioConfig==None): return # Close if not filename founded
        self.killAplayProcess(audioConfig)

    def sendMessageToSpeaker(self,speakerId,status):
        try:
            speakerAux = SpeakerDevice.get_by_id(self.devicesList,speakerId)
            speakerPublishTopic = speakerAux.get_publish_topic()
            message = speakerAux.get_parsed_message(status)
            self.mqttController.send_message(speakerPublishTopic,message)
        except:
            self.logger.error("[Switch Speaker Error]: An exception occurred switching Speaker [id: "+speakerId+"] status")

    def executeAplay(self,audioConfig):
        audio_id = audioConfig.id
        try:
            if(self.queueFilesPlaying.get(audio_id)!=None):
                self.logger.info("Audio already executing")
                self.killAplayProcess(audioConfig)
            sub_process_aux = subprocess.Popen(['aplay', self.soundsFolder+audioConfig.file_name])
            self.queueFilesPlaying[audio_id]=sub_process_aux
        except:
            self.logger.error("[Aplay Error]: An exception occurred using Aplay")

    def killAplayProcess(self,audioConfig):
        audio_id = audioConfig.id
        self.logger.info(f"Stopping Audio file: {audio_id}...")
        try:
            sub_process_aux = self.queueFilesPlaying[audio_id]
            sub_process_aux.kill()
            self.logger.info(f"Stopped")
        except:
            self.logger.error(f"Unable to kill audio file: {audio_id}")

    def checkPlayingFiles(self):
        if(len(list(self.queueFilesPlaying.keys()))>0):
            for audio_id in list(self.queueFilesPlaying.keys()):
                sub_process_aux = self.queueFilesPlaying[audio_id]
                if sub_process_aux.poll() is not None:
                    self.remove_playing_file(audio_id)
            if(len(list(self.queueFilesPlaying.keys()))==0 and self.raspotifyStatus):
                self.spotifyController.play_song()


    def remove_playing_file(self,audio_id):
        if audio_id in self.queueFilesPlaying:
            del self.queueFilesPlaying[audio_id]
            for speakerDevice in self.devicesList:
                is_empty = speakerDevice.remove_audio(audio_id)
                if(is_empty and (not self.raspotifyStatus)):
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
