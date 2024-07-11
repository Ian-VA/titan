import os
import csv
from pysis import pixelinfo, isis
from pysis.exceptions import ProcessError
from tqdm import tqdm
import matplotlib.pyplot as plt
from datetime import datetime

# Emission = Viewing Zenith
# Incidence = Solar Zenith
# Phase = Scattering Angle
# Group data by pass

def get_key_from_pixel(observation_name, lat, lon, key=None):
    pvlres = pixelinfo.point_info(observation_name, lon, lat, point_type="ground")
    return pvlres['GroundPoint']

def get_filter_info(observation_name):
    try:
        filter_key = isis.getkey(from_=observation_name, keyword="FilterName", grpname="BandBin")
        filter_key = filter_key.decode('utf-8').strip().split('/')

        polarization_angles_nac = {
                "P0": 0,
                "P60": 60,
                "P120": 120,
                "IRP0": "IR"
        }

        polarization_angles_wac = {
                "IRP0": 0,
                "IRP90": 90
        }

        wavelengths_nac = {
                "UV1": 264,
                "UV2": 306,
                "UV3": 343,
                "BL2": 441,
                "BL1": 455,
                "GRN": 569,
                "MT1": 619,
                "CB1": 619,
                "CB1a": 635,
                "CB1b": 603,
                "RED": 649,
                "HAL": 656,
                "MT2": 727,
                "CB2": 750,
                "IR1": 750,
                "IR2": 861,
                "MT3": 889,
                "CB3": 938,
                "IR3": 928,
                "IR4": 1001,
                "CL1": 651,
                "CL2": 51,
                "UV2-UV3": 318,
                "RED-GRN": 601,
                "RED-IR1": 702,
                "IR2-IR1": 827,
                "IR2-IR3": 902,
                "IR4-IR3": 996
        }

        wavelengths_wac = {
                "VIO": 420,
                "BL1": 463,
                "GRN": 568,
                "RED": 647,
                "HAL": 656,
                "MT2": 728,
                "CB2": 752,
                "IR1": 740,
                "IR2": 852,
                "MT3": 890,
                "CB3": 939,
                "IR3": 917,
                "IR4": 1000,
                "IR5": 1027,
                "CL1": 634,
                "CL2": 634,
                "IR1-IR2": 826
        }
        
        try:

            return polarization_angles_nac[filter_key[0]], wavelengths_nac[filter_key[1]]
        except:
            try:
                return polarization_angles_wac[filter_key[0]], wavelengths_wac[filter_key[1]]
            except:
                return polarization_angles_wac[filter_key[1]], wavelengths_wac[filter_key[0]]

    except ProcessError as e:
        print(f"Error obtaining filter name from {observation_name}: {e.stderr}")


def get_pixel_data_through_dataset(key, lat, lon):
    """
    Returns all available keys throughout an entire dataset of a single pixel
    """

    with open(f"{key}.csv", 'w+') as csvfile: # initialize csvfile
        csv.writer(csvfile).writerow(['Time', 'Intensity', key,  "Polarization Angle", "Wavelength"])

    for i in tqdm(os.listdir("processed")):
        name = "processed/" + i

        if i.endswith(".cub"):
            pvlfile = get_key_from_pixel(name, lat, lon)
            get_filter_info(name)

            if pvlfile['PixelValue'] != None:

                pixel_intensity = float(pvlfile['PixelValue'])
                pixel_key = float(pvlfile[key])
                time = pvlfile["UTC"]
                pangle, pwavelength = get_filter_info(name)

                with open(f"{key}.csv", 'a+') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([time, pixel_intensity, pixel_key, pangle, pwavelength])

def draw_scatter_plot(key, flyby_only=False, wavelengths=[]):
    data = []
    intensity = []

    if flyby_only:
        with open(f"{key}.csv") as csvfile:
            reader = csv.reader(csvfile)
            all_days = []

            previous_timestamp = None
            cnt = 0

            for row in reader:
                if cnt == 0:
                    cnt += 1
                    continue

                if cnt == 1:
                    previous_timestamp = datetime.strptime(row[0], "%d/%m/%Y")
                    cnt += 1
                else:
                    timestamp = datetime.strptime(row[0], "%d/%m/%Y")

                    if timestamp not in all_days:
                        all_days.append([timestamp])

                    if timestamp == previous_timestamp:
                        for i in all_days:
                            if i[0] == previous_timestamp:
                                i[0].append(timestamp)
                    else:
                        previous_timestamp = timestamp
                        


    if wavelengths:
        wavelength_list = [[] for i in range(len(wavelengths))]
        with open(f"{key}.csv") as csvfile:
            reader = csv.reader(csvfile)

            for row in reader:
                if row[4] != "Wavelength" and row[4]:
                    if int(row[4]) in wavelengths:
                        wavelength_list.append(row)
                        print(row)

        for i in wavelength_list:
            data.append(float(i[1]))
            intensity.append(float(i[0]))


    wavelength_list = []
    if not wavelengths:
        with open(f"{key}.csv") as csvfile:
            data = []
            reader = csv.reader(csvfile)

            for row in reader:
                if row[4] != "Wavelength" and row[4]:
                    wavelength = int(row[4])

                    if wavelength not in wavelength_list:
                        wavelength_list.append(wavelength)
                        data.append([wavelength])
                    elif wavelength in wavelength_list:
                        for i in data:
                            if i[0] == wavelength:
                                i.append(row)

        for i in data:
            intensities = []
            keys = []

            for j in i[1:]:
                keys.append(float(j[2]))
                intensities.append(float(j[1]))


            plt.legend(wavelength_list)
            plt.scatter(keys, intensities)
            plt.xlabel(key)
            plt.ylabel("Intensity")
            plt.title(f"Intensity vs. {key}")

                        
    #plt.title(f"{key} vs. Intensity")
    #plt.xlabel(key)
    #plt.ylabel("Intensity")
    #plt.scatter(data, intensity)
    
    plt.show()



get_pixel_data_through_dataset("SubSolarAzimuth", 60,20)
draw_scatter_plot("SubSolarAzimuth")
