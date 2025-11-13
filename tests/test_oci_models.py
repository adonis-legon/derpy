"""Tests for OCI models."""

import pytest
from pathlib import Path
from derpy.oci.models import (
    Descriptor,
    Layer,
    RootFS,
    HistoryEntry,
    ContainerConfig,
    ImageConfig,
    Manifest,
    Index,
    Image,
    MEDIA_TYPE_IMAGE_CONFIG,
    MEDIA_TYPE_IMAGE_LAYER,
    MEDIA_TYPE_IMAGE_MANIFEST,
)


class TestDescriptor:
    """Tests for Descriptor model."""
    
    def test_create_descriptor(self):
        """Test creating a valid descriptor."""
        desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:abc123",
            size=1024
        )
        assert desc.media_type == MEDIA_TYPE_IMAGE_LAYER
        assert desc.digest == "sha256:abc123"
        assert desc.size == 1024
    
    def test_descriptor_to_dict(self):
        """Test descriptor serialization to dict."""
        desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:abc123",
            size=1024
        )
        data = desc.to_dict()
        assert data["mediaType"] == MEDIA_TYPE_IMAGE_LAYER
        assert data["digest"] == "sha256:abc123"
        assert data["size"] == 1024
    
    def test_descriptor_from_dict(self):
        """Test descriptor deserialization from dict."""
        data = {
            "mediaType": MEDIA_TYPE_IMAGE_LAYER,
            "digest": "sha256:abc123",
            "size": 1024
        }
        desc = Descriptor.from_dict(data)
        assert desc.media_type == MEDIA_TYPE_IMAGE_LAYER
        assert desc.digest == "sha256:abc123"
        assert desc.size == 1024
    
    def test_descriptor_validation_success(self):
        """Test descriptor validation with valid data."""
        desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:abc123",
            size=1024
        )
        errors = desc.validate()
        assert len(errors) == 0
    
    def test_descriptor_validation_missing_digest(self):
        """Test descriptor validation with missing digest."""
        desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="",
            size=1024
        )
        errors = desc.validate()
        assert len(errors) > 0
        assert any("digest" in err for err in errors)


class TestLayer:
    """Tests for Layer model."""
    
    def test_create_layer(self):
        """Test creating a valid layer."""
        layer = Layer(
            digest="sha256:abc123",
            size=2048,
            diff_id="sha256:def456"
        )
        assert layer.digest == "sha256:abc123"
        assert layer.size == 2048
        assert layer.diff_id == "sha256:def456"
    
    def test_layer_to_descriptor(self):
        """Test converting layer to descriptor."""
        layer = Layer(
            digest="sha256:abc123",
            size=2048,
            media_type=MEDIA_TYPE_IMAGE_LAYER
        )
        desc = layer.to_descriptor()
        assert desc.digest == layer.digest
        assert desc.size == layer.size
        assert desc.media_type == layer.media_type


class TestImageConfig:
    """Tests for ImageConfig model."""
    
    def test_create_image_config(self):
        """Test creating a valid image config."""
        config = ImageConfig(
            architecture="amd64",
            os="linux"
        )
        assert config.architecture == "amd64"
        assert config.os == "linux"
    
    def test_image_config_to_dict(self):
        """Test image config serialization."""
        config = ImageConfig(
            architecture="amd64",
            os="linux"
        )
        data = config.to_dict()
        assert data["architecture"] == "amd64"
        assert data["os"] == "linux"
        assert "config" in data
        assert "rootfs" in data
    
    def test_image_config_validation_success(self):
        """Test image config validation with valid data."""
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(diff_ids=["sha256:abc123"])
        )
        errors = config.validate()
        assert len(errors) == 0
    
    def test_image_config_validation_missing_arch(self):
        """Test image config validation with missing architecture."""
        config = ImageConfig(
            architecture="",
            os="linux"
        )
        errors = config.validate()
        assert len(errors) > 0
        assert any("architecture" in err for err in errors)


