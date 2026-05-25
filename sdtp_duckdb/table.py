import duckdb
from sdtp.sdtp_table import SDMLTable, RowTable, ALLOWED_FILTERED_ROW_RESULT_FORMATS, DEFAULT_FILTERED_ROW_RESULT_FORMAT
from sdtp.sdtp_utils import InvalidDataException
from sdtp.sdtp_filter import SDQLFilter

class DuckDBTable(SDMLTable):
    """
    An optimized, high-performance SDMLTable implementation backed by DuckDB.
    Translates your SDQL filter AST directly into native, parameterized SQL 
    predicates and projections.
    """

    def __init__(self, table_name: str, schema: list, db_path: str):
        super().__init__(schema)
        self.table_name = table_name
        self.db_path = db_path
        
        try:
            # Open the connection in read_only mode to permit concurrent scaling
            self.conn = duckdb.connect(self.db_path, read_only=True)
        except Exception as e:
            raise InvalidDataException(f"Failed to connect to DuckDB file at {db_path}: {e}")

    def _validate_column(self, column_name: str):
        """Ensures safety against SQL injection by checking column legitimacy."""
        if column_name not in self.column_names():
            raise InvalidDataException(f"'{column_name}' is not a valid column of table '{self.table_name}'")

    def _run_query(self, query: str, params: list = None) -> list:
        try:
            return self.conn.execute(query, params or []).fetchall()
        except Exception as e:
            raise InvalidDataException(f"DuckDB SQL execution failure: {e}")

    def all_values(self, column_name: str) -> list:
        self._validate_column(column_name)
        query = f"SELECT DISTINCT {column_name} FROM {self.table_name} ORDER BY {column_name} ASC"
        return [row[0] for row in self._run_query(query)]

    def get_column(self, column_name: str) -> list:
        self._validate_column(column_name)
        query = f"SELECT {column_name} FROM {self.table_name}"
        return [row[0] for row in self._run_query(query)]

    def range_spec(self, column_name: str) -> list:
        self._validate_column(column_name)
        query = f"SELECT MIN({column_name}), MAX({column_name}) FROM {self.table_name}"
        rows = self._run_query(query)
        return [] if not rows or rows[0][0] is None else [rows[0][0], rows[0][1]]

    def _compile_filter_spec(self, spec: dict) -> tuple[str, list]:
        """
        Recursively compiles your SDQL filter specification dictionary into 
        a parameterized SQL string and matching bind variables.
        """
        if not isinstance(spec, dict) or "operator" not in spec:
            return "", []

        operator = spec["operator"]

        # 1. Handle Set-Quantifier Compound Operators (ALL, ANY, NONE)
        null_arguments = {
            "ALL": "1=1",   # Vacuously True: not (False in []) -> True
            "ANY": "1=0",   # False: True in [] -> False
            "NONE": "1=1"   # True: not (True in []) -> True
        }

        if operator in ("ALL", "ANY", "NONE"):
            arguments = spec.get("arguments", [])
            if not arguments:
                # Returns the SQL boolean expression along with an empty bind parameter list
                return null_arguments[operator], []

            sub_clauses, params = [], []
            for sub_spec in arguments:
                clause, sub_params = self._compile_filter_spec(sub_spec)
                if clause:
                    sub_clauses.append(f"({clause})")
                    params.extend(sub_params)

            if not sub_clauses:
                return "", []

            if operator == "ALL":
                return " AND ".join(sub_clauses), params
            elif operator == "ANY":
                return " OR ".join(sub_clauses), params
            elif operator == "NONE":
                # Translates NONE(f1, f2) into NOT ((f1) OR (f2))
                combined = " OR ".join(sub_clauses)
                return f"NOT ({combined})", params

        # 2. Handle Atomic Column Operators
        column = spec.get("column")
        if not column:
            return "", []
        self._validate_column(column)

        # Handle IN_LIST operator (also captures EQ and NEQ variants natively)
        if operator == "IN_LIST":
            values = spec.get("values", [])
            if not values:
                return "1=0", []  # An empty list match condition is always false
            if len(values) == 1:
                return f"{column} = ?", [values[0]]
            placeholders = ", ".join(["?"] * len(values))
            return f"{column} IN ({placeholders})", list(values)

        # Handle Standard Mathematical Comparisons
        if operator in ("GE", "GT", "LE", "LT"):
            sql_ops = {"GE": ">=", "GT": ">", "LE": "<=", "LT": "<"}
            return f"{column} {sql_ops[operator]} ?", [spec.get("value")]

        # Handle Text Pattern Matching using DuckDB's POSIX regex syntax
        if operator == "REGEX_MATCH":
            return f"REGEXP_MATCHES({column}, ?)", [spec.get("expression")]

        return "", []

    def get_filtered_rows(self, filter_spec=None, columns=None, format=DEFAULT_FILTERED_ROW_RESULT_FORMAT):
        """
        Overrides the master query entrypoint to pipe full projection pushdowns 
        and compiled filter predicates down into DuckDB concurrently.
        """
        if format is None:
            format = DEFAULT_FILTERED_ROW_RESULT_FORMAT
        if format not in ALLOWED_FILTERED_ROW_RESULT_FORMATS:
            raise InvalidDataException(f"Format value must be one of {ALLOWED_FILTERED_ROW_RESULT_FORMATS}")

        # Step 1: Execute Projection Pushdown
        requested_columns = columns if columns else self.column_names()
        select_clause = ", ".join(requested_columns)

        # Step 2: Extract & Compile the Predicate Filter Tree
        where_clause, params = "", []
        if filter_spec:
            # Safely handle both incoming raw dictionaries or fully instantiated Pydantic Filters
            normalized_spec = filter_spec.to_filter_spec() if isinstance(filter_spec, SDQLFilter) else filter_spec
            
            # Note: Your core expand_in_range_spec converts an IN_RANGE shorthand 
            # down to clean ALL/comparison primitives, so handle it immediately
            if normalized_spec.get("operator") == "IN_RANGE":
                from sdtp.sdtp_filter import expand_in_range_spec
                normalized_spec = expand_in_range_spec(normalized_spec)
                
            where_clause, params = self._compile_filter_spec(normalized_spec)

        # Assemble the clean query statement
        query = f"SELECT {select_clause} FROM {self.table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        # Step 3: Run the optimized engine computation scan
        raw_rows = [list(row) for row in self._run_query(query, params)]

        # Step 4: Map cleanly to requested structural transport response
        if format == 'list':
            return raw_rows
            
        if format == 'dict':
            return [{requested_columns[i]: row[i] for i in range(len(requested_columns))} for row in raw_rows]

        # Format is 'sdml': generate a targeted RowTable on the dynamically sliced schema
        column_indices = [self.column_names().index(col) for col in requested_columns]
        projected_schema = [self.schema[i] for i in column_indices]
        return RowTable(projected_schema, raw_rows)

    def _get_filtered_rows_from_filter(self, filter=None):
        """Satisfies fallback requirement, though short-circuited by get_filtered_rows upstream."""
        spec = filter.to_filter_spec() if filter else None
        query = f"SELECT * FROM {self.table_name}"
        where_clause, params = self._compile_filter_spec(spec)
        if where_clause:
            query += f" WHERE {where_clause}"
        return [list(row) for row in self._run_query(query, params)]