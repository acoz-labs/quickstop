"""Sum one numeric column of a CSV file."""
import csv


def column_sum(lines, column):
    rows = csv.DictReader(line for line in lines if line.strip())
    return sum(float(row[column]) for row in rows)
