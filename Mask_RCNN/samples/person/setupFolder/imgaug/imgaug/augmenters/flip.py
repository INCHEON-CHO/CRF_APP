"""
Augmenters that apply mirroring/flipping operations to images.

Do not import directly from this file, as the categorization is not final.
Use instead ::

    from imgaug import augmenters as iaa

and then e.g. ::

    seq = iaa.Sequential([
        iaa.Fliplr((0.0, 1.0)),
        iaa.Flipud((0.0, 1.0))
    ])

List of augmenters:

    * Fliplr
    * Flipud

"""
from __future__ import print_function, division, absolute_import

import numpy as np
import cv2

from . import meta
from .. import parameters as iap


# pylint:disable=pointless-string-statement
"""
Speed comparison by datatype and flip method.

HORIZONTAL FLIPS.

----------
bool
----------
               slice 0.00052ms
       slice, contig 0.21878ms
              fliplr 0.00180ms
       fliplr contig 0.22000ms
                 cv2 Error: Expected cv::UMat for argument 'src'
          cv2 contig Error: Expected cv::UMat for argument 'src'
            fort cv2 Error: Expected cv::UMat for argument 'src'
     fort cv2 contig Error: Expected cv::UMat for argument 'src'
                cv2_ Error: Expected cv::UMat for argument 'src'
         cv2_ contig Error: Expected cv::UMat for argument 'src'
           fort cv2_ Error: Expected cv::UMat for argument 'src'
    fort cv2_ contig Error: Expected cv::UMat for argument 'src'
            cv2_ get Error: Expected cv::UMat for argument 'src'
     cv2_ get contig Error: Expected cv::UMat for argument 'src'
       fort cv2_ get Error: Expected cv::UMat for argument 'src'
fort cv2_ get contig Error: Expected cv::UMat for argument 'src'

----------
uint8
----------
               slice 0.00052ms
       slice, contig 0.21878ms
              fliplr 0.00174ms
       fliplr contig 0.21828ms
                 cv2 0.07037ms (3.11x)
          cv2 contig 0.07355ms (2.97x)
            fort cv2 0.33900ms (0.65x)
     fort cv2 contig 0.34198ms (0.64x)
                cv2_ 0.08093ms (2.70x)
         cv2_ contig 0.08554ms (2.56x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.25783ms (0.17x)
fort cv2_ get contig 1.25868ms (0.17x)

----------
uint16
----------
               slice 0.00176ms
       slice, contig 0.21250ms
              fliplr 0.00489ms
       fliplr contig 0.21438ms
                 cv2 0.16964ms (1.25x)
          cv2 contig 0.17314ms (1.23x)
            fort cv2 0.50989ms (0.42x)
     fort cv2 contig 0.51188ms (0.42x)
                cv2_ 0.18803ms (1.13x)
         cv2_ contig 0.19136ms (1.11x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.48429ms (0.14x)
fort cv2_ get contig 1.48392ms (0.14x)

----------
uint32
----------
               slice 0.00181ms
       slice, contig 0.22855ms
              fliplr 0.00486ms
       fliplr contig 0.23070ms
                 cv2 Error: Expected cv::UMat for argument 'src'
          cv2 contig Error: Expected cv::UMat for argument 'src'
            fort cv2 Error: Expected cv::UMat for argument 'src'
     fort cv2 contig Error: Expected cv::UMat for argument 'src'
                cv2_ Error: Expected cv::UMat for argument 'src'
         cv2_ contig Error: Expected cv::UMat for argument 'src'
           fort cv2_ Error: Expected cv::UMat for argument 'src'
    fort cv2_ contig Error: Expected cv::UMat for argument 'src'
            cv2_ get Error: Expected cv::UMat for argument 'src'
     cv2_ get contig Error: Expected cv::UMat for argument 'src'
       fort cv2_ get Error: Expected cv::UMat for argument 'src'
fort cv2_ get contig Error: Expected cv::UMat for argument 'src'

----------
uint64
----------
               slice 0.00175ms
       slice, contig 0.28662ms
              fliplr 0.00497ms
       fliplr contig 0.28986ms
                 cv2 Error: Got dtype int32
          cv2 contig Error: Got dtype int32
            fort cv2 Error: Got dtype int32
     fort cv2 contig Error: Got dtype int32
                cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
         cv2_ contig Error: Got dtype object
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: Got dtype int32
     cv2_ get contig Error: Got dtype int32
       fort cv2_ get Error: Got dtype int32
fort cv2_ get contig Error: Got dtype int32

----------
int8
----------
               slice 0.00052ms
       slice, contig 0.21802ms
              fliplr 0.00183ms
       fliplr contig 0.21866ms
                 cv2 0.07026ms (3.10x)
          cv2 contig 0.07234ms (3.01x)
            fort cv2 0.34137ms (0.64x)
     fort cv2 contig 0.35426ms (0.62x)
                cv2_ 0.08145ms (2.68x)
         cv2_ contig 0.08498ms (2.57x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.27798ms (0.17x)
fort cv2_ get contig 1.26791ms (0.17x)

----------
int16
----------
               slice 0.00146ms
       slice, contig 0.21083ms
              fliplr 0.00443ms
       fliplr contig 0.21287ms
                 cv2 0.17461ms (1.21x)
          cv2 contig 0.17523ms (1.20x)
            fort cv2 0.51030ms (0.41x)
     fort cv2 contig 0.50438ms (0.42x)
                cv2_ 0.18627ms (1.13x)
         cv2_ contig 0.19703ms (1.07x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.47157ms (0.14x)
fort cv2_ get contig 1.48715ms (0.14x)

----------
int32
----------
               slice 0.00177ms
       slice, contig 0.22641ms
              fliplr 0.00505ms
       fliplr contig 0.22934ms
                 cv2 0.33548ms (0.67x)
          cv2 contig 0.34303ms (0.66x)
            fort cv2 0.77874ms (0.29x)
     fort cv2 contig 0.78380ms (0.29x)
                cv2_ 0.39785ms (0.57x)
         cv2_ contig 0.39249ms (0.58x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.89115ms (0.12x)
fort cv2_ get contig 1.89214ms (0.12x)

----------
int64
----------
               slice 0.00176ms
       slice, contig 0.28347ms
              fliplr 0.00484ms
       fliplr contig 0.28658ms
                 cv2 Error: Got dtype int32
          cv2 contig Error: Got dtype int32
            fort cv2 Error: Got dtype int32
     fort cv2 contig Error: Got dtype int32
                cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
         cv2_ contig Error: Got dtype object
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: Got dtype int32
     cv2_ get contig Error: Got dtype int32
       fort cv2_ get Error: Got dtype int32
fort cv2_ get contig Error: Got dtype int32

----------
float16
----------
               slice 0.00155ms
       slice, contig 0.21066ms
              fliplr 0.00435ms
       fliplr contig 0.21295ms
                 cv2 Error: Expected cv::UMat for argument 'src'
          cv2 contig Error: Expected cv::UMat for argument 'src'
            fort cv2 Error: Expected cv::UMat for argument 'src'
     fort cv2 contig Error: Expected cv::UMat for argument 'src'
                cv2_ Error: Expected cv::UMat for argument 'src'
         cv2_ contig Error: Expected cv::UMat for argument 'src'
           fort cv2_ Error: Expected cv::UMat for argument 'src'
    fort cv2_ contig Error: Expected cv::UMat for argument 'src'
            cv2_ get Error: Expected cv::UMat for argument 'src'
     cv2_ get contig Error: Expected cv::UMat for argument 'src'
       fort cv2_ get Error: Expected cv::UMat for argument 'src'
fort cv2_ get contig Error: Expected cv::UMat for argument 'src'

----------
float32
----------
               slice 0.00177ms
       slice, contig 0.22798ms
              fliplr 0.00495ms
       fliplr contig 0.22916ms
                 cv2 0.33821ms (0.67x)
          cv2 contig 0.31665ms (0.72x)
            fort cv2 0.78119ms (0.29x)
     fort cv2 contig 0.77838ms (0.29x)
                cv2_ 0.39515ms (0.58x)
         cv2_ contig 0.41023ms (0.56x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.88737ms (0.12x)
fort cv2_ get contig 1.89616ms (0.12x)

----------
float64
----------
               slice 0.00179ms
       slice, contig 0.28810ms
              fliplr 0.00495ms
       fliplr contig 0.29130ms
                 cv2 0.63258ms (0.46x)
          cv2 contig 0.64089ms (0.45x)
            fort cv2 1.64795ms (0.17x)
     fort cv2 contig 1.65449ms (0.17x)
                cv2_ 0.75202ms (0.38x)
         cv2_ contig 0.74789ms (0.39x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 3.99237ms (0.07x)
fort cv2_ get contig 3.97847ms (0.07x)

----------
float128
----------
               slice 0.00179ms
       slice, contig 0.51371ms
              fliplr 0.00545ms
       fliplr contig 0.51618ms
                 cv2 Error: Expected cv::UMat for argument 'src'
          cv2 contig Error: Expected cv::UMat for argument 'src'
            fort cv2 Error: Expected cv::UMat for argument 'src'
     fort cv2 contig Error: Expected cv::UMat for argument 'src'
                cv2_ Error: Expected cv::UMat for argument 'src'
         cv2_ contig Error: Expected cv::UMat for argument 'src'
           fort cv2_ Error: Expected cv::UMat for argument 'src'
    fort cv2_ contig Error: Expected cv::UMat for argument 'src'
            cv2_ get Error: Expected cv::UMat for argument 'src'
     cv2_ get contig Error: Expected cv::UMat for argument 'src'
       fort cv2_ get Error: Expected cv::UMat for argument 'src'
fort cv2_ get contig Error: Expected cv::UMat for argument 'src'

==============================
flip method followed by Add
==============================
               slice 1.29597ms
       slice, contig 1.32523ms
              fliplr 1.29298ms
       fliplr contig 1.33087ms
                 cv2 1.17829ms
          cv2 contig 1.18350ms
            fort cv2 1.45182ms
     fort cv2 contig 1.45762ms
                cv2_ 1.19331ms
         cv2_ contig 1.19364ms
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 2.43293ms
fort cv2_ get contig 2.48836ms

==============================
flip method followed by Affine
==============================
               slice 2.83081ms
       slice, contig 2.88243ms
              fliplr 2.84253ms
       fliplr contig 2.89106ms
                 cv2 2.72900ms
          cv2 contig 2.74500ms
            fort cv2 2.99842ms
     fort cv2 contig 3.03457ms
                cv2_ 2.73629ms
         cv2_ contig 2.77505ms
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 4.01583ms
fort cv2_ get contig 4.03347ms

==============================
flip method followed by AverageBlur
==============================
               slice 0.77109ms
       slice, contig 0.80603ms
              fliplr 0.77666ms
       fliplr contig 0.81088ms
                 cv2 0.66065ms
          cv2 contig 0.66496ms
            fort cv2 0.94078ms
     fort cv2 contig 0.92662ms
                cv2_ 0.65560ms
         cv2_ contig 0.66237ms
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.88932ms
fort cv2_ get contig 1.89190ms

"""

