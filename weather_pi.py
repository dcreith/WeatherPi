#!/usr/bin/python
'''*****************************************************************************************************************
    Pi Weather Station v1.0

    Measure temperature, humidity and pressure the Pi Sense Hat and a DS18b20 temperature probe.
    TODO -> test for probe error with temperature of 85 C (85000)
    TODO -> take photos on a regular basis
********************************************************************************************************************'''

from __future__ import print_function

import datetime
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import time
import math
import json
from urllib import urlencode
import cPickle as pickle
import errno
import fnmatch

import urllib2
from sense_hat import SenseHat

# from config import Config

mypath = os.path.abspath(__file__)  # Find the full path of this python script
baseDir = os.path.dirname(mypath)   # get the path location only (excluding script name)
baseFileName = os.path.splitext(os.path.basename(mypath))[0]
progName = os.path.basename(__file__)

# Check for config.py variable file to import and error out if not found.
configFilePath = os.path.join(baseDir, "config.py")
if not os.path.exists(configFilePath):
    print("ERROR - %s File Not Found. Cannot Import Configuration Variables." % ( configFilePath ))
    quit()
else:
    # Read Configuration variables from config.py file
    print("INFO  - Import Configuration Variables from File %s" % ( configFilePath ))
    from config import *

# set up logging
logFilePath = os.path.join(baseDir, baseFileName + ".log")

logger = logging.getLogger('weather_pi')
if Config.LOGGING_DEBUG:
    logger.setLevel(logging.DEBUG)
elif Config.LOGGING_INFO:
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.WARNING)
handler = RotatingFileHandler(logFilePath, maxBytes=Config.LOGGING_BYTES, backupCount=Config.LOGGING_ROTATION)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# ============================================================================
# Constants
# ============================================================================
GO=True
REBOOT=False
SHUTDOWN=False
FAILURE_COUNTER=0
STANDARD_PRESSURE=1013.25
# Dew Point Temperature (oC) =(B1*(ln(RH/100) + (A1*t)/(B1 +t)))/(A1-ln(RH/100)-A1*t/(B1+t))
A1=17.625
B1=243.04

# init environment
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# set up the colours (blue, red, empty)
# modified from https://www.raspberrypi.org/learning/getting-started-with-the-sense-hat/worksheet/
r = [255, 0, 0]     # red
g = [35, 125, 0]    # green ->[0, 255, 0]
b = [0, 0, 255]     # blue
o = [255, 128, 0]   # orange
y = [255, 255, 0]   # yellow
p = [204, 0, 102]   # pink
l = [127, 0, 255]   # purple
e = [0, 0, 0]       # empty

NOTICE_OFFSET_LEFT = 0
NOTICE_OFFSET_TOP = 7
NOTICE ={"Air":{"Notify":False,"Colour":r,"Offset":1},
        "ColdFrame":{"Notify":False,"Colour":p,"Offset":2},
        "DataLoad":{"Notify":False,"Colour":g,"Offset":3},
        "PiServer":{"Notify":False,"Colour":b,"Offset":4},
        "WUServer":{"Notify":False,"Colour":o,"Offset":5}}

OFFSET_LEFT = 1
OFFSET_TOP = 1

NUMS =[1,1,1,1,0,1,1,0,1,1,0,1,1,1,1,  # 0
       0,1,0,0,1,0,0,1,0,0,1,0,0,1,0,  # 1
       1,1,1,0,0,1,0,1,0,1,0,0,1,1,1,  # 2
       1,1,1,0,0,1,1,1,1,0,0,1,1,1,1,  # 3
       1,0,0,1,0,1,1,1,1,0,0,1,0,0,1,  # 4
       1,1,1,1,0,0,1,1,1,0,0,1,1,1,1,  # 5
       1,1,1,1,0,0,1,1,1,1,0,1,1,1,1,  # 6
       1,1,1,0,0,1,0,1,0,1,0,0,1,0,0,  # 7
       1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,  # 8
       1,1,1,1,0,1,1,1,1,0,0,1,0,0,1]  # 9

def infoMsg(lvl,msg):
    if (Config.LOGGING_PRINT): print(msg)
    if (lvl=='d'):
        logger.debug(msg)
    elif (lvl=='w'):
        logger.warning(msg)
    elif (lvl=='e'):
        logger.error(msg)
    elif (lvl=='c'):
        logger.critical(msg)
    else:
        logger.info(msg)

