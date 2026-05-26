from typing import Literal
from sdtp import BaseTableSchema

class SQLiteTableSchema(BaseTableSchema):
    """
    The structural specification required to initialize a SQLiteTable.
    """
    type: Literal["SQLiteTable"]
    table_name: str
    db_path: str

# Map SQLite type affinities to universal SDML types
SQLITE_TO_SDML_TYPES = {
    "INTEGER": "number",
    "REAL": "number",
    "NUMERIC": "number",
    "FLOAT": "number",
    "DOUBLE": "number",
    "INT": "number",
    "TEXT": "string",
    "VARCHAR": "string",
    "CLOB": "string",
    "BLOB": "string",
    "BOOLEAN": "boolean",
    "DATE": "date",
    "DATETIME": "datetime",
    "TIMESTAMP": "datetime"
}