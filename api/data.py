from datetime import datetime, timedelta

from flask import Blueprint, abort, request
from pymongo import aggregation

from models import Region, CaseEntry

bp = Blueprint("data", __name__)

@bp.route("/query", methods=["POST"])
def query():
    region_id = request.json.get("region_id")
    region = Region.objects(region_id=region_id).first()
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

    if "demographic_distributions" in requested_aggregates:
        result["demographic_distributions"] = _demographic_distributions(
            region_id, start_date, end_date,
        )

    if "trends" in requested_aggregates:
        result["trends"] = _trends(region_id, start_date, end_date)

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

    result = list(aggregate)[0]
    del result["_id"]
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
    subregion_list = list(Region.objects(parent_ids__0=region.region_id))
    subregion_name_map = {s.region_id:s.name for s in subregion_list}
    subregion_name_map["admin_0"] = "unknown"
    for obj in aggregate:
        obj["name"] = subregion_name_map.get(obj["_id"], obj["_id"])

    return aggregate



def _demographic_distributions(region_id, start_date, end_date):
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

    return {
        "age_range": list(age_range_distribution),
        "gender": list(gender_distribution)
    }

def _trends(region_id, start_date, end_date):
    start_sunday = start_date
    if start_date.weekday()!=6:
        start_sunday -= timedelta(days=1+start_date.weekday())

    delta = 5 - end_date.weekday()
    if delta==-1:
        delta = 6
    end_saturday = end_date + timedelta(days=delta)

    query = CaseEntry.objects(
        regions = region_id,
        record_date__gte = start_sunday,
        record_date__lte = end_saturday,
    ).only("tested", "confirmed")

    aggregate = query.aggregate([
        {"$group": {
            "_id": {"$week": "$record_date"},
            "tested": {"$sum": "$tested"},
            "confirmed": {"$sum": "$confirmed"},
        }},
        {"$sort": {"_id": 1}},
    ])

    labels = []
    date = start_sunday
    while date<end_saturday:
        labels.append(date.isoformat().split("T")[0])
        date += timedelta(days=7)

    records = list(aggregate)
    for i in range(len(records)):
        records[i]["_id"] = labels[i]

    return records
