import os
import sys
import random
import colorsys
import math
import re
import time
import numpy as np
import tensorflow as tf
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import skimage.io
import time
from flask import Flask, request, send_file, jsonify, json, Response
from werkzeug import secure_filename

import pandas as pd
from sqlalchemy import create_engine
from PIL import Image
import base64
from io import BytesIO

import argparse
import os
import cv2, time
import numpy as np
import tensorflow as tf
import neuralgym as ng

sys.path.insert(0, "..\\..\\")

from inpaint_model import InpaintCAModel


parser = argparse.ArgumentParser()
parser.add_argument('--image', default='..\\..\\training_data\\images\\test.png', type=str,
                    help='The filename of image to be completed.')
#parser.add_argument('--image', default='.\\imageintoDB.jpg', type=str,
#                    help='The filename of image to be completed.')                    
parser.add_argument('--mask', default='..\\..\\training_data\\images\\mask.png', type=str,
                    help='The filename of mask, value 255 indicates mask.')
#parser.add_argument('--mask', default='.\\Mask.jpg', type=str,
#                    help='The filename of mask, value 255 indicates mask.')                    
parser.add_argument('--output', default='output.png', type=str,
                    help='Where to write output.')
parser.add_argument('--checkpoint_dir', default='..\\..\\model_logs\\snap-0', type=str,
                    help='The directory of tensorflow checkpoint.')



# 프로젝트의 root directory
ROOT_DIR = os.path.abspath("../../")

# Import Mask RCNN
sys.path.append(ROOT_DIR)

graph = tf.get_default_graph()
sess_config = tf.ConfigProto()

from mrcnn import utils
from mrcnn import visualize
from mrcnn.visualize import display_images
import mrcnn.model as modellib
from mrcnn.model import log

from samples.person import person

from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)


def get_ax(rows=1, cols=1, size=16):
    """Return a Matplotlib Axes array to be used in
    all visualizations in the notebook. Provide a
    central point to control graph sizes.
    
    Adjust the size attribute to control how big to render images
    """
    _, ax = plt.subplots(rows, cols, figsize=(size*cols, size*rows))
    return ax

def apply_mask(image, mask, color, alpha=0.5):
    """Apply the given mask to the image.
    """
    for c in range(3):
        image[:, :, c] = np.where(mask == 1,
                                  image[:, :, c] *
                                  (1 - alpha) + alpha * color[c] * 255,
                                  image[:, :, c])
    return image

def save_image(image, image_name, boxes, masks, class_ids, scores, class_names, filter_classs_names=None, scores_thresh=0.1, save_dir=None, mode=0):
    """
        image: imgae
        image_name: 저장할 이름
        boxes: [y1, x1, y2, x2] in image 좌표
        masks: [num_instances, height, width] -> Boolean 값
        class_ids: [num_instances] -> person으로 한정시켰기 때문에 모든 값을 가짐
        scores: box당 할당된 점수
        class_names: dataset에 있는 class들의 list지만 'BG', 'person'뿐이다.
        filter_classs_names: (optional) 보고 싶은 class의 네임들
        scores_thresh: (optional) scores의 임계점
        save_dir: (optional) 저장 위치
        mode: (optional) 저장하고 싶은 모드 선택
                mode = 0 , box, 객체명, 점수, mask와 함께 이미지 저장
                mode = 1 , box, 객체명, score와 함께 이미지 저장
                mode = 2 , 객체명, 점수, mask와 함께 이미지 저장
                mode = 3 , 검은 배경에 mask와 함께 이미지 저장
                mode = 4 , box내 하얀 mask와 검은 배경 구현 예정
    """
    mode_list = [0, 1, 2, 3]
    assert mode in mode_list, "mode's value should in mode_list %s" % str(mode_list)

    if save_dir is None:
        save_dir = os.path.join(os.getcwd(), "output")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

    useful_mask_indices = []

    N = boxes.shape[0]
    if not N:
        print("\n*** No instances in image %s to draw *** \n" % (image_name))
        return
    else:
        assert boxes.shape[0] == masks.shape[-1] == class_ids.shape[0]

    for i in range(N):
        # filter
        class_id = class_ids[i]
        score = scores[i] if scores is not None else None
        if score is None or score < scores_thresh:
            continue

        label = class_names[class_id]
        if (filter_classs_names is not None) and (label not in filter_classs_names):
            continue

        if not np.any(boxes[i]):
            # Skip this instance. Has no bbox. Likely lost in image cropping.
            continue

        useful_mask_indices.append(i)

    if len(useful_mask_indices) == 0:
        print("\n*** No instances in image %s to draw *** \n" % (image_name))
        return

    colors = random_colors(len(useful_mask_indices),bright=False)

    if mode != 3:
        masked_image = image.astype(np.uint8).copy()
    else:
        masked_image = np.zeros(image.shape).astype(np.uint8)

    if mode != 1:
        for index, value in enumerate(useful_mask_indices):
            masked_image = apply_mask(masked_image, masks[:, :, value], colors[index])

    masked_image = Image.fromarray(masked_image)

    if mode == 3:
        masked_image.save(os.path.join(save_dir, '%s.jpg' % (image_name)))
        print("Save complete!")
        return

    draw = ImageDraw.Draw(masked_image)
    colors = np.array(colors).astype(int) * 255

    for index, value in enumerate(useful_mask_indices):
        class_id = class_ids[value]
        score = scores[value]
        label = class_names[class_id]

        y1, x1, y2, x2 = boxes[value]
        if mode != 2:
            color = tuple(colors[index])
            draw.rectangle((x1, y1, x2, y2), outline=color)
        # Label
        draw.text((x1, y1), "%s %f" % (label, score), (255, 255, 255))

    masked_image.save(os.path.join(save_dir, '%s.jpg' % (image_name)))
    print("Save complete!")
    
