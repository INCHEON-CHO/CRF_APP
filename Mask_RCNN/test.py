import argparse

import os
import cv2, time
import numpy as np
import tensorflow as tf
import neuralgym as ng

from inpaint_model import InpaintCAModel


parser = argparse.ArgumentParser()
parser.add_argument('--image', default='training_data/images/test.png', type=str,
                    help='The filename of image to be completed.')
parser.add_argument('--mask', default='training_data/images/mask.png', type=str,
                    help='The filename of mask, value 255 indicates mask.')
parser.add_argument('--output', default='output.png', type=str,
                    help='Where to write output.')
parser.add_argument('--checkpoint_dir', default='model_logs/snap-0', type=str,
                    help='The directory of tensorflow checkpoint.')


if __name__ == "__main__":
    #ng.get_gpus(1)
    
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


    sess_config = tf.ConfigProto()
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
    start = time.time()
    with tf.Session(config=sess_config) as sess:
        sess.run(assign_ops)
        print('Model loaded.')
        result = sess.run(output)
        cv2.imwrite(args.output, result[0][:, :, ::-1])
        print(time.time() - start)
        
        
