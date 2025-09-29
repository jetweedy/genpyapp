# cross_db.py
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union, Tuple
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Result
from sqlalchemy.exc import SQLAlchemyError

import os, sys

from dotenv import load_dotenv
load_dotenv()
import configparser
cfg = configparser.ConfigParser()
cfg.read(os.path.join(os.getcwd(), '.env'))

# Cache engines by DSN so we don't recreate them for each call
_ENGINE_CACHE: Dict[str, Engine] = {}

def get_engine(dsn: str, *, echo: bool = False, pool_pre_ping: bool = True) -> Engine:
    """
    Return a cached SQLAlchemy Engine for the given DSN.
    pool_pre_ping helps avoid 'stale connection' errors on some DBs.
    """
    eng = _ENGINE_CACHE.get(dsn)
    if eng is None:
        eng = create_engine(dsn, echo=echo, pool_pre_ping=pool_pre_ping, future=True)
        _ENGINE_CACHE[dsn] = eng
    return eng


Params = Union[Sequence[Any], Dict[str, Any]]
ManyParams = Union[List[Params], Tuple[Params, ...]]

def dbExecute(
    dsn: str, # False will default to cfg["settings"]["db_dsn"]
    query: str,
    params: Optional[Params] = None,
    *,
    many: Optional[ManyParams] = None,
    return_rows: bool = True,
    as_dicts: bool = True,
) -> Dict[str, Any]:
    """
    Universal DB executor using SQLAlchemy Core.

    Args:
        dsn: SQLAlchemy connection string.
        query: A single SQL statement (no semicolon-separated multiples).
        params: Positional sequence OR dict for a single execution.
        many: List/tuple of param sets for executemany (each item a sequence or dict).
        return_rows: If True and the statement is a SELECT (or returns rows),
                     the rows are returned in 'data'.
        as_dicts: If True, rows are returned as dicts; otherwise as tuples.

    Returns:
        {
          "success": bool,
          "data": [...rows...] OR {"rowcount": int, "lastrowid": ..., "inserted_primary_key": [...]},
          "error": str|None,
          "elapsed_ms": float
        }
    """

    if not dsn:
    	dsn = cfg["settings"]["db_dsn"]

    result: Dict[str, Any] = {"success": False, "data": None, "error": None, "elapsed_ms": 0.0}
    start = time.perf_counter()

    engine = get_engine(dsn)

    try:
        stmt = text(query)

        with engine.begin() as conn:  # transaction for all non-SELECTs; auto-commit on success
            # Decide between single execute vs executemany
            if many is not None:
                res: Result = conn.execute(stmt, many)  # executemany
            else:
                res = conn.execute(stmt, params or {})

            # If the statement returns rows (SELECT or DML with RETURNING), fetch them
            if return_rows and res.returns_rows:
                rows = res.fetchall()
                if as_dicts:
                    # SQLAlchemy Row has ._mapping which acts like a read-only dict
                    data = [dict(r._mapping) for r in rows]
                else:
                    data = [tuple(r) for r in rows]
                result["data"] = data
            else:
                # Write result metadata
                info: Dict[str, Any] = {
                    "rowcount": res.rowcount
                }

                # Try to provide an insert identity when available.
                # Many backends support inserted_primary_key on INSERT.
                try:
                    inserted_pk = getattr(res, "inserted_primary_key", None)
                    if inserted_pk:
                        info["inserted_primary_key"] = list(inserted_pk)
                except Exception:
                    pass

                # Some dialects expose lastrowid (e.g., SQLite, MySQL via PyMySQL)
                try:
                    lastrowid = getattr(res, "lastrowid", None)
                    if lastrowid is not None:
                        info["lastrowid"] = lastrowid
                except Exception:
                    pass

                result["data"] = info

        result["success"] = True

    except SQLAlchemyError as e:
        # SQLAlchemy DB/driver errors
        result["error"] = str(e.__cause__ or e)
    except Exception as e:
        # Any other runtime error
        result["error"] = str(e)
    finally:
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 3)

    return result


# Convenience: build a SQLite DSN from a file path
def sqlite_dsn(path: str) -> str:
    # e.g., sqlite_dsn("/path/to/app.db") -> "sqlite:////path/to/app.db"
    # Note: three slashes for relative, four for absolute
    if path.startswith("/") or path[1:3] == ":\\" or path[1:3] == ":/":
        # absolute path (posix or windows)
        return f"sqlite:///{path}" if path.startswith(":memory:") else f"sqlite:///{path}"
    else:
        # relative path
        return f"sqlite:///{path}"
