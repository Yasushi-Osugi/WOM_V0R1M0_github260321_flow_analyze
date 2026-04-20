from wom_cockpit.services.delta_detector import compare_snapshots
from wom_cockpit.services.fact_extractor import extract_management_facts
from wom_cockpit.services.issue_engine import generate_issues
from wom_cockpit.ui.cockpit_view_model import build_cockpit_view_model
from wom_cockpit.ui.scenario_compare_presenter import present_scenario_compare
from wom_cockpit.services.narrative_service import render_narrative_text

plan_delta = compare_snapshots(baseline_snapshot, scenario_snapshot)
facts = extract_management_facts(plan_delta)
issues = generate_issues(facts, group_similar_facts=False)
vm = build_cockpit_view_model(plan_delta, issues)

presentation = present_scenario_compare(vm)
print(presentation.header_title)
print(presentation.summary_text)

narrative_text = render_narrative_text(vm)
print(narrative_text)