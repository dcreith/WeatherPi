class Config:
    # Weather Underground
    STATION_ID = "yourStationIDHere"
    STATION_KEY = "yourKeyHere"

    # local station info
    LOCAL_STATION_ID = "6100245999979349"
    LOCAL_STATION_TIMEZONE = "America/Eastern"

    # logging config
    LOGGING_DEBUG = False       # log on debug -->  if both set to false min
    LOGGING_INFO = True         # log on info  -->  level is warning
    LOGGING_BYTES = 10240       # bytes in log file before archive
    LOGGING_ROTATION = 5        # number of log files to archive
    LOGGING_PRINT = False       # set to true to print to console

    FAILURE_CSV = True          # capture data in CSV in upload fails
    FAILURE_DIR = 'failurelogs' # where failure logs are stored
    FAILURE_REBOOT = True       # attempt reboot if upload failures excede maximum (below)
    FAILURE_MAX = 18            # maximum upload failures before reboot

    # daytime
    SUNRISE = 5
    SUNSET = 19

    # temperature probes
    PROBE_1 = '28-0417a2d9f9ff'  # probe 1 - air
    PROBE_2 = '28-0417a2ec2aff'  # probe 2 - coldframe

    TEMP_SENSOR_1 = '/sys/bus/w1/devices/'+PROBE_1+'/w1_slave'
    TEMP_SENSOR_2 = '/sys/bus/w1/devices/'+PROBE_2+'/w1_slave'

    USE_PROBE_1 = True
    USE_PROBE_2 = True
    USE_SENSEHAT_TEMPERATURE = True

    MEASUREMENT_INTERVAL = 1  # minutes

    # 8x8 LED display
    DISPLAY_INTERVAL = 1    # minutes
    DISPLAY_ON = True       # True is On
    DISPLAY_DIM = False     # True is Dim
    DISPLAY_SI = True       # display temperature in metric if true, imperial if false

    # call back settings   **** currently unused **** currently unused ****
    CAPTURE_SI = True   # capture local data as metric if true, imperial if false

    # PW - Weather DB
    PW_UPLOAD = True
    PW_UPLOAD_INTERVAL = 2  # minutes
    PW_URL = "http://192.168.0.99/weather/assets/ajax/aPostWeather.php"
    PW_ID = LOCAL_STATION_ID

    # WU - Weather Underground DB
    WU_UPLOAD = False
    WU_UPLOAD_INTERVAL = 15  # minutes
    WU_URL = "http://weatherstation.wunderground.com/weatherstation/updateweatherstation.php"
