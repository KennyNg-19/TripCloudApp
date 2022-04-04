import os, re, json, urllib, requests, math
import datetime

import pandas as pd
import numpy as np

from collections import defaultdict
from tqdm import tqdm

import geopy.distance

#########################################
# may need to add timer for api callers
#########################################

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
    # in the starting part, get parking lot availability data for future use <- really fast... get results immediately...
    # out:
    # record: dict, { carpark_id : available lots }
    now = datetime.datetime.now()

    date = str(now.date())
    time = str(now.time())
    time = time[:time.find(".")] # remove ms part
    carpark_availaility = get_parking_data(date, time)
    
    record = dict()
    for lots in tqdm(carpark_availaility["carpark_data"]):
        record[lots["carpark_number"]] = lots["carpark_info"][0]["lots_available"]
    return record
# temp = get_current_parking_data()
# print(temp["Y38"])


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


def convert_hdb_parking_data(hdb_data_path="data/hdb-carpark-information.csv", save_path=None):
    # reorgnize and extract the data of hdb-carpark-info, save as json dict file, takes around 7 minutes to finish
    # input:
    # hdb_data_path, save_path: str, file paths
    # output:
    # record: dict {car_park_num <- identifier: [lat, long, address, short_term_parking, fress_parking, night_parking, gantry_height] <- info}
    df = pd.read_csv(hdb_data_path)
    record = dict()
    for idx, row in tqdm(df.iterrows()):
        carpark_num = row["car_park_no"]
        x_coord, y_coord = row["x_coord"], row["y_coord"]
        # record[carpark_num] = get_lat_and_long(x_coord, y_coord)
        x_coord, y_coord = get_lat_and_long(x_coord, y_coord)
        record[carpark_num] = [x_coord, y_coord, row["address"], row["short_term_parking"], row["free_parking"], row["night_parking"], row["gantry_height"]]
    if save_path:
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        with open(save_path + "carpark_coordinates.json", "w") as fout:
            json.dump(record, fout)
    return record
# carpark_coord = convert_hdb_parking_data(save_path="data/")
# print(len(carpark_coord)) # 2176


def scaled_euclidean_dis(x1, y1, x2, y2, scaling=1000):
    x1 *= scaling
    y1 *= scaling
    x2 *= scaling
    y2 *= scaling
    return math.sqrt( (x1 - x2)**2 + (y1- y2)**2 )


def find_closest_N_carpark(places, carparks, N=5, save_path=None):
    # for every recorded place, compute the closest N parking lot and save as json dict file
    # input:
    # places: data frame, [name, address, type, lat, long]
    # carparks: dict, pre computed coordinate
    # output:
    # record: dict {place_name: [ parking lot identifier ]}
    carpark_id = list(carparks.keys())
    carpark_coord = np.array([v[:2] for _, v in carparks.items()])
    
    scaling = 1000 ######
    record = defaultdict(list)
    for idx, row in tqdm(places.iterrows()):
        name = row["name"]
        lat  = float(row["lat"])
        lon  = float(row["lon"])
        coord = np.array([[lat, lon]])
        
        distance = np.power(carpark_coord * scaling - coord * scaling, 2).sum(axis=1)
        distance = np.sqrt(distance)
        closest_idx = np.argsort(distance)[:N]
        for idx in closest_idx:
            record[name].append(carpark_id[idx])
    if save_path:
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        with open(save_path + "closest_parking_lot.json", "w") as fout:
            json.dump(record, fout)
    return record
# places = pd.read_csv("sg-places-new.csv")
# with open("data/carpark_coordinates.json") as fin:
#     carparks = json.load(fin)
# find_closest_N_carpark(places, carparks, save_path="data/")


def NV_find_closest_N_carpark(place_lat, place_lon, N=5, carpark_coord=None):
    # new version, compute closest N parking lot given coordinates
    # input:
    # place_lat, place_lon: latitude and longitude of a desired place, str or float
    # N: num of output parking lots
    # carpark_coord: dict, pre-saved parking lots information
    # output:
    # result: list [ "parking lot id" ]
    if not carpark_coord:
        with open("data/carpark_coordinates.json") as fin:
            carpark_coord = json.load(fin)
    
    carpark_id    = list(carpark_coord.keys())
    carpark_coord = np.array([v[:2] for _, v in carpark_coord.items()]) * 1000
    place_coord   = np.array([place_lat, place_lon], dtype=float) * 1000
    distance = np.power(carpark_coord - place_coord, 2).sum(axis=1)
    distance = np.sqrt(distance)
    result = []
    for idx in np.argsort(distance)[:N]:
        result.append(carpark_id[idx])
    return result
# print(NV_find_closest_N_carpark(place_lat=1.315874, place_lon=103.834639)) # ['BH1', 'BH2', 'KJM1', 'KJ3', 'AH1']


def check_availability(parks, availability=None):
    # given a list of desired parking lots id, return remaining lots for each in the same order
    # input:
    # parks: str, carparking_id
    # output: 
    # record: int or str, remain_lots or N/A
    if not availability:
        availability = get_current_parking_data()
    record = "N/A"
    if parks in availability.keys():
        record = availability[parks]
    return record
# print(check_availability(["BH1", "BH2", "KJM1", "KJ3", "AH1"]))


def distance_from_dest(dest_lat, dest_lon, carpark_lat,car_park_lon):
    return geopy.distance.distance([dest_lat, dest_lon], [carpark_lat,car_park_lon]).km


# # running example: 
# # for a selected place, e.g. VIP Hotel, coordinates [1.315874, 103.834639]
# with open("data/carpark_coordinates.json") as fin:
#     coordinates = json.load(fin)
# with open("data/closest_parking_lot.json") as fin:
#     closest_parking_lot = json.load(fin)
# VIP_Hotel_closest = closest_parking_lot["VIP Hotel"]
# print("Closest parking lots: ", VIP_Hotel_closest) # ['BH1', 'BH2', 'KJM1', 'KJ3', 'AH1']
# print("Their coordinates: ", [coordinates[name] for name in VIP_Hotel_closest]) # [[1.3249913646328675, 103.8424599258254], [1.3260459729073188, 103.842761303002], [1.3160936666077356, 103.84879589885311], [1.3144266158666138, 103.84993059473969], [1.3282834951094042, 103.84461988914597]]
# print("Remaining lots: ", check_availability(VIP_Hotel_closest)) # ['47', '39', '162', '145', '125']

###################################################

# avai = get_current_parking_data()
# k_avai = set(avai.keys()) # len: 1960
# with open("data/carpark_coordinates.json") as fin:
#     coord = json.load(fin)
# k_coord = set(coord.keys()) # len: 2176
# print(len(k_avai), len(k_coord))

# uni = (k_avai & k_coord) # len: 1893
# print(len(uni))

# print(len(k_coord - k_avai)) # 287

####################################################

# 为了Bokeh的画图： Define function to switch from lat/long to mercator coordinates
def x_coord(x, y):
    lat = x
    lon = y

    r_major = 6378137.000
    x = r_major * np.radians(lon)
    scale = x / lon
    y = 180.0 / np.pi * np.log(np.tan(np.pi / 4.0 +
                                      lat * (np.pi / 180.0) / 2.0)) * scale
    return (x, y)




