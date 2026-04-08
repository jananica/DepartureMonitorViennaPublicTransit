import network #type:ignore
from datetime import timedelta
from machine import Pin, SPI, idle #type:ignore
import time

from micropython_ssd1322.xglcd_font import XglcdFont

from Monitors import Monitor
import DataConversion

#configuration data - displaying options
display_mode0 = {'flag_show_platform_nr': True, 'flag_show_line':False} #if 'flag_show_platform_nr' then the Platform number will be shown
display_mode1 = {'flag_show_platform_nr': False, 'flag_show_line':True} #if 'flag_show_line' then the line will be displayed
display_modes = [display_mode0,display_mode1]
Platform_Sides = ('LEFT','RIGHT') #Side the platform number should be shown, the i-th component refers to the i-th monitor
font_path = 'fonts/default_font.c' #string, path to font
display_text_spacing = 1 #unit: pixel(s), space between letters

#configuration data - time constants, ** all times are expressed in seconds **
TIME_BETWEEN_API_REQUESTS = 120 #time between updates of departure data
MIN_TIME_BETWEEN_API_REQUESTS = 15 #minimum time between API requests
ADVANCED_PREVIEW_ANIMATION_PERIOD = 4 #period switching between the second and third departure
UPDATE_PERIOD = 1 #should be at least 0.5*#(monitors), meassured time for update of one monitor is ~300ms

#configuration data - for input, all values as SoC numbers
LINES = ['U1','U2','U3','U4','U5','U6']
Pin_in_selectLine = [5,6,7] #these Pins are used to select the line
Pin_in_selectStation = [8,9,10,17,18] #these pins are usedd to select the 'station-index', see DataConversion.__get_meassured_ids
Pin_in_selectAdvancedPreview = 21
Pin_in_select_displaymode = 44

#configuration data - Pins for display connections
Pin_SCK = 48
Pin_COPI = 38
Pins_CS = (1,2) #the i-th component refers to the i-th monitor
Pins_DC = (4,12)
Pins_RST = (3,11)

#configuration data - Network credentials
ssid = 'wlan-ssid'
password = 'wlan-pw'

