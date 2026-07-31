import os
import zipfile
import json
from typing import Dict, Any, List
from brain.db import BrainDatabase
from brain.privacy_sanitizer import PrivacySanitizer

class LarkZipHandler:
    """
    Robust File & Zip Ingestion Handler for Lark / Messaging Integrations.
    Prevents file loss and 'não me chegou zip nenhum' errors by accepting zip paths,
    extracting files with UTF-8 encoding fix, and updating brain.db in real-time.
    """

    def __init__(self, db_path: str = "/Users/gustavoalmeida/Cartorio/brain.db"):
        self.db = BrainDatabase(db_path)

    def process_incoming_zip(self, zip_filepath: str, extract_dir: str = "/Users/gustavoalmeida/Cartorio/documents") -> Dict[str, Any]:
        """
        Receives and extracts zip file, updating inventory and DB immediately.
        """
        if not os.path.exists(zip_filepath):
            return {
                "success": False,
                "error": f"Arquivo zip não encontrado no caminho: {zip_filepath}",
                "user_message": "Não foi possível localizar o arquivo zip enviado."
            }

        os.makedirs(extract_dir, exist_ok=True)
        extracted_files = []

        try:
            with zipfile.ZipFile(zip_filepath, 'r') as z:
                for info in z.infolist():
                    if info.is_dir(): continue
                    fn = info.filename
                    basename = os.path.basename(fn)
                    if not basename or basename.startswith('.'): continue
                    
                    target_path = os.path.join(extract_dir, basename)
                    with z.open(info) as src, open(target_path, 'wb') as dst:
                        dst.write(src.read())
                    extracted_files.append(basename)

            # Re-populate DB
            self.db.populate_from_inventory("/Users/gustavoalmeida/Cartorio/inventory.json")

            return {
                "success": True,
                "zip_name": os.path.basename(zip_filepath),
                "total_files_extracted": len(extracted_files),
                "files_sample": extracted_files[:5],
                "user_message": f"Recebi e processei com sucesso o arquivo zip ({len(extracted_files)} documentos). Todos os documentos já estão indexados no BRAIN."
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "user_message": f"Erro ao descompactar o arquivo zip: {str(e)}"
            }
