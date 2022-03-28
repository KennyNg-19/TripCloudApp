import streamlit as st
import pandas as pd
# 压制SettingWithCopyWarning的warning
pd.set_option('mode.chained_assignment', None)

import numpy as np

import warnings
warnings.filterwarnings("ignore")

# bokeh==2.2.2
from bokeh.io import output_notebook, show, output_file
from bokeh.plotting import figure, ColumnDataSource
from bokeh.tile_providers import get_provider, Vendors
from bokeh.palettes import PRGn, RdYlGn
from bokeh.transform import linear_cmap,factor_cmap
from bokeh.layouts import row, column
# from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, NumeralTickFormatter

# API to get current lang and lont
import geocoder
my_lan_lon = geocoder.ip('me').latlng

# TODO: function for calculate distance: mgeopy.distance.distance(coord1, corrd2)
import geopy.distance


# import bokeh
# bokeh.__version__

st.title('TripElite')
st.subheader("- A platform for finding entertainment and carpark places.")

# read data
df = pd.read_csv("sg-places-new.csv").dropna()

tp = st.selectbox("Place type", df['type'].unique())

num = st.selectbox("No. of the place(Less than 10)", range(1,11))

# 需要根据位置坐标，排序
st.write(f"Your geolocation is {my_lan_lon}.")
st.write(f"{num} closest {tp} is/are:")

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
df_K_closest.loc[-1] = ['My loc', 'My loc', '', my_lan_lon[0], my_lan_lon[1], 0.0]


# ------------------画图-----------------------
# 为了Bokeh的画图： Define function to switch from lat/long to mercator coordinates
def x_coord(x, y):
    lat = x
    lon = y
    
    r_major = 6378137.000
    x = r_major * np.radians(lon)
    scale = x/lon
    y = 180.0/np.pi * np.log(np.tan(np.pi/4.0 + 
        lat * (np.pi/180.0)/2.0)) * scale
    return (x, y)

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

# Tell Bokeh to use df as the source of the data
df_places = ColumnDataSource(data=df_K_mercat.iloc[:-1])
df_myloc = ColumnDataSource(data=df_K_mercat.iloc[-1:])

# Set tooltips - these appear when we hover over a data point in our map, very nifty and very useful
tooltips = [("Place","@name"), ("Addr", "@address")]

# Create figure
p = figure(title = 'Places@Singapore', x_axis_type="mercator", y_axis_type="mercator",
           x_axis_label = 'Longitude', y_axis_label = 'Latitude', tooltips = tooltips,
           plot_width=900, plot_height=800)

# Add map tile
p.add_tile(chosentile)

# Add place points using mercator coordinates
p.circle(x = 'mercator_x', y = 'mercator_y',
         source=df_places, size=15, fill_alpha = .7)
# and the point for my location
p.triangle(x = 'mercator_x', y = 'mercator_y',
         source=df_myloc, size=25, fill_alpha = 1, color='red')

# Show map
# st.bokeh_chart(p)
st.write(p)
# ----------------------------end of graph--------------------------------------

# 获取用户选择的目的地
df_K_closest = df_K_closest.iloc[:-1] # 已经显示完了，可以移除my_location这一行
dest_name = st.selectbox("Choose one as the destination you'd like:",
                           pd.Series(" ").append(df_K_closest.name))
dest_info = df_K_closest.loc[df_K_closest['name']==dest_name]
st.write(f"You choose {dest_name} as destination!")
dest_info
# TODO:  通过dest_info这个经纬度，可以进一步获取停车场信息了...


