import os
from tts_services.google_tts_handler import GoogleTTSHandler

class TextToSpeechGenerator:
    tts_handler = None
    max_characters = 10000
    used_chars_filename = 'charactersSended.txt'

    def __init__(self,config_file):
        self.set_google_as_tts_handler(config_file)

    def set_google_as_tts_handler(self,config_file):
        self.tts_handler = GoogleTTSHandler(config_file)
        self.max_characters = 30000

    def can_synthesize_audio(self, text_to_send):
        
        # Create charactersSended.txt file if it doesn't exist
        if not os.path.exists(self.used_chars_filename):
            with open(self.used_chars_filename, 'w') as f:
                f.write('0')

        # Read current character count from file
        with open(self.used_chars_filename, 'r') as f:
            current_count = int(f.read())
        
        # Check if new character count exceeds maximum
        character_count = len(text_to_send)
        if current_count + character_count <= self.max_characters:
            return True
        else:
            return False
        
    def update_amount_used_chars(self,text_to_send):
        with open(self.used_chars_filename, 'r+') as f:
            character_count = len(text_to_send)
            current_count = int(f.read())
            f.seek(0)
            f.write(str(current_count + character_count))
            f.truncate()

    def generate_audio_file(self,text_to_send,output_filename):
        if(not self.can_synthesize_audio(text_to_send)):
            print("Cannot synthesize audio. Character limit reached.")
            return
        print("Generating audio from text")
        self.tts_handler.generate_audio(text_to_send, output_filename)
        self.update_amount_used_chars(text_to_send)