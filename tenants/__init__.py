import importlib
import inspect
import os

from config import Tenant

domain_map = {}
for filename in os.listdir("tenants"):
    if not filename[-3:] == ".py":
        continue
    module = importlib.import_module("tenants." + filename[:-3])
    for obj_name in dir(module):
        obj = getattr(module, obj_name)
        if inspect.isclass(obj) and issubclass(obj, Tenant):
            for domain in obj.domains:
                domain_map[domain] = obj

def get_tenant_for_domain(domain):
    return domain_map.get(domain)