def show_steady_state(colour):
  e = [0, 0, 0]
  sense.set_pixel(NOTICE_OFFSET_LEFT, 0, colour)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 7, colour)
  time.sleep(0.15)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 1, colour)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 6, colour)
  time.sleep(0.15)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 0, e)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 7, e)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 2, colour)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 5, colour)
  time.sleep(0.15)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 1, e)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 6, e)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 3, colour)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 4, colour)
  time.sleep(0.15)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 2, e)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 5, e)
  time.sleep(0.15)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 3, e)
  sense.set_pixel(NOTICE_OFFSET_LEFT, 4, e)

def show_trending_up(colour):
  e = [0, 0, 0]
  for p in range(7,-1,-1):
    if (p<7):
        sense.set_pixel(NOTICE_OFFSET_LEFT, (p+1), e)
    sense.set_pixel(NOTICE_OFFSET_LEFT, p, colour)
    time.sleep(0.15)
  sense.set_pixel(NOTICE_OFFSET_LEFT, (p), e)

def show_trending_down(colour):
  e = [0, 0, 0]
  for p in range(0, 8):
    if (p>0):
        sense.set_pixel(NOTICE_OFFSET_LEFT, (p-1), e)
    sense.set_pixel(NOTICE_OFFSET_LEFT, p, colour)
    time.sleep(0.15)
  sense.set_pixel(NOTICE_OFFSET_LEFT, (p), e)

def show_notification(offset,colour):
  global State
  if State['DisplayOn']:
    for p in range(0, 8):
    # print("\nSetting Pixel %d" % (p))
      sense.set_pixel(p, NOTICE_OFFSET_TOP, colour)
      # sense.set_pixel(offset, NOTICE_OFFSET_TOP, colour)
      time.sleep(0.15)

def check_notification():

    if (NOTICE['Air']['Notify']==True):
        show_notification(NOTICE['Air']['Offset'],NOTICE['Air']['Colour'])
    if (NOTICE['ColdFrame']['Notify']==True):
        show_notification(NOTICE['ColdFrame']['Offset'],NOTICE['ColdFrame']['Colour'])
    if (NOTICE['DataLoad']['Notify']==True):
        show_notification(NOTICE['DataLoad']['Offset'],NOTICE['DataLoad']['Colour'])
    if (NOTICE['PiServer']['Notify']==True):
        show_notification(NOTICE['PiServer']['Offset'],NOTICE['PiServer']['Colour'])
    if (NOTICE['WUServer']['Notify']==True):
        show_notification(NOTICE['WUServer']['Offset'],NOTICE['WUServer']['Colour'])

    show_notification(0,e)

# Displays a single digit (0-9)
def show_digit(val, xd, yd, r, g, b):
  global State
  offset = val * 15
  for p in range(offset, offset + 15):
    xt = p % 3
    yt = (p-offset) // 3
    if (State['DisplayOn']): sense.set_pixel(xt+xd, yt+yd, r*NUMS[p], g*NUMS[p], b*NUMS[p])

# Displays a two-digits positive number (0-99)
def show_number(val, rgb):
  abs_val = abs(val)
  tens = abs_val // 10
  units = abs_val % 10
  if (abs_val > 9): show_digit(tens, OFFSET_LEFT, OFFSET_TOP, rgb[0], rgb[1], rgb[2])
  show_digit(units, OFFSET_LEFT+4, OFFSET_TOP, rgb[0], rgb[1], rgb[2])

def c_to_f(input_temp):
    # convert input_temp from Celsius to Fahrenheit
    return (input_temp * 1.8) + 32

def get_cpu_temp():
    # 'borrowed' from https://www.raspberrypi.org/forums/viewtopic.php?f=104&t=111457
    # executes a command at the OS to pull in the CPU temperature
    res = os.popen('vcgencmd measure_temp').readline()
    return float(res.replace("temp=", "").replace("'C\n", ""))


# use moving average to smooth readings
def get_smooth(x):
    # do we have the t object?
    if not hasattr(get_smooth, "t"):
        # then create it
        get_smooth.t = [x, x, x]
    # manage the rolling previous values
    get_smooth.t[2] = get_smooth.t[1]
    get_smooth.t[1] = get_smooth.t[0]
    get_smooth.t[0] = x
    # average the three last temperatures
    xs = (get_smooth.t[0] + get_smooth.t[1] + get_smooth.t[2]) / 3
    return xs


