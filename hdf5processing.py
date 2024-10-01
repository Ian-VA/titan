import h5py
import pandas as pd
import pysis.isis as isis
from pysis.exceptions import ProcessError
import os
import numpy as np
import pvl
from tqdm import tqdm
from cube_operations import get_filter_info
import subprocess
import time
import concurrent.futures

def check_compatible(cube_name):
    """

    Returns a boolean value to check if a cube's polarization angle and wavelength are compatible for calculating Stokes parameters, and, if True, returns its wavelength and polarization angle

    args:
        cube_name: Name of a given cube to check compatibility

    returns:
        boolean: True for compatible, False for incompatible

    """

    compatible_filters = ["P0", "P60", "P120"]
    compatible_filters_ir = ["IRP0", "CLR", "IRP90"]

    compatible_wavelengths_ir = ["MT2", "CB2", "MT3", "CB3"]
    compatible_wavelengths = ["UV3", "BL2", "GRN", "MT1", "CB1", "MT2", "CB2"]

    pangle, pwavelength = get_filter_info(cube_name, True)

    if pwavelength[0] == 'P' or pwavelength[:2] == "IR":
        temp = pwavelength
        pwavelength = pangle
        pangle = temp

    if (pangle in compatible_filters and pwavelength in compatible_wavelengths) or (pangle in compatible_filters_ir and pwavelength in compatible_wavelengths_ir):
        return True, pwavelength, pangle
    else:
        return False, pwavelength, pangle


def process_calculated_values(is_nac, is_wac, data_names):
    """
    
    Calibrates and projects calculated values, like degree of linear polarization

    """

    label_to_use = data_names[1]
    label_to_use = label_to_use[:-3]
    label_to_use += "LBL"

    process_names = []

    if is_nac:
        process_names = ["intensity", "polarization", "theta"]
    if is_wac:
        process_names = ["q", "intensity"]

    os.system(f"ciss2isis from={label_to_use} to=interim.cub")

    with open("interim.cub", "r", encoding='utf-8') as f:
        labels = f.read(2340) # number of bytes for all the labels

    with open("labels.txt", "w+") as f:
        f.write(labels)

    cisscal_dir = os.path.expanduser('~/data_collection/cisscal')

    for i in process_names:
        os.system(f"vicar2isis from={cisscal_dir}/{i}.vicar to={cisscal_dir}/{i}.cub")

        with open(f'{cisscal_dir}/{i}.cub', 'rb') as f:
            f.seek(250)
            data = f.read().splitlines(True)

        with open(f"{cisscal_dir}/{i}.cub", 'wb+') as f:
            f.write(labels.encode())
            for i in data[32:]:
                f.write(i)