def random_colors(N, bright=True):
    """
    Generate random colors.
    To get visually distinct colors, generate them in HSV space then
    convert to RGB.
    """
    brightness = 1.0 if bright else 0.7
    hsv = [(i / N, 1, brightness) for i in range(N)]
    colors = list(map(lambda c: colorsys.hsv_to_rgb(*c), hsv))
    random.shuffle(colors)
    return colors

@app.route("/")
def index():
    """
    this is a root dir of my server
    :return: str
    """
    return "This is root"
    
@app.route('/receive',methods=['POST', 'GET'])
def getFile():
    if request.method == 'POST':
        file = request.files['file']
        print("get files")
        #Filename = secure_filename(file.filename)
        Filename = "Image.jpg"
        file.save(Filename)
        global graph
        with graph.as_default():
            start = time.time()
            #IMAGE_DIR = os.path.join(ROOT_DIR, "images")
            #filename = os.getcwd() + "\" + Filename
            #filename = os.getcwd() + "\\Image.jpg"
            filename = os.getcwd() + "\\image2.png"
            image = skimage.io.imread(filename)
            # Run object detection
            results = model.detect([image], verbose=1)
                
            # Display results
            #ax = get_ax(1)
            r = results[0]

            #visualize.display_instances(image, r['rois'], r['masks'], r['class_ids'],dataset.class_names, r['scores'], ax=ax,title="Predictions")

            #Save results
            #save_image(image,"results", r['rois'], r['masks'],r['class_ids'],r['scores'],class_names,filter_classs_names=['person'],scores_thresh=0.9,save_dir=ROOT_DIR,mode=0)
            #print("Complete!")
            print(time.time() - start)
            
            return jsonify(r['rois'].tolist())
    else:
        return "Y U NO USE POST?"

#image inpainting에 필요한 이미지 전달
@app.route('/pass',methods=['POST'])
def GetFile():
    file = request.files['file']
    print("Get Files")
    Filename = "imageintoDB.jpg"
    #Filename = secure_filename(file.filename)
    file.save(Filename)

    engine = create_engine('mysql+pymysql://root:root@localhost/crf', echo = False)
    buffer = BytesIO()
    im = Image.open(Filename)

    im.save(buffer, format='jpeg')
    img_str = base64.b64encode(buffer.getvalue())

    img_df = pd.DataFrame({'image':[img_str]})

    img_df.to_sql(name="object_detection_dataset", con=engine, if_exists='append', index=False)
        
    return "success"

#image inpainting에 필요한 Mask 전달
@app.route('/passMask',methods=['POST'])
def GetMask():
    file = request.files['file']
    print("Get Files")
    Filename = "Mask.jpg"
    #Filename = secure_filename(file.filename)
    file.save(Filename)

    return "success"