def get_temp():
    # ====================================================================
    # Unfortunately, getting an accurate temperature reading from the
    # Sense HAT is improbable, see here:
    # https://www.raspberrypi.org/forums/viewtopic.php?f=104&t=111457
    # so we'll have to do some approximation of the actual temp
    # taking CPU temp into account. The Pi foundation recommended
    # using the following:
    # http://yaab-arduino.blogspot.co.uk/2016/08/accurate-temperature-reading-sensehat.html
    # ====================================================================
    # First, get temp readings from both sensors
    t1 = sense.get_temperature_from_humidity()
    t2 = sense.get_temperature_from_pressure()
    # t becomes the average of the temperatures from both sensors
    t = (t1 + t2) / 2
    # Now, grab the CPU temperature
    t_cpu = get_cpu_temp()
    # Calculate the 'real' temperature compensating for CPU heating
    # t_corr = t - ((t_cpu - t) / 1.5)
    t_corr = t - ((t_cpu - t) / .75)
    # Finally, average out that value across the last three readings
    t_corr = get_smooth(t_corr)
    # convoluted, right?
    # Return the calculated temperature
    return t_corr

def probe_temp_raw(temp_sensor):
    status = 9
    try:
        f = open(temp_sensor, 'r')
        lines = f.readlines()
        f.close()
        status = 0
    except:
        lines = ''
        infoMsg("w","...Unable To Retrieve Sensor Data:%s" % str(temp_sensor))

    return {'status':status, 'lines':lines}

def probe_temp(temp_sensor):
    raw_temp = probe_temp_raw(temp_sensor)
    status = 9
    celcius = 0
    if (raw_temp['status']==0):
        if (raw_temp['lines'][0].strip()[-3:]=='YES'):
            temp_output = raw_temp['lines'][1].find('t=')
            if temp_output != -1:
                status = 0
                temp_string = raw_temp['lines'][1].strip()[temp_output+2:]
                celcius = float(temp_string) / 1000.0
                if (celcius==85.0): status = 8
                # temp_f = temp_c * 9.0 / 5.0 + 32.0
    return {'status':status, 'celcius':celcius}

def failureLog(t,rh,p,dp,cf,pid,cid,ct):
    utc_datetime=datetime.datetime.utcnow()
    local_datetime=datetime.datetime.now()
    if (ct==0 or ct==30):
        fn='fl_'+local_datetime.strftime('%Y-%m-%d')+'_'+local_datetime.strftime('%H:%M:%S')+'.csv'
        fl=os.path.join(Config.FAILURE_DIR , fn)
        dt =[local_datetime.strftime('%Y-%m-%d'),local_datetime.strftime('%H:%M:%S'),t,rh,p,dp,cf,pid,cid,utc_datetime.strftime('%Y-%m-%d'),utc_datetime.strftime('%H:%M:%S')]
        try:
            fLog = open(fl, 'w')
            with fLog:
                writer = csv.writer(fLog)
                writer.writerow(dt)
            fLog.close()
        except:
            infoMsg("w",".....Unable to Save Failure Log")

def saveState(s):
    global State
    State['Calling'] = s
    State['Status'] = 'Current'
    State['Updated'] = datetime.datetime.now()
    try:
      outfile = open('State.pkl', 'wb')
      # Use a dictionary (rather than pickling 'raw' values) so
      # the number & order of things can change without breaking.
      pickle.dump(State, outfile)
      outfile.close()
    except:
      State['Status'] = 'Error'
      infoMsg("w",".....Unable to Save State")

def loadState():
    global State
    try:
      infile = open('State.pkl', 'rb')
      State= pickle.load(infile)
      infile.close()
    except:
      infoMsg("w",".....State File Not Found")

def reboot_now():
    os.system('reboot')

def shutdown_now():
    os.system('shutdown -h now')

