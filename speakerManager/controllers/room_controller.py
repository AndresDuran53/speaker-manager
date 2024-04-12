from utils.custom_logging import CustomLogging

class Room:
    name: str
    speakers: list[str]

    def __init__(self,name: str):
        self.name = name.lower()
        self.speakers = []
    
    def add_speaker(self,speaker_id: str):
        self.speakers.append(speaker_id)

class RoomController:
    __instance = None
    rooms: list

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance
    
    def __init__(self, config_data, logger:CustomLogging):
        if not hasattr(self, 'rooms'):
            self.logger = logger
            self.logger.info("Creating Room Controller...")
            self._configuration()
            self.add_rooms_from_json(config_data)
            
    def _configuration(self):
        self.rooms = []

    def add_room(self, room_name: str) -> Room:
        room_name = room_name.lower()
        found_room = self.find_existing_room_by_name(room_name)
        if(found_room is None):
            room = Room(room_name)
            self.rooms.append(room)
            return room

    def add_speaker_id_to_room(self, room_name: str, speaker_id: str):
        found_room = self.find_existing_room_by_name(room_name)
        if(found_room is None):
            raise Exception("Room not found.")
        found_room.add_speaker(speaker_id)

    def find_existing_room_by_name(self,room_name: str) -> Room:
        room_name = room_name.lower()
        for room_aux in self.rooms:
            if room_aux.name == room_name:
                return room_aux
        return None

    def get_rooms_from_topic(self,topic: str) -> list[Room]:
        final_list = []
        rooms_names = topic.split("-")
        for room_name_aux in rooms_names:
            room_name_aux = room_name_aux.lower()
            if(room_name_aux == "all"): 
                return self.rooms[:]
            found_room = self.find_existing_room_by_name(room_name_aux)
            if(not found_room is None): final_list.append(found_room)
        return final_list
    
    def add_rooms_from_json(self, json_data):
        rooms = json_data["rooms"]
        for room in rooms:
            name = room["name"]
            devices = room["devices"]
            new_room = self.add_room(name)
            for device in devices:
                new_room.add_speaker(device)