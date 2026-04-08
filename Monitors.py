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
    def __init__(self, cs, dc, rst, spi, font:XglcdFont, normal_spacing = 1, 
                 period_advanced_preview = 4, platform_display_side = 'LEFT'):
        
        self.font = font
        self.normal_spacing = normal_spacing

        self.platform_display_side = 'RIGHT' if platform_display_side=='RIGHT' else 'LEFT'
        self.show_line = False
        self.show_platform = False
        self.advanced_preview = False
        
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
        self.in_station_animation_index = 0
        self.period_advanced_preview = period_advanced_preview

        self.advanced_preview_animation_index = 0

    def update_display_variables(self,show_platform:bool, show_line:bool):
        self.show_platform = show_platform
        self.show_line = show_line
        self.clear()

    def update_advanced_preview(self, advanced_preview:bool):
        self.advanced_preview = advanced_preview
    
    def get_item_x_positions(self):
        '''**returns:** starting x-position of elements to be displayed
        '''
        Platform_Left = {'platform':0, 'separator':35, 'text':40, 'ramp':216, 'countdown':230}
        Platform_Right = {'text':4, 'ramp':180, 'countdown':194, 'separator':219, 'platform':220}
        No_Platform = {'text':4, 'ramp':216, 'countdown':230}

        Platform_shown = {'LEFT':Platform_Left, 'RIGHT':Platform_Right}
        if(self.show_platform):
            return Platform_shown[self.platform_display_side]
        return No_Platform
    
    def show_departures(self, departures, ref_time, platform:int=None):
        '''updates display with departure data. 
        - departures: list of dicts, each dict corresponds to one departure and has the following entries: 
            - towards: str
            - time: datetime
            - foldingRamp: bool
            - line: str
        - ref_time: datetime, used to calculate countdown
        - platform: int | None'''

        self.Display.draw_text(0, 0, 'test', self.font, gs=8)
        self.Display.present()
        time.sleep(5)

        self.item_x_positions = self.get_item_x_positions()
        item_y_positions = [8,40]
        max_char_towards = math.floor(self.item_x_positions['ramp']-self.item_x_positions['text'])
        
        self.__show_platform(platform)
            
        is_second_line = False
        for i in range(len(departures)):
            departure = departures[i]
            countdown = delta_minutes(ref_time, departure['time'])
            
            if (countdown<0):
                continue #train no longer in station, continue
            
            y_start = item_y_positions[1] if is_second_line else item_y_positions[0]
            grayscale_this_departure = 15
            if (self.advanced_preview and is_second_line and len(departures)-1>i): 
                #we are in second line, advanced preview is enabled and a next departure exists
                
                #gradual implementation, not currently used
                # t = time.ticks_ms()*math.pi % (self.period_advanced_preview*math.pi*2000)
                # grayscale_this_departure = max(math.floor(15.9*math.cos(t)), 0)
                # grayscale_next_departure = -min(math.floor(15.9*math.cos(t)), 0)

                #display next_departure - this is a hotfix TODO: clean up code
                grayscale_next_departure = 0
                if(self.advanced_preview_animation_index>= self.period_advanced_preview and self.advanced_preview_animation_index< 2*self.period_advanced_preview-1):
                    grayscale_next_departure = 15

                next_departure = departures[i+1]
                self.__print_towards(y_start, next_departure,
                                    max_len=max_char_towards, gs=grayscale_next_departure)
                self.__print_foldingRamp(y_start, next_departure, gs=grayscale_next_departure)
                next_countdown = delta_minutes(ref_time,next_departure['time'])
                self.__print_countdown(y_start, next_countdown, gs=grayscale_next_departure)

            # this is also a hotfix TODO: clean up code
            grayscale_this_departure = 15
            if(is_second_line and self.advanced_preview_animation_index>=self.period_advanced_preview - 1):
                grayscale_this_departure = 0
                self.advanced_preview_animation_index += 1
                self.advanced_preview_animation_index %= self.period_advanced_preview
            
            if(not is_second_line or grayscale_this_departure>0):
                self.__print_towards(y_start, departure, 
                                    max_len=max_char_towards, gs=grayscale_this_departure)
                self.__print_foldingRamp(y_start, departure, gs=grayscale_this_departure)
                self.__print_countdown(y_start, countdown, gs=grayscale_this_departure)

            
            if (is_second_line):#breaks after second line
                break
            is_second_line = True

    def present(self):
        self.Display.present()

    def __show_platform(self, platform:int):
        '''updates platform number on display, if it should be updated. 

        It should be updated, if
        - show_platform is enabled 
        - and platform is not None 
        - and the platform to be displayed differs from the currently displayed one.
        '''
        should_update_platform = self.show_platform and platform!=None and self.platform_number_displayed != platform

        if (should_update_platform):
            platform_path = f'img/Gleis{platform}.mono'
            self.Display.draw_bitmap_mono(platform_path, self.item_x_positions['platform'], 0, 35, 64, invert=True)#TODO: catch no file in directory error
            self.Display.draw_rectangle(self.item_x_positions['separator'], 0, 1, 64, gs=15)
            self.platform_number_displayed = platform

    def __print_towards(self, y_start:int, departure, max_len=16, gs=15):
        '''updates towards of this departure, if towards needs to be updated.

            it should be updated if 
            - advanced preview is enabled 
            - or if the towards text for this line is different from the currently displayed one.
        '''
        should_update_towards = self.advanced_preview or \
            (y_start not in self.towards_data_displayed) \
            or (self.towards_data_displayed[y_start] != departure['towards'])
        
        if(not should_update_towards):
            return #same data already displayed, no need to update

        #clear old data
        x_start = self.item_x_positions['text']
        x_end = self.item_x_positions['ramp']
        self.Display.fill_rectangle(x_start, y_start, x_end-x_start, 16, gs=0)

        towards = departure['towards'][:max_len]
        if (self.show_line):
            towards = (departure['line'] + ' ' + towards)[:max_len]
        
        
        self.Display.draw_text(x_start, y_start, towards, self.font, gs=gs, spacing=self.normal_spacing)

        self.towards_data_displayed[y_start] = towards
        
    def __print_foldingRamp(self, y_start:int, departure, gs=15):
        '''updates folding ramp status of this departure, if it needs to be updated.

            it needs to be updated if
            - advanced preview is enabled
            - or if the folding ramp status for this line is different from the currently displayed one.
        '''
        should_update_foldingRamp = self.advanced_preview or \
            (y_start not in self.folding_ramp_displayed) \
            or (self.folding_ramp_displayed[y_start] != departure['foldingRamp'])
        
        if(not should_update_foldingRamp):
            return #same data already displayed, no need to update
        
        #clear old data
        x_start = self.item_x_positions['ramp']
        self.Display.fill_rectangle(x_start, y_start, 10, 16, gs=0)

        folding_ramp_state = departure['foldingRamp']
        if (folding_ramp_state):
            self.Display.draw_text(x_start, y_start, '-', self.font, gs=gs)

        self.folding_ramp_displayed[y_start] = folding_ramp_state

    def __print_countdown(self, y_start:int, countdown:int, gs=15):
        '''updates countdown of this departure, if it needs to be updated.

            it needs to be updated if
            - advanced preview is enabled
            - or if the countdown for this line is different from the currently displayed one.
            - or if countdown==0, because then the 'in-station animation' should be shown. 
        '''
        should_update_countdown = self.advanced_preview or \
            (y_start not in self.countdown_displayed) \
            or (self.countdown_displayed[y_start] != countdown) \
            or countdown==0 #countdown should be updated if train just arrived in station (countdown==0), to show 'in-station animation'
        
        if(not should_update_countdown):
            return #same data already displayed, no need to update
        
        #clear old data
        x_start = self.item_x_positions['countdown']
        x_end = self.item_x_positions['platform'] if (self.show_platform and self.platform_display_side=='RIGHT') else 256
        self.Display.fill_rectangle(x_start, y_start, x_end-x_start, 16, gs=0) 

        str_countdown = str(countdown)
        if (countdown==0):
            currently_in_station = ['*', '* '] #without leading spaces!
            t = self.in_station_animation_index #old implementation: t = int(time.time()) % 2
            self.in_station_animation_index = 1 - self.in_station_animation_index
            str_countdown = currently_in_station[t]

        
        if (len(str_countdown)<=1): #increase x_start
            x_start = x_start+10+self.normal_spacing
            
        self.Display.draw_text(x_start, y_start, str_countdown, 
                               self.font, gs=gs, spacing=self.normal_spacing)
        
        self.countdown_displayed[y_start] = countdown

    def show_debug_text(self, text: str, x: int, y: int, clear_first: bool = True):
        #Note: the following code section was auto-generated by CodeGPT.
        '''shows debug text on display at given position. Used for debugging purposes.'''

        if clear_first: self.clear(force_clear=True)
        self.Display.draw_text(x, y, text, self.font,spacing=self.normal_spacing, gs=15)
        self.Display.present()
    
    def clear(self, force_clear=False):
        '''clears display. 

        Also resets the programatically stored currently displayed data.
        - force_clear: bool, if True, display is cleared even if it is 
        programmatically determined that the display is already clear.
        '''
        max_displayed_len = max(map(len,[self.towards_data_displayed, self.folding_ramp_displayed, self.countdown_displayed]))
        
        if not force_clear and max_displayed_len==0 and self.platform_number_displayed==None:
            return #display already clear, no need to clear again
        self.Display.clear()
        self.towards_data_displayed = {}
        self.folding_ramp_displayed = {}
        self.countdown_displayed = {}
        self.platform_number_displayed = None



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
        