import pychromecast
import time
from devices.speaker_interface import Speaker

class ChromecastAudioDevice(Speaker):
    def __init__(self, friendly_name, filespath):
        self.id = friendly_name
        self.cast = self._get_chromecast(friendly_name)
        self.filespath = filespath

    def _get_chromecast(self, friendly_name):
        chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=[friendly_name])
        return chromecasts[0] if chromecasts else None
    
    def play_audio(self, filename):
        if not self.cast:
            print("No se encontró el dispositivo Chromecast.")
            return
        media_url = f"{self.filespath}/{filename}"
        self._play_media(media_url)
    
    def _play_media(self, media_url):
        self.cast.wait()
        media_controller = self.cast.media_controller
        media_controller.play_media(media_url, 'audio/wav')
        media_controller.block_until_active()
        media_controller.play()
        while(not media_controller.status.player_is_playing):
            time.sleep(0.02)

    def stop(self):
        if not self.cast:
            print("No se encontró el dispositivo Chromecast.")
            return
        self.cast.media_controller.stop()

    def get_id(self):
        return self.id 
    
    def have_to_be_turned_on(self):
        return False
    
    def turn_off_if_apply(self): 
        return None

    @classmethod
    def get_by_id(cls,speaker_list,speaker_id): 
        for device in speaker_list:
            if device.id == speaker_id:
                return device
        return None

    @staticmethod
    def list_from_json(json_data):
        devices = json_data["chromecasts"]["devices"]
        host_path = json_data["chromecasts"]["hostPath"]
        chromecast_devices = []
        for device_name in devices:
            device = ChromecastAudioDevice(device_name, host_path)
            chromecast_devices.append(device)
        return chromecast_devices