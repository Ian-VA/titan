import os
import pysis
import requests
import urllib.request
from pysis import isis
from pysis.util import file_variations
import zipfile
import multiprocessing
from pysis.exceptions import ProcessError
import contextlib

query = {
        "Mission": "Cassini",
        "instrument": "Cassini ISS",
        "polarizationType": "Linear",
        "target": "Titan",
        "surfacegeometrytargetname": "Titan",
        "SURFACEGEOtitan_incidence1": "5",
        "SURFACEGEOtitan_incidence2": "85",
        "SURFACEGEOtitan_emission1": "5",
        "SURFACEGEOtitan_emission2": "85",
        "limit" : "10000",
        "cols": []
}

endpoint = "https://opus.pds-rings.seti.org/opus/api/data.json"
k = 1

def remove_null(data):
    return [i for i in data if i != ["N/A"]]

def scrape_data(data):
    urllib.request.urlretrieve("https://opus.pds-rings.seti.org/opus/api/download/" + data + ".zip", "CubeData/unprocessed/"+data)
    
    name = data[7:].capitalize()

    with zipfile.ZipFile(f"CubeData/unprocessed/{data}", 'r') as zip_ref:
        zip_ref.extractall(f"CubeData/unprocessed/{name}")

    os.system(f"rm -rf CubeData/unprocessed/{data}")
    img_and_label_only(name)


def img_and_label_only(name):
    image, label = "", ""

    for i in os.listdir(f"CubeData/unprocessed/{name}"):
        if i.endswith(".IMG"):
            image = i

        if i.endswith(".LBL"):
            label = i

    print(image)
    print(label)


    os.system(f"mv CubeData/unprocessed/{name}/{image} CubeData/unprocessed/{image}; mv CubeData/unprocessed/{name}/{label} CubeData/unprocessed/{label}")
    os.system(f"rm -rf CubeData/unprocessed/{name}")

def convert_to_cube(name):
    label = ""

    for i in os.listdir(f"CubeData/processed/{name}"):
        if i.endswith(".LBL"):
            label = i
            break

    try:
        isis.ciss2isis(from_=f"CubeData/processed/{name}/{label}", to=f"CubeData/processed/{name}.cub")
    except ProcessError as e:
        print(f"Error encountered with ciss2isis: {e.stderr}")

    os.system(f"rm -rf CubeData/processed/{name}")

def processing(names):
    
    with pysis.IsisPool() as pool:
        for file in names:
            try:
                pool.spiceinit(from_=f"CubeData/processed/{file}")
            except ProcessError as e:
                print(f"Error encountered with sample {file} during spiceinit: {e.stderr}")

    with pysis.IsisPool() as pool:
        for file in names:
            cal_name, map_name = file_variations(file, ['.cal.cub', '.map.cub'])

            try:
                pool.cisscal(from_=f"CubeData/processed/{file}", to=f"CubeData/processed/{cal_name}")
            except ProcessError as e:
                print(f"Error encountered with sample {file} during cisscal: {e.stderr}")

            os.system(f"rm processed/{file}")

    with pysis.IsisPool() as pool:
        for file in names:
            cal_name, map_name = file_variations(file, ['.cal.cub', '.map.cub'])

            try:
                pool.cam2map(from_=f"CubeData/processed/{cal_name}", to=f"CubeData/processed/{map_name}", map='reconfigure.map')
            except ProcessError as e:
                print(f"Error encountered with sample {file} during map projection: {e.stderr}")

            os.system(f"rm CubeData/processed/{cal_name}")


if __name__ == "__main__":
    q1 = query
    q1["cols"] = []

    response = requests.get(
            endpoint,
            params=query
    )

    data = response.json()
    data["page"] = remove_null(data["page"]) # remove null values
    data = data["page"]
    observation_names = []
    labels = []

    if not os.path.exists("CubeData/processed"):
        os.system("mkdir CubeData/processed")

    for i in data:
        observation_names.append(i[0])

    with multiprocessing.Pool() as p:
        p.map(scrape_data, observation_names)

    with multiprocessing.Pool() as p:
        p.map(convert_to_cube, os.listdir("CubeData/unprocessed/"))

    processing(os.listdir("CubeData/unprocessed"))


