from types import SimpleNamespace
import sys
import types


def _ensure_matplotlib_stub():
    if "matplotlib" in sys.modules and "matplotlib.pyplot" in sys.modules:
        return
    matplotlib_stub = types.ModuleType("matplotlib")
    pyplot_stub = types.ModuleType("matplotlib.pyplot")
    backends_stub = types.ModuleType("matplotlib.backends")
    backend_tkagg_stub = types.ModuleType("matplotlib.backends.backend_tkagg")
    backend_tkagg_stub.FigureCanvasTkAgg = object
    animation_stub = types.ModuleType("matplotlib.animation")
    animation_stub.FuncAnimation = object
    figure_stub = types.ModuleType("matplotlib.figure")
    figure_stub.Figure = object
    matplotlib_stub.pyplot = pyplot_stub
    matplotlib_stub.use = lambda *_args, **_kwargs: None
    sys.modules.setdefault("matplotlib", matplotlib_stub)
    sys.modules.setdefault("matplotlib.pyplot", pyplot_stub)
    sys.modules.setdefault("matplotlib.backends", backends_stub)
    sys.modules.setdefault("matplotlib.backends.backend_tkagg", backend_tkagg_stub)
    sys.modules.setdefault("matplotlib.figure", figure_stub)
    sys.modules.setdefault("matplotlib.animation", animation_stub)


_ensure_matplotlib_stub()
sys.modules.setdefault("networkx", types.ModuleType("networkx"))
from pysi.gui.cockpit_tk import WOMCockpit


def test_open_explicit_pipeline_kpi_view_calls_builder_and_renderer(monkeypatch):
    calls = {}

    fake_env = object()
    fake_self = SimpleNamespace(env=fake_env)
    fake_view_model = {"available": True}
    fake_window = object()

    def fake_builder(env):
        calls["env"] = env
        return fake_view_model

    def fake_renderer(parent, view_model):
        calls["parent"] = parent
        calls["view_model"] = view_model
        return fake_window

    monkeypatch.setattr(
        "pysi.gui.explicit_pipeline_management_cockpit_view.build_explicit_pipeline_management_cockpit_view_model",
        fake_builder,
    )
    monkeypatch.setattr(
        "pysi.gui.explicit_pipeline_management_cockpit_view.render_explicit_pipeline_management_cockpit_tk",
        fake_renderer,
    )

    result = WOMCockpit._open_explicit_pipeline_kpi_view(fake_self)

    assert result is fake_window
    assert calls["env"] is fake_env
    assert calls["parent"] is fake_self
    assert calls["view_model"] is fake_view_model
