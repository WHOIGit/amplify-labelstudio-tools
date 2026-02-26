import pickle

import json

with open('cache/version_22.pkl', 'rb') as f:
    version_content = pickle.load(f)

from pprint import pprint

pprint(version_content)

task_data = 'cruise media media_fps frame image'.split()
task_fields = 'check-me holdout note training verified'.split()
task_rect_fields = 'class roi-verified roi-checkme ClassStrCorrection|Note'.split()

# for each frame, build list of task dicts
# upload those

# for each task, cross reference with cached frames
# for each task, if frame and rois are verified, create annotation
#                else: create prediction

media0 = list(version_content.keys())[0]
media = version_content['OTZ_AR43_12Mar2020_001']
frame = media['frames'][552]

task_data = dict(
    cruise = media['cruise'],
    media = media['name'],
    media_fps = media['fps'],
    frame = frame['frame'],
    image = frame['image'],
)

with open('configs/ls_config.isiis.json') as f:
    ls_config = json.load(f)
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

from label_studio_sdk.client import LabelStudio

client = LabelStudio(base_url=ls_config['host'], api_key=ls_config['token'])
project = client.projects.get(ls_config['project'])
#x = client.tasks.create(project=project.id, data=task_data)

# TODO next comes annotation/prediction
