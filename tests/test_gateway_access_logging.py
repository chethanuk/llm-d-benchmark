"""Tests for gateway.accessLogging in 11_infra.yaml.j2.

Only the default (Istio) branch maps the key to
``gateway.gatewayParameters.istio.accessLogging``. When the key is unset the
output is unchanged, and other gateway classes never get an ``istio`` key.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from llmdbenchmark.parser.render_plans import RenderPlans

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "templates"
    / "jinja"
    / "11_infra.yaml.j2"
)

_UNSET = object()


@pytest.fixture(scope="module")
def template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


@pytest.fixture
def renderer():
    r = RenderPlans.__new__(RenderPlans)
    r.logger = MagicMock()
    r._jinja_env = None
    return r


def _render(renderer, template, gw_class, access_logging=_UNSET) -> dict:
    gateway = {
        "className": gw_class,
        "logLevel": "error",
        "service": {"type": "NodePort"},
        "resources": {
            "limits": {"cpu": "16", "memory": "16Gi"},
            "requests": {"cpu": "4", "memory": "4Gi"},
        },
    }
    if access_logging is not _UNSET:
        gateway["accessLogging"] = access_logging
    values = {
        "standalone": {"enabled": False},
        "kustomize": {"enabled": False},
        "gateway": gateway,
        "model_id_label": "model-1",
        "namespace": {"name": "llmdbench"},
    }
    return yaml.safe_load(renderer._render_template(template, values))


@pytest.mark.parametrize("gw_class", ["istio", "custom-istio-class"])
@pytest.mark.parametrize("value", [False, True, "false", "true"])
def test_istio_renders_boolean(renderer, template, gw_class, value):
    doc = _render(renderer, template, gw_class, value)
    expected = str(value).lower() == "true"
    assert doc["gateway"]["gatewayParameters"]["istio"] == {"accessLogging": expected}


@pytest.mark.parametrize("gw_class", ["istio", "custom-istio-class"])
def test_istio_unset_omits_istio_key(renderer, template, gw_class):
    doc = _render(renderer, template, gw_class)
    assert "istio" not in doc["gateway"]["gatewayParameters"]


@pytest.mark.parametrize("gw_class", ["istio", "custom-istio-class"])
def test_istio_null_omits_istio_key(renderer, template, gw_class):
    """An empty YAML key must not render the truthy string 'none'."""
    doc = _render(renderer, template, gw_class, None)
    assert "istio" not in doc["gateway"]["gatewayParameters"]


@pytest.mark.parametrize(
    "gw_class", ["agentgateway", "gke", "data-science-gateway-class"]
)
@pytest.mark.parametrize("value", [_UNSET, False, True])
def test_other_classes_have_no_istio_key(renderer, template, gw_class, value):
    doc = _render(renderer, template, gw_class, value)
    assert "istio" not in doc["gateway"].get("gatewayParameters", {})
