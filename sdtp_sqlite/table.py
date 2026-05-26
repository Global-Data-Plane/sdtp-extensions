import sqlite3
import re
from sdtp import BaseSQLTable, InvalidDataException

class SQLiteTable(BaseSQLTable):
    def __init__(self, table_name: str, schema: list, db_path: str, spec=None):
        super().__init__(schema, table_name)
        self.spec = spec
        self.db_path = db_path
        try:
            self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            self.conn.create_function("REGEXP", 2, lambda expr, item: item is not None and re.search(expr, str(item)) is not None)
        except Exception as e:
            raise InvalidDataException(f"SQLite connection failed: {e}")

    def _execute_sql(self, query: str, params: list|None = None) -> list:
        try:
            return [list(row) for row in self.conn.execute(query, params or []).fetchall()]
        except Exception as e:
            raise InvalidDataException(f"SQLite query failed: {e}") from e

    def _compile_dialect_operator(self, operator: str, column: str, spec: dict) -> tuple[str, list]:
        if operator == "REGEX_MATCH":
            return f"{column} REGEXP ?", [spec.get("expression")]
        return "", []

    def all_values(self, column_name: str) -> list:
        self._validate_column(column_name)
        return [r[0] for r in self._execute_sql(f"SELECT DISTINCT {column_name} FROM {self.table_name} ORDER BY {column_name} ASC")]

    def range_spec(self, column_name: str) -> list:
        self._validate_column(column_name)
        rows = self._execute_sql(f"SELECT MIN({column_name}), MAX({column_name}) FROM {self.table_name}")
        return [] if not rows or rows[0][0] is None else [rows[0][0], rows[0][1]]