"""
Speed comparison by datatype and flip method.

VERTICAL FLIPS.

----------
bool
----------
               slice 0.00047ms
       slice, contig 0.02332ms
              flipud 0.00143ms
       flipud contig 0.02502ms
                 cv2 Error: Expected cv::UMat for argument 'src'
          cv2 contig Error: Expected cv::UMat for argument 'src'
            fort cv2 Error: Expected cv::UMat for argument 'src'
     fort cv2 contig Error: Expected cv::UMat for argument 'src'
                cv2_ Error: Expected cv::UMat for argument 'src'
         cv2_ contig Error: Expected cv::UMat for argument 'src'
           fort cv2_ Error: Expected cv::UMat for argument 'src'
    fort cv2_ contig Error: Expected cv::UMat for argument 'src'
            cv2_ get Error: Expected cv::UMat for argument 'src'
     cv2_ get contig Error: Expected cv::UMat for argument 'src'
       fort cv2_ get Error: Expected cv::UMat for argument 'src'
fort cv2_ get contig Error: Expected cv::UMat for argument 'src'

----------
uint8
----------
               slice 0.00049ms
       slice, contig 0.02311ms
              flipud 0.00155ms
       flipud contig 0.02506ms
                 cv2 0.03030ms (0.76x)
          cv2 contig 0.03401ms (0.68x)
            fort cv2 0.31000ms (0.07x)
     fort cv2 contig 0.33619ms (0.07x)
                cv2_ 0.01753ms (1.32x)
         cv2_ contig 0.01841ms (1.26x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.26680ms (0.02x)
fort cv2_ get contig 1.27027ms (0.02x)

----------
uint16
----------
               slice 0.00147ms
       slice, contig 0.04861ms
              flipud 0.00406ms
       flipud contig 0.05060ms
                 cv2 0.06169ms (0.79x)
          cv2 contig 0.06397ms (0.76x)
            fort cv2 0.39190ms (0.12x)
     fort cv2 contig 0.39098ms (0.12x)
                cv2_ 0.03375ms (1.44x)
         cv2_ contig 0.03619ms (1.34x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.51197ms (0.03x)
fort cv2_ get contig 1.52977ms (0.03x)

----------
uint32
----------
               slice 0.00167ms
       slice, contig 0.09415ms
              flipud 0.00476ms
       flipud contig 0.09660ms
                 cv2 Error: Expected cv::UMat for argument 'src'
          cv2 contig Error: Expected cv::UMat for argument 'src'
            fort cv2 Error: Expected cv::UMat for argument 'src'
     fort cv2 contig Error: Expected cv::UMat for argument 'src'
                cv2_ Error: Expected cv::UMat for argument 'src'
         cv2_ contig Error: Expected cv::UMat for argument 'src'
           fort cv2_ Error: Expected cv::UMat for argument 'src'
    fort cv2_ contig Error: Expected cv::UMat for argument 'src'
            cv2_ get Error: Expected cv::UMat for argument 'src'
     cv2_ get contig Error: Expected cv::UMat for argument 'src'
       fort cv2_ get Error: Expected cv::UMat for argument 'src'
fort cv2_ get contig Error: Expected cv::UMat for argument 'src'

----------
uint64
----------
               slice 0.00175ms
       slice, contig 0.17413ms
              flipud 0.00488ms
       flipud contig 0.17508ms
                 cv2 Error: Got dtype int32
          cv2 contig Error: Got dtype int32
            fort cv2 Error: Got dtype int32
     fort cv2 contig Error: Got dtype int32
                cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
         cv2_ contig Error: Got dtype object
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: Got dtype int32
     cv2_ get contig Error: Got dtype int32
       fort cv2_ get Error: Got dtype int32
fort cv2_ get contig Error: Got dtype int32

----------
int8
----------
               slice 0.00057ms
       slice, contig 0.02604ms
              flipud 0.00146ms
       flipud contig 0.02806ms
                 cv2 0.03434ms (0.76x)
          cv2 contig 0.03676ms (0.71x)
            fort cv2 0.30920ms (0.08x)
     fort cv2 contig 0.31123ms (0.08x)
                cv2_ 0.01625ms (1.60x)
         cv2_ contig 0.01799ms (1.45x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.29065ms (0.02x)
fort cv2_ get contig 1.29596ms (0.02x)

----------
int16
----------
               slice 0.00142ms
       slice, contig 0.05079ms
              flipud 0.00403ms
       flipud contig 0.05312ms
                 cv2 0.06277ms (0.81x)
          cv2 contig 0.06527ms (0.78x)
            fort cv2 0.39710ms (0.13x)
     fort cv2 contig 0.39851ms (0.13x)
                cv2_ 0.03419ms (1.49x)
         cv2_ contig 0.03668ms (1.38x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.52476ms (0.03x)
fort cv2_ get contig 1.52594ms (0.03x)

----------
int32
----------
               slice 0.00172ms
       slice, contig 0.09621ms
              flipud 0.00469ms
       flipud contig 0.09868ms
                 cv2 0.12192ms (0.79x)
          cv2 contig 0.12459ms (0.77x)
            fort cv2 0.57915ms (0.17x)
     fort cv2 contig 0.58571ms (0.16x)
                cv2_ 0.07337ms (1.31x)
         cv2_ contig 0.07595ms (1.27x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.97937ms (0.05x)
fort cv2_ get contig 1.97919ms (0.05x)

----------
int64
----------
               slice 0.00167ms
       slice, contig 0.17308ms
              flipud 0.00470ms
       flipud contig 0.17542ms
                 cv2 Error: Got dtype int32
          cv2 contig Error: Got dtype int32
            fort cv2 Error: Got dtype int32
     fort cv2 contig Error: Got dtype int32
                cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
         cv2_ contig Error: Got dtype object
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: Got dtype int32
     cv2_ get contig Error: Got dtype int32
       fort cv2_ get Error: Got dtype int32
fort cv2_ get contig Error: Got dtype int32

----------
float16
----------
               slice 0.00146ms
       slice, contig 0.05094ms
              flipud 0.00408ms
       flipud contig 0.05359ms
                 cv2 Error: Expected cv::UMat for argument 'src'
          cv2 contig Error: Expected cv::UMat for argument 'src'
            fort cv2 Error: Expected cv::UMat for argument 'src'
     fort cv2 contig Error: Expected cv::UMat for argument 'src'
                cv2_ Error: Expected cv::UMat for argument 'src'
         cv2_ contig Error: Expected cv::UMat for argument 'src'
           fort cv2_ Error: Expected cv::UMat for argument 'src'
    fort cv2_ contig Error: Expected cv::UMat for argument 'src'
            cv2_ get Error: Expected cv::UMat for argument 'src'
     cv2_ get contig Error: Expected cv::UMat for argument 'src'
       fort cv2_ get Error: Expected cv::UMat for argument 'src'
fort cv2_ get contig Error: Expected cv::UMat for argument 'src'

----------
float32
----------
               slice 0.00164ms
       slice, contig 0.09606ms
              flipud 0.00461ms
       flipud contig 0.09897ms
                 cv2 0.12151ms (0.79x)
          cv2 contig 0.12514ms (0.77x)
            fort cv2 0.57887ms (0.17x)
     fort cv2 contig 0.58280ms (0.16x)
                cv2_ 0.07312ms (1.31x)
         cv2_ contig 0.07581ms (1.27x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.97501ms (0.05x)
fort cv2_ get contig 1.98010ms (0.05x)

----------
float64
----------
               slice 0.00170ms
       slice, contig 0.17300ms
              flipud 0.00483ms
       flipud contig 0.17539ms
                 cv2 0.23941ms (0.72x)
          cv2 contig 0.24220ms (0.71x)
            fort cv2 1.26645ms (0.14x)
     fort cv2 contig 1.27246ms (0.14x)
                cv2_ 0.14879ms (1.16x)
         cv2_ contig 0.15185ms (1.14x)
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 4.02958ms (0.04x)
fort cv2_ get contig 4.02822ms (0.04x)

----------
float128
----------
               slice 0.00168ms
       slice, contig 0.35407ms
              flipud 0.00513ms
       flipud contig 0.35716ms
                 cv2 Error: Expected cv::UMat for argument 'src'
          cv2 contig Error: Expected cv::UMat for argument 'src'
            fort cv2 Error: Expected cv::UMat for argument 'src'
     fort cv2 contig Error: Expected cv::UMat for argument 'src'
                cv2_ Error: Expected cv::UMat for argument 'src'
         cv2_ contig Error: Expected cv::UMat for argument 'src'
           fort cv2_ Error: Expected cv::UMat for argument 'src'
    fort cv2_ contig Error: Expected cv::UMat for argument 'src'
            cv2_ get Error: Expected cv::UMat for argument 'src'
     cv2_ get contig Error: Expected cv::UMat for argument 'src'
       fort cv2_ get Error: Expected cv::UMat for argument 'src'
fort cv2_ get contig Error: Expected cv::UMat for argument 'src'

==============================
flip method followed by Add
==============================
               slice 1.11286ms
       slice, contig 1.14822ms
              flipud 1.11858ms
       flipud contig 1.14703ms
                 cv2 1.14892ms
          cv2 contig 1.15923ms
            fort cv2 1.43633ms
     fort cv2 contig 1.44342ms
                cv2_ 1.15194ms
         cv2_ contig 1.14864ms
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 2.47966ms
fort cv2_ get contig 2.48177ms

==============================
flip method followed by Affine
==============================
               slice 2.61450ms
       slice, contig 2.67402ms
              flipud 2.62069ms
       flipud contig 2.67267ms
                 cv2 2.66312ms
          cv2 contig 2.68482ms
            fort cv2 2.94520ms
     fort cv2 contig 2.97767ms
                cv2_ 2.64183ms
         cv2_ contig 2.64857ms
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 3.94321ms
fort cv2_ get contig 4.01652ms

==============================
flip method followed by AverageBlur
==============================
               slice 0.57750ms
       slice, contig 0.60905ms
              flipud 0.58156ms
       flipud contig 0.61562ms
                 cv2 0.61704ms
          cv2 contig 0.62293ms
            fort cv2 0.90804ms
     fort cv2 contig 0.90495ms
                cv2_ 0.60047ms
         cv2_ contig 0.60876ms
           fort cv2_ Error: 'cv2.UMat' object has no attribute 'ndim'
    fort cv2_ contig Error: Got dtype object
            cv2_ get Error: 'numpy.ndarray' object has no attribute 'get'
     cv2_ get contig Error: 'numpy.ndarray' object has no attribute 'get'
       fort cv2_ get 1.93064ms
fort cv2_ get contig 1.95215ms
"""
# pylint:enable=pointless-string-statement

