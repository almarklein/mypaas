"""
Implementation of a transactional database for storage and retrieval of dict items.
"""

import json
import sqlite3


json_encode = json.JSONEncoder(ensure_ascii=True).encode
json_decode = json.JSONDecoder().decode


# Notes:
#
# * Setting isolation_level to None turns on autocommit mode. We need to do
#   this to prevent Python from issuing BEGIN before DML statements.
# * Using a connection object as a context manager auto-commits/rollbacks a
#   transaction.
# * We should close cursos objects as soon as possible, because they can hold
#   back waiting writers. That's why we dont have an iterator.
# * MongoDB's approach of db.tablename.push() looks nice, but I don't like
#   the "magical" side of it, especially since the db does not know its tables.
#   Also it makes the code more complex, introduces an extra class, and
#   increases the risk of preventing a db from closing (by holding a table).


# todo: Spin this out? It would need some more:
# - delete objects
# - other management tasks, like dropping tables, re-indexing etc.


class ItemDB:
    """ A transactional database for storage and retrieval of dict items.

    The items in the database can be any JSON serializable dictionary.
    Indices can be defined for specific fields to enable selecting items
    based on these values. Indices can be marked as unique to make a field
    mandatory and *identify* items based on that field.

    This class makes use SQLite, resulting in a fast and reliable
    (ACID-compliant) system suitable for heavy duty work (e.g. in a web
    server). Though with a simple API, and the flexibility to store
    items with arbitrary fields, and add indices when needed.

    Example:

        # Open the database
        db = ItemDB(filename)

        # Make sure that it has a "persons" table with appropriate indices
        db.ensure("persons", "!name", "age")

        # Insert a few items
        with db:
            db.put("persons", dict(name="Jane", age=22))
            db.put("persons", dict(name="John", age=20, fav_number=7))
            db.put("persons", dict(name="Guido"))

        # Show some stats
        print(db.count_all("persons"), "persons in the database")
        print(db.select("persons", "age > 10"))
        print(db.select_one("persons", "name = ?", "John"))

        # Update one person
        with db:
            db.put("persons", dict(name="John", age=21, fav_number=8))

        # When done - also consider using ``with closing(db)``
        db.close()

    One can see how items are added that include additional fields, or
    do not have all fields (Guido does not have an age). The ``name`` field
    is mandatory though, indicated by the exclamation mark ("!"). It also means
    that the ``name`` field is unique. Putting an item with an existing name
    will update/overwrite it (as in the second case where John is stored).

    Indices can be added at any time, but note that it will exist forever.
    Further, a unique index (prefixed with "!") can only be created when the
    database is opened for the first time.

    As you see in the example, ``put`` can only be used inside a context
    (a with-statement). A context represents a transaction: only one
    transaction can be done at a given time, and a transaction either
    completely succeeds or is canceled as a whole. For example:

        # The change to John will be "rolled back".
        with db:
            db.put("persons", dict(name="John", age=99))
            ...
            raise RuntimeError()

        # The transaction is "atomic". This works across processes
        # (even across Docker containers using the same db in a shared folder).
        with db:
            john = db.select_one("persons", "name = ?", "John")
            john["fav_number"] += 1
            # Without a context, Johns favourite number could be changed from
            # somewhere else and we would wrongly overwrite that change.
            db.put("persons", john)

    On terminology:

    * A "table" is what is also called "table" in SQL databases, a
      "collection" in MongoDB, and an "object store" in IndexedDB.
    * An "item" is what is called a "row" in SQL databases, a "document"
      in MongoDB, and an "object" in IndexedDB.

    """

    def __init__(self, filename):
        self._conn = sqlite3.connect(
            filename, timeout=60, isolation_level=None, check_same_thread=False
        )
        self._cur = None
        self._indices_per_table = {}

    def __enter__(self):
        if self._cur is not None:
            raise IOError("Already in a transaction")
        self._cur = self._conn.cursor()
        self._cur.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(self, type, value, traceback):
        self._cur.close()
        self._cur = None
        if value:
            self._conn.rollback()
        else:
            self._conn.commit()

    def __del__(self):
        self._conn.close()

    def close(self):
        """ Close the database connection. This will be automatically
        called when the instance is deleted. But since it can be held
        e.g. in a traceback, consider using ``with closing(db):``.
        """
        self._conn.close()

    def get_table_info(self):
        """ Return a list with a tuple (table_name, count, indices) for
        each table present in the database (sorted by table name).
        """
        tables = []
        # Get table names
        cur = self._conn.cursor()
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            table_names = {x[0] for x in cur}
        finally:
            cur.close()
        # Get info on each table
        for table_name in sorted(table_names):
            indices = sorted(self.get_indices(table_name))
            count = self.count_all(table_name)
            tables.append((table_name, count, indices))
        return tables

    def get_indices(self, table_name):
        """ Get a set of indices for the given table. Names prefixed with "!"
        represent fields that are required and unique. Raises KeyError if the
        table does not exist.
        """
        # Use cached?
        try:
            return self._indices_per_table[table_name]
        except KeyError:
            pass
        except TypeError:
            raise TypeError("Table name must be str.")

        # Check table name
        if not isinstance(table_name, str):
            raise TypeError("Table name must be str.")
        elif not table_name.isidentifier():
            raise ValueError("Table name must be an identifier.")

        # Get columns for the table (cid, name, type, notnull, default, pk)
        cur = self._conn.cursor()
        try:
            cur.execute(f"PRAGMA table_info('{table_name}');")
            found_indices = {(x[3] * "!" + x[1]) for x in cur}  # includes !_ob
        finally:
            cur.close()

        # Cache and return - or fail
        if found_indices:
            found_indices.difference_update({"!_ob", "_ob"})
            self._indices_per_table[table_name] = found_indices
            return found_indices
        else:
            raise KeyError(f"Table {table_name} not present, maybe ensure() it first?")

    def ensure(self, table_name, *indices):
        """ Ensure that the given table exists and has the given indices.
        This method is designed to return as quickly as possible when the table
        is already ok. Returns the databse object, so calls to this method
        can be stacked.
        """

        if not all(isinstance(x, str) for x in indices):
            raise TypeError("Indices must be str")

        # Select missing indices
        try:
            missing_indices = set(indices).difference(self.get_indices(table_name))
        except KeyError:
            missing_indices = {"--table--"}

        # Do we need to do some work?
        if missing_indices:
            with self:
                # Make sure the table is complete
                self._ensure_table(table_name, indices)
                self._indices_per_table.pop(table_name, None)  # let it refresh
                # Update values that already had a value for the just added columns/indices
                items = [
                    item
                    for item in self.select_all(table_name)
                    if any(x.lstrip("!") in item for x in missing_indices)
                ]
                self.put(table_name, *items)

        return self  # allow stacking this function

    def _ensure_table(self, table_name, indices):
        """ Slow version to ensure table.
        """

        cur = self._cur

        # Check the column names
        for fieldname in indices:
            key = fieldname.lstrip("!")
            if not key.isidentifier():
                raise ValueError("Column names must be identifiers.")
            elif key == "_ob":
                raise IndexError("Column names cannot be '_ob'.")

        # Ensure the table.
        # If there is one unique key, make it a the primary key and omit rowid.
        # This results in smaller and faster databases.
        text = f"CREATE TABLE IF NOT EXISTS {table_name} (_ob TEXT NOT NULL"
        unique_keys = sorted(x.lstrip("!") for x in indices if x.startswith("!"))
        if len(unique_keys) == 1:
            text += f", {unique_keys[0]} NOT NULL PRIMARY KEY) WITHOUT ROWID;"
        else:
            for key in unique_keys:
                text += f", {key} NOT NULL UNIQUE"
            text += ");"
        cur.execute(text)

        # Ensure the columns and indices
        cur.execute(f"PRAGMA table_info('{table_name}');")
        found_indices = {(x[3] * "!" + x[1]) for x in cur}

        for fieldname in sorted(indices):
            key = fieldname.lstrip("!")
            if fieldname not in found_indices:
                if fieldname.startswith("!"):
                    raise IndexError(
                        f"Cannot add unique index {fieldname!r} after db creation."
                    )
                elif fieldname in {x.lstrip("!") for x in found_indices}:
                    raise IndexError(f"Given index {fieldname!r} should be unique.")
                cur.execute(f"ALTER TABLE {table_name} ADD {key};")
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{key} ON {table_name} ({key})"
            )

    def count_all(self, table_name):
        """ Get the total number of items in the given table.
        """
        self.get_indices(table_name)  # Fail with KeyError for invalid table name
        cur = self._conn.cursor()
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cur.fetchone()[0]
        finally:
            cur.close()

    def count(self, table_name, query=None, *args):
        """ Get the number of items in the given table that match the given query.

        Can raise KeyError if an invalid table is given, IndexError if an
        invalid field is used in the query, or sqlite3.OperationalError for
        an invalid query.
        """
        self.get_indices(table_name)  # Fail with KeyError for invalid table name
        cur = self._conn.cursor()
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {query}", args)
            return cur.fetchone()[0]
        except sqlite3.OperationalError as err:
            if "no such column" in str(err).lower():
                raise IndexError(str(err))
            raise err
        finally:
            cur.close()

    def select_all(self, table_name):
        """ Get all items in the given table.
        """
        self.get_indices(table_name)  # Fail with KeyError for invalid table name
        cur = self._conn.cursor()
        try:
            cur.execute(f"SELECT _ob FROM {table_name}")
            return [json_decode(x[0]) for x in cur]
        finally:
            cur.close()

    def select(self, table_name, query=None, *args):
        """ Get the items in the given table that match the given query.

        The query follows SQLite syntax and can only include indexed fields.
        Therefore the query is always fast (which is why this method is called
        select, and not search). To filter items bases on non-indexed fields,
        use a list comprehension, e.g.:

            items = db.select("table_name", ...)  # or select_all("table_name")
            items = [i for i in items if i["value"] > 100]

        Can raise KeyError if an invalid table is given, IndexError if an
        invalid field is used in the query, or sqlite3.OperationalError for
        an invalid query.
        """
        self.get_indices(table_name)  # Fail with KeyError for invalid table name
        # It is tempting to make this a generator, but also dangerous because
        # the cursor might not be closed if the generator is stored somewhere
        # and not run through the end.
        cur = self._conn.cursor()
        try:
            cur.execute(f"SELECT _ob FROM {table_name} WHERE {query}", args)
            return [json_decode(x[0]) for x in cur]
        except sqlite3.OperationalError as err:
            if "no such column" in str(err).lower():
                raise IndexError(str(err))
            raise err
        finally:
            cur.close()

    def select_one(self, table_name, query, *args):
        """ Get the first item in the given table that match the given query.
        Returns None if there was no match.
        """
        items = self.select(table_name, query, *args)
        return items[0] if items else None

    def put(self, table_name, *items):
        """ Put one or more items into the given table.

        Can raise KeyError if an invalid table is given, IOError if not
        used within a transaction, TypeError if an item is not a (JSON
        serializable) dict, or IndexError if an item does not have a
        required field.
        """
        cur = self._cur
        if cur is None:
            raise IOError("Can only put() under a context.")

        # Get indices - fail with KeyError for invalid table name
        indices = self.get_indices(table_name)

        for item in items:
            if not isinstance(item, dict):
                raise TypeError("Expecing each item to be a dict")

            row_keys = "_ob"
            row_plac = "?"
            row_vals = [json_encode(item)]  # Can raise TypeError
            for fieldname in indices:
                key = fieldname.lstrip("!")
                if key in item:
                    row_keys += ", " + key
                    row_plac += ", ?"
                    row_vals.append(item[key])
                elif fieldname.startswith("!"):
                    raise IndexError(f"Item does not have required field {key!r}")

            cur.execute(
                f"INSERT OR REPLACE INTO {table_name} ({row_keys}) VALUES ({row_plac})",
                row_vals,
            )

    def put_one(self, table_name, **item):
        """ Put an item into the given table using kwargs.
        """
        self.put(table_name, item)
