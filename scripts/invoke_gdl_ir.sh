#!/bin/bash

read -r -d '' IDL_SCRIPT <<EOF
  ans = make_polar_image("$1", "$2", align=TRUE, outfile="out.IMG")
  ; print, ans ;?
EOF

# Print the script out for debugging
echo "${IDL_SCRIPT}"
cd ~/data_collection/cisscal
gdl <<< "${IDL_SCRIPT}"
