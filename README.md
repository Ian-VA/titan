# titan-mapp

## What's this?

A processing workflow for polarized Titan data, with the endgoal being to use Cassini Titan data with a modified version of PACE-MAPP

### Tools used?

* USGS ISIS
* GDL: GNU Data Language as a replacement to IDL to run the original cisscal application
* Modified, working version of the pysis ISIS wrapper (not in this repository)
* Python
  
## Processing Workflow?

1. In scripts/data_collect.py: Data is collected from OPUS and automatically downloaded based on user-defined data constraints, converted into ISIS .cub format, initialized with SPICE info, then calibrated w/ cisscal and projected to a map
2. In cube_operations.py:
    1. Cubes are sorted by flybys, where two cubes are considered in the same flyby if taken on the same day
    3. Optionally, all cubes are trimmed such that pixels only with <70 degree phase angle are left in
    4. Metadata is collected from the cubes using USGS ISIS campt
    5. CSV datasets are created, with CassiniData being all processed cubes and other csv files being specific cube metadata
    6. Optionally, this metadata is then graphed
3. In hdf5processing.py: Cubes are converted to usable HDF5 files, with each flyby being one HDF5 file
    1. return_geolocation_values goes through each cube's pixel and runs campt, which returns scattering angle, solar zenith, etc. that is then included in the HDF5 file
    2. return_spectral_values goes through each cube's filter data and makes a list of wavelengths and polarizations present in the flyby
    3. return_calculated_values uses the non-ISIS cisscal function make_polar_image to calculate intensity and degree of linear polarization for the flyby (more info found [here](https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/Cassini/logs/iss_data_user_guide_180916.pdf), page 127). GDL is called automatically with the bash scripts in the script directory

