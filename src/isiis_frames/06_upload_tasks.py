import os
import json
import glob
import time
import datetime as dt

import httpx
from tqdm import tqdm

from task_class import IsiisTask
from labelstudio_tools import TaskManager

TASKSCACHEDIR = 'cache/tasks'

jsonl_files = sorted(glob.glob(os.path.join(TASKSCACHEDIR, '*_tasks.jsonl')))
print(f'found {len(jsonl_files)} task files in {TASKSCACHEDIR}/')

tm = TaskManager.from_config('configs/ls_config.isiis.BRICK.json')

total_exists = 0
total_created = 0

for filepath in tqdm(jsonl_files, desc='media files'):
    with open(filepath) as f:
        tasks_as_ls_dicts = [IsiisTask.from_dict(json.loads(line)).as_new_taskdata_dict(predictions_key='predictions') for line in f]

    medias = {t['data']['media'] for t in tasks_as_ls_dicts}
    media_filter = {
        'conjunction': 'or',
        'items': [{'filter': 'filter:tasks:data.media', 'operator': 'equal', 'value': m, 'type': 'String'} for m in medias],
    }
    tm.cached_tasks = tm.get_tasks(filter_dict=media_filter, limit_fields_to=['id', 'data'])
    tm.cached_tasks_timestamp = dt.datetime.now()

    for attempt in range(1, 12):
        try:
            report, import_tasks_responses = tm.create_tasks(tasks_as_ls_dicts, pk_datafields='image', dry_run=False, force_recache=False)
            break
        except httpx.ReadTimeout:
            if attempt == 11:
                raise
            wait = 5 * attempt
            tqdm.write(f'ReadTimeout on attempt {attempt} for {medias}, retrying in {wait}s...')
            time.sleep(wait)

    exists  = sum(1 for r in report.values() if r['task_exists'])
    created = sum(1 for r in report.values() if r['task_created'])
    total_exists += exists
    total_created += created

print(f'exists:{total_exists}, created: {total_created}, total: {total_exists + total_created}')
