import json
import pickle
import tator
from tqdm import tqdm
from time import sleep

def collate_version(media_map, tator_api, TATOR_PROJECT_ID, version_id):
    version_content = dict()

    locs = []
    chunk = 500
    locs_total = tator_api.get_localization_count(TATOR_PROJECT_ID, version=[version_id])
    print()
    for start in tqdm(range(0, locs_total, chunk), total=int(locs_total / chunk), desc=f'locs (v={version_id})'):
        locs.extend(tator_api.get_localization_list(TATOR_PROJECT_ID, start=start, stop=start + chunk))
    #locs = tator_api.get_localization_list(TATOR_PROJECT_ID, version=[version_id])

    locs = sorted(locs, key=lambda loc: (loc.media, loc.frame, loc.x, loc.y))
    states = tator_api.get_state_list(TATOR_PROJECT_ID, version=[version_id])
    states = sorted(states, key=lambda state: (state.media[0], state.frame))

    print('\nCollating states...', flush=True)
    for state in states:
        media_entry = media_map[state.media[0]]
        media_name = media_entry['name']

        if media_name not in version_content:
            media_info = dict(name = media_name,
                              fps = media_entry['fps'],
                              cruise = media_entry['section'],
                              frames = dict()
                              )
            version_content[media_name] = media_info
        else:
            media_info = version_content[media_name]

        frame_number = media_entry['frames'][state.frame]['frame']
        if frame_number in media_info['frames']:
            frame_info = media_info['frames'][frame_number]
        else:
            frame_info = media_entry['frames'][state.frame].copy()
            frame_info.pop('tator_media_id')
            frame_info.pop('tator_frame')
            frame_info['state'] = None
            frame_info['localizations'] = []
            media_info['frames'][frame_number] = frame_info

        state_info = dict(verified = state.attributes['Verified'],
                          training = state.attributes['training'],
                          holdout = state.attributes['holdout'],
                          check_me = state.attributes['check-me'],
                          note = state.attributes['Note'],
                          )

        frame_info['state'] = state_info

    print('Collating localizations...')
    for loc in locs:
        media_entry = media_map[loc.media]
        media_name = media_entry['name']

        if media_name not in version_content:
            media_info = dict(name=media_name,
                              fps=media_entry['fps'],
                              cruise=media_entry['section'],
                              frames=dict()
                              )
            version_content[media_name] = media_info
        else:
            media_info = version_content[media_name]

        try:
            frame_number = media_entry['frames'][loc.frame]['frame']
        except KeyError as e:
            if loc.frame == 0:
                print(f'SUSPECTED TITLE-FRAME LOCALIZATION IGNORED: "{media_name}" ({loc.media}) at tator-frame {loc.frame}')
                continue
            else: raise e

        if frame_number in media_info['frames']:
            frame_info = media_info['frames'][frame_number]
        else:
            frame_info = media_entry['frames'][loc.frame].copy()
            frame_info.pop('tator_media_id')
            frame_info.pop('tator_frame')
            frame_info['state'] = None
            frame_info['localizations'] = []
            media_info['frames'][frame_number] = frame_info

        loc_info = dict(x = loc.x,# - loc.width/2,
                        y = loc.y,# - loc.height/2,
                        width = loc.width,
                        height = loc.height)
        loc_info.update(loc.attributes)

        frame_info['localizations'].append(loc_info)

    return version_content


TATOR_PROJECT_ID = 1

with open('cache/tator_media_map.pkl', 'rb') as f:
    media_map = pickle.load(f)

media_keys = list(media_map.keys())
print(media_map[media_keys[0]].keys())
print(media_map[media_keys[0]]['frames'][0])

with open('configs/ls_config.isiis.json') as f:
    ls_config = json.load(f)

with open('configs/tator.json') as f:
    tator_api_kwargs = json.load(f)
tator_api = tator.get_api(**tator_api_kwargs)



versions = tator_api.get_version_list(TATOR_PROJECT_ID)
counts_per_version = {version.id:tator_api.get_localization_count(TATOR_PROJECT_ID, version=[version.id]) for version in versions}
versions = sorted(versions, key=lambda version: counts_per_version[version.id])

for version in tqdm(versions, desc='versions'):

    if version.id == 2:
        continue  # this one has ClassStrCorrection issues
    elif version.id == 25:
        continue  # this one has state training-x-holdout issue
    elif version.id in [22, 27, 24]:
        continue # it's been done!

    version_content = collate_version(media_map, tator_api, TATOR_PROJECT_ID, version_id=version.id)

    with open(f'cache/version_{version.id}.pkl', 'wb') as f:
        pickle.dump(version_content, f)
    print('Sleep two mins...', flush=True)
    sleep(120)


# {'OTZ_AR43_12Mar2020_001':
#      {  'name': 'OTZ_AR43_12Mar2020_001',
#         'cruise': 'AR43',
#         'fps': 15.0,
#         'frames': {15: {'frame': 15,
#                         'image': 's3://amplify/labelstudio/isiis/frames_jpg/OTZ_AR43_12Mar2020_001/OTZ_AR43_12Mar2020_001__000015.jpg',
#                         'localizations': [],
#                         'state': {'check_me': False,
#                                   'holdout': False,
#                                   'note': '',
#                                   'training': True,
#                                   'verified': True}},
#                    799: {'frame': 799,
#                          'image': 's3://amplify/labelstudio/isiis/frames_jpg/OTZ_AR43_12Mar2020_001/OTZ_AR43_12Mar2020_001__000799.jpg',
#                          'localizations': [{'Class': 'radiolarian',
#                                             'ClassStrCorrection': '',
#                                             'ModelName': '',
#                                             'Note': '',
#                                             'Verified': True,
#                                             'check-me': False,
#                                             'height': 0.0948239436267576,
#                                             'width': 0.0738197416067123,
#                                             'x': 0.635622330009937,
#                                             'y': 0.480038918746381}],
#                          'state': None}},
#         }}
