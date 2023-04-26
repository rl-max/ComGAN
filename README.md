# ComGAN PyTorch Implementation. 
This is a implementation of our work ComGAN[1] built upon StudioGAN framework[2]. Our paper is avaiable at [here](https://arxiv.org/abs/2304.12098).


**To get started**, please read the StudioGAN documentation [here](https://github.com/POSTECH-CVLab/PyTorch-StudioGAN) and finish the basic set up. \
After all, you can run, for example, SComGAN by executing the following command. 

```
!python src/main.py -t -hdf5 -l -metrics is fid prdc -ref test --num_workers 2 --save_freq 2000 --print_freq 100 \
    -cfg src/configs/JointGAN/CIFAR10/joint-dcgan.yaml \
    -data ./cifar10 -save . --post_resizer friendly --eval_backbone InceptionV3_tf
```
For Tiny-ImageNet, please run the following command in the directory of `PyTorch-StudioGAN` in order to download the dataset. 
```
!wget http://cs231n.stanford.edu/tiny-imagenet-200.zip
!wget https://gist.github.com/rl-max/58825fd2df2ca82fb4693032b3077ea5/raw -O process_tiny_imagenet.sh
!bash process_tiny_imagenet.sh
!mv tiny-imagenet-200/val tiny-imagenet-200/valid
!rm tiny-imagenet-200.zip
```
Then, excute this. 
```
!python src/main.py -t -hdf5 -l -metrics is fid prdc -ref valid --num_workers 2 --save_freq 2000 --print_freq 100 \
    -cfg src/configs/JointGAN/Tiny_ImageNet/joint-wgan-gp.yaml \
    -data ./tiny-imagenet-200 -save . --post_resizer friendly --eval_backbone InceptionV3_tf
```

### Configurations

To run other losses, corresponding files can be found under `src/configs/JointGAN/CIFAR10/`(e.g. Use "joint-lsgan.yaml" for least square loss) and similarly for Tiny-ImageNet. For the arguments of the above commmand such as `-metric`, `-t`, and `-eval_backbone`, please refer to the StudioGAN documentation. 

In each of yaml files, you will have the following options that are components of ComGAN.

- **MODEL.jointgan_arch**: This determines which architecture to use for ComGAN. Options are provided among `[rgan, ragan, concat]`. 
- **LOSS.jointgan_object**: This determines whether to use real data, fake data, or same sample for comparative sample[1], each of which is denoted by `[r, f, s]`.
- **LOSS.apply_reg**: This determines the equality regularization[1] to be applied. The available options are `[N/A, l1, l1_mean, l2, l2_mean, logistic, logistic_mean, hf]`. We recommend using "l2_mean" for RGAN/RaGAN and "l2" for concat architecture. 

### References 
[1] Haeone Lee. ComGAN: Toward GANs Exploiting Multiple Samples. arXiv preprint arXiv:2304.12098. 2023 April 24. \
[2] Kang M, Shin J, Park J. Studiogan: A taxonomy and benchmark of gans for image synthesis. arXiv preprint arXiv:2206.09479. 2022 Jun 19.
