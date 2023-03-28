import environment as envrmt
import agent as agt
from driver import driver

def main():
    env = envrmt.env()
    drv1 = driver('drv_1')
    drv2 = driver('drv_1')
    env.add_agents([drv1,drv2])
    
    drv1.recieve_msg(drv1.my_name,'achieve',agt.plan('start_agent',[drv1]))


    # drv1.add_belief(agt.belief('a',['b']))
    # drv1.prepare_msg('drv_2','tell',agt.belief('crenc',['first']))
    
    # drv1.prepare_msg('drv_2','tell',agt.belief('crenc',['second']))

    # drv2.print_beliefs()
    # drv1.prepare_msg('drv_2','askAll',agt.belief('crenc',['A']))
    print("END")

if __name__ == "__main__":
    main()