_FLIPLR_DTYPES_CV2 = {"uint8", "uint16", "int8", "int16"}


def fliplr(arr):
    """Flip an image-like array horizontally.

    dtype support::

        * ``uint8``: yes; fully tested
        * ``uint16``: yes; fully tested
        * ``uint32``: yes; fully tested
        * ``uint64``: yes; fully tested
        * ``int8``: yes; fully tested
        * ``int16``: yes; fully tested
        * ``int32``: yes; fully tested
        * ``int64``: yes; fully tested
        * ``float16``: yes; fully tested
        * ``float32``: yes; fully tested
        * ``float64``: yes; fully tested
        * ``float128``: yes; fully tested
        * ``bool``: yes; fully tested

    Parameters
    ----------
    arr : ndarray
        A 2D/3D `(H, W, [C])` image array.

    Returns
    -------
    ndarray
        Horizontally flipped array.

    Examples
    --------
    >>> import numpy as np
    >>> import imgaug.augmenters.flip as flip
    >>> arr = np.arange(16).reshape((4, 4))
    >>> arr_flipped = flip.fliplr(arr)

    Create a ``4x4`` array and flip it horizontally.

    """
    if arr.dtype.name in _FLIPLR_DTYPES_CV2:
        return _fliplr_cv2(arr)
    return _fliplr_sliced(arr)


