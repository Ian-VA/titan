#!/bin/bash

read -r -d '' IDL_SCRIPT <<EOF
  ans = make_polar_image("$1", "$2", "$3")
  ; print, ans ;?
EOF

# Print the script out for debugging
echo "${IDL_SCRIPT}"
cd ~/cisscal
gdl <<< "${IDL_SCRIPT}"
