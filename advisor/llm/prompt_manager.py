from pathlib import Path
from typing import Any

from jinja2 import Environment, Template, TemplateSyntaxError


class PromptManager:
    """
    Prompt template manager using Jinja2 that loads templates from local files.

    Templates are loaded from the 'prompts' directory at the project root.
    File structure: prompts/{prompt_key}/{version}.md
    Example: prompts/welcome_message/v1.md
    """

    def __init__(self, prompts_dir: Path | None = None):
        """
        Initialize the PromptManager.

        Args:
            prompts_dir: Optional custom path to prompts directory.
                        If None, uses 'prompts' directory at project root.
        """
        self._templates: dict[str, dict[str, Template]] = {}
        self._jinja_env = Environment(autoescape=True)

        # Determine prompts directory path
        if prompts_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            self.prompts_dir = project_root / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        # Auto-load all prompts on initialization
        self._load_all_prompts()

    def _load_all_prompts(self) -> None:
        """Automatically load all prompt templates from the prompts directory."""
        if not self.prompts_dir.exists():
            return

        # Iterate through prompt directories
        for prompt_dir in self.prompts_dir.iterdir():
            if prompt_dir.is_dir():
                prompt_key = prompt_dir.name

                # Load all version files in this prompt directory
                for version_file in prompt_dir.glob("*.md"):
                    version = version_file.stem  # Filename without extension
                    self._load_prompt_from_file(prompt_key, version, version_file)

    def _load_prompt_from_file(self, prompt_key: str, version: str, file_path: Path) -> None:
        """Load a single prompt template from a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            jinja_template = self._jinja_env.from_string(template_content)

            if prompt_key not in self._templates:
                self._templates[prompt_key] = {}

            self._templates[prompt_key][version] = jinja_template
        except TemplateSyntaxError as e:
            raise ValueError(f"Invalid template syntax in {file_path}: {str(e)}")
        except Exception as e:
            raise IOError(f"Error loading template from {file_path}: {str(e)}")

    def reload_prompts(self) -> None:
        """Reload all prompts from disk, clearing the cache."""
        self._templates.clear()
        self._load_all_prompts()

    def reload_prompt(self, prompt_key: str, version: str | None = None) -> None:
        """
        Reload a specific prompt or version from disk.

        Args:
            prompt_key: The prompt identifier
            version: Optional specific version to reload. If None, reloads all versions.
        """
        prompt_dir = self.prompts_dir / prompt_key

        if not prompt_dir.exists():
            raise FileNotFoundError(f"Prompt directory not found: {prompt_dir}")

        if version:
            # Reload specific version
            version_file = prompt_dir / f"{version}.md"
            if not version_file.exists():
                raise FileNotFoundError(f"Version file not found: {version_file}")

            self._load_prompt_from_file(prompt_key, version, version_file)
        else:
            # Reload all versions for this prompt
            if prompt_key in self._templates:
                del self._templates[prompt_key]

            for version_file in prompt_dir.glob("*.md"):
                version_name = version_file.stem
                self._load_prompt_from_file(prompt_key, version_name, version_file)

    def get_prompt_template(self, prompt_key: str, version: str | None = None) -> Template:
        """Retrieves template, defaulting to latest version."""
        if prompt_key not in self._templates:
            raise KeyError(f"Prompt template '{prompt_key}' not found")

        versions = self._templates[prompt_key]

        if version and version in versions:
            return versions[version]

        # Return latest version (lexicographically sorted)
        latest_version = max(versions.keys())
        return versions[latest_version]

    def register_prompt(self, prompt_key: str, template: str, version: str = "v1") -> None:
        """
        Registers or updates a prompt template in memory only.

        Note: This does NOT save to disk. Use save_prompt_to_file() for persistence.
        """
        try:
            jinja_template = self._jinja_env.from_string(template)

            if prompt_key not in self._templates:
                self._templates[prompt_key] = {}

            self._templates[prompt_key][version] = jinja_template
        except TemplateSyntaxError as e:
            raise ValueError(f"Invalid template syntax: {str(e)}")

    def save_prompt_to_file(self, prompt_key: str, template: str, version: str = "v1") -> Path:
        """
        Save a prompt template to disk and register it in memory.

        Returns:
            Path to the saved file
        """
        # Create prompt directory if it doesn't exist
        prompt_dir = self.prompts_dir / prompt_key
        prompt_dir.mkdir(parents=True, exist_ok=True)

        # Save to file
        file_path = prompt_dir / f"{version}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(template)

        # Register in memory
        self.register_prompt(prompt_key, template, version)

        return file_path

    def list_prompts(self) -> dict[str, list[str]]:
        """
        List all available prompts and their versions.

        Returns:
            Dictionary mapping prompt keys to lists of available versions
        """
        return {prompt_key: list(versions.keys()) for prompt_key, versions in self._templates.items()}

    def validate_variables(self, prompt_key: str, variables: dict[str, Any]) -> bool:
        """
        Validates variables against template requirements.

        Note: Full validation requires AST parsing of Jinja2 templates.
        This is a simplified version that attempts rendering.
        """
        template = self.get_prompt_template(prompt_key)
        try:
            template.render(**variables)
            return True
        except Exception as e:
            raise ValueError(f"Invalid variables for template '{prompt_key}': {str(e)}")

    def render(self, prompt_key: str, variables: dict[str, Any], version: str | None = None) -> str:
        """
        Convenience method to get and render template in one call.
        """
        template = self.get_prompt_template(prompt_key, version)
        return template.render(**variables)
