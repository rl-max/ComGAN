# PyTorch StudioGAN: https://github.com/POSTECH-CVLab/PyTorch-StudioGAN
# The MIT License (MIT)
# See license file or visit https://github.com/POSTECH-CVLab/PyTorch-StudioGAN for details

# models/resnet.py

import torch
import torch.nn as nn
import torch.nn.functional as F

import utils.ops as ops
import utils.misc as misc


from ..resnet import Generator, DiscBlock, DiscOptBlock

class Discriminator(nn.Module):
    def __init__(self, img_size, d_conv_dim, apply_d_sn, apply_attn, attn_d_loc, d_cond_mtd, aux_cls_type, d_embed_dim, normalize_d_embed,
                 num_classes, d_init, d_depth, mixed_precision, MODULES, MODEL):
        super(Discriminator, self).__init__()
        
        input_image_channels = 3 * 2

        d_in_dims_collection = {
            "32": [input_image_channels] + [d_conv_dim * 2, d_conv_dim * 2, d_conv_dim * 2],
            "64": [input_image_channels] + [d_conv_dim, d_conv_dim * 2, d_conv_dim * 4, d_conv_dim * 8],
            "128": [input_image_channels] + [d_conv_dim, d_conv_dim * 2, d_conv_dim * 4, d_conv_dim * 8, d_conv_dim * 16],
            "256": [input_image_channels] + [d_conv_dim, d_conv_dim * 2, d_conv_dim * 4, d_conv_dim * 8, d_conv_dim * 8, d_conv_dim * 16],
            "512": [input_image_channels] + [d_conv_dim, d_conv_dim, d_conv_dim * 2, d_conv_dim * 4, d_conv_dim * 8, d_conv_dim * 8, d_conv_dim * 16]
        }

        d_out_dims_collection = {
            "32": [d_conv_dim * 2, d_conv_dim * 2, d_conv_dim * 2, d_conv_dim * 2],
            "64": [d_conv_dim, d_conv_dim * 2, d_conv_dim * 4, d_conv_dim * 8, d_conv_dim * 16],
            "128": [d_conv_dim, d_conv_dim * 2, d_conv_dim * 4, d_conv_dim * 8, d_conv_dim * 16, d_conv_dim * 16],
            "256": [d_conv_dim, d_conv_dim * 2, d_conv_dim * 4, d_conv_dim * 8, d_conv_dim * 8, d_conv_dim * 16, d_conv_dim * 16],
            "512":
            [d_conv_dim, d_conv_dim, d_conv_dim * 2, d_conv_dim * 4, d_conv_dim * 8, d_conv_dim * 8, d_conv_dim * 16, d_conv_dim * 16]
        }

        d_down = {
            "32": [True, True, False, False],
            "64": [True, True, True, True, False],
            "128": [True, True, True, True, True, False],
            "256": [True, True, True, True, True, True, False],
            "512": [True, True, True, True, True, True, True, False]
        }

        self.d_cond_mtd = d_cond_mtd
        self.aux_cls_type = aux_cls_type
        self.normalize_d_embed = normalize_d_embed
        self.num_classes = num_classes
        self.mixed_precision = mixed_precision
        self.in_dims = d_in_dims_collection[str(img_size)]
        self.out_dims = d_out_dims_collection[str(img_size)]
        self.MODEL = MODEL
        down = d_down[str(img_size)]

        self.blocks = []
        for index in range(len(self.in_dims)):
            if index == 0:
                self.blocks += [[
                    DiscOptBlock(in_channels=self.in_dims[index], out_channels=self.out_dims[index], apply_d_sn=apply_d_sn, MODULES=MODULES)
                ]]
            else:
                self.blocks += [[
                    DiscBlock(in_channels=self.in_dims[index],
                              out_channels=self.out_dims[index],
                              apply_d_sn=apply_d_sn,
                              MODULES=MODULES,
                              downsample=down[index])
                ]]

            if index + 1 in attn_d_loc and apply_attn:
                self.blocks += [[ops.SelfAttention(self.out_dims[index], is_generator=False, MODULES=MODULES)]]

        self.blocks = nn.ModuleList([nn.ModuleList(block) for block in self.blocks])

        self.activation = MODULES.d_act_fn

        # linear layer for adversarial training
        if self.d_cond_mtd == "MH":
            self.linear1 = MODULES.d_linear(in_features=self.out_dims[-1], out_features=1 + num_classes, bias=True)
        elif self.d_cond_mtd == "MD":
            self.linear1 = MODULES.d_linear(in_features=self.out_dims[-1], out_features=num_classes, bias=True)
        else:
            self.linear1 = MODULES.d_linear(in_features=self.out_dims[-1], out_features=1, bias=True)

        # double num_classes for Auxiliary Discriminative Classifier
        if self.aux_cls_type == "ADC":
            num_classes = num_classes * 2

        # linear and embedding layers for discriminator conditioning
        if self.d_cond_mtd == "AC":
            self.linear2 = MODULES.d_linear(in_features=self.out_dims[-1], out_features=num_classes, bias=False)
        elif self.d_cond_mtd == "PD":
            self.embedding = MODULES.d_embedding(num_classes, self.out_dims[-1])
        elif self.d_cond_mtd in ["2C", "D2DCE"]:
            self.linear2 = MODULES.d_linear(in_features=self.out_dims[-1], out_features=d_embed_dim, bias=True)
            self.embedding = MODULES.d_embedding(num_classes, d_embed_dim)
        else:
            pass

        # linear and embedding layers for evolved classifier-based GAN
        if self.aux_cls_type == "TAC":
            if self.d_cond_mtd == "AC":
                self.linear_mi = MODULES.d_linear(in_features=self.out_dims[-1], out_features=num_classes, bias=False)
            elif self.d_cond_mtd in ["2C", "D2DCE"]:
                self.linear_mi = MODULES.d_linear(in_features=self.out_dims[-1], out_features=d_embed_dim, bias=True)
                self.embedding_mi = MODULES.d_embedding(num_classes, d_embed_dim)
            else:
                raise NotImplementedError

        # Q head network for infoGAN
        if self.MODEL.info_type in ["discrete", "both"]:
            out_features = self.MODEL.info_num_discrete_c*self.MODEL.info_dim_discrete_c
            self.info_discrete_linear = MODULES.d_linear(in_features=self.out_dims[-1], out_features=out_features, bias=False)
        if self.MODEL.info_type in ["continuous", "both"]:
            out_features = self.MODEL.info_num_conti_c
            self.info_conti_mu_linear = MODULES.d_linear(in_features=self.out_dims[-1], out_features=out_features, bias=False)
            self.info_conti_var_linear = MODULES.d_linear(in_features=self.out_dims[-1], out_features=out_features, bias=False)

        if d_init:
            ops.init_weights(self.modules, d_init)

    def forward(self, x, label=None, eval=False, adc_fake=False):
        with torch.cuda.amp.autocast() if self.mixed_precision and not eval else misc.dummy_context_mgr() as mp:
            embed, proxy, cls_output = None, None, None
            mi_embed, mi_proxy, mi_cls_output = None, None, None
            info_discrete_c_logits, info_conti_mu, info_conti_var = None, None, None
            #input x is always a concatentation of two datas
            h = x
            for index, blocklist in enumerate(self.blocks):
                for block in blocklist:
                    h = block(h)
            bottom_h, bottom_w = h.shape[2], h.shape[3]
            h = self.activation(h)
            h = torch.sum(h, dim=[2, 3])

            # adversarial training
            adv_output = torch.squeeze(self.linear1(h))

            # make class labels odd (for fake) or even (for real) for ADC
            if self.aux_cls_type == "ADC":
                if adc_fake:
                    label = label*2 + 1
                else:
                    label = label*2

            # forward pass through InfoGAN Q head
            if self.MODEL.info_type in ["discrete", "both"]:
                info_discrete_c_logits = self.info_discrete_linear(h/(bottom_h*bottom_w))
            if self.MODEL.info_type in ["continuous", "both"]:
                info_conti_mu = self.info_conti_mu_linear(h/(bottom_h*bottom_w))
                info_conti_var = torch.exp(self.info_conti_var_linear(h/(bottom_h*bottom_w)))

            # class conditioning
            if self.d_cond_mtd == "AC":
                if self.normalize_d_embed:
                    for W in self.linear2.parameters():
                        W = F.normalize(W, dim=1)
                    h = F.normalize(h, dim=1)
                cls_output = self.linear2(h)
            elif self.d_cond_mtd == "PD":
                adv_output = adv_output + torch.sum(torch.mul(self.embedding(label), h), 1)
            elif self.d_cond_mtd in ["2C", "D2DCE"]:
                embed = self.linear2(h)
                proxy = self.embedding(label)
                if self.normalize_d_embed:
                    embed = F.normalize(embed, dim=1)
                    proxy = F.normalize(proxy, dim=1)
            elif self.d_cond_mtd == "MD":
                idx = torch.LongTensor(range(label.size(0))).to(label.device)
                adv_output = adv_output[idx, label]
            elif self.d_cond_mtd in ["W/O", "MH"]:
                pass
            else:
                raise NotImplementedError

            # extra conditioning for TACGAN and ADCGAN
            if self.aux_cls_type == "TAC":
                if self.d_cond_mtd == "AC":
                    if self.normalize_d_embed:
                        for W in self.linear_mi.parameters():
                            W = F.normalize(W, dim=1)
                    mi_cls_output = self.linear_mi(h)
                elif self.d_cond_mtd in ["2C", "D2DCE"]:
                    mi_embed = self.linear_mi(h)
                    mi_proxy = self.embedding_mi(label)
                    if self.normalize_d_embed:
                        mi_embed = F.normalize(mi_embed, dim=1)
                        mi_proxy = F.normalize(mi_proxy, dim=1)
        return {
            "h": h,
            "adv_output": adv_output,
            "embed": embed,
            "proxy": proxy,
            "cls_output": cls_output,
            "label": label,
            "mi_embed": mi_embed,
            "mi_proxy": mi_proxy,
            "mi_cls_output": mi_cls_output,
            "info_discrete_c_logits": info_discrete_c_logits,
            "info_conti_mu": info_conti_mu,
            "info_conti_var": info_conti_var
        }
