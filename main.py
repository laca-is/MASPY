import maspy.communication as cmnct
from maspy.agent import Belief, Ask, Objective
from driver import driver
from manager import manager
import importlib as imp

def main():
    # comm = cmnct.comms('Simple_comm')
    # drv1 = driver('drv1', [Belief('price',[10])], [Objective('offer')])
    # drv2 = driver('drv2')
    # drv4 = driver('drv3', [Belief('price',[15])])
    # mgr = manager('mgr')
    # comm.add_agents([drv1,drv2,drv4])
    # comm.add_agents(mgr)
    # comm.start_all_agents()
    # v = {}
    # v['any'] = {}
    # v['any'].update({'vaga': {}})
    # v['any']
    # print(v)

    # #for vaga in caracs['vagas']:
    imprt = imp.import_module('maspy.''environment')
    env = imprt.env()
    env.add_fact('vagas',{'a' : 1},'gerente')
    env.add_fact('vagas',{'b' : 2},'kay')
    env.add_role('kay')
    print(env.get_facts('all'))
    env.rm_fact('vagas','b')
    print(env.get_facts('all'))
    #drv = driver('driver')
    #drv.recieve_msg('World','achieve',Objective('test_focus'))
    #drv.reasoning()
    
    
    print("END")

if __name__ == "__main__":
    main()
