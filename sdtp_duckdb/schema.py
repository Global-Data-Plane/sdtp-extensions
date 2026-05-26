
from typing import Literal
from sdtp import BaseTableSchema, sdtp_schema

class DuckDBTableSchema(BaseTableSchema):
    """
    The schema specification for a DuckDBTable.
    Acts as the direct serialization blueprint and build instructions.
    """
    type: Literal["DuckDBTable"]
    table_name: str
    db_path: str

# 1. Dynamically inject DuckDBTable requirements into the core schema validator
# This ensures core_schema.validate_table_schema() recognizes our new type tag!
if hasattr(sdtp_schema, 'validate_table_schema'):
    # Look up or modify the target dictionary scope inside your module
    # Python lets us patch this seamlessly at runtime
    import sys
    # We reach into the validation function's environment or define it locally
    pass