def main():
    global last_temp, State
    global GO, REBOOT, SHUTDOWN, NOTICE, FAILURE_COUNTER

    last_pressure = 0
    # initialize the lastMinute variable to the current time to start
    last_minute = datetime.datetime.now().minute
    # on startup, just use the previous minute as lastMinute
    last_minute -= 1
    if last_minute == 0:
        last_minute = 59

    # infinite loop to continuously check weather values
    infoMsg("i","Start Loop...")

    while (GO==True):
        # The temp measurement smoothing algorithm's accuracy is based
        # on frequent measurements, so we'll take measurements every 5 seconds
        # but only show on DISPLAY_INTERVAL
        current_second = datetime.datetime.now().second
        # are we at the top of the minute or at a 5 second interval?
        if (current_second == 0) or ((current_second % 5) == 0):
            # ========================================================
            # read values from the Sense HAT
            # ========================================================
            # Calculate the temperature. The get_temp function 'adjusts' the recorded temperature adjusted for the
            # current processor temp in order to accommodate any temperature leakage from the processor to
            # the Sense HAT's sensor. This happens when the Sense HAT is mounted on the Pi in a case.
            # If you've mounted the Sense HAT outside of the Raspberry Pi case, then you don't need that
            # calculation. So, when the Sense HAT is external, replace the following line (comment it out  with a #)
            # calc_temp = get_temp()
            # with the following line (uncomment it, remove the # at the line start)
            # calc_temp = sense.get_temperature_from_pressure()
            # or the following line (each will work)
            # calc_temp = sense.get_temperature_from_humidity()
            # ========================================================
            # At this point, we should have an accurate temperature, so lets use the recorded (or calculated)
            # temp for our purposes

            AirTemperature=probe_temp(Config.TEMP_SENSOR_1)
            if (AirTemperature['status']==0):
                NOTICE['Air']['Notify']=False
                temp_c = round(AirTemperature['celcius'],1)
                temp_f = round(c_to_f(AirTemperature['celcius']),1)
                AirTemperatureProbeId = Config.PROBE_1
            elif Config.USE_SENSEHAT_TEMPERATURE:
                NOTICE['Air']['Notify']=True
                calc_temp = get_temp()
                temp_c = round(calc_temp,1)
                temp_f = round(c_to_f(calc_temp),1)
                AirTemperatureProbeId = 'SenseHat'
            else:
                temp_c = -99
                temp_f = -99
                AirTemperatureProbeId = 'NotSet'

            ColdFrameTemperature=probe_temp(Config.TEMP_SENSOR_2)
            if (ColdFrameTemperature['status']==0):
                NOTICE['ColdFrame']['Notify']=False
                coldframe_temp_c = round(ColdFrameTemperature['celcius'],1)
                coldframe_temp_f = round(c_to_f(ColdFrameTemperature['celcius']),1)
                ColdFrameTemperatureProbeId = Config.PROBE_2
            elif State['ColdFrameOn']:
                NOTICE['ColdFrame']['Notify']=True
                calc_temp = get_temp()
                coldframe_temp_c = 0
                coldframe_temp_f = 0
                ColdFrameTemperatureProbeId = 'None'
            else:
                coldframe_temp_c = -99
                coldframe_temp_f = -99
                ColdFrameTemperatureProbeId = 'NotSet'

            humidity = round(sense.get_humidity(), 1)
            # calculate dew point
            try:
                dew_point_c=round((B1*(math.log(humidity/100) + (A1*temp_c)/(B1 +temp_c)))/(A1-math.log(humidity/100)-A1*temp_c/(B1+temp_c)),1)
            except:
                dew_point_c=0.0
                infoMsg("i","************************************")
                infoMsg("i","******** Error on dew point ********")
                infoMsg("i","************************************")
                infoMsg("i","A1=======>"+str(A1))
                infoMsg("i","B1=======>"+str(B1))
                infoMsg("i","humidity=>"+str(humidity))
                infoMsg("i","temp_c===>"+str(temp_c))
                infoMsg("i","=========> (B1*(math.log(humidity/100) + (A1*temp_c)/(B1 +temp_c)))/(A1-math.log(humidity/100)-A1*temp_c/(B1+temp_c)) <<====")
                infoMsg("i","************************************")

            # convert pressure from millibars to inHg for weather underground
            calc_pressure = sense.get_pressure()
            pressure_mB = round(calc_pressure, 2)
            pressure_Hg = round(calc_pressure * 0.0295300, 2)
            # print("Temp: %sF (%sC), Pressure: %s inHg, Humidity: %s%%" % (temp_f, temp_c, pressure, humidity))
            # pressure = pressure_mB
            temp = temp_f
            pressure = pressure_mB

            # display celcius if SI selected
            if (Config.DISPLAY_SI): temp = temp_c

            # set display temp to integer
            display_temp=int(round(temp,0))

            # get the current minute
            current_minute = datetime.datetime.now().minute
            current_hour = datetime.datetime.now().hour

            # test pressure change over 15 minute intervals
            if (current_minute == 0) or ((current_minute % 15) == 0):
                last_pressure = round(pressure_mB,1)

            # show pressure trend
            this_pressure = round(pressure_mB,1)
            if (this_pressure>last_pressure): show_trending_up(b)
            elif (this_pressure<last_pressure): show_trending_down(b)
            else: show_steady_state(b)

            # print("C/L:%s=/=%s Temp: %sF (%sC), Dew Point: %d Pressure: %s inHg, Humidity: %s%%" % (current_minute, last_minute, temp_f, temp_c, dew_point_c, pressure, humidity))
            # is it the same minute as the last time we checked?
            if current_minute != last_minute:
                # reset last_minute to the current_minute
                last_minute = current_minute
                # is minute zero, or divisible by 10?
                # we're only going to take measurements every DISPLAY_INTERVAL minutes
                now = datetime.datetime.now()
                if (current_minute == 0) or ((current_minute % Config.DISPLAY_INTERVAL) == 0):
                    # print("\n%d minute mark (%d @ %s)" % (DISPLAY_INTERVAL, current_minute, str(now)))
                    # did the temperature go up or down?
                    if last_temp != display_temp:
                        rgb=g
                        if (display_temp<1): rgb=b
                        sense.clear()
                        if (current_hour>Config.SUNSET) and (current_hour<Config.SUNRISE): sense.low_light = True
                        show_number(display_temp, rgb)
                    last_temp = display_temp

                    # show pressure trend
                    # if (pressure_mB>last_pressure): show_trending_up(b)
                    # elif (pressure_mB<last_pressure): show_trending_down(b)
                    # else: show_steady_state(b)

                    # last_pressure = pressure_mB

                utc_datetime=datetime.datetime.utcnow()
                local_datetime=datetime.datetime.now()

                # ========================================================
                # Upload the weather data to DB's
                # ========================================================
                if Config.PW_UPLOAD:
                    if (current_minute == 0) or ((current_minute % Config.PW_UPLOAD_INTERVAL) == 0):
                        # print("Pi Server Upload...%s" % (local_datetime))
                        infoMsg("d","Pi Server Upload...")
                        NOTICE['DataLoad']['Notify']=False
                        NOTICE['PiServer']['Notify']=False
                        rpt_dim=0
                        rpt_display=0
                        rpt_coldframe=0
                        rpt_WU=0
                        if State['DisplayDim']==True: rpt_dim=1
                        if State['DisplayOn']==True: rpt_display=1
                        if State['ColdFrameOn']==True: rpt_coldframe=1
                        if State['WUUpload']==False: rpt_WU=0
                        else: rpt_WU=State['WUInterval']
                        # From http://wiki.wunderground.com/index.php/PWS_-_Upload_Protocol
                        # print("Uploading data to Weather Pi")
                        # build a weather data object
                            # "cf": str(coldframe_temp_c),
                            # "cid": str(ColdFrameTemperatureProbeId),
                        weather_data = {
                            "si": Config.PW_ID,
                            "t": str(temp),
                            "rh": str(humidity),
                            "p": str(pressure),
                            "dp": str(dew_point_c),
                            "sld": local_datetime.strftime('%Y-%m-%d'),
                            "slt": local_datetime.strftime('%H:%M:%S'),
                            "stz": Config.LOCAL_STATION_TIMEZONE,
                            "sud": utc_datetime.strftime('%Y-%m-%d'),
                            "sut": utc_datetime.strftime('%H:%M:%S'),
                            "pid": str(AirTemperatureProbeId),
                            "cf": str(coldframe_temp_c),
                            "cid": str(ColdFrameTemperatureProbeId),
                            "dd": str(rpt_dim),
                            "do": str(rpt_display),
                            "co": str(rpt_coldframe),
                            "wu": str(rpt_WU),
                            "st": "Current",
                        }
                        try:
                            upload_url = Config.PW_URL + "?" + urlencode(weather_data)
                            response = urllib2.urlopen(upload_url)
                            rtn_control = json.load(response)
                            FAILURE_COUNTER=0
                            if ("Status" in rtn_control):
                                infoMsg("d","Returned==> %s" % str(rtn_control))
                                if (rtn_control["Status"]==0):
                                    NOTICE['DataLoad']['Notify']=False
                                elif (rtn_control["Status"]==1):
                                    infoMsg("i","Parameter Updates...")
                                    NOTICE['DataLoad']['Notify']=False
                                    if "PiShutdown" in rtn_control:
                                        GO=False
                                        SHUTDOWN=True
                                        infoMsg("i","Shutting Down Weather Pi....")
                                    if "PiReboot" in rtn_control:
                                        GO=False
                                        REBOOT=True
                                        infoMsg("i","Rebooting Weather Pi....")
                                    if "WeatherPiOff" in rtn_control:
                                        GO=False
                                        infoMsg("i","Shutting Weather Pi App Off....")
                                    if "DisplayDim" in rtn_control:
                                        if (rtn_control["DisplayDim"]=='Yes'):
                                            Config.DISPLAY_DIM=True
                                            infoMsg("i","Display to Dim")
                                        else:
                                            Config.DISPLAY_DIM=False
                                            infoMsg("i","Display to Bright")
                                        State['DisplayDim']=Config.DISPLAY_DIM
                                        State['Status']='Stale'
                                    if "DisplayOn" in rtn_control:
                                        if (rtn_control["DisplayOn"]=='Yes'):
                                            Config.DISPLAY_ON=True
                                            show_number(display_temp, rgb)
                                            infoMsg("i","Display On")
                                        else:
                                            Config.DISPLAY_ON=False
                                            sense.clear()
                                            infoMsg("i","Display Off")
                                        State['DisplayOn']=Config.DISPLAY_ON
                                        State['Status']='Stale'
                                    if "PiServerUploadInterval" in rtn_control:
                                        if (int(rtn_control["WUServerUploadInterval"])>0):
                                            Config.PW_UPLOAD=True
                                            Config.PW_UPLOAD_INTERVAL=int(rtn_control["PiServerUploadInterval"])
                                            infoMsg("i","Setting Upload to Weather DB to "+str(Config.PW_UPLOAD_INTERVAL)+" minutes")
                                        else:
                                            Config.PW_UPLOAD=False
                                            infoMsg("i","Setting Upload to Weather DB Off")
                                    if "ColdFrame" in rtn_control:
                                        infoMsg("i","Setting ColdFrame "+rtn_control["ColdFrame"])
                                        if (rtn_control["ColdFrame"]==On):
                                            Config.USE_PROBE_2=True
                                        else:
                                            Config.USE_PROBE_2=False
                                        State['ColdFrameOn']=Config.USE_PROBE_2
                                        State['Status']='Stale'
                                    if "WUServerUploadInterval" in rtn_control:
                                        infoMsg("i","Setting WUServerUploadInterval=> %s" % rtn_control["WUServerUploadInterval"])
                                        Config.WU_UPLOAD=False
                                        if (int(rtn_control["WUServerUploadInterval"])>14):
                                            Config.WU_UPLOAD=True
                                            Config.WU_UPLOAD_INTERVAL=int(rtn_control["WUServerUploadInterval"])
                                            infoMsg("i","Setting WU Interval to "+str(Config.WU_UPLOAD_INTERVAL)+" minutes")
                                        else:
                                            Config.WU_UPLOAD=False
                                            infoMsg("i","Setting Weather Underground Upload Off")
                                        State['WUUpload']=Config.WU_UPLOAD
                                        State['WUInterval']=Config.WU_UPLOAD_INTERVAL
                                        State['Status']='Stale'
                                else:
                                    infoMsg("w","...DataLoad Status "+rtn_control["Status"])
                                    infoMsg("w","...Weather_data==>"+str(weather_data))
                                    NOTICE['DataLoad']['Notify']=True
                            else:
                                html = response.read()
                                infoMsg("w","...DataLoad No Status Returned")
                                infoMsg("w","...Server response==>"+str(html))
                                response.close()  # best practice to close the file
                                NOTICE['PiServer']['Notify']=True

                        except:
                            infoMsg("w","...PW Exception:"+str(sys.exc_info()[0]))
                            t=str(temp)
                            rh=str(humidity)
                            p=str(pressure)
                            dp=str(dew_point_c)
                            cf=str(coldframe_temp_c)
                            pid=str(AirTemperatureProbeId)
                            cid=str(ColdFrameTemperatureProbeId)
                            if Config.FAILURE_CSV: failureLog(t,rh,p,dp,cf,pid,cid,current_minute)
                            NOTICE['PiServer']['Notify']=True
                            FAILURE_COUNTER=FAILURE_COUNTER+1
                            if (FAILURE_COUNTER>Config.FAILURE_MAX) and (Config.FAILURE_REBOOT):
                                GO=False
                                REBOOT=True
                                infoMsg("i","Rebooting Weather Pi Due To Excessive Upload Failures (%s)...." % str(FAILURE_COUNTER))

                # else:
                    # NOTICE['PiServer']['Notify']=True
                    # print("Skipping Weather Pi upload")

                # ========================================================
                # Upload the weather data to Weather Underground
                # ========================================================
                # is weather upload enabled (True)?
                if State['WUUpload']:
                    if (current_minute == 0) or ((current_minute % State['WUInterval']) == 0):
                        # From http://wiki.wunderground.com/index.php/PWS_-_Upload_Protocol
                        # print("Uploading data to Weather Underground")
                        # build a weather data object
                        infoMsg("d","WU Server Upload...")
                        weather_data = {
                            "action": "updateraw",
                            "ID": wu_station_id,
                            "PASSWORD": wu_station_key,
                            "dateutc": "now",
                            "tempf": str(temp_f),
                            "humidity": str(humidity),
                            "baromin": str(pressure_Hg),
                        }
                        try:
                            upload_url = Config.WU_URL + "?" + urlencode(weather_data)
                            response = urllib2.urlopen(upload_url)
                            html = response.read()
                            infoMsg("d","WU Response:"+str(html))
                            response.close()  # best practice to close the file
                            NOTICE['WUServer']['Notify']=False
                        except:
                            infoMsg("w","...WU URL      :"+str(upload_url))
                            infoMsg("w","...WU Exception:"+str(sys.exc_info()[0]))
                            # infoMsg("w","...WU Response:"+str(html))
                            NOTICE['WUServer']['Notify']=True

                # else:
                    # NOTICE['WUServer']['Notify']=True
                    # print("Skipping Weather Underground upload")

            if State['Status']=='Stale': saveState('main')
            # scroll notifications if any are set
            check_notification()

        # wait a second then check again
        # You can always increase the sleep value below to check less often
        time.sleep(1)  # this should never happen since the above is an infinite loop

    infoMsg("i","Sending GoodBye....")
    sense.clear()
    sense.show_message("GoodBye", text_colour=[255, 255, 0], back_colour=[0, 0, 255])
    time.sleep(10)
    sense.clear()
    if (SHUTDOWN):
        infoMsg("i","Shutdown....")
        shutdown_now()
    if (REBOOT):
        infoMsg("i","Reboot....")
        reboot_now()
    infoMsg("i","Exiting!")

