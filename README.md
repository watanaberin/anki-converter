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
This will output `filename.apkg.csv`. HTML tags are automatically stripped from the output, and a "Note Type" column is added as the first column to identify the model of each note.

### Excel Output

You can export to Excel by specifying the output filename with `.xlsx` extension or using the `--format` flag.

```bash
python src/run.py filename.apkg -o filename.xlsx
# OR
python src/run.py filename.apkg --format xlsx
```

### Filtering by Note Type

If your deck contains multiple Note Types, you can list them and filter the export.

**List available Note Types:**
```bash
python src/run.py filename.apkg --list-types
```

**Filter by Note Type:**
```bash
python src/run.py filename.apkg --filter "Note Type Name"
```

### Filtering by Card Type

You can also filter by "Card Type" (Template Name), e.g., "Card 1".
**Note:** The export format is now one row per **Card**. If a note has multiple cards, it will appear multiple times in the output.

```bash
python src/run.py filename.apkg --card-type "Card 1"
```

### Options

- `input_file`: Path to the .apkg file.
- `-o`, `--output`: Path to the output file.
- `--format`: Output format (`csv` or `xlsx`).
- `--filter`: Filter by Note Type (Model Name).
- `--card-type`: Filter by Card Type (Template Name).
- `--list-types`: List available Note Types.

## Tests

```bash
python -m unittest tests.TestFile
```

## Contributions

Contributions are welcome and will be fully credited.

## License

This project is open-sourced software licensed under the MIT license.