class TestManifest:
    """Tests for Manifest model."""
    
    def test_create_manifest(self):
        """Test creating a valid manifest."""
        config_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest="sha256:config123",
            size=512
        )
        layer_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:layer123",
            size=1024
        )
        manifest = Manifest(
            config=config_desc,
            layers=[layer_desc]
        )
        assert manifest.config == config_desc
        assert len(manifest.layers) == 1
        assert manifest.schema_version == 2
    
    def test_manifest_to_dict(self):
        """Test manifest serialization."""
        config_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest="sha256:config123",
            size=512
        )
        manifest = Manifest(config=config_desc, layers=[])
        data = manifest.to_dict()
        assert data["schemaVersion"] == 2
        assert data["mediaType"] == MEDIA_TYPE_IMAGE_MANIFEST
        assert "config" in data
    
    def test_manifest_validation_success(self):
        """Test manifest validation with valid data."""
        config_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest="sha256:config123",
            size=512
        )
        layer_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:layer123",
            size=1024
        )
        manifest = Manifest(
            config=config_desc,
            layers=[layer_desc]
        )
        errors = manifest.validate()
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestImageConfigAdditional:
    """Additional tests for ImageConfig model."""
    
    def test_image_config_with_env(self):
        """Test ImageConfig with environment variables."""
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(type="layers", diff_ids=[]),
            config=ContainerConfig()
        )
        config.config.env = ["PATH=/usr/bin", "HOME=/root"]
        assert len(config.config.env) == 2
    
    def test_image_config_with_labels(self):
        """Test ImageConfig with labels."""
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(type="layers", diff_ids=[]),
            config=ContainerConfig()
        )
        config.config.labels = {"version": "1.0", "maintainer": "test"}
        assert config.config.labels["version"] == "1.0"


class TestManifestAdditional:
    """Additional tests for Manifest model."""
    
    def test_manifest_with_multiple_layers(self):
        """Test Manifest with multiple layers."""
        manifest = Manifest(
            schema_version=2,
            media_type=MEDIA_TYPE_IMAGE_MANIFEST,
            config=Descriptor(
                media_type=MEDIA_TYPE_IMAGE_CONFIG,
                digest="sha256:config",
                size=100
            ),
            layers=[
                Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_LAYER,
                    digest="sha256:layer1",
                    size=200
                ),
                Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_LAYER,
                    digest="sha256:layer2",
                    size=300
                )
            ]
        )
        assert len(manifest.layers) == 2
        assert manifest.layers[0].digest == "sha256:layer1"
        assert manifest.layers[1].digest == "sha256:layer2"


class TestImageAdditional:
    """Additional tests for Image model."""
    
    def test_image_creation(self):
        """Test Image creation."""
        image = Image(
            manifest=Manifest(
                schema_version=2,
                media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                config=Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_CONFIG,
                    digest="sha256:config",
                    size=100
                ),
                layers=[]
            ),
            config=ImageConfig(
                architecture="amd64",
                os="linux",
                rootfs=RootFS(type="layers", diff_ids=[]),
                config=ContainerConfig()
            ),
            layers=[]
        )
        assert image is not None
        assert image.manifest is not None
        assert image.config is not None
        assert image.layers == []
    
    def test_image_with_layers(self):
        """Test Image with layers."""
        image = Image(
            manifest=Manifest(
                schema_version=2,
                media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                config=Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_CONFIG,
                    digest="sha256:config",
                    size=100
                ),
                layers=[
                    Descriptor(
                        media_type=MEDIA_TYPE_IMAGE_LAYER,
                        digest="sha256:layer1",
                        size=200
                    )
                ]
            ),
            config=ImageConfig(
                architecture="amd64",
                os="linux",
                rootfs=RootFS(type="layers", diff_ids=["sha256:layer1"]),
                config=ContainerConfig()
            ),
            layers=[Layer(digest="sha256:layer1", size=200)]
        )
        assert len(image.layers) == 1
        assert image.layers[0].digest == "sha256:layer1"


