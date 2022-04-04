from distutils.log import info
from utils import *
import streamlit as st
import pandas as pd
# 压制SettingWithCopyWarning的warning
pd.set_option('mode.chained_assignment', None)

import numpy as np

import warnings
warnings.filterwarnings("ignore")

# bokeh==2.4.1， not latest 2.4.2
from bokeh.io import output_notebook, show, output_file
from bokeh.plotting import figure, ColumnDataSource
from bokeh.tile_providers import get_provider, Vendors
from bokeh.palettes import PRGn, RdYlGn
from bokeh.layouts import row, column

# function for calculate distance: mgeopy.distance.distance(coord1, corrd2)
import geopy.distance

# API to get current lang and lont
import geocoder
# my_lan_lon = geocoder.ip('me').latlng
# print(type(my_lan_lon[0]))
# my_lan_lon = geocoder.google('Mountain View, CA').latlng


# 标题
st.title('TripElite 🚗 💨')
st.subheader("- A platform for finding entertainment and carpark places.")

# read data
df = pd.read_csv("sg-places-new.csv").dropna()

#! step0: input a 目的地, in Singapore to go
st.write("### 0. Input a Destination in SG you plan to reach:")
input_destination = st.text_input("A place name in SG, PRESS Enter!")
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="example app")
info_dict = geolocator.geocode(input_destination + " ,Singapore").raw
my_lan_lon = [float(info_dict['lat']), float(info_dict['lon'])]

#! step1: 获取目的地周围的
st.write("### 1.Find Entertainment places nearby")
tp = st.selectbox("Place type", df['type'].unique())

num = st.selectbox("No. of closest places(Less than 10)", range(1,11))

# 有输入了，再生成DF+画图
if input_destination:
    # 需要根据位置坐标，排序
    st.write(f"Your place geolocation is {[round(num, 3) for num in my_lan_lon]}, \
        {num} closest {tp} is/are:")

    # filter by type
    df_with_type = df.loc[df.type == tp]

    # 计算离my_loc的距离
    dis2me = [] # add a new colm
    for idx, row in df_with_type.iterrows():
        dis2me.append(geopy.distance.distance(my_lan_lon, [row.lat, row.lon]).km)
    df_with_type.loc[:, 'dis2me'] = dis2me # add a new col
    # st.write(df_with_type)

    # 获取K个最近的地点
    df_K_closest = df_with_type.nsmallest(num, 'dis2me')
    df_K_closest.reset_index(drop=True, inplace=True)
    st.write(df_K_closest.drop('type', axis=1))

    # 同时，一行new row 加入my location，一起做转化和可视化在图上
    df_K_closest.loc[-1] = [input_destination, info_dict['display_name'], '', my_lan_lon[0], my_lan_lon[1], 0.0]

    # ------------------------Boken 画图准备-----------------------

    # Define coord as tuple (lat,long)
    df_K_mercat = df_K_closest.copy(deep=True)
    df_K_mercat['coordinates'] = list(zip(df_K_mercat['lat'], df_K_mercat['lon']))

    # Obtain list of mercator coordinates
    mercators = [x_coord(x, y) for x, y in df_K_mercat['coordinates']]
    # Create mercator column in our df_K_closest
    df_K_mercat['mercator'] = mercators
    # Split that column out into two separate columns - mercator_x and mercator_y
    df_K_mercat[['mercator_x', 'mercator_y']] = df_K_mercat['mercator'].apply(pd.Series)
    # Select tile set to use
    chosentile = get_provider(Vendors.STAMEN_TONER)
    # Choose palette
    palette = PRGn[10]

    # Set tooltips - these appear when we hover over a data point in our map, very nifty and very useful
    tooltips = [("Place Name","@name"), ("Address", "@address")]

    # Create figure
    p = figure(title = 'Places@Singapore', x_axis_type="mercator", y_axis_type="mercator",
            x_axis_label = 'Longitude', y_axis_label = 'Latitude', tooltips = tooltips,
            plot_width=900, plot_height=800)

    # Add map tile
    p.add_tile(chosentile)
    df_myloc = ColumnDataSource(data=df_K_mercat.iloc[-1:])

    # 始终显示 the point for my location
    p.inverted_triangle(x='mercator_x', y='mercator_y',
            source=df_myloc, size=25, fill_alpha=1, color='red')
