import os
import pytest
from brain.db import BrainDatabase

def test_db_init_and_search(tmp_path):
    db_file = str(tmp_path / "test_brain.db")
    db = BrainDatabase(db_path=db_file)
    
    # Test document search on populated DB
    db.populate_from_inventory(inventory_json_path="/Users/gustavoalmeida/Cartorio/inventory.json")
    results = db.search_documents("Testamento", limit=5)
    assert len(results) > 0
    assert any("Testamento" in r["category"] or "Testamento" in r["filename"] for r in results)