def _fliplr_sliced(arr):
    return arr[:, ::-1, ...]


def _fliplr_cv2(arr):
    # cv2.flip() returns None for arrays with zero height or width
    if arr.shape[0] == 0 or arr.shape[1] == 0:
        return np.copy(arr)

    result = cv2.flip(arr, 1)
    if result.ndim == 2 and arr.ndim == 3:
        return result[..., np.newaxis]
    return result


def flipud(arr):
    """Flip an image-like array vertically.

    dtype support::

        * ``uint8``: yes; fully tested
        * ``uint16``: yes; fully tested
        * ``uint32``: yes; fully tested
        * ``uint64``: yes; fully tested
        * ``int8``: yes; fully tested
        * ``int16``: yes; fully tested
        * ``int32``: yes; fully tested
        * ``int64``: yes; fully tested
        * ``float16``: yes; fully tested
        * ``float32``: yes; fully tested
        * ``float64``: yes; fully tested
        * ``float128``: yes; fully tested
        * ``bool``: yes; fully tested

    Parameters
    ----------
    arr : ndarray
        A 2D/3D `(H, W, [C])` image array.

    Returns
    -------
    ndarray
        Vertically flipped array.

    Examples
    --------
    >>> import numpy as np
    >>> import imgaug.augmenters.flip as flip
    >>> arr = np.arange(16).reshape((4, 4))
    >>> arr_flipped = flip.flipud(arr)

    Create a ``4x4`` array and flip it vertically.

    """
    # Note that this function is currently not called by Flipud for performance
    # reasons. Changing this will therefore not affect Flipud.
    return arr[::-1, ...]


