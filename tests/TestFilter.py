import unittest
import sys
import os
import sqlite3
import pandas as pd

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from anki_converter import AnkiConverter

class TestFilter(unittest.TestCase):
    def setUp(self):
        self.test_apkg = 'tests/test.apkg'
        self.test_db = 'tests/tempfile'
        # Ensure test files exist
        if not os.path.exists(self.test_apkg):
            raise FileNotFoundError(f"{self.test_apkg} not found")
        if not os.path.exists(self.test_db):
            raise FileNotFoundError(f"{self.test_db} not found")

    def test_get_model_names(self):
        converter = AnkiConverter(self.test_apkg)
        model_names = converter.get_model_names()
        # Based on previous tests, we know the structure but not the exact model name in test.apkg
        # Let's inspect it dynamically or assume there is at least one
        self.assertTrue(len(model_names) > 0)
        # We can verify the type
        self.assertIsInstance(model_names[0], str)

    def test_filter_valid_model(self):
        converter = AnkiConverter(self.test_apkg)
        model_names = converter.get_model_names()
        valid_model = model_names[0]
        
        output_csv = 'tests/test_filter_valid.csv'
        if os.path.exists(output_csv):
            os.remove(output_csv)
            
        converter.convert(output_csv, model_name=valid_model)
        self.assertTrue(os.path.exists(output_csv))
        
        df = pd.read_csv(output_csv)
        self.assertTrue(len(df) > 0)
        
        if os.path.exists(output_csv):
            os.remove(output_csv)

    def test_filter_invalid_model(self):
        converter = AnkiConverter(self.test_apkg)
        with self.assertRaises(ValueError):
            converter.convert('tests/should_not_exist.csv', model_name="InvalidModelName")

if __name__ == '__main__':
    unittest.main()
