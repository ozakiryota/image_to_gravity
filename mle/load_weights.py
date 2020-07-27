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
mean_element = 0.5
std_element = 0.5
mean = ([mean_element, mean_element, mean_element])
std = ([std_element, std_element, std_element])

## list
val_rootpath = "../dataset/val"
csv_name = "imu_camera.csv"
val_list = make_datapath_list.make_datapath_list(val_rootpath, csv_name)

## transform
transform = data_transform.data_transform(size, mean, std)

## dataset
val_dataset = original_dataset.OriginalDataset(
    data_list=val_list,
    transform=data_transform.data_transform(size, mean, std),
    phase="val"
)

## dataloader
batch_size = 10
val_dataloader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

## mini-batch prediction
list_img_path = [data[3] for data in val_list]
inputs_arr = np.empty(0)
labels_arr = np.empty([0, 3])
mu_arr = np.empty([0, 3])
cov_arr = np.empty([0, 3, 3])
for inputs, labels in val_dataloader:
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

## class
class Sample:
    def __init__(self, index, img_path, inputs, label, mu, cov):
        self.index = index  #int
        self.img_path = img_path    #str
        self.inputs = inputs    #ndarray
        self.label = label  #array
        self.mu = mu    #array
        self.cov = cov  #ndarray
        self.label_r, self.label_p = self.accToRP(label)    #float
        self.output_r, self.output_p = self.accToRP(mu) #float
        self.error_r, self.error_p = self.computeErrorRP()  #float
        self.mul_sigma = self.computeMulSigma() #float

    def accToRP(self, acc):
        r = math.atan2(acc[1], acc[2])
        p = math.atan2(-acc[0], math.sqrt(acc[1]*acc[1] + acc[2]*acc[2]))
        return r, p

    def computeErrorRP(self):
        e_r = math.atan2(math.sin(self.label_r - self.output_r), math.cos(self.label_r - self.output_r))
        e_p = math.atan2(math.sin(self.label_p - self.output_p), math.cos(self.label_p - self.output_p))
        return e_r, e_p

    def computeMulSigma(self):
        mul_sigma = math.sqrt(self.cov[0, 0]) * math.sqrt(self.cov[1, 1]) * math.sqrt(self.cov[2, 2])
        return mul_sigma

    def PrintData(self):
        print("-----", self.index, "-----")
        print("img_path: ", self.img_path)
        # print("inputs: ", self.inputs)
        print("inputs: ", self.inputs.shape)
        print("label: ", self.label)
        print("mu: ", self.mu)
        print("Cov: ", self.cov)
        print("l_r[deg]: ", self.label_r/math.pi*180.0, ", l_p[deg]: ", self.label_p/math.pi*180.0)
        print("o_r[deg]: ", self.output_r/math.pi*180.0, ", o_p[deg]: ", self.output_p/math.pi*180.0)
        print("e_r[deg]: ", self.error_r/math.pi*180.0, ", e_p[deg]: ", self.error_p/math.pi*180.0)
        print("mul_sigma: ", self.mul_sigma)

## access each sample
list_sample = []
list_er = []
list_ep = []
list_er_selected = []
list_ep_selected = []
list_mul_sigma = []
for i in range(len(list_img_path)):
    ## input
    sample = Sample(
        i,
        list_img_path[i],
        inputs_arr[i],
        labels_arr[i],
        mu_arr[i],
        cov_arr[i]
    )
    list_sample.append(sample)

    ## append
    list_er.append(abs(sample.error_r))
    list_ep.append(abs(sample.error_p))
    list_mul_sigma.append(sample.mul_sigma)

    if sample.mul_sigma < th_outlier_sigma:
        list_er_selected.append(abs(sample.error_r))
        list_ep_selected.append(abs(sample.error_p))

## sort
# sorted_indicies = np.argsort(list_mul_sigma)    #small->large
sorted_indicies = np.argsort(list_mul_sigma)[::-1]  #large->small
list_sample = [list_sample[index] for index in sorted_indicies]

## print & imshow
plt.figure()
i = 0
h = 5
w = 10

th_outlier_deg = 10.0
th_outlier_sigma = 0.0001
for sample in list_sample:
    ## print
    sample.PrintData()
    
    ## judge
    if (abs(sample.error_r/math.pi*180.0) < th_outlier_deg) and (abs(sample.error_p/math.pi*180.0) < th_outlier_deg):
        is_big_error = False
    else:
        is_big_error = True
        print("BIG ERROR")

    if sample.mul_sigma > th_outlier_sigma:
        print("BIG SIGMA")

    ## picture
    if i < h*w:
        plt.subplot(h, w, i+1)
        plt.tick_params(labelbottom=False, labelleft=False, bottom=False, left=False)
        plt.imshow(np.clip(sample.inputs.transpose((1, 2, 0)), 0, 1))
        if not is_big_error:
            plt.title(str(sample.index) + "*")
        else:
            plt.title(sample.index)
        i = i + 1

## error
list_er = np.array(list_er)
list_ep = np.array(list_ep)
print("---ave---\n e_r[deg]: ", list_er.mean()/math.pi*180.0, " e_p[deg]: ",  list_ep.mean()/math.pi*180.0)
## selected error
list_er_selected = np.array(list_er_selected)
list_ep_selected = np.array(list_ep_selected)
print("---selected ave---\n e_r[deg]: ", list_er_selected.mean()/math.pi*180.0, " e_p[deg]: ",  list_ep_selected.mean()/math.pi*180.0)
print("list_er_selected.size = ", list_er_selected.size)
## mul_sigma
list_mul_sigma = np.array(list_mul_sigma)
print("list_mul_sigma.mean() = ", list_mul_sigma.mean())

plt.show()
