#!/bin/bash

cd /home/ian/data_collection/CubeData/unprocessed

read -r -d '' IDL_SCRIPT <<EOF
  ans = make_polar_image("$1", "$2", "$3", align=true)
  ; print, ans ;?
EOF

# Print the script out for debugging
echo "${IDL_SCRIPT}"
cd /home/ian/data_collection/cisscal
gdl <<< "${IDL_SCRIPT}"
