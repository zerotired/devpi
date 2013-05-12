import os
import subprocess

from mock import Mock
import py
import pytest

from devpi_server.config import parseoptions
from devpi_server.ctl import ensure_supervisor_started, devpictl
from devpi_server import gendeploy

pytestmark = pytest.mark.skipif("sys.platform == 'win32'")


def test_gendeploycfg(tmpdir, monkeypatch):
    monkeypatch.setattr(gendeploy, "create_crontab", lambda x, y, z: "")
    config = parseoptions(["x", "--port=3200", "--redisport=3205",
                           "--datadir=%s" % tmpdir])
    gendeploy.gendeploycfg(config, tmpdir)
    assert tmpdir.check()
    sup = tmpdir.join("etc/supervisord.conf").read()
    redis = tmpdir.join("etc/redis-devpi.conf").read()
    nginx = tmpdir.join("etc/nginx-devpi.conf").read()
    assert "--port=3200" in sup
    assert "--redisport=3205" in sup
    assert "port 3205" in redis
    assert "port 3205" in redis
    assert "proxy_pass http://localhost:3200" in nginx


def test_create_devpictl(tmpdir):
    tw = py.io.TerminalWriter()
    devpiserver = tmpdir.ensure("bin", "devpi-server")
    devpiserver.write("FIRST LINE\n")
    devpictl = gendeploy.create_devpictl(tw, tmpdir, redisport=17, httpport=18)
    assert devpictl.check()
    assert devpictl.stat().mode & py.std.stat.S_IXUSR
    firstline = devpictl.readlines(cr=0)[0]
    assert firstline == "FIRST LINE"


def test_create_crontab(tmpdir, monkeypatch):
    monkeypatch.setattr(py.path.local, "sysexec", lambda x, y: "")
    tw = py.io.TerminalWriter()
    devpictl = tmpdir.join("devpi-ctl")
    if py.path.local.sysfind("crontab"):
        cron = gendeploy.create_crontab(tw, tmpdir, devpictl)
        assert cron
        expect = "crontab %s" % tmpdir.join("crontab")
        assert expect in cron
        assert "@reboot" in tmpdir.join("crontab").read()
    else:
        pytest.skip('crontab not installed')


def test_no_user_crontab(tmpdir, monkeypatch):
    def sysexec_raise(x, y):
        raise py.process.cmdexec.Error(1, 2, x, "", "")

    monkeypatch.setattr(py.path.local, "sysexec", sysexec_raise)
    with pytest.raises(EnvironmentError):
        gendeploy.create_crontab(None, None, None)


def test_ensure_supervisor_started(tmpdir, monkeypatch):
    m = Mock()
    monkeypatch.setattr(subprocess, "check_call", m)
    tmpdir.join("supervisord.pid").write("123123")
    supconfig = tmpdir.join("etc", "supervisord.conf")
    ensure_supervisor_started(tmpdir, supconfig)
    m.assert_called_once()


def test_ensure_supervisor_started_exists(tmpdir, monkeypatch):
    m = Mock()
    monkeypatch.setattr(subprocess, "check_call", m)
    tmpdir.join("supervisord.pid").write(os.getpid())
    ensure_supervisor_started(tmpdir, None)
    assert not m.called


def test_devpictl(tmpdir, monkeypatch):
    m = Mock()
    monkeypatch.setattr(subprocess, "call", m)
    tmpdir.join("supervisord.pid").write(os.getpid())
    tmpdir.ensure("etc", "supervisord.conf")
    devpictl(str(tmpdir.join("bin", "devpi-ctl")))
    m.assert_called_once()
