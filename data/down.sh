#!/bin/bash
while IFS= read -r name; do
    aria2c -x 16 -s 16 "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/${name}/${name}_final_adj_5mpp_slp.tif" &
done < files.txt
wait
