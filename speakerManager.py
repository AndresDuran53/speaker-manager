import subprocess
import time
from ConfigurationReader import ConfigurationReader
from SpeakerDevice import SpeakerDevice
from AudioController import AudioController, AudioRequests, AudioConfig
from MqttController import MqttController, MqttConfig

class SpeakerManager():
    mqttController = None
    audioController = None
    raspotifyStatus = True
    audiosList = []
    devicesList = []
    queueFilesPlaying = {}
    soundsFolder = "sounds/"

    def __init__(self):
        print("Creating Speaker Manager...")
        self.update_config_values()

    def update_config_values(self):
        print("Updating configuration Values")
        config_data = ConfigurationReader().read_config_file()
        SpeakerManager.validate_config_values(config_data)
        #Set Audios
        self.audioController = AudioController()
        self.audiosList = self.get_audios_config(config_data)
        #Set Devices
        self.devicesList = self.get_devices_config(config_data)
        #Setting Mqtt config
        mqtt_config = MqttConfig.from_json(config_data)
        self.mqttController = MqttController(mqtt_config,self.on_message)

    def get_audios_config(self,config_data):
        audios = []
        for audio_data in config_data['audios']:
            audio_config = AudioConfig.from_json(audio_data)
            audios.append(audio_config)
        return audios
        
    def get_devices_config(self,config_data):
        devices = []
        for device_data in config_data['devices']:
            try:
                device = SpeakerDevice.from_json(device_data)
                devices.append(device)
            except TypeError:
                print(f'Error: Invalid device configuration: {device_data}')
        return devices
    
    def on_message(self,client, userdata, message):
        topicRecieved = message.topic
        messageRecieved = str(message.payload.decode("utf-8"))
        print("[Topic]:",topicRecieved,"[Message Recieved]:",messageRecieved)

        if(MqttController.is_raspotify_topic(topicRecieved)):
            self.update_raspotify_status(messageRecieved)
        #If is equal to topicSub reproduce
        elif(MqttController.is_reproduce_topic(topicRecieved)):
            speakerId = topicRecieved.split("/")[-2]
            audioRequests = AudioRequests(messageRecieved,speakerId)
            self.audioController.add_next_to_reproduce(audioRequests)
        #If is equal to topicSub Stop
        elif(MqttController.is_stop_topic(topicRecieved)): 
            speakerId = topicRecieved.split("/")[-2]
            audioRequests = AudioRequests(messageRecieved,speakerId)
            self.audioController.add_next_to_stop(audioRequests)

    def update_raspotify_status(self,messageRecieved):
        if(messageRecieved=="stopped"):
            self.raspotifyStatus = False
        else:
            self.raspotifyStatus = True
        print("New Raspotify Status:",self.raspotifyStatus)

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
                print(f"No speaker {speaker_id} found")
                return # Close if not speaker founded
            else:
                speakers = [speaker_found]
        
        audioConfig = AudioConfig.get_by_id(self.audiosList,audio_id)
        if(audioConfig==None): 
            print(f"No filename {audio_id} found")
            return # Close if not filename founded
        print(f"Reproducing Audio: {audioConfig.file_name}")

        for speaker_aux in speakers:
            speaker_aux.add_audio(audio_id)
            self.sendMessageToSpeaker(speaker_aux.id,"1")
        
        time.sleep(1.5)
        self.executeAplay(audioConfig)
        time.sleep(0.5)
        #switchSpeakersStatus(speakerId,"0")

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
            print("[Switch Speaker Error]: An exception occurred switching Speaker [id: "+speakerId+"] status")

    def executeAplay(self,audioConfig):
        audio_id = audioConfig.id
        try:
            if(self.queueFilesPlaying.get(audio_id)!=None):
                print("Audio already executing")
                self.killAplayProcess(audioConfig)
            sub_process_aux = subprocess.Popen(['aplay', self.soundsFolder+audioConfig.file_name])
            self.queueFilesPlaying[audio_id]=sub_process_aux
        except:
            print("[Aplay Error]: An exception occurred using Aplay")

    def killAplayProcess(self,audioConfig):
        audio_id = audioConfig.id
        print(f"Stopping Audio file: {audio_id}...")
        try:
            sub_process_aux = self.queueFilesPlaying[audio_id]
            sub_process_aux.kill()
            print(f"Stopped")
        except:
            print(f"Unable to kill audio file: {audio_id}")

    def checkPlayingFiles(self):
        for audio_id in list(self.queueFilesPlaying.keys()):
            sub_process_aux = self.queueFilesPlaying[audio_id]
            if sub_process_aux.poll() is not None:
                self.remove_playing_file(audio_id)

    def remove_playing_file(self,audio_id):
        if audio_id in self.queueFilesPlaying:
            del self.queueFilesPlaying[audio_id]
            for speakerDevice in self.devicesList:
                is_empty = speakerDevice.remove_audio(audio_id)
                if(is_empty and (not self.raspotifyStatus)):
                    self.sendMessageToSpeaker(speakerDevice.id,"0")


    @classmethod
    def validate_config_values(cls,config_data):
        if ('mqtt' not in config_data):
            raise ValueError('MQTT configuration data not found in configuration file')
        if ('devices' not in config_data):
            raise ValueError('Device configuration data not found in configuration file')

def main():
    print("Starting Speaker Manager...")
    speakerManager = SpeakerManager()
    print("Executing reproduceThreadLoop")
    while True:
        speakerManager.check_add_next_message()
        speakerManager.checkPlayingFiles()

main()
