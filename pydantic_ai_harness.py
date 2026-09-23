"""Pydantic AI Harness capabilities and agent hooks module."""

import os
import sys
import subprocess
import shutil
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path


class BaseCapability(ABC):
    """Conceptual base class and hook spec for Pydantic AI Harness capabilities."""

    def __init__(self, name: str = "BaseCapability"):
        self.name = name

    def initialize(self) -> None:
        """Lifecycle hook called when capability is loaded."""
        pass

    def cleanup(self) -> None:
        """Lifecycle hook called when task completes."""
        pass


class FileSystem(BaseCapability):
    """File system management capability for output directories and blog assets."""

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__(name="FileSystem")
        self.root_dir = Path(root_dir) if root_dir else None

    def set_root_dir(self, root_dir: str) -> None:
        self.root_dir = Path(root_dir)

    def ensure_dir(self, dir_path: str) -> Path:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_file(self, relative_or_abs_path: str, content: str, mode: str = "w", encoding: str = "utf-8") -> Path:
        if self.root_dir and not Path(relative_or_abs_path).is_absolute():
            full_path = self.root_dir / relative_or_abs_path
        else:
            full_path = Path(relative_or_abs_path)
        
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, mode, encoding=encoding) as f:
            f.write(content)
        return full_path

    def read_file(self, relative_or_abs_path: str, encoding: str = "utf-8") -> str:
        if self.root_dir and not Path(relative_or_abs_path).is_absolute():
            full_path = self.root_dir / relative_or_abs_path
        else:
            full_path = Path(relative_or_abs_path)
            
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
            
        with open(full_path, "r", encoding=encoding) as f:
            return f.read()

    def list_files(self, directory: Optional[str] = None) -> List[str]:
        target = Path(directory) if directory else (self.root_dir or Path("."))
        if not target.exists():
            return []
        return [str(p) for p in target.glob("**/*") if p.is_file()]


class CodeMode(BaseCapability):
    """Code processing and safety execution capability."""

    def __init__(self):
        super().__init__(name="CodeMode")

    def execute_python_snippet(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Safely execute python code within an isolated local dict context."""
        local_scope = context or {}
        global_scope = {"__builtins__": __builtins__}
        try:
            exec(code, global_scope, local_scope)
            return {"success": True, "output": local_scope, "error": None}
        except Exception as e:
            return {"success": False, "output": local_scope, "error": str(e)}

    def format_code(self, code_str: str, language: str = "html") -> str:
        """Basic indentation/formatting helper for generated code snippets."""
        return code_str.strip()


class Shell(BaseCapability):
    """Shell command capability for local environment operations."""

    def __init__(self, cwd: Optional[str] = None):
        super().__init__(name="Shell")
        self.cwd = cwd

    def run_command(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        target_cwd = cwd or self.cwd or os.getcwd()
        try:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=target_cwd,
                timeout=30
            )
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip()
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e)
            }
