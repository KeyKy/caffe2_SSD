import numpy as np
import os, time, argparse, sys

from caffe2.proto import caffe2_pb2
from caffe2.python import workspace, core
import caffe2.python._import_c_extension as C

def parse_args():
    parser = argparse.ArgumentParser(description='benchmark net in caffe2')
    parser.add_argument('--init_net', help='init net', type=str, required=True)
    parser.add_argument('--pred_net', help='pred net', type=str, required=True)
    parser.add_argument('--cudnn', help='use cudnn', action='store_true', default=False)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    return args

def deviceOpts():
    device_opts = caffe2_pb2.DeviceOption()
    device_opts.device_type = caffe2_pb2.CUDA
    device_opts.cuda_gpu_id = 3
    return device_opts

def initNet(init_net_path, device_opts):
    init_def = caffe2_pb2.NetDef()
    with open(init_net_path, 'r') as f:
        init_def.ParseFromString(f.read())
        init_def.device_option.CopyFrom(device_opts)
        workspace.RunNetOnce(init_def)
    return init_def

def createNet(predict_net_path, device_opts, use_cudnn=False):
    net_def = caffe2_pb2.NetDef()
    dev = caffe2_pb2.DeviceOption()
    dev.device_type = caffe2_pb2.CPU

    global final_dev 
    final_dev = device_opts
    with open(predict_net_path, 'r') as f:
        net_def.ParseFromString(f.read())
        if use_cudnn:
            for op in net_def.op:
                if op.type == 'PriorBox':
                    op.device_option.CopyFrom(final_dev)
                elif op.type == 'Concat' and op.output[0] == 'mbox_priorbox':
                    op.device_option.CopyFrom(dev)
                elif op.type == 'Norm':
                    op.device_option.CopyFrom(final_dev)
                else:
                    op.device_option.CopyFrom(final_dev)
                    op.engine = 'CUDNN'
        print net_def
        workspace.CreateNet(net_def)
    return net_def

def main(args):
    device_opts = deviceOpts()
    init_def = initNet(args.init_net, device_opts)
    net_def = createNet(args.pred_net, device_opts, use_cudnn=args.cudnn)
     
    print net_def 
    workspace.FeedBlob('data', np.zeros([1, 3, 300, 300]).astype(np.float32), final_dev)
    start = time.time()
    for i in range(1000):
        workspace.RunNet(net_def.name, 1)
    end = time.time()
    print (end-start) / 1000
    

if __name__ == '__main__':
    args = parse_args()
    main(args)
