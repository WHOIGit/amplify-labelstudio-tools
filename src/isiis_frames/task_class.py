from typing import Literal

from labelstudio_tools.taskclass import BBox, ResultField, BaseRegion, BaseAnnotation, BaseTask


# Re-export BBox so existing imports continue to work
__all__ = ['BBox', 'IsiisRoi', 'IsiisAnnotation', 'IsiisTask']


# ResultField descriptors for ISIIS Label Studio config
_RF_ROI          = ResultField('roi',          'image', 'rectangle')
_RF_ROI_CLASS    = ResultField('roi_class',    'image', 'taxonomy')
_RF_ROI_BOOLEANS = ResultField('roi_booleans', 'image', 'choices')
_RF_ROI_NOTE     = ResultField('roi_note',     'image', 'textarea')

_RF_FRAME_DATASET  = ResultField('frame_dataset',  'image', 'choices')
_RF_FRAME_BOOLEANS = ResultField('frame_booleans', 'image', 'choices')
_RF_FRAME_NOTE     = ResultField('frame_note',     'image', 'textarea')


class IsiisRoi(BaseRegion):
    def __init__(self, xywh: BBox | tuple, class_taxonpath: list[str],
                 verified: bool = False, checkme: bool = False,
                 note: str = None, score: float = None,
                 original_width: int = None, original_height: int = None):
        super().__init__(score=score, original_width=original_width,
                         original_height=original_height)
        self.xywh: BBox = xywh if isinstance(xywh, BBox) else BBox(*xywh)
        self.class_taxonpath: list[str] = class_taxonpath
        self.verified = verified
        self.checkme = checkme
        self.note = note

    def as_result_dicts(self, region_id: str = None) -> list:
        output = []

        output.append(_RF_ROI.build(
            self.xywh.to_dict(),
            region_id=region_id,
            score=self.score,
            original_width=self.original_width,
            original_height=self.original_height,
        ))

        if self.class_taxonpath:
            taxonpath = [self.class_taxonpath] if isinstance(self.class_taxonpath, list) else [[self.class_taxonpath]]
            output.append(_RF_ROI_CLASS.build(
                {'taxonomy': taxonpath},
                region_id=region_id,
            ))

        choices = []
        if self.verified:
            choices.append('roi-verified')
        if self.checkme:
            choices.append('roi-checkme')
        if choices:
            output.append(_RF_ROI_BOOLEANS.build(
                {'choices': choices},
                region_id=region_id,
            ))

        if self.note:
            output.append(_RF_ROI_NOTE.build(
                {'text': [self.note]},
                region_id=region_id,
            ))

        return output

    def to_dict(self) -> dict:
        return {
            'xywh': self.xywh.to_dict(),
            'class_taxonpath': self.class_taxonpath,
            'verified': self.verified,
            'checkme': self.checkme,
            'note': self.note,
            'score': self.score,
            'original_width': self.original_width,
            'original_height': self.original_height,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'IsiisRoi':
        return cls(
            xywh=BBox.from_dict(d['xywh']),
            class_taxonpath=d['class_taxonpath'],
            verified=d.get('verified', False),
            checkme=d.get('checkme', False),
            note=d.get('note'),
            score=d.get('score'),
            original_width=d.get('original_width'),
            original_height=d.get('original_height'),
        )


class IsiisAnnotation(BaseAnnotation):
    def __init__(self, training: bool = False, holdout: bool = False,
                 verified: bool = False, checkme: bool = False,
                 note: str = None, rois: list[IsiisRoi] = None,
                 score: float = None, model_version: str = None,
                 original_width: int = None, original_height: int = None):
        super().__init__(regions=rois, score=score, model_version=model_version,
                         original_width=original_width, original_height=original_height)
        self.training = training
        self.holdout = holdout
        self.verified = verified
        self.checkme = checkme
        self.note = note

    @property
    def rois(self) -> list[IsiisRoi]:
        return self.regions

    def add_roi(self, xywh: BBox | tuple, class_taxonpath: list[str],
                score: float = None) -> IsiisRoi:
        roi = IsiisRoi(xywh=xywh, class_taxonpath=class_taxonpath, score=score)
        self.regions.append(roi)
        return roi

    def is_prediction(self) -> bool:
        has_model_version = self.model_version is not None
        has_score = (self.score or self.score_from_regions()) is not None
        return has_model_version or has_score

    def as_dict(self, task_id: int = None,
                force: Literal['annotation', 'prediction'] = None) -> dict:
        # Build frame-level results to prepend
        frame_results = []

        dataset_choices = []
        if self.training:
            dataset_choices.append('training')
        if self.holdout:
            dataset_choices.append('holdout')
        if dataset_choices:
            frame_results.append(_RF_FRAME_DATASET.build({'choices': dataset_choices}))

        bool_choices = []
        if self.verified:
            bool_choices.append('frame-verified')
        if self.checkme:
            bool_choices.append('frame-checkme')
        if bool_choices:
            frame_results.append(_RF_FRAME_BOOLEANS.build({'choices': bool_choices}))

        if self.note:
            frame_results.append(_RF_FRAME_NOTE.build({'text': [self.note]}))

        # Get base output (handles regions + score/model_version logic)
        output = super().as_dict(task_id=task_id, force=force)
        output['result'] = frame_results + output['result']

        # Remap 'task' key to 'task_id' to preserve original contract
        if task_id is not None and 'task' in output:
            output['task_id'] = output.pop('task')

        return output

    def to_dict(self) -> dict:
        return {
            'training': self.training,
            'holdout': self.holdout,
            'verified': self.verified,
            'checkme': self.checkme,
            'note': self.note,
            'rois': [r.to_dict() for r in self.regions],
            'score': self.score,
            'model_version': self.model_version,
            'original_width': self.original_width,
            'original_height': self.original_height,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'IsiisAnnotation':
        return cls(
            training=d.get('training', False),
            holdout=d.get('holdout', False),
            verified=d.get('verified', False),
            checkme=d.get('checkme', False),
            note=d.get('note'),
            rois=[IsiisRoi.from_dict(r) for r in d.get('rois', [])],
            score=d.get('score'),
            model_version=d.get('model_version'),
            original_width=d.get('original_width'),
            original_height=d.get('original_height'),
        )


class IsiisTask(BaseTask):
    def __init__(self, cruise: str, media: str, media_fps: float, frame: int,
                 image: str, annotations: list[IsiisAnnotation] = None):
        super().__init__(annotations=annotations)
        self.cruise = cruise
        self.media = media
        self.media_fps = media_fps
        self.frame = frame
        self.image = image

    def data_dict(self) -> dict:
        return {
            'cruise': self.cruise,
            'media': self.media,
            'media_fps': self.media_fps,
            'frame': self.frame,
            'image': self.image,
        }

    def to_dict(self) -> dict:
        return {
            **self.data_dict(),
            'annotations': [a.to_dict() for a in self.annotations],
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'IsiisTask':
        return cls(
            cruise=d['cruise'],
            media=d['media'],
            media_fps=d['media_fps'],
            frame=d['frame'],
            image=d['image'],
            annotations=[IsiisAnnotation.from_dict(a) for a in d.get('annotations', [])],
        )
