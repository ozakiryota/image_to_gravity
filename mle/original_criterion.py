import numpy as np
import math

import torch

def getCov(x):
    sigma = x[:, 3:6].clone()
    corr = x[:, 6:9].clone()
    sxx = sigma[:, 0] * sigma[:, 0]
    syy = sigma[:, 1] * sigma[:, 1]
    szz = sigma[:, 2] * sigma[:, 2]
    sxy = corr[:, 0] * sigma[:, 0] * sigma[:, 1]
    syz = corr[:, 1] * sigma[:, 1] * sigma[:, 2]
    szx = corr[:, 2] * sigma[:, 2] * sigma[:, 0]

    cov = torch.empty(sigma.size(0), 3, 3)
    cov[:, 0, 0] = sxx
    cov[:, 0, 1] = sxy
    cov[:, 0, 2] = szx
    cov[:, 1, 0] = sxy
    cov[:, 1, 1] = syy
    cov[:, 1, 2] = szx
    cov[:, 2, 0] = szx
    cov[:, 2, 1] = syz
    cov[:, 2, 2] = szz
    return cov

def originalCriterion(outputs, labels):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    k = labels.size(1)
    g = outputs[:, :3].clone()
    cov = getCov(outputs)
    cov_inv = torch.inverse(cov)
    diff = labels - g
    diff = diff.unsqueeze_(1)
    diff_trans = torch.transpose(diff, 1, 2)
    # print("k = ", k)
    # print("cov.size() = ", cov.size())
    # print("cov = ", cov)
    # print("cov_inv.size() = ", cov_inv.size())
    # print("cov_inv = ", cov_inv)
    # print("diff.size() = ", diff.size())
    # print("diff = ", diff)
    # print("diff_trans.size() = ", diff_trans.size())
    # print("diff_trans = ", diff_trans)
    print("cov[0] = ", cov[0])
    print("cov_inv[0] = ", cov_inv[0])

    cov_inv = cov_inv.to(device)
    numerator = torch.exp(-1 / 2 * torch.bmm(torch.bmm(diff, cov_inv), diff_trans))
    numerator = numerator.clone().squeeze_()
    denominator = torch.sqrt(((2*math.pi)**k) * torch.det(cov)) #det() works in torch>1.2.0
    denominator = denominator.to(device)
    # print("denominator.size() = ", denominator.size())
    # print("denominator = ", denominator)
    # print("numerator.size() = ", numerator.size())
    # print("numerator = ", numerator)
    loss = numerator / denominator
    epsiron = 1e-20
    loss = -torch.log(torch.clamp(loss, min=epsiron))
    loss = torch.sum(loss) / loss.size(0)

    # loss = torch.mean((g - labels)**2)
    return loss

##### test #####
# outputs = np.array([
#     [1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 0.5, 0.5, 0.5],
#     [1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 0.5, 0.5, 0.5]
# ]).astype(np.float32)
# outputs = torch.from_numpy(outputs)
# print("outputs.size() = ", outputs.size())
# print("outputs = ", outputs)
# labels = np.array([
#     [2.1, 3.2, 4.3],
#     [2.1, 3.2, 4.3]
# ]).astype(np.float32)
# labels = torch.from_numpy(labels)
# print("labels.size() = ", labels.size())
# print("labels = ", labels)
#
# loss = originalCriterion(outputs, labels)
# print("loss.size() = ", loss.size())
# print("loss = ", loss)