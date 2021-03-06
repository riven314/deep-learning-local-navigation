import os
import sys
import time
ROOT_PATH = os.path.join(os.getcwd(), '..', '..')
MOBILENET_PATH = os.path.join(ROOT_PATH, 'mobilenet_segment')
sys.path.append(ROOT_PATH)
sys.path.append(MOBILENET_PATH)

import numpy as np
import cv2
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject
import torch
from model_utils import ModelMetaConfig

class FrameStore:
    """
    store key data at a snapshot
    (i.e. rgb image, depth image and segmentation result)

    attribute:
        rgb_img -- np array
        depth_img -- np array
        seg_out -- np array 
    
    * all have same dimension
    """
    def __init__(self):
        self.rgb_img_1 = None
        self.rgb_img_2 = None
        self.seg_out = None
        

class FrameObject(QObject):
    frame_signal = pyqtSignal(FrameStore)

    def __init__(self, parent = None):
        super().__init__()
        self.load_img()
        self.IS_SILENT = True
        self.model_config = ModelMetaConfig(root = MOBILENET_PATH)
        self.model_config.ENSEMBLE_N = 1
        self.frame_store = FrameStore()
        self.switch = True
    
    def load_img(self):
        self.PATH_1 = os.path.join(os.getcwd(), '..', '..', 'test_cases', 'test2_rgb.jpg')
        self.PATH_2 = os.path.join(os.getcwd(), '..', '..', 'test_cases', 'test3_rgb.jpg')
        rgb_img_1 = cv2.imread(self.PATH_1)
        rgb_img_2 = cv2.imread(self.PATH_2)
        # slow without img.copy()
        #self.rgb_img_1 = rgb_img_1[:, :, ::-1].copy()
        #self.rgb_img_2 = rgb_img_2[:, :, ::-1].copy()
        self.rgb_img_1 = rgb_img_1
        self.rgb_img_2 = rgb_img_2

    @pyqtSlot()
    def run(self):
        """
        continuously feed image into segmentation model repeatedly (to simulate real time workload)

        BREAKDOWN (MAIN THREAD):
            [model run] 100 - 110 ms
            [unexplained] ~1-5 ms
        """
        end_loop = time.time()
        while True:
            crt_t = time.time()
            print('time = {:10.4f} s'.format(time.time()))
            print('unexplain = {:10.4f} s'.format(crt_t - end_loop))
            torch.cuda.synchronize()
            start = time.time()
            if self.switch:
                rgb_img = self.rgb_img_1
                self.switch = False
            else:
                rgb_img = self.rgb_img_2
                self.switch = True
            seg_out = self.model_config.raw_predict(rgb_img, self.IS_SILENT)
            seg_out = self.model_config.process_predict(seg_out, self.IS_SILENT)
            torch.cuda.synchronize()
            end = time.time()
            print('model run = {:10.4f} s'.format(end - start))
            start = time.time()
            # store key data at a snapsho
            self.frame_store.rgb_img = rgb_img
            self.frame_store.seg_out = seg_out
            self.frame_signal.emit(self.frame_store)
            end_loop = time.time()
            print('emit = {:10.4f} s'.format(end_loop - start))