class WienerLinienMonitor:
    def __init__(self):
        ''' - configures GPIO pins and spi connection to monitors
        '''
        #setup GPIO
        self.p_selAdvPrev = Pin(Pin_in_selectAdvancedPreview,Pin.IN,Pin.PULL_UP)

        self.pl_lineSelect = []
        for pin_nr in Pin_in_selectLine:
            self.pl_lineSelect.append(Pin(pin_nr,Pin.IN,Pin.PULL_UP))
            
        self.pl_stationSelect = []
        for pin_nr in Pin_in_selectStation:
            self.pl_stationSelect.append(Pin(pin_nr,Pin.IN,Pin.PULL_UP))

        self.p_setDisplayMode = Pin(Pin_in_select_displaymode,Pin.IN,Pin.PULL_UP)

        #init the (on board) RGB LED 
        self.RED_LED = Pin(46,Pin.OUT, value = 0)
        self.GREEN_LED = Pin(0,Pin.OUT, value = 0)
        self.BLUE_LED = Pin(45,Pin.OUT, value = 0)

        #init Displays
        monitor_font = XglcdFont(font_path, 10, 16, letter_count=190)
        self.spi = SPI(1, baudrate=250000, sck=Pin(48), mosi=Pin(38))

        min_len = min(map(len,[Pins_CS,Pins_DC,Pins_RST,Platform_Sides]))
        self.Monitors:list[Monitor] = []
        for i in range(min_len):
            cs_i = Pins_CS[i]
            dc_i = Pins_DC[i]
            rst_i = Pins_RST[i]
            self.Monitors.append(Monitor(cs_i,dc_i,rst_i,self.spi,
                                         font = monitor_font,
                                         normal_spacing = display_text_spacing,
                                         period_advanced_preview = ADVANCED_PREVIEW_ANIMATION_PERIOD,
                                         platform_display_side = Platform_Sides[i]))
        self.AdvancedPrev = False
        self.displaymode = display_modes[0]

        for Mo in self.Monitors:
            Mo.update_advanced_preview(self.AdvancedPrev)
            Mo.update_display_variables(show_platform=self.displaymode['flag_show_platform_nr'],
                                       show_line=self.displaymode['flag_show_line'])
        self.departure_data = None

    def update_RGB(self,r=None,g=None,b=None):
        ''' sets light value of internal rgb-LED. 
            input: r,g,b: int {0,1} | None
                - 0 -> off
                - 1 -> on
                - None -> no change
            The LED is active low, hence the inverted values of r,g,b are used.
        '''
        if(r!=None):
            self.RED_LED.value(r-1)
        if(g!=None):
            self.GREEN_LED.value(g-1)
        if(b!=None):
            self.BLUE_LED.value(b-1)

    def connect_WLAN(self):
        '''attempts to connect to WLAN
        
            **returns:** true, if successful, false otherwise
        '''
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        try:
            if not wlan.isconnected():
                wlan.connect(ssid, password)
                while not wlan.isconnected():
                    idle()
        except OSError as err:
            print('An error occured while trying to connect to WLAN. \nMessage:',err)
            self.Monitors[0].show_debug_text('WLAN CONNECTION FAILED',8,32)
            return False
        print('connected to WLAN.')
        self.Monitors[0].clear(force_clear=True)
        return True
        
    def display(self):
        '''continuously displays departure data on monitors.

            breaks, if no valid data could be fetched for at least 10 consecutive attempts.
        '''
        while True:
            self.__read_input_and_update_monitors_if_neccessary()

            flag_have_valid_departure_data = self.departure_data!=None
            for _ in range(10):
                if(self.departure_data==None or time.time()-self.time_last_API_request>TIME_BETWEEN_API_REQUESTS):
                    if not self.__fetch_departure_data(): continue
                
                flag_have_valid_departure_data = True
                self.__update_displays()

            if(not flag_have_valid_departure_data):
                break

        print('No valid departure data could be fetched for a long time, stopping to display. ' \
        'Please check your network connection and the API status.')
        self.Monitors[0].show_debug_text('FETCHING DATA FAILED',8,8)
        self.Monitors[0].show_debug_text('TERMINATING PROGRAM',14,40, clear_first=False)
        time.sleep(10)

    def __read_input_and_update_monitors_if_neccessary(self):
        '''reads in all input pins and updates the monitors data if necessary.
        
        - Note: all entries are inverted because I used pullup-resistors
        '''
        new_AdvancedPrev = True if self.p_selAdvPrev.value()==0 else False
        if(new_AdvancedPrev!=self.AdvancedPrev):
            self.AdvancedPrev = new_AdvancedPrev
            self.monitors_update_advanced_preview()

        list_lineSelect = [1 - pin_id.value() for pin_id in self.pl_lineSelect]
        self.line_selected = LINES[int(''.join(map(str,list_lineSelect)),2)]

        list_stationSelect = [1 - pin_id.value() for pin_id in self.pl_stationSelect]
        self.station_index = int(''.join(map(str,list_stationSelect)),2)

        new_displaymode = display_modes[1 - self.p_setDisplayMode.value()]
        if(new_displaymode!=self.displaymode):
            self.displaymode = new_displaymode
            self.monitors_update_display_variables()

        print('input is: advanced Prev:',self.AdvancedPrev ,'line:',self.line_selected, 
              'station_index: ',self.station_index,'displaymode: ',self.displaymode)

    def monitors_update_display_variables(self):
        for Mo in self.Monitors:
            Mo.update_display_variables(show_platform=self.displaymode['flag_show_platform_nr'],
                                       show_line=self.displaymode['flag_show_line'])
            
    def monitors_update_advanced_preview(self):
        for Mo in self.Monitors:
            Mo.update_advanced_preview(self.AdvancedPrev)

    def __fetch_departure_data(self):
        '''Attempts once to fetch departure data from the API and converts it to an internal format. 

        **returns:** true, if successful, false otherwise

        If unsuccessful, the function waits for MIN_TIME_BETWEEN_API_REQUESTS seconds before returning.
        '''
        data = DataConversion.fetch(self.line_selected,self.station_index)
        if(data==None): #fetch failed, try again after minimum time between API requests
            self.update_RGB(r=1)
            time.sleep(MIN_TIME_BETWEEN_API_REQUESTS)
            self.update_RGB(r=0)
            return False
        
        self.time_last_API_request = time.time()
        self.update_RGB(g=1)
        self.ref_time = DataConversion.get_refTime(data)

        self.departure_data, self.platforms \
        = DataConversion.get_departures(data, platform_mode=self.displaymode['flag_show_platform_nr'],
                                        number_of_monitors=len(self.Monitors))
        
        self.update_RGB(g=0)
        return True

    def __update_displays(self):
        '''upates each display.

        if no departure data exists for a monitor, the monitor displays nothing.
        It then waits a given time for each monitor to ensure a smooth animation.
        '''
        delta_time_fetched = int(time.time()-self.time_last_API_request)
        current_time = self.ref_time + timedelta(seconds=delta_time_fetched)
        
        number_of_monitors = len(self.Monitors)
        for i in range(number_of_monitors):
            ticks1 = time.ticks_ms()

            Mo = self.Monitors[i]
            if(len(self.departure_data)<=i): Mo.clear()#no data for this monitor, skip
            else:
                current_departure_data = self.departure_data[i]
                current_platform = None if self.platforms==None or len(self.platforms)<=i else self.platforms[i]
                Mo.show_departures(current_departure_data,current_time,current_platform)
            
            delta_ms = time.ticks_diff(time.ticks_ms(),ticks1)
            time.sleep_ms(UPDATE_PERIOD*1000//number_of_monitors-delta_ms)

        for i in range(number_of_monitors):
            self.Monitors[i].present()
        
            
    def cleanup(self):
        '''Cleans up the monitors and the spi connection.'''
        for Mo in self.Monitors:
            Mo.cleanup()
        self.spi.deinit()
        print('Monitors cleaned up.')
        







    
