import matplotlib.pyplot as plt
import numpy as np
import math

import torch
from torchvision import models
import torch.nn as nn

import make_datapath_list
import data_transform
import original_dataset
import original_network
import original_criterion

## device
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("device = ", device)

## network
net = original_network.OriginalNet()
print(net)
net.to(device)
net.eval()

## saved in CPU -> load in CPU, saved in GPU -> load in GPU
load_path = "../weights/mle.pth"
load_weights = torch.load(load_path)
net.load_state_dict(load_weights)

## trans param
size = 224  #VGG16
mean = ([0.25, 0.25, 0.25])
std = ([0.5, 0.5, 0.5])

## list
train_rootpath = "../dataset/train"
val_rootpath = "../dataset/val"
csv_name = "imu_camera.csv"
train_list = make_datapath_list.make_datapath_list(train_rootpath, csv_name)
val_list = make_datapath_list.make_datapath_list(val_rootpath, csv_name)

## transform
transform = data_transform.data_transform(size, mean, std)

## dataset
train_dataset = original_dataset.OriginalDataset(
    data_list=train_list,
    transform=data_transform.data_transform(size, mean, std),
    phase="train"
)
val_dataset = original_dataset.OriginalDataset(
    data_list=val_list,
    transform=data_transform.data_transform(size, mean, std),
    phase="val"
)

## dataloader
batch_size = 10
train_dataloader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
val_dataloader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
dataloaders_dict = {"train": train_dataloader, "val": val_dataloader}

## predict
inputs_arr = np.empty(0)
labels_arr = np.empty([0, 3])
mu_arr = np.empty([0, 3])
cov_arr = np.empty([0, 3, 3])
for inputs, labels in dataloaders_dict["val"]:
    inputs = inputs.to(device)
    outputs = net(inputs)
    Cov = original_criterion.getCovMatrix(outputs)
    ## tensor -> numpy
    inputs_arr = np.append(
        inputs_arr.reshape(-1, inputs.size(1), inputs.size(2), inputs.size(3)),
        inputs.cpu().detach().numpy(),
        axis=0
    )
    labels_arr = np.append(labels_arr, labels.cpu().detach().numpy(), axis=0)
    mu_arr = np.append(mu_arr, outputs[:, :3].cpu().detach().numpy(), axis=0)
    cov_arr = np.append(cov_arr, Cov.cpu().detach().numpy(), axis=0)

print("inputs_arr.shape = ", inputs_arr.shape)
print("mu_arr.shape = ", mu_arr.shape)
print("cov_arr.shape = ", cov_arr.shape)

## graph
plt.figure()
h = 5
w = 10

def accToRP(acc):
    r = math.atan2(acc[1], acc[2])
    p = math.atan2(-acc[0], math.sqrt(acc[1]*acc[1] + acc[2]*acc[2]))
    return r, p

## access each sample
list_r = []
list_p = []
list_r_selected = []
list_p_selected = []
th_outlier_deg = 10.0
th_outlier_sigma = 0.005
for i in range(labels_arr.shape[0]):
    print("-----", i, "-----")
    print("label: ", labels_arr[i])
    print("mu: ", mu_arr[i])
    print("Cov: ", cov_arr[i])

    l_r, l_p = accToRP(labels_arr[i])
    o_r, o_p = accToRP(mu_arr[i])
    e_r = math.atan2(math.sin(l_r - o_r), math.cos(l_r - o_r))
    e_p = math.atan2(math.sin(l_p - o_p), math.cos(l_p - o_p))
    print("l_r[deg]: ", l_r/math.pi*180.0, " l_p[deg]: ", l_p/math.pi*180.0)
    print("o_r[deg]: ", o_r/math.pi*180.0, " o_p[deg]: ", o_p/math.pi*180.0)
    print("e_r[deg]: ", e_r/math.pi*180.0, " e_p[deg]: ", e_p/math.pi*180.0)

    if (abs(e_r/math.pi*180.0) < th_outlier_deg) and (abs(e_p/math.pi*180.0) < th_outlier_deg):
        is_big_error = False
    else:
        is_big_error = True
        print("BIG ERROR")

    list_r.append(abs(e_r))
    list_p.append(abs(e_p))

    mul_sigma = math.sqrt(cov_arr[i, 0, 0]) * math.sqrt(cov_arr[i, 1, 1]) * math.sqrt(cov_arr[i, 2, 2])
    print("mul_sigma = ", mul_sigma)
    if mul_sigma < th_outlier_sigma:
        list_r_selected.append(abs(e_r))
        list_p_selected.append(abs(e_p))
    else:
        print("BIG SIGMA")
    
    ## graph
    if i < h*w:
        plt.subplot(h, w, i+1)
        plt.tick_params(labelbottom=False, labelleft=False, bottom=False, left=False)
        plt.imshow(np.clip(inputs_arr[i].transpose((1, 2, 0)), 0, 1))
        if not is_big_error:
            plt.title(str(i) + "*")
        else:
            plt.title(i)

list_r = np.array(list_r)
list_p = np.array(list_p)
print("---ave---\n e_r[deg]: ", list_r.mean()/math.pi*180.0, " e_p[deg]: ",  list_p.mean()/math.pi*180.0)
list_r_selected = np.array(list_r_selected)
list_p_selected = np.array(list_p_selected)
print("---selected ave---\n e_r[deg]: ", list_r_selected.mean()/math.pi*180.0, " e_p[deg]: ",  list_p_selected.mean()/math.pi*180.0)
print("list_r_selected.size = ", list_r_selected.size)

plt.show()
