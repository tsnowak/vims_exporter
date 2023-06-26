import os
import sys
from datetime import datetime

import validators
from icalendar import Calendar, Event
from PyQt5.QtCore import QDateTime, QSize
from PyQt5.QtWidgets import (
    QApplication,
    QDateEdit,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
)
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.driver = None

        self.setWindowTitle("VIMS Exporter")

        # vims url input
        self.w_vims_url_label = QLabel("VIMS URL:", self)
        self.w_vims_url_label.move(10, 10)
        self.w_vims_url = QLineEdit(self)
        self.w_vims_url.setGeometry(100, 10, 200, 30)

        # date range
        self.w_date_range_label = QLabel("Date Range:", self)
        self.w_date_range_label.move(10, 50)
        self.w_start_date_range = QDateEdit(self, calendarPopup=True)
        self.w_start_date_range.setDateTime(QDateTime.currentDateTime())
        self.w_start_date_range.setGeometry(100, 45, 100, 40)
        self.w_end_date_range = QDateEdit(self, calendarPopup=True)
        self.w_end_date_range.setDateTime(QDateTime.currentDateTime())
        self.w_end_date_range.setGeometry(200, 45, 100, 40)

        # username
        self.w_username_label = QLabel("VIMS Username: ", self)
        self.w_username_label.move(10, 90)
        self.w_username = QLineEdit(self)
        self.w_username.setGeometry(125, 90, 200, 30)

        # password
        # TODO: make it passwordy
        self.w_password_label = QLabel("VIMS Password: ", self)
        self.w_password_label.move(10, 130)
        self.w_password = QLineEdit("", self)
        self.w_password.setGeometry(125, 130, 200, 30)

        # output path
        self.w_output_label = QLabel("Output Path: ", self)
        self.w_output_label.move(10, 170)
        self.w_output_button = QPushButton("Select Output Folder", self)
        self.w_output_button.clicked.connect(self._open_file_dialog)
        self.w_output_button.setGeometry(125, 170, 200, 30)
        self.w_output = QLineEdit("", self)
        self.w_output.setGeometry(10, 210, 380, 30)

        # create status bar
        self.w_status_label = QLabel("Status: ", self)
        self.w_status_label.move(10, 250)
        self.status = QLineEdit("", self)
        self.status.move(60, 250)
        self.status.resize(180, 30)

        # Create a button in the window
        self.button = QPushButton("Download .ics", self)
        self.button.clicked.connect(self.on_start)
        self.button.setGeometry(250, 250, 150, 40)

        self.setFixedSize(QSize(400, 300))

    def __del__(
        self,
    ):
        if self.driver:
            self.driver.close()

    def _status(self, text):
        self.status.setText(text)

    def _open_file_dialog(self):
        d = QFileDialog(self, "Select Output Folder")
        out = d.getExistingDirectory()
        self.w_output.setText(out)

    def create_driver(
        self,
    ):
        options = Options()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(options=options)
        return driver

    def login(self, url, username, password):
        self.driver.get(url)

        # handle failure to fetch fields and login
        try:
            username_field = self.driver.find_element(By.NAME, "user_name")
            password_field = self.driver.find_element(By.NAME, "password")
            username_field.send_keys(username)
            password_field.send_keys(password)
            self.driver.find_element(By.NAME, "submit").click()
        except Exception as e:
            self._status(f"Error. Incompatible site. {e}")
            return False

        # handle login fail
        try:
            # NOTE: hard coded vims user homepage address
            WebDriverWait(self.driver, 3).until(
                lambda driver: "rcs_home_user.php" in self.driver.current_url
            )
            return True
        except TimeoutException:
            self._status("VIMS Login Failed")
            return False

    def parse_vims_calendar(self, url, start_date, end_date):
        cal_url = f"{url}/rcs_print_calendar.php?txtFrom={start_date}&txtTo={end_date}"
        self.driver.get(cal_url)
        tags = self.driver.find_elements(By.TAG_NAME, "td")
        # first event info appears at element 9
        events = tags[9:]
        events = [x.text for x in events]
        # [start, end, description, creator, accepted, <blank>], repeat
        nfields = 6
        nevents = len(events) // nfields

        # create list of lists for events and fields
        events_list = []
        for n in range(nevents):
            events_list.append(events[(n * nfields) : ((n + 1) * nfields)])

        parsed_events_list = []
        for event in events_list:
            # ex: '05/03/2023\n6:30 PM'
            start_text = event[0].replace("\n", " ")
            # ex: '05/03/2023\n8:30 PM'
            end_text = event[1].replace("\n", " ")
            # ex: 'Class presentations on Helicopters (Terry) and Drones (Emma)'
            title_text = event[2]
            # ex: 'Kelly Thomas'
            creator_text = event[3]
            # ex: 'James Lewis,\nPaul Kelly'
            attendees_text = event[4].replace(",\n", ",")

            # parse dates
            format = "%m/%d/%Y %I:%M %p"
            start_date = datetime.strptime(start_text, format)
            end_date = datetime.strptime(end_text, format)

            out_dict = {
                "title": title_text,
                "creator": creator_text,
                "attendees": attendees_text,
                "start": start_date,
                "end": end_date,
            }

            parsed_events_list.append(out_dict)

        return parsed_events_list

    def create_ics_calendar(self, events):
        cal = Calendar()
        for e in events:
            event = Event()
            event.add("summary", e["title"])
            event.add("dtstart", e["start"])
            event.add("dtend", e["end"])
            # NOTE: creator and attendees not currently used
            # Adding events to calendar
            cal.add_component(event)
        return cal

    def save_ics_file(self, cal, out_path):
        file_path = f"{str(out_path)}/vims_cal.ics"
        with open(file_path, "wb") as f:
            f.write(cal.to_ical())

    def on_start(self):
        url = self.w_vims_url.text()
        start_date = self.w_start_date_range.date().toString("MM/dd/yyyy")
        end_date = self.w_end_date_range.date().toString("MM/dd/yyyy")
        username = self.w_username.text()
        password = self.w_password.text()
        output_path = self.w_output.text()

        # verify URL
        url, ok = check_url(url)
        if not ok:
            self._status("Bad URL.")
            return None

        # verify output path
        if not os.path.exists(output_path):
            self._status("Invalid output path.")
            return None

        self.driver = self.create_driver()
        if not self.login(url, username, password):
            return None

        events = self.parse_vims_calendar(url, start_date, end_date)
        if len(events) == 0:
            self._status("No events.")
            return None

        cal = self.create_ics_calendar(events)
        self.save_ics_file(cal, output_path)

        self._status("Success!")


def check_url(url):
    if "http" not in url:
        url = "http://" + url
    if "index.php" in url:
        url = url.split("index.php")[0]
    if url[-1] == "/":
        url = url[:-1]
    return url, validators.url(url)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
