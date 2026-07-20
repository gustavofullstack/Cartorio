import json
from pathlib import Path
from tests import postman_sync

CANONICAL_COLLECTION = Path("../infra/postman/cartorio-api.postman_collection.json")
openapi = postman_sync.load_openapi_from_app()
expected = postman_sync.convert_to_postman_v21(openapi, "https://api.2notasudi.com.br")

print("Writing to", CANONICAL_COLLECTION.absolute())
CANONICAL_COLLECTION.write_text(json.dumps(expected, indent=4) + "\n", encoding="utf-8")
