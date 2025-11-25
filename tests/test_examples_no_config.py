"""
Test that examples work without configuration files.

This test verifies that all example Dockerfiles can be parsed and don't
require any user configuration to work.
"""

import os
from pathlib import Path
import pytest
from derpy.dockerfile.parser import DockerfileParser


class TestExamplesNoConfig:
    """Test examples work without config files."""

    @pytest.fixture
    def examples_dir(self):
        """Get the examples directory path."""
        return Path(__file__).parent.parent / "examples"

    def test_minimal_example_no_config(self, examples_dir):
        """Test minimal example works without config."""
        dockerfile_path = examples_dir / "minimal" / "Dockerfile"
        assert dockerfile_path.exists(), "Minimal Dockerfile should exist"

        # Parse the Dockerfile - should work without any config
        parser = DockerfileParser()
        dockerfile = parser.parse(dockerfile_path)

        # Verify it has the expected instructions
        assert len(dockerfile.instructions) > 0, "Should have instructions"
        assert (
            dockerfile.instructions[0].type.value == "FROM"
        ), "First instruction should be FROM"
        assert (
            "alpine" in dockerfile.instructions[0].value.lower()
        ), "Should use alpine base"

    def test_alpine_python_example_no_config(self, examples_dir):
        """Test alpine-python example works without config."""
        dockerfile_path = examples_dir / "alpine-python" / "Dockerfile"
        assert dockerfile_path.exists(), "Alpine-python Dockerfile should exist"

        # Parse the Dockerfile - should work without any config
        parser = DockerfileParser()
        dockerfile = parser.parse(dockerfile_path)

        # Verify it has the expected instructions
        assert len(dockerfile.instructions) > 0, "Should have instructions"
        assert (
            dockerfile.instructions[0].type.value == "FROM"
        ), "First instruction should be FROM"

    def test_nginx_web_example_no_config(self, examples_dir):
        """Test nginx-web example works without config."""
        dockerfile_path = examples_dir / "nginx-web" / "Dockerfile"
        assert dockerfile_path.exists(), "Nginx-web Dockerfile should exist"

        # Parse the Dockerfile - should work without any config
        parser = DockerfileParser()
        dockerfile = parser.parse(dockerfile_path)

        # Verify it has the expected instructions
        assert len(dockerfile.instructions) > 0, "Should have instructions"
        assert (
            dockerfile.instructions[0].type.value == "FROM"
        ), "First instruction should be FROM"

    def test_python_app_example_no_config(self, examples_dir):
        """Test python-app example works without config."""
        dockerfile_path = examples_dir / "python-app" / "Dockerfile"
        assert dockerfile_path.exists(), "Python-app Dockerfile should exist"

        # Parse the Dockerfile - should work without any config
        parser = DockerfileParser()
        dockerfile = parser.parse(dockerfile_path)

        # Verify it has the expected instructions
        assert len(dockerfile.instructions) > 0, "Should have instructions"
        assert (
            dockerfile.instructions[0].type.value == "FROM"
        ), "First instruction should be FROM"

    def test_ubuntu_curl_example_no_config(self, examples_dir):
        """Test ubuntu-curl example works without config."""
        dockerfile_path = examples_dir / "ubuntu-curl" / "Dockerfile"
        assert dockerfile_path.exists(), "Ubuntu-curl Dockerfile should exist"

        # Parse the Dockerfile - should work without any config
        parser = DockerfileParser()
        dockerfile = parser.parse(dockerfile_path)

        # Verify it has the expected instructions
        assert len(dockerfile.instructions) > 0, "Should have instructions"
        assert (
            dockerfile.instructions[0].type.value == "FROM"
        ), "First instruction should be FROM"

    def test_ubuntu_tools_example_no_config(self, examples_dir):
        """Test ubuntu-tools example works without config."""
        dockerfile_path = examples_dir / "ubuntu-tools" / "Dockerfile"
        assert dockerfile_path.exists(), "Ubuntu-tools Dockerfile should exist"

        # Parse the Dockerfile - should work without any config
        parser = DockerfileParser()
        dockerfile = parser.parse(dockerfile_path)

        # Verify it has the expected instructions
        assert len(dockerfile.instructions) > 0, "Should have instructions"
        assert (
            dockerfile.instructions[0].type.value == "FROM"
        ), "First instruction should be FROM"

    def test_no_config_files_in_examples(self, examples_dir):
        """Verify no config.yaml files exist in examples directory."""
        # Search for any config.yaml files in examples
        config_files = list(examples_dir.rglob("config.yaml"))
        user_config_files = list(examples_dir.rglob(".derpy/config.yaml"))

        assert len(config_files) == 0, "No config.yaml files should exist in examples"
        assert (
            len(user_config_files) == 0
        ), "No .derpy/config.yaml files should exist in examples"

    def test_examples_readme_no_config_references(self, examples_dir):
        """Verify examples README doesn't reference user config commands."""
        readme_path = examples_dir / "README.md"
        assert readme_path.exists(), "Examples README should exist"

        content = readme_path.read_text()

        # Should not reference user config commands
        assert (
            "derpy config" not in content
        ), "README should not reference 'derpy config' commands"
        # Note: daemon-config.yaml.example is fine (daemon config, not user config)
        assert (
            "~/.derpy/config.yaml" not in content
        ), "README should not reference user config.yaml files"
