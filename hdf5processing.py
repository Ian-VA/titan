import h5py
import pysis.isis as isis
from pysis.exceptions import ProcessError
import os
import numpy as np
import pvl
from tqdm import tqdm
from cube_operations import get_filter_info
import subprocess

def return_calculated_values(cube_list):
    filters_dict = {}
    wavelength_dict = {}

    if len(cube_list) < 2:
        raise Exception("Given flyby too small to supply Stokes parameters")

    compatible_filters = ["P0", "P60", "P120"]
    compatible_filters_ir = ["IRP0", "CLR", "IRP90"]

    compatible_wavelengths_ir = ["MT2", "CB2", "MT3", "CB3"]
    compatible_wavelengths = ["UV3", "BL2", "GRN", "MT1", "CB1", "MT2", "CB2"]


    for i in cube_list:
        i = i.strip('\n')
        file_name = f"trimmed/{i}"
        pangle, pwavelength = get_filter_info(file_name, True)

        if pwavelength[0] == 'P' or pwavelength[:2] == "IR":
            temp = pwavelength
            pwavelength = pangle
            pangle = temp

        if (pangle in compatible_filters and pwavelength in compatible_wavelengths) or (pangle in compatible_filters_ir and pwavelength in compatible_wavelengths_ir):

            filters_dict[file_name] = pangle

            if not pwavelength in wavelength_dict:
                wavelength_dict[pwavelength] = []
                wavelength_dict[pwavelength].append(file_name)
            else:
                wavelength_dict[pwavelength].append(file_name)

    for i in wavelength_dict:
        if len(wavelength_dict[i]) >= 2:
            pangles = {}

            for j in wavelength_dict[i]:
                pangles[filters_dict[j]] = j 

            if set(compatible_filters).issubset(pangles.keys()):
                print(pangles['P0'])
                print(pangles['P60'])
                p0, p1, p2 = os.path.abspath(pangles['P0']), os.path.abspath(pangles['P60']), os.path.abspath(pangles['P120'])

                path = p0.split('trimmed', 1)[0]
                path = path + "translated/"
                p0, p1, p2 = p0.split('trimmed/', 1)[1], p1.split('trimmed/', 1)[1], p2.split('trimmed/', 1)[1]
                name1, name2, name3 = p0.split('.', 1)[0], p1.split('.', 1)[0], p2.split('.', 1)[0]
                p0, p1, p2 = path + name1 + ".vicar", path + name2 + ".vicar", path + name3 + ".vicar" 

                print(p0)
                subprocess.call(['bash', 'scripts/invoke_gdl_nac.sh', p0, p1, p2])

                return p0, p1

            elif set(compatible_filters_ir).issubset(set(pangles.keys())):

                try:
                    p0, p90 = os.path.abspath(pangles['IRP0']), os.path.abspath(pangles['IRP90'])
                except:
                    p0, p90 = os.path.abspath(pangles['IRP0']), os.path.abspath(pangles['CLR'])

                path = p0.split('trimmed', 1)[0]
                path = path + "translated/"
                p0, p90 = p0.split('trimmed/', 1)[1], p90.split('trimmed/', 1)[1]

                name1, name2 = p0.split('.', 1)[0], p90.split('.', 1)[0]

                p0, p90 = path + name1 + ".vicar", path + name2 + ".vicar" 

                subprocess.call(['bash', 'scripts/invoke_gdl_ir.sh', p0, p90])

                return p0, p90


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
                "relative_azimuth": np.zeros((samples, lines)),
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

                geolocation_dict1["relative_azimuth"][i][j] = abs(float(pvlfile["SpacecraftAzimuth"]) - 180.0 - float(pvlfile["SubSolarAzimuth"]))

            geolocation_values.append(geolocation_dict1)

    return geolocation_values

def return_spectral_values(cube_list):
    """

    Returns the wavelengths and polarization angles of a list of cubes

    """
    polarization_angles, wavelengths = [], []

    for i in cube_list:
        file_name = f"trimmed/{i}"
        samples, lines = isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Samples"), isis.getkey(from_=file_name, objname="Core", grpname="Dimensions", keyword="Lines")

        polarization_angle, wavelength = get_filter_info(file_name)

        samples, lines = int(samples.decode("utf-8")), int(lines.decode("utf-8"))

        if polarization_angle == "IR 0": polarization_angle = 0

        polarization_angles.append(float(polarization_angle))
        wavelengths.append(float(wavelength))

    return polarization_angles, wavelengths

def convert_flybys_to_hdf5(directory: str = "Flybys/", trimmed: bool = True):
    """
    Converts all flybys into HDF5 files
    """
    flybys = os.listdir(directory)

    for i in flybys:
        with h5py.File(f"HDF5Data/Flyby-{i}.hdf5", 'a') as file:
            cube_list = []

            with open(f"{directory}/{i}") as f:
                cube_list = list(f)   
                cube_list.pop(0)


            for j in cube_list:
                file.create_group(j)
                file.create_group(f"{j}/geolocation_values")

            for j in ["calculated_values", "spectral_values"]:
                file.create_group(f"{j}")


            geolocation = return_geolocation_values(cube_list)

            for index, j in enumerate(geolocation):
                for k in j.keys():
                    file.create_dataset(f"{cube_list[index]}/geolocation_values/{k}", data=j[k], dtype='f')

            polarization_angles, wavelengths = return_spectral_values(cube_list)
            file.create_dataset(f"spectral_values/polarization_angles", data=polarization_angles, dtype='f')
            file.create_dataset(f"spectral_values/wavelengths", data=wavelengths, dtype='f')


            """

            try:
                intensity, dolp = return_calculated_values(cube_list)
                file.create_dataset(f"calculated_values/i", data=intensity, dtype='f')
                file.create_dataset(f"calculated_values/dolp", data=dolp, dtype='f')
            except:
                continue
            """

if __name__ == "__main__":
    convert_flybys_to_hdf5()
