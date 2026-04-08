from datetime import datetime
import urequests #type:ignore

def stripDatetime(datetime_str:str):
    '''**returns:** datetime representation of input string.

    asserts the format of datetime_str to be: YYYY-MM-DDThh:mm:ss[XXX], where [XXX] is simply ignored
    '''
    index_endOfDate = datetime_str.index('T')
    index_endOfTime = index_endOfDate + 9  # Assuming HH:MM:SS format, other option: datetime_str.index('.') if '.' in datetime_str
    date_str = datetime_str[:index_endOfDate]
    time_str = datetime_str[index_endOfDate+1:index_endOfTime]

    list_date_str = date_str.split('-')
    list_date_int = list(map(int,list_date_str))
    list_time_str = time_str.split(':')
    list_time_int = list(map(int,list_time_str))

    return datetime(*list_date_int,*list_time_int)

def fetch(line_selected:str, station_selected:int):
    '''**returns:** API data as a dictionary | None, if an error occured.'''
    list_meassure_ids = __get_meassured_ids(line_selected,station_selected)
    URL = __generateAPI_URL(list_meassure_ids)
    data = None
    try:
        response = urequests.get(URL)
        data:dict = response.json()
        response.close()
    except OSError as err:
        print('Error while attempting to open API data. Message:',err)
    
    return data
        
def __generateAPI_URL(list_meassure_ids,FLAG_use_stopID=True):
    '''**returns:** url for get-request of the stopIDs (or diva, not currently used) in list_meassure_ids.'''
    assert len(list_meassure_ids)>0
    request_type = 'stopID=' if FLAG_use_stopID else 'diva='
    string = 'https://www.wienerlinien.at/ogd_realtime/monitor?' + request_type + str(list_meassure_ids[0])
    for name in list_meassure_ids[1:]:
        string += '&' + request_type + str(name)
    return string

#index 0,0 is Oberlaa ->Leopoldau
stop_IDs_U1 = [[4134,4133], [4135,4132], [4136,4131], [4137,4130], [4138,4129], [4101,4128], [4103,4126], 
               [4105,4124], [4107,4122], [4109,4120], [4111,4118], [4113,4116], [4115,4114], [4117,4112], 
               [4119,4110], [4121,4108], [4123,4106], [4125,4104], [4127,4102], [4181,4186], [4182,4187], 
               [4183,4188], [4184,4189], [4185,4190]]

#index 0,0 is Seestadt -> Karlsplatz
stop_IDs_U2 = [[4277,4276], [4278,4275], [4279,4274], [4280,4273], [4251,4272], [4252,4271], [4253,4270], 
               [4254,4269], [4256,4267], [4255,4268], [4257,4266], [4258,4265], [4259,4264], [4260,4263], 
               [4261,4262], [4201,4214], [4203,4212], [4205,4210], [4209,4206], [4211,4204], [4213,4202]] 

#index 0,0 is Ottakring -> Simmering
stop_IDs_U3 = [[4931,4930], [4932,4929], [4933,4928], [4926,4925], [4927,4924], [4921,4920], [4922,4919], 
               [4923,4918], [4909,4908], [4910,4907], [4911,4906], [4912,4905], [4913,4904], [4914,4903], 
               [4915,4902], [4916,4901], [4917,4900], [4934,4941], [4935,4940], [4936,4939], [4937,4938]] 

#index 0,0 is Hütteldorf -> Heiligenstadt           
stop_IDs_U4 = [[4401,4436], [4403,4434], [4405,4432], [4407,4430], [4409,4428], [4411,4426], [4413,4424], 
               [4437,4438], [4415,4422], [4417,4420], [4419,4418], [4421,4416], [4423,4414], [4425,4412], 
               [4427,4410], [4429,4408], [4431,4406], [4433,4404], [4439,4440], [4435,4402]] 

#index 0,0 is Siebenhirten -> Floridsdorf
stop_IDs_U6 = [[4635,4634], [4636,4633], [4637,4632], [4638,4631], [4639,4630], [4640,4629], [4615,4614], 
               [4616,4613], [4617,4612], [4618,4611], [4619,4610], [4620,4609], [4621,4608], [4622,4607], 
               [4623,4606], [4624,4605], [4625,4604], [4626,4603], [4627,4651], [4641,4650], [4642,4649], 
               [4643,4648], [4644,4647], [4645,4646]]

Stop_IDs = {'U1':stop_IDs_U1,'U2':stop_IDs_U2,'U3':stop_IDs_U3,'U4':stop_IDs_U4,'U6':stop_IDs_U6}
    
