from __future__ import print_function

import argparse

import os
import sys
import glob

sys.path.insert(0, os.path.realpath(__file__ + ('/..' * 3)))
print(f'Running from package root directory {sys.path[0]}')

import matplotlib.pyplot as plt
import torch.utils.data

import pandas as pd
import seaborn as sns

from common.generators import Generator_mnist
from common.utils import *
from common.models_fid import *
from common.metrics import compute_fid

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Testing GANs under max hyper volume training')
	parser.add_argument('--cp-folder', type=str, default=None, metavar='Path', help='Checkpoint/model path')
	parser.add_argument('--ntests', type=int, default=30, metavar='N', help='number of samples to generate (default: 4)')
	parser.add_argument('--nsamples', type=int, default=10000, metavar='Path', help='number of samples per replication')
	parser.add_argument('--no-plots', action='store_true', default=False, help='Disables plot of train/test losses')
	parser.add_argument('--fid-model-path', type=str, default=None, metavar='Path', help='Path to fid model')
	parser.add_argument('--data-stat-path', type=str, default='../test_data_statistics.p', metavar='Path', help='Path to file containing test data statistics')
	parser.add_argument('--model-mnist', choices=['cnn', 'mlp'], default='cnn', help='model for FID computation on Cifar. (Default=cnn)')
	parser.add_argument('--batch-size', type=int, default=512, metavar='Path', help='batch size')
	parser.add_argument('--no-cuda', action='store_true', default=False, help='Disables GPU use')
	args = parser.parse_args()
	args.cuda = True if not args.no_cuda and torch.cuda.is_available() else False

	if args.model_mnist == 'cnn':
		fid_model = cnn().eval()

	elif args.model_mnist == 'mlp':
		fid_model = mlp().eval()

	mod_state = torch.load(args.fid_model_path, map_location = lambda storage, loc: storage)
	fid_model.load_state_dict(mod_state['model_state'])

	if args.cuda:
		fid_model = fid_model.cuda()

	mod_state = torch.load(args.fid_model_path, map_location = lambda storage, loc: storage)
	fid_model.load_state_dict(mod_state['model_state'])

	models_dict = {'hyper': 'HV', 'vanilla': 'AVG', 'gman': 'GMAN', 'mgd': 'MGD'}

	fid_dict = {}

	pfile = open(args.data_stat_path, 'rb')
	statistics = pickle.load(pfile)
	pfile.close()

	m, C = statistics['m'], statistics['C']

	if args.cp_folder is None:
		raise ValueError('There is no checkpoint/model path. Use arg --cp-path to indicate the path!')

	files_list = glob.glob(args.cp_folder + 'G_*.pt')
	files_list.sort()

	for file_id in files_list:

		file_name = file_id.split('/')[-1].split('_')[1]

		print(file_name)		

		key = models_dict[file_name]

		generator = Generator_mnist().eval()
		gen_state = torch.load(file_id, map_location = lambda storage, loc: storage)
		generator.load_state_dict(gen_state['model_state'])

		if args.cuda:
			generator = generator.cuda()
		
		fid = []

		for i in range(args.ntests):
			fid.append(compute_fid(generator, fid_model, args.batch_size, args.nsamples, m, C, args.cuda, inception = False, mnist = True))

		fid_dict[key] = fid

	
	# Random generator
	random_generator = Generator_mnist().eval()
	
	if args.cuda:
		random_generator = random_generator.cuda()
	
	fid_random = []
	for i in range(args.ntests):
			fid_random.append(compute_fid(random_generator, fid_model, args.batch_size, args.nsamples, m, C, args.cuda, inception = False, mnist = True))
	

	df = pd.DataFrame(fid_dict)
	df.head()
	order_plot = ['AVG', 'GMAN', 'HV', 'MGD']
	box = sns.boxplot(data = df, palette = "Set3", width = 0.2, linewidth = 1.0, showfliers = False, order = order_plot)
	box.set_xlabel('Model', fontsize = 12)
	box.set_ylabel('FID', fontsize = 12)	
	box.set_yscale('log')
	plt.axhline(np.mean(fid_random), color='k', linestyle='dashed', linewidth=1)
	plt.savefig('FID_best_models_mnist.pdf')
	plt.show()