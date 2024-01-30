from luma.core.interface.serial import i2c, spi
from luma.oled.device import ssd1306, sh1106
from luma.core.render import canvas
from PIL import ImageDraw, ImageFont, Image
from time import sleep
from datetime import datetime
import os, math, signal, subprocess, psutil
import sqlite3

SECONDS_IN_A_DAY = 86400
database_path = '/root/Reports/database.db'

IP_command = "/sbin/ip -4 -o a | cut -d ' ' -f 2,7 | cut -d '/' -f 1"


serial = i2c(port=0, address=0x3C)
device = sh1106(serial, rotate=0)  

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
IMAGE_FILE = "/root/utilities/oled_controller/images/embedos_logo.png"

logo_x_offset =  6                  #original 7
logo_y_offset = 5                   #original 5

OLED_X = 128
OLED_Y = 64
NUMBER_R = 25
HOUR_HAND_LENGTH = 10   
MINUTE_HAND_LENGTH = 15
Y_OFFSET = 5

font = ImageFont.load_default()

font2 = ImageFont.truetype("/root/utilities/oled_controller/fonts/Volter__28Goldfish_29.ttf", 12)
font3 = ImageFont.truetype("/root/utilities/oled_controller/fonts/Exo_Regular400.ttf", 12)
font4 = ImageFont.truetype("/root/utilities/oled_controller/fonts/Red_Alert.ttf", 12)


def clear_display():
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
            
#Dispaly embedos logo     
def show_logo(device):
    with canvas(device) as draw:
        logo = Image.open(IMAGE_FILE)
        draw.bitmap((logo_x_offset, logo_y_offset), logo, fill=1)
        draw.text((10,  logo_y_offset + 30), "      info@embedos.io  ",font=font4,fill=255)
        draw.text((10,  logo_y_offset + 42), "      www.embedos.io  ",font=font4,fill=255)


def show_hostname(device, hostname='emap000'):
        with canvas(device) as draw:
            draw.text((5,  10), "- - - - - HOSTNAME - - - - - ", font=font4,  fill=255)
            draw.text((0,  35), "             " + hostname, font=font4, fill=255)


def show_clock(device):
        with canvas(device) as draw:
            hour = int((datetime.now()).strftime("%H"))
            if hour > 12:
                hour = hour - 12
            minute = int((datetime.now()).strftime("%M"))
            if minute == 0:
                minute = 60
            hour_angle = ((hour*30) + (minute/2) - 90)*2*3.14/360
            minute_angle = ((minute*6) - 90)*2*3.14/360 
            for i in range(12):
                draw.text((OLED_X/2 + NUMBER_R*math.cos(((i+1)*30 - 90)*2*3.14/360),OLED_Y/2 + NUMBER_R*math.sin(((i+1)*30 - 90)*2*3.14/360) - Y_OFFSET), str(i+1),fill=255)
            draw.line((OLED_X/2, OLED_Y/2, OLED_X/2 + HOUR_HAND_LENGTH*math.cos(hour_angle), OLED_Y/2 + HOUR_HAND_LENGTH*math.sin(hour_angle)), fill=255)
            draw.line((OLED_X/2, OLED_Y/2, OLED_X/2 + MINUTE_HAND_LENGTH*math.cos(minute_angle), OLED_Y/2 + MINUTE_HAND_LENGTH*math.sin(minute_angle)), fill=255)

def device_status():
        resp = subprocess.Popen(IP_command, shell=True, stdout=subprocess.PIPE)
        out, err = resp.communicate()
        IP_Interfaces = out.decode().split('\n')
        device_time = str((datetime.now()).strftime("%d-%m-%Y %H:%M"))

        with canvas(device) as draw: 
            y_coordinate = 0
            draw.text((0,  y_coordinate), "- - - - DEVICE DETAILS - - - - ", font=font4, fill=255)
            y_coordinate = y_coordinate + 10

            try:       
                draw.text((1,  y_coordinate + 10), "TIME : " + device_time, font=font4, fill=255)
                y_coordinate = y_coordinate + 15
            except Exception as e:
                # print("ERROR getting Time: " + str(e))
                pass

            for interface in IP_Interfaces:
                if interface != '':
                    iface = (interface.split(' ')[0])[:6]
                    if iface != 'lo':
                        if iface[:3].lower() == 'wlx': iface = 'wi-fi'
                        try:
                            ip = (interface.split(' ')[1])
                            iface_ip = ' '.join((iface, ":", ip))
                        except Exception as err:
                            iface_ip = ' '.join((iface, ":", "ERROR"))

                        draw.text((1,  y_coordinate + 10), iface_ip, font=font4, fill=255)
                        y_coordinate = y_coordinate + 15


def application(last_date, last_count):
     with canvas(device) as draw:
         draw.text((0,  5), "- - - - - - - DATE - - - - - - - ", font=font4,  fill=255)
         draw.text((35,  20), last_date, font=font4,  fill=255)
         
         draw.text((0,  35), "- - - - TOTALIZED VALUE - - - - ",font=font4,  fill=255)
         draw.text((55,  50), last_count, font=font3, fill=255)


def get_counts():
    con = sqlite3.connect(database_path)
    cur = con.cursor()

    query = 'SELECT * FROM ALL_COUNTS_TABLE ORDER BY ROWID DESC LIMIT 1;'
    cur.execute(query)
    data = cur.fetchone()

    req_data = list(data)
    day = req_data[0] if len(req_data[0]) > 1 else '0' + req_data[0]
    month = req_data[1] if len(req_data[1]) > 1 else '0' + req_data[1]
    year = req_data[2]
    last_date = day + "/" + month + "/" + year
    last_count = req_data[3]

    con.commit()
    con.close()

    if data is None:
        return None
    else:
        return [last_date, last_count]


def main():
    with open("/etc/hostname", 'r') as host_file:
        hostname = str(host_file.readline())
        host_file.close()

    while 1 :
        clear_display()     
        show_logo(device)
        sleep(5)
        clear_display()

        show_hostname(device, hostname)
        sleep(5)
        clear_display()

        show_clock(device)
        sleep(5)
        clear_display()

        device_status()
        sleep(5)
        clear_display()

        result_application = get_counts()
        if result_application is not None:
            last_date, last_count = result_application
            application(last_date, last_count)
            sleep(5)
            clear_display()
        else:
            # print("Error: Unable to retrieve counts.")
            pass

main()
    