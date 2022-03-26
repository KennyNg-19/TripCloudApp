import os, re, json, urllib, requests
import datetime

import pandas as pd


# may need to add timers for api call
def get_parking_data(date, time):
    # get carparking information given date and time
    # input:
    # date: str, a valid date can be today or past in YYYY-MM-DD format, eg 2022-03-01
    # time: str, valid time in a day in HH:MM:SS format, eg 09:30:00
    # output:
    # carpark_data: dict{timestamp, carpark_data: [{carpark_info}]}
    request_url = "https://api.data.gov.sg/v1/transport/carpark-availability?date_time={date}T{time}".format(date=date, time=time)
    carparking = requests.get(request_url).text
    carparking = json.loads(carparking)
    carpark_data = carparking["items"][0]
    return carpark_data


def get_current_parking_data():
    now = datetime.datetime.now()

    date = str(now.date())
    time = str(now.time())
    time = time[:time.find(".")] # remove ms part
    return get_parking_data(date, time)


def get_lat_and_long(x_coord, y_coord):
    # use oneMap coordinate convertor: https://www.onemap.gov.sg/docs/#coordinates-converters
    # input:
    # x_coord, y_coord: str, coordinate in SVY21 format
    # output:
    # lat, long: float, latitude and longitude, 
    request_url = "https://developers.onemap.sg/commonapi/convert/3414to4326?X={X}&Y={Y}".format(X=x_coord, Y=y_coord)
    coordinate  = requests.get(request_url).text
    coordinate  = json.loads(coordinate)
    return coordinate["latitude"], coordinate["longitude"]
# get_lat_and_long("21443.7871", "39574.4888")


def convert_hdb_parking_data(data_path="data/hdb-carpark-information.csv", save_path=None):
    # reorgnize and extract the data of hdb-carpark-info
    # input:
    # data_path, save_path: str, file paths
    # output:
    # data: dict {car_park_num <- identifier: {lat, long, or something needed (determined later)} <- info}
    pass




