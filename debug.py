import sys
sys.path.insert(0, '.')
try:
    from scripts.run_condition import load_conditions
    print('Loaded conditions OK')
    conds = load_conditions()
    print(f'Found {len(conds)} conditions')
    print(f'Condition 01 exists: {"01" in conds}')
except Exception as e:
    import traceback
    print(f'Error: {e}')
    traceback.print_exc()
