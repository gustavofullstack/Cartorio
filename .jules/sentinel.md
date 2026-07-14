## 2024-05-30 - [SQL Injection Risk via F-strings]
**Vulnerability:** SQL queries in `lgpd_direitos_v2.py` were using Python f-strings for dynamic time evaluation (e.g., `text(f"SELECT COUNT(*) FROM audit_log WHERE timestamp >= {ts_1d_expr}")`). Although not actively exploitable via user input in this specific instance, it is a significant anti-pattern.
**Learning:** Dialect-specific date logic (checking if SQLite or Postgres) in pure SQL text was driving the usage of string interpolation instead of safe binding.
**Prevention:** Compute dates securely in Python using `datetime.now(timezone.utc) - timedelta(...)` and pass them down as bound parameters (`{"ts_1d": ts_1d}`) with SQLAlchemy's `text()`.
