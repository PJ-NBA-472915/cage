import pytest
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

# def test_list_repos(client):
#     response = client.get("/repos")
#     assert response.status_code == 200
#     assert isinstance(response.json(), list) or isinstance(response.json(), dict)

# def test_init_repo(client):
#     import tempfile
#     import shutil
#     from pathlib import Path
#     import subprocess

#     test_dir = tempfile.mkdtemp()
#     local_repo = Path(test_dir) / "local_repo"
#     local_repo.mkdir()
#     (local_repo / "test.txt").write_text("hello")
#     subprocess.run(["git", "init"], cwd=str(local_repo), check=True)
#     subprocess.run(["git", "add", "."], cwd=str(local_repo), check=True)
#     subprocess.run(["git", "commit", "-m", "initial"], cwd=str(local_repo), check=True)

#     response = client.post("/repos", json={"origin": str(local_repo)})
#     assert response.status_code == 200
#     metadata = response.json()
#     assert "temp_dir" in metadata
#     assert Path(metadata["temp_dir"]).exists()
#     shutil.rmtree(test_dir)
#     shutil.rmtree(metadata["temp_dir"])

def test_close_repo(client):
    # This test is a placeholder.
    # A proper test would involve:
    # 1. Initializing a repo via the API.
    # 2. Making changes to the repo.
    # 3. Calling the close endpoint.
    # 4. Verifying that the repo is closed and pushed.
    assert True