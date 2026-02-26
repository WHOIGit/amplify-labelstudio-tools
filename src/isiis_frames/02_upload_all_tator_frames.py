import io
import json
import os
import pickle
from collections import defaultdict
from typing import Union, Literal

import botocore
import tator
from PIL import Image
from tqdm import tqdm

from utils_s3 import s3_client_and_bucket, s3_url_to_bucket_and_key, s3_list_objects, s3key_exists

def frame_to_s3(api, media_id, frame, s3_client, s3_key, bucket: Union[str,object]=None, skip_extant:Union[bool,list,set]=True):
    # if s3key_exists(s3_client, s3_key, bucket):
    #     print('skip')
    #     return None

    if s3_key.startswith('s3://'):
        s3_url = s3_key
        bucket_str, s3_key = s3_url_to_bucket_and_key(s3_url)
        if isinstance(bucket, str):
            assert bucket_str == bucket
        elif bucket is not None:
            assert bucket_str == bucket.name
        else:
            bucket = bucket_str

    if bucket is None:
        raise ValueError("Bucket must be specified either in s3_client config or as an argument")
    elif isinstance(bucket, str):
        bucket = s3_client.Bucket(bucket)

    if skip_extant is True:
        try: bucket.Object(s3_key).load()
        except botocore.exceptions.ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("404", "NoSuchKey"):
                return None
            else:
                raise e
    elif isinstance(skip_extant,(list,set)) and s3_key in skip_extant:
        return None

    #tmpimg = api.get_frame(media_id, frames=[frame])
    resp = api.get_frame(media_id, frames=[frame], _preload_content=False)
    img = Image.open(io.BytesIO(resp.read()))  # png
    img = img.convert("RGB")

    img_jpg = io.BytesIO()
    img.save(img_jpg, format="JPEG", quality=90, optimize=True)
    img_jpg.seek(0)

    bucket.upload_fileobj(img_jpg, s3_key,
        ExtraArgs={"ContentType": "image/jpeg"})

    return s3_key


# TODO THIS FUNCTION IS UNTESTED
def transfer_frames_parallel(frames, submit_fn, *, max_workers=64, max_in_flight=256):
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

    it = iter(frames)
    in_flight = set()

    with ThreadPoolExecutor(max_workers=max_workers) as ex, \
         tqdm(total=len(frames), desc="Uploading", dynamic_ncols=True) as pbar:

        # prime the pump
        for _ in range(min(max_in_flight, len(frames))):
            try:
                frame = next(it)
            except StopIteration:
                break
            in_flight.add(ex.submit(submit_fn, frame))

        # keep pipeline full
        while in_flight:
            done, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)

            for fut in done:
                fut.result()          # raises if failed
                pbar.update(1)

                # replace completed future with a new one (if any remain)
                try:
                    frame = next(it)
                except StopIteration:
                    continue
                in_flight.add(ex.submit(submit_fn, frame))


def transfer_frames(tator_api, s3_client, frames, bucket_name='amplify', skip_extant:Literal[True,'PRELOAD']=True, parallel=False):

    if skip_extant=='PRELOAD':
        print('loading skiplist from s3')
        skip_extant = set(s3_list_objects(s3_config, bucket_name, prefix='labelstudio/isiis/frames_jpg/'))
        print(f'{len(skip_extant)} keys in skiplist')

    upload_count = 0
    skip_count = 0
    if not parallel:
        with tqdm(frames, total=len(frames), desc="Uploading", dynamic_ncols=True) as pbar:
            for frame in frames:
                new_s3key = frame_to_s3(tator_api, frame['tator_media_id'], frame['tator_frame'], s3_client, frame['image'], bucket_name, skip_extant)
                if new_s3key: upload_count += 1
                else: skip_count += 1
                pbar.update(1)
                if pbar.n % 100 == 0:
                    pbar.set_postfix(uploaded=upload_count, skipped=skip_count)
    else:
        def submit_fn(frame):
            return frame_to_s3(tator_api, frame['tator_media_id'], frame['tator_frame'], s3_client, frame['image'], bucket_name, skip_extant)
        transfer_frames_parallel(frames, submit_fn, max_workers=16, max_in_flight=256)


def yolozone_frame_filter(media_map, results_csv):
    import csv
    from collections import defaultdict

    ar88_map = defaultdict(set)

    with open(results_csv, 'r') as f:
        reader = csv.reader(f, delimiter=' ')
        next(reader)  # Skip header
        for row in tqdm(reader, desc=f'reading "{results_csv}"'):
            # row[0] is Basler_avA2300-25gm-001-20250418T194457.801Z_100.txt
            media_name, frame_number = os.path.splitext(row[0])[0].rsplit('_', 1)
            ar88_map[media_name].add(int(frame_number))

    name_to_id = {m['name']:media_id for media_id, m in media_map.items()}

    keep_frames = []
    missing_media = []
    for media_name, frames_numbers in tqdm(ar88_map.items(), desc='keep_frames'):
        if media_name not in name_to_id.keys():
            missing_media.append(media_name)
            continue
        media_entry = media_map[name_to_id[media_name]]
        frames = [frame_dict for frame_tator_id, frame_dict in media_entry['frames'].items() if frame_tator_id in frames_numbers]
        keep_frames.extend(frames)

    return keep_frames, missing_media



if __name__ == '__main__':
    with open('configs/s3_config.amplify.json') as f:
        s3_config = json.load(f)
    s3_client, bucket = s3_client_and_bucket(s3_config)

    with open('configs/tator.json') as f:
        tator_api_kwargs = json.load(f)
    tator_api = tator.get_api(**tator_api_kwargs)

    with open('cache/tator_media_map.pkl', 'rb') as f:
        media_map = pickle.load(f)

    # frames = []
    # for m in media_map.values():
    #     frames.extend(m['frames'].values())

    frames, media_not_in_tator = yolozone_frame_filter(media_map, 'cache/AR88_yolo_concatenated_results.csv')

    transfer_frames(tator_api, s3_client, frames, skip_extant=True, parallel=False)
    print(media_not_in_tator)

    # TATOR_PROJECT_ID = 1
    #
    #
    #
    #
    # #print(frames[0])
    # frame = [f for f in frames if f['image']=='s3://amplify/labelstudio/isiis/frames_jpg/OTZ_AR43_12Mar2020_001/OTZ_AR43_12Mar2020_001__000552.jpg'][0]
    # print(frame)
    # x= frame_to_s3(tator_api, frame['tator_media_id'], frame['tator_frame'], s3_client, frame['image'], bucket)
    # print(x)


