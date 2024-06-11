import cv2
from scipy.spatial import distance as dist
import numpy as np
import os
import cv2

BASE_DIR_OUTPUT = 'path'
INPUT_FOLDER = 'path'
# Durata delle clip
video_dur = 8

# Threshold per conteggio dei blinks
EYE_AR_THRESH = 0.23
EYE_AR_CONSEC_FRAMES = 3

##### HEAD POSITION #####
# Funzione per disegnare le powlyline per le feature del volto
def drawPolyline(img, shapes, start, end, isClosed=False):
    points = []
    for i in range(start, end + 1):
        point = [shapes.part(i).x, shapes.part(i).y]
        points.append(point)
    points = np.array(points, dtype=np.int32)
    cv2.polylines(img, [points], isClosed, (255, 80, 0), thickness=1, lineType=cv2.LINE_8)

# Funzione per disegnare le feature del volto
def draw(img, shapes):
    drawPolyline(img, shapes, 0, 16)
    drawPolyline(img, shapes, 17, 21)
    drawPolyline(img, shapes, 22, 26)
    drawPolyline(img, shapes, 27, 30)
    drawPolyline(img, shapes, 30, 35, True)
    drawPolyline(img, shapes, 36, 41, True)
    drawPolyline(img, shapes, 42, 47, True)
    drawPolyline(img, shapes, 48, 59, True)
    drawPolyline(img, shapes, 60, 67, True)

# Modello 3D punti del volto
def ref3DModel():
    modelPoints = [
        [0.0, 0.0, 0.0],          # Punta del naso
        [0.0, -330.0, -65.0],     # Mento
        [-225.0, 170.0, -135.0],  # Angolo sinistro dell'occhio sinistro
        [225.0, 170.0, -135.0],   # Angolo destro dell'occhio destro
        [-150.0, -150.0, -125.0], # Angolo sinistro della bocca
        [150.0, -150.0, -125.0]   # Angolo destro della bocca
    ]
    return np.array(modelPoints, dtype=np.float64)

# Punti 2D dei landmark
def ref2dImagePoints(shape):
    imagePoints = [
        [shape.part(30).x, shape.part(30).y],  # Punta del naso
        [shape.part(8).x, shape.part(8).y],    # Mento
        [shape.part(36).x, shape.part(36).y],  # Angolo sinistro dell'occhio sinistro
        [shape.part(45).x, shape.part(45).y],  # Angolo destro dell'occhio destro
        [shape.part(48).x, shape.part(48).y],  # Angolo sinistro della bocca
        [shape.part(54).x, shape.part(54).y]   # Angolo destro della bocca
    ]
    return np.array(imagePoints, dtype=np.float64)