def __get_meassured_ids(line_selected:str,station_selected):
    '''
    - station_selected: Int = index of station in list, see below

    **returns:** list of stopIDs corresponding to selected line and station.

    Values of StopIDs obtained from 'wienerlinien-ogd-haltepunkte.csv' 
    downloaded from https://www.wienerlinien.at/ogd_realtime/doku/
    (last updated 14.03.2026)
    
    For each line, the stations are indexed the following way:
    - U1: index 0,0 is Oberlaa ->Leopoldau
    - U2: index 0,0 is Seestadt -> Karlsplatz
    - U3: index 0,0 is Ottakring -> Simmering
    - U4: index 0,0 is Hütteldorf -> Heiligenstadt
    - U6: index 0,0 is Siebenhirten -> Floridsdorf

    Example: U6 'Bahnhof Meidling' is index 6 in stop_IDs_U6; 
    stop_IDs_U6[6] = [4615,4614], where 
    - 4615 <-> 'Bahnhof Meidling direction Siebenhirten'
    - 4614 <-> 'Bahnhof Meidling direction Floridsdorf'
    '''
    
    return Stop_IDs[line_selected][station_selected]

def get_departures(data:dict, platform_mode = False,number_of_monitors=2):
    '''
    - platform_mode: bool
        - if True -> see __get_departures_platform_mode
        - if False -> see __get_departures_direction_mode
    
    **returns:** tuple(departures: list[list[dict[str,...]]], (platforms: list[int] | None))
    * departures: each dictionary corresponds to one train, 
        each list of dict either corresponds to trains of one platform or trains traveling in one direction

        entries in each dictionary:
            - towards: str
            - departure: datetime
            - foldingRamp: bool
            - line: str
            - direction: str (H or R)
    * platforms: list of the platform-numbers or None if platform_mode==False   
    '''
    JSON_CONVERSION_FUNCTIONS = {False:__get_departures_direction_mode, True:__get_departures_platform_mode}
    return JSON_CONVERSION_FUNCTIONS[platform_mode](data,number_of_monitors)

def __get_departures_platform_mode(data:dict,number_of_monitors):
    '''
    Idea: Show each platform (where there are departures) separately.

    If there are more platforms with departures than monitors, 
    only the platforms with the most departures are returned.
    
    **returns:** tuple (departures, platforms)
    - departures is a list of list containing dictionaries. Each dictionary corresponds to one departure.
    - platforms is a list of the platform-numbers, 
    where the order corresponds to the order of the list of departures 
    (i.e. platforms[i] is the platform number of trains in departures[i])
    '''
    unfiltered_departures = __get_unfiltered_departure_data(data)

    #INFO: the following code section was auto generated by VSCode 'CodeGPT' extension.
    platform_departure_tuples = []
    for key in unfiltered_departures.keys():
        platform_departure_tuples.append((key, unfiltered_departures[key], len(unfiltered_departures[key])))
    platform_departure_tuples.sort(key=lambda x: x[2], reverse=True) #sort by number of departures, descending

    if(len(platform_departure_tuples)>number_of_monitors and platform_departure_tuples[number_of_monitors][2]>0):
        print('Warning: more platforms with departures than monitors, ' \
        'some platforms with departures are not shown. ' \
        'Number of departures on not shown platforms: ', sum(tup[2] for tup in platform_departure_tuples[number_of_monitors:]))
        print('platforms not shown: \n', platform_departure_tuples[number_of_monitors:])
    
    platform_departure_tuples = platform_departure_tuples[:number_of_monitors] #only keep platforms with most departures
    platform_departure_tuples.sort(key=lambda x: x[0]) #sort by platform number, ascending
    departures = [tup[1] for tup in platform_departure_tuples]
    platforms = [tup[0] for tup in platform_departure_tuples]
    return departures, platforms

