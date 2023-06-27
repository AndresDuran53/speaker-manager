import pychromecast
import time

class ChromecastAudioDevice():
    def __init__(self, friendly_name, filespath):
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
        mediaController = self.cast.media_controller
        mediaController.play_media(media_url, 'audio/wav')
        mediaController.block_until_active()
        mediaController.play()
        print(f"init mc {mediaController.status.player_is_playing}")
        while(not mediaController.status.player_is_playing):
            print(f"actual mc {mediaController.status.player_is_playing}")
            time.sleep(0.05)

    def stop(self):
        if not self.cast:
            print("No se encontró el dispositivo Chromecast.")
            return
        self.cast.media_controller.stop()

    @staticmethod
    def list_from_json(json_data):
        devices = json_data["chromecasts"]["devices"]
        host_path = json_data["chromecasts"]["hostPath"]
        chromecast_devices = []
        for device_name in devices:
            device = ChromecastAudioDevice(device_name, host_path)
            chromecast_devices.append(device)
        return chromecast_devices