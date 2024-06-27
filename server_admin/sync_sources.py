import datetime
import glob
import os

import import_from_file
from models import CaseEntry, Prediction, SourceFile

DATA_TYPES = ("case_data", "predictions")
SOURCE_DIR = "source_files/"

def _delete_source(source):
    print("Deleting", source.name)
    if source.data_type=="case_data":
        CaseEntry.objects(source_filename=source.name).delete()
    elif source.data_type=="predictions":
        Prediction.objects(source_filename=source.name).delete()
    source.delete()


print("\n\nCHECKING IF ANY EXISTING SOURCES HAVE BEEN DELETED")
for source in SourceFile.objects():
    if not os.path.exists(source.name):
        print(source.name, "not present in source_files/")
        _delete_source(source)

for t in DATA_TYPES:
    dir = SOURCE_DIR + t + "/"
    for filepath in glob.iglob(dir + "**/*.csv", recursive=True):
        print("\nPROCESSING:", filepath)
        source = SourceFile.objects(name=filepath).first()
        if source:
            print("Source Exists, Last Synced At:", source.import_date)
            last_mod_date = datetime.datetime.utcfromtimestamp(os.path.getmtime(filepath))
            print("File Last Modified At:", last_mod_date)
            if source.import_date>last_mod_date:
                print("File Unchanged, Skipping Import")
                continue
            else:
                print("File Changed, Dropping and Reimporting Records")
                _delete_source(source)

        import_errors = getattr(import_from_file, t)(filepath)
        if import_errors is not None:
            print(len(import_errors), "ERROR(S)")
            SourceFile(
                name = filepath,
                data_type = t,
                import_errors = import_errors,
            ).save()
