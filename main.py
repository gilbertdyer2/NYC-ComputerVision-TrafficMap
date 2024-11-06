from carDetect import save_images, update_car_count, update_csv
from mapCreation import update_map_html, show_map

if __name__ == "__main__":
    update_csv()
    save_images()
    update_car_count()
    show_map(update_map=True)

