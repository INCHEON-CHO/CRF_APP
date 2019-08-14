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

# 프로젝트의 root directory
ROOT_DIR = os.path.abspath("../../")

# Import Mask RCNN
sys.path.append(ROOT_DIR)
from mrcnn import utils
from mrcnn import visualize
from mrcnn.visualize import display_images
import mrcnn.model as modellib
from mrcnn.model import log

from samples.person import person

from PIL import Image, ImageDraw, ImageFont

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


# Load validation dataset
dataset = person.personDataset()
dataset.load_person(PERSON_DIR, "val")

# dataset을 사용하기 전에 반드시 실행해야 함
dataset.prepare()

with tf.device(DEVICE):
    model = modellib.MaskRCNN(mode="inference", model_dir=MODEL_DIR,config=config)
    
    
model.load_weights(BALLON_WEIGHTS_PATH, by_name=True)


IMAGE_DIR = os.path.join(ROOT_DIR, "images")
filename=os.path.join(IMAGE_DIR,'image2.png')
image = skimage.io.imread(filename)
# Run object detection
results = model.detect([image], verbose=1)
    
# Display results
ax = get_ax(1)
r = results[0]

#visualize.display_instances(image, r['rois'], r['masks'], r['class_ids'],dataset.class_names, r['scores'], ax=ax,title="Predictions")

#Save results
class_names = ['BG', 'person']
save_image(image,"results", r['rois'], r['masks'],r['class_ids'],r['scores'],class_names,filter_classs_names=['person'],scores_thresh=0.9,save_dir="c:/Users/kkh11/Desktop",mode=0)