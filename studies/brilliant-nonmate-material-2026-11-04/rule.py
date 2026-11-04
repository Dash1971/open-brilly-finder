"""Fixed prior mating rule, excluding known or uncertain material-win alternatives."""
import json
from pathlib import Path
from base_rule import mating_rule as original_mating_rule
FEATURES = json.loads((Path(__file__).parent/'FEATURES.json').read_text())
def mating_rule(case):
    if not original_mating_rule(case):
        return False
    return all(FEATURES[case['key']][w]['nonmate_material_win'] == 0 for w in ['current','previous'])
