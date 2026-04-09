from datetime import datetime
from machine import Pin, SPI #type:ignore
import math, time

from micropython_ssd1322.xglcd_font import XglcdFont
from micropython_ssd1322.ssd1322 import Display

def delta_minutes(dtime_1:datetime, dtime_2:datetime):
    cutoff_expired = -2 #seconds
    in_station_time = 30 #seconds
    delta_time = (dtime_2-dtime_1).total_seconds()
    if delta_time<cutoff_expired: return -1
    if delta_time<in_station_time: return 0
    return int(delta_time+in_station_time)//60

class Monitor:
    def __init__(self, cs, dc, rst, spi, displaymode: dict, font:XglcdFont, normal_spacing = 1, 
                 platform_display_side = 'LEFT'):
        
        self.font = font
        self.normal_spacing = normal_spacing

        self.platform_display_side = 'RIGHT' if platform_display_side=='RIGHT' else 'LEFT'
        self.displaymode = displaymode
        self.displaymode['SHOW_LINE'] = False
        self.show_advanced_preview = displaymode['PERIOD_ADVANCED_PREVIEW']>0
        
        #create display:
        CS = Pin(cs, Pin.OUT)
        DC = Pin(dc, Pin.OUT)
        RS = Pin(rst, Pin.OUT)
        self.Display = Display(spi, CS, DC, RS)

        #variables for data displayed on monitor
        self.towards_data_displayed = {} #key - y-coordinate of text, value: text
        self.folding_ramp_displayed = {}
        self.countdown_displayed = {}
        self.platform_number_displayed = None
        
        #variables for 'in-station animation' and 'advanced-preview animation'
        self.counter_mod_16 = 0
        self.counter_mod_8 = 0
        self.advanced_preview_animation_index = 0

    def update_display_variables(self,new_displaymode: dict):
        self.displaymode = new_displaymode
        self.show_advanced_preview = new_displaymode['SHOW_ADVANCED_PREVIEW']

    def __advance_counters(self):
        self.counter_mod_16 = (self.counter_mod_16 + 1) % 16
        self.counter_mod_8 = self.counter_mod_16 % 8
        self.advanced_preview_animation_index += 1
        self.advanced_preview_animation_index %= 2 * self.displaymode['PERIOD_ADVANCED_PREVIEW']
    
    def __get_item_x_positions(self):
        '''**returns:** starting x-position of elements to be displayed'''
        
        Platform_Left = {'platform':0, 'separator':35, 'text':40, 'ramp':216, 'countdown':230}
        Platform_Right = {'text':4, 'ramp':180, 'countdown':194, 'separator':220, 'platform':221}
        No_Platform = {'text':4, 'ramp':216, 'countdown':230}

        Platform_shown = {'LEFT':Platform_Left, 'RIGHT':Platform_Right}
        if(self.displaymode['SHOW_PLATFORM_NR']):
            return Platform_shown[self.platform_display_side]
        return No_Platform
    
    def show_departures(self, departures, ref_time, platform:int=None):
        '''updates display with departure data. Advances the counters.
        - departures: list of dicts, each dict corresponds to one departure and has the following entries: 
            - towards: str
            - time: datetime
            - foldingRamp: bool
            - line: str
        - ref_time: datetime, used to calculate countdown
        - platform: int | None
        '''
        self.__advance_counters()
        self.Display.clear_buffers()
        self.item_x_positions = self.__get_item_x_positions()
        item_y_positions = [8,40]
        max_char_towards = math.floor(self.item_x_positions['ramp']-self.item_x_positions['text'])
        
        self.__show_platform(platform)

        show_custom_text_instead = len(self.displaymode['CUSTOM_STATEMENT'])>0 and self.counter_mod_16<4
        if(show_custom_text_instead):
            self.__show_custom_text()
            return
        
        is_second_line = False
        for i in range(len(departures)):
            departure = departures[i]
            countdown = delta_minutes(ref_time, departure['time'])
            
            if (countdown<0):
                continue #train no longer in station, continue
            
            y_start = item_y_positions[1] if is_second_line else item_y_positions[0]
            #grayscale_this_departure = 15
            if (self.show_advanced_preview and is_second_line and len(departures)-1>i): 
                #we are in second line, advanced preview is enabled and a next departure exists
                
                #gradual implementation, not currently used, TODO: remove
                # t = time.ticks_ms()*math.pi % (self.displaymode['PERIOD_ADVANCED_PREVIEW']*math.pi*2000)
                # grayscale_this_departure = max(math.floor(15.9*math.cos(t)), 0)
                # grayscale_next_departure = -min(math.floor(15.9*math.cos(t)), 0)

                next_departure = departures[i+1]
                use_next_departure = self.advanced_preview_animation_index < self.displaymode['PERDIOD_ADVANCED_PREVIEW']
                departure = next_departure if use_next_departure else departure

                # self.__print_towards(y_start, next_departure,
                #                     max_len=max_char_towards, gs=grayscale_next_departure)
                # self.__print_foldingRamp(y_start, next_departure, gs=grayscale_next_departure)
                # next_countdown = delta_minutes(ref_time,next_departure['time'])
                # self.__print_countdown(y_start, next_countdown, gs=grayscale_next_departure)
            
            grayscale_this_departure = 15
            if(is_second_line and self.show_advanced_preview):
                grayscale_this_departure = 0
            
            if(not is_second_line or grayscale_this_departure>0):
                self.__print_towards(y_start, departure, 
                                    max_len=max_char_towards, gs=grayscale_this_departure)
                self.__print_foldingRamp(y_start, departure, gs=grayscale_this_departure)
                self.__print_countdown(y_start, countdown, gs=grayscale_this_departure)
            
            if (is_second_line):#breaks after second line
                break
            is_second_line = True

    def __show_custom_text(self):
        statement:str = self.displaymode['CUSTOM_STATEMENT']
        line1 = statement
        line2 = ""
        if(';' in statement):
            line_separator_pos = statement.index(';')
            line1 = statement[:line_separator_pos]
            line2 = statement[line_separator_pos+1:]
        self.draw_text_centered(line1,8)
        self.draw_text_centered(line2,40)
        
    def present(self):
        self.Display.present()

    def __show_platform(self, platform:int):
        '''updates platform number on display~~, if it should be updated.~~

        ~~It should be updated, if~~
        - show_platform is enabled 
        - and platform is not None 
        - and the platform to be displayed differs from the currently displayed one.
        '''
        platform_path = f'img/Gleis{platform}.mono'
        self.Display.draw_bitmap_mono(platform_path, self.item_x_positions['platform'], 0, 35, 64, invert=True)#TODO: catch no file in directory error
        self.Display.draw_rectangle(self.item_x_positions['separator'], 0, 1, 64, gs=15)

        self.platform_number_displayed = platform
    
        
    def __print_towards(self, y_start:int, departure, max_len=16, gs=15):
        '''updates towards of this departure~~, if towards needs to be updated.~~

            ~~it should be updated if~~
            - advanced preview is enabled 
            - or if the towards text for this line is different from the currently displayed one.
        '''
        towards = departure['towards'][:max_len]
        if (self.displaymode['SHOW_LINE']):
            towards = (departure['line'] + ' ' + towards)[:max_len]
        x_start = self.item_x_positions['text']
        self.draw_text(x_start, y_start, towards, gs=gs)
        
    def __print_foldingRamp(self, y_start:int, departure, gs=15):
        '''updates folding ramp status of this departure~~, if it needs to be updated.~~

            ~~it needs to be updated if~~
            - advanced preview is enabled
            - or if the folding ramp status for this line is different from the currently displayed one.
        '''
        folding_ramp_state = departure['foldingRamp']
        if (folding_ramp_state):
            x_start = self.item_x_positions['ramp']
            self.draw_text(x_start, y_start, '-', gs=gs)

    def __print_countdown(self, y_start:int, countdown:int, gs=15):
        '''updates countdown of this departure~~, if it needs to be updated.~~

            ~~it needs to be updated if~~
            - ~~advanced preview is enabled~~
            - ~~or if the countdown for this line is different from the currently displayed one.~~
            - ~~or if countdown==0, because then the 'in-station animation' should be shown.~~
        '''
        str_countdown = self.__create_countdown_str(countdown)
        x_start = self.item_x_positions['countdown']
        if (len(str_countdown)<=1): #increase x_start
            x_start = x_start+10+self.normal_spacing
            
        self.draw_text(x_start, y_start, str_countdown, gs=gs)

    def __create_countdown_str(self, countdown:int):
        str_countdown = str(countdown)
        if (countdown==0):
            currently_in_station = ['*', '* '] #without leading spaces!
            str_countdown = currently_in_station[self.counter_mod_8 % 2]
        return str_countdown
    
    def show_empty_monitor_info(self, other_departures, platform: int, ref_time):
        self.__advance_counters()
        self.Display.clear_buffers()
        m = self.displaymode['SHOW_ON_EMPTY']
        if('NEXT_DEPARTURE' == m): self.__show_next_departure_of_other_monitor(other_departures, platform, ref_time)
        if('NO_BOARDING_DE' == m): self.__show_stay_back(platform=platform)
        if('NO_BOARDING' == m): self.__show_stay_back(platform=platform, with_english_text=True)

    def __show_next_departure_of_other_monitor(self, other_departures, platform: int, ref_time, show_line=False):
        starting_coordinates = {'info':(18, 8), 'towards':(18, 40), 'ramp':(205, 40), 'countdown':(216, 40)}
        max_char_towards = (starting_coordinates['ramp'][0] - starting_coordinates['towards'][0])//11
        
        for i in range(len(other_departures)):
            departure = other_departures[i]
            countdown = delta_minutes(ref_time, departure['time'])
            if (countdown<0):
                continue
            
            self.draw_text(*starting_coordinates['info'], 'NÄCHSTER ZUG GLEIS ' + str(platform))

            str_towards = departure['line'] + ' ' + departure['towards'] if show_line else departure['towards']
            self.draw_text(*starting_coordinates['towards'], str_towards[:max_char_towards])

            self.draw_text(*starting_coordinates['ramp'], '-' if departure['foldingRamp'] else '')

            str_countdown = self.__create_countdown_str(countdown)
            x_start = starting_coordinates['countdown']
            if(len(str_countdown)>1): x_start -= 11
            self.draw_text(x_start,starting_coordinates['countdown'][1], str_countdown)
        
    def __show_stay_back(self, platform = None, with_english_text=False):
        '''displays the text:
            ZURÜCKBLEIBEN!
            NICHT EINSTEIGEN!
        '''
        if(self.displaymode['SHOW_PLATFORM_NR'] and platform != None):
            self.__show_platform(platform)
        self.draw_text_centered('ZURÜCKBLEIBEN!', 8)
        if(self.counter_mod_8 < 2):
            self.draw_text_centered('NICHT EINSTEIGEN!', 40)
            return
        if((self.counter_mod_8 + 4) % 8< 2):
            self.draw_text_centered('PLEASE DO NOT BOARD!' if with_english_text else 'NICHT EINSTEIGEN!', 40)

    def draw_text(self, x_start:int, y_start:int, text:str, gs:int=15):
        self.Display.draw_text(x_start, y_start, text, self.font, spacing=self.normal_spacing, gs=gs)

    def draw_text_centered(self, text:str, y:int, gs=15):
        '''prints text centered on display at given y-coordinate
            if 'SHOW_PLATFORM_NR'==True then it leaves space for platform.
        '''
        x_start = self.item_x_positions['text']
        platform_limitation = self.displaymode['SHOW_PLATFORM_NR'] and self.platform_display_side=='RIGHT'
        x_end = self.item_x_positions['separator'] - 3 if platform_limitation else 256
        space = x_end-x_start

        text_width = self.font.measure_text(text) #font width is 11 pixels
        while(text_width>space):
            text = text[:-1]
            text_width = self.font.measure_text(text)
            
        x = (x_end + x_start - text_width)//2
        self.draw_text(x, y, text,  gs=gs)

    def show_debug_text(self, text: str, x: int, y: int, clear_first: bool = True):
        #Note: the following code section was auto-generated by CodeGPT.
        '''shows debug text on display at given position. Used for debugging purposes.'''

        self.Display.clear_buffers()
        self.draw_text(x, y, text)
        self.Display.present()
    
    #TODO: remove
    # def clear(self, force_clear=False, only_clear_buffer=False):
    #     '''clears display. 

    #     Also resets the programatically stored currently displayed data.
    #     - force_clear: bool, if True, display is cleared even if it is 
    #     programmatically determined that the display is already clear.
    #     '''

    #     max_displayed_len = max(map(len,[self.towards_data_displayed, self.folding_ramp_displayed, self.countdown_displayed]))
        
    #     if not force_clear and max_displayed_len==0 and self.platform_number_displayed==None:
    #         return #display already clear, no need to clear again
    #     self.Display.clear_buffers() if only_clear_buffer else self.Display.clear()
    #     self.towards_data_displayed = {}
    #     self.folding_ramp_displayed = {}
    #     self.countdown_displayed = {}
    #     self.platform_number_displayed = None

    def cleanup(self):
        '''clean up resources of monitor. Used when program is terminated.

            Note: Use of Dislplay.cleanup() is discouraged, 
            because it causes the de-initialization of SPI, 
            which is used by all monitors. Instead, 
            the display is just cleared and put to sleep, 
            to save energy and prevent burn-in.
            The spi should be handled after calling this function.
        '''
        self.Display.clear()
        self.Display.sleep()
        