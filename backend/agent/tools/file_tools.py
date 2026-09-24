import os
from smolagents import Tool

class ReadFileTool(Tool):
    name = "read_file"
    description = "Reads the contents of a file."
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Absolute path to the file to read."
        }
    }
    output_type = "string"

    def forward(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

class WriteFileTool(Tool):
    name = "write_file"
    description = "Writes text content to a file."
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Absolute path to the file to write."
        },
        "content": {
            "type": "string",
            "description": "Content to write to the file."
        }
    }
    output_type = "string"

    def forward(self, file_path: str, content: str) -> str:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {e}"

class ListDirectoryTool(Tool):
    name = "list_directory"
    description = "Lists files and folders in a directory."
    inputs = {
        "dir_path": {
            "type": "string",
            "description": "Absolute path to the directory."
        }
    }
    output_type = "string"

    def forward(self, dir_path: str) -> str:
        try:
            items = os.listdir(dir_path)
            return "\n".join(items)
        except Exception as e:
            return f"Error listing directory: {e}"
