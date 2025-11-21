import argparse
import sys
import os

# Ensure we can import from the same directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from anki_converter import AnkiConverter

def main():
    parser = argparse.ArgumentParser(description="Convert .apkg Anki deck files to .csv or .xlsx")
    parser.add_argument("input_file", help="Path to the .apkg file")
    parser.add_argument("-o", "--output", help="Path to the output file (e.g., filename.csv or filename.xlsx)")
    parser.add_argument("--format", choices=['csv', 'xlsx'], help="Output format (overrides file extension)")
    parser.add_argument("--filter", help="Filter by Note Type (Model Name)")
    parser.add_argument("--card-type", help="Filter by Card Type (Template Name)")
    parser.add_argument("--list-types", action="store_true", help="List available Note Types")
    parser.add_argument("--media", action="store_true", help="Extract media files and link them in the output")

    args = parser.parse_args()

    input_path = args.input_file
    
    if args.list_types:
        try:
            converter = AnkiConverter(input_path)
            models = converter.get_model_names()
            print(f"Available Note Types in '{input_path}':")
            for model in models:
                print(f"- {model}")
            sys.exit(0)
        except Exception as e:
            print(f"Error listing types: {e}")
            sys.exit(1)

    output_path = args.output
    output_format = args.format
    filter_model = args.filter
    filter_card_type = args.card_type
    export_media = args.media

    if not output_path:
        # Default to CSV if no output specified
        output_path = f"{input_path}.csv"
        if output_format == 'xlsx':
            output_path = f"{input_path}.xlsx"
    
    # If format is explicitly specified, ensure extension matches
    if output_format:
        if output_format == 'xlsx' and not output_path.lower().endswith('.xlsx'):
             output_path = os.path.splitext(output_path)[0] + '.xlsx'
        elif output_format == 'csv' and not output_path.lower().endswith('.csv'):
             output_path = os.path.splitext(output_path)[0] + '.csv'

    try:
        converter = AnkiConverter(input_path)
        converter.convert(output_path, model_name=filter_model, card_type=filter_card_type, export_media=export_media)
        print(f"Successfully converted '{input_path}' to '{output_path}'")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()