from config.logging import new_trace_id, setup_logging, trace_id_var


def test_new_trace_id_sets_contextvar():
    tid = new_trace_id()
    assert len(tid) == 12
    assert trace_id_var.get() == tid


def test_setup_logging_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    setup_logging()
