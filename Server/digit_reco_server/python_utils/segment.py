import cv2
import numpy as np
import os.path
import math
import sys
from sympySolver import solveIt
import json

# from preprocessor import process_image_for_ocr
from predict import predict_image


ymin,ymax,xmax,xmin = 0,0,0,0
xminCrop, yminCrop = 100000, 100000
xmaxCrop, ymaxCrop = 0, 0

def img_segment(file):

    global ymax,ymin,xmax,xmin

    path=file
    im = cv2.imread(path)
    # im = process_image_for_ocr(path)
    # cv2.imwrite('./Images/preprocessed.jpg',im)
    im = cv2.fastNlMeansDenoisingColored(im,None,10,10,7,21)
    global gray_image
    gray_image = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

    folder_path,name = os.path.split(path)
    folder_path = os.path.splitext(folder_path)[0]

    gray_path = os.path.join(folder_path, "gray_"+name)

    im = gray_image
    mini = 255
    maxi = 0
    j=0
    while j < im.shape[1]:
        i=0
        while i<im.shape[0]:
            if im[i][j] > maxi:
                maxi = im[i][j]
            if im[i][j] < mini:
                mini = im[i][j]
            i = i +1
        j = j + 1
    avg = (0.4*maxi + 0.6*mini)
    j=0
    while j < im.shape[1]:
        i=0
        while i<im.shape[0]:
            if im[i][j] <avg:
                im[i][j] = 0
            else:
                im[i][j] = 255
            i = i+1
        j = j+1



    gray_image = im

    cv2.imwrite(gray_path, gray_image)

    segmented_image_list = []
    flag = 0
    write_flag = False
    global output_image
    output_image = np.full((gray_image.shape[0], gray_image.shape[1]), 255)


    j=0
    while j < gray_image.shape[1]:
        i=0
        while i<gray_image.shape[0]:

            if gray_image[i][j] <= 123:
                write_flag = True

                # yjump,xmax,xmin =
                yjump = dfs(i,j)

                global xminCrop, xmaxCrop, yminCrop, ymaxCrop
                xminCrop = min(xminCrop, xmin)
                yminCrop = min(yminCrop, ymin)
                xmaxCrop = max(xmaxCrop, xmax)
                ymaxCrop = max(ymaxCrop, ymax)

                max_jump = int(yjump*0.5)
                if max_jump != 0: #And symbol is not square root -> Has to be dealt seperately
                    j += max_jump
                    i=-1
            i+=1
        j+=1

        if write_flag:
            write_flag = False
            flag += 1

            seg_path = os.path.join(folder_path,str(flag)+"seg_"+ name)
            output_image = output_image[xminCrop:xmaxCrop, yminCrop:ymaxCrop]

            ydiff = xmax-xmin
            xdiff = ymax-ymin
            # pads each side with 50 pixels
            pad1 = 0
            pad2 = 0

            if xdiff>ydiff:
                pad1 += (xdiff-ydiff)/2
            else:
                pad2 += (ydiff-xdiff)/2

            output_image = cv2.copyMakeBorder(output_image,
                    math.floor(pad1),math.ceil(pad1),math.floor(pad2),math.ceil(pad2),
                    cv2.BORDER_CONSTANT,value=[255,255,255])

            cv2.imwrite(seg_path,output_image)
            output_image = np.full((gray_image.shape[0], gray_image.shape[1]), 255)
            segmented_image_list.append(seg_path)

            xminCrop, yminCrop = 100000, 100000
            xmaxCrop, ymaxCrop = 0, 0

    predicted_list = [ '(' ]
    for i,img in enumerate(segmented_image_list):
        if str(predict_image(img, i)) == '=' :
            predicted_list.append(')')
            predicted_list.append('-')
            predicted_list.append('(')
        else:
            predicted_list.append(str(predict_image(img,i)))
    predicted_list.append(')')

    final_eq = "("
    i = 1
    while i < len(predicted_list):
        val = predicted_list[i]
        if val >= '0' and val <= '9':
            final_eq += val
            i+=1
            val = predicted_list[i]
            while i < len(predicted_list) and (val >= '0' and val <= '9'):
                final_eq += val
                i+=1
                val = predicted_list[i]
            final_eq += '*'
            i -= 1
        elif val == '(' or val == ')' or val == '+' or val == '-':
            if final_eq[-1] == '*':
                final_eq = final_eq[:-1]
            final_eq += val
        elif val == "pi" or val == 'e':
            final_eq += val
            final_eq += '*'
        else:
            if predicted_list[i+1] >= '0' and predicted_list[i+1] <= '9':
                final_eq += val
                final_eq += "**"
            else :
                final_eq += val
        i = i + 1

    result = {}
    result["solution"] = solveIt(final_eq)
    result["equation"] = final_eq
    print(json.dumps(result))
    sys.stdout.flush()

def dfs(a,b):
#Iterative
    global ymax,ymin,xmax,xmin
    ymin,ymax = b,b
    xmax,xmin = a,a

    stack = []
    stack.append((a, b))
    while len(stack):
        x = stack[-1][0]
        y = stack[-1][1]

        # if ymax < y:
        #     ymax = y
        ymax = max(y, ymax)
        ymin = min(y, ymin)

        xmax = max(x, xmax)
        xmin = min(x, xmin)

        stack.pop()

        if gray_image[x][y] > 123:
            continue
        else:
            gray_image[x][y] = 255
            output_image[x][y] = 0
            for i in range(-1,2):
                for j in range(-1,2):
                    if i+x>=0 and i+x<gray_image.shape[0] and y+j>=0 and y+j<gray_image.shape[1] :
                        stack.append((x+i,y+j))
    return (ymax-ymin)

img_segment(sys.argv[1])