# ============================================================================
# Start Start Start Start Start Start Start Start Start Start Start Start
# ============================================================================
infoMsg("i",".........................")
infoMsg("i",".........................")
infoMsg("i","Weather Pi....Starting...")
infoMsg("i",".........................")
infoMsg("i",".........................")

infoMsg("i","Initializing Configuration")

infoMsg("i","USE_PROBE_1================>"+str(Config.USE_PROBE_1))
infoMsg("i","PROBE_1====================>"+Config.PROBE_1)
infoMsg("i","TEMP_SENSOR_1==============>"+Config.TEMP_SENSOR_1)
infoMsg("i","USE_PROBE_2================>"+str(Config.USE_PROBE_2))
infoMsg("i","PROBE_2====================>"+Config.PROBE_2)
infoMsg("i","TEMP_SENSOR_2==============>"+Config.TEMP_SENSOR_2)
infoMsg("i","USE_SENSEHAT_TEMPERATURE===>"+str(Config.USE_SENSEHAT_TEMPERATURE))

infoMsg("i","LOCAL_STATION_ID===========>"+Config.LOCAL_STATION_ID)
infoMsg("i","LOCAL_STATION_TIMEZONE=====>"+Config.LOCAL_STATION_TIMEZONE)

infoMsg("i","SUNRISE====================>"+str(Config.SUNRISE))
infoMsg("i","SUNSET=====================>"+str(Config.SUNSET))

