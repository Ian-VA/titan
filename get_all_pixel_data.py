import os
import pysis
import csv
from pysis import pixelinfo
import pvl
from tqdm import tqdm

def get_key_from_pixel(observation_name, lat, lon, key=None):
    pvlres = pixelinfo.point_info(observation_name, lon, lat, point_type="ground")
    return pvlres['GroundPoint']

def get_wavelength(observation_name, lat, lon):
    pvlres = get_key_from_pixel(observation_name, lat, lon)
    wavelength = pvlres['Filter']
    print(wavelength)
    

def get_pixel_data_through_dataset(key, lat, lon):
    """
    Returns all available keys throughout an entire dataset of a single pixel
    """

    with open("pixel.csv", 'w+') as csvfile: # initialize csvfile
        csv.writer(csvfile).writerow(['Intensity', key])

    for i in tqdm(os.listdir("processed")):
        name = "processed/" + i

        if i.endswith(".cub"):
            pvlfile = get_key_from_pixel(name, lat, lon)
            get_wavelength(name, lat, lon)

            if pvlfile['PixelValue'] != None:

                pixel_intensity = float(pvlfile['PixelValue'])
                pixel_key = float(pvlfile[key])

                with open("pixel.csv", 'a+') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([pixel_intensity, pixel_key])


get_pixel_data_through_dataset("SpacecraftAzimuth", 60,20)
