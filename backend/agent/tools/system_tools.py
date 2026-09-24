import datetime
import subprocess
import tkinter as tk
from smolagents import Tool

class GetCurrentTimeTool(Tool):
    name = "get_current_time"
    description = "Gets the current date and time."
    inputs = {}
    output_type = "string"

    def forward(self) -> str:
        return datetime.datetime.now().isoformat()

class OpenApplicationTool(Tool):
    name = "open_application"
    description = "Opens an application by path or command."
    inputs = {
        "command": {
            "type": "string",
            "description": "Command or path to execute."
        }
    }
    output_type = "string"

    def forward(self, command: str) -> str:
        try:
            subprocess.Popen(command, shell=True)
            return f"Started {command}"
        except Exception as e:
            return f"Error starting app: {e}"

class GetClipboardTool(Tool):
    name = "get_clipboard"
    description = "Reads content from the clipboard."
    inputs = {}
    output_type = "string"

    def forward(self) -> str:
        try:
            root = tk.Tk()
            root.withdraw()
            content = root.clipboard_get()
            root.destroy()
            return content
        except Exception as e:
            return f"Error reading clipboard: {e}"
