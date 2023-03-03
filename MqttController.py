import paho.mqtt.client as mqtt

class MqttController:
    topicSubReproduce = "speaker-message/+/reproduce"
    topicSubStop = "speaker-message/+/stop"
    topicSubTts = "speaker-message/+/tts"
    topicRaspotify = "raspotify/event"

    def __init__(self,mqtt_config,on_message,client_id="SpeakerManager"):
        print("Configuring Mqtt...")
        self.client = mqtt.Client(client_id=client_id, clean_session=False, userdata=None, protocol=mqtt.MQTTv311, transport="tcp")
        self.client.on_message=on_message #attach function to callback
        self.client.username_pw_set(username=mqtt_config.mqtt_user, password=mqtt_config.mqtt_pass)
        self.client.connect(mqtt_config.broker_address) #connect to broker
        self.client.subscribe(self.topicSubReproduce)
        self.client.subscribe(self.topicSubStop)
        self.client.subscribe(self.topicSubTts)
        self.client.subscribe(self.topicRaspotify)
        print("Mqtt client created.")
        #client.loop_forever() #start the loop
        self.client.loop_start()
    
    def send_message(self,topic,message):
        print("Sending:",topic,message)
        self.client.publish(topic,message,qos=1,retain=False)

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