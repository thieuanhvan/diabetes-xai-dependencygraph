"""Load the UNEDITED vendored CARLA files (commit 24db00aa8616eb2faedea0d6edf6e307cee9d192) without the rest of
the CARLA package: `carla.log`, `carla.models.api.MLModel` and `carla.recourse_methods.processing` are provided by
minimal shims, so the vendored source files themselves run byte for byte. Used by the parity tests only
(Wachter) and by the Growing Spheres port (sampling helper `hyper_sphere_coordindates`)."""
from __future__ import annotations

import hashlib
import importlib.util
import logging
import sys
import types
from pathlib import Path

VENDOR = Path(__file__).resolve().parent / "vendor" / "carla_24db00a"
COMMIT = "24db00aa8616eb2faedea0d6edf6e307cee9d192"
FILES = {
    "LICENSE": "67dc3f15d0341b89d6bd1fb7a3968fa7b95ead6d25409a6f9883ee34de120697",
    "carla/models/catalog/ANN_TORCH/model_ann.py": "7d1ec8511ae624d7336ff38206458f93a8237280113663f730e6f55a990616c3",
    "carla/recourse_methods/catalog/actionable_recourse/model.py": "8e1f4acb5f7461bc2ecabca838fc165657c27e29dd59b108b58188ae943c84d3",
    "carla/recourse_methods/catalog/growing_spheres/library/gs_counterfactuals.py": "7b6a4dded0364ae472d6fb996b80cdca2a5412b68071e22978520ef80e4f65a1",
    "carla/recourse_methods/catalog/growing_spheres/model.py": "8ff28cb6c13cdb0710c04fb6403b77154975be67697a23937532d24da9290f7e",
    "carla/recourse_methods/catalog/wachter/library/wachter.py": "90326aa9f810d586e4f6b2b4335037dbd7a7315b39b69bc5fd0f716e5751675e",
    "carla/recourse_methods/catalog/wachter/model.py": "35c1f1b8e8aef9eec188f13f8813c80a94f862c8b3c1a36c5fb8c9a8ac95921a",
    "carla/recourse_methods/processing/counterfactuals.py": "5a6300ddd64156d7dcdfd9b13e1a98184ee85cea117c01b97a5a0e59288f1d61",
}


def verify() -> None:
    for rel, h in FILES.items():
        got = hashlib.sha256((VENDOR / rel).read_bytes()).hexdigest()
        if got != h:
            raise SystemExit(f"vendored file changed: {rel} {got}")


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, VENDOR / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _shims():
    if "carla" in sys.modules and getattr(sys.modules["carla"], "_p7_shim", False):
        return
    carla = types.ModuleType("carla")
    carla._p7_shim = True
    carla.log = logging.getLogger("carla_vendored")
    sys.modules["carla"] = carla
    models = types.ModuleType("carla.models")
    api = types.ModuleType("carla.models.api")
    api.MLModel = object
    sys.modules["carla.models"] = models
    sys.modules["carla.models.api"] = api
    rm = types.ModuleType("carla.recourse_methods")
    sys.modules["carla.recourse_methods"] = rm
    cf = _load("carla.recourse_methods.processing.counterfactuals", "carla/recourse_methods/processing/counterfactuals.py")
    proc = types.ModuleType("carla.recourse_methods.processing")
    proc.reconstruct_encoding_constraints = cf.reconstruct_encoding_constraints
    proc.check_counterfactuals = cf.check_counterfactuals
    proc.merge_default_parameters = cf.merge_default_parameters
    sys.modules["carla.recourse_methods.processing"] = proc


def carla_wachter():
    """The unedited CARLA wachter_recourse."""
    verify()
    _shims()
    return _load("carla_vendored_wachter", "carla/recourse_methods/catalog/wachter/library/wachter.py").wachter_recourse


def carla_gs():
    """The unedited CARLA growing-spheres module (hyper_sphere_coordindates, growing_spheres_search)."""
    verify()
    _shims()
    return _load("carla_vendored_gs", "carla/recourse_methods/catalog/growing_spheres/library/gs_counterfactuals.py")


def carla_ann():
    verify()
    return _load("carla_vendored_ann", "carla/models/catalog/ANN_TORCH/model_ann.py").AnnModel
