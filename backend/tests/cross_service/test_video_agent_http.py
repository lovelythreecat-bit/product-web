"""Run both repositories' production code over HTTP, with isolated local media.

Run from backend: python -m pytest tests/cross_service/test_video_agent_http.py -q
Requires the sibling videoAgent checkout and FFmpeg. No provider calls or live DB writes.
"""

import importlib
import shutil
import socket
import sys
import time
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import Thread
from uuid import uuid4

import pytest
import uvicorn
from cryptography.fernet import Fernet
from PIL import Image

from app.agents.media_http import MediaServiceError
from app.agents.video import VideoAgentAdapter, VideoAgentProfile


@pytest.fixture
def video_runtime(tmp_path, monkeypatch):
    sibling = Path(__file__).resolve().parents[4] / "videoAgent"
    if not (sibling / "api_app" / "app.py").is_file():
        pytest.skip("Requires sibling videoAgent checkout")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Requires FFmpeg and ffprobe")
    monkeypatch.syspath_prepend(str(sibling))
    # Use the sibling's already installed extra dependencies (multipart), while
    # keeping the web interpreter's installed dependencies first in resolution.
    extra_packages = sibling / ".venv" / "Lib" / "site-packages"
    if extra_packages.is_dir():
        monkeypatch.setattr(sys, "path", [*sys.path, str(extra_packages)])
    create_app = importlib.import_module("api_app.app").create_app
    Database = importlib.import_module("video_agent.db").Database
    SettingsService = importlib.import_module("video_agent.settings_service").SettingsService
    VideoAgent = importlib.import_module("video_agent.service").VideoAgent
    RuntimeSettings = importlib.import_module("video_agent.runtime").RuntimeSettings
    SettingsPatch = importlib.import_module("video_agent.config").SettingsPatch
    ratios = importlib.import_module("video_agent.config").RATIO_PAIRS
    runtime = RuntimeSettings(
        home=tmp_path,
        business_token="TEST_ONLY_business",
        admin_token="TEST_ONLY_admin",
        secret_key=Fernet.generate_key().decode(),
    )
    db = Database(tmp_path)
    settings = SettingsService(db, runtime.secret_key)
    current = settings.read_settings()
    settings.save_settings(
        SettingsPatch(
            default_duration=5,
            video_bitrate=200000,
            resolutions={r: (w * 20, h * 20) for r, (w, h) in ratios.items()},
        ),
        expected_version=current.configuration_revision,
    )
    agent = VideoAgent(tmp_path, database=db, settings_service=settings)
    app = create_app(runtime, agent=agent, settings_service=settings)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    address = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, "Video HTTP server did not start"
        yield agent, settings, address
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        db.close()


def test_workspace_adapter_to_actual_video_api_and_original_mp4(video_runtime):
    agent, settings, address = video_runtime
    file_id, external, user = str(uuid4()), str(uuid4()), str(uuid4())
    image = BytesIO()
    Image.new("RGB", (64, 64), "tan").save(image, "PNG")
    data = image.getvalue()
    material = dict(
        file_id=file_id,
        version="v1",
        content=data,
        media_type="image/png",
        sha256=sha256(data).hexdigest(),
    )
    snapshot = dict(
        user_id=user,
        input_snapshot=dict(
            product={"name": "测试杯", "sellingPoints": "保温"},
            instruction="展示杯子",
            parameters={"first_frame_file_id": file_id},
            material_versions=[{"file_id": file_id, "version": "v1"}],
        ),
    )
    state = {}

    def adapter():
        return VideoAgentAdapter(
            profile=VideoAgentProfile(
                base_url=address,
                service_key="TEST_ONLY_business",
                max_result_bytes=16 * 1024 * 1024,
            ),
            external_submission_id=external,
            material_loader=lambda: [material],
            load_state=lambda: deepcopy(state),
            save_state=lambda patch: state.update(deepcopy(patch)),
        )

    client = adapter()
    submitted = client.submit(snapshot, external)
    assert submitted.status == "ACCEPTED", state
    task_id = submitted.upstream_task_id
    assert client.submit(snapshot, external).upstream_task_id == task_id
    for _ in range(12):
        if agent.get_task(task_id).status == "awaiting_confirmation":
            break
        assert agent.tick().did_work
    found = client.query_by_external(external)
    assert found.state == "RUNNING"
    assert state["status"] == "awaiting_confirmation"
    assert (
        state["plan"]["document"]["first_frame_asset_id"]
        == state["request_body"]["first_frame_asset_id"]
    )
    assert agent.get_task(task_id).generation_id is None  # Polling never confirms.
    version = state["head_plan_version"]
    client.confirm(version, "TEST_ONLY_confirm")
    generation = state["generation_id"]
    assert client.confirm(version, "TEST_ONLY_confirm")["generation_id"] == generation
    for _ in range(100):
        view = agent.get_generation(generation)
        assert view.status != "failed", view.model_dump()
        if view.status == "succeeded":
            break
        if not agent.tick().did_work:
            time.sleep(0.02)
    assert agent.get_generation(generation).status == "succeeded"
    # Current admin settings cannot retroactively alter this generation's checks.
    current = settings.read_settings()
    settings.save_settings(
        importlib.import_module("video_agent.config").SettingsPatch(default_duration=10),
        expected_version=current.configuration_revision,
    )
    resumed = adapter()
    outcome = resumed.query(task_id)
    assert outcome.state == "RESULT_READY", {"state": state, "outcome": outcome.model_dump()}
    artifact = resumed.client.json("GET", f"/api/v1/tasks/{task_id}/artifacts")[1][0]
    assert artifact["quality_status"] == "not_assessed"
    assert artifact["visual_check_enabled"] is False
    item = outcome.result.items[0]
    original = resumed.retrieve_original(item.locator)
    assert original.status == "AVAILABLE"
    assert sha256(original.content).hexdigest() == item.sha256
    downloaded = agent.home / "workspace-download.mp4"
    downloaded.write_bytes(original.content)
    info = importlib.import_module("video_agent.media").probe(downloaded)
    assert (info.width, info.height, info.frame_count) == (180, 320, 150)
    with agent.db.transaction(write=False) as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"] == 1
        assert conn.execute("SELECT COUNT(*) AS n FROM generations").fetchone()["n"] == 1


def test_actual_business_key_reports_missing_admin_permission(video_runtime):
    _, _, address = video_runtime
    adapter = VideoAgentAdapter(
        profile=VideoAgentProfile(
            base_url=address, service_key="TEST_ONLY_business", max_result_bytes=1024
        )
    )
    with pytest.raises(MediaServiceError) as error:
        adapter.client.json("GET", "/api/v1/admin/settings")
    assert "管理 Key" in (error.value.public_message or "")