def HorizontalFlip(*args, **kwargs):
    """Alias for Fliplr."""
    return Fliplr(*args, **kwargs)


def VerticalFlip(*args, **kwargs):
    """Alias for Flipud."""
    return Flipud(*args, **kwargs)


class Fliplr(meta.Augmenter):
    """Flip/mirror input images horizontally.

    .. note ::

        The default value for the probability is ``0.0``.
        So, to flip *all* input images use ``Fliplr(1.0)`` and *not* just
        ``Fliplr()``.

    dtype support::

        See :func:`imgaug.augmenters.flip.fliplr`.

    Parameters
    ----------
    p : number or imgaug.parameters.StochasticParameter, optional
        Probability of each image to get flipped.

    name : None or str, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    deterministic : bool, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    random_state : None or int or imgaug.random.RNG or numpy.random.Generator or numpy.random.bit_generator.BitGenerator or numpy.random.SeedSequence or numpy.random.RandomState, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    Examples
    --------
    >>> import imgaug.augmenters as iaa
    >>> aug = iaa.Fliplr(0.5)

    Flip ``50`` percent of all images horizontally.


    >>> aug = iaa.Fliplr(1.0)

    Flip all images horizontally.

    """

    def __init__(self, p=0, name=None, deterministic=False, random_state=None):
        super(Fliplr, self).__init__(
            name=name, deterministic=deterministic, random_state=random_state)
        self.p = iap.handle_probability_param(p, "p")

    def _augment_images(self, images, random_state, parents, hooks):
        nb_images = len(images)
        samples = self.p.draw_samples((nb_images,), random_state=random_state)
        for i, (image, sample) in enumerate(zip(images, samples)):
            if sample > 0.5:
                images[i] = fliplr(image)
        return images

    def _augment_heatmaps(self, heatmaps, random_state, parents, hooks):
        arrs_flipped = self._augment_images(
            [heatmaps_i.arr_0to1 for heatmaps_i in heatmaps],
            random_state=random_state,
            parents=parents,
            hooks=hooks
        )
        for heatmaps_i, arr_flipped in zip(heatmaps, arrs_flipped):
            heatmaps_i.arr_0to1 = arr_flipped
        return heatmaps

    def _augment_segmentation_maps(self, segmaps, random_state, parents, hooks):
        arrs_flipped = self._augment_images(
            [segmaps_i.arr for segmaps_i in segmaps],
            random_state=random_state,
            parents=parents,
            hooks=hooks
        )
        for segmaps_i, arr_flipped in zip(segmaps, arrs_flipped):
            segmaps_i.arr = arr_flipped
        return segmaps

    def _augment_keypoints(self, keypoints_on_images, random_state, parents,
                           hooks):
        nb_images = len(keypoints_on_images)
        samples = self.p.draw_samples((nb_images,), random_state=random_state)
        for i, keypoints_on_image in enumerate(keypoints_on_images):
            if not keypoints_on_image.keypoints:
                continue
            elif samples[i] > 0.5:
                width = keypoints_on_image.shape[1]
                for keypoint in keypoints_on_image.keypoints:
                    keypoint.x = width - float(keypoint.x)
        return keypoints_on_images

    def _augment_polygons(self, polygons_on_images, random_state, parents,
                          hooks):
        # TODO maybe reverse the order of points afterwards? the flip probably
        #      inverts them
        return self._augment_polygons_as_keypoints(
            polygons_on_images, random_state, parents, hooks)

    def get_parameters(self):
        return [self.p]


