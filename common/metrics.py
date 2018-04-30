from __future__ import print_function

import numpy as np
import torch
import torch.utils.data
from numpy.lib.stride_tricks import as_strided
from scipy.stats import entropy
from torch import nn
from torch.autograd import Variable
from torch.nn import functional as F
from torchvision.models.inception import inception_v3


def inception_score(model, N=1000, cuda=True, batch_size=32, resize=False, splits=1):
    """
    adapted from: https://github.com/sbarratt/inception-score-pytorch/blob/master/inception_score.py
    Computes the inception score of images generated by model
    model -- Pretrained Generator
    N -- Number of samples to test
    cuda -- whether or not to run on GPU
    batch_size -- batch size for feeding into Inception v3
    splits -- number of splits
    """

    assert batch_size > 0
    assert N > batch_size

    # Set up dtype
    if cuda:
        dtype = torch.cuda.FloatTensor
    else:
        if torch.cuda.is_available():
            print("WARNING: You have a CUDA device, so you should probably set cuda=True")
        dtype = torch.FloatTensor

    # Load inception model
    inception_model = inception_v3(pretrained=True, transform_input=False).type(dtype)
    inception_model.eval();
    up = nn.Upsample(size=(299, 299), mode='bilinear').type(dtype)

    def get_pred(N_s):

        z_ = torch.randn(N_s, 100).view(-1, 100, 1, 1)

        if cuda:
            z_ = z_.cuda()

        z_ = Variable(z_)

        x = model.forward(z_)

        if resize:
            x = up(x)
        x = inception_model(x)
        return F.softmax(x, dim=1).data.cpu().numpy()

    indexes = strided_app(np.arange(N), batch_size, batch_size)

    N = indexes[-1][-1] + 1

    # Get predictions
    preds = np.zeros((N, 1000))

    for i, idx in enumerate(indexes, 0):
        batch_size_i = idx.shape[0]

        preds[i * batch_size:i * batch_size + batch_size_i] = get_pred(batch_size_i)

    # Now compute the mean kl-div
    split_scores = []

    for k in range(splits):
        part = preds[k * (N // splits): (k + 1) * (N // splits), :]
        py = np.mean(part, axis=0)
        scores = []
        for i in range(part.shape[0]):
            pyx = part[i, :]
            scores.append(entropy(pyx, py))
        split_scores.append(np.exp(np.mean(scores)))

    return np.mean(split_scores), np.std(split_scores)


def strided_app(a, L, S):
    nrows = ((len(a) - L) // S) + 1
    n = a.strides[0]
    return as_strided(a, shape=(nrows, L), strides=(S * n, n))
