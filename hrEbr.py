from commonPyGpi.bin.be.util.const import CONST
from commonPyGpi.bin.be.util.languages import _languages
from commonPyGpi.bin.be.util.logging import _logging
from commonPyGpi.bin.be.util.file import File
from flask import request
import base64
import os
import pandas as pd
import numpy as np
import json
import dlib
from datetime import datetime
from detectHR import get_HR
from getAttention import get_AttLev
from detectEBR_headpose_lightCond import preprocess_getEbrHeadPose

BASE_DIR_OUTPUT = 'path'
INPUT_FOLDER = 'path'
JSON_FOLDER = 'path'

###### DLIB #######
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(os.path.join(BASE_DIR_OUTPUT, "shape_predictor_68_face_landmarks.dat"))

# Apertura o creazione del file json per salvare valore di hr/ebr precedente, se esiste già un file appartenente 
# a stesso username ma con diverso idVisita viene cancellato
def open_or_create_json(visit_id, username):
    json_files = [file for file in os.listdir(JSON_FOLDER) if file.endswith('.json')]
    for filename in json_files:
        visit_id_file, username_file = filename.split('#')[0], filename.split('#')[1]
        if username == username_file and visit_id != visit_id_file:
            os.remove(os.path.join(JSON_FOLDER, filename))

    rec_file = f"{visit_id}#{username}#hrEbr.json"
    rec_file_path = os.path.join(JSON_FOLDER, rec_file)
    if os.path.exists(rec_file_path):
        with open(rec_file_path, 'r') as file:
            rec = json.load(file)
    else:
        rec = [{
            'prev_hr': -1,
            'avg_hr': -1,
            'prev_ebr': -1,
            'prev_blinks': -1,
            'prev_attLev': -1,
            'valid': 0
        }]
        with open(rec_file_path, 'w') as file:
            json.dump(rec, file)
    return rec_file_path, rec

# Aggiunta dei dati al file json della visita

def update_json(filename, hr_value, avg_hr, blinks, ebr, attLev, valid):
    rec = {
        'prev_hr': None,
        'avg_hr': None,
        'prev_ebr': None,
        'prev_blinks': None,
        'prev_attLev': None,
        'valid': None
    }

    if os.path.exists(filename):
        with open(filename, 'r') as file:
            data = json.load(file)
            if data:
                existing_rec = data[0]
                rec.update(existing_rec)
        rec['valid'] = valid
        if hr_value != -1:
            rec['prev_hr'] = hr_value
            rec['avg_hr'] = avg_hr
        if ebr != -1 and blinks != -1:
            rec['prev_ebr'] = ebr
            rec['prev_blinks'] = blinks
        if attLev != -1:
            rec['prev_attLev'] = attLev

        with open(filename, 'w') as file:
            json.dump([rec], file, indent=4)

        # Write the updated dictionary to the JSON file
        with open(filename, 'w') as file:
            json.dump([rec], file, indent=4)



