import hmac
import importlib
from fastapi import FastAPI, Depends, Request

try:
    from backend.app.api.v1 import router as r
    print("Router module successfully imported.")
    print("hmac is available in router module:", 'hmac' in dir(r))
except Exception as e:
    print("Error importing router module:", e)
