"""ableton-mcp-dump-live-api with a fake Ableton connection."""

import json

from MCP_Server import live_api_dump
from MCP_Server.server import AbletonCommandError

VERSION = {"major": 11, "minor": 3, "bugfix": 42, "string": "11.3.42"}

MODULES = {
    "Song": {
        "module": "Song",
        "live_version": VERSION,
        "classes": {
            "Song": {
                "doc": "This class represents a Live set.",
                "members": {
                    "tempo": {"kind": "property", "doc": "Get/Set the tempo | in BPM."},
                    "create_scene": {
                        "kind": "method",
                        "doc": "create_scene( (Song)arg1, (int)arg2) -> Scene :\n    Create a scene.",
                    },
                    "View": {"kind": "class", "doc": None},
                },
            },
            "Song.View": {"doc": None, "members": {}},
        },
    },
    "Clip": {
        "module": "Clip",
        "live_version": VERSION,
        "classes": {
            "Clip": {"doc": None, "members": {"muted": {"kind": "property", "doc": "\n\nMute state."}}},
        },
    },
}


class FakeConnection:
    def __init__(self, modules=MODULES, error=None):
        self.modules = modules
        self.error = error
        self.calls = []
        self.disconnected = False

    def send_command(self, command_type, params=None):
        self.calls.append((command_type, params))
        if self.error:
            raise self.error
        assert command_type == "dump_live_api"
        if not params:
            return {"live_version": VERSION, "modules": list(self.modules)}
        return self.modules[params["module"]]

    def disconnect(self):
        self.disconnected = True


def run(tmp_path, *extra, connection=None):
    connection = connection or FakeConnection()
    code = live_api_dump.main(["--out", str(tmp_path), *extra],
                              connect=lambda host, port: connection)
    return code, connection


def test_writes_json_and_index(tmp_path, capsys):
    code, conn = run(tmp_path)
    assert code == 0
    assert conn.disconnected
    assert conn.calls == [
        ("dump_live_api", {}),
        ("dump_live_api", {"module": "Song"}),
        ("dump_live_api", {"module": "Clip"}),
    ]

    target = tmp_path / "11.3.42"
    assert json.loads((target / "Song.json").read_text()) == MODULES["Song"]
    assert json.loads((target / "Clip.json").read_text()) == MODULES["Clip"]

    index = (target / "index.md").read_text()
    assert "# Live API — Live 11.3.42" in index
    assert "## Song" in index and "## Clip" in index
    assert "### Song.View" in index
    assert "This class represents a Live set." in index
    assert "| `create_scene` | method | create_scene( (Song)arg1, (int)arg2) -> Scene : |" in index
    assert "| `tempo` | property | Get/Set the tempo \\| in BPM. |" in index
    assert "| `muted` | property | Mute state. |" in index
    assert "| `View` | class |  |" in index

    assert str(target) in capsys.readouterr().out


def test_module_filter(tmp_path):
    code, conn = run(tmp_path, "--module", "Clip")
    assert code == 0
    assert conn.calls[1:] == [("dump_live_api", {"module": "Clip"})]
    assert not (tmp_path / "11.3.42" / "Song.json").exists()
    assert "## Song" not in (tmp_path / "11.3.42" / "index.md").read_text()


def test_unknown_module(tmp_path, capsys):
    code, _ = run(tmp_path, "--module", "Nope")
    assert code != 0
    assert "Nope" in capsys.readouterr().err


def test_connection_failure(tmp_path, capsys):
    def connect(host, port):
        raise ConnectionError("refused")

    code = live_api_dump.main(["--out", str(tmp_path), "--host", "h", "--port", "1"],
                              connect=connect)
    assert code != 0
    assert "h:1" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_default_connect_failure(tmp_path, capsys, monkeypatch):
    from MCP_Server import server

    monkeypatch.setattr(server.AbletonConnection, "connect", lambda self: False)
    code = live_api_dump.main(["--out", str(tmp_path)])
    assert code != 0
    assert "Could not connect to Ableton" in capsys.readouterr().err


def test_script_without_dump_command(tmp_path, capsys):
    conn = FakeConnection(error=AbletonCommandError("Unknown command: dump_live_api",
                                                    "unknown_command"))
    code, _ = run(tmp_path, connection=conn)
    assert code != 0
    err = capsys.readouterr().err
    assert "dump_live_api" in err and "ableton-mcp-install-script" in err
    assert conn.disconnected


def test_default_out_dir_and_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ABLETON_HOST", "example")
    monkeypatch.setenv("ABLETON_PORT", "1234")
    seen = {}

    def connect(host, port):
        seen["addr"] = (host, port)
        return FakeConnection()

    assert live_api_dump.main([], connect=connect) == 0
    assert seen["addr"] == ("example", 1234)
    assert (tmp_path / "docs" / "live-api" / "11.3.42" / "index.md").exists()
