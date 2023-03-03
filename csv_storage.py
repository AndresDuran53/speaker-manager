import os
import csv
import datetime

class CSVStorage:
    def __init__(self, csv_filename):
        self.csv_filename = csv_filename
        self.create_if_not_exists()

    def create_if_not_exists(self):
        if not os.path.exists(self.csv_filename):
            with open(self.csv_filename, 'w') as f:
                f.write('')
    
    def get_today_date_string(self):
        date_format = '%Y-%m-%d'
        return datetime.datetime.now().strftime(date_format)

    def read_csv(self):
        data = {}
        with open(self.csv_filename, mode='r') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                date_str, value = row
                data[date_str] = int(value)
        return data
    
    def write_csv(self, data):
        with open(self.csv_filename, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            for date_str, value in data.items():
                csv_writer.writerow([date_str, value])

    def get_value_for_date(self, date_str=None):
        if date_str is None:
            date_str = self.get_today_date_string()

        data = self.read_csv()
        value = data.get(date_str, 0)
        return value
    
    def set_key_value_csv(self, key, value):
        data = self.read_csv()
        data[key] = value
        self.write_csv(data)

    def set_value_for_today(self, value):
        date_str = self.get_today_date_string()
        data = self.read_csv()
        data[date_str] = value
        self.write_csv(data)
    
    def increase_value_for_today_by(self, value):
        date_str = self.get_today_date_string()
        data = self.read_csv()
        stored_value = self.get_value_for_date()
        data[date_str] = stored_value+value
        self.write_csv(data)