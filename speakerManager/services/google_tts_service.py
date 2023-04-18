import wave
from contextlib import closing
from google.cloud import texttospeech

class GoogleTTSService:
    def __init__(self, key_path):
        self.client = texttospeech.TextToSpeechClient.from_service_account_file(key_path)
        self.voice_en = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Neural2-F")
        self.voice_es = texttospeech.VoiceSelectionParams(language_code="es-US", name="es-US-Neural2-C")
        self.audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)

    def generate_audio(self, text_to_send, filename,language="en"):
        speech_lines = SpeechSplitter.divide_text_by_newline(text_to_send)
        audio_files_name = []
        for i, speech_line in enumerate(speech_lines):
            file_name = f"output_temp_{i}.wav"
            self._generate_audio_from_speech(speech_line,file_name,language)
            audio_files_name.append(file_name)
        AudioMerger.merge_audio_files(audio_files_name,filename)

    def _generate_audio_from_speech(self, text_to_send, filename,language="en"):
        voice_to_use = self.voice_en
        if(language=="es"):
            voice_to_use = self.voice_es
        synthesis_input = texttospeech.SynthesisInput(text=text_to_send)
        request = texttospeech.SynthesizeSpeechRequest(input=synthesis_input, voice=voice_to_use, audio_config=self.audio_config)
        print(f"Sending text to google: {text_to_send}")
        response = self.client.synthesize_speech(request=request)

        with open(filename, 'wb') as out:
            out.write(response.audio_content)

class SpeechSplitter():

    @staticmethod
    def divide_text_by_newline(text, max_bytes=600):
        lines = text.split('\n')
        groups = []
        current_group = ''
        for line in lines:
            if len(line.encode()) <= max_bytes:
                current_group = SpeechSplitter._add_to_group(current_group, line, groups, max_bytes)
            else:
                current_group = SpeechSplitter._split_long_line(line, current_group, groups, max_bytes)
        SpeechSplitter._add_current_group(groups, current_group)
        return groups

    @staticmethod
    def _add_to_group(current_group, line, groups, max_bytes):
        if len(current_group.encode() + line.encode()) > max_bytes:
            SpeechSplitter._add_current_group(groups, current_group)
            current_group = line
        else:
            current_group += line
        return current_group

    @staticmethod
    def _split_long_line(line, current_group, groups, max_bytes):
        while len(line) > 0:
            limit = min(len(line), max_bytes)
            index = line.rfind('. ', 0, limit) + 1
            if index == 0:
                index = limit
            fragment = line[:index]
            current_group = SpeechSplitter._add_to_group(current_group, fragment, groups, max_bytes)
            line = line[len(fragment):]
        return current_group

    @staticmethod
    def _add_current_group(groups, current_group):
        if current_group:
            groups.append(current_group)

class AudioMerger:

    @classmethod
    def merge_audio_files(cls, file_paths, output_path):
        output_file = cls._create_output_file(file_paths[0], output_path)

        for file_path in file_paths:
            input_file = cls._open_input_file(file_path)
            cls._append_audio_data(output_file, input_file)
            input_file.close()

        output_file.close()

    @staticmethod
    def _create_output_file(first_file_path, output_path):
        with closing(wave.open(first_file_path, 'rb')) as first_file:
            output_file = wave.open(output_path, 'wb')
            output_file.setnchannels(first_file.getnchannels())
            output_file.setsampwidth(first_file.getsampwidth())
            output_file.setframerate(first_file.getframerate())
            return output_file

    @staticmethod
    def _open_input_file(file_path):
        input_file = wave.open(file_path, 'rb')
        return input_file

    @staticmethod
    def _append_audio_data(output_file, input_file):
        num_frames = input_file.getnframes()
        audio_data = input_file.readframes(num_frames)
        output_file.writeframes(audio_data)