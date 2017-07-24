# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
from argparse import RawTextHelpFormatter
import os
import shutil
import cv2
from deep_ocr.caffe_clf import CaffeClsBuilder
from deep_ocr.cv2_img_proc import PreprocessResizeKeepRatio
from deep_ocr.cv2_img_proc import PreprocessBackgroundMask
from deep_ocr.id_cards.segmentation import Segmentation
from deep_ocr.id_cards.char_set import CharSet
from deep_ocr.reco_text_line import RecoTextLine
from deep_ocr.reco_text_line import RectImageClassifier

import json
from flask import Flask
from flask import request
from flask import redirect
from flask import jsonify
app = Flask(__name__)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
	if request.method == 'POST':
		f = request.files['file']
		f.save('/home/ygh/flask/id_card_img.jpg')
		
		## path_img = os.path.expanduser("/home/ygh/deep_ocr/data/id_card_img.jpg")
		path_img = os.path.expanduser("/home/ygh/flask/id_card_img.jpg")
		debug_path = os.path.expanduser("/home/ygh/deep_ocr_workspace/debug")
		if debug_path is not None:
			if os.path.isdir(debug_path):
				shutil.rmtree(debug_path)
			os.makedirs(debug_path)

    	cls_dir_sim = os.path.expanduser("/home/ygh/deep_ocr_workspace/data/chongdata_caffe_cn_sim_digits_64_64")
    	cls_dir_ua = os.path.expanduser("/home/ygh/deep_ocr_workspace/data/chongdata_train_ualpha_digits_64_64")

    	caffe_cls_builder = CaffeClsBuilder()
    	cls_sim = caffe_cls_builder.build(cls_dir=cls_dir_sim,)
    	cls_ua = caffe_cls_builder.build(cls_dir=cls_dir_ua,)
    	caffe_classifiers = {"sim": cls_sim, "ua": cls_ua}

    	seg_norm_width = 600
    	seg_norm_height = 600
    	preprocess_resize = PreprocessResizeKeepRatio(
        	seg_norm_width, seg_norm_height)
    	id_card_img = cv2.imread(path_img)
    	id_card_img = preprocess_resize.do(id_card_img)    
    	segmentation = Segmentation(debug_path)
    	key_to_segmentation = segmentation.do(id_card_img)

    	boundaries = [
        	((0, 0, 0), (100, 100, 100)),
    	]
    	boundary2binimgs = []
    	for boundary in boundaries:
        	preprocess_bg_mask = PreprocessBackgroundMask(boundary)
        	id_card_img_mask = preprocess_bg_mask.do(id_card_img)
        	boundary2binimgs.append((boundary, id_card_img_mask))

    	char_set = CharSet()
    	char_set_data = char_set.get()

    	rect_img_clf = RectImageClassifier(
        	None,
        	None,
        	char_set,
        	caffe_cls_width=64,
        	caffe_cls_height=64)

    	reco_text_line = RecoTextLine(rect_img_clf)

    	key_ocr_res = {}
    	for key in key_to_segmentation:
        	key_ocr_res[key] = []
        	print("="*64)
        	print(key)
        	for i, segment in enumerate(key_to_segmentation[key]):
				if debug_path is not None:
					line_debug_path = "key_%s_%i" % (key, i)
					line_debug_path = os.path.join(debug_path, line_debug_path)
					reco_text_line.debug_path = line_debug_path
				reco_text_line.char_set = char_set_data[key]
                ## 初始化模型
				caffe_cls = caffe_classifiers[
					char_set_data[key]["caffe_cls"]]
                ## 输入到模型中进行识别
				ocr_res = reco_text_line.do(boundary2binimgs, segment, caffe_cls)
                ## 将结果输出到列表中
				key_ocr_res[key].append(ocr_res)
    	print("ocr res:")
    	for key in key_ocr_res:
        	print("="*60)
        	print(key)
        	for res_i in key_ocr_res[key]:
				print(res_i.encode("utf-8"))
    	if debug_path is not None:
        	path_debug_image_mask = os.path.join(
				debug_path, "reco_debug_01_image_mask.jpg")
		cv2.imwrite(path_debug_image_mask, id_card_img_mask)

        ## 返回结果 将其封装成json的键值对的格式
		data = [{"result":"sucess","response":{"name":key_ocr_res["name"],"address":key_ocr_res["address"],"month":key_ocr_res["month"],"minzu":key_ocr_res["minzu"],"year":key_ocr_res["year"],"sex":key_ocr_res["sex"],"id":key_ocr_res["id"],"day":key_ocr_res["day"]}}]
		## data = '{"result":"sucess"}
		## result = json.loads(data)
		return json.dumps(data,skipkeys=True,ensure_ascii=False,encoding="utf-8")
	else:
		data2 = [{"result":"error"}]
		## result2 = json.loads(data2)
		return json.dumps(data2)
		## return "error"
		



if __name__ == '__main__':
	app.run(host='0.0.0.0',port=8880)