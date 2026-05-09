from vad_code.tools.schemas import ListFilesSchema, ReadFileSchema, WriteFileSchema, ReplaceInFileSchema
import pytest
from pydantic import ValidationError

def test_list_files_schema():
    schema = ListFilesSchema(directory="/tmp")
    assert schema.directory == "/tmp"
    
    schema_default = ListFilesSchema()
    assert schema_default.directory == "."

def test_read_file_schema():
    schema = ReadFileSchema(filepath="test.txt")
    assert schema.filepath == "test.txt"
    
    with pytest.raises(ValidationError):
        ReadFileSchema()

def test_write_file_schema():
    schema = WriteFileSchema(filepath="test.txt", content="hello")
    assert schema.filepath == "test.txt"
    assert schema.content == "hello"
    
    with pytest.raises(ValidationError):
        WriteFileSchema(filepath="test.txt")

def test_replace_in_file_schema():
    schema = ReplaceInFileSchema(
        filepath="test.txt", 
        old_text="old", 
        new_text="new"
    )
    assert schema.filepath == "test.txt"
    assert schema.old_text == "old"
    assert schema.new_text == "new"
    
    with pytest.raises(ValidationError):
        ReplaceInFileSchema(filepath="test.txt", old_text="old")