#-------------------准备end--------------------

    #选择地点并获取附近停车场
    with open("data/carpark_coordinates.json") as fin:
        coordinates = json.load(fin)
    with open("data/closest_parking_lot.json") as fin:
        closest_parking_lot = json.load(fin)

    # 获取用户选择的目的地
    st.write("### 2.Choose a Place, then Carpark info will show up.")
    df_K_closest = df_K_closest.iloc[:-1]
    # dest_name = df_K_closest.name[0]
    dest_name = st.selectbox(f"Choose a destination from the {num} nearest places above",
                            pd.Series(" ").append(df_K_closest.name))
    # dest_info = df_K_closest.loc[df_K_closest['name']==dest_name]

    ###########################################################
    # pre-call this function to save time
    # THIS IS TIME CONSUMING. DO NOT CALL THIS TOO FREQUENTLY.
    available_parking_lots = get_current_parking_data()
    ###########################################################

    # ------------------判定显示：选定的places VS 停车场-----------------
    if dest_name == " ": # 第一幅图
        df_places = ColumnDataSource(data=df_K_mercat.iloc[:-1])

        p.circle(x='mercator_x', y='mercator_y',
                source=df_places, size=15, fill_alpha=.7)
    
    else: # 第二幅图，停车信息
        st.write(f"You choose {dest_name} as destination(<font color=‘blue’>blue traingle</font>)!", unsafe_allow_html=True)
        st.write("The Parking info are shown as above(<font color=green>green circle</font>):", unsafe_allow_html=True)
        
        # 获取目的地经纬度
        dest_lat = df_K_closest.loc[df_K_closest['name']==dest_name].iat[0,3]
        dest_lon = df_K_closest.loc[df_K_closest['name']==dest_name].iat[0,4]

        # 找到附近的停车场
        closest_carpark = closest_parking_lot[dest_name]

        # 展示附近停车场信息
        carpark_info = []
        for i in closest_carpark:
            distance = distance_from_dest(dest_lat, dest_lon, coordinates[i][0], coordinates[i][1])
            # new_row = [i,coordinates[i][0],coordinates[i][1],check_availability([i])[0],distance]
            # new_row = [i,[coordinates[i][0],coordinates[i][1]],coordinates[i][2],check_availability([i])[0],distance]
            new_row = [i, [coordinates[i][0], coordinates[i][1]], coordinates[i][2], check_availability(i, available_parking_lots), distance] # input of check_availability has been redesigned
            carpark_info.append(new_row)
        df_carpark = pd.DataFrame(carpark_info)
        # df_carpark.columns = ["carpark_number", "lat", "lon", "number_of_available_lots", "distance_from_dest"]
        df_carpark.columns = ["name", "loc", "address", "number_of_available_lots", "distance_from_dest (km)"]

        st.write(df_carpark.drop('loc', axis=1))
        # st.write(df_K_mercat)

        # Obtain list of mercator coordinates
        carpark_mercators = [x_coord(x, y) for x, y in df_carpark['loc']]
        # Create mercator column in our df_K_closest
        df_carpark['mercator'] = carpark_mercators
        # Split that column out into two separate columns - mercator_x and mercator_y
        df_carpark[['mercator_x', 'mercator_y']] = df_carpark['mercator'].apply(pd.Series)

        # 绘制选定destination—— 用, 蓝色正三角
        df_choose_places = ColumnDataSource(data=df_K_mercat.loc[df_K_mercat['name']==dest_name])
        p.triangle(x='mercator_x', y='mercator_y',
                    source=df_choose_places, size=20, fill_alpha=1)

        # 选定destination 附近停车场地点, 画图 —— 绿色点
        df_closest_carpark = ColumnDataSource(data=df_carpark)
        p.circle(x='mercator_x', y='mercator_y',
                source=df_closest_carpark, size=15, fill_alpha=.7, color="green")


    st.write(p)



