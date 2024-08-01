import os
import csv
from pysis import pixelinfo, isis
from pysis.exceptions import ProcessError
from tqdm import tqdm
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.cm as cm
import matplotlib
import numpy as np
import pandas as pd
import multiprocessing

# Emission = Viewing Zenith
# Incidence = Solar Zenith
# Phase = Scattering Angle
# Group data by pass

def cmap_map(function, cmap):
    """ Applies function (which should operate on vectors of shape 3: [r, g, b]), on colormap cmap.
    This routine will break any discontinuous points in a colormap.
    """
    cdict = cmap._segmentdata
    step_dict = {}
    # Firt get the list of points where the segments start or end
    for key in ('red', 'green', 'blue'):
        step_dict[key] = list(map(lambda x: x[0], cdict[key]))
    step_list = sum(step_dict.values(), [])
    step_list = np.array(list(set(step_list)))
    # Then compute the LUT, and apply the function to the LUT
    reduced_cmap = lambda step : np.array(cmap(step)[0:3])
    old_LUT = np.array(list(map(reduced_cmap, step_list)))
    new_LUT = np.array(list(map(function, old_LUT)))
    # Now try to make a minimal segment definition of the new LUT
    cdict = {}
    for i, key in enumerate(['red','green','blue']):
        this_cdict = {}
        for j, step in enumerate(step_list):
            if step in step_dict[key]:
                this_cdict[step] = new_LUT[j, i]
            elif new_LUT[j,i] != old_LUT[j, i]:
                this_cdict[step] = new_LUT[j, i]
        colorvector = list(map(lambda x: x + (x[1], ), this_cdict.items()))
        colorvector.sort()
        cdict[key] = colorvector

    return matplotlib.colors.LinearSegmentedColormap('colormap',cdict,1024)

def get_key_from_pixel(observation_name: str, lat: int, lon: int):
    pvlres = pixelinfo.point_info(observation_name, lon, lat, point_type="ground")
    return pvlres['GroundPoint']


def trim_by_phase(max_incidence: int=70):
    """
    Trims pixels from all cubes in the directory processed that have an incidence greater than the given angle

    """

    for i in tqdm(os.listdir("processed/")):
        if i.endswith(".cub"):
            try:
                isis.photrim(from_="processed/"+i, to="trimmed/"+i, MAXINCIDENCE=max_incidence)
            except ProcessError as e:
                print(f"Error with trimming by incidence angle: {e.stderr}")

