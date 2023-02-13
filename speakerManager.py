import sys
import paho.mqtt.client as mqtt
import paho.mqtt.publish as mqttpublish
import requests
import secrets
import subprocess
import threading
import time

broker_address = secrets.BROKER_ADDRESS
topicSub = "speaker-message/+/message"
topicSubStop = "speaker-message/+/stop"
#soundsFolder = "/home/developer/sounds/"
soundsFolder = "sounds/"
apiKey = secrets.API_KEY
chatId = secrets.CHAT_ID
mqttUser = secrets.MQTT_USER
mqttPass = secrets.MQTT_PASS
clientId = "SpeakerManager"
client = None
queueFilesToReproduce = []
queueFilesToStop = []
queueFilesPlaying = {}

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

def sendMessage(topic,message):
    print("Sending:",topic,message)
    client.publish(topic,message,qos=1,retain=False)

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
    global queueFilesPlaying
    try:
        if(queueFilesPlaying.get(audioFile)!=None):
            print("Audio already executing")
            killAplayProcess(audioFile)
        sub_process_aux = subprocess.Popen(['aplay', soundsFolder+audioFile])
        queueFilesPlaying[audioFile]=sub_process_aux
            
    except:
        print("[Aplay Error]: An exception occurred using Aplay")

def reproduceMessage(speakerId,message):
    audioFile = audiosFilename.get(message)
    if(audioFile==None): return # Close if not filename founded
    print(f"Reproducing Audio: {audioFile}")
    switchSpeakersStatus(speakerId,"1")
    time.sleep(1.5)
    executeAplay(audioFile)
    time.sleep(0.5)
    switchSpeakersStatus(speakerId,"0")

def stopMessage(message):
    global queueFilesPlaying
    audioFile = audiosFilename.get(message)
    if(audioFile==None): return # Close if not filename founded
    killAplayProcess(audioFile)

def killAplayProcess(audioFile):
    print(f"Stopping Audio file: {audioFile}...")
    try:
        sub_process_aux = queueFilesPlaying[audioFile]
        sub_process_aux.kill()
        print(f"Stopped")
    except:
        print(f"Unable to kill audio file: {audioFile}")

def on_message(client, userdata, message):
    global queueFilesToReproduce
    topicRecieved = message.topic
    if(topicRecieved.split("/")[-1] == topicSub.split("/")[-1]):
        speakerId = topicRecieved.split("/")[-2]
        messageRecieved = str(message.payload.decode("utf-8"))
        print("[Topic]:",topicRecieved,"[Message Recieved]:",messageRecieved)
        queueFilesToReproduce.append((speakerId,messageRecieved))
    elif(topicRecieved.split("/")[-1] == topicSubStop.split("/")[-1]):
        messageRecieved = str(message.payload.decode("utf-8"))
        queueFilesToStop.append(messageRecieved)

def createMqttClient():
    global client
    print("Configuring Mqtt...")
    client = mqtt.Client(client_id=clientId, clean_session=False, userdata=None, protocol=mqtt.MQTTv311, transport="tcp")
    client.on_message=on_message #attach function to callback
    client.username_pw_set(username=mqttUser, password=mqttPass)
    client.connect(broker_address) #connect to broker
    client.subscribe(topicSub)
    client.subscribe(topicSubStop)
    print("Mqtt client created.")
    #client.loop_forever() #start the loop
    client.loop_start()

def reproduceThreadLoop():
    global queueFilesToReproduce
    print("Executing reproduceThreadLoop")
    while True:
        if(len(queueFilesToReproduce)>0):
            speakerId,message = queueFilesToReproduce.pop(0)
            reproduceMessage(speakerId,message)
        if(len(queueFilesToStop)>0):
            stopMessage(queueFilesToStop.pop(0))
            
def main():
    print("Starting Speaker Manager...")
    createMqttClient()
    reproduceThreadLoop()

main()
