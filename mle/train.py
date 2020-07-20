from tqdm import tqdm
import matplotlib.pyplot as plt
import time

import torch
from torchvision import models
import torch.nn as nn
import torch.optim as optim
from tensorboardX import SummaryWriter

import make_datapath_list
import data_transform
import original_dataset
import original_network
import original_criterion

def train_model(net, dataloaders_dict, optimizer, num_epochs, str_hyperparameter):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print("device = ", device)

    net.to(device)

    # loss record
    writer = SummaryWriter(logdir="../runs")
    record_loss_train = []
    record_loss_val = []

    for epoch in range(num_epochs):
        print("----------")
        print("Epoch {}/{}".format(epoch+1, num_epochs))

        for phase in ["train", "val"]:
            if phase == "train":
                net.train()
            else:
                net.eval()

            epoch_loss = 0.0

            if (epoch == 0) and (phase=="train"):
                continue

            for inputs, labels in tqdm(dataloaders_dict[phase]):
                inputs = inputs.to(device)
                labels = labels.to(device)

                ## initialize optimizer
                optimizer.zero_grad()   #reset grad to zero (after .step())

                with torch.set_grad_enabled(phase == "train"):  #compute grad only in "train"
                    ## forward
                    outputs = net(inputs)
                    loss = original_criterion.originalCriterion(outputs, labels, device)

                    ## backward
                    if phase == "train":
                        torch.autograd.set_detect_anomaly(True)
                        loss.backward()     #accumulate gradient to each Tensor
                        optimizer.step()    #update param depending on current .grad

                    epoch_loss += loss.item() * inputs.size(0)

            epoch_loss = epoch_loss / len(dataloaders_dict[phase].dataset)
            print("{} Loss: {:.4f}".format(phase, epoch_loss))

            if phase == "train":
                record_loss_train.append(epoch_loss)
                writer.add_scalar("Loss/train", epoch_loss, epoch)
            else:
                record_loss_val.append(epoch_loss)
                writer.add_scalar("Loss/val", epoch_loss, epoch)
    ## save param
    save_path = "../weights/mle.pth"
    torch.save(net.state_dict(), save_path)
    print("Parameter file is saved as ", save_path)

    ## graph
    graph = plt.figure()
    plt.plot(range(len(record_loss_train)), record_loss_train, label="Train")
    plt.plot(range(len(record_loss_val)), record_loss_val, label="Validation")
    plt.legend()
    plt.xlabel("Epoch")
    plt.ylabel("Error")
    plt.title(str_hyperparameter)
    graph.savefig("../graph/mle.jpg")
    plt.show()

    writer.close()

##### execution #####
## hyperparameter
mean_element = 0.25
std_element = 0.5
lr0 = 1e-5
lr1 = 1e-4
batch_size = 50
num_epochs = 100
str_hyperparameter = "mle_"\
    + "mean" + str(mean_element) \
    + "std" + str(std_element) \
    + "lr" + str(lr0) \
    + "lr" + str(lr1) \
    + "batch" + str(batch_size) \
    + "epoch" + str(num_epochs)
print("str_hyperparameter = ", str_hyperparameter)

## random
keep_reproducibility = False
if keep_reproducibility:
    torch.manual_seed(1234)
    np.random.seed(1234)
    random.seed(1234)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

## list
train_rootpath = "../dataset/train"
val_rootpath = "../dataset/val"
csv_name = "imu_camera.csv"
train_list = make_datapath_list.make_datapath_list(train_rootpath, csv_name)
val_list = make_datapath_list.make_datapath_list(val_rootpath, csv_name)

## trans param
size = 224  #VGG16
mean = ([mean_element, mean_element, mean_element])
std = ([std_element, std_element, std_element])

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
print("batch_size = ", batch_size)
train_dataloader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
val_dataloader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
dataloaders_dict = {"train": train_dataloader, "val": val_dataloader}
print("train data: ", len(dataloaders_dict["train"].dataset))
print("val data: ", len(dataloaders_dict["val"].dataset))

## network
net = original_network.OriginalNet()
print(net)
# vgg = models.vgg16(pretrained=True)
# print(vgg)


## param
list_cnn_param_value, list_fc_param_value = net.getParamValueList()

## optimizer
# optimizer = optim.SGD([
#     {"params": list_cnn_param_value, "lr": lr0},
#     {"params": list_fc_param_value, "lr": lr1}
# ], momentum=0.9)
optimizer = optim.Adam([
    {"params": list_cnn_param_value, "lr": lr0},
    {"params": list_fc_param_value, "lr": lr1}
])
print(optimizer)

## execution
start_clock = time.time()
train_model(net, dataloaders_dict, optimizer, num_epochs, str_hyperparameter)
## training time
mins = (time.time() - start_clock) // 60
secs = (time.time() - start_clock) % 60
print ("training_time: ", mins, " [min] ", secs, " [sec]")
