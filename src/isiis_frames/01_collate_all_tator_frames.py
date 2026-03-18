import os
import json
import pickle

import tator
from tqdm import tqdm


def setup(api, PROJECT_ID, s3key_pattern):
    sections = api.get_section_list(PROJECT_ID)
    section_map = {s.tator_user_sections: s.name for s in sections}

    medias = api.get_media_list(PROJECT_ID)
    media_map = dict()

    for media in tqdm(medias):

        if not media.num_frames:
            print(f'\nMedia {media.name} ({media.id}) has no frames, skipping.')
            continue

        media_name = media.name
        if media_name.endswith( ('.mp4', '.avi')):
            media_name = media_name[:-4]

        section = section_map.get(media.attributes['tator_user_sections'], None)

        frames = dict()
        has_title_frame = section not in ['AR88_14gm','AR88_25gm']
        for f_tator in range(media.num_frames):

            if not has_title_frame: # first frame will be #1, which is what we want
                f = f_tator + 1
            else:
                if f_tator == 0:
                    continue
                f = f_tator  # to account for title frame, tator is zero indexed, but here we are not

            frame = dict(
                tator_media_id = media.id,
                tator_frame = f_tator,
                frame = f,
                image = s3key_pattern.format(media_name=media_name, frame=f),
                #state = ...,
                #localizations = ...,
            )
            frames[f_tator] = frame

        map_entry = dict(
            tator_id = media.id,
            name = media_name,
            fps = media.fps,
            section = section,
            frames = frames
        )
        if tiff_dir := media.attributes.get('tiff_dir', None):
            map_entry['tiff_dir'] = tiff_dir
        if tiff_pattern := media.attributes.get('tiff_pattern', None):
            map_entry['tiff_pattern'] = tiff_pattern
        if timestamp := media.attributes.get('timestamp', None):
            map_entry['timestamp'] = timestamp
        if note := media.attributes.get('Note', None):
            map_entry['note'] = note
        media_map[media.id] = map_entry
    return media_map


if __name__ == '__main__':
    with open('configs/tator.json') as f:
        tator_api_kwargs = json.load(f)
    tator_api = tator.get_api(**tator_api_kwargs)

    PROJECT_ID = 1
    s3key_pattern = 's3://amplify/labelstudio/isiis/frames_jpg/{media_name}/{media_name}__{frame:06d}.jpg'

    media_map = setup(tator_api, PROJECT_ID, s3key_pattern)
    print('Writing to cache...')
    with open('cache/tator_media_map.pkl', 'wb') as f:
        pickle.dump(media_map, f)

    print(len(media_map))
    m0 = media_map[list(media_map.keys())[0]]
    print(m0.keys(), m0['section'])

    frames_count = 0
    for m in media_map.values():
        frames_count += len(m['frames'])
    print('frame count:', frames_count)


