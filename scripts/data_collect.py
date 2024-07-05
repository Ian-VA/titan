import os
import pysis
import requests

query = {
        "Mission": "Cassini",
        "instrument": "Cassini ISS",
        "polarizationType": "Linear",
        "target": "Titan",
        "limit" : "10000",
        "cols": []
}

endpoint = "https://opus.pds-rings.seti.org/opus/api/data.json"
k = 1

def remove_null(data):
    return [i for i in data if i != ["N/A"]]

def data_collect():


if __name__ == "__main__":
    q1 = query
    q1["cols"] = [metadata]

    response = requests.get(
            endpoint,
            params=query
    )

    data = response.json()
    data["page"] = remove_null(data["page"]) # remove null values
    data = data["page"]
