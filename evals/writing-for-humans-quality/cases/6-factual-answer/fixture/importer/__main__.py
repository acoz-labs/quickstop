import sys

from importer.load import import_file

if __name__ == "__main__":
    count = import_file(sys.argv[1])
    print(f"imported {count} contacts")
