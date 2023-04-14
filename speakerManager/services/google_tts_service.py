from google.cloud import texttospeech

class GoogleTTSService:
    def __init__(self, key_path):
        self.client = texttospeech.TextToSpeechClient.from_service_account_file(key_path)
        self.voice_en = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Neural2-C")
        self.voice_es = texttospeech.VoiceSelectionParams(language_code="es-US", name="es-US-Neural2-C")
        self.audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
    
    def generate_audio(self, text_to_send, filename,language="en"):
        print("Sending text to google")
        voice_to_use = self.voice_en
        if(language=="es"):
            voice_to_use = self.voice_es
        synthesis_input = texttospeech.SynthesisInput(text=text_to_send)
        request = texttospeech.SynthesizeSpeechRequest(input=synthesis_input, voice=voice_to_use, audio_config=self.audio_config)
        response = self.client.synthesize_speech(request=request)

        with open(filename, 'wb') as out:
            out.write(response.audio_content)