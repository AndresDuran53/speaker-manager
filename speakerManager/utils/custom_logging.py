from datetime import datetime

class CustomLogging:

    def __init__(self, file_name):
        self.file_name = file_name

    def debug(self, message):
        self.log('DEBUG', message)

    def info(self, message):
        self.log('INFO', message)

    def warning(self, message):
        self.log('WARNING', message)

    def error(self, message):
        self.log('ERROR', message)

    def log(self, level, message):
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        final_message = f'[{timestamp}] {level} - {message}\n'
        print(final_message)
        with open(self.file_name, 'a') as file:
            file.write(final_message)