import sqlite3
import json
import csv
import os
import tempfile
from zipfile import ZipFile
from typing import List, Dict
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

    def _get_header(self, conn: sqlite3.Connection) -> List[str]:
        """Retrieves the header columns from the database."""
        try:
            models = self._get_models(conn)
            if not models:
                raise ValueError("No models found in collection")
            
            field_names: List[str] = []
            seen = set()
            for model in models.values():
                for field in model.get('flds', []):
                    name = field['name']
                    if name not in seen:
                        seen.add(name)
                        field_names.append(name)

            return ["Note Type", "Card Type"] + field_names
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

    def _get_values(self, conn: sqlite3.Connection, header_fields: List[str], media_map: Dict[str, str] = None, is_excel: bool = False) -> List[List[str]]:
        """Retrieves the note values from the database, one row per card."""
        try:
            models = self._get_models(conn)
            cur = conn.cursor()
            
            query = """
                SELECT n.flds, n.mid, c.ord 
                FROM notes n
                JOIN cards c ON n.id = c.nid
            """
            
            cur.execute(query)
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
                
                field_map = {}
                for idx, field_def in enumerate(model.get('flds', [])):
                    field_name = field_def['name']
                    raw_value = fields[idx] if idx < len(fields) else ""
                    if media_map:
                        raw_value = self._process_media_tags(raw_value, media_map, is_excel)
                    field_map[field_name] = self._clean_html(raw_value)

                ordered_fields = [field_map.get(name, "") for name in header_fields]
                cleaned_rows.append([model_name, card_type_name] + ordered_fields)
            return cleaned_rows
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve values: {e}")

    def convert(self, output_path: str, export_media: bool = False):
        """Converts the apkg file to a CSV or Excel file based on extension."""
        db_path = None
        conn = None
        try:
            db_path = self._extract_db()
            conn = self._get_connection(db_path)

            media_map = {}
            if export_media:
                output_dir = os.path.dirname(os.path.abspath(output_path))
                print("Do not support media extraction yet")
                # media_map = self._extract_media(output_dir)

            header = self._get_header(conn)
            is_excel = output_path.lower().endswith('.xlsx')
            values = self._get_values(conn, header_fields=header[2:], media_map=media_map, is_excel=is_excel)
            
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