def return_calculated_values(cube_list):
    filters_dict = {}
    wavelength_dict = {}

    if len(cube_list) < 2:
        raise Exception("Given flyby too small to supply Stokes parameters")

    for i in cube_list:
        i = i.strip('\n')
        file_name = f"CubeData/trimmed/{i}"

        is_compatible, pwavelength, pangle = check_compatible(file_name)

        if is_compatible: # if the cube has compatible filter & wavelength, add it to a dictionary of 1) known wavelengths (because a matching set needs to have the same wavelength) and 2) a dictionary of known filters for easy checking later
            filters_dict[file_name] = pangle

            if not pwavelength in wavelength_dict:
                wavelength_dict[pwavelength] = []
                wavelength_dict[pwavelength].append(file_name)
            else:
                wavelength_dict[pwavelength].append(file_name)

    polarized_data_names = []

    for i in wavelength_dict:
        if len(wavelength_dict[i]) >= 2:
            pangles = {}

            for j in wavelength_dict[i]:
                pangles[filters_dict[j]] = j  # put a cube with a given filter into the pangles dictionary for that specific filter

            compatible_filters = ["P0", "P60", "P120"]
            compatible_filters_ir = ["IRP0", "CLR", "IRP90"]

            if set(compatible_filters).issubset(pangles.keys()): # if NAC-compatible filter combinations are a subset of pangles, that means we have a matching set
                p0, p1, p2 = os.path.abspath(pangles['P0']), os.path.abspath(pangles['P60']), os.path.abspath(pangles['P120']) # 

                path = p0.split('CubeData/trimmed', 1)[0]
                path = path + "CubeData/unprocessed/"
                p0, p1, p2 = p0.split('CubeData/trimmed/', 1)[1], p1.split('CubeData/trimmed/', 1)[1], p2.split('trimmed/', 1)[1]
                name1, name2, name3 = p0.split('.', 1)[0], p1.split('.', 1)[0], p2.split('.', 1)[0]

                for filename in os.listdir("CubeData/unprocessed/"):
                    if filename.startswith(name1):
                        name1 = filename
                    elif filename.startswith(name2):
                        name2 = filename
                    elif filename.startswith(name3):
                        name3 = filename

                p0, p1, p2 = path + name1, path + name2, path + name3

                subprocess.call(['bash', 'scripts/invoke_gdl_nac.sh', p0, p1, p2])

                polarized_data_names[0], polarized_data_names[1], polarized_data_names[3] = p0, p1, p2

                return True, False, polarized_data_names

            if set(compatible_filters_ir).issubset(set(pangles.keys())):

                try:
                    p0, p90 = os.path.abspath(pangles['IRP0']), os.path.abspath(pangles['IRP90'])
                except:
                    p0, p90 = os.path.abspath(pangles['IRP0']), os.path.abspath(pangles['CLR'])

                path = p0.split('CubeData/trimmed', 1)[0]
                path = path + "CubeData/unprocessed/"
                p0, p90 = p0.split('CubeData/trimmed/', 1)[1], p90.split('CubeData/trimmed/', 1)[1]

                name1, name2 = p0.split('.', 1)[0], p90.split('.', 1)[0]


                p0, p90 = path + name1, path + name2

                subprocess.call(['bash', 'scripts/invoke_gdl_ir.sh', p0, p90])

                polarized_data_names[0], polarized_data_names[1] = p0, p90

                return False, True, polarized_data_names

    return False, False, polarized_data_names

def return_one_geolocation_value(cube):
    file_name = f"CubeData/trimmed/{cube}"

    samples, lines = isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Samples"), isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Lines")

    samples, lines = int(samples.decode("utf-8")), int(lines.decode("utf-8"))
    
    geolocation_dict1 = {
            "latitude": np.zeros((samples, lines)),
            "longitude": np.zeros((samples, lines)),
            "viewer_azimuth": np.zeros((samples, lines)),
            "sub_solar_azimuth": np.zeros((samples, lines)),
            "relative_azimuth": np.zeros((samples, lines)),
            "scattering_angle": np.zeros((samples, lines)),
            "solar_zenith": np.zeros((samples, lines)),
            "viewing_zenith": np.zeros((samples, lines)),
            "irradiance_over_flux": np.zeros((samples, lines))
    }

    for i in range(0, samples):
        for j in range(0, lines):
            try:
                pvlfile = pvl.loads(isis.campt(from_=file_name, coordtype="IMAGE", sample=i, line=j))
                pvlfile = pvlfile["GroundPoint"]
            except ProcessError as e:
                print(f"Error processing campt: {e.stderr}")

                for k in geolocation_dict1.keys():
                    geolocation_dict1[k][i][j] = np.NaN
                continue

            geolocation_dict1["latitude"][i][j] = float(pvlfile["PlanetocentricLatitude"])
            geolocation_dict1["longitude"][i][j] = float(pvlfile["PositiveEast360Longitude"])
            geolocation_dict1["solar_zenith"][i][j] = float(pvlfile["Incidence"])
            geolocation_dict1["viewer_azimuth"][i][j] = float(pvlfile["SpacecraftAzimuth"])

            try:
                geolocation_dict1["irradiance_over_flux"][i][j] = float(pvlfile["PixelValue"])
            except:
                geolocation_dict1["irradiance_over_flux"][i][j] = np.NaN

            geolocation_dict1["scattering_angle"][i][j] = float(pvlfile["Phase"])
            geolocation_dict1["sub_solar_azimuth"][i][j] = float(pvlfile["SubSolarAzimuth"])
            geolocation_dict1["viewing_zenith"][i][j] = float(pvlfile["Emission"])

            geolocation_dict1["relative_azimuth"][i][j] = abs(float(pvlfile["SpacecraftAzimuth"]) - 180.0 - float(pvlfile["SubSolarAzimuth"]))

