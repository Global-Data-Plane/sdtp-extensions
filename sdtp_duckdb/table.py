import duckdb
from sdtp import BaseSQLTable, InvalidDataException

class DuckDBTable(BaseSQLTable):
    def __init__(self, table_name: str, schema: list, db_path: str, spec=None):
        super().__init__(schema, table_name)
        self.spec = spec
        self.db_path = db_path
        try:
            self.conn = duckdb.connect(self.db_path, read_only=True)
        except Exception as e:
            raise InvalidDataException(f"DuckDB connection failed: {e}")

    def _execute_sql(self, query: str, params: list|None = None) -> list:
        try:
            return [list(row) for row in self.conn.execute(query, params or []).fetchall()]
        except Exception as e:
            raise InvalidDataException(f"DuckDB query failed: {e}") from e

    def _compile_dialect_operator(self, operator: str, column: str, spec: dict) -> tuple[str, list]:
        if operator == "REGEX_MATCH":
            return f"REGEXP_MATCHES({column}, ?)", [spec.get("expression")]
        return "", []

    # Simple metadata aggregation redirects
    def all_values(self, column_name: str) -> list:
        self._validate_column(column_name)
        return [r[0] for r in self._execute_sql(f"SELECT DISTINCT {column_name} FROM {self.table_name} ORDER BY {column_name} ASC")]

    def range_spec(self, column_name: str) -> list:
        self._validate_column(column_name)
        rows = self._execute_sql(f"SELECT MIN({column_name}), MAX({column_name}) FROM {self.table_name}")
        return [] if not rows or rows[0][0] is None else [rows[0][0], rows[0][1]]
