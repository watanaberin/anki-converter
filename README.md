# Apkg to Csv/Xlsx

Converts .apkg Anki deck SRS file to .csv or .xlsx

## Requirements

- Python 3.6+
- pandas
- openpyxl
- beautifulsoup4

## Installation

1. Clone the repository.
2. Install dependencies:

```bash
pip install pandas openpyxl beautifulsoup4
```

## Usage

Export your Deck in Anki (for older versions, click Support older Anki versions).

### Basic Usage (CSV)

```bash
python src/run.py filename.apkg
```
This will output `filename.apkg.csv`. HTML tags are stripped automatically, and every field defined in your Anki models is exported alongside `Note Type` and `Card Type` so you can slice the data directly in Excel.

### Excel Output

You can export to Excel by specifying the output filename with `.xlsx` extension or using the `--format` flag.

```bash
python src/run.py filename.apkg -o filename.xlsx
# OR
python src/run.py filename.apkg --format xlsx
```

Once the file is generated, open it in Excel (or any spreadsheet tool) to build your own filters, pivot tables, and charts. Every card is exported with every field so you can manipulate the data without running additional commands.

### Options

- `input_file`: Path to the .apkg file.
- `-o`, `--output`: Path to the output file.
- `--format`: Output format (`csv` or `xlsx`).
- `--media`: Extract media files and link them in the output (experimental).

## Tests

```bash
python -m unittest discover -s tests -p "Test*.py"
```

## Contributions

Contributions are welcome and will be fully credited.

## License

This project is open-sourced software licensed under the MIT license.