infoMsg("i","MEASUREMENT_INTERVAL=======>"+str(Config.MEASUREMENT_INTERVAL))
infoMsg("i","DISPLAY_INTERVAL===========>"+str(Config.DISPLAY_INTERVAL))
infoMsg("i","DISPLAY_ON=================>"+str(Config.DISPLAY_ON))
infoMsg("i","DISPLAY_DIM================>"+str(Config.DISPLAY_DIM))
infoMsg("i","DISPLAY_SI=================>"+str(Config.DISPLAY_SI))

infoMsg("i","FAILURE_CSV================>"+str(Config.FAILURE_CSV))
infoMsg("i","FAILURE_DIR================>"+str(Config.FAILURE_DIR))
infoMsg("i","FAILURE_REBOOT=============>"+str(Config.FAILURE_REBOOT))
infoMsg("i","FAILURE_MAX================>"+str(Config.FAILURE_MAX))

infoMsg("i","PW_UPLOAD==================>"+str(Config.PW_UPLOAD))
infoMsg("i","PW_UPLOAD_INTERVAL=========>"+str(Config.PW_UPLOAD_INTERVAL))
infoMsg("i","PW_URL=====================>"+Config.PW_URL)
infoMsg("i","PW_ID======================>"+Config.PW_ID)

infoMsg("i","WU_UPLOAD==================>"+str(Config.WU_UPLOAD))
infoMsg("i","WU_UPLOAD_INTERVAL=========>"+str(Config.WU_UPLOAD_INTERVAL))
infoMsg("i","WU_URL=====================>"+Config.WU_URL)

