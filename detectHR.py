import os
import pyVHR as vhr
from pyVHR.BVP import *
import numpy as np

from commonPyGpi.bin.be.util.logging import _logging

BASE_DIR_OUTPUT = 'path'
INPUT_FOLDER = 'path'

# Pipeline per l'estrazione della frequenza cardiaca (pyVHR - metodo con patches)
def get_HR_pipeline(video):
    wsize = 6
    sig_extractor = vhr.extraction.SignalProcessing()
    sig_extractor.set_skin_extractor(vhr.extraction.SkinExtractionConvexHull())

    fps = vhr.extraction.get_fps(video)
    sig_extractor.set_total_frames(0)

    vhr.extraction.SkinProcessingParams.RGB_LOW_TH = 0
    vhr.extraction.SkinProcessingParams.RGB_HIGH_TH = 240

    vhr.extraction.SignalProcessingParams.RGB_LOW_TH = 0
    vhr.extraction.SignalProcessingParams.RGB_HIGH_TH = 240

    sig_extractor.set_visualize_skin_and_landmarks(
        visualize_skin=True, 
        visualize_landmarks=True, 
        visualize_landmarks_number=True, 
        visualize_patch=True)

    landmarks = vhr.extraction.MagicLandmarks.cheek_left_top +\
                    vhr.extraction.MagicLandmarks.forehead_center +\
                    vhr.extraction.MagicLandmarks.forehoead_right +\
                    vhr.extraction.MagicLandmarks.cheek_right_top +\
                    vhr.extraction.MagicLandmarks.forehead_left +\
                    vhr.extraction.MagicLandmarks.nose 

    sig_extractor.set_landmarks(landmarks)

    sig_extractor.set_square_patches_side(30.0)
    sig = sig_extractor.extract_patches(video, "squares", "mean")

    windowed_sig = []
    wsize += 2
    while len(windowed_sig) == 0 and wsize > 1:
        wsize -= 2
        windowed_sig, timesES = vhr.extraction.sig_windowing(sig, wsize, 1, fps)
    
    if len(windowed_sig) == 0:
        return None
    
    # Pre-filtering
    filtered_windowed_sig = vhr.BVP.apply_filter(windowed_sig, vhr.BVP.rgb_filter_th, params={'RGB_LOW_TH': 0, 'RGB_HIGH_TH': 230})
    filtered_windowed_sig = vhr.BVP.apply_filter(filtered_windowed_sig, vhr.BVP.BPfilter, params={'order':6,'minHz':0.4,'maxHz':4,'fps':fps})
    filtered_windowed_sig = vhr.BVP.apply_filter(filtered_windowed_sig, vhr.BVP.zscore)

    # Metodo LGI per la conversione del segnale RGB in BVP
    bvps = RGB_sig_to_BVP(filtered_windowed_sig, fps, device_type='cpu', method=cpu_LGI)

    # Post-filtering
    bvps = vhr.BVP.apply_filter(bvps, BPfilter, params={'order':6,'minHz':0.8,'maxHz':2.2,'fps':fps})
    bvps = vhr.BVP.apply_filter(bvps, vhr.BVP.zeromean)
    bpm = vhr.BPM.BVP_to_BPM_PSD_clustering(bvps, fps)
    return bpm

# Salvataggio delle stime in response
def get_HR(video, prev_hr, avg_hr):
    try:
        result_hr = {'outcome':True, 'hr':{'value': -1, 'avg': -1, 'response': 'Ok'}}

        if not(os.path.exists(video)):
            result_hr['outcome'] = False
            if prev_hr != -1:
                result_hr['hr']['value'] = prev_hr
                result_hr['hr']['avg'] = avg_hr
            else:
                result_hr['hr']['value'] = -1
                result_hr['hr']['avg'] = -1
            result_hr['hr']['response'] = "HR - Video file doesn't exist"
            result_hr['outcome'] = False
            _logging.debug(str(result_hr))
            return result_hr
        bpm = get_HR_pipeline(video)
        bpm = [hr for hr in bpm if hr !=0]
        try:
            bpm = np.median(bpm)
            if prev_hr != -1:
                if abs(prev_hr-bpm)>12:
                    bpm = (avg_hr + bpm)/2
                result_hr['hr']['value'] = int(round(bpm))
                result_hr['hr']['avg'] = int(round((avg_hr + bpm)/2))
            else:
                result_hr['hr']['value'] = int(round(bpm))
                result_hr['hr']['avg'] = int(round(bpm))
            result_hr['hr']['response'] = "HR - Ok"
        except Exception as error:
            _logging.exception(error)
            result_hr['outcome'] = False
            if prev_hr != -1:
                result_hr['hr']['value'] = prev_hr
                result_hr['hr']['avg'] = avg_hr
            else:
                result_hr['hr']['value'] = -1
                result_hr['hr']['avg'] = -1
            result_hr['hr']['response'] = "HR - Detection error"
            return result_hr
    except Exception as error:
        _logging.exception(error)
        result_hr['outcome'] = False
        if prev_hr != -1:
                result_hr['hr']['value'] = prev_hr
                result_hr['hr']['avg'] = avg_hr
        else:
            result_hr['hr']['value'] = -1
            result_hr['hr']['avg'] = -1
        result_hr['hr']['response'] = "HR - Generic error"

    #_logging.debug(str(result))
    return result_hr