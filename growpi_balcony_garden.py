import csv
import math
import os
import picamera
import time
import secrets
#not all modules are needed a lot depends on your sensors type/model
#i got mine from ali ;))


from ftplib import FTP
from grovepi import *
from grove_rgb_lcd import *

# connect your sensors with rPI
# Connect waterpump

# set up your sensors
moistureSensor = 0
lightSensor = 1
waterPump = 2
ledRed = 3
tempSensor = 4
distanceSensor = 6

# Heights
potHeight = 12
sensorHeight = 73
#display is also optional
displayInterval = 1 * 60  # How long should the display stay on?
checkInterval = 10 * 60  # How long before loop starts again?
lightThreshold = 10  # Value above threshold is lightsOn

dryIntervals = 5  # How many consecutive dry intervals before waterPlants
mlSecond = 5  # How much ml water the waterpump produces per second
waterAmount = 50  # How much ml water should be given to the plants

localImagePath = '/kacper/pi/Desktop/images/'  # Where the images are stored



def appendCSV():
    fields = ['Time', 'Temperature', 'Humidity', 'Moisture', 'MoistureClass',
              'LightValue', 'Lights', 'PiTemperature', 'Height', 'SonicDistance', 'Image', 'WaterGiven']

    with open(r'temp.csv', 'a') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writerow({'Time': currentTime,
                         'Temperature': temp,
                         'Humidity': humidity,
                         'Moisture': moisture,
                         'MoistureClass': moistureClass,
                         'LightValue': lightValue,
                         'Lights': lightsOn,
                         'PiTemperature': (piTemperature()),
                         'Height': (calcPlantHeight()),
                         'SonicDistance': ultraSonicDistance,
                         'Image': image,
                         'WaterGiven': waterGiven
                         })


def calcPlantHeight():
    return sensorHeight - potHeight - ultraSonicDistance


def displayText():
    setRGB(0, 128, 64)
    setText("{}C {}% {}\n{} ({}) {}".format(temp, humidity,
                                            piTemperature(), moisture, moistureClass, lightValue))
    time.sleep(displayInterval)
    setText("")
    setRGB(0, 0, 0)


def piTemperature():
    temp = os.popen("vcgencmd measure_temp").readline()
    return temp[5:9]


def moistureClassifier():
    if moisture < 300:
        moistureResult = 'Dry'
    elif moisture < 600:
        moistureResult = 'Moist'
    else:
        moistureResult = 'Wet'
    return moistureResult


def printSensorData():
    print(currentTime)
    if math.isnan(temp) == False and math.isnan(humidity) == False:
        print("Temperature: {}'C\nHumidity: {}%".format(temp, humidity))
    else:
        print("Couldn't get temperature/humidity sensor readings")

    print('Moisture: {0} ({1})'.format(moisture, moistureClass))
    print("Lights: {} ({})".format(lightValue, "On" if lightsOn else "Off"))
    print("Height: {} cm".format(calcPlantHeight()))
    print("Raspberry pi: {}'C".format(piTemperature()))
    if waterGiven:
        print("Water given: {}ml".format(waterGiven))
    if lightsOn:
        print("Image: {}\n".format(image))
    else:
        print("")


# sleeptime
def sleepTimer():
    currentMinute = time.strftime("%M")
    currentSecond = time.strftime("%S")
    sleeptime = (10 - int(currentMinute[1])) * 60 - int(currentSecond)
    time.sleep(sleeptime)


def takePicture():
    timestamp = time.strftime("%Y-%m-%d--%H-%M")
    image = '{}.jpg'.format(timestamp)
    imagePath = localImagePath + image
    with picamera.PiCamera() as camera:
        camera.start_preview()
        camera.awb_mode = 'sunlight'
        time.sleep(5)
        camera.capture(imagePath)
        camera.stop_preview()
    return image


def uploadCSV():
    ftp = FTP(secrets.FTP_URL)
    ftp.login(user=secrets.USERNAME, passwd=secrets.PASSWORD)
    filename = 'temp.csv'
    ftp.storbinary('STOR ' + filename, open(filename, 'rb'))
    ftp.quit()


def uploadImage():
    if image:
        ftp = FTP(secrets.FTP_URL)
        ftp.login(user=secrets.USERNAME, passwd=secrets.PASSWORD)
        ftp.cwd('/images/')
        filename = localImagePath + image
        ftp.storbinary('STOR ' + image, open(filename, 'rb'))
        ftp.quit()


def waterPlants():
    digitalWrite(waterPump, 1)
    time.sleep(waterAmount / mlSecond)
    digitalWrite(waterPump, 0)


# Main Loop

waterCheck = []
while True:
    try:
        # Start loop at every tenth minute of the hour
        sleepTimer()

        # Get sensor readings
        lightValue = analogRead(lightSensor)
        ultraSonicDistance = ultrasonicRead(distanceSensor)
        moisture = analogRead(moistureSensor)
        [temp, humidity] = dht(tempSensor, 1)

        currentTime = time.ctime()
        moistureClass = moistureClassifier()
        lightsOn = lightValue > lightThreshold

        # Lights on
        if lightsOn:
            # Turn on red LED when ground is dry, when lightsOn
            if moistureClass == 'Dry':
                digitalWrite(ledRed, 1)
                waterCheck.append(moisture)

                # Get x consecutive dryIntervals, before waterPlants
                if len(waterCheck) >= dryIntervals:
                    waterPlants()
                    waterGiven = waterAmount
                    waterCheck = []
                else:
                    waterGiven = 0

            # Ground not dry
            else:
                waterCheck = []
                waterGiven = 0
                digitalWrite(ledRed, 0)

            # Take picture every loop, while lightsOn, store path in image variable
            image = takePicture()

            # PrintSensorData and appendCSV, before displayText
            printSensorData()
            appendCSV()
            uploadImage()
            uploadCSV()

            # Textdisplay when lightsOn
            displayText()

        # Lights off
        else:
            waterCheck = []
            waterGiven = 0

            # In case ground was dry, when lightsOn
            digitalWrite(ledRed, 0)

            # No picture when lights off, empty string for appendCSV
            image = ''

            printSensorData()
            appendCSV()
            uploadCSV()

    except KeyboardInterrupt:
        digitalWrite(waterPump, 0)
        digitalWrite(ledRed, 0)
        setText("")
        setRGB(0, 0, 0)
        print(" Leds and RGB shutdown safely")
        break
    except IOError:
        print("Error")