# make sure we don't have a DISPLAY_INTERVAL > 60
if (Config.MEASUREMENT_INTERVAL is None) or (Config.MEASUREMENT_INTERVAL > 60):
    infoMsg("w","The application's 'MEASUREMENT_INTERVAL' cannot be empty or greater than 60")
    sys.exit(1)
if (Config.DISPLAY_INTERVAL is None) or (Config.DISPLAY_INTERVAL > 60):
    infoMsg("w","The application's 'DISPLAY_INTERVAL' cannot be empty or greater than 60")
    sys.exit(1)
if (Config.PW_UPLOAD_INTERVAL is None) or (Config.PW_UPLOAD_INTERVAL > 60):
    infoMsg("w","The application's 'PW_UPLOAD_INTERVAL' cannot be empty or greater than 60")
    sys.exit(1)
if (Config.WU_UPLOAD_INTERVAL is None) or (Config.WU_UPLOAD_INTERVAL < 15) or (Config.WU_UPLOAD_INTERVAL > 60):
    infoMsg("w","The application's 'WU_UPLOAD_INTERVAL' cannot be empty, less than 15 or greater than 60")
    sys.exit(1)

#  Set Weather Underground Configuration Parameters
wu_station_id = Config.STATION_ID
wu_station_key = Config.STATION_KEY
if (wu_station_id is None) or (wu_station_key is None):
    infoMsg("w","Missing values from the Weather Underground configuration file")
    Config.WU_UPLOAD = False

