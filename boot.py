import time
import sys
from machine import Pin #type:ignore

'''all configuration data is located in Program.py
    except:
    - the stop-ids for the different lines and stations, 
        which are used to generate the API request, see __get_meassured_ids in DataConversion.py
    - the API URL, 
        which is generated in __generateAPI_URL in DataConversion.py
    - constants for conversion of countdown time to minutes, 
        see delta_minutes in Monitors.py
    - constants for the display of the departure information, 
        see get_item_x_positions in Monitors.py
    - MAX_ITEMS_PER_PLATFORM, 
        which is the maximum number of departures per platform that are processed, 
        see __get_departures_direction_mode in DataConversion.py
'''
from Program import WienerLinienMonitor

WLM = WienerLinienMonitor()

incr_val = 1
while not WLM.connect_WLAN():
    WLM.update_RGB(r = incr_val%2)
    incr_val += 1
    time.sleep(10)

WLM.update_RGB(r = 0)

def turn_off(_):
    WLM.update_RGB(r = 1,b = 1)
    WLM.cleanup()
    time.sleep(2)
    sys.exit(0)
p_Interrupt = Pin(13,Pin.IN,Pin.PULL_UP)
p_Interrupt.irq(handler = turn_off, trigger = Pin.IRQ_FALLING)

WLM.display()
turn_off(None)