import os
import json
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm
from label_studio_sdk.client import LabelStudio

from core import LabelStudioPlus

TASKSCACHE = 'cache/tasks.pkl'
FAILEDCACHE = 'cache/from_results_csv__missing_in_mediamap.json'


with open('configs/ls_config.isiis.json') as f:
    ls_config = json.load(f)
    ls_config['s3_config'].pop('prefix') # not integrated  yet
# {
#   "host": "https://amplify-labelstudio.whoi.edu",
#   "token": "fd65f820d80ac66631102a5327f201e7d437076f",
#   "project": 1,
#   "pk": "image",
#   "s3_config": {
#     "bucket": "amplify",
#     "endpoint_url": "http://vast.whoi.edu",
#     "aws_access_key_id": "N7A3WRCAR65YMGF1TEXX",
#     "aws_secret_access_key": "NDIiIVyHlGGLKk/ETsiOvRCL8Q5GELhUxlTwqm24",
#     "prefix": "labelstudio/isiis/"
#   }
# }


def new_task_plus_predictions(client, project_id, task):
    resp = client.tasks.create(project=project_id, data=task.as_new_taskdata_dict())
    client.predictions.create(task=resp.id, **task.annotations[0].as_dict())

client = LabelStudio(base_url=ls_config['host'], api_key=ls_config['token'])
project = client.projects.get(ls_config['project'])

print(f'loading tasks from {TASKSCACHE}')
with open(TASKSCACHE, 'rb') as f:
    tasks = pickle.load(f)
    tasks = dict(sorted(tasks.items()))

lsp = LabelStudioPlus(**ls_config)
#print(f'parsing {len(tasks)} tasks...')
tasks_as_ls_dicts = (t.as_new_taskdata_dict(predictions_key='predictions') for t in tqdm(tasks.values(), desk='tasks.as_ls_dicts()'))

report,import_tasks_responses = lsp.create_tasks(tasks_as_ls_dicts, pk_datafields='image', dry_run=False)
extant_taskcount = 426_960
# print('estimating size...')
# MAX_MB = 200
# _, biggest_task, biggest_results_count = largest_by_results_count(tasks_as_ls_dicts)
# biggest_task_mb = json_size_mb(biggest_task)
# if biggest_task_mb > MAX_MB:
#     raise ValueError(f"Largest single task is {biggest_task_mb:.2f} MiB > {MAX_MB} MiB")
# total_MB_estimate = len(tasks)*biggest_task_mb  # an over-estimate
# chunk_count = total_MB_estimate//MAX_MB+1
# chunk_size = len(tasks)//chunk_count
# print(f'biggest_task_mb: {biggest_task_mb} ({biggest_results_count} results), total_MB_estimate: {total_MB_estimate}, chunk_size: {chunk_size}, chunk_amount: {chunk_count}')


# for task in tqdm(tasks.values()):
#     resp = client.tasks.create(project=project.id, data=task.as_new_taskdata_dict())
#     client.predictions.create(task=resp.id, **task.annotations[0].as_dict())

# with tqdm(total=len(tasks), desc="Uploading", dynamic_ncols=True, miniters=16) as pbar:
#     with ThreadPoolExecutor(max_workers=16) as ex:
#         futures = [ex.submit(new_task_plus_predictions, client, project.id, task) for task in tasks.values()]
#         for fut in as_completed(futures):
#             fut.result()
#             pbar.update(1)

print('Done')

exists,created = [r for r in report.values() if r['task_exists']],[r for r in report.values() if r['task_created']]
print(f'exists:{len(exists)}, created: {len(created)}, total: {len(report)}')

# from pprint import pprint
# pprint(created[0]['task'])


