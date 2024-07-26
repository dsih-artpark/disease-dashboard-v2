echo
echo "GENERATING COMPRESSED MAPS..."
mkdir -p source_files/geojsons/compressed_individual/
rm source_files/geojsons/compressed_individual/*

for filepath in $(find source_files/geojsons/individual -name '*.geojson'); do
  filesize="$(wc -c $filepath | cut -d' ' -f1)"
  echo $filepath
  echo $filesize
  targetfilepath="${filepath/\/individual\//\/compressed_individual\/}"
  if [[ $filesize -gt 200000 ]]
    then
      mapshaper -i $filepath -simplify 5% -o $targetfilepath format=geojson
    else
      echo "copying"
      cp $filepath $targetfilepath
  fi

done