# Funzione per creare la camera matrix a partire dal frame
def cameraMatrix(img_size):
    focal_length = img_size[1]
    center = (img_size[1] / 2, img_size[0] / 2)
    return np.array([[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype="double")

# Funzione per determinare la posizione del volto
def headposition(frame, shape):
    face3Dmodel = ref3DModel()
    draw(frame, shape)
    refImgPts = ref2dImagePoints(shape)
    height, width, _ = frame.shape
    cameraMatrix1 = cameraMatrix((height, width))
    mdists = np.zeros((4, 1), dtype=np.float64)

    success, rotationVector, _ = cv2.solvePnP(face3Dmodel, refImgPts, cameraMatrix1, mdists, flags=cv2.SOLVEPNP_ITERATIVE)

    if not success:
        return 0, yaw
    
    rmat, _ = cv2.Rodrigues(rotationVector)
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

    yaw = angles[1]

    if abs(yaw) < 25:
        return 1, yaw # Sguardo alla camera
    else:
        return 0, yaw  # Sguardo a destra/sinistra

### EYE BLINKING ###
def eye_aspect_ratio(eye):
    ear = None
    # Calcolo della distanza euclidea a partire dai landmarks
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    # Eye Aspect Ratio
    ear = (A + B) / (2.0 * C)
    return ear

# Calcolo della frequenza di battito di ciglia
def calculate_blink_frequency(num_blinks, video_length_seconds):
    video_length_minutes = video_length_seconds / 60
    blinks_per_minute = int(round((num_blinks / video_length_minutes)))
    return blinks_per_minute


def processVideo_ebrHeadPose(video, detector, predictor):
    vidcap = cv2.VideoCapture(video)
    frame_counter = 0
    low_light_frames = 0
    low_light_threshold = 80
    error_frames = 0
    COUNTER = 0
    TOTAL = 0
    head_pos = []
    yaws = []
    leftEAR = None
    rightEAR = None

    # Per il controllo della luminosità calcolo la media dell'intensità dell'immagine grayscale tagliata sul volto. Il controllo avviene sui 
    # primi 10 frame del video
    while True:
        success, frame = vidcap.read()
        if success:
            frame_counter += 1
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_locations = detector(gray_frame)
            if len(face_locations)>0:
                # Stima luminosità ambientale
                shape = predictor(gray_frame, face_locations[0])
                top, right, bottom, left = (face_locations[0].top(), face_locations[0].right(), face_locations[0].bottom(), face_locations[0].left())
                gray_frame = gray_frame[top:bottom, left:right]
                average_intensity = cv2.mean(gray_frame)[0]
                if average_intensity < low_light_threshold:
                    low_light_frames += 1
                
                landmarks = np.array([[p.x, p.y] for p in shape.parts()])
                if len(landmarks) > 0:
                    # Stima posizione della testa
                    hp, yaw = headposition(frame, shape)
                    head_pos.append(hp)
                    yaws.append(yaw)

                    # Calcolo dell'eye aspect ratio per ogni occhio
                    left_eye = landmarks[36:42]
                    right_eye = landmarks[42:48]
                    leftEAR = eye_aspect_ratio(left_eye)
                    rightEAR = eye_aspect_ratio(right_eye)
                    # Se uno dei due EAR è "None" copio l'altro
                    if leftEAR is None and rightEAR is not None:
                        leftEAR = rightEAR
                    elif leftEAR is not None and rightEAR is None:
                        rightEAR = leftEAR
                else:
                    error_frames += 1
                    leftEAR = None
                    rightEAR = None
                    
            else:
                error_frames += 1
                low_light_frames += 1
                head_pos.append(1)
            

            if leftEAR is not None and rightEAR is not None:
                # Media dei due EAR
                ear = (leftEAR + rightEAR) / 2.0
                # Con "COUNTER" conto il numero di volto EAR è inferiore alla threshold conto (numero di frame)
                if ear < EYE_AR_THRESH:
                    COUNTER += 1
                else:
                    # Considero un battito di ciglia quando l'occhio rimane chiuso per più di 3 frame
                    if COUNTER >= EYE_AR_CONSEC_FRAMES:
                        TOTAL += 1
                    # reset the eye frame counter
                    COUNTER = 0
        else:
            break
    vidcap.release()

    # 0 bassa luminosità, 1 luminosità ok
    if low_light_frames > 20:
        lightCond = 0
    else:
        lightCond = 1
    
    return lightCond, TOTAL, error_frames, head_pos, yaws

def preprocess_getEbrHeadPose(video, prev_blinks, valid_videos, prev_ebr, detector, predictor):
    try:
        result_ebr_hp = {'outcome':True, 'blinks':{}, 'ebr':-1, 'head_pos':0, 'yaw':-1, 'valid':0}
        if not(os.path.exists(video)):
            result_ebr_hp['outcome'] = False
            result_ebr_hp['blinks']['response'] = "EBR_hp - video file doesn't exist"
            return result_ebr_hp
        try:
            lightCond, blinks, error_frames, head_pos, yaws = processVideo_ebrHeadPose(video, detector, predictor)
            if error_frames < 100:
                result_ebr_hp['blinks']['value'] = int(blinks)
                result_ebr_hp['head_pos'] = int(round(np.mean(head_pos)))
                if len(yaws)>0:
                    result_ebr_hp['yaw'] = float(np.mean(yaws))
                else:
                    result_ebr_hp['yaw'] = None
                result_ebr_hp['blinks']['response'] = "EBR_hp - Ok"
                valid_videos += 1
                result_ebr_hp['valid'] = valid_videos
                if prev_ebr != -1:
                    tot_blinks = prev_blinks + blinks
                else:
                    tot_blinks = blinks
                result_ebr_hp['ebr'] = calculate_blink_frequency(tot_blinks, valid_videos*video_dur)
            else:
                result_ebr_hp['valid'] = valid_videos
                if prev_ebr != -1 and prev_blinks != -1:
                    result_ebr_hp['ebr'] = int(prev_ebr)
                    result_ebr_hp['blinks']['value'] = int(prev_blinks)
                    result_ebr_hp['blinks']['response'] = "EBR_hp - Too many error frames"
                    result_ebr_hp['outcome'] = False
                else:
                    result_ebr_hp['blinks']['response'] = "EBR_hp - No previous ebr/attLev to take"
                    result_ebr_hp['blinks']['value'] = -1
                    result_ebr_hp['ebr'] = -1
                    result_ebr_hp['outcome'] = False
        except Exception as error:
            result_ebr_hp['ebr'] = -1
            result_ebr_hp['attLev'] = -1
            result_ebr_hp['blinks']['value'] = -1
            result_ebr_hp['outcome'] = False
            result_ebr_hp['blinks']['response'] = "EBR_hp - Error during detection of EBR"
            return result_ebr_hp, lightCond
    except Exception as error:
        result_ebr_hp['outcome'] = False
        result_ebr_hp['blinks']['response'] = "Generic error during processing"
    
    #_logging.debug(str(result))
    return result_ebr_hp, lightCond