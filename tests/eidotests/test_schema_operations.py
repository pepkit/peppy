from yaml import safe_load

from peppy.eido.schema import read_schema


class TestSchemaReading:
    def test_imports_file_schema(self, schema_imports_file_path):
        s = read_schema(schema_imports_file_path)
        assert isinstance(s, list)
        assert len(s) == 2

    def test_imports_dict_schema(self, schema_imports_file_path):
        with open(schema_imports_file_path, "r") as f:
            s = read_schema(safe_load(f))
        assert isinstance(s, list)
        assert len(s) == 2
