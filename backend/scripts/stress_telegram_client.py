import sys
import os
import asyncio
import fakeredis
import fakeredis.aioredis
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

def simulate():
    # Setup global fakeredis
    fake_sync = fakeredis.FakeRedis()
    fake_async = fakeredis.aioredis.FakeRedis()
    
    with patch("redis.from_url", return_value=fake_sync), \
         patch("redis.asyncio.from_url", return_value=fake_async):
        
        client = TestClient(app)
        success = 0
        errors = 0
        
        for i in range(1000):
            payload = {
                "update_id": 1000000 + i,
                "message": {
                    "message_id": 100 + i,
                    "from": {
                        "id": 123456789,
                        "is_bot": False,
                        "first_name": "Gustavo",
                        "username": "gustavoalmeida"
                    },
                    "chat": {
                        "id": 123456789,
                        "first_name": "Gustavo",
                        "username": "gustavoalmeida",
                        "type": "private"
                    },
                    "date": 1718000000 + i,
                    "text": f"Olá, bot! Mensagem humana de teste {i}"
                }
            }
            
            try:
                # Bypass rate limit by changing IP per batch
                headers = {"X-Forwarded-For": f"1.1.1.{i % 200}"}
                res = client.post("/api/v1/telegram/webhook", json=payload, headers=headers)
                if res.status_code in (200, 202):
                    success += 1
                else:
                    errors += 1
                    print(f"Error {res.status_code}: {res.text}")
            except Exception as e:
                errors += 1
                print(f"Exception: {e}")
                
            if (i+1) % 100 == 0:
                print(f"Processed {i+1}/1000 - Success: {success}, Error: {errors}")

        print(f"Final -> Success: {success}, Errors: {errors}")

if __name__ == "__main__":
    simulate()
