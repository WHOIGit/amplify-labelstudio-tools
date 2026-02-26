from typing import Literal


class BBox:
    def __init__(self, x:float, y:float, width:float, height:float):
        # for labelstudio, x and y are top-left corner
        # units are in percent of whole image
        # eg: x=50 y=50 is center of image, w=50 h=50 is therefor the bottom-right quadrant or image
        self.x:float = x
        self.y:float = y
        self.width:float = width
        self.height:float = height

    def as_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            #'rotation': 0,
        }

    @classmethod
    def from_yolo(cls, x_center, y_center, width, height):
        # units: fractions of whole image,
        # eg: x=0.5 y=0.5, w=0.5, h=0.5 is a box in center of image
        x = x_center-width/2
        y = y_center-height/2
        x, y, w, h = 100*x, 100*y, 100*width, 100*height
        return cls(x,y,w,h)



class IsiisRoi:
    def __init__(self, xywh:BBox|tuple, class_taxonpath:list[str],
                 verified:bool=False, checkme:bool=False,
                 note:str=None, score:float=None,
                 original_width:int=None, original_height:int=None):
        self.xywh:BBox = xywh if isinstance(xywh, BBox) else BBox(*xywh)
        self.class_taxonpath:list[str] = class_taxonpath  # todo taxonomy validation
        self.verified = verified
        self.checkme = checkme
        self.note = note

        self.score = score
        self.original_width = original_width
        self.original_height = original_height


    def as_dict(self, region_id:str=None):
        output = []
        roi = dict(
            from_name = 'roi',
            to_name = 'image',
            type = 'rectangle',
            value = self.xywh.as_dict(),
        )
        output.append(roi)

        taxonpath = [self.class_taxonpath] if isinstance(self.class_taxonpath, list) else [[self.class_taxonpath]]
        roi_class = dict(
            from_name = 'roi_class',
            to_name = 'image',
            type = 'taxonomy',
            value = dict(taxonomy = taxonpath),
                # eg ['Animalia', 'Chordata', 'Mammalia', 'Carnivora', 'Felidae', 'Felis', 'Felis catus']
                # may need to also include self.xywh geometry in label - unclear
        )
        if self.class_taxonpath:
            output.append(roi_class)

        roi_booleans = dict(
            from_name = 'roi_booleans',
            to_name = 'image',
            type = 'choices',
            value = dict(choices = [])
        )
        if self.verified:
            roi_booleans['value']['choices'].append('roi-verified')
        if self.checkme:
            roi_booleans['value']['choices'].append('roi-checkme')
        if self.verified or self.checkme:
            output.append(roi_booleans)

        roi_note = dict(
            from_name = 'roi_note',
            to_name = 'image',
            type = 'textarea',
            value = dict(text=[self.note or '']),
        )
        if self.note:
            output.append(roi_note)

        # IDs is how results are per-region grouped, so this is important
        if region_id is not None:
            roi['id'] = region_id
            roi_class['id'] = region_id
            roi_booleans['id'] = region_id
            roi_note['id'] = region_id

        if self.score is not None:
            roi['score'] = self.score

        if self.original_width is not None and self.original_height is not None:
            roi['original_width'] = self.original_width
            roi['original_height'] = self.original_height

        # these results extend the other results for the task annotation/prediction being submitted
        return output


class IsiisAnnotation:
    def __init__(self, training:bool=False, holdout:bool=False,
                 verified:bool=False, checkme:bool=False,
                 note:str=None, rois:list[IsiisRoi]=None,
                 score:float=None, model_version:str=None,
                 original_width:int=None, original_height:int=None):
        self.training = training
        self.holdout = holdout
        self.verified = verified
        self.checkme = checkme
        self.note = note
        self.rois:list[IsiisRoi] = rois or []

        self.score = score
        self.model_version = model_version

        self.original_width = original_width
        self.original_height = original_height

    def add_roi(self, xywh:BBox|tuple, class_taxonpath:list[str], score:float=None):
        roi = IsiisRoi(xywh=xywh, class_taxonpath=class_taxonpath, score=score)
        self.rois.append(roi)
        return roi

    def score_from_rois(self):
        roi_scores = [roi.score for roi in self.rois if roi.score is not None]
        assert len(roi_scores) == len(self.rois), 'all rois must have scores to compute annotation score'
        if roi_scores:
            return sum(roi_scores) / len(roi_scores)
        else:
            return None

    def is_prediction(self):
        has_model_version = self.model_version is not None
        has_score = (self.score or self.score_from_rois()) is not None
        return has_model_version or has_score


    def as_dict(self, task_id:int=None, force:Literal['annotation','prediction']=None):
        results = []
        output = dict(result = results)

        frame_dataset = dict(
            from_name = 'frame_dataset',
            to_name = 'image',
            type = 'choices',
            value = dict(choices = [])
        )
        if self.training:
            frame_dataset['value']['choices'].append('training')
        if self.holdout:
            frame_dataset['value']['choices'].append('holdout')
        # if self.holdout and self.training:
        #     raise ValueError('frame cannot be both training and holdout')
        if self.training or self.holdout:
            results.append(frame_dataset)

        frame_booleans = dict(
            from_name = 'frame_booleans',
            to_name = 'image',
            type = 'choices',
            value = dict(choices = []))
        if self.verified:
            frame_booleans['value']['choices'].append('frame-verified')
        if self.checkme:
            frame_booleans['value']['choices'].append('frame-checkme')
        if self.verified or self.checkme:
            results.append(frame_booleans)

        frame_note = dict(
            from_name = 'frame_note',
            to_name = 'image',
            type = 'textarea',
            value = dict(text=[self.note or '']))
        if self.note:
            results.append(frame_note)

        for i, roi_obj in enumerate(self.rois):
            roi_id = f'roi-{i:03d}'
            if self.original_width and self.original_height:
                roi_obj.original_width = self.original_width
                roi_obj.original_height = self.original_height
            results.extend(roi_obj.as_dict(roi_id))

        average_score = self.score_from_rois()
        score = self.score or average_score

        if force == 'prediction':
            output['score'] = score or 0.50  # dummy value
            output['model_version'] = self.model_version or 'dummy-model-version'

        if not force=='annotation':
            if score is not None:
                output['score'] = score
            if self.model_version is not None:
                output['model_version'] = self.model_version
                assert score is not None, 'model_version provided without score'

        if task_id is not None:
            output['task_id'] = task_id

        return output


class IsiisTask:
    def __init__(self, cruise:str, media:str, media_fps:float, frame:int, image: str,
                 annotations:list[IsiisAnnotation]=None):
        self.cruise = cruise
        self.media = media
        self.media_fps = media_fps
        self.frame = frame
        self.image = image
        self.annotations:list[IsiisAnnotation] = annotations or []
        # note that annotations with scores are considered predictions

    def as_new_taskdata_dict(self, predictions_key=None, annotations_key=None):
        task_data = dict(
            cruise = self.cruise,
            media = self.media,
            media_fps = self.media_fps,
            frame = self.frame,
            image = self.image,
        )
        task_dict = dict(data=task_data)
        if predictions_key:
            preds = [pred.as_dict() for pred in self.annotations if pred.is_prediction()]
            task_dict['predictions'] = preds
        if annotations_key:
            annots = [annot.as_dict() for annot in self.annotations if not annot.is_prediction()]
            task_dict['annotations'] = annots
        return task_dict
