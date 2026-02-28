from app.skills import code_exec


def test_code_exec_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ARCHILLX_ENABLE_CODE_EXEC", raising=False)
    res = code_exec.run({"code": "print(1)"})
    assert res["success"] is False
    assert res["backend"] in {"process", "docker"}


def test_code_exec_process_backend_success(monkeypatch):
    monkeypatch.setenv("ARCHILLX_ENABLE_CODE_EXEC", "true")
    monkeypatch.setenv("ARCHILLX_SANDBOX_BACKEND", "process")
    res = code_exec.run({"code": "print(6*7)"})
    assert res["success"] is True
    assert "42" in (res.get("stdout") or "")
    assert res.get("worker_mode") is True
    assert res.get("run_id")


def test_code_exec_docker_preflight_failure(monkeypatch):
    monkeypatch.setenv("ARCHILLX_ENABLE_CODE_EXEC", "true")
    monkeypatch.setenv("ARCHILLX_SANDBOX_BACKEND", "docker")
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_USER", "0:0")
    monkeypatch.setenv("ARCHILLX_SANDBOX_REQUIRE_NON_ROOT_USER", "true")
    monkeypatch.setenv("ARCHILLX_SANDBOX_REQUIRE_SECCOMP_PROFILE", "false")
    res = code_exec.run({"code": "print(1)"})
    assert res["success"] is False
    assert res["backend"] == "docker"
    assert res.get("preflight")
