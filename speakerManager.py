import sys
import paho.mqtt.client as mqtt
import paho.mqtt.publish as mqttpublish
import requests
import secrets
import subprocess

broker_address = secrets.BROKER_ADDRESS
topicSub = "speaker-message/+/message"
soundsFolder = "/home/developer/sounds/"
apiKey = secrets.API_KEY
chatId = secrets.CHAT_ID
mqttUser = secrets.MQTT_USER
mqttPass = secrets.MQTT_PASS
clientId = "SpeakerManager"
#client = None

savedSpeakers = {
    "nag241":{
        "type":"ZARUS",
        "status":{"0":"0","1":"1"},
        "template":'{"CID":"1","spst":"%_v%"}',
        "publishTopic":"speaker-switch/nag241/cmd",
        "subscribeTopic":"speaker-switch/nag241/cmd"
    },
    "25070A":{
        "type":"TASMOTA",
        "status":{"0":"OFF","1":"ON"},
        "template":"%_v%",
        "publishTopic":"casa/cocina/parlantes/cmnd/25070A/POWER",
        "subscribeTopic":"casa/cocina/parlantes/stat/25070A/POWER"
    }
}

audiosFilename = {
    "CloseGarage":"It's-safe-now-the-garage-door-has-closed.wav",
    "OpenGarage":"Beware-the-garage-door-has-been-opened.wav",
    "FeedCats":"comidaGatas.wav",
    "tboiS2":"The_Binding_of_Issac_Sacrificial2.wav",
    "Sims4Theme":"The_Sims_4_theme.wav",
}

#Examples:
# speaker-message/all/message "OpenGarage"
# speaker-message/25070A/message "Receta"
# speaker-message/nag241/message "Welcome Guest"

def sendMessage(topic,message):
    print("Sending:",topic,message)
    mqttpublish.single(topic, payload=message, qos=1, retain=False,
                        hostname=secrets.BROKER_ADDRESS,port=1883, client_id=clientId,
                        keepalive=60, will=None,
                        auth={"username":secrets.MQTT_USER,"password":secrets.MQTT_PASS},
                        tls=None, protocol=mqtt.MQTTv311, transport="tcp")

def checkActualStatus(device):
    if(device["type"]=="TASMOTA"):
        #Publish
        pass

def sendMessageToSpeaker(speakerId,status):
    try:
        speakerAux = savedSpeakers[speakerId]
        speakerPublishTopic = speakerAux["publishTopic"]
        template = speakerAux["template"]
        statusSelected = speakerAux["status"][status]
        msg = template.replace("%_v%",statusSelected)
        sendMessage(speakerPublishTopic,msg)
    except:
        print("[Switch Speaker Error]: An exception occurred switching Speaker [id: "+speakerId+"] status")

def switchSpeakersStatus(speakerId,status):
    if(speakerId=="all"):
        for speakerKey in list(savedSpeakers.keys()):
            sendMessageToSpeaker(speakerKey,status)
    else:
        sendMessageToSpeaker(speakerId,status)

def executeAplay(audioFile):
    try:
        subprocess.run(['aplay', soundsFolder+audioFile])
    except:
        print("[Aplay Error]: An exception occurred using Aplay")

def reproduceMessage(speakerId,message):
    audioFile = audiosFilename.get(message)
    if(audioFile==None): return # Close if not filename founded
    print(f"Reproducing Audio: {audioFile}")
    switchSpeakersStatus(speakerId,"1")
    executeAplay(audioFile)
    switchSpeakersStatus(speakerId,"0")

def on_message(client, userdata, message):
    topicRecieved = message.topic
    speakerId = topicRecieved.split("/")[-2]
    messageRecieved = str(message.payload.decode("utf-8"))
    print("[Topic]:",topicRecieved,"[Message Recieved]:",messageRecieved)
    reproduceMessage(speakerId,messageRecieved)

def createMqttClient():
    #global client
    print("Configuring Mqtt...")
    client = mqtt.Client(client_id=clientId, clean_session=False, userdata=None, protocol=mqtt.MQTTv311, transport="tcp")
    client.on_message=on_message #attach function to callback
    client.username_pw_set(username=mqttUser, password=mqttPass)
    client.connect(broker_address) #connect to broker
    client.subscribe(topicSub)
    print("Mqtt client created.")
    client.loop_forever() #start the loop

def main():
    print("Starting Speaker Manager...")
    createMqttClient()

main()
