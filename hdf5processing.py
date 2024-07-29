import h5py
import pysis.isis as isis
from pysis.exceptions import ProcessError
import os
import numpy as np
import pvl
from tqdm import tqdm
from cube_operations import get_filter_info

def return_calculated_values(cube_list):
    values = []

    for i in cube_list:
        file_name = f"trimmed/{i}"

        samples, lines = isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Samples"), isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Lines")

        samples, lines = int(samples.decode("utf-8")), int(lines.decode("utf-8"))
        
        calculated_values_dict1 = {
                "i": np.zeros((samples, lines)),
                "q": np.zeros((samples, lines)),
                "u": np.zeros((samples, lines)),
                "v": np.zeros((samples, lines)), # no circular polarization, so this probably stays this way
                "dolp": np.zeros((samples, lines)),
        }

        values.append(calculated_values_dict1)

        # TODO: figure out a way to calculate stokes parameters from Cassini ISS

    return values
        
def return_geolocation_values(cube_list):

    geolocation_values = []

    for i in cube_list:
        file_name = f"trimmed/{i}"
        samples, lines = isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Samples"), isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Lines")

        samples, lines = int(samples.decode("utf-8")), int(lines.decode("utf-8"))
        
        geolocation_dict1 = {
                "latitude": np.zeros((samples, lines)),
                "longitude": np.zeros((samples, lines)),
                "viewer_azimuth": np.zeros((samples, lines)),
                "sub_solar_azimuth": np.zeros((samples, lines)),
                "scattering_angle": np.zeros((samples, lines)),
                "solar_zenith": np.zeros((samples, lines)),
                "viewing_zenith": np.zeros((samples, lines)),
                "irradiance_over_flux": np.zeros((samples, lines))
        }

        for i in tqdm(range(0, samples)):
            for j in tqdm(range(0, lines)):
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

            geolocation_values.append(geolocation_dict1)

    return geolocation_values


def return_spectral_values(cube_list):

    polarization_angles, wavelengths = [], []

    for i in cube_list:
        file_name = f"trimmed/{i}"
        samples, lines = isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Samples"), isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Lines")

        polarization_angle, wavelength = get_filter_info(file_name)

        samples, lines = int(samples.decode("utf-8")), int(lines.decode("utf-8"))

        if polarization_angle == "IR 0": polarization_angle = 0

        polarization_angle = np.full((samples, lines), float(polarization_angle))
        wavelength = np.full((samples, lines), float(wavelength))

        polarization_angles.append(polarization_angle)
        wavelengths.append(wavelength)

    return polarization_angles, wavelengths

def convert_flybys_to_hdf5(directory: str = "Flybys/", trimmed: bool = True):
    flybys = os.listdir(directory)

    for i in flybys:
        file = h5py.File(f"HDF5Data/Flyby-{i}.hdf5", "w")
        cube_list = []

        with open(f"{directory}/{i}") as f:
            cube_list = list(f)   
            cube_list.pop(0)


        for i in cube_list:
            file.create_group(i)

            for j in ["calculated_values", "geolocation_values", "spectral_values"]:
                file.create_group(f"{i}/{j}")

        geolocation = return_geolocation_values(cube_list)

        for index, i in enumerate(geolocation):
            for j in i.keys():
                file.create_dataset(f"{cube_list[index]}/geolocation_values/{j}", data=i[j], dtype='f')

        polarization_angles, wavelengths = return_spectral_values(cube_list)

        for index, i in enumerate(polarization_angles):
            file.create_dataset(f"{cube_list[index]}/spectral_values/polarization_angle", data=i, dtype='f')

        for index, i in enumerate(wavelengths):
            file.create_dataset(f"{cube_list[index]}/spectral_values/wavelength", data=i, dtype='f')

        calculated_values = return_calculated_values(cube_list)

        for index, i in enumerate():
            for j in i.keys():
                file.create_dataset(f"{cube_list[index]}/calculated_values/{j}", data=i[j], dtype='f')

if __name__ == "__main__":
    convert_flybys_to_hdf5()