def elabora():
    """
    {
    "idEvento": stringa,
    "username": stringa,
    "video":"base64"
    }
    """

    jsonResponse = {"hr": -1, "avg_hr": -1, "blinks":-1, "attLev": -1, "yaw":None, "lightCond": -1, "datetime_video_recorded":-1, "response_value":CONST.__OK__, "response_text": {}, "response_function":"ai.HR_EBR"}
    try:
        jsonRequest = request.json
        dInput = {}
        if jsonRequest.get("video",'') == '':
            jsonResponse['response_text']  = _languages._default("REQUIRED")+' '+"video"
            jsonResponse['response_value'] = CONST.__ERROR__
            return
        dInput["video"] = jsonRequest["video"]
        dInput["username"] = jsonRequest["username"]
        dInput["idEvento"] = jsonRequest["idEvento"]

        prev_hr = -1
        prev_blinks = -1
        prev_ebr = -1
        valid_videos = 0
        prev_attLev = -1
        try:
            rec_file, rec = open_or_create_json(dInput["idEvento"], dInput["username"])
            if len(rec[0])>1:
                prev_hr = rec[0]['prev_hr']
                avg_hr = rec[0]['avg_hr']
                prev_blinks = rec[0]['prev_blinks']
                prev_ebr = rec[0]['prev_ebr']
                prev_attLev = rec[0]['prev_attLev']
                valid_videos = rec[0]['valid']
        except Exception as error:
            _logging(error)
            jsonResponse['response_value'] = CONST.__ERROR__
            jsonResponse['response_text']['generic'] = "Error in retrieving/creating the file of the previous data"
            File().delete(filename)
            return jsonResponse

        if jsonResponse['response_value'] == CONST.__OK__:
            now = (datetime.now()).strftime("%Y%m%d%H%M%S")
            filename =  INPUT_FOLDER + os.sep + now +".mov"
            video = base64.b64decode(dInput["video"])
            with open(filename, "wb+") as fh:
                fh.write(video)
            timestamp = (datetime.now()).strftime("%d/%m/%Y, %H:%M:%S")
            jsonResponse['datetime_video_recorded'] = timestamp
            # Preprocessing del video (identificazione delle condizioni di luce del volto)
            ### STIMA EBR e HEADPOSE ###
            result_ebr_hp, lightCond = preprocess_getEbrHeadPose(filename, prev_blinks, valid_videos, prev_ebr, detector, predictor)
            jsonResponse['lightCond'] = int(lightCond)
            blinks = result_ebr_hp['blinks']['value']
            ebr = result_ebr_hp['ebr']
            head_pos = result_ebr_hp['head_pos']
            valid_videos = result_ebr_hp['valid']

            # Se il video non esiste, errore (tutti i campi a -1)
            if not os.path.exists(filename): 
                jsonResponse['response_text'] = "File not exists: "+str(filename)
                jsonResponse['response_value'] = CONST.__ERROR__
                File().delete(filename)
                return jsonResponse
            ########## STIMA DELLA FREQUENZA CARDIACA ###########
            result_hr = get_HR(filename, prev_hr, avg_hr)
            hr_value = result_hr['hr']['value']
            avg_hr = result_hr['hr']['avg']
        
            ########## STIMA DEL LIVELLO DI ATTENZIONE ###########
            attLev = round(get_AttLev(prev_ebr, ebr, prev_hr, hr_value, prev_attLev, head_pos))
            
            # Aggiornamento dati nel json
            update_json(rec_file, hr_value, avg_hr, blinks, ebr, attLev, valid_videos)

            if result_hr['outcome'] and attLev != -1:
                jsonResponse['hr'] = result_hr['hr']['value']
                jsonResponse['attLev'] = int(attLev)
                jsonResponse['avg_hr']  = result_hr['hr']['avg']
                jsonResponse['blinks']  = result_ebr_hp['blinks']['value']
                jsonResponse['yaw']  = result_ebr_hp['yaw']
                jsonResponse['response_text']['hr']  = result_hr['hr']['response']
                jsonResponse['response_text']['blinks']  = result_ebr_hp['blinks']['response']
            else:
                jsonResponse['response_text']['hr']  = result_hr['hr']['response']
                jsonResponse['response_text']['blinks']  = result_ebr_hp['blinks']['response']
                jsonResponse['response_value'] = CONST.__ERROR__
            
        if jsonResponse['response_value'] != CONST.__OK__:
            _logging.debug("ai.HR_EBR jsonResponse (ebr): "+str(jsonResponse))
        
        File().delete(filename)

    except Exception as error:
        _logging.exception(error)
        jsonResponse["response_text_hr"] = _languages._default("EXC")
        jsonResponse["response_text_ebr"] = _languages._default("EXC")
        _logging.debug(str(jsonResponse))
        if os.path.exists(filename):
            File().delete(filename)
    
    return jsonResponse
