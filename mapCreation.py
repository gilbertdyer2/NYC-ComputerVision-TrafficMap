import folium
from folium.plugins import MarkerCluster
from folium import IFrame

import pandas as pd
import os
import sys
import base64


# For running as executable with PyInstaller
# ----- FILE SETTINGS ----- #
def get_base_filepath():
    if getattr(sys, 'frozen', False):
        print("Detected ran from PyInstaller")
        return sys._MEIPASS
    else:
        print("Detected ran from local")
        return ''
    

# ----- DEFINITIONS ---- #
BASE_FILEPATH = get_base_filepath()
MAP_FILEPATH = os.path.join(BASE_FILEPATH, 'trafficMap.html')

# LOCATIONS
NEW_YORK = (40.730610, -73.935242)
BOROUGHS = ['Manhattan', 'Brooklyn', 'Staten Island', 'Queens', 'Bronx']

# COLOR THRESHOLDS
GREEN_THRESH = 1
YELLOW_THRESH = 7
RED_THRESH = 14
BLACK_THRESH = 25


# Gets the image of a respective camera
def get_popup(sorted_df, index : int, local_HTML : bool = False):
    
    if (local_HTML):
        # Get image from local folder (larger HTML file)
        image_path = os.path.join(BASE_FILEPATH, f"BoundedImages/img{sorted_df.iloc[index].at['id']}.jpg")
        encoded = base64.b64encode(open(image_path, 'rb').read())

        image_url = f"data:image/png;base64,{encoded.decode('UTF-8')}";
    else:
        # Get image from AWS S3 bucket
        image_url = f"https://trafficimagetest.s3.us-east-2.amazonaws.com/images/img{sorted_df.iloc[index].at['id']}.jpg"
        
    camera_name = sorted_df.iloc[index].at['name']
    car_count = int(sorted_df.iloc[index].at['car_count'])


    # Create html window to display image and text
    html = f"""
    <div style="text-align: center;">
        <img src="{image_url}" style="max-width: 100%;">
        <h1 style = "font-size: 17;">{f"{camera_name}"}</h1>
        <p style = "font-size: 15;">{f"Cars Found: {car_count}"}</p>
    </div>
    """
    # Construct the html with IFrame
    # - For w/h reference, images captured are usually (400x352)
    iframe = IFrame(html, width=400, height=330)
    popup = folium.Popup(iframe, max_width=400)

    return popup


# Gets the icon of a camera, assigns it a color based on car count
def get_icon(car_count : int):
    # Get color of icon, red > yellow > green for car density
    return folium.Icon(get_color(car_count))


# Returns a transparent circle to be placed around a camera location
# - The returned color indicates the amount of traffic 
def get_circle(sorted_df, index : int):
    car_count = sorted_df.iloc[index].at['car_count']

    color = get_color(car_count)
    fill_opacity = 0.0
    opacity = 0.0
    if (color == 'black'):
        fill_opacity = 0.4
        opacity = 0.4
    elif (color == 'darkred'):
        fill_opacity = 0.3
        opacity = 0.3
    elif (color == 'orange'):
        fill_opacity = 0.2
        opacity = 0.2
    elif (color == 'green'):
        fill_opacity = 0.1
        opacity = 0.1

    circle_marker = folium.Circle(
        location=[sorted_df.iloc[index].at['latitude'], sorted_df.iloc[index].at['longitude']],
        radius=600,
        color=color,
        weight=0,
        fill_opacity=fill_opacity,
        opacity=opacity,
        fill_color=color,
        fill=False,  # Overridden by fill_color
        popup=get_popup(sorted_df, index),
    )
    return circle_marker
    

# Returns an assigned color according to the car count 
#   In order from least -> most traffic: Green < Yellow/Orange < Red < Black
def get_color(car_count : int):
    # **Color thresholds are defined in header**
    if (car_count > BLACK_THRESH):
        return 'black'
    elif (car_count > RED_THRESH):
        return 'darkred'
    elif (car_count > YELLOW_THRESH):
        return 'orange'
    elif (car_count > GREEN_THRESH):
        return 'green'
    
    return 'white'


def update_map_html():
    print("Building map...")

    map = folium.Map(location=NEW_YORK, zoom_start=12, tiles="Cartodb Positron")

    # Define circle heatmaps and camera icons as feature groups that can be enabled/disabled
    circle_markers = folium.FeatureGroup(name="Heatmap").add_to(map)
    camera_markers = folium.FeatureGroup(name="Camera Icons").add_to(map)

    # Enable for toggleable boroughs 
    # Define regions as clusters of markers; 
    # area_manhattan = MarkerCluster(name="Cameras - Manhattan").add_to(map)
    # area_brooklyn = MarkerCluster(name="Cameras - Brooklyn").add_to(map)
    # area_staten_island = MarkerCluster(name="Cameras - Staten Island").add_to(map)
    # area_queens = MarkerCluster(name="Cameras - Queens").add_to(map)
    # area_bronx = MarkerCluster(name="Cameras - Bronx").add_to(map)
    # 
    # BOROUGHS = {"Manhattan" : area_manhattan, "Brooklyn" : area_brooklyn,
    #         "Staten Island" : area_staten_island, "Queens" : area_queens,
    #         "Bronx" : area_bronx}

    
    # Get the dataframe and sort it
    #   Sorting cameras by ascending car count means markers with the highest car counts
    #   will be on the top layers
    #   e.g. Clicking on overlapping circle regions will bring up the highest car count 
    df = pd.read_csv(os.path.join(BASE_FILEPATH, 'out.csv'))
    df['car_count'] = pd.to_numeric(df['car_count'], errors='coerce')
    sorted_df = df.sort_values(by='car_count', ascending=True)
    
    for i in range(len(df.axes[0])):
        car_count = sorted_df.iloc[i].at['car_count']

        # Check if image was successfully analyzed (bounded image was made)
        image_path = os.path.join(BASE_FILEPATH, f"BoundedImages/img{sorted_df.iloc[i].at['id']}.jpg")
        if not os.path.exists(image_path):
            print(f"could not find image ({sorted_df.iloc[i].at['id']})")
            continue
        
        # Get the camera image displayed on click
        popup = get_popup(sorted_df, i)
        # Get the color of the icon (changes based on car count at camera location)
        icon = folium.Icon(get_color(car_count))

        # Create circular camera marker with constant size on the map
        camera_marker = folium.Circle(
            location=[sorted_df.iloc[i].at['latitude'], sorted_df.iloc[i].at['longitude']],
            radius=25,
            color='black',
            weight=2,
            fill_opacity=1,
            opacity=1,
            fill_color=get_color(car_count),
            fill=False,  # Overridden by fill_color
            popup=popup,
        )
        circle_marker = get_circle(sorted_df, i)
        
        # Add created markers 
        camera_markers.add_child(camera_marker)
        circle_markers.add_child(circle_marker)

        # Enable to use with Borough marker cluster regions
        # Adds the markers to its respective borough group, defined by the BOROUGHS dictionary
        # BOROUGHS[sorted_df.iloc[i].at['area']].add_child(camera_marker)
        # BOROUGHS[sorted_df.iloc[i].at['area']].add_child(circle_marker)
        
        
    # Add OpenStreetMap as secondary map option
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(map)

    # Add layer toggling interface to the map
    folium.LayerControl().add_to(map)

    # Save map as a local HTML file
    map.save(MAP_FILEPATH)
    
    print("Finished building map")

def show_map(update_map : bool):
    # Create a local html file of the map
    if (update_map):
        update_map_html()


# ----- MAIN ----- #
if __name__ == "__main__":
    show_map(update_map=True)