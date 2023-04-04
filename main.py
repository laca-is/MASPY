import environment as envrmt
import agent as agt
from driver import driver

def main():
    env = envrmt.env()
    drv1 = driver('dr#v')
    drv2 = driver('dr#v')
    env.add_agents([drv1,drv2])
    env.start_all_agents()
    #env.add_agent(driver('drv'))
    #drv1.recieve_msg(drv1.my_name,'achieve',agt.plan('reason',[drv1]))


    # drv1.add_belief(agt.belief('a',['b']))
    # drv1.prepare_msg('drv_2','tell',agt.belief('crenc',['first']))
    
    # drv1.prepare_msg('drv_2','tell',agt.belief('crenc',['second']))

    # drv2.print_beliefs()
    # drv1.prepare_msg('drv_2','askAll',agt.belief('crenc',['A']))
    print("END")

if __name__ == "__main__":
    main()
