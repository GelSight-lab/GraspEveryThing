import cv2
import math
import numpy as np

import scipy, scipy.fftpack
from scipy.interpolate import griddata
from scipy.signal import convolve2d

# Return the closest odd integer to the given float
def closest_odd_int(x):
    if math.floor(x) % 2 == 1:
        return math.floor(x)
    else:
        return math.ceil(x)

def draw_circle(img, cx, cy, r):
    cimg = img.copy()
    # draw circle boundary
    cv2.circle(cimg, (cy, cx), r, (255, 255, 255), -1)
    cimg = img * 1.0 - cimg / 6
    cimg = np.clip(cimg, 0, 255).astype(np.uint8)
    # draw the center of the circle
    cv2.circle(cimg, (cy, cx), 2, (0, 0, 255), 3)
    return cimg

def label_circle(img, cx=200, cy=150, r=10):
    # label the circle info: r (radius), cx (center x), cy (center y)
    dx, dy, dr = 1, 1, 1
    while True:
        cimg = draw_circle(img, cx, cy, r)
        cv2.imshow("label_circle", cimg)

        c = cv2.waitKey(1)
        if c == ord("q") or c == 27:
            # save
            return cx, cy, r
        elif c == ord("w"):
            # Up
            cx -= dx
        elif c == ord("s"):
            # Down
            cx += dx
        elif c == ord("a"):
            # Left
            cy -= dy
        elif c == ord("d"):
            # Right
            cy += dy
        elif c == ord("="):
            # Increase radius
            r += dr
        elif c == ord("-"):
            # Decrese radius
            r -= dr

def find_marker(frame, threshold_list=(0.275, 0.275, 0.275)): # threshold_list=(80, 80, 80)):
    RESCALE = 600.0 / frame.shape[0]
    frame_small = frame

    # Blur image to remove noise
    kernel_size = closest_odd_int(127 / RESCALE)
    blur = cv2.GaussianBlur(frame_small, (kernel_size, kernel_size), 0)

    # Subtract the surrounding pixels to magnify difference between markers and background
    diff = blur - frame_small.astype(np.float32)
    diff *= 16.0
    # diff = np.clip(diff, -30, 255.0)
    kernel_size = closest_odd_int(15 / RESCALE)
    diff = cv2.GaussianBlur(diff, (kernel_size, kernel_size), 0)
    mask = (
        (diff[:, :, 0] > threshold_list[0])
        & (diff[:, :, 2] > threshold_list[1])
        & (diff[:, :, 1] > threshold_list[2])
    )
    mask = cv2.resize(mask.astype(np.uint8), (frame.shape[1], frame.shape[0]))
    return mask

def dilate(img, ksize=5):
    kernel = np.ones((ksize, ksize), np.uint8)
    return cv2.dilate(img, kernel, iterations=1)

def erode(img, ksize=5):
    kernel = np.ones((ksize, ksize), np.uint8)
    return cv2.erode(img, kernel, iterations=1)

def interpolate_grad(img, mask):
    # mask = (soft_mask > 0.5).astype(np.uint8) * 255
    # cv2.imshow("mask_hard", mask)
    # pixel around markers
    mask_around = (dilate(mask, ksize=3) > 0) & (mask != 1)
    # mask_around = mask == 0
    mask_around = mask_around.astype(np.uint8)

    x, y = np.arange(img.shape[0]), np.arange(img.shape[1])
    yy, xx = np.meshgrid(y, x)

    # mask_zero = mask == 0
    mask_zero = mask_around == 1
    mask_x = xx[mask_zero]
    mask_y = yy[mask_zero]
    points = np.vstack([mask_x, mask_y]).T
    values = img[mask_x, mask_y]
    markers_points = np.vstack([xx[mask != 0], yy[mask != 0]]).T
    # method = "nearest"
    method = "linear"
    # method = "cubic"
    x_interp = griddata(points, values, markers_points, method=method)
    x_interp[x_interp != x_interp] = 0.0
    ret = img.copy()
    ret[mask != 0] = x_interp
    return ret

def demark(img, gx, gy):
    mask = find_marker(img)
    gx = interpolate_grad(gx, mask)
    gy = interpolate_grad(gy, mask)
    return gx, gy

def warp_perspective(img, corners, output_sz=(210, 270)):
    TOPLEFT, TOPRIGHT, BOTTOMLEFT, BOTTOMRIGHT = corners
    WARP_W = output_sz[0]
    WARP_H = output_sz[1]
    points1=np.float32([TOPLEFT,TOPRIGHT,BOTTOMLEFT,BOTTOMRIGHT])
    points2=np.float32([[0,0],[WARP_W,0],[0,WARP_H],[WARP_W,WARP_H]])
    matrix=cv2.getPerspectiveTransform(points1,points2)
    result = cv2.warpPerspective(img, matrix, (WARP_W, WARP_H))
    return result

def poisson_reconstruct(grady, gradx, boundarysrc):
    # Thanks to Dr. Ramesh Raskar for providing the original matlab code from which this is derived
    # Dr. Raskar's version is available here: http://web.media.mit.edu/~raskar/photo/code.pdf

    # Laplacian
    gyy = grady[1:,:-1] - grady[:-1,:-1]
    gxx = gradx[:-1,1:] - gradx[:-1,:-1]
    f = np.zeros(boundarysrc.shape)
    f[:-1,1:] += gxx
    f[1:,:-1] += gyy

    # Boundary image
    boundary = boundarysrc.copy()
    boundary[1:-1,1:-1] = 0

    # Subtract boundary contribution
    f_bp = -4*boundary[1:-1,1:-1] + boundary[1:-1,2:] + boundary[1:-1,0:-2] + boundary[2:,1:-1] + boundary[0:-2,1:-1]
    f = f[1:-1,1:-1] - f_bp

    # Discrete Sine Transform
    tt = scipy.fftpack.dst(f, norm='ortho')
    fsin = scipy.fftpack.dst(tt.T, norm='ortho').T

    # Eigenvalues
    (x,y) = np.meshgrid(range(1,f.shape[1]+1), range(1,f.shape[0]+1), copy=True)
    denom = (2*np.cos(math.pi*x/(f.shape[1]+2))-2) + (2*np.cos(math.pi*y/(f.shape[0]+2)) - 2)
    f = fsin/denom

    # Inverse Discrete Sine Transform
    tt = scipy.fftpack.idst(f, norm='ortho')
    img_tt = scipy.fftpack.idst(tt.T, norm='ortho').T

    # New center + old boundary
    result = boundary
    result[1:-1,1:-1] = img_tt

    return result