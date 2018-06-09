WeatherPi
=========

WeatherPi is a Python application making use of a SenseHat & temperature probes
to gather information that is logged to a database.

See the WeatherDB & WeatherConsole repositories for complementary applications
that log & present the data.

WeatherPi (weather_pi.py) was pulled together from various other Raspberry Pi
(and Arduino) projects. The core function pulls data from the SenseHat
and probes before logging the data to a local DB server and the WeatherUnderground
web service.

**Prerequisites:**

Raspberry Pi (anything that supports the SenseHat)

SenseHat

1 or 2 DS18B20 Temperature Probes

**Setup**

SenseHat - plug in, get libs

Probes - see various instructables - Links to come

Cron - see sample crontab, I reboot once a day to cover any interruptions

**Get repo:**

    git clone https://github.com/dcreith/WeatherPi.git

**Usage:**

cd home/pi/weatherstation

sudo python ./weather_pi.py
