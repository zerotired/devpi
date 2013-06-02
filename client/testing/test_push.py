import sys
import py
import pytest
import types
from subprocess import check_call, Popen, check_output
from devpi import config
from devpi.main import Hub

def runproc(cmd):
    args = cmd.split()
    return check_output(args)


def test_main(monkeypatch, tmpdir):
    from devpi.push import main
    l = []
    def mypost(url, data):
        l.append((url, data))
        class r:
            status_code = 201
        return r
    monkeypatch.setattr(py.std.requests, "post", mypost)

    class args:
        clientdir = tmpdir.join("client")

    hub = Hub(args)
    hub.config.reconfigure(dict(pushrelease="/push"))
    p = tmpdir.join("pypirc")
    p.write(py.std.textwrap.dedent("""
        [distutils]
        index-servers = whatever

        [whatever]
        repository: http://anotherserver
        username: test
        password: testp
    """))
    class args:
        pypirc = str(p)
        posturl = "whatever"
        nameversion = "pkg-1.0"
    main(hub, args)
    assert len(l) == 1
    url, data = l[0]
    assert url == "/push"
    req = py.std.json.loads(data)
    assert req["name"] == "pkg"
    assert req["version"] == "1.0"
    assert req["posturl"] == "http://anotherserver"
    assert req["username"] == "test"
    assert req["password"] == "testp"

class TestPush:
    def test_help(self, ext_devpi):
        result = ext_devpi("push", "-h")
        assert result.ret == 0
        result.stdout.fnmatch_lines("""
            *release*
            *url*
        """)
