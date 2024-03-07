import subprocess

class VolumeController:
    audio_card_index = 0

    @staticmethod
    def _execute_command(volume):
        #command = f"amixer -c {VolumeController.audio_card_index} set 'Master' {volume}%"
        command = f"amixer set 'Master' {volume}%"
        subprocess.run(command, shell=True)

    @staticmethod
    def set_volume(volume):
        try:
            volume_float = float(volume)
            volume_int = round(volume_float)
            if 0 <= volume_int <= 100:
                VolumeController._execute_command(volume_int)
        except:
            pass
            
            
            