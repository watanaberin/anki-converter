import unittest
import sys
import os
import sqlite3
import pandas as pd

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from anki_converter import AnkiConverter

class TestFile(unittest.TestCase):
    def setUp(self):
        self.test_apkg = 'tests/test.apkg'
        self.test_db = 'tests/tempfile'
        # Ensure test files exist
        if not os.path.exists(self.test_apkg):
            raise FileNotFoundError(f"{self.test_apkg} not found")
        if not os.path.exists(self.test_db):
            raise FileNotFoundError(f"{self.test_db} not found")

    def test_header(self):
        converter = AnkiConverter(self.test_apkg)
        conn = sqlite3.connect(self.test_db)
        try:
            header = converter._get_header(conn)
            self.assertEqual(['Note Type', 'Card Type', 'English', 'French', 'Word Type', 'Example', 'Example in English'], header)
        finally:
            conn.close()
    
    def test_values(self):
        converter = AnkiConverter(self.test_apkg)
        conn = sqlite3.connect(self.test_db)
        try:
            header = converter._get_header(conn)
            values = converter._get_values(conn, header_fields=header[2:])
            # Assuming 'Card 1' is the default template name if not specified otherwise
            # We need to be careful here. Let's see what the actual values are by running tests.
            # For now, I'll assume 'Card 1' and update if it fails.
            expected_values = [
                ['French Vocabulary', 'Card 1', 'cat', 'le chat', 'noun', 'je vois le chat', 'I see the cat'],
                ['French Vocabulary', 'Card 1', 'chien', 'le chien', 'noun', 'le chien me voit', 'the dog sees me'],
                ['French Vocabulary', 'Card 1', 'king', 'roi', 'noun, masculine', "Le Prince Charles deviendra un jour Roi d'Angleterre.", 'Prince Charles will be King of England one day.']
            ]
            values.sort()
            expected_values.sort()
            self.assertEqual(expected_values, values)
        finally:
            conn.close()
    
    def test_invalid_file(self):
        with self.assertRaises(FileNotFoundError):
            AnkiConverter('non_existent_file.apkg')

    def test_convert_csv(self):
        output_csv = 'tests/test_output.csv'
        converter = AnkiConverter(self.test_apkg)
        converter.convert(output_csv)
        
        self.assertTrue(os.path.exists(output_csv))
        
        df = pd.read_csv(output_csv)
        self.assertEqual(list(df.columns), ['Note Type', 'Card Type', 'English', 'French', 'Word Type', 'Example', 'Example in English'])
        self.assertEqual(len(df), 3)
        
        if os.path.exists(output_csv):
            os.remove(output_csv)

    def test_convert_xlsx(self):
        output_xlsx = 'tests/test_output.xlsx'
        converter = AnkiConverter(self.test_apkg)
        converter.convert(output_xlsx)
        
        self.assertTrue(os.path.exists(output_xlsx))
        
        df = pd.read_excel(output_xlsx)
        self.assertEqual(list(df.columns), ['Note Type', 'Card Type', 'English', 'French', 'Word Type', 'Example', 'Example in English'])
        self.assertEqual(len(df), 3)
        
        if os.path.exists(output_xlsx):
            os.remove(output_xlsx)

    def test_convert_media(self):
        # This test requires a mock or a real apkg with media.
        # Since we are using a mocked apkg in setUp, we need to mock the ZipFile behavior or add media to the mock.
        # Adding media to the mock apkg is complicated because we need to create a valid zip with 'media' file.
        # For now, let's test the _process_media_tags method directly as it's the core logic for linking.
        
        converter = AnkiConverter(self.test_apkg)
        media_map = {"sound.mp3": "media/sound.mp3"}
        
        # Test CSV linking
        text = "Listen [sound:sound.mp3] here"
        processed = converter._process_media_tags(text, media_map, is_excel=False)
        self.assertEqual(processed, "Listen media/sound.mp3 here")
        
        # Test Excel linking
        processed = converter._process_media_tags(text, media_map, is_excel=True)
        self.assertEqual(processed, 'Listen =HYPERLINK("media/sound.mp3", "Play Audio") here')
        
        # Test missing media
        text = "Listen [sound:missing.mp3] here"
        processed = converter._process_media_tags(text, media_map, is_excel=False)
        self.assertEqual(processed, "Listen [sound:missing.mp3] here")

if __name__ == '__main__':
    unittest.main()
