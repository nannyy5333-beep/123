
import os
from typing import Any, Dict, List, Optional
import httpx

class DataStore:
    """
    Универсальный слой доступа к данным:
     - Если заданы SUPABASE_URL и SUPABASE_SERVICE_KEY -> используем REST (PostgREST).
     - Иначе пробуем DATABASE_URL (Postgres) через psycopg (опционально).
    """
    def __init__(self):
        self.supabase_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.supabase_schema = os.getenv("SUPABASE_DB_SCHEMA")  # если схема не public, укажи тут
        self.database_url = os.getenv("DATABASE_URL")

        self._client: Optional[httpx.Client] = None
        self._pg_conn = None

        if self.supabase_url and self.supabase_key:
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Accept": "application/json",
            }
            if self.supabase_schema and self.supabase_schema != "public":
                headers["Accept-Profile"] = self.supabase_schema
            self._client = httpx.Client(
                base_url=self.supabase_url + "/rest/v1/",
                headers=headers,
                timeout=30.0,
            )
        else:
            # Путь для psycopg3 (опционально)
            try:
                import psycopg
                if self.database_url:
                    self._pg_conn = psycopg.connect(self.database_url)
            except Exception:
                self._pg_conn = None

    # ---------------- Supabase REST helpers -----------------

    def _sb_get(self, path: str, params: Any) -> httpx.Response:
        """
        GET с понятной ошибкой (возвращаем тело при 4xx/5xx).
        params может быть dict или list[tuple] для повторяющихся ключей.
        """
        r = self._client.get(path, params=params)  # type: ignore[attr-defined]
        if r.status_code >= 400:
            raise httpx.HTTPStatusError(f"Supabase {r.status_code}: {r.text}", request=r.request, response=r)
        return r

    def _sb_select(self, table: str, select: str = "*", **filters) -> List[Dict[str, Any]]:
        params: List[tuple[str, str]] = [("select", select)]
        for k, v in filters.items():
            if isinstance(v, str) and (v.startswith("ilike.") or v.startswith("gte.") or v.startswith("lte.") or v.startswith("eq.")):
                params.append((k, v))
            else:
                params.append((k, f"eq.{v}"))
        return self._sb_get(table, params).json()

    def _sb_insert(self, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
        r = self._client.post(  # type: ignore[attr-defined]
            table,
            json=row,
            headers={"Prefer": "return=representation"},
        )
        if r.status_code >= 400:
            raise httpx.HTTPStatusError(f"Supabase {r.status_code}: {r.text}", request=r.request, response=r)
        data = r.json()
        return data[0] if isinstance(data, list) and data else data

    def _sb_update(self, table: str, id: Any, patch: Dict[str, Any]) -> Dict[str, Any]:
        r = self._client.patch(  # type: ignore[attr-defined]
            f"{table}?id=eq.{id}",
            json=patch,
            headers={"Prefer": "return=representation"},
        )
        if r.status_code >= 400:
            raise httpx.HTTPStatusError(f"Supabase {r.status_code}: {r.text}", request=r.request, response=r)
        data = r.json()
        return data[0] if isinstance(data, list) and data else data

    def _sb_delete(self, table: str, id: Any) -> int:
        r = self._client.delete(f"{table}?id=eq.{id}")  # type: ignore[attr-defined]
        if r.status_code >= 400:
            raise httpx.HTTPStatusError(f"Supabase {r.status_code}: {r.text}", request=r.request, response=r)
        return r.status_code

    # ---------------- Postgres helpers (опционально) -----------------

    def _pg_fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._pg_conn.cursor() as cur:  # type: ignore[union-attr]
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _pg_fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with self._pg_conn.cursor() as cur:  # type: ignore[union-attr]
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None

    def _pg_insert_returning(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        keys = list(data.keys())
        vals = [data[k] for k in keys]
        placeholders = ", ".join(["%s"] * len(keys))
        with self._pg_conn.cursor() as cur:  # type: ignore[union-attr]
            cur.execute(f"insert into {table} ({', '.join(keys)}) values ({placeholders}) returning *", vals)
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            self._pg_conn.commit()  # type: ignore[union-attr]
            return dict(zip(cols, row))

    def _pg_update_returning(self, table: str, id_field: str, id_val: Any, patch: Dict[str, Any]) -> Dict[str, Any]:
        sets = ", ".join([f"{k}=%s" for k in patch])
        vals = list(patch.values()) + [id_val]
        with self._pg_conn.cursor() as cur:  # type: ignore[union-attr]
            cur.execute(f"update {table} set {sets} where {id_field}=%s returning *", vals)
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            self._pg_conn.commit()  # type: ignore[union-attr]
            return dict(zip(cols, row))

    # ---------------- Misc helpers -----------------

    def _infer_columns(self, table: str) -> set:
        """
        Пробует угадать допустимые колонки таблицы: берёт один ряд и использует его ключи.
        Если таблица пустая/недоступна — возвращает безопасный набор.
        """
        if not self._client:
            return {"id","name","price","stock","description","created_at","updated_at","category_id","subcategory_id"}
        try:
            r = self._sb_get(table, {"select":"*", "limit":"1"})
            rows = r.json()
            if isinstance(rows, list) and rows:
                return set(rows[0].keys())
        except Exception:
            pass
        return {"id","name","price","stock","description","created_at","updated_at","category_id","subcategory_id"}

    # ---------------- Public API -----------------

    def list_products(self, q: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Безопасный листинг товаров:
         - не полагается на поле category (которого может не быть);
         - делает fallback-попытки с разными наборами полей;
         - при необходимости добавляет category=None для совместимости шаблонов.
        """
        if self._client:
            attempts = [
                {"fields": "id,name,price,stock,created_at", "order": "created_at.desc"},
                {"fields": "id,name,price,stock", "order": None},
                {"fields": "id,name,price", "order": None},
            ]
            last_err: Optional[Exception] = None
            for att in attempts:
                params: List[tuple[str, str]] = [("select", att["fields"]), ("limit", str(limit))]
                if att["order"]:
                    params.append(("order", att["order"]))
                if q:
                    params.append(("name", f"ilike.*{q}*"))
                try:
                    data = self._sb_get("products", params).json()
                    for item in data:
                        item.setdefault("category", None)
                    return data
                except Exception as e:
                    last_err = e
                    continue
            raise RuntimeError(f"Не удалось получить список товаров: {last_err}")
        elif self._pg_conn:
            if q:
                return self._pg_fetch_all(
                    "select id,name,price,stock,created_at from products where name ilike %s order by created_at desc limit %s",
                    (f"%{q}%", limit),
                )
            return self._pg_fetch_all(
                "select id,name,price,stock,created_at from products order by created_at desc limit %s",
                (limit,),
            )
        return []

    def get_product(self, pid: Any) -> Optional[Dict[str, Any]]:
        if self._client:
            rows = self._sb_select("products", "*", id=pid)
            return rows[0] if rows else None
        elif self._pg_conn:
            return self._pg_fetch_one("select * from products where id=%s", (pid,))
        return None

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Устойчивое создание продукта:
        - удаляет пустые значения;
        - при ошибке PGRST204/42703 (нет колонки 'category') пробует обрезать payload по известным колонкам;
        - маппит 'category' -> 'category_id' / 'subcategory_id' если такие колонки существуют.
        """
        payload = {k: v for k, v in (data or {}).items() if v not in (None, "", [])}
        if self._client:
            try:
                return self._sb_insert("products", payload)
            except httpx.HTTPStatusError as e:
                txt = (e.response.text if getattr(e, "response", None) else "") or str(e)
                if getattr(e, "response", None) and e.response.status_code == 400 and ("PGRST204" in txt or "42703" in txt or "column" in txt):
                    allowed = self._infer_columns("products")
                    pruned = {k: v for k, v in payload.items() if k in allowed}
                    if "category" in payload and "category" not in allowed:
                        def _to_int(x):
                            try: return int(str(x))
                            except Exception: return None
                        cat_int = _to_int(payload.get("category"))
                        if cat_int is not None:
                            if "category_id" in allowed:
                                pruned["category_id"] = cat_int
                            elif "subcategory_id" in allowed:
                                pruned["subcategory_id"] = cat_int
                    pruned.pop("category", None)
                    if not pruned:
                        for key in ("name","price","stock","description"):
                            if key in payload:
                                pruned[key] = payload[key]
                    return self._sb_insert("products", pruned)
                raise
        elif self._pg_conn:
            keys = list(payload.keys())
            vals = [payload[k] for k in keys]
            placeholders = ", ".join(["%s"] * len(keys))
            with self._pg_conn.cursor() as cur:
                cur.execute(f"insert into products ({', '.join(keys)}) values ({placeholders}) returning *", vals)
                cols = [d[0] for d in cur.description]
                row = cur.fetchone()
                self._pg_conn.commit()
                return dict(zip(cols, row))
        return {}

    def update_product(self, pid: Any, patch: Dict[str, Any]) -> Dict[str, Any]:
        if self._client:
            return self._sb_update("products", pid, patch)
        elif self._pg_conn:
            return self._pg_update_returning("products", "id", pid, patch)
        return {}

    def delete_product(self, pid: Any) -> bool:
        if self._client:
            self._sb_delete("products", pid)
            return True
        elif self._pg_conn:
            with self._pg_conn.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("delete from products where id=%s", (pid,))
                self._pg_conn.commit()  # type: ignore[union-attr]
            return True
        return False

    # ---- Customers ----

    def list_customers(self, limit: int = 100) -> List[Dict[str, Any]]:
        if self._client:
            r = self._sb_get("users", {"select": "id,telegram_id,name,phone,language,created_at", "order": "created_at.desc", "limit": str(limit)})
            return r.json()
        elif self._pg_conn:
            return self._pg_fetch_all(
                "select id,telegram_id,name,phone,language,created_at from users order by created_at desc limit %s",
                (limit,),
            )
        return []

    # ---- Orders ----

    def list_orders(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        if self._client:
            params: List[tuple[str, str]] = [("select", "id,user_id,status,payment_status,total,created_at"),
                                             ("order", "created_at.desc"),
                                             ("limit", str(limit))]
            if status:
                params.append(("status", f"eq.{status}"))
            return self._sb_get("orders", params).json()
        elif self._pg_conn:
            if status:
                return self._pg_fetch_all(
                    "select id,user_id,status,payment_status,total,created_at from orders where status=%s order by created_at desc limit %s",
                    (status, limit),
                )
            return self._pg_fetch_all(
                "select id,user_id,status,payment_status,total,created_at from orders order by created_at desc limit %s",
                (limit,),
            )
        return []

    def list_orders_filtered(self, status=None, pay=None, date_from=None, date_to=None, limit: int = 500):
        if self._client:
            params: List[tuple[str, str]] = [("select", "id,user_id,status,payment_status,total,created_at"),
                                             ("order", "created_at.desc"),
                                             ("limit", str(limit))]
            if status: params.append(("status", f"eq.{status}"))
            if pay: params.append(("payment_status", f"eq.{pay}"))
            orders = self._sb_get("orders", params).json()
            if date_from or date_to:
                import datetime
                def ok(o):
                    ts = (o.get("created_at", "") or "")[:19]
                    try:
                        dt = datetime.datetime.fromisoformat(ts)
                    except Exception:
                        return True
                    if date_from and dt.date() < date_from: return False
                    if date_to and dt.date() > date_to: return False
                    return True
                orders = [o for o in orders if ok(o)]
            return orders
        elif self._pg_conn:
            clauses, vals = [], []
            if status: clauses.append("status=%s"); vals.append(status)
            if pay: clauses.append("payment_status=%s"); vals.append(pay)
            if date_from: clauses.append("created_at::date >= %s"); vals.append(date_from)
            if date_to: clauses.append("created_at::date <= %s"); vals.append(date_to)
            sql = "select id,user_id,status,payment_status,total,created_at from orders"
            if clauses: sql += " where " + " and ".join(clauses)
            sql += " order by created_at desc limit %s"; vals.append(limit)
            return self._pg_fetch_all(sql, tuple(vals))
        return []

    def get_order(self, oid: Any) -> Optional[Dict[str, Any]]:
        if self._client:
            rows = self._sb_select("orders", "*", id=oid)
            if not rows:
                return None
            order = rows[0]
            items = self._sb_select("order_items", "*", order_id=oid)
            order["items"] = items
            return order
        elif self._pg_conn:
            order = self._pg_fetch_one("select * from orders where id=%s", (oid,))
            if not order: return None
            items = self._pg_fetch_all("select * from order_items where order_id=%s", (oid,))
            order["items"] = items
            return order
        return None

    def update_order_status(self, oid: Any, status: str, payment_status: Optional[str] = None) -> Dict[str, Any]:
        patch = {"status": status}
        if payment_status is not None:
            patch["payment_status"] = payment_status
        if self._client:
            return self._sb_update("orders", oid, patch)
        elif self._pg_conn:
            return self._pg_update_returning("orders", "id", oid, patch)
        return {}

    # ---- Inventory ----

    def list_stock(self, limit: int = 200) -> List[Dict[str, Any]]:
        if self._client:
            r = self._sb_get("products", {"select": "id,name,stock,price,updated_at", "order": "updated_at.desc", "limit": str(limit)})
            return r.json()
        elif self._pg_conn:
            return self._pg_fetch_all(
                "select id,name,stock,price,updated_at from products order by updated_at desc limit %s",
                (limit,),
            )
        return []

    def adjust_stock(self, product_id: Any, delta: int, reason: str = "manual") -> Dict[str, Any]:
        p = self.get_product(product_id)
        if not p: return {}
        new_stock = max(0, int(p.get("stock") or 0) + int(delta))
        upd = self.update_product(product_id, {"stock": new_stock})
        if self._client:
            try:
                self._sb_insert("inventory_movements", {"product_id": product_id, "delta": delta, "reason": reason})
            except Exception:
                pass
        elif self._pg_conn:
            try:
                with self._pg_conn.cursor() as cur:  # type: ignore[union-attr]
                    cur.execute("insert into inventory_movements (product_id, delta, reason) values (%s,%s,%s)",
                                (product_id, delta, reason))
                    self._pg_conn.commit()  # type: ignore[union-attr]
            except Exception:
                pass
        return upd

    # ---- Analytics / Finances (simple) ----

    def kpis(self) -> Dict[str, Any]:
        out = {"orders_today": 0, "revenue_today": 0.0, "products": 0, "customers": 0}
        try:
            if self._client:
                out["products"] = len(self._sb_select("products", "id"))
                out["customers"] = len(self._sb_select("users", "id"))
                import datetime
                today = datetime.date.today().isoformat()
                orders = self._sb_get("orders", {"select": "id,total,created_at,status", "order": "created_at.desc", "limit": "500"}).json()
                for o in orders:
                    if (o.get("created_at", "") or "")[:10] == today:
                        out["orders_today"] += 1
                        out["revenue_today"] += float(o.get("total") or 0.0)
            elif self._pg_conn:
                out["products"] = self._pg_fetch_one("select count(*) as c from products")["c"]  # type: ignore[index]
                out["customers"] = self._pg_fetch_one("select count(*) as c from users")["c"]  # type: ignore[index]
                row = self._pg_fetch_one("select count(*) as c, coalesce(sum(total),0) as s from orders where created_at::date = current_date")
                out["orders_today"], out["revenue_today"] = int(row["c"]), float(row["s"])  # type: ignore[index]
        except Exception:
            pass
        return out

    # ----------------- FILTERED QUERIES -----------------

    def list_products_filtered(self, q=None, category=None, price_min=None, price_max=None, in_stock=None, limit: int = 500):
        if self._client:
            params: List[tuple[str, str]] = [
                ("select", "id,name,price,stock,description,created_at"),
                ("order", "created_at.desc"),
                ("limit", str(limit)),
            ]
            if q:
                params.append(("name", f"ilike.*{q}*"))
            if category:
                # если у тебя есть поле 'category' в таблице — можно добавить фильтр
                # params.append(("category", f"eq.{category}"))
                pass
            if price_min is not None:
                params.append(("price", f"gte.{price_min}"))
            if price_max is not None:
                params.append(("price", f"lte.{price_max}"))
            if in_stock is not None:
                params.append(("stock", "gt.0" if in_stock else "eq.0"))
            return self._sb_get("products", params).json()

        elif self._pg_conn:
            clauses, vals = [], []
            if q: clauses.append("name ilike %s"); vals.append(f"%{q}%")
            if category: clauses.append("category = %s"); vals.append(category)  # если столбца нет — убери
            if price_min is not None: clauses.append("price >= %s"); vals.append(price_min)
            if price_max is not None: clauses.append("price <= %s"); vals.append(price_max)
            if in_stock is not None:
                clauses.append("stock > 0" if in_stock else "stock = 0")
            sql = "select id,name,price,stock,description,created_at from products"
            if clauses:
                sql += " where " + " and ".join(clauses)
            sql += " order by created_at desc limit %s"; vals.append(limit)
            return self._pg_fetch_all(sql, tuple(vals))
        return []

    def list_customers_filtered(self, q=None, date_from=None, date_to=None, limit: int = 1000):
        if self._client:
            users = self._sb_get("users", {"select": "id,telegram_id,name,phone,language,created_at", "order": "created_at.desc", "limit": str(limit)}).json()
            if q:
                ql = (q or "").lower()
                users = [u for u in users if ql in (str(u.get("name", "")).lower() + str(u.get("phone", "")).lower() + str(u.get("telegram_id", "")).lower())]
            if date_from or date_to:
                import datetime
                def ok(u):
                    ts = (u.get("created_at", "") or "")[:19]
                    try:
                        dt = datetime.datetime.fromisoformat(ts)
                    except Exception:
                        return True
                    if date_from and dt.date() < date_from: return False
                    if date_to and dt.date() > date_to: return False
                    return True
                users = [u for u in users if ok(u)]
            return users
        elif self._pg_conn:
            clauses, vals = [], []
            if q:
                clauses.append("(name ilike %s or phone ilike %s or cast(telegram_id as text) ilike %s)")
                vals += [f"%{q}%", f"%{q}%", f"%{q}%"]
            if date_from: clauses.append("created_at::date >= %s"); vals.append(date_from)
            if date_to: clauses.append("created_at::date <= %s"); vals.append(date_to)
            sql = "select id,telegram_id,name,phone,language,created_at from users"
            if clauses: sql += " where " + " and ".join(clauses)
            sql += " order by created_at desc limit %s"; vals.append(limit)
            return self._pg_fetch_all(sql, tuple(vals))
        return []

    # ----------------- ANALYTICS -----------------

    def analytics_period(self, date_from, date_to):
        res = {"orders": 0, "revenue": 0.0, "avg_check": 0.0, "top_categories": [], "funnel": {}, "rfm": []}
        try:
            orders = self.list_orders_filtered(date_from=date_from, date_to=date_to, limit=5000)
            res["orders"] = len(orders)
            res["revenue"] = float(sum(float(o.get("total") or 0) for o in orders))
            res["avg_check"] = (res["revenue"] / res["orders"]) if res["orders"] else 0.0

            stages = ["created", "confirmed", "paid", "shipped", "done", "canceled"]
            funnel = {s: 0 for s in stages}
            for o in orders:
                funnel[o.get("status") or "created"] += 1
            res["funnel"] = funnel

            # Top categories
            if self._client:
                items = self._sb_get("order_items", {"select": "order_id,product_id,quantity,price", "limit": "999999"}).json()
                prods = self._sb_get("products", {"select": "id,category", "limit": "999999"}).json()
                cat = {p["id"]: p.get("category") for p in prods}
            elif self._pg_conn:
                items = self._pg_fetch_all("select order_id, product_id, quantity, price from order_items")
                prows = self._pg_fetch_all("select id, category from products")
                cat = {r["id"]: r.get("category") for r in prows}
            else:
                items, cat = [], {}

            totals_by_cat: Dict[str, float] = {}
            order_ids = {o["id"] for o in orders}
            for it in items:
                if it["order_id"] in order_ids:
                    c = cat.get(it["product_id"]) or "—"
                    totals_by_cat[c] = totals_by_cat.get(c, 0.0) + float(it.get("quantity") or 0) * float(it.get("price") or 0)
            res["top_categories"] = sorted(
                [{"category": k, "revenue": v} for k, v in totals_by_cat.items()],
                key=lambda x: x["revenue"],
                reverse=True
            )[:10]

            # RFM
            import datetime
            by_user = {}
            for o in orders:
                uid = o.get("user_id")
                ts = (o.get("created_at", "") or "")[:19]
                try:
                    dt = datetime.datetime.fromisoformat(ts)
                except Exception:
                    dt = None
                s = float(o.get("total") or 0)
                if uid not in by_user:
                    by_user[uid] = {"last": dt, "count": 1, "sum": s}
                else:
                    by_user[uid]["count"] += 1
                    by_user[uid]["sum"] += s
                    if dt and (by_user[uid]["last"] is None or dt > by_user[uid]["last"]):
                        by_user[uid]["last"] = dt
            today = __import__("datetime").date.today()
            rfm = []
            for uid, v in by_user.items():
                rec = (today - v["last"].date()).days if v["last"] else None
                rfm.append({"user_id": uid, "recency_days": rec, "frequency": v["count"], "monetary": v["sum"]})
            res["rfm"] = sorted(rfm, key=lambda x: (x["recency_days"] or 999999, -x["frequency"], -x["monetary"]))[:200]
        except Exception:
            pass
        return res

    # ----------------- FINANCE -----------------

    def finance_summary(self, date_from=None, date_to=None, commission_rate: float = None):
        commission_rate = commission_rate if commission_rate is not None else float(os.getenv("COMMISSION_RATE", "0.02"))
        orders = self.list_orders_filtered(date_from=date_from, date_to=date_to, limit=100000)
        revenue = float(sum(float(o.get("total") or 0) for o in orders if (o.get("payment_status") in (None, "paid", "refunded"))))
        refunds = float(sum(float(o.get("total") or 0) for o in orders if o.get("payment_status") == "refunded"))
        commissions = revenue * commission_rate
        net = revenue - refunds - commissions
        payouts = 0.0
        try:
            if self._client:
                p = self._sb_get("payouts", {"select": "amount"})
                payouts = sum(float(x.get("amount") or 0) for x in p.json())
            elif self._pg_conn:
                row = self._pg_fetch_one("select coalesce(sum(amount),0) as s from payouts")
                payouts = float(row["s"]) if row else 0.0
        except Exception:
            pass
        return {"revenue": revenue, "refunds": refunds, "commissions": commissions, "net": net, "payouts": payouts}

    # ----------------- SCHEDULED POSTS -----------------

    def list_scheduled_posts(self, limit=500):
        """
        Устойчивый листинг scheduled_posts.
        - Если нет product_id/run_at, делаем select=* и нормализуем поля.
        - Сортируем клиент-сайд по run_at/scheduled_at/created_at.
        """
        if self._client:
            try:
                r = self._sb_get(
                    "scheduled_posts",
                    {"select": "id,product_id,run_at,caption,status", "order": "run_at.asc", "limit": str(limit)},
                )
                return r.json()
            except Exception:
                try:
                    data = self._sb_get("scheduled_posts", {"select": "*", "limit": str(limit)}).json()
                except Exception:
                    return []
                for row in data:
                    pid = None
                    for key in ("product_id", "product", "pid", "item_id"):
                        if key in row:
                            pid = row[key]
                            break
                    row.setdefault("product_id", pid)
                def _key(r):
                    return r.get("run_at") or r.get("scheduled_at") or r.get("created_at") or ""
                data.sort(key=_key)
                return data

        elif self._pg_conn:
            try:
                return self._pg_fetch_all(
                    "select id, product_id, run_at, caption, status from scheduled_posts order by run_at asc limit %s",
                    (limit,),
                )
            except Exception:
                try:
                    rows = self._pg_fetch_all("select * from scheduled_posts limit %s", (limit,))
                except Exception:
                    return []
                for r in rows:
                    pid = None
                    for key in ("product_id", "product", "pid", "item_id"):
                        if key in r:
                            pid = r[key]
                            break
                    r.setdefault("product_id", pid)
                rows.sort(key=lambda r: r.get("run_at") or r.get("scheduled_at") or r.get("created_at") or "")
                return rows
        return []

    def create_scheduled_post(self, product_id, run_at, caption=None):
        """
        Надёжное создание: пробуем разные имена колонки для продукта.
        """
        row_common = {"run_at": str(run_at), "caption": caption, "status": "scheduled"}
        if self._client:
            last_err = None
            for key in ("product_id", "product", "pid", "item_id"):
                try:
                    payload = {**row_common, key: product_id}
                    return self._sb_insert("scheduled_posts", payload)
                except Exception as e:
                    last_err = e
                    continue
            raise RuntimeError(f"Не удалось создать запись в scheduled_posts: нет подходящей колонки для product_id ({last_err})")
        elif self._pg_conn:
            for key in ("product_id", "product", "pid", "item_id"):
                try:
                    return self._pg_insert_returning("scheduled_posts", {**row_common, key: product_id})
                except Exception:
                    continue
            raise RuntimeError("Не удалось создать запись в scheduled_posts: нет подходящей колонки для product_id")
        return {}

    def delete_scheduled_post(self, pid):
        if self._client:
            self._sb_delete("scheduled_posts", pid)
            return True
        elif self._pg_conn:
            with self._pg_conn.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("delete from scheduled_posts where id=%s", (pid,))
                self._pg_conn.commit()  # type: ignore[union-attr]
                return True
        return False

    # Immediate posting (requires TELEGRAM_BOT_TOKEN + POST_CHANNEL_ID)
    def post_product_to_channel(self, product_id: int, caption: str | None = None) -> bool:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        channel = os.getenv("POST_CHANNEL_ID") or os.getenv("TELEGRAM_CHANNEL_ID")
        if not token or not channel:
            return False
        p = self.get_product(product_id)
        if not p:
            return False
        text = caption or f"{p.get('name')} — {p.get('price')}"
        try:
            from telegram import Bot
            bot = Bot(token=token)
            bot.send_message(chat_id=channel, text=text)
            return True
        except Exception:
            return False

    # ----------------- CATEGORIES / SUBCATEGORIES -----------------

    def list_categories(self, limit: int = 5000):
        if self._client:
            return self._sb_get("categories", {"select": "id,name,created_at", "order": "name.asc", "limit": str(limit)}).json()
        elif self._pg_conn:
            return self._pg_fetch_all("select id,name,created_at from categories order by name asc limit %s", (limit,))
        return []

    def get_category(self, cid):
        if self._client:
            rows = self._sb_select("categories", "*", id=cid)
            return rows[0] if rows else None
        elif self._pg_conn:
            return self._pg_fetch_one("select * from categories where id=%s", (cid,))
        return None

    def create_category(self, name: str):
        if self._client:
            return self._sb_insert("categories", {"name": name})
        elif self._pg_conn:
            return self._pg_insert_returning("categories", {"name": name})
        return {}

    def update_category(self, cid, name: str):
        if self._client:
            return self._sb_update("categories", cid, {"name": name})
        elif self._pg_conn:
            return self._pg_update_returning("categories", "id", cid, {"name": name})
        return {}

    def delete_category(self, cid):
        if self._client:
            self._sb_delete("categories", cid)
            return True
        elif self._pg_conn:
            with self._pg_conn.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("delete from categories where id=%s", (cid,))
                self._pg_conn.commit()  # type: ignore[union-attr]
                return True
        return False

    def list_subcategories(self, category_id=None, limit: int = 5000):
        if self._client:
            params: List[tuple[str, str]] = [("select", "id,category_id,name,created_at"), ("order", "name.asc"), ("limit", str(limit))]
            if category_id is not None:
                params.append(("category_id", f"eq.{category_id}"))
            return self._sb_get("subcategories", params).json()
        elif self._pg_conn:
            if category_id is not None:
                return self._pg_fetch_all(
                    "select id,category_id,name,created_at from subcategories where category_id=%s order by name asc limit %s",
                    (category_id, limit),
                )
            return self._pg_fetch_all("select id,category_id,name,created_at from subcategories order by name asc limit %s", (limit,))
        return []

    def create_subcategory(self, category_id: int, name: str):
        row = {"category_id": category_id, "name": name}
        if self._client:
            return self._sb_insert("subcategories", row)
        elif self._pg_conn:
            return self._pg_insert_returning("subcategories", row)
        return {}

    def update_subcategory(self, sid, category_id: int, name: str):
        patch = {"category_id": category_id, "name": name}
        if self._client:
            return self._sb_update("subcategories", sid, patch)
        elif self._pg_conn:
            return self._pg_update_returning("subcategories", "id", sid, patch)
        return {}

    def delete_subcategory(self, sid):
        if self._client:
            self._sb_delete("subcategories", sid)
            return True
        elif self._pg_conn:
            with self._pg_conn.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("delete from subcategories where id=%s", (sid,))
                self._pg_conn.commit()  # type: ignore[union-attr]
                return True
        return False

    # ----------------- TIMESERIES FOR CHARTS -----------------

    def timeseries_revenue_orders(self, days: int = 14):
        import datetime
        end = datetime.date.today()
        start = end - datetime.timedelta(days=days - 1)
        labels = [(start + datetime.timedelta(days=i)).isoformat() for i in range(days)]
        rev = {d: 0.0 for d in labels}
        cnt = {d: 0 for d in labels}
        orders = self.list_orders_filtered(limit=10000)  # фильтруем в Python
        for o in orders:
            d = (o.get("created_at", "") or "")[:10]
            if d in rev:
                rev[d] += float(o.get("total") or 0)
                cnt[d] += 1
        return {"labels": labels, "revenue": [rev[d] for d in labels], "orders": [cnt[d] for d in labels]}

    def products_with_subcat(self, limit: int = 10000):
        rows = self.list_products_filtered(limit=limit)
        subs = self.list_subcategories(limit=5000)
        submap = {s.get("id"): s.get("name") for s in subs}
        for r in rows:
            r["subcategory_name"] = submap.get(r.get("subcategory_id"))
        return rows

    def timeseries_grouped(self, date_from, date_to, group: str = "day"):
        """
        group: day/week/month
        Returns labels and series for revenue & orders between dates inclusive.
        """
        import datetime
        orders = self.list_orders_filtered(date_from=date_from, date_to=date_to, limit=100000)

        def key(dt: datetime.date):
            if group == "week":
                y, w, _ = dt.isocalendar()
                return f"{y}-W{w:02d}"
            if group == "month":
                return f"{dt.year}-{dt.month:02d}"
            return dt.isoformat()

        labels_set: List[str] = []
        rev: Dict[str, float] = {}
        cnt: Dict[str, int] = {}
        cur = date_from
        while cur <= date_to:
            k = key(cur)
            if k not in rev:
                rev[k] = 0.0
                cnt[k] = 0
                labels_set.append(k)
            cur += datetime.timedelta(days=1 if group == "day" else (7 if group == "week" else 31))
        for o in orders:
            ts = (o.get("created_at", "") or "")[:19]
            try:
                dt = __import__("datetime").datetime.fromisoformat(ts).date()
            except Exception:
                continue
            if date_from <= dt <= date_to:
                k = key(dt)
                rev[k] = rev.get(k, 0.0) + float(o.get("total") or 0)
                cnt[k] = cnt.get(k, 0) + 1
                if k not in labels_set:
                    labels_set.append(k)
        labels = sorted(labels_set)
        return {"labels": labels, "revenue": [rev.get(k, 0.0) for k in labels], "orders": [cnt.get(k, 0) for k in labels]}

    def top_products(self, date_from, date_to, limit: int = 10):
        orders = self.list_orders_filtered(date_from=date_from, date_to=date_to, limit=100000)
        oids = {o["id"] for o in orders}
        if self._client:
            items = self._sb_get("order_items", {"select": "order_id,product_id,quantity,price", "limit": "999999"}).json()
            prods = self._sb_get("products", {"select": "id,name", "limit": "999999"}).json()
            names = {p["id"]: p.get("name") for p in prods}
        elif self._pg_conn:
            items = self._pg_fetch_all("select order_id, product_id, quantity, price from order_items")
            prows = self._pg_fetch_all("select id, name from products")
            names = {r["id"]: r["name"] for r in prows}
        else:
            items, names = [], {}
        totals: Dict[Any, float] = {}
        for it in items:
            if it["order_id"] in oids:
                pid = it["product_id"]
                totals[pid] = totals.get(pid, 0.0) + float(it.get("quantity") or 0) * float(it.get("price") or 0)
        arr = [{"product_id": pid, "name": names.get(pid) or str(pid), "revenue": v} for pid, v in totals.items()]
        arr.sort(key=lambda x: x["revenue"], reverse=True)
        return arr[:limit]

    def count_open_orders(self):
        """Count orders that are not done/canceled."""
        orders = self.list_orders_filtered(limit=100000)
        open_status = {"created", "confirmed", "paid", "shipped"}
        return sum(1 for o in orders if (o.get("status") or "created") in open_status)