def return_geolocation_values(cube_list):

    with concurrent.futures.ProcessPoolExecutor(max_workers=None) as executor:
        all_geolocation_data = [executor.submit(return_one_geolocation_value, cube_name) for cube_name in cube_list]
        concurrent.futures.wait(all_geolocation_data)

    outputs = [future.result() for future in all_geolocation_data]

    return outputs

def return_spectral_values(cube_list):
    """

    Returns the wavelengths and polarization angles of a list of cubes

    """
    polarization_angles, wavelengths = [], []

    for i in cube_list:
        file_name = f"CubeData/trimmed/{i}"
        samples, lines = isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Samples"), isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Lines")

        polarization_angle, wavelength = get_filter_info(file_name)

        samples, lines = int(samples.decode("utf-8")), int(lines.decode("utf-8"))

        if polarization_angle == "IR 0": polarization_angle = 0

        polarization_angles.append(float(polarization_angle))
        wavelengths.append(float(wavelength))

    return polarization_angles, wavelengths

def convert_flybys_to_hdf5(directory: str = "Data/Flybys/", trimmed: bool = True):
    """
    Converts all flybys into HDF5 files
    """

    flybys = os.listdir(directory)

    for i in flybys:
        with h5py.File(f"Data/HDF5Data/Flyby-{i}.hdf5", 'a') as file:
            cube_list = []

            with open(f"{directory}/{i}") as f:
                cube_list = list(f)   
                cube_list.pop(0)

            for j in cube_list:
                file.create_group(j)
                file.create_group(f"{j}/geolocation_values")

            for j in ["calculated_values", "spectral_values"]:
                file.create_group(f"{j}")

            """
            geolocation = return_geolocation_values(cube_list)

            for index, j in enumerate(geolocation):
                file.create_dataset(f"{cube_list[index]}/geolocation_values/{j}", data=j, dtype='f')

            """

            polarization_angles, wavelengths = return_spectral_values(cube_list)
            file.create_dataset(f"spectral_values/polarization_angles", data=polarization_angles, dtype='f')
            file.create_dataset(f"spectral_values/wavelengths", data=wavelengths, dtype='f')

            try:
                is_nac, is_wac, names = return_calculated_values(cube_list)
                process_calculated_values(names, is_nac, is_wac)

                if is_nac:
                    intensity = pd.read_csv("cisscal/intensity.csv").to_numpy()
                    theta = pd.read_csv("cisscal/theta.csv").to_numpy()
                    polarization = pd.read_csv("cisscal/polarization.csv").to_numpy()

                    file.create_dataset(f"calculated_values/intensity", data=intensity, dtype='f')
                    file.create_dataset(f"calculated_values/dolp", data=polarization, dtype='f')
                    file.create_dataset(f"calculated_values/theta", data=theta, dtype='f')
                if is_wac:
                    intensity = pd.read_csv("cisscal/intensity_ir.csv").to_numpy()                           
                    q = pd.read_csv("cisscal/q.csv").to_numpy()

                    file.create_dataset(f"calculated_values/intensity_ir", data=intensity, dtype='f')
                    file.create_dataset(f"calculated_values/q", data=q, dtype='f')
            except:
                continue

if __name__ == "__main__":
    #convert_flybys_to_hdf5()

    process_calculated_values(True, False, ["/home/ian/data_collection/CubeData/unprocessed/N1481591826_4.IMG", "/home/ian/data_collection/CubeData/unprocessed/N1481591931_4.IMG", "/home/ian/data_collection/CubeData/unprocessed/N1481592068_4.IMG"])
