from pysi.cost.load_cost_masters import load_cost_masters
m = load_cost_masters("./data/cost_masters")
print(m.summary())