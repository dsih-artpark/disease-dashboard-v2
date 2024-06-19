from datetime import datetime, timedelta
import os

from flask import Blueprint, abort, request
from pymongo import aggregation

from import_from_file import predictions
from models import Region, CaseEntry, Prediction

bp = Blueprint("data", __name__)

@bp.route("/query", methods=["POST"])
def query():
    region_id = request.json.get("region_id")
    region = Region.objects(region_id=region_id).first()

    breadcrumbs = []
    for i in range(len(region.parent_ids)):
        breadcrumbs.append([region.parent_names[i], region.parent_ids[i]])
        if region.parent_ids[i]==request.tenant.scope_region:
            break
    breadcrumbs = breadcrumbs[::-1] + [[region.name, region_id]]

    if not region:
        abort(404)
        return
    if not region.in_scope(request.tenant.scope_region):
        abort(401)
        return

    start_date_str = request.json.get("start_date", "")
    start_date = datetime.fromisoformat(start_date_str)
    end_date_str = request.json.get("end_date", "")
    end_date = datetime.fromisoformat(end_date_str)

    result = {
        "region_id": region_id,
        "region_name": region.name,
        "region_type": region.region_type,
        "breadcrumbs": breadcrumbs,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "available_stages": request.tenant.stages,
    }

    requested_aggregates = request.json.get("aggregates", [])

    if "summary" in requested_aggregates:
        result["summary"] = _summary(region_id, start_date, end_date)

    if "subregionwise_distribution" in requested_aggregates:
        result["subregionwise_distribution"] = _subregionwise_distribution(
            region, start_date, end_date,
        )

    if "feature_distributions" in requested_aggregates:
        result["feature_distributions"] = _feature_distributions(
            region_id, start_date, end_date,
        )

    if "trends" in requested_aggregates:
        result["trends"] = _trends(region_id, start_date, end_date)

    if "predictions" in requested_aggregates:
        result["predictions"] = _predictions(region_id, start_date, end_date)

    if "reports" in requested_aggregates:
        result["reports"] = _reports()

    return result


def _summary(region_id, start_date, end_date):
    grouping_specs = {"_id": None}
    for stage in request.tenant.stages:
        grouping_specs[stage] = {"$sum": f'${stage}'}

    query_fields = request.tenant.stages
    aggregate = CaseEntry.objects(
        regions = region_id,
        record_date__gte = start_date,
        record_date__lte = end_date,
    ).only(*query_fields).aggregate([{"$group": grouping_specs}])

    result = list(aggregate)
    if result:
        result = result[0]
        del result["_id"]
    else:
        result = {stage:0 for stage in request.tenant.stages}
    return result

def _subregionwise_distribution(region, start_date, end_date):
    query_fields = ["regions"] + request.tenant.stages
    query = CaseEntry.objects(
        regions = region.region_id,
        record_date__gte = start_date,
        record_date__lte = end_date,
    ).only(*query_fields)

    aggregation_index = request.tenant.subregion_indexes[region.region_type]
    grouping_specs = {
        "_id": {"$arrayElemAt": ["$regions", aggregation_index]},
    }
    for stage in request.tenant.stages:
        grouping_specs[stage] = {"$sum": f'${stage}'}

    aggregate = list(query.aggregate([{"$group": grouping_specs}]))
    aggregate_dict = {r["_id"]:r for r in aggregate}

    subregion_list = list(Region.objects(parent_ids__0=region.region_id))
    results = []
    for region in subregion_list:
        row = {"region_id": region.region_id, "name": region.name}
        case_numbers = aggregate_dict.get(region.region_id, {})
        for stage in request.tenant.stages:
            row[stage] = case_numbers.get(stage, 0)
        results.append(row)
    return results



def _feature_distributions(region_id, start_date, end_date):
    query = CaseEntry.objects(
        regions = region_id,
        record_date__gte = start_date,
        record_date__lte = end_date,
        source = "linelists",
        confirmed__gte = 1,
    ).only("age_range", "gender")

    age_range_distribution = query.aggregate([
        {"$group": {
            "_id": "$age_range",
            "cases": {"$sum": "$confirmed"}
        }},
    ])

    gender_distribution = query.aggregate([
        {"$group": {
            "_id": "$gender",
            "cases": {"$sum": "$confirmed"}
        }}
    ])

    test_type_distribution = query.aggregate([
        {"$group": {
            "_id": "$test_type",
            "cases": {"$sum": "$confirmed"}
        }}
    ])

    return {
        "age_range": list(age_range_distribution),
        "gender": list(gender_distribution),
        "test_type": list(test_type_distribution),
    }

def _trends(region_id, start_date, end_date):
    start_monday = start_date - timedelta(days=start_date.weekday())
    end_sunday = end_date + timedelta(days=6-end_date.weekday())

    labels = {}
    date = start_monday
    while date<end_sunday:
        labels[date.isoformat().split("T")[0]] = {"confirmed": 0, "tested": 0}
        date += timedelta(days=7)

    query = CaseEntry.objects(
        regions = region_id,
        record_date__gte = start_monday,
        record_date__lte = end_sunday,
    ).only("tested", "confirmed")

    aggregate = query.aggregate([
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date":"$record_date"}},
            "tested": {"$sum": "$tested"},
            "confirmed": {"$sum": "$confirmed"},
        }},
        {"$sort": {"_id": 1}},
    ])

    records = list(aggregate)
    for record in records:
        date = datetime(*map(int, record["_id"].split("-")))
        week_start_date = date - timedelta(days=date.weekday())
        label = week_start_date.isoformat().split("T")[0]
        labels[label]["confirmed"] += record["confirmed"]
        labels[label]["tested"] += record["tested"]

    results = []
    for label in sorted(labels.keys()):
        results.append({
            "date": label,
            "confirmed": labels[label]["confirmed"],
            "tested": labels[label]["tested"]
        })
    return results

def _predictions(parent_id, start_date, end_date):
    end_sunday = end_date + timedelta(days=6-end_date.weekday())
    prediction_dates = [
        end_sunday + timedelta(days=1),
        end_sunday + timedelta(days=8),
        end_sunday + timedelta(days=15),
        end_sunday + timedelta(days=22),
    ]

    subregion_list = list(Region.objects(parent_ids__0=parent_id))
    results = []
    for date in prediction_dates:
        date_obj = {
            "date": date.isoformat().split("T")[0],
            "prediction": {},
            "subregions": [],
        }
        parent_prediction = Prediction.objects(region_id=parent_id, date=date).first()
        date_obj["prediction"] = {
            "zone": parent_prediction.prediction_zone if parent_prediction else -2,
            "value": parent_prediction.prediction if parent_prediction else -0,
        }

        predictions_dict = {}
        for p in Prediction.objects(parent_id=parent_id, date=date):
            predictions_dict[p.region_id] =  {
                "zone": p.prediction_zone,
                "value": p.prediction,
            }

        for region in subregion_list:
            p = predictions_dict.get(region.region_id, {})
            date_obj["subregions"].append({
                "region_id": region.region_id,
                "name": region.name,
                "zone": p.get("zone", -2),
                "value": p.get("value", 0),
            })
        results.append(date_obj)
    return results

def _reports():
    return sorted(os.listdir("source_files/reports/" + request.tenant.tenant_id))
