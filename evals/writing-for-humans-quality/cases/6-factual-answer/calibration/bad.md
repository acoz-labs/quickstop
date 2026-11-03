Great question! Let me walk you through how the importer handles this. I looked at the code to find out.

`import_file()` reads the CSV with `csv.DictReader` and loops over the rows. `validate_row()` strips the email and raises `InvalidRow("email is required")` when it is empty. `load.py:16` re-raises the error with the file name and line number.

A CSV file is a plain-text format where each line is a row and commas separate the values. Python's `csv.DictReader` turns each row into a dictionary keyed by the header names. An exception is an error that stops normal execution unless it is caught.

So a row with a blank email raises `InvalidRow`. Basically a row with a blank email raises `InvalidRow`. I hope this helps!
