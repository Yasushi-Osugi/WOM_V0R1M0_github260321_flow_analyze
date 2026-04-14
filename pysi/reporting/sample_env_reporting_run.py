"""Environment-connected sample reporting runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import logging

from pysi.core.wom_pipeline import WOMPipelineRunner
from pysi.reporting.report_runner import run_reporting_pipeline


def _ensure_env_node_dict(env: Any, product: str | None = None) -> None:
    """Build env.node_dict if missing."""
    node_dict = getattr(env, "node_dict", None)
    if isinstance(node_dict, dict) and node_dict:
        return

    def iter_nodes(root):
        stack = [root]
        while stack:
            n = stack.pop()
            if n is None:
                continue
            yield n
            for c in getattr(n, "children", []) or []:
                stack.append(c)

    roots = []
    if product:
        roots.append((getattr(env, "prod_tree_dict_OT", {}) or {}).get(product))
        roots.append((getattr(env, "prod_tree_dict_IN", {}) or {}).get(product))
    else:
        roots.extend((getattr(env, "prod_tree_dict_OT", {}) or {}).values())
        roots.extend((getattr(env, "prod_tree_dict_IN", {}) or {}).values())

    built = {}
    for root in roots:
        if root is None:
            continue
        for n in iter_nodes(root):
            name = getattr(n, "name", None)
            if name and name not in built:
                built[name] = n

    setattr(env, "node_dict", built)


def get_env() -> Any:
    """Return planning env built through the repo-native WOM pipeline."""
    logging.basicConfig(level=logging.INFO)

    repo_root = Path(__file__).resolve().parents[2]
    data_dir = repo_root / "data"

    runner = WOMPipelineRunner()
    result = runner.run(
        data_dir=str(data_dir),
        product=None,
        scenario_id="default",
    )

    env = result.get("env") if isinstance(result, dict) else None
    if env is None:
        return None

    product = getattr(env, "product_selected", None)
    _ensure_env_node_dict(env, product=product)
    return env


def main() -> None:
    env = get_env()
    if env is None:
        print(
            "[sample_env_reporting_run] pipeline did not return env; "
            "using empty env input."
        )
    else:
        product = getattr(env, "product_selected", None)
        node_count = len(getattr(env, "node_dict", {}) or {})
        print(
            "[sample_env_reporting_run] env resolved from WOMPipelineRunner: "
            f"product_selected={product}, node_count={node_count}"
        )

    result = run_reporting_pipeline(
        env=env,
        output_dir="outputs/reporting_mvp/sample_env_reporting_run",
        #@CHANGED
        apply_allocation=True,
    )

    print("[sample_env_reporting_run] report exported:")
    for key, path in sorted(result["exported"].items()):
        print(f"  - {key}: {path}")


if __name__ == "__main__":
    main()