def get_filter_info(observation_name: str, get_raw : bool=False):
    """
    Translates cube observation_name's FilterName keyword into wavelengths and polarization angles.

    Args:
        observation_name: String
    """

    try:
        filter_key = isis.getkey(from_=observation_name, keyword="FilterName", grpname="BandBin")
        filter_key = filter_key.decode('utf-8').strip().split('/')

        if get_raw:
            return filter_key[0], filter_key[1]

        polarization_angles_nac = {
                "P0": 0,
                "P60": 60,
                "P120": 120,
                "IRP0": "IR 0"
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

def convert_one_sample(sample: str):
    """
    Converts a single cube file's resolution. Meant to be used with convert_pixel_resolution()

    Args:
        Sample: String
    """
    if sample.endswith(".cub"):
        new_name = sample[:12]
        new_name = new_name + "_RC.cub"

        try:
            isis.map2map(from_=f"processed/{sample}", to=f"processed/{new_name}", map="reconfigure.map", pixres="map")
            os.system(f"rm processed/{sample}")
        except ProcessError as e:
            print(f"Error recalculating pixel resolution for sample {sample}: {e.stderr}")

def convert_pixel_resolution():
    """
    Uses a multiprocessing pool to convert the resolution of all cubes in the directory processed/

    Note that the resolution needs to be defined in the map file "reconfigure.map"
    """
    cub_names = [i for i in os.listdir("processed/")]

    with multiprocessing.Pool() as p:
        p.map(convert_one_sample, cub_names)

def get_pixel_data_through_dataset(key: str, lat: int, lon: int):
    """
    Returns the user-defined key, focused on a single pixel throughout all cubes in directory processed/. 

    For any cube that has both the user-defined pixel and key, writes the cube name, time, pixel intensity, user-defined key, polarization angle, and wavelength to a .csv file with the same name as the user-defined key.

    Args:
        key: String
        lat: int
        lon: int
    """

    with open(f"{key}.csv", 'w+') as csvfile: # initialize csvfile
        csv.writer(csvfile).writerow(['Observation', 'Time', 'Intensity', key,  "Polarization Angle", "Wavelength"])

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
                    writer.writerow([name, time, pixel_intensity, pixel_key, pangle, pwavelength])

def dataset_to_csv(name: str="CassiniData"):
    """
    Loops through all cubes in directory processed and saves their names, the date observed, and their polarization angles and wavelengths to the csv file name

    Args:
        name: String

    """
    with open(f"{name}.csv", "w+") as csvfile:
        csv.writer(csvfile).writerow(['Observation', 'Time', 'Polarization Angle', 'Wavelength'])

    for i in tqdm(os.listdir("processed")):
        cube_name = "processed/" + i
        if i.endswith(".cub"):
            pangle, pwavelength = get_filter_info(cube_name)
            time = isis.getkey(from_=cube_name, grpname="Instrument", keyword="StartTime")
            time = time.decode("utf-8")
            
            with open(f"{name}.csv", "a+") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([cube_name, time, pangle, pwavelength])

def organize_cubes_by_flybys(name: str="CassiniData"):
    """
    Loops through a given csv file and organizes cubes by date of observation

    Args:
        name: Name of the csv file (excluding .csv)
    """

    df = pd.read_csv(name + ".csv")
    df = df.sort_values('Time', ascending=True)
    df = df.replace(r'\r\n',' ', regex=True)


    if not os.path.exists("Flybys"):
        os.system("mkdir Flybys")

    unique_dates = df["Time"].map(lambda t: t[:8]).unique().tolist()
    df["Time"] = df["Time"].map(lambda t: t[:8])
    df["Observation"] = df["Observation"].map(lambda x : x[10:])

    for i in unique_dates:
        df1 = df[df['Time'] == i]
        df1 = df1["Observation"]
        df1.to_csv(f"Flybys/{i}", index=False)

    
def draw_scatter_plot(key: str, flyby_only: bool=False, n: int=15, wavelengths=[]):
    """

    Uses a .csv file generated by get_pixel_data_through_dataset() to draw a scatter plot.

    Args:
        key: String (the user-defined csv file / key)
        flyby_only: bool (if True, flybys will be identified based on the time specific observations were taken (two observations are considered part of the same flyby if they were taken on the same day) and scatter plots will be generated for each flyby that has observations greater than n)
        wavelengths: list (if this list is not empty, scatter plots will only include the specified wavelengths. See NAC and WAC wavelengths for specific examples)

    """
    data = []
    intensity = []
    all_days = []
    long_flybys = []

    if flyby_only and not wavelengths:
        with open(f"{key}.csv") as csvfile:
            reader = csv.reader(csvfile)
            reader = sorted(reader, key=lambda row: row[0], reverse=True) # sort by time

            previous_timestamp = None
            cnt = 0
            bad = False

            for row in reader:
                if cnt == 0:
                    cnt += 1
                    continue

                if cnt == 1:
                    previous_timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f%z").strftime("%m/%d/%y")
                    cnt += 1

                    all_days.append([previous_timestamp])
                else:
                    try:
                        timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f%z").strftime("%m/%d/%y")
                    except:
                        timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f").strftime("%m/%d/%y") # for some reason, some dates are like this

                    for i in all_days:
                        if timestamp == i[0]: bad = True

                    if not bad: all_days.append([timestamp])
                    bad = False

                    if timestamp == previous_timestamp:
                        for i in all_days:
                            if i[0] == previous_timestamp:
                                i.append(row)
                    else:
                        previous_timestamp = timestamp

        long_flybys = []

        for x in all_days:
            if len(x) > n:
                long_flybys.append(x)

        del all_days

        cnt = 0

        for i in long_flybys:
            x = []
            y = []

            targets = []

            for j in i[1:]:
                targets.append(int(j[4]))
                x.append(float(j[2]))
                y.append(float(j[1]))


            fig, ax = plt.subplots()

            dark_spectral = cmap_map(lambda x : x * 0.9, matplotlib.cm.Spectral_r)
            
            scatter = ax.scatter(x, y, c=targets, cmap=dark_spectral)
            legend = ax.legend(*scatter.legend_elements(), loc="upper left", title="Legend")
            ax.add_artist(legend)

            try:
                plt.xlabel(f"{key} ({key_dict[key]})")
            except:
                plt.xlabel(f"{key}")

            plt.title(f"Flyby on {i[0]}: {len(i)} Observations, Intensity vs {key}")
            
            plt.ylabel("Intensity (Irradiance / Flux)")

            plt.savefig(f"Data/Flyby/{key}")
            cnt += 1

    if wavelengths and not flyby_only: # if we want to constrain data to certain wavelength ranges
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

    if not wavelengths and not flyby_only: # meaning to get data across all wavelengths and flybys
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

        dark_spectral = cmap_map(lambda x : x * 0.9, matplotlib.cm.Spectral_r)

        for i in data:
            intensities = []
            keys = []
            colors = []

            for j in i[1:]:
                keys.append(float(j[2]))
                intensities.append(float(j[1]))
                colors.append(float(j[4]))

            plt.plot()
            plt.legend(wavelength_list)
            plt.scatter(keys, intensities, cmap=dark_spectral)

            try:
                plt.xlabel(f"{key} ({key_dict[key]})")
            except:
                plt.xlabel(f"{key}")

            plt.ylabel("Intensity (Irradiance / Flux)")
            plt.title(f"Intensity vs. {key}")
            
        plt.savefig(f"Data/Angle-Specific/{key}")
        

if __name__ == "__main__":
    key_dict = {
            "Phase": "Scattering Angle (degrees)",
            "Incidence": "Solar Zenith (degrees)",
            "Emission": "Viewing Zenith (degrees)"
    }

    """

    get_pixel_data_through_dataset("SpacecraftAzimuth", 60,20)
    trim_by_phase(70)
    for i in ["SpacecraftAzimuth", "Emission", "Incidence", "Phase", "SubSolarAzimuth"]:
        draw_scatter_plot(i, True)
        draw_scatter_plot(i)

    """

    trim_by_phase(70)

