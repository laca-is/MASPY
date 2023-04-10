import environment as envrmt
from agent import Belief, Ask, Objective
from driver import driver
from manager import manager

def main():
    env = envrmt.env('Simple_Env')
    drv1 = driver('drv1', [Belief('price',[10])], [Objective('offer')])
    drv2 = driver('drv2')
    drv3 = driver('drv3')
    drv4 = driver('drv4', [Belief('price',[20])])
    mgr = manager('mgr')
    env.add_agents([drv1,drv2,drv3,drv4,mgr])
    env.start_all_agents()

    print("END")

if __name__ == "__main__":
    main()