class TestMediaTypeConstants:
    """Tests for media type constants."""
    
    def test_media_type_constants_exist(self):
        """Test that media type constants are defined."""
        assert MEDIA_TYPE_IMAGE_CONFIG is not None
        assert MEDIA_TYPE_IMAGE_LAYER is not None
        assert MEDIA_TYPE_IMAGE_MANIFEST is not None
    
    def test_media_type_constants_are_strings(self):
        """Test that media type constants are strings."""
        assert isinstance(MEDIA_TYPE_IMAGE_CONFIG, str)
        assert isinstance(MEDIA_TYPE_IMAGE_LAYER, str)
        assert isinstance(MEDIA_TYPE_IMAGE_MANIFEST, str)
    
    def test_media_type_constants_follow_oci_spec(self):
        """Test that media types follow OCI spec format."""
        assert "application/vnd.oci" in MEDIA_TYPE_IMAGE_CONFIG
        assert "application/vnd.oci" in MEDIA_TYPE_IMAGE_LAYER
        assert "application/vnd.oci" in MEDIA_TYPE_IMAGE_MANIFEST



class TestDescriptorExtended:
    """Extended tests for Descriptor."""
    
    def test_descriptor_with_urls(self):
        """Test Descriptor with URLs."""
        desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:abc123",
            size=1024,
            urls=["https://example.com/layer"]
        )
        assert desc.urls == ["https://example.com/layer"]
    
    def test_descriptor_with_annotations(self):
        """Test Descriptor with annotations."""
        desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:abc123",
            size=1024,
            annotations={"key": "value"}
        )
        assert desc.annotations == {"key": "value"}


class TestLayerExtended:
    """Extended tests for Layer."""
    
    def test_layer_to_descriptor(self):
        """Test Layer to_descriptor method."""
        layer = Layer(
            digest="sha256:abc123",
            size=1024
        )
        desc = layer.to_descriptor()
        
        assert isinstance(desc, Descriptor)
        assert desc.digest == "sha256:abc123"
        assert desc.size == 1024
    
    def test_layer_with_diff_id(self):
        """Test Layer with diff_id."""
        layer = Layer(
            digest="sha256:abc123",
            size=1024,
            diff_id="sha256:def456"
        )
        assert layer.diff_id == "sha256:def456"
    
    def test_layer_with_content_path(self):
        """Test Layer with content_path."""
        layer = Layer(
            digest="sha256:abc123",
            size=1024,
            content_path=Path("/tmp/layer.tar.gz")
        )
        assert layer.content_path == Path("/tmp/layer.tar.gz")


class TestRootFSExtended:
    """Extended tests for RootFS."""
    
    def test_rootfs_with_multiple_diff_ids(self):
        """Test RootFS with multiple diff_ids."""
        rootfs = RootFS(
            type="layers",
            diff_ids=["sha256:layer1", "sha256:layer2", "sha256:layer3"]
        )
        assert len(rootfs.diff_ids) == 3
        assert rootfs.diff_ids[0] == "sha256:layer1"


class TestHistoryEntryExtended:
    """Extended tests for HistoryEntry."""
    
    def test_history_entry_with_all_fields(self):
        """Test HistoryEntry with all fields."""
        entry = HistoryEntry(
            created="2024-01-01T00:00:00Z",
            created_by="RUN apt-get update",
            comment="Update packages",
            empty_layer=False
        )
        assert entry.created == "2024-01-01T00:00:00Z"
        assert entry.created_by == "RUN apt-get update"
        assert entry.comment == "Update packages"
        assert entry.empty_layer is False
    
    def test_history_entry_empty_layer(self):
        """Test HistoryEntry with empty_layer."""
        entry = HistoryEntry(
            created="2024-01-01T00:00:00Z",
            created_by="ENV PATH=/usr/bin",
            empty_layer=True
        )
        assert entry.empty_layer is True


