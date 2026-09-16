1. Use `replace_with_git_merge_diff` to replace `len(db.execute(count_stmt).scalars().all())` with `db.execute(select(func.count()).select_from(count_stmt.subquery())).scalar()` in `backend/app/api/v1/_helpers.py`.
2. Format and verify the code changes using `uv run ruff format . && uv run ruff check .` and tests.
3. Complete pre commit steps to ensure proper testing, verification, review, and reflection are done.
4. Submit the change with `submit`.
