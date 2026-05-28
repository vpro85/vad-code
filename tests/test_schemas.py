from vad_code.tools.schemas import ListFilesSchema, ReadFileSchema, WriteFileSchema, ReplaceInFileSchema
import pytest
from pydantic import ValidationError


def test_list_files_schema():
    schema = ListFilesSchema(path="/tmp")
    assert schema.path == "/tmp"

    schema_default = ListFilesSchema()
    assert schema_default.path == "."


def test_read_file_schema():
    schema = ReadFileSchema(path="test.txt")
    assert schema.path == "test.txt"

    with pytest.raises(ValidationError):
        ReadFileSchema()


def test_write_file_schema():
    schema = WriteFileSchema(path="test.txt", content="hello")
    assert schema.path == "test.txt"
    assert schema.content == "hello"

    with pytest.raises(ValidationError):
        WriteFileSchema(path="test.txt")


def test_replace_in_file_schema():
    schema = ReplaceInFileSchema(
        path="test.txt",
        old_text="old",
        new_text="new"
    )
    assert schema.path == "test.txt"
    assert schema.old_text == "old"
    assert schema.new_text == "new"

    with pytest.raises(ValidationError):
        ReplaceInFileSchema(path="test.txt", old_text="old")
