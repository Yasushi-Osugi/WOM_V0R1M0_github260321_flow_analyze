git restore data\kpi_summary.csv
git restore data\node_money_eval.csv
git restore data\product_money_summary.csv

del data\node_price_waterfall.csv
del data\price_propagation_trace.csv
rmdir /s /q outputs\run_full_plan

git status