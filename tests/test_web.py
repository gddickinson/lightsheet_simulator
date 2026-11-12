"""Web interface tests: every exported endpoint answers, the static build is complete, and the JS engine tests pass.

Run: python -m pytest -q tests/test_web.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.app import STATIC, STATIC_ENDPOINTS, app  # noqa: E402

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "static/main.js" in r.text


@pytest.mark.parametrize("path", STATIC_ENDPOINTS)
def test_endpoint(path):
    r = client.get("/api" + path)
    assert r.status_code == 200, r.text
    assert r.json() is not None


def test_static_build(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_static
    build_static.build(tmp_path / "site")
    assert (tmp_path / "site" / "index.html").read_text().count("APP_STATIC") == 1
    for path in STATIC_ENDPOINTS:
        assert (tmp_path / "site" / "api" / (path.strip("/") + ".json")).exists()


def test_static_assets_referenced_exist():
    html = (STATIC / "index.html").read_text()
    for name in ("style.css", "main.js"):
        assert f"static/{name}" in html and (STATIC / name).exists()


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_engine():
    tests = sorted(STATIC.glob("*.test.mjs"))
    for t in tests:
        r = subprocess.run(["node", str(t)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


# --- project-specific -------------------------------------------------------------------------------------------
import json  # noqa: E402

import numpy as np  # noqa: E402


def test_fixture_is_current():
    """The committed Python-vs-JS fixture still matches the Python code (tolerance: libm differs across platforms)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_engine_fixture as mf
    old = json.loads(mf.FIXTURE.read_text())
    np.testing.assert_allclose(mf._flat(old), mf._flat(mf.make()), rtol=1e-9, atol=1e-12)


def test_params_have_units():
    p = client.get("/api/params").json()
    for group in ("structure_specs", "blob_specs", "web_specs"):
        for k, s in p[group].items():
            assert {"min", "max", "default", "unit"} <= set(s), (group, k)
    assert p["structure_specs"]["cell_radius"]["unit"] == "um"
    assert p["defaults"]["voxel_um"] == [1.0, 1.0, 1.0] and p["defaults"]["size"] == [30, 100, 100]


def test_check_cases_cover_every_mode_and_cell_type():
    cases = client.get("/api/check").json()["cases"]
    assert {c["params"]["mode"] for c in cases} == {"cell", "blobs", "diffusion"}
    assert {c["params"]["cell_type"] for c in cases if c["params"]["mode"] == "cell"} == {
        "spherical", "neuron", "epithelial", "muscle"}
    for c in cases:
        assert c["shape"][2:] == [30, 100, 100] and len(c["summary"]) >= 1


def test_check_custom_post():
    r = client.post("/api/check", json={"mode": "cell", "cell_type": "muscle", "size": [10, 30, 30], "seed": 3})
    assert r.status_code == 200 and r.json()["shape"] == [1, 3, 10, 30, 30]
    assert client.post("/api/check", json={"mode": "nope"}).status_code == 400
    assert client.post("/api/check", json={"mode": "cell", "size": [500, 500, 500]}).status_code == 400


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_tiff_export_reads_back_with_scale(tmp_path):
    """tiff.js writes an ImageJ hyperstack that tifffile reads with the right shape, values and micrometre scale."""
    tifffile = pytest.importorskip("tifffile")
    from web.pipeline import build_sample, default_params
    p = dict(default_params(), mode="blobs", size=[6, 20, 24], num_volumes=2, voxel_um=[2.5, 0.4, 0.4], seed=9)
    script = tmp_path / "w.mjs"
    script.write_text(
        f"import {{ writeFileSync }} from 'node:fs';\n"
        f"import {{ buildSample }} from '{(STATIC / 'pipeline.js').as_uri()}';\n"
        f"import {{ writeTiff }} from '{(STATIC / 'tiff.js').as_uri()}';\n"
        f"writeFileSync(process.argv[3], writeTiff(buildSample(JSON.parse(process.argv[2]))));\n")
    out = tmp_path / "s.tif"
    r = subprocess.run(["node", str(script), json.dumps(p), str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    with tifffile.TiffFile(out) as f:
        arr, meta = f.asarray(), f.imagej_metadata
        xres = f.pages[0].tags["XResolution"].value
    data, _, _ = build_sample(p)
    assert arr.shape == (2, 6, 2, 20, 24)  # (t, z, c, y, x)
    np.testing.assert_allclose(arr, data.transpose(0, 2, 1, 3, 4), atol=1e-6)
    assert meta["unit"] == "micron" and meta["spacing"] == 2.5 and xres[0] / xres[1] == pytest.approx(1 / 0.4)
