from pprint import pprint
import tator
import json

task_data = 'cruise media media_fps frame image'.split()
task_fields = 'check-me holdout note training verified'.split()
task_rect_fields = 'class ClassStrCorrection'.split()

with open('configs/tator.json') as f:
    tator_api_kwargs = json.load(f)
tator_api = tator.get_api(**tator_api_kwargs)

leafs = tator_api.get_leaf_list(1)
# {'attributes': {},
#  'id': 305,
#  'name': 'salp_solitary',
#  'parent': 286,
#  'path': 'ISIIS.Classes.chordate.salpa_aspera.salp_solitary',
#  'project': 1,
#  'type': 3}

leafs = sorted([leaf.path.split('.',2)[-1] for leaf in leafs])
if 'Classes' in leafs:
    leafs.pop(leafs.index('Classes'))
pprint(leafs)

def list_to_tree(items):
    tree = {}

    for item in items:
        parts = item.split(".")
        current = tree

        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]

    def build_output(d):
        result = []
        for key, value in sorted(d.items()):
            node = {"value": key}
            if value:  # if has children
                node["children"] = build_output(value)
            result.append(node)
        return result

    return {"items": build_output(tree)}

taxonomy = list_to_tree(leafs)
pprint(taxonomy, sort_dicts=False)

json_str = json.dumps(taxonomy, indent=2)
json_str = json_str.replace('{\n      "','{ "').replace('"\n      }','" }')
json_str = json_str.replace('{\n          "','{ "').replace('"\n        }','" }')
json_str = json_str.replace('{\n            "','{ "').replace('"\n          }','" }')
json_str = json_str.replace('{\n              "','{ "').replace('"\n            }','" }')

with open('cache/classes.Taxonomy.json', 'w') as f:
    f.write(json_str)

# TODO send to apiUrl= "s3://amplify/labelstudio/isiis/classes.Taxonomy.json"

