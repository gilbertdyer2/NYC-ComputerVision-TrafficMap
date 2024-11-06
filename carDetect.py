import cv2
import pandas as pd
import requests
import numpy as np
import sys, os


# For running as executable with PyInstaller
# ----- FILEPATH DEFS ----- # 
def get_base_filepath():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        print("Using base_filepath: ''")
        return ''


# ----- DEFINITIONS ---- #
BASE_FILEPATH = get_base_filepath()


# Runs specified image through opencv and displays cars found with red bounding boxes
def find_cars(df, i : int, confirm_picture : bool):
    # haar_cascade = 'cars.xml'
    haar_cascade = os.path.join(BASE_FILEPATH, 'cars.xml')
    car_cascade = cv2.CascadeClassifier(haar_cascade)

    camera_id = df.loc[i].at['id'] # Camera id is used in saved file 
    image_path = os.path.join(BASE_FILEPATH, f"CapturedImages/img{camera_id}.jpg")
    image = cv2.imread(image_path)
    if image is None:
        return 0


    # Image treatment 
    image = cv2.resize(image, (1000, 600))
    cropped = image[100:600, 0:1000] # Cut off black bar from top of image
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    dilated = cv2.dilate(blur, np.ones((3, 3)))
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    closing = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)


    # Get loc of cars
    cars = car_cascade.detectMultiScale(closing, 1.04, 6, minSize = [20, 20])
    # Track num of cars & draw bounding boxes
    car_count = 0
    for (x,y,w,h) in cars:
        car_count += 1
        cv2.rectangle(cropped,(x,y),(x+w,y+h),(0,0,255),2)
    # print(f'Cars Found: {car_count}')

    # Show the image, and pause until a key is pressed 
    if (confirm_picture):
        cv2.imshow('image', cropped)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # Save the image in 'BoundedImages' dir
    cropped = cv2.resize(cropped, (352, 240))
    cv2.imwrite((os.path.join(BASE_FILEPATH, f"BoundedImages/img{camera_id}.jpg")), cropped)

    return car_count


# saves all images of cameras stored in out.csv
def save_images():
    print("Saving images...")
    df = pd.read_csv(os.path.join(BASE_FILEPATH, 'out.csv'))
    cur_image_num = 0
    
    for i in range(len(df.axes[0])):
        # get image from data
        image_url = df.loc[cur_image_num].at['imageUrl']
        response = requests.get(image_url)
        
        camera_id = df.loc[cur_image_num].at['id']
        # Create/Modify stored image file 
        f = open((os.path.join(BASE_FILEPATH, f'CapturedImages/img{camera_id}.jpg')), 'wb')
        f.write(response.content) 
        f.close()

        if (cur_image_num % 100 == 0):
            print(f"Progress: {i} images...")
        cur_image_num += 1 

    print("Finished saving images...")


# edits the csv file to include a car count parameter
def update_car_count():
    print("Updating car count...")

    df = pd.read_csv(os.path.join(BASE_FILEPATH, 'out.csv'))

    for i in range(len(df.axes[0])):
        # Save image of bounded cars & get # of cars found
        car_count = find_cars(df, i, False)
        # Update car count value of the csv file
        df.loc[i, 'car_count'] = int(car_count)

    df.to_csv(os.path.join(BASE_FILEPATH, 'out.csv'), index=False)

    print("Finished updating car count")


# Returns the csv to the original state of the website provided by the url
def update_csv():
    url = 'https://webcams.nyctmc.org/api/cameras/'
    r = requests.get(url)
    new_df = pd.DataFrame(r.json())
    new_df.to_csv(os.path.join(BASE_FILEPATH, 'out.csv'), index=False, float_format='%.6f')