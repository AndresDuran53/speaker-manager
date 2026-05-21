"""
SpeakerManager test client.

Sends MQTT commands directly to the broker, exercising the same topics the
running system subscribes to.  Run from the repository root so the config
file is resolved correctly:

    python speakerManager/test_actions.py list
    python speakerManager/test_actions.py speaker-on 25070A
    python speakerManager/test_actions.py play CloseGarage cocina
    python speakerManager/test_actions.py tts "Hello world" habitacion
    python speakerManager/test_actions.py volume 60
"""

import argparse
import sys
import time

import paho.mqtt.client as mqtt
from zarus_core import ConfigurationReader, CustomLogging

CONFIG_FILE = "conf/configuration.json"
logger: CustomLogging = None  # initialised in main()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    try:
        return ConfigurationReader.read_config_file(CONFIG_FILE)
    except FileNotFoundError:
        logger.error(f"Config file not found at '{CONFIG_FILE}'. Run this script from the repository root.")
        sys.exit(1)


def find_device(config: dict, speaker_id: str) -> dict | None:
    for device in config.get("devices", []):
        if device["id"] == speaker_id:
            return device
    return None


def build_speaker_message(device: dict, power: str) -> str:
    """power: '1' (on) or '0' (off). Returns the formatted MQTT payload."""
    status_value = device["status"][power]
    return device["template"].replace("%_v%", status_value)


# ---------------------------------------------------------------------------
# MQTT connection
# ---------------------------------------------------------------------------

DRY_RUN = False  # set to True via --dry-run flag


def connect_mqtt(config: dict) -> mqtt.Client | None:
    if DRY_RUN:
        return None
    mqtt_cfg = config["mqtt"]
    client = mqtt.Client(client_id="SpeakerManagerTest", clean_session=True)
    client.username_pw_set(mqtt_cfg["mqttUser"], mqtt_cfg["mqttPass"])
    client.connect(mqtt_cfg["brokerAddress"])
    client.loop_start()
    return client


def publish_and_disconnect(client: mqtt.Client | None, topic: str, message: str):
    if DRY_RUN:
        logger.info(f"[DRY-RUN] Would publish | topic: {topic} | message: {message}")
        return
    logger.info(f"Publishing | topic: {topic} | message: {message}")
    client.publish(topic, message, qos=1)
    time.sleep(0.5)  # let the QoS-1 handshake complete before disconnecting
    client.loop_stop()
    client.disconnect()
    logger.info("Done.")


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def action_list(config: dict):
    logger.info("=== Speakers ===")
    for d in config.get("devices", []):
        logger.info(f"  {d['id']}  ({d['type']})  publish: {d['publishTopic']}  subscribe: {d['subscribeTopic']}")

    cc = config.get("chromecasts", {})
    if cc.get("devices"):
        logger.info("=== Chromecasts ===")
        for name in cc["devices"]:
            logger.info(f"  {name}")

    logger.info("=== Rooms ===")
    for r in config.get("rooms", []):
        speakers = ", ".join(r["devices"]) or "(none)"
        logger.info(f"  {r['name']}  →  {speakers}")

    logger.info("=== Audio IDs ===")
    for a in config.get("audios", []):
        logger.info(f"  {a['id']:<30}  {a['file_name']}")


def action_speaker_on(client: mqtt.Client, config: dict, speaker_id: str):
    device = find_device(config, speaker_id)
    if device is None:
        logger.error(f"Speaker '{speaker_id}' not found. Run 'list' to see available speakers.")
        sys.exit(1)
    logger.info(f"Turning ON speaker '{speaker_id}'")
    publish_and_disconnect(client, device["publishTopic"], build_speaker_message(device, "1"))


def action_speaker_off(client: mqtt.Client, config: dict, speaker_id: str):
    device = find_device(config, speaker_id)
    if device is None:
        logger.error(f"Speaker '{speaker_id}' not found. Run 'list' to see available speakers.")
        sys.exit(1)
    logger.info(f"Turning OFF speaker '{speaker_id}'")
    publish_and_disconnect(client, device["publishTopic"], build_speaker_message(device, "0"))


