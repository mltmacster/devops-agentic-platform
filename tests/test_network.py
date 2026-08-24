"""Tests for URL Formatting & Network Configuration."""

import pytest


class TestNetworkConfig:
    """Tests for the NetworkConfig data class."""

    def test_default_config(self):
        from src.network import NetworkConfig

        config = NetworkConfig()

        assert config.base_host == "sandbox.dap.io"
        assert config.default_port == 80
        assert config.ide_base_port == 8080
        assert not config.enable_https

    def test_custom_config(self):
        from src.network import NetworkConfig

        config = NetworkConfig(
            base_host="mycompany.dev",
            default_port=443,
            ide_base_port=9090,
            enable_https=True,
        )

        assert config.base_host == "mycompany.dev"
        assert config.default_port == 443
        assert config.ide_base_port == 9090
        assert config.enable_https

    def test_scheme_properties(self):
        from src.network import NetworkConfig

        http_config = NetworkConfig()
        assert http_config.scheme == "http"
        assert http_config.ide_scheme == "ws"

        https_config = NetworkConfig(enable_https=True)
        assert https_config.scheme == "https"
        assert https_config.ide_scheme == "wss"


class TestBuildIdeUrl:
    """Tests for the build_ide_url function."""

    def test_default_ide_url(self):
        from src.network import build_ide_url

        url = build_ide_url("abc123")

        assert url == "ws://sandbox-abc123.sandbox.dap.io:8080/api/ide/ws/abc123"

    def test_custom_host_ide_url(self):
        from src.network import build_ide_url

        url = build_ide_url("xyz789", base_host="mycompany.dev")

        assert url == "ws://sandbox-xyz789.mycompany.dev:8080/api/ide/ws/xyz789"

    def test_custom_port_ide_url(self):
        from src.network import build_ide_url

        url = build_ide_url("abc123", port=9090)

        assert url == "ws://sandbox-abc123.sandbox.dap.io:9090/api/ide/ws/abc123"

    def test_https_ide_url(self):
        from src.network import build_ide_url

        url = build_ide_url("abc123", use_https=True)

        assert url == "wss://sandbox-abc123.sandbox.dap.io:8080/api/ide/ws/abc123"

    def test_https_with_custom_host_ide_url(self):
        from src.network import build_ide_url

        url = build_ide_url("abc123", base_host="secure.dev", use_https=True)

        assert url == "wss://sandbox-abc123.secure.dev:8080/api/ide/ws/abc123"


class TestBuildSandboxHttpUrl:
    """Tests for the build_sandbox_http_url function."""

    def test_default_web_url(self):
        from src.network import build_sandbox_http_url

        url = build_sandbox_http_url("abc123")

        assert url == "http://sandbox-abc123.sandbox.dap.io:80/"

    def test_custom_host_web_url(self):
        from src.network import build_sandbox_http_url

        url = build_sandbox_http_url("abc123", base_host="mycompany.dev")

        assert url == "http://sandbox-abc123.mycompany.dev:80/"

    def test_custom_port_web_url(self):
        from src.network import build_sandbox_http_url

        url = build_sandbox_http_url("abc123", port=443)

        assert url == "http://sandbox-abc123.sandbox.dap.io:443/"

    def test_https_web_url(self):
        from src.network import build_sandbox_http_url

        url = build_sandbox_http_url("abc123", use_https=True)

        assert url == "https://sandbox-abc123.sandbox.dap.io:80/"

    def test_https_with_custom_host_web_url(self):
        from src.network import build_sandbox_http_url

        url = build_sandbox_http_url("abc123", base_host="secure.dev", use_https=True)

        assert url == "https://sandbox-abc123.secure.dev:80/"


class TestBuildIdeConfigUrls:
    """Tests for the build_ide_config_urls function."""

    def test_returns_all_required_keys(self):
        from src.network import build_ide_config_urls

        urls = build_ide_config_urls("abc123")

        assert "websocket" in urls
        assert "web" in urls
        assert "status" in urls
        assert "config" in urls

    def test_websocket_url_format(self):
        from src.network import build_ide_config_urls

        urls = build_ide_config_urls("abc123")

        assert urls["websocket"].startswith("ws://")
        assert "api/ide/ws/abc123" in urls["websocket"]

    def test_web_url_format(self):
        from src.network import build_ide_config_urls

        urls = build_ide_config_urls("abc123")

        assert urls["web"].startswith("http://")
        assert "/sandbox-abc123.sandbox.dap.io:80/" in urls["web"]

    def test_https_urls(self):
        from src.network import build_ide_config_urls

        urls = build_ide_config_urls("abc123", use_https=True)

        assert urls["websocket"].startswith("wss://")
        assert urls["web"].startswith("https://")


class TestFormatSandboxResponseUrls:
    """Tests for the format_sandbox_response_urls function."""

    def test_with_default_config(self):
        from src.network import NetworkConfig, format_sandbox_response_urls

        urls = format_sandbox_response_urls("abc123")

        assert "websocket" in urls
        assert "web" in urls
        assert "status" in urls
        assert "config" in urls

    def test_with_custom_config(self):
        from src.network import NetworkConfig, format_sandbox_response_urls

        config = NetworkConfig(
            base_host="mycompany.dev",
            ide_base_port=9090,
            default_port=443,
            enable_https=True,
        )

        urls = format_sandbox_response_urls("abc123", config=config)

        assert urls["websocket"] == "wss://sandbox-abc123.mycompany.dev:9090/api/ide/ws/abc123"
        assert urls["web"] == "https://sandbox-abc123.mycompany.dev:443/"
        assert urls["status"] == "https://sandbox-abc123.mycompany.dev:9090/api/ide/status/abc123"
        assert urls["config"] == "https://sandbox-abc123.mycompany.dev:9090/api/ide/config"


class TestNetworkConfigImmutability:
    """Tests for NetworkConfig frozen=True immutability."""

    def test_config_is_frozen(self):
        from src.network import NetworkConfig

        config = NetworkConfig()

        with pytest.raises(Exception):
            config.base_host = "new.host"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
