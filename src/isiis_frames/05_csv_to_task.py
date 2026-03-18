import os
import json
import pickle

from tqdm import tqdm

from task_class import *

import yaml
with open('cache/data.yaml') as f:
    CLASSNAMES = yaml.safe_load(f)
    CLASSNAMES = CLASSNAMES.get('names', None)

with open('cache/classes.Taxonomy.json') as f:
    taxonomy = json.load(f)

def build_value_paths(data):
    result = {}

    def traverse(node, path):
        current_value = node["value"]
        current_path = path + [current_value]

        # Store the path for this value
        result[current_value] = current_path

        # Recurse into children if they exist
        for child in node.get("children", []):
            traverse(child, current_path)

    # Start traversal from each top-level item
    for item in data.get("items", []):
        traverse(item, [])

    return result

CLASS_TO_TAXONOMY = build_value_paths(taxonomy)

def row_to_roi(row):
    # row[1] is class_idx, row[6] is score
    # row[2,3,4,5] are x,y,w,h
    bbox = BBox.from_yolo(x_center=float(row[2]),
                          y_center=float(row[3]),
                          width=float(row[4]),
                          height=float(row[5]))
    class_name = CLASSNAMES[int(row[1])]
    taxonomy_path = CLASS_TO_TAXONOMY[class_name]

    roi = IsiisRoi(bbox, taxonomy_path, score=float(row[6]))
    return roi


def parse_results_csv(media_map, results_csv, include_all_media_frames=False):
    import csv

    name_to_id = {m['name']: media_id for media_id, m in media_map.items()}

    tasks = dict()
    from_results_csv__missing_in_mediamap = set()
    for media_tator_id, media_entry in media_map.items():
        for frame_tator_id, frame_dict in media_entry['frames'].items():
            key = (media_tator_id, frame_tator_id)
            tasks[key] = IsiisTask(
                cruise = media_entry['section'],
                media = media_entry['name'],
                media_fps = media_entry['fps'],
                frame = frame_dict['frame'],
                image = frame_dict['image'],
            )

    with open(results_csv, 'r') as f:
        reader = csv.reader(f, delimiter=' ')
        next(reader)  # Skip header
        for row in tqdm(reader, desc=f'reading "{results_csv}"'):
            # row[0] is Basler_avA2300-25gm-001-20250418T194457.801Z_100.txt
            # row[1] is class_idx, row[6] is score
            # row[2,3,4,5] are x,y,w,h
            media_name, frame_number = os.path.splitext(row[0])[0].rsplit('_', 1)

            try:
                media_id = name_to_id[media_name]
            except KeyError:
                from_results_csv__missing_in_mediamap.add((media_name,None,int(frame_number)))
                continue
            try:
                task:IsiisTask = tasks[(media_id,int(frame_number))]
            except KeyError:
                from_results_csv__missing_in_mediamap.add((media_name, media_id, int(frame_number)))
                continue

            if not task.annotations:
                new_annotation = IsiisAnnotation(model_version='train7',
                    #original_width=..., original_height=...,
                )
                tasks[(media_id,int(frame_number))].annotations.append(new_annotation)
            roi = row_to_roi(row)
            tasks[(media_id,int(frame_number))].annotations[0].rois.append(roi)


    if include_all_media_frames:
        for task in tasks.values():
            if not task.annotations:
                task.annotations.append(IsiisAnnotation(model_version='train7'))
    else:
        tasks = {key:task for key,task in tasks.items() if task.annotations}

    return tasks, from_results_csv__missing_in_mediamap



