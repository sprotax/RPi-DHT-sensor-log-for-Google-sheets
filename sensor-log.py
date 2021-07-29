"""
RaspberryPi-DHT-Sensor-Log

Copyright 2021, sprotax

https://github.com/sprotax


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the    
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
import sys
import time
from datetime import datetime
import os
import board
import adafruit_dht
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.request as request
import json
import logging
#wait 10 seconds to allow the raspberry to fully boot up
time.sleep(10)
current_time = datetime.now()
current_time = current_time.strftime("%d:%m:%Y %H:%M:%S")
log =f'./RaspberryPi-DHT-sensor-Log/logs/[{current_time}]info.log'


#enables logging of errors and warnings to "info.log"
print('Program started, Please look in info.log for warnings and errors')
logging.basicConfig(filename=log, filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d/%b/20%y %H:%M:%S')
logging.info('*****************************************')
logging.info('Program starting...')

#checks if a file named "stop" exists and terminates the program if so. 
#The file MUST be labled "stop" with no file extension like ".txt".
if os.path.exists('./stop'):
    logging.warning('Program stopped due file "stop" existing. Delete the file and restart the program.')
    quit()

#Gathers variable data from the config.json file to use in this program
with open('./sensor-log/config.json') as CONFIG:
    try:
        DATA = json.load(CONFIG)
        DHT = DATA['logger']['DHT-type']
        PIN = DATA['logger']['GPIO-pin']
        MAX_ROWS = int(DATA['logger']['Max-Length'])
        INTERVAL = int(DATA['logger']['interval'])
        auth_key_file = DATA['certification']['json-authentication']
        SPREADSHEET = DATA['certification']['spreadsheet-name']
        LOCAL = DATA['logger']['Store-Data-locally']
    except: 
        logging.warning('An exception  occured while collecting infomation from the Json file, please check for propper spelling and grammer')
#Check if user entered data is accpetable. This is not a fool proof test yet.
try:
    #DHT
    if DHT == "DHT11" or DHT == 'DHT22':
        pass
    else:
        logging.error('This program only supports DHT11 or DHT22 sensor modules. We do not support: ' + DHT + ' .Please check spelling.')
        quit()
    #PIN
    parts = PIN.split('.')
    module = ".".join(parts[:-1])
    if module != "board":
        logging.error('please check spelling for GPIO-pin. please use the GPIO (A.K.A digital ) digital pin number')
        os.exit()
    #MAX_ROWS
    if MAX_ROWS < 3 or MAX_ROWS > 1500000 or type(MAX_ROWS) != int:
        logging.error('the number entered for maximum number of rows is outside the allowoed range of 4 to 1.5 million.')
        sys.exit()
    #INTERVAL
    if INTERVAL < 4 or type(INTERVAL) != int:
        logging.error('the minium delay required is 5 seconds')
    #OUATH_KEY_FILE
    if os.path.exists(OUATH_KEY_FILE):
        pass
    else:
        logging.error('The authentication Json file (' + OUATH_KEY_FILE +') does not exist, please check spelling and that it is in the same folder')
except:
    logging.warning('An exception  occured while checking user inputed data from the Json file, please check for propper spelling and grammer.')

#Establish a connection with the google API to send the data. 
def login_logger():
    try:
        LOOKUP =  ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        CREDENTIALS = ServiceAccountCredentials.from_json_keyfile_name(auth_key_file, LOOKUP)
        GOOGLE_SHEET = gspread.authorize(CREDENTIALS)
        log_sheet = GOOGLE_SHEET.open(SPREADSHEET).sheet1 
        return log_sheet
    except Exception as e: 
        logging.error('Google sheet login failed with error:', e)
        quit()

#Setup the Google Sheet header (A1 to C3) to label each columan with what they represent.
#Tell which DHT device is being used
log_sheet = login_logger()
if DHT == "DHT11":
    DHT_TYPE = adafruit_dht.DHT11
    log_sheet.update('A1:C3', [["Date / Time", "Temperature (0 ~ 50℃ )", "Humidity (20 - 90% RH)"], ["DD/MM/YY  HH:MM:SS", "Celsius (±2℃)", "Humidity (±5% RH)"]])

elif  DHT == "DHT22":
    DHT_TYPE = adafruit_dht.DHT22
    log_sheet.update('A1:C3', [["Date / Time", "Temperature (-40 ~ 80℃ )", "Humidity (0 - 100% RH)"], ["DD/MM/YY  HH:MM:SS", "Celsius (±0.5℃)", "Humidity (±2% RH)"]])
else:
    print("logger.py -- the DHT entered in the config.json is unkown. I currently only support DHT11 and DHT22 sensors")

#Takes a string and returns the relative class function back. 
#It is being used to tell the program which  raspberry pi pin is being used for the sensor
#This fumction comes from 
#https://stackoverflow.com/questions/452969/does-python-have-an-equivalent-to-java-class-forname
def get_class( str ):
    parts = str.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)            
    return m

#Initialize the DHT sensor
BOARD_PIN = get_class(PIN)
DHT_PIN  = BOARD_PIN
DHT_DEVICE = DHT_TYPE(DHT_PIN)  

#Get the temperature data from the DHT sensor.
def get_temp():
    try:
        temp = DHT_DEVICE.temperature
        return temp
    except:
        logging.warning("An exception has occured while collecting Temperature info from the DHT sensor.")    

#Get the humidity data from the DHT sensor.
def get_humidity():
    try:
        humidity = DHT_DEVICE.humidity
        return humidity
    except:
        logging.warning('An exception has occured while collecting Humidity info from the DHT sensor.')

#Collect the Date and Time data from the host machine (The raspberry pi).
#If the time is not correct type sudo raspi-config in cmd > 5 Localisation Options > L2 Timezone > and folllow the on screen prompts.
def get_time():
    try:
        current_time = datetime.now()
        current_time = current_time.strftime("%d/%m/%Y %H:%M:%S")
        return current_time
    except:
        logging.warning('An exception has occured while gathering Date and Time data')

#reset the Google API connection
log_sheet = None

logging.info(f'Program has Started, begining loop. I will run every {INTERVAL} seconds')

#begin an infinite loop of gathering infomation and posting it on the Google spreadsheet.
while True:
    
    #if the Google API is not logged in, log in now.
    if log_sheet is None:
        log_sheet = login_logger()
    
    #Try to receive data from the DHT sensor
    temp = get_temp()
    humidity = get_humidity()

    #Insure that the sensor provided readable data and if not wait 2 seconds and retry.
    while humidity is None or temp is None:
        time.sleep(2)
        temp = get_temp()
        humidity = get_humidity()

    #Get the total Length of the google spreadsheet and if at certain length delete oldest entered data.
    total_rows = len(log_sheet.get_all_values())
    if total_rows > MAX_ROWS:
        log_sheet.delete_rows(MAX_ROWS, total_rows)     

    #Try to send the data to the Gooogle spreadsheet.
    try:
        current_time = get_time()   
        log_sheet.insert_row((current_time, temp, humidity), index=3, value_input_option='RAW')
    except:
        logging.error('An error occured prevanting the addition of new sensor data.')
        logging.error(f'The Data was: {current_time} for current time, {temp}C for temperature, {humidity}% for humidity.')
        log_sheet = None
    #add the data to the "info.log" file
    if LOCAL:
        logging.info(f'The Temperature is {temp}C and the Relative humidity is {humidity}%')
    #wait the amount specifyed in the Json file
    time.sleep(INTERVAL)
