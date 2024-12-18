from utils.custom_logging import CustomLogging
import paho.mqtt.client as mqtt

class MqttConfig:
    broker_address:str
    mqtt_user:str
    mqtt_pass:str
    subscription_topics:list

    def __init__(self, broker_address=None, mqtt_user=None, mqtt_pass=None, subscription_topics=None):
        self.broker_address = broker_address
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass
        self.subscription_topics = subscription_topics

    @classmethod
    def from_json(cls, config_data):
        mqtt_config = MqttConfig(
            broker_address=config_data['mqtt']['brokerAddress'],
            mqtt_user=config_data['mqtt']['mqttUser'],
            mqtt_pass=config_data['mqtt']['mqttPass'],
            subscription_topics=config_data['mqtt']['subscriptionTopics']
        )
        return mqtt_config
    

class MqttService:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, mqtt_config:MqttConfig=None, process_message=None, client_id="SpeakerManager", logger=CustomLogging("logs/mqtt.log")):
        if not hasattr(self, 'client'):
            if mqtt_config is None or process_message is None or client_id is None:
                raise ValueError('MQTT configuration not found at object creation')
            logger.info("Creating New Mqtt Service...")
            self._configuration(mqtt_config, process_message, client_id, logger)

    def _configuration(self, mqtt_config:MqttConfig, process_message, client_id:str, logger:CustomLogging):
        self.logger = logger
        self.logger.info("Configuring Mqtt...")
        self.process_message = process_message
        self.client = mqtt.Client(client_id=client_id, clean_session=False, userdata=None, protocol=mqtt.MQTTv311, transport="tcp")
        self.client.on_message = self.on_message
        self.client.username_pw_set(username=mqtt_config.mqtt_user, password=mqtt_config.mqtt_pass)
        self.client.connect(mqtt_config.broker_address)
        self.know_commands = mqtt_config.subscription_topics
        self.subscribe_know_topics()
        self.logger.info("Mqtt client created.")
        self.client.loop_start()

    def add_subscription(self, topic:str):
        self.client.subscribe(topic)
        self.logger.info(f"Subscribed to topic: {topic}")

    def subscribe_know_topics(self):
        for know_command in self.know_commands:
            topic = know_command["topic"]
            self.add_subscription(topic)
    
    def on_message(self, client, userdata, message):        
        topic_recieved, message_recieved = self.extract_topic_and_payload(message)
        self.process_message(topic_recieved, message_recieved)

    def send_message(self, topic:str, message:str):
        self.logger.info(f"[Sending] | [Topic]:{topic} | [Message]:{message}")
        self.client.publish(topic,message,qos=1,retain=False)

    def get_command_from_topic(self, topic:str) -> str:
        splitted_topic = topic.split("/")
        for know_command in self.know_commands:
            founded = True
            splitted_know_command = know_command["topic"].split("/")
            if(len(splitted_know_command) == len(splitted_topic)):
                for i in range(len(splitted_know_command)):
                    if(splitted_know_command[i] != splitted_topic[i] and splitted_know_command[i] != '+'):
                        founded = False
                if(founded):
                    return know_command["commandName"]
        return None

    def extract_topic_and_payload(self, message):
        topic = message.topic
        payload = message.payload.decode("utf-8")
        self.logger.debug(f"[Topic]: {topic} [Message Recieved]: {payload}")
        return topic, payload