from devices.speaker_interface import Speaker
from services.mqtt_service import MqttService
import time

class SpeakerDevice(Speaker):

    def __init__(self, id=None, type=None, status=None, template=None, publish_topic=None, subscribe_topic=None):
        self.id = id
        self.type = type
        self.status = status
        self.template = template
        self.publish_topic = publish_topic
        self.subscribe_topic = subscribe_topic
        self.speaker_status = False
        self.audio_list = []
        self.mqtt_service = MqttService()
        self.mqtt_service.add_subscription(self.subscribe_topic)

    def _send_message_to_speaker(self,status):
        speakerPublishTopic = self.get_publish_topic()
        message = self.get_parsed_message(status)
        self.mqtt_service.send_message(speakerPublishTopic,message)

    def turn_on_speaker(self):
        self._send_message_to_speaker("1")

    def turn_off_speaker(self):
        self._send_message_to_speaker("0")

    def get_status(self):
        return self.speaker_status

    def parse_speaker_status(self,new_status):
        aux_status = False
        if new_status == '0':
            aux_status = False
        elif new_status == '1':
            aux_status = True
        if(aux_status != self.speaker_status):
            self.speaker_status = aux_status
            print(f"Speaker status updated: {self.speaker_status}")
        return self.speaker_status

    def add_audio(self, audio_id):
        self.audio_list.append(audio_id)

    def remove_audio(self, audio_id):
        if audio_id in self.audio_list:
            self.audio_list.remove(audio_id)
            if not self.audio_list:
                return True
        return False
        
    def get_publish_topic(self):
        return self.publish_topic
    
    def get_subscribe_topic(self):
        return self.subscribe_topic
    
    def get_parsed_message(self,status):
        template = self.template
        status_selected = self.status[status]
        msg = template.replace("%_v%",status_selected)
        return msg
    
    def update_status_from_message(self, message):
        template_parts = self.template.split("%_v%")
        start_index = message.index(template_parts[0]) + len(template_parts[0])
        end_index = message.index(template_parts[1], start_index)
        if(end_index == 0): end_index = len(message)
        status_value = message[start_index:end_index]
        new_status = None
        for key, value in self.status.items():
            if value == status_value:
                new_status = key
                break
        actual_status = self.parse_speaker_status(new_status)
        return actual_status
    
    def get_id(self):
        return self.id 
    
    def turn_off_if_apply(self): 
        self.turn_off_speaker()

    @classmethod
    def from_json(cls, config_data:dict):
        return cls(
            id=config_data.get('id', None),
            type=config_data.get('type', None),
            status=config_data.get('status', None),
            template=config_data.get('template', None),
            publish_topic=config_data.get('publishTopic', None),
            subscribe_topic=config_data.get('subscribeTopic', None)
        )
    
    @classmethod
    def list_from_json(cls,config_data):
        devices = []
        for device_data in config_data['devices']:
                device = cls.from_json(device_data)
                devices.append(device)
        return devices

    @classmethod
    def get_by_id(cls, speaker_list, speaker_id):
        for device in speaker_list:
            if device.id == speaker_id:
                return device
        return None
    
    @classmethod
    def get_by_subs_topic(cls, speaker_list, subs_topic):
        for speaker in speaker_list:
            if(subs_topic == speaker.get_subscribe_topic()):
                return speaker