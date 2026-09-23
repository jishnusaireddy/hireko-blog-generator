"""Dataclass dependencies container for Pydantic AI Agent RunContext."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic_ai_harness import FileSystem, Shell, CodeMode


@dataclass
class BlogAgentDeps:
    """Dependency container injected into Pydantic AI Agent operations."""

    output_dir: str = "./output"
    article_name: str = "article"
    topic: str = "AI Agents & Modern Software Engineering Architecture"
    audience: str = "Software Engineers, System Architects, & Tech Leaders"
    goal: str = "Provide a pedantic, fact-checked, deep-dive technical reference guide with actionable patterns"
    word_target: int = 800
    template_name: str = "Casual Blog"  # Casual Blog, Classic, Magazine, Full-Bleed Banner, Sidebar Layout, Dark Mode

    # Harness Capabilities
    fs: FileSystem = field(default_factory=FileSystem)
    shell: Shell = field(default_factory=Shell)
    code: CodeMode = field(default_factory=CodeMode)

    # 3-Iteration State Management
    current_iteration: int = 1
    evidence_pack: List[Dict[str, Any]] = field(default_factory=list)
    keywords: Dict[str, Any] = field(default_factory=dict)
    section_outline: List[Dict[str, Any]] = field(default_factory=list)
    raw_draft: str = ""
    audited_draft: str = ""
    generated_assets: List[str] = field(default_factory=list)
    final_html_path: str = ""
    content_source: str = ""

    def get_article_folder(self) -> str:
        """Returns full absolute path to the target article output directory."""
        import os
        import re
        safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", self.article_name).strip(".-")
        if not safe_name:
            safe_name = "article"
        return os.path.abspath(os.path.join(self.output_dir, safe_name))
