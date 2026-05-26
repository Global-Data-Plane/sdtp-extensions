from sdtp import InvalidDataException, SDMLTableFactory, TableBuilder
from .schema import DuckDBTableSchema
from .table import DuckDBTable


class DuckDBTableFactory(SDMLTableFactory):
    @classmethod
    def build_table(cls, spec, *args, **kwargs):
        try:
            validated_spec = DuckDBTableSchema.model_validate(spec)
        except Exception as e:
            raise InvalidDataException(f"DuckDBTable configuration validation failed: {e}") from e

        return DuckDBTable(
            table_name=validated_spec.table_name,
            schema=[column.model_dump() for column in validated_spec.schema_fields],
            db_path=validated_spec.db_path,
            spec=validated_spec,
        )

TableBuilder.register_factory_class('DuckDBTable', DuckDBTableFactory, locked=True)
