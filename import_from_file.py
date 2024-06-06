import csv
from datetime import datetime
import traceback

from models import CaseEntry, Region, SourceFile

def _read_csv(filepath):
    rows = []
    with open(filepath) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows

def case_data(filename):
    print("IMPORTING CSV CASE DATA:", filename)
    source_exists = SourceFile.objects(name=filename).first()
    if source_exists:
        print("FILE ALREADY IMPORTED, SKIPPING")
        return

    rows = _read_csv(filename)
    errors = []
    line_number = 1
    for row in rows:
        line_number += 1
        try:
            entry = CaseEntry()

            entry.record_id = row["metadata.recordID"]
            date_str = row["metadata.recordDate"].split("T")[0]
            entry.record_date = datetime(*list(map(int, date_str.split("-"))))

            entry.source = row["metadata.source"]
            assert entry.source
            entry.source_filename = filename

            entry.hierarchy = row["location.admin.hierarchy"]
            assert entry.hierarchy

            entry.regions = []
            entry.regions.append(row.get("location.admin1.ID", "admin_0"))
            entry.regions.append(row.get("location.admin2.ID", "admin_0"))
            entry.regions.append(row.get("location.admin3.ID", "admin_0"))
            entry.regions.append(row.get("location.admin4.ID", "admin_0"))
            entry.regions.append(row.get("location.admin5.ID", "admin_0"))

            entry.suspected = int((row["cases.suspected"] or "0").split(".")[0])
            entry.tested = int((row["cases.tested"] or "0").split(".")[0])
            entry.confirmed = int((row["cases.confirmed"] or "0").split(".")[0])
            entry.deaths = int((row["cases.deaths"] or "0").split(".")[0])

            entry.age_range = row["demographics.ageRange"]
            entry.gender = row["demographics.gender"]
            entry.test_type = row["test.type"]

            entry.save()
        except Exception as e:
            error = traceback.format_exc()
            errors.append({"line_number": line_number, "error": error, "row": row})
    return errors

def regions(filename):
    rows = _read_csv(filename)
    row_index = {}
    for row in rows:
        row_index[row["regionID"]] = row

    for region_id in row_index:
        row = row_index[region_id]

        region = Region()
        region.region_id = region_id
        region.region_type = region_id.split("_")[0]
        region.name = row["regionName"]
        region.parent_ids = []
        region.parent_names = []

        parent_row = row_index.get(row["parentID"])
        while parent_row:
            region.parent_ids.append(parent_row["regionID"])
            region.parent_names.append(parent_row["regionName"])

            parent_row = row_index.get(parent_row["parentID"])

        region.save()
