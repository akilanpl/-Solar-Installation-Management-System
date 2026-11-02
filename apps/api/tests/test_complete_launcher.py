"""The local launcher must refuse conflicts without starting or stopping services."""
import importlib.util
import socket
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "complete_local", Path(__file__).resolve().parents[1] / "scripts/complete_local.py"
)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


@pytest.mark.parametrize("ports", [(80, 3063), (8063, 65536), (3063, 3063)])
def test_invalid_ports_are_rejected_before_environment_or_children(monkeypatch, ports):
    monkeypatch.setattr(sys, "argv", ["complete_local", "serve", "--api-port", str(ports[0]), "--web-port", str(ports[1])])
    monkeypatch.setattr(launcher, "dotenv_values", lambda *_args, **_kwargs: pytest.fail("Environment read before port validation"))
    with pytest.raises(SystemExit) as error:
        launcher.main()
    assert error.value.code == 2


def test_occupied_web_port_never_starts_api_or_stops_listener(monkeypatch, tmp_path):
    build = tmp_path / ".next"
    build.mkdir()
    (build / "BUILD_ID").write_text("fixture")
    monkeypatch.setattr(launcher, "WEB", tmp_path)
    monkeypatch.setattr(launcher, "dotenv_values", lambda *_args, **_kwargs: {
        "SOLAROPS_APP_ENV": "development",
        "SOLAROPS_DATABASE_URL": "postgresql+psycopg://fixture@127.0.0.1/solarops_release_demo_20261102",
    })
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("Started a child despite occupied web port"))
    with socket.socket() as occupied, socket.socket() as free:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        free.bind(("127.0.0.1", 0))
        api_port = free.getsockname()[1]
        free.close()
        monkeypatch.setattr(sys, "argv", ["complete_local", "serve", "--api-port", str(api_port), "--web-port", str(occupied.getsockname()[1])])
        with pytest.raises(SystemExit) as error:
            launcher.main()
        assert error.value.code == 2
        # The listener owned by this test is still usable after the refusal.
        with socket.create_connection(occupied.getsockname(), timeout=1):
            accepted, _ = occupied.accept()
            accepted.close()


def test_released_listener_can_restart_while_connection_is_in_time_wait():
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        with socket.create_connection(server.getsockname(), timeout=1) as client:
            accepted, _ = server.accept()
            accepted.shutdown(socket.SHUT_WR)
            accepted.close()
            assert client.recv(1) == b""
    launcher.check_port(port)
