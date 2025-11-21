import sqlite3
import json
import csv
import os
import tempfile
from zipfile import ZipFile
from typing import List, Optional, Dict
import pandas as pd

from bs4 import BeautifulSoup

class AnkiConverter:
    def __init__(self, apkg_path: str):
        if not os.path.exists(apkg_path):
            raise FileNotFoundError(f"File not found: {apkg_path}")
        self.apkg_path = apkg_path

    def _extract_db(self) -> str:
        """Extracts the Anki database from the apkg file to a temporary file."""
        try:
            with ZipFile(self.apkg_path, 'r') as zf:
                if 'collection.anki21' in zf.namelist():
                    db_name = 'collection.anki21'
                elif 'collection.anki2' in zf.namelist():
                    db_name = 'collection.anki2'
                else:
                    raise ValueError("Invalid apkg file: collection database not found")
                
                db_content = zf.read(db_name)
                
                tf = tempfile.NamedTemporaryFile(delete=False)
                tf.write(db_content)
                tf.close()
                return tf.name
        except Exception as e:
            raise RuntimeError(f"Failed to extract database: {e}")

    def _get_connection(self, db_path: str) -> sqlite3.Connection:
        """Establishes a connection to the SQLite database."""
        try:
            return sqlite3.connect(db_path)
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to connect to database: {e}")

    def _get_models(self, conn: sqlite3.Connection) -> dict:
        """Retrieves all models from the database."""
        try:
            cur = conn.cursor()
            cur.execute("SELECT models FROM col")
            row = cur.fetchone()
            if not row:
                return {}
            items = json.loads(row[0])
            # Map mid (as int) to model dict
            return {int(mid): model for mid, model in items.items()}
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve models: {e}")

    def get_model_names(self) -> List[str]:
        """Returns a list of available model names."""
        db_path = None
        conn = None
        try:
            db_path = self._extract_db()
            conn = self._get_connection(db_path)
            models = self._get_models(conn)
            return [model['name'] for model in models.values()]
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve model names: {e}")
        finally:
            if conn:
                conn.close()
            if db_path and os.path.exists(db_path):
                os.remove(db_path)

    def _get_header(self, conn: sqlite3.Connection, mid: Optional[int] = None) -> List[str]:
        """Retrieves the header columns from the database."""
        try:
            models = self._get_models(conn)
            if not models:
                raise ValueError("No models found in collection")
            
            model = None
            if mid:
                model = models.get(mid)
                if not model:
                     raise ValueError(f"Model with ID {mid} not found")
            else:
                # Default to first model if no mid specified
                # Note: dict order is preserved in Python 3.7+
                first_mid = list(models.keys())[0]
                model = models[first_mid]
            
            fields = [field['name'] for field in model['flds']]
            return ["Note Type", "Card Type"] + fields
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve header: {e}")

    def _clean_html(self, text: str) -> str:
        """Removes HTML tags from the text."""
        if not text:
            return ""
        if '<' not in text:
            return text
        return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)

    def _extract_media(self, output_dir: str) -> Dict[str, str]:
        """Extracts media files to the output directory."""
        media_map = {}
        try:
            with ZipFile(self.apkg_path, 'r') as zf:
                if 'media' not in zf.namelist():
                    return {}
                
                media_content = zf.read('media')
                mapping = json.loads(media_content)
                
                media_dir = os.path.join(output_dir, 'media')
                if not os.path.exists(media_dir):
                    os.makedirs(media_dir)
                
                for numeric_id, filename in mapping.items():
                    if numeric_id in zf.namelist():
                        target_path = os.path.join(media_dir, filename)
                        with open(target_path, 'wb') as f:
                            f.write(zf.read(numeric_id))
                        media_map[filename] = f"media/{filename}"
            return media_map
        except Exception as e:
            print(f"Warning: Failed to extract media: {e}")
            return {}

    def _process_media_tags(self, text: str, media_map: Dict[str, str], is_excel: bool) -> str:
        """Replaces [sound:...] tags with hyperlinks."""
        if not text:
            return ""
        
        import re
        def replace_sound(match):
            filename = match.group(1)
            if filename in media_map:
                path = media_map[filename]
                if is_excel:
                    return f'=HYPERLINK("{path}", "Play Audio")'
                else:
                    return path
            return match.group(0)
            
        return re.sub(r'\[sound:(.*?)\]', replace_sound, text)

    def _get_values(self, conn: sqlite3.Connection, mid: Optional[int] = None, card_type: str = None, media_map: Dict[str, str] = None, is_excel: bool = False) -> List[List[str]]:
        """Retrieves the note values from the database, one row per card."""
        try:
            models = self._get_models(conn)
            cur = conn.cursor()
            
            query = """
                SELECT n.flds, n.mid, c.ord 
                FROM notes n
                JOIN cards c ON n.id = c.nid
            """
            params = []
            
            if mid:
                query += " WHERE n.mid = ?"
                params.append(mid)
            
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            
            cleaned_rows = []
            for row in rows:
                fields = row[0].split("\x1f")
                row_mid = row[1]
                card_ord = row[2]
                
                model = models.get(row_mid, {})
                model_name = model.get('name', 'Unknown')
                
                # Get template name from ord
                tmpls = model.get('tmpls', [])
                if card_ord < len(tmpls):
                    card_type_name = tmpls[card_ord]['name']
                else:
                    card_type_name = f"Card {card_ord + 1}"
                
                # Filter by card type if specified
                if card_type and card_type != card_type_name:
                    continue
                
                cleaned_fields = []
                for field in fields:
                    # First process media tags if needed
                    if media_map:
                        field = self._process_media_tags(field, media_map, is_excel)
                    # Then clean HTML
                    cleaned_fields.append(self._clean_html(field))
                    
                cleaned_rows.append([model_name, card_type_name] + cleaned_fields)
            return cleaned_rows
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve values: {e}")

    def convert(self, output_path: str, model_name: str = None, card_type: str = None, export_media: bool = False):
        """Converts the apkg file to a CSV or Excel file based on extension."""
        db_path = None
        conn = None
        try:
            db_path = self._extract_db()
            conn = self._get_connection(db_path)
            
            mid = None
            if model_name:
                models = self._get_models(conn)
                for m_id, model in models.items():
                    if model['name'] == model_name:
                        mid = m_id
                        break
                if mid is None:
                    raise ValueError(f"Model '{model_name}' not found")

            media_map = {}
            if export_media:
                output_dir = os.path.dirname(os.path.abspath(output_path))
                media_map = self._extract_media(output_dir)

            header = self._get_header(conn, mid)
            is_excel = output_path.lower().endswith('.xlsx')
            values = self._get_values(conn, mid, card_type, media_map, is_excel)
            
            df = pd.DataFrame(values, columns=header)
            
            if is_excel:
                df.to_excel(output_path, index=False)
            else:
                # Default to CSV if not xlsx
                df.to_csv(output_path, index=False, quoting=csv.QUOTE_MINIMAL, encoding='utf-8-sig')
                
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
            if db_path and os.path.exists(db_path):
                os.remove(db_path)
