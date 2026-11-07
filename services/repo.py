"""Tiny data-access layer. Real mode -> Supabase (RLS enforced with the user's JWT).
Demo mode -> in-memory store in session_state. Services above this layer are identical for both."""
import uuid
from datetime import datetime, timezone

from demo.demo_data import get_store
from services import supabase_client
from services.auth_service import is_demo


def _now():
    return datetime.now(timezone.utc).isoformat()


def select(table, eq=None, order=None, desc=True, limit=None):
    eq = eq or {}
    if is_demo():
        rows = [dict(r) for r in get_store()[table] if all(r.get(k) == v for k, v in eq.items())]
        if order:
            rows.sort(key=lambda r: str(r.get(order) or ""), reverse=desc)
        return rows[:limit] if limit else rows
    q = supabase_client.get_client().table(table).select("*")
    for k, v in eq.items():
        q = q.eq(k, v)
    if order:
        q = q.order(order, desc=desc)
    if limit:
        q = q.limit(limit)
    return q.execute().data or []


def insert(table, row):
    if is_demo():
        new = {"id": str(uuid.uuid4()), "created_at": _now(), **row}
        get_store()[table].append(new)
        return new
    data = supabase_client.get_client().table(table).insert(row).execute().data
    return data[0] if data else row


def update(table, row_id, fields):
    if is_demo():
        for r in get_store()[table]:
            if r["id"] == row_id:
                r.update(fields)
                return dict(r)
        raise PermissionError("Record not found.")
    data = supabase_client.get_client().table(table).update(fields).eq("id", row_id).execute().data
    if not data:
        raise PermissionError("Not permitted, or the record no longer exists.")
    return data[0]


def delete(table, eq):
    if is_demo():
        store = get_store()
        store[table] = [r for r in store[table] if not all(r.get(k) == v for k, v in eq.items())]
        return
    q = supabase_client.get_client().table(table).delete()
    for k, v in eq.items():
        q = q.eq(k, v)
    q.execute()
