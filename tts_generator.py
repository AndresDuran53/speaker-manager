import os
from tts_services.google_tts_handler import GoogleTTSHandler
from csv_storage import CSVStorage

class TextToSpeechGenerator:
    tts_handler = None
    max_characters_per_requests = 1500
    max_characters_per_day = 30000
    max_characters_per_month = 900000
    used_chars_filename = 'charactersSended.txt'

    def __init__(self,config_file):
        self.set_google_as_tts_handler(config_file)
        self.storage_characters_used = CSVStorage(self.used_chars_filename)

    def set_google_as_tts_handler(self,config_file):
        self.max_characters_per_requests = 1500
        self.max_characters_per_day = 30000
        self.max_characters_per_month = 900000
        self.tts_handler = GoogleTTSHandler(config_file)


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

    def generate_audio_file(self,text_to_send,output_filename,language="en"):
        if(not self.can_synthesize_audio(text_to_send)):
            print("Cannot synthesize audio. Character limit reached.")
            return
        print("Generating audio from text")
        self.tts_handler.generate_audio(text_to_send, output_filename,language)
        self.update_amount_used_chars(text_to_send)