infoMsg("i","Station ID:"+wu_station_id)

infoMsg("i","Successfully Set Configuration Values")

infoMsg("i","Load Saved State")

# weather station state
State= {'Status': 'Stale',
        'Updated': 'Unknown',
        'DisplayDim': False,
        'DisplayOn': True,
        'ColdFrameOn': True,
        'WUUpload': False,
        'WUInterval': 15}

State['DisplayDim']=Config.DISPLAY_DIM
State['DisplayOn']=Config.DISPLAY_ON
State['ColdFrameOn']=Config.USE_PROBE_2
State['WUUpload']=Config.WU_UPLOAD
State['WUInterval']=Config.WU_UPLOAD_INTERVAL

loadState()

infoMsg("i","State -> Status ==========>"+str(State['Status']))
infoMsg("i","         Updated =========>"+str(State['Updated']))
infoMsg("i","         DisplayDim ======>"+str(State['DisplayDim']))
infoMsg("i","         DisplayOn =======>"+str(State['DisplayOn']))
infoMsg("i","         ColdFrameOn =====>"+str(State['ColdFrameOn']))
infoMsg("i","         WUUpload ========>"+str(State['WUUpload']))
infoMsg("i","         WUInterval ======>"+str(State['WUInterval']))

infoMsg("i","Successfully Set State Values")

# ============================================================================
# initialize the Sense HAT object
# ============================================================================
try:
    infoMsg("i","Initializing the Sense HAT client")
    sense = SenseHat()
    sense.low_light = False
    # if (current_hour>SUNSET) and (current_hour<SUNRISE): sense.low_light = True
    # sense.set_rotation(180)
    # then write some text to the Sense HAT's 'screen'
    sense.show_message("Weather Pi", text_colour=[255, 255, 0], back_colour=[0, 0, 255])
    # clear the screen
    sense.clear()
    # get the current temp to use when checking the previous measurement
    # last_temp = int(round(c_to_f(get_temp()), 0))
    last_temp = 0
    rgb=g
    if (last_temp<1): rgb=b
    # sense.low_light = True
    show_number(last_temp, rgb)
    infoMsg("i","Current temperature reading:"+str(last_temp))
except:
    infoMsg("w","...Unable to initialize the Sense HAT library:"+str(sys.exc_info()[0]))
    sys.exit(1)


infoMsg("i","Initialization complete!")

# Now see what we're supposed to do next
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting application\n")
        sys.exit(0)

    saveState('__main__')
