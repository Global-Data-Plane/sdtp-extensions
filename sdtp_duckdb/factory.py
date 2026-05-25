# sdtp_duckdb/factory.py

from sdtp.sdtp_table_factory import SDMLTableFactory, TableBuilder
from .table import DuckDBTable




class DuckDBTableFactory(SDMLTableFactory):
    @classmethod
    def build_table(cls, spec, *args, **kwargs):
        # We can perform our own local structural check first to be safe
        if "db_path" not in spec or "table_name" not in spec:
            raise ValueError("DuckDBTable requires both 'db_path' and 'table_name'")
            
        # Bypass or execute core mapping cleanly
        return DuckDBTable(
            table_name=spec['table_name'],
            schema=spec['schema'],
            db_path=spec['db_path']
        )

# Register the factory class into your global builder
TableBuilder.register_factory_class('DuckDBTable', DuckDBTableFactory, locked=True)