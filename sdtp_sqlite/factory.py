from sdtp import SDMLTableFactory, TableBuilder, InvalidDataException
from .schema import SQLiteTableSchema
from .table import SQLiteTable

class SQLiteTableFactory(SDMLTableFactory):
    @classmethod
    def build_table(cls, spec, *args, **kwargs):
        try:
            validated_spec = SQLiteTableSchema.model_validate(spec)
        except Exception as e:
            raise InvalidDataException(f"SQLiteTable configuration validation failed: {e}") from e

        return SQLiteTable(
            table_name=validated_spec.table_name,
            schema=[column.model_dump() for column in validated_spec.schema_fields],
            db_path=validated_spec.db_path,
            spec=validated_spec,
        )

TableBuilder.register_factory_class('SQLiteTable', SQLiteTableFactory, locked=True)
