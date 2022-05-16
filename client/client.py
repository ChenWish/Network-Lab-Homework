import os
import os.path as osp
import sys
BUILD_DIR = osp.join(osp.dirname(osp.abspath(__file__)), "build/service/")
sys.path.insert(0, BUILD_DIR)
import argparse

import grpc
import fib_pb2
import fib_pb2_grpc


def main(args):
    host = f"{args['ip']}:{args['port']}"
    print(host)
    with grpc.insecure_channel(host) as channel:
        stub = fib_pb2_grpc.FibCalculatorStub(channel)

        request = fib_pb2.FibRequest()
        pre_mode = 'None' # 'Hand', 'Object', 'Pose'
        current_mode = 'None'
        while True :
            # print(pre_mode)
            current_mode = input("Please input the mode name: ")
            # print(current_mode != pre_mode)
            if(current_mode != pre_mode) :
                # print("in")
                if(current_mode == 'None'):
                    request.order = 0
                    pre_mode = current_mode
                    response = stub.Compute(request)
                    print(response.value)
                elif(current_mode == 'Hand'):
                    request.order = 1
                    pre_mode = current_mode
                    response = stub.Compute(request)
                    print(response.value)
                elif(current_mode == 'Object'):
                    request.order = 2
                    pre_mode = current_mode
                    response = stub.Compute(request)
                    print(response.value)
                elif(current_mode == 'Pose'):
                    request.order = 3
                    pre_mode = current_mode
                    response = stub.Compute(request)
                    print(response.value)
                else :
                    pass
            else :
                print("The mode is current srunning.")
                
            


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=5487)
    args = vars(parser.parse_args())
    main(args)
