echo
echo "GENERATING COMPRESSED MAPS..."
mkdir -p source_files/geojsons/compressed_individual/
rm source_files/geojsons/compressed_individual/*

for filepath in $(find source_files/geojsons/individual -name '*.geojson'); do
  targetfilepath="${filepath/\/individual\//\/compressed_individual\/}"
  mapshaper -i $filepath -simplify 1% -o $targetfilepath format=geojson
done
