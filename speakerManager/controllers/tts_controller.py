import os
from services.google_tts_service import GoogleTTSService
from utils.csv_storage import CSVStorage
from utils.custom_logging import CustomLogging

class TextToSpeechGenerator:
    tts_handler = None
    max_characters_per_requests = 1500
    max_characters_per_day = 30000
    max_characters_per_month = 900000
    used_chars_filename = 'data/charactersSended.txt'
    audio_output_filename = "output.wav"

    def __init__(self, config_file, sounds_folder:str, logger:CustomLogging):
        self.logger = logger
        self.logger.info("Creating TextToSpeechGenerator Controller...")
        self.sounds_folder = sounds_folder
        self.set_google_as_tts_handler(config_file)
        self.storage_characters_used = CSVStorage(self.used_chars_filename)

    def set_google_as_tts_handler(self,config_file):
        self.max_characters_per_requests = 1500
        self.max_characters_per_day = 30000
        self.max_characters_per_month = 900000
        self.tts_handler = GoogleTTSService(config_file)


    def can_synthesize_audio(self, text_to_send):

        character_count = len(text_to_send)
        if(character_count > self.max_characters_per_requests): return False

        # Read current character count from file
        current_count = self.storage_characters_used.get_value_for_date()
        total_character_count = character_count + current_count

        if(total_character_count > self.max_characters_per_day): return False

        if(total_character_count > self.max_characters_per_month): return False
        
        return True
        
    def update_amount_used_chars(self,text_to_send):
        character_count = len(text_to_send)
        self.storage_characters_used.increase_value_for_today_by(character_count)

    def generate_audio_file(self,text_to_send,language="en"):
        output_filename = f"{self.sounds_folder}/{self.audio_output_filename}"
        if(not self.can_synthesize_audio(text_to_send)):
            print("Cannot synthesize audio. Character limit reached.")
            return False
        print("Generating audio from text")
        try:
            self.tts_handler.generate_audio(text_to_send, output_filename,language)
            self.update_amount_used_chars(text_to_send)
            return True
        except:
            print("Cannot synthesize audio. Google Error.")
            return False