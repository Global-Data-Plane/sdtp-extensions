# How to Build an SDTP Database Extension
This guide walks through implementing a custom database adapter extension for the Simple Data Transport Protocol (SDTP). By building an extension using our Dynamic Plugin Architecture, your database adapter can remain entirely independent of the core library, allowing it to run within its own isolated, lightweight containers.

## What is An Data Plane Extension?
The Data Plane  is designed as a standard representation and interchange format for all forms of tabular data.  A Data Plane Table is simply an object that conforms to the Simple Data Markup Language Table API., and so writing one-off tables is very simple, just by following the recipe in https://global-data-plane.github.io/sdtp/sdml_reference/:
```
class MyTable(SDMLTable):
    def all_values(self, column_name):
        # Return all distinct values in the specified column

    def get_column(self, column_name: str):
        # Return all values (including duplicates) in the specified column

    def range_spec(self, column_name: str):
        # Return [min, max] for the specified column

    def _get_filtered_rows_from_filter(self, filter=None):
        # Return all rows matching the filter (full rows, schema order)

    def to_dictionary(self):
        # Return the table as a Python dictionary

    def to_json(self):
        # Return the table as a JSON-serializable object
```
Even simpler versions are available by subclassing `RowTable` and simply providing a `get_rows()` function.

However,  it's also desirable to write new classes of table.  For example, writing a general class of table for SQLite databases, and then simply instantiating it to point to a specific database.  Such a class is an _extension_ of the Data Plane.  In order to build an extension, three things are required:
1. The code for the extension, which is typically implemented by subclassing `SDMLTable` and supplying the appropriate methods
2. Writing a `TableFactory` class for the extension, which takes in a JSON description of an instance of the class and produces an instance of it.  This should subclass `SDMLTableFactory` and implement a class method `build_table(cls, spec, *args, **kwargs)`
3. Writing a spec for the JSON description of the instance.  This shoulkd subclass `BaseTableSchema` and simply provide the information required for an instance, which _must_ include the table type as `type`, the name of the instance in `table_name`, and then any type-specific information.  For example, a `DuckDBTable` contains a path to a database file.

## Extension Architecture Overview
An SDTP database extension is housed as a dedicated submodule folder inside the sdtp_extensions repository and consists of three core structural files:

schema.py: Defines the wire-format build instructions and translates native database engine types to universal SDML types.

table.py: Subclasses SDMLTable to handle engine connections and query execution.

factory.py: Implements the SDMLTableFactory to instantiate the table and register the plugin automatically via Python Entry Points on boot.

### Step 1: Define the Instruction Schema (schema.py)
Your extension requires a declarative dictionary blueprint that acts as the minimal set of build instructions for your engine. Inherit from the core framework's `BaseTableSchema`.

```
from typing import Literal
from sdtp import BaseTableSchema, register_table_schema

class MyDatabaseTableSchema(BaseTableSchema):
    """
    The structural specification required to initialize this extension.
    """
    type: Literal["MyDatabaseTable"]
    table_name: str
    db_path: str  # Or any necessary connection string parameters

register_table_schema("MyDatabaseTable", MyDatabaseTableSchema)
```
⚠️ Important: When mapping your database's internal primitives to SDML types, you must strictly map integers and floats to "number", and times to "timeofday" to ensure validation passes.

### Step 2: Implement the Table Type (table.py)
Subclass `BaseSQLTable` for relational engines. Rather than fetching large blocks of rows into memory, implement the database execution hook and metadata methods so projection and predicate handling stay in the shared SQL base class.
```
from sdtp import BaseSQLTable, InvalidDataException

class MyDatabaseTable(BaseSQLTable):
    def __init__(self, table_name: str, schema: list, db_path: str, spec=None):
        super().__init__(schema, table_name)
        self.spec = spec
        # Initialize your database connection here...

    def _execute_sql(self, query: str, params: list | None = None) -> list:
        # Execute query with bound positional parameters and return list[list].
        ...

    def all_values(self, column_name: str) -> list:
        # Delegate DISTINCT and ORDER BY calculation straight to your SQL engine
        ...

    def range_spec(self, column_name: str) -> list:
        # Compute MIN() and MAX() inside the database engine
        ...

    def _compile_dialect_operator(self, operator: str, column: str, spec: dict) -> tuple[str, list]:
        # Optionally handle engine-specific operators such as REGEX_MATCH.
        return "", []
```
### Step 3: Create the Factory and Registry Hook (factory.py)
Implement an SDMLTableFactory that parses incoming setup instructions and instantiates your runtime engine table. At the bottom of this file, register your class into the core framework's TableBuilder.
```
from sdtp import InvalidDataException, SDMLTableFactory, TableBuilder
from .schema import MyDatabaseTableSchema
from .table import MyDatabaseTable

class MyDatabaseTableFactory(SDMLTableFactory):
    @classmethod
    def build_table(cls, spec, *args, **kwargs):
        try:
            validated_spec = MyDatabaseTableSchema.model_validate(spec)
        except Exception as e:
            raise InvalidDataException(f"MyDatabaseTable configuration validation failed: {e}") from e

        return MyDatabaseTable(
            table_name=validated_spec.table_name,
            schema=[column.model_dump() for column in validated_spec.schema_fields],
            db_path=validated_spec.db_path,
            spec=validated_spec,
        )

# This line registers your extension automatically when Python discovers your package!
TableBuilder.register_factory_class('MyDatabaseTable', MyDatabaseTableFactory, locked=True)
```
### Step 4: Register the Extension Point (pyproject.toml)
Your extension registers itself with the core runtime engine using a standard Python entry-point. Add your new table definition block under the root pyproject.toml file of the extensions project:
```
[project]
name = "sdtp-extensions"
version = "0.1.0"
dependencies = [
    "sdtp",
    "mydatabase-driver"
]

[project.entry-points."sdtp.tables"]
MyDatabaseTable = "sdtp_mydatabase.factory:MyDatabaseTableFactory"
```