if __name__ == '__main__':
    import os
    from collections import defaultdict

    TASKSCACHEDIR = 'cache/tasks'
    FAILEDCACHE = 'cache/from_results_csv__missing_in_mediamap.json'

    existing_jsonl = [f for f in os.listdir(TASKSCACHEDIR) if f.endswith('_tasks.jsonl')] if os.path.isdir(TASKSCACHEDIR) else []

    if existing_jsonl:
        print(f'cache exists ({len(existing_jsonl)} media files in {TASKSCACHEDIR}/), skipping rebuild')
    else:
        results_csv = 'cache/AR88_yolo_concatenated_results.csv'

        with open('cache/tator_media_map.pkl', 'rb') as f:
            media_map = pickle.load(f)

        tasks, from_results_csv__missing_in_mediamap = parse_results_csv(media_map, results_csv, include_all_media_frames=True)
        print(f'built {len(tasks)} tasks across {len({t.media for t in tasks.values()})} media')
        print(f'missing: {len(from_results_csv__missing_in_mediamap)}')

        with open(FAILEDCACHE, 'w') as f:
            json.dump(sorted(from_results_csv__missing_in_mediamap, key=lambda t: (t[0], t[2], t[1] is None, t[1] or 0)), f)

        # Group tasks by media
        media_tasks = defaultdict(list)
        for task in tasks.values():
            media_tasks[task.media].append(task)

        os.makedirs(TASKSCACHEDIR, exist_ok=True)

        summary = {}
        agg = {'frames_with_rois': 0, 'frames_without_rois': 0, 'total_rois': 0}
        skipped_media = []

        SKIP_EMPTY_MEDIA = True  # set False to write JSONL even for media with no ROIs

        for media_name, task_list in tqdm(sorted(media_tasks.items()), desc='writing task files'):
            task_list.sort(key=lambda t: t.frame)

            with_rois = 0
            without_rois = 0
            roi_count = 0

            for task in task_list:
                n_rois = sum(len(a.rois) for a in task.annotations)
                if n_rois > 0:
                    with_rois += 1
                else:
                    without_rois += 1
                roi_count += n_rois

            if SKIP_EMPTY_MEDIA and roi_count == 0:
                skipped_media.append(media_name)
                continue

            filepath = os.path.join(TASKSCACHEDIR, f'{media_name}_tasks.jsonl')
            with open(filepath, 'w') as f:
                for task in task_list:
                    f.write(json.dumps(task.to_dict()) + '\n')

            summary[media_name] = {
                'frames_with_rois': with_rois,
                'frames_without_rois': without_rois,
                'total_rois': roi_count,
                'total_frames': with_rois + without_rois,
            }
            agg['frames_with_rois'] += with_rois
            agg['frames_without_rois'] += without_rois
            agg['total_rois'] += roi_count

        agg['total_frames'] = agg['frames_with_rois'] + agg['frames_without_rois']
        summary['_aggregate'] = agg
        summary['_skipped_empty_media'] = skipped_media

        with open(os.path.join(TASKSCACHEDIR, 'summary.json'), 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"aggregate: {agg}")


# todo next steps
#  parse AR88_yolo_concatenated_results.csv to task data + task predictions
#   - class names in cache/data.yaml. model name is "train7", cruise is AR88
#  if there's a tator link, then it exists on tator, yay. push frames into s3 with correct keys
#  upload task and predictions to label studio


'''
>>> head cache/AR88_yolo_concatenated_results.csv -n3
filename class_id x_center y_center width height confidence
Basler_avA2300-25gm-001-20250418T194457.801Z_100.txt 11 0.0582358 0.664 0.0211367 0.0251275 0.691623
Basler_avA2300-25gm-001-20250418T194457.801Z_100.txt 11 0.88572 0.296244 0.0229084 0.0238131 0.686119

>>> head cache/20250418_AR88.csv -n3
media_path,media,media_time,frame,times,status,id,link
/proj/nes-lter/Stingray/data/NESLTER_AR88/Basler_avA2300-25gm/20250418T194457.801Z/Basler_avA2300-25gm-001-20250418T194457.801Z.avi,Basler_avA2300-25gm-001-20250418T194457.801Z,2025-04-18 19:44:57.801,0.0,2025-04-18 19:44:57.867667,ok,25634.0,https://tator.whoi.edu/1/annotation/25634?frame=0
/proj/nes-lter/Stingray/data/NESLTER_AR88/Basler_avA2300-25gm/20250418T194457.801Z/Basler_avA2300-25gm-001-20250418T194457.801Z.avi,Basler_avA2300-25gm-001-20250418T194457.801Z,2025-04-18 19:44:57.801,1.0,2025-04-18 19:44:57.934334,ok,25634.0,https://tator.whoi.edu/1/annotation/25634?frame=1
'''