#빈부분이 채워진 사진 app으로 전달
@app.route('/download', methods=['POST'])
def downloadFile():
    start = time.time()
    os.environ['CUDA_VISIABLE_DEVICE'] = '0'
    args = parser.parse_args()

    model = InpaintCAModel()
    image = cv2.imread(args.image)
    mask = cv2.imread(args.mask)

    assert image.shape == mask.shape

    h, w, _ = image.shape
    grid = 8
    image = image[:h//grid*grid, :w//grid*grid, :]
    mask = mask[:h//grid*grid, :w//grid*grid, :]
    print('Shape of image: {}'.format(image.shape))

    image = np.expand_dims(image, 0)
    mask = np.expand_dims(mask, 0)
    input_image = np.concatenate([image, mask], axis=2)

    #sess_config = tf.ConfigProto()
    #sess_config.gpu_options.allow_growth = True
    
    
    input_image = tf.constant(input_image, dtype=tf.float32)
    output = model.build_server_graph(input_image)
    output = (output + 1.) * 127.5
    output = tf.reverse(output, [-1])
    output = tf.saturate_cast(output, tf.uint8)
    # load pretrained model
    vars_list = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES)
    assign_ops = []
    
    for var in vars_list:
        vname = var.name
        from_name = vname
        var_value = tf.contrib.framework.load_variable(args.checkpoint_dir, from_name)
        assign_ops.append(tf.assign(var, var_value))

    global sess_config
    with tf.Session(config=sess_config) as sess: 
        sess.run(assign_ops)
        print('Model loaded.')
        result = sess.run(output)
        cv2.imwrite(args.output, result[0][:, :, ::-1])
    print(time.time() - start)
    return send_file('output.png')

#image inpainting training dataset에 이미지 추가
@app.route('/insert', methods=['POST'])
def insertdb():
    engine = create_engine('mysql+pymysql://root:root@localhost/crf', echo = False)
    buffer = BytesIO()
    im = Image.open('output.png')

    im.save(buffer, format='jpeg')
    img_str = base64.b64encode(buffer.getvalue())

    img_df = pd.DataFrame({'image':[img_str]})

    img_df.to_sql(name="image_inpainting_dataset", con=engine, if_exists='append', index=False)

    return "success"

#메인
if __name__ == '__main__':

    # 프로젝트의 root directory
    ROOT_DIR = os.path.abspath("../../")

    # Import Mask RCNN
    sys.path.append(ROOT_DIR)

    # logs와 trained model이 저장되어있는 Directory
    MODEL_DIR = os.path.join(ROOT_DIR, "logs")

    #trained weights의 경로
    BALLON_WEIGHTS_PATH = ROOT_DIR+"/mask_rcnn_person.h5"

    config = person.personConfig()
    PERSON_DIR = os.path.join(ROOT_DIR, "datasets\\person")

    class InferenceConfig(config.__class__):
        # Run detection on one image at a time
        GPU_COUNT = 1
        IMAGES_PER_GPU = 1

    config = InferenceConfig()

    DEVICE = "/cpu:0"  # /cpu:0 or /gpu:0

    # training, inference 모드가 있음
    TEST_MODE = "inference"

    class_names = ['BG', 'person']

    # Load validation dataset
    dataset = person.personDataset()
    dataset.load_person(PERSON_DIR, "val")

    # dataset을 사용하기 전에 반드시 실행해야 함
    dataset.prepare()

    with tf.device(DEVICE):
        model = modellib.MaskRCNN(mode="inference", model_dir=MODEL_DIR,config=config)
            
    model.load_weights(BALLON_WEIGHTS_PATH, by_name=True)

###############################################################

    #ng.get_gpus(1)
    
    '''os.environ['CUDA_VISIABLE_DEVICE'] = '0'
    args = parser.parse_args()

    model = InpaintCAModel()
    image = cv2.imread(args.image)
    mask = cv2.imread(args.mask)

    assert image.shape == mask.shape

    h, w, _ = image.shape
    grid = 8
    image = image[:h//grid*grid, :w//grid*grid, :]
    mask = mask[:h//grid*grid, :w//grid*grid, :]
    print('Shape of image: {}'.format(image.shape))

    image = np.expand_dims(image, 0)
    mask = np.expand_dims(mask, 0)
    input_image = np.concatenate([image, mask], axis=2)

    #sess_config = tf.ConfigProto()
    #sess_config.gpu_options.allow_growth = True
    
    
    input_image = tf.constant(input_image, dtype=tf.float32)
    output = model.build_server_graph(input_image)
    output = (output + 1.) * 127.5
    output = tf.reverse(output, [-1])
    output = tf.saturate_cast(output, tf.uint8)
    # load pretrained model
    vars_list = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES)
    assign_ops = []
    
    for var in vars_list:
        vname = var.name
        from_name = vname
        var_value = tf.contrib.framework.load_variable(args.checkpoint_dir, from_name)
        assign_ops.append(tf.assign(var, var_value))'''

    app.run(host='0.0.0.0', port=80)