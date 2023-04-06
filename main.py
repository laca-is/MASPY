import environment as envrmt
from agent import belief, ask, objective
from driver import driver

def main():
    env = envrmt.env('Simple_Env')
    drv1 = driver('drv1', [belief('price',[10])], [objective('offer')])
    drv2 = driver('drv2', [belief('price',[16])])
    drv3 = driver('drv3')
    env.add_agents([drv1,drv2,drv3])
    env.start_all_agents()

    print("END")

if __name__ == "__main__":
    main()
