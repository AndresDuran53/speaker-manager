import subprocess

class VolumeController:

    @staticmethod
    def _execute_command(volume):
        command = f'amixer set PCM -M {volume}%'
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
            
            
            