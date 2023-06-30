import paho.mqtt.client as mqtt

class MqttService:
    __instance = None
    topicSubReproduce = "speaker-message/+/reproduce"    
    topicSubStop = "speaker-message/+/stop"
    topicSubTts = "speaker-message/+/tts"
    topicSubTtsEs = "speaker-message/+/tts-es"
    topicRaspotify = "raspotify/event"

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, mqtt_config=None, on_message=None, client_id="SpeakerManager"):
        if not hasattr(self, 'client'):
            if mqtt_config is None or on_message is None or client_id is None:
                raise ValueError('MQTT configuration not found at object creation')
            self._configuration(mqtt_config, on_message, client_id)

    def _configuration(self,mqtt_config,on_message,client_id):
        if(mqtt_config is None or on_message is None or client_id is None):
            raise ValueError('MQTT configuration not found in at object creation')
        print("Configuring Mqtt...")
        self.client = mqtt.Client(client_id=client_id, clean_session=False, userdata=None, protocol=mqtt.MQTTv311, transport="tcp")
        self.client.on_message=on_message #attach function to callback
        self.client.username_pw_set(username=mqtt_config.mqtt_user, password=mqtt_config.mqtt_pass)
        self.client.connect(mqtt_config.broker_address) #connect to broker
        self.add_subscription(self.topicSubReproduce)
        self.add_subscription(self.topicSubStop)
        self.add_subscription(self.topicSubTts)
        self.add_subscription(self.topicSubTtsEs)
        self.add_subscription(self.topicRaspotify)
        print("Mqtt client created.")
        self.client.loop_start()

    def add_subscription(self, topic):
        self.client.subscribe(topic)
        print("Subscribed to topic:", topic)
    
    def send_message(self,topic,message):
        print("Sending:",topic,message)
        self.client.publish(topic,message,qos=1,retain=False)

    @staticmethod
    def extract_topic_and_payload(message):
        topic = message.topic
        payload = message.payload.decode("utf-8")
        return topic, payload
    
    def get_instance(mqtt_config=None, on_message=None, client_id="SpeakerManager"):
        if not MqttService.__instance:
            MqttService.__instance = MqttService(mqtt_config, on_message, client_id)
        return MqttService.__instance

    @classmethod
    def is_raspotify_topic(cls,topicRecieved):
        return (topicRecieved == cls.topicRaspotify)
    
    @classmethod
    def is_reproduce_topic(cls,topicRecieved):
        isSpeakerMessage = (topicRecieved.split("/")[0] == cls.topicSubReproduce.split("/")[0])
        isReproduce = (topicRecieved.split("/")[-1] == cls.topicSubReproduce.split("/")[-1])
        return (isSpeakerMessage and isReproduce)

    @classmethod
    def is_stop_topic(cls,topicRecieved):
        isSpeakerMessage = (topicRecieved.split("/")[0] == cls.topicSubReproduce.split("/")[0])
        isStop = (topicRecieved.split("/")[-1] == cls.topicSubStop.split("/")[-1])
        return (isSpeakerMessage and isStop)
    
    @classmethod
    def is_tts_topic(cls,topicRecieved):
        isSpeakerMessage = (topicRecieved.split("/")[0] == cls.topicSubReproduce.split("/")[0])
        isTts = (topicRecieved.split("/")[-1] == cls.topicSubTts.split("/")[-1])
        return (isSpeakerMessage and isTts)
    
    @classmethod
    def is_tts_spanish_topic(cls,topicRecieved):
        isSpeakerMessage = (topicRecieved.split("/")[0] == cls.topicSubReproduce.split("/")[0])
        isTts = (topicRecieved.split("/")[-1] == cls.topicSubTtsEs.split("/")[-1])
        return (isSpeakerMessage and isTts)
    
class MqttConfig:
    broker_address = None
    mqtt_user = None
    mqtt_pass = None

    def __init__(self, broker_address=None, mqtt_user=None, mqtt_pass=None):
        self.broker_address = broker_address
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass

    @classmethod
    def from_json(cls, config_data):
        mqtt_config = MqttConfig(
            broker_address=config_data['mqtt']['broker_address'],
            mqtt_user=config_data['mqtt']['mqtt_user'],
            mqtt_pass=config_data['mqtt']['mqtt_pass']
        )
        return mqtt_config