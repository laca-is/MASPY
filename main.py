import environment as envrmt
from agent import belief, ask, objective
from driver import driver
from manager import manager

def main():
    env = envrmt.env('Simple_Env')
    drv1 = driver('drv1', [belief('price',[10])], [objective('offer')])
    drv2 = driver('drv2')
    drv3 = driver('drv3')
    drv4 = driver('drv4', [belief('price',[20])])
    mgr = manager('mgr')
    env.add_agents([mgr,drv1,drv2,drv3,drv4])
    env.start_all_agents()

    print("END")

if __name__ == "__main__":
    main()
