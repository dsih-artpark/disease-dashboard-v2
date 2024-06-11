import os
import json

from fast_autocomplete import AutoComplete, autocomplete_factory

from models import Region
from tenants import all_tenants

os.makedirs("autocomplete_objs/", exist_ok=True)

def generate_objs():
    counts = {
        "country": 10,
        "state": 9,
        "district": 8,
        "ulb": 8,
        "subdistrict": 7,
        "zone": 7,
        "prabhag": 7,
        "ward": 4,
        "village": 4,
    }
    for tenant in all_tenants:
        words = {}
        regions_to_visit = list(Region.objects(region_id=tenant.scope_region))
        while regions_to_visit:
            region = regions_to_visit[0]
            print(tenant.tenant_id, region.region_id)
            key = region.name + " " + region.region_id
            context = {}
            display = region.region_id + "|||" + region.name
            count = counts[region.region_type]
            words[key] = [context, display, count]
            regions_to_visit = regions_to_visit[1:] + list(Region.objects(parent_ids__0=region.region_id))
        with open("autocomplete_objs/" + tenant.tenant_id + ".json", "w") as f:
            json.dump(words, f)

autocompleters = {}
def init():
    for tenant in all_tenants:
        autocompleters[tenant.tenant_id] = autocomplete_factory(
            content_files = {
                "words": {
                    "filepath":"autocomplete_objs/" + tenant.tenant_id + ".json",
                    "compress": True
                }
            }
        )

def search(tenant_id, term):
    matches = autocompleters[tenant_id].search(word=term, max_cost=3, size=5)
    results = []
    for match in matches:
        word = autocompleters[tenant_id].words[match[0]]
        results.append(word.display.split("|||"))
    return results