# TODO merge with Fliplr
class Flipud(meta.Augmenter):
    """Flip/mirror input images vertically.

    .. note ::

        The default value for the probability is ``0.0``.
        So, to flip *all* input images use ``Flipud(1.0)`` and *not* just
        ``Flipud()``.

    dtype support::

        See :func:`imgaug.augmenters.flip.flipud`.

    Parameters
    ----------
    p : number or imgaug.parameters.StochasticParameter, optional
        Probability of each image to get flipped.

    name : None or str, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    deterministic : bool, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    random_state : None or int or imgaug.random.RNG or numpy.random.Generator or numpy.random.bit_generator.BitGenerator or numpy.random.SeedSequence or numpy.random.RandomState, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    Examples
    --------
    >>> import imgaug.augmenters as iaa
    >>> aug = iaa.Flipud(0.5)

    Flip ``50`` percent of all images vertically.

    >>> aug = iaa.Flipud(1.0)

    Flip all images vertically.

    """

    def __init__(self, p=0, name=None, deterministic=False, random_state=None):
        super(Flipud, self).__init__(
            name=name, deterministic=deterministic, random_state=random_state)
        self.p = iap.handle_probability_param(p, "p")

    def _augment_images(self, images, random_state, parents, hooks):
        nb_images = len(images)
        samples = self.p.draw_samples((nb_images,), random_state=random_state)
        for i, (image, sample) in enumerate(zip(images, samples)):
            if sample > 0.5:
                # We currently do not use flip.flipud() here, because that
                # saves a function call.
                images[i] = image[::-1, ...]
        return images

    def _augment_heatmaps(self, heatmaps, random_state, parents, hooks):
        arrs_flipped = self._augment_images(
            [heatmaps_i.arr_0to1 for heatmaps_i in heatmaps],
            random_state=random_state,
            parents=parents,
            hooks=hooks
        )
        for heatmaps_i, arr_flipped in zip(heatmaps, arrs_flipped):
            heatmaps_i.arr_0to1 = arr_flipped
        return heatmaps

    def _augment_segmentation_maps(self, segmaps, random_state, parents, hooks):
        arrs_flipped = self._augment_images(
            [segmaps_i.arr for segmaps_i in segmaps],
            random_state=random_state,
            parents=parents,
            hooks=hooks
        )
        for segmaps_i, arr_flipped in zip(segmaps, arrs_flipped):
            segmaps_i.arr = arr_flipped
        return segmaps

    def _augment_keypoints(self, keypoints_on_images, random_state, parents,
                           hooks):
        nb_images = len(keypoints_on_images)
        samples = self.p.draw_samples((nb_images,), random_state=random_state)
        for i, keypoints_on_image in enumerate(keypoints_on_images):
            if not keypoints_on_image.keypoints:
                continue
            elif samples[i] > 0.5:
                height = keypoints_on_image.shape[0]
                for keypoint in keypoints_on_image.keypoints:
                    keypoint.y = height - float(keypoint.y)
        return keypoints_on_images

    def _augment_polygons(self, polygons_on_images, random_state, parents,
                          hooks):
        # TODO how does flipping affect the point order?
        return self._augment_polygons_as_keypoints(
            polygons_on_images, random_state, parents, hooks)

    def get_parameters(self):
        return [self.p]
