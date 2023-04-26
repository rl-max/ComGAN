# ComGAN PyTorch Implementation. 
This is a implementation of our work ComGAN[1] built upon StudioGAN framework[2]. Our paper is avaiable at [here](https://arxiv.org/abs/2304.12098).


**To get started**, please read the StudioGAN documentation [here](https://github.com/POSTECH-CVLab/PyTorch-StudioGAN) and finish the basic set up. \
After all, you can run, for example, SComGAN by executing the command of 

```
!python src/main.py -t -hdf5 -l -metrics is fid prdc -ref valid --num_workers 2 --save_freq 2000 --print_freq 100 \
                    -cfg src/configs/JointGAN/CIFAR10/joint-dcgan.yaml \
                    -data ./tiny-imagenet-200 -save . --post_resizer friendly --eval_backbone InceptionV3_tf
```
