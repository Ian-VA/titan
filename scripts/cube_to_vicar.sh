# !/bin/bash

APP_ROOT="$(dirname "$(dirname "$(readlink -fm "$0")")")"

cd "$(dirname "$0")"
cd ..

translate(){
    for entry in "trimmed"/*
    do
        new_name=${entry%.cub}
        new_name=${new_name%._RC}
        new_name=${new_name##*/}

        gdal_translate -strict -if ISIS3 -of VICAR "$APP_ROOT/$entry" "$APP_ROOT/translated/$new_name.vicar"

    done
}

translate
