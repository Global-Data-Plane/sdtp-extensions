
from typing import Literal
from sdtp import BaseTableSchema, register_table_schema

class DuckDBTableSchema(BaseTableSchema):
    """
    The schema specification for a DuckDBTable.
    Acts as the direct serialization blueprint and build instructions.
    """
    type: Literal["DuckDBTable"]
    table_name: str
    db_path: str

register_table_schema("DuckDBTable", DuckDBTableSchema)