def action_play(client: mqtt.Client, audio_id: str, room: str):
    logger.info(f"Playing '{audio_id}' in room '{room}'")
    publish_and_disconnect(client, f"speaker-message/{room}/reproduce", audio_id)


def action_stop(client: mqtt.Client, audio_id: str, room: str):
    logger.info(f"Stopping '{audio_id}' in room '{room}'")
    publish_and_disconnect(client, f"speaker-message/{room}/stop", audio_id)


def action_tts(client: mqtt.Client, text: str, room: str, lang: str):
    suffix = "tts" if lang == "en" else "tts-es"
    logger.info(f"TTS ({lang}) in room '{room}': \"{text}\"")
    publish_and_disconnect(client, f"speaker-message/{room}/{suffix}", text)


def action_volume(client: mqtt.Client, value: int):
    if not 0 <= value <= 100:
        logger.error("Volume must be between 0 and 100.")
        sys.exit(1)
    logger.info(f"Setting volume to {value}")
    publish_and_disconnect(client, "speaker-message/set-volume", str(value))


def action_spotify(client: mqtt.Client, event: str):
    logger.info(f"Sending Spotify event: '{event}'")
    publish_and_disconnect(client, "spotify/event", event)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SpeakerManager test client — sends MQTT commands to the running system.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Log what would be sent without connecting to the broker or publishing anything.",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("list", help="List speakers, rooms, and audio IDs from config")

    p = sub.add_parser("speaker-on", help="Turn on a speaker (sends directly to its MQTT topic)")
    p.add_argument("speaker_id", help="Device ID, e.g. 25070A")

    p = sub.add_parser("speaker-off", help="Turn off a speaker")
    p.add_argument("speaker_id", help="Device ID, e.g. 25070A")

    p = sub.add_parser("play", help="Play an audio file in a room")
    p.add_argument("audio_id", help="Audio ID from config, e.g. CloseGarage")
    p.add_argument("room", help="Room name, e.g. cocina")

    p = sub.add_parser("stop", help="Stop a playing audio in a room")
    p.add_argument("audio_id", help="Audio ID")
    p.add_argument("room", help="Room name")

    p = sub.add_parser("tts", help="Speak text aloud in a room (English)")
    p.add_argument("text", help="Text to synthesize")
    p.add_argument("room", help="Room name")

    p = sub.add_parser("tts-es", help="Speak text aloud in a room (Spanish)")
    p.add_argument("text", help="Text to synthesize")
    p.add_argument("room", help="Room name")

    p = sub.add_parser("volume", help="Set master volume (0–100)")
    p.add_argument("value", type=int, help="Volume level")

    p = sub.add_parser("spotify", help="Simulate a librespot Spotify event")
    p.add_argument("event", choices=["start", "play", "pause", "stop", "change"])

    return parser


def main():
    global logger
    CustomLogging.configure_project(project_name="test_actions", force_reconfigure=True)
    logger = CustomLogging(component_name="TestActions")

    args = build_parser().parse_args()
    config = load_config()

    if args.dry_run:
        global DRY_RUN
        DRY_RUN = True
        logger.info("Dry-run mode enabled — no messages will be published.")

    if args.action == "list":
        action_list(config)
        return

    client = connect_mqtt(config)

    if args.action == "speaker-on":
        action_speaker_on(client, config, args.speaker_id)
    elif args.action == "speaker-off":
        action_speaker_off(client, config, args.speaker_id)
    elif args.action == "play":
        action_play(client, args.audio_id, args.room)
    elif args.action == "stop":
        action_stop(client, args.audio_id, args.room)
    elif args.action == "tts":
        action_tts(client, args.text, args.room, "en")
    elif args.action == "tts-es":
        action_tts(client, args.text, args.room, "es")
    elif args.action == "volume":
        action_volume(client, args.value)
    elif args.action == "spotify":
        action_spotify(client, args.event)


if __name__ == "__main__":
    main()
