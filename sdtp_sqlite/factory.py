from sdtp import SDMLTableFactory, TableBuilder, _make_table_schema, InvalidDataException
from .table import SQLiteTable

class SQLiteTableFactory(SDMLTableFactory):
    @classmethod
    def build_table(cls, spec, *args, **kwargs):
        cls.check_table_type(spec["type"])
        
        if "db_path" not in spec or "table_name" not in spec:
            raise InvalidDataException("SQLiteTable requires both 'db_path' and 'table_name'")
            
        schema_spec = _make_table_schema(spec)
        
        return SQLiteTable(
            table_name=spec['table_name'],
            schema=schema_spec['schema'],
            db_path=spec['db_path']
        )

# Automatically hook into the core discovery engine on boot!
TableBuilder.register_factory_class('SQLiteTable', SQLiteTableFactory, locked=True)