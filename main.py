import communication as cmnct
from agent import Belief, Ask, Objective
from driver import driver
from manager import manager

def main():
    comm = cmnct.comms('Simple_comm')
    drv1 = driver('drv1', [Belief('price',[10])], [Objective('offer')])
    drv2 = driver('drv2')
    drv4 = driver('drv3', [Belief('price',[15])])
    mgr = manager('mgr')
    comm.add_agents([drv1,drv2,drv4])
    comm.add_agents(mgr)
    comm.start_all_agents()

    print("END")

if __name__ == "__main__":
    main()
