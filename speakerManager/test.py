from utils.ConfigurationReader import ConfigurationReader
from services.spotify_service import SpotifyService, SpotifyConfig

config_data = ConfigurationReader().read_config_file()
config = SpotifyConfig.from_json(config_data)
spotify_service = SpotifyService(config)

devices = spotify_service.get_devices()
print(f"devices {devices}")
for device in devices:
    print(device.name)
    print(device.id)