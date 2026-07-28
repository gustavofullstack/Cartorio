import json
from pathlib import Path
from tests.test_postman_sync_g8 import convert_to_postman_v21, load_openapi_from_app

CANONICAL_COLLECTION = Path("../infra/postman/cartorio-api.postman_collection.json")
openapi = load_openapi_from_app()
expected = convert_to_postman_v21(openapi, "https://api.2notasudi.com.br")

print("Writing to", CANONICAL_COLLECTION.absolute())
CANONICAL_COLLECTION.write_text(json.dumps(expected, indent=4) + "\n", encoding="utf-8")
