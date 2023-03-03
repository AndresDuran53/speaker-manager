from google.cloud import texttospeech

class GoogleTTSHandler:
    def __init__(self, key_path):
        self.client = texttospeech.TextToSpeechClient.from_service_account_file(key_path)
        self.voice_en = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Neural2-C")
        self.audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
    
    def generate_audio(self, text_to_send, filename):
        print("Sending text to google")
        synthesis_input = texttospeech.SynthesisInput(text=text_to_send)
        request = texttospeech.SynthesizeSpeechRequest(input=synthesis_input, voice=self.voice_en, audio_config=self.audio_config)
        response = self.client.synthesize_speech(request=request)

        with open(filename, 'wb') as out:
            out.write(response.audio_content)