def __get_departures_direction_mode(data:dict,number_of_monitors = 2):
    '''
    Attempts to solve the problem of the possibility of more platforms with departures than monitors 
    by grouping the departures by direction (H or R) instead of platform.
    
    **returns:** tuple (departures, number_of_monitors*[None]) 
        - departures is a list with two items:
            - item 0: list containing departing trains with direction 'H', 
            - item 1: list containing departing trains with direction 'R'.     
    '''
    assert(number_of_monitors>=2, 'direction-mode is only implemented for at least 2 monitors. ' + 
    'Number of monitors given is: {}'.format(number_of_monitors))
    
    departures:list[list[dict]] = [[], []] #index 0 is for direction 'H', index 1 for the direction 'R'.

    #INFO: the following code section was auto generated by VSCode 'CodeGPT' extension.
    unfiltered_departures = __get_unfiltered_departure_data(data)
    for platform in unfiltered_departures.keys():
        for departure in unfiltered_departures[platform]:
            if departure['direction']=='H':
                departures[0].append(departure)
            elif departure['direction']=='R':
                departures[1].append(departure)
            else:
                print('Warning: unknown direction {} for departure {}, skipping...'.format(departure['direction'], departure))
    departures[0].sort(key=lambda x: x['time']) #sort by departure time, ascending
    departures[1].sort(key=lambda x: x['time']) #sort by departure time, ascending
    
    return departures, number_of_monitors*[None]

def __get_unfiltered_departure_data(data:dict):
    '''
    Extracts the important information of departures from the API data.

    **returns:** a dictionary, where the keys are the platform numbers and the 
    values are lists of dictionaries, each corresponding to one departure on that platform.

    data collected for each departure:
    - towards: str
    - time: datetime
    - foldingRamp: bool
    - line: str
    - direction: str (H or R)
    '''
    MAX_ITEMS_PER_PLATFORM = 4
    unfiltered_departures:dict[int,list[dict]] = {}

    monitor_keys = range(len(data['data']['monitors']))

    for monitor_key in monitor_keys:
        line_data_array = data['data']['monitors'][monitor_key]['lines']
        for line_data in line_data_array:
            line = line_data['name']
            default_platform_nr = line_data['platform']
            default_towards_raw = line_data['towards']
            default_direction = line_data['direction']

            dep_data_array = line_data['departures']['departure']
            for dep_data in dep_data_array:
                if not 'departureTime' in dep_data.keys():
                    print('departureTime not found in data, continuing...', dep_data)
                    continue

                platform_nr = default_platform_nr
                towards_raw = default_towards_raw
                vehicle_direction = default_direction
                folding_ramp = False

                if 'vehicle' in dep_data.keys(): 
                    platform_nr = dep_data['vehicle']['platform']
                    towards_raw:str = dep_data['vehicle']['towards']
                    line = dep_data['vehicle']['name']
                    vehicle_direction = dep_data['vehicle']['direction']
                    if 'foldingRamp' in dep_data['vehicle']:
                        folding_ramp = dep_data['vehicle']['foldingRamp']

                if(platform_nr in unfiltered_departures 
                   and len(unfiltered_departures[platform_nr])>MAX_ITEMS_PER_PLATFORM):
                    continue

                dep_time_str:str = dep_data['departureTime']['timeReal'] if 'timeReal' in dep_data['departureTime'] \
                                                                    else dep_data['departureTime']['timePlanned']
                dep_time = stripDatetime(dep_time_str)
                towards = __check_station_name(towards_raw)

                #append to departures
                toAppend = {'towards':towards,'time':dep_time,'foldingRamp':folding_ramp,'line':line, 'direction':vehicle_direction}
                if platform_nr not in unfiltered_departures:
                    unfiltered_departures[platform_nr] = [toAppend]
                    continue
                unfiltered_departures[platform_nr].append(toAppend)
    return unfiltered_departures

def __check_station_name(name:str, line:str = None):
    '''
    attempts to clean up the station name of e.g. 
    - encoding errors, 
    - trailing/leading whitespaces, 
    - special cases like 'HEILIGENSTADT S+U' -> 'HEILIGENSTADT'
    '''
    value = name.upper().strip()
    #deal with special cases like 'HEILIGENSTADT S+U'
    if ' ' in value:
        value = value[:value.index(' ',6)]
    #TODO: check for decoding errors here
    #need for replacement ÃŸ -> SS? probably it is correct decoded and need only to replace ß -> SS
    value.replace('ß','SS')
    common_names = ['OBERLAA', 'LEOPOLDAU', 'KARLSPLATZ', 'SEESTADT', 
                    'SIMMERING', 'OTTAKRING','HÜTTELDORF', 'HEILIGENSTADT', 
                    'SIEBENHIRTEN', 'FLORIDSDORF','ALAUDAGASSE','ASPERNSTRASSE']
    if value in common_names:
        return value
    #TODO: implement more checks when not correct values occur
    return value

def get_refTime(data:dict):
    '''**returns:** server-time contained in API-response
    '''
    reftime_str:str = data['message']['serverTime']
    reftime = stripDatetime(reftime_str)
    return reftime

