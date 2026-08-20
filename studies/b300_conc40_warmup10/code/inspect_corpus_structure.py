import json
from collections import Counter

p = "/tmp/b300_conc40_analysis/corpus_prefix_500m.bin"
outer_types = Counter()
outer_keys = Counter()
nested_fields = Counter()
nested_item_keys = Counter()
examples = {}
with open(p) as f:
    for row_i, line in enumerate(f):
        if row_i >= 94:
            break
        x = json.loads(line)
        for outer_i, req in enumerate(x["requests"]):
            outer_types[str(req.get("type"))] += 1
            outer_keys[tuple(sorted(req))] += 1
            for k, v in req.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    nested_fields[k] += 1
                    nested_item_keys[tuple(sorted(v[0]))] += 1
                    examples.setdefault(k, (row_i, outer_i, len(v), sorted(v[0])))
print("outer_types", outer_types)
print("outer_key_shapes")
for k, v in outer_keys.most_common():
    print(v, k)
print("nested_fields", nested_fields)
print("nested_item_key_shapes")
for k, v in nested_item_keys.most_common():
    print(v, k)
print("nested_examples", examples)
