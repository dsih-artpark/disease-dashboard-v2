import glob

import import_from_file
from models import SourceFile

DATA_TYPES = ("case_data", "predictions")
SOURCE_DIR = "source_files/"

for t in DATA_TYPES:
    dir = SOURCE_DIR + t + "/"
    for filepath in glob.iglob(dir + "**/*.csv", recursive=True):
        print("\nIMPORTING:", filepath)
        source_exists = SourceFile.objects(name=filepath).first()
        if source_exists:
            print("ALREADY IMPORTED, SKIPPING")
            continue

        import_errors = getattr(import_from_file, t)(filepath)
        if import_errors is not None:
            print(len(import_errors), "ERROR(S)")
            SourceFile(
                name = filepath,
                data_type = t,
                import_errors = import_errors,
            ).save()