class TestContainerConfigExtended:
    """Extended tests for ContainerConfig."""
    
    def test_container_config_with_env(self):
        """Test ContainerConfig with environment variables."""
        config = ContainerConfig(
            env=["PATH=/usr/bin", "HOME=/root"]
        )
        assert len(config.env) == 2
    
    def test_container_config_with_cmd(self):
        """Test ContainerConfig with CMD."""
        config = ContainerConfig(
            cmd=["python", "app.py"]
        )
        assert config.cmd == ["python", "app.py"]
    
    def test_container_config_with_labels(self):
        """Test ContainerConfig with labels."""
        config = ContainerConfig(
            labels={"version": "1.0", "maintainer": "test@example.com"}
        )
        assert config.labels["version"] == "1.0"
    
    def test_container_config_with_working_dir(self):
        """Test ContainerConfig with working directory."""
        config = ContainerConfig(
            working_dir="/app"
        )
        assert config.working_dir == "/app"


class TestIndexExtended:
    """Extended tests for Index."""
    
    def test_index_with_multiple_manifests(self):
        """Test Index with multiple manifests."""
        index = Index(
            schema_version=2,
            manifests=[
                Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                    digest="sha256:manifest1",
                    size=100
                ),
                Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                    digest="sha256:manifest2",
                    size=200
                )
            ]
        )
        assert len(index.manifests) == 2
    
    def test_index_with_annotations(self):
        """Test Index with annotations."""
        index = Index(
            schema_version=2,
            manifests=[],
            annotations={"org.opencontainers.image.ref.name": "latest"}
        )
        assert index.annotations is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestDescriptorValidation:
    """Tests for Descriptor validation."""
    
    def test_descriptor_validate_method(self):
        """Test Descriptor validate method if it exists."""
        desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:abc123",
            size=1024
        )
        if hasattr(desc, 'validate'):
            errors = desc.validate()
            assert isinstance(errors, list)
    
    def test_descriptor_from_dict(self):
        """Test Descriptor from_dict method."""
        data = {
            "mediaType": MEDIA_TYPE_IMAGE_LAYER,
            "digest": "sha256:abc123",
            "size": 1024
        }
        desc = Descriptor.from_dict(data)
        
        assert desc.media_type == MEDIA_TYPE_IMAGE_LAYER
        assert desc.digest == "sha256:abc123"
        assert desc.size == 1024


class TestLayerValidation:
    """Tests for Layer validation."""
    
    def test_layer_validate_returns_list(self):
        """Test Layer validate returns list."""
        layer = Layer(
            digest="sha256:abc123",
            size=1024
        )
        errors = layer.validate()
        assert isinstance(errors, list)
    
    def test_layer_validate_empty_digest(self):
        """Test Layer validation with empty digest."""
        layer = Layer(
            digest="",
            size=1024
        )
        errors = layer.validate()
        assert len(errors) > 0


class TestManifestValidation:
    """Tests for Manifest validation."""
    
    def test_manifest_validate_method(self):
        """Test Manifest validate method if it exists."""
        manifest = Manifest(
            schema_version=2,
            media_type=MEDIA_TYPE_IMAGE_MANIFEST,
            config=Descriptor(
                media_type=MEDIA_TYPE_IMAGE_CONFIG,
                digest="sha256:config",
                size=100
            ),
            layers=[]
        )
        if hasattr(manifest, 'validate'):
            errors = manifest.validate()
            assert isinstance(errors, list)


class TestImageConfigValidation:
    """Tests for ImageConfig validation."""
    
    def test_image_config_validate_method(self):
        """Test ImageConfig validate method if it exists."""
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(type="layers", diff_ids=[]),
            config=ContainerConfig()
        )
        if hasattr(config, 'validate'):
            errors = config.validate()
            assert isinstance(errors, list)


class TestContainerConfigDefaults:
    """Tests for ContainerConfig defaults."""
    
    def test_container_config_empty_defaults(self):
        """Test ContainerConfig with empty defaults."""
        config = ContainerConfig()
        
        # Check that optional fields can be None or empty
        assert config.env is None or isinstance(config.env, list)
        assert config.cmd is None or isinstance(config.cmd, list)
        assert config.labels is None or isinstance(config.labels, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
