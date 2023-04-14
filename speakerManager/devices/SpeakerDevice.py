class SpeakerDevice:

    def __init__(self, id=None, type=None, status=None, template=None, publish_topic=None, subscribe_topic=None):
        self.id = id
        self.type = type
        self.status = status
        self.template = template
        self.publish_topic = publish_topic
        self.subscribe_topic = subscribe_topic
        self.speaker_status = False
        self.audio_list = []

    def turn_on_speaker(self):
        if not self.speaker_status:
            self.speaker_status = True

    def turn_off_speaker(self):
        if self.speaker_status:
            self.speaker_status = False

    def check_speaker_status(self):
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
    
    def get_parsed_message(self,status):
        template = self.template
        statusSelected = self.status[status]
        msg = template.replace("%_v%",statusSelected)
        return msg

    @classmethod
    def from_json(cls, config_data):
        return cls(
            id=config_data.get('id', None),
            type=config_data.get('type', None),
            status=config_data.get('status', None),
            template=config_data.get('template', None),
            publish_topic=config_data.get('publishTopic', None),
            subscribe_topic=config_data.get('subscribeTopic', None)
        )

    @classmethod
    def get_by_id(cls, device_list, id):
        for device in device_list:
            if device.id == id:
                return device
        return None