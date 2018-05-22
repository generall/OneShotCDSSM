"""
This script should perform training of the CDSSM model
"""
import argparse

import nltk
import torch
from torch.autograd import Variable
import torch.optim as optim
from torchlite.torch.learner import Learner
from torchlite.torch.learner.cores import ClassifierCore
from torchlite.torch.metrics import Metric
from torchlite.torch.train_callbacks import TensorboardVisualizerCallback
from tqdm import tqdm

from config import TB_DIR
from model.siames import Siames
from utils.loader import MentionsLoader


def tokenizer(text, alpha_only=True):  # create a tokenizer function
    return [tok for tok in nltk.word_tokenize(text) if (not alpha_only or tok.isalpha())]


def loss_foo(distances, target, alpha=0.4):
    """

    :param alpha: minimal distance
    :param distances: 1d Tensor shape: (num_examples, )
    :param target: 1d Tensor shape: (num_examples, )
    """

    diff = torch.abs(distances - target)
    return torch.sum(diff[diff > alpha])


class DistAccuracy(Metric):

    def __init__(self, alpha=0.4):
        self.alpha = alpha

    @property
    def get_name(self):
        return "dist_accuracy"

    def __call__(self, y_pred, y_true):
        diff = torch.abs(y_pred - y_true)
        positive = torch.sum((diff > self.alpha).int()).data.item()
        total = y_true.shape[0]
        return positive / total


parser = argparse.ArgumentParser(description='Train One Shot CDSSM')

parser.add_argument('--train-data', dest='train_data', help='path to train data')
parser.add_argument('--valid-data', dest='valid_data', help='path to valid data')

parser.add_argument('--epoch', type=int, default=10)
parser.add_argument('--read-size', type=int, default=500)
parser.add_argument('--batch-size', type=int, default=10)
parser.add_argument('--dict-size', type=int, default=20000)
parser.add_argument('--cuda', type=bool, default=False)

args = parser.parse_args()


train_loader = MentionsLoader(
    args.train_data,
    read_size=args.read_size,
    batch_size=args.batch_size,
    dict_size=args.dict_size,
    tokenizer=tokenizer
)

test_loader = MentionsLoader(
    args.valid_data,
    read_size=args.read_size,
    batch_size=args.batch_size,
    dict_size=args.dict_size,
    tokenizer=tokenizer
)

loss = loss_foo
model = Siames()

optimizer = optim.RMSprop(model.parameters(), lr=1e-3)
metrics = [DistAccuracy()]
callbacks = [TensorboardVisualizerCallback(TB_DIR)]

learner = Learner(ClassifierCore(model, optimizer, loss), use_cuda=args.cuda)
learner.train(args.epoch, metrics, train_loader, test_loader, callbacks=callbacks)

