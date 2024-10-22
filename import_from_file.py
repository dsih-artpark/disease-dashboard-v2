import csv
from datetime import datetime
import traceback

from models import CaseEntry, Prediction, Region, SourceFile, Serotype

def _read_csv(filepath):
    rows = []
    with open(filepath) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows

def case_data(filename):
    '''
    Expected Fields in CSV File:
    
    - metadata.recordID: Unique ID for the record
    - metadata.recordData: Date of this record used by the dashboard
        for indexing, aggregating and filtering
    - metadata.source: Source of the data

    - location.admin.hierarchy: Type of hierarchy used describing
        locations of this record
    - location.admin1.ID: The region_id of the topmost
        region this case falls under. Usually state_ or country_
    - location.admin2.ID, location.admin3.ID,
        location.admin4.ID, location.admin5.ID:
        Regions this case falls under, in decreasing hierarchical order
    NOTE: The value 'admin_0' represents a null value for these fields.

    - cases.suspected: No. of suspected cases under this record
    - cases.tested: No. of tested cases
    - cases.confirmed: No. of confirmed cases
    - cases.deaths: No. of deaths
    NOTE: In case of summaries, one or more the cases fields can
        have non-zero values. In case of line lists, only one these
        fields can have a value of 1, while all others are zero.

    - demographics.ageRange: A string representing the age
        range the patient falls under
    - demographics.gender: String representing the gender of patient
    - test.type: Test type used for determining the status of infection
    NOTE: The above 3 fields are only relevant for line lists.
    '''
    
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

def predictions(filename):
    '''
    Expected fields in CSV file:

    - regionID: The region for which this prediction is issued
    - startDatePredictedWeek: The date string for the first day
        of the week for which this prediction is issued for
    - dateOfComputingPrediction: Date on which the prediction was issued.
        Existing Predictions for the same week will be superseded by
        predictions that were more recently computed.
    - prediction: The predicted value
    - predictionZone: One of predefined prediction categories
    - thresholdMethod: [Optional] Method used while computing prediction    
    '''
    
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
            obj = Prediction()

            obj.region_id = row["regionID"]
            assert obj.region_id

            region = Region.objects(region_id=obj.region_id).first()
            obj.parent_id = region.parent_ids[0] if region.parent_ids else ""

            obj.date = datetime(*map(int, row["startDatePredictedWeek"].split("-")))
            obj.computation_date = datetime(*map(int, row["dateOfComputingPrediction"].split("-")))

            existing_prediction = Prediction.objects(
                region_id=obj.region_id, date=obj.date,
            ).first()
            if existing_prediction and existing_prediction.computation_date>obj.computation_date:
                continue

            obj.source_filename = filename
            obj.prediction = float(row["prediction"])
            obj.prediction_zone = int(str(row["predictionZone"]).split(".")[0])
            obj.threshold_method = row.get("thresholdMethod", "")
            obj.save()
        except Exception as e:
            error = traceback.format_exc()
            errors.append({"line_number": line_number, "error": error, "row": row})

    return errors

def serotype(filename):
    '''
    Expected Fields in CSV File:

    - metadata.recordID: Unique Record ID
    - event.test.sampleCollectionDate: Date on which test sample was collected

    - location.admin.hierarchy: Type of hierarchy used describing
        locations of this record
    - location.admin1.ID: The region_id of the topmost
        region this case falls under. Usually state_ or country_
    - location.admin2.ID, location.admin3.ID,
        location.admin4.ID, location.admin5.ID:
        Regions this case falls under, in decreasing hierarchical order
    NOTE: The value 'admin_0' represents a null value for these fields.

    - event.test.test3.serotype: The serotype detected in the test.
    '''
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
            entry = Serotype()

            entry.record_id = row["metadata.recordID"]
            date_str = row["event.test.sampleCollectionDate"].split("T")[0]
            entry.record_date = datetime(*list(map(int, date_str.split("-"))))

            entry.source_filename = filename

            entry.hierarchy = row["location.admin.hierarchy"]
            assert entry.hierarchy

            entry.regions = []
            entry.regions.append(row.get("location.admin1.ID", "admin_0"))
            entry.regions.append(row.get("location.admin2.ID", "admin_0"))
            entry.regions.append(row.get("location.admin3.ID", "admin_0"))
            entry.regions.append(row.get("location.admin4.ID", "admin_0"))
            entry.regions.append(row.get("location.admin5.ID", "admin_0"))

            entry.serotype = row.get("event.test.test3.serotype", "UNKNOWN").upper()
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
