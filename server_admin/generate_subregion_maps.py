import json
import os

from models import Region

MAP_FOLDER = "source_files/geojsons/"
os.makedirs(MAP_FOLDER+"subregions/", exist_ok=True)

for region in Region.objects():
    if region.region_type in ["village", "ward"]:
        continue

    subregions = Region.objects(parent_ids__0=region.region_id)
    if not subregions:
        continue

    print("\nProcessing", region.region_id)
    features = []
    for subregion in subregions:
        try:
            with open(f'{MAP_FOLDER}compressed_individual/{subregion.region_id}.geojson') as f:
                data = json.loads(f.read())
            feature = data["features"][0]
            feature["properties"] = {"region_id": subregion.region_id}
            features.append(feature)
        except FileNotFoundError:
            print("DATA NOT AVAILABLE", subregion.region_id)
    if features:
        fc = {"type": "FeatureCollection", "features": features}
        with open(f'{MAP_FOLDER}subregions/{region.region_id}.geojson', "w") as f:
            f.write(json.dumps(fc))
