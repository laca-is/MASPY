import maspy.communication as cmnct
import maspy.environment as envrmt
from maspy.system_control import Control
from maspy.agent import Belief, Ask, Objective
from driver import driver
from manager import manager
import importlib as imp

def main():

    # comm = cmnct.comms('comm')
    #ctrl = control()

    # drv3 = driver('drv3', 1 ,[Objective('a')], plans=('a', lambda agent, src: print('Hello World agent')))
    # drv2 = driver('drv2')
    # drv1 = driver('drv1', [Belief('price',[10])], [Objective('offer')])
    # Control().start_all_agents()
    
    # mgr = manager('mgr')
    # ctrl.add_agents([drv1,drv2,drv4])
    # ctrl.add_agents(mgr)
    # ctrl2 = control()
    # print(ctrl2.get_agents())
    # ctrl.start_all_agents()
    # v = {}
    # v['any'] = {}
    # v['any'].update({'vaga': {}})
    # v['any']
    # print(v)
    
    # a = cmnct.comms('Publico')
    # b = cmnct.comms('Publico')
    # c = cmnct.comms()
    # print(a is b)
    # print(a is c)
    # print(b is c)
    
    
    # imprt = imp.import_module('maspy.''environment')
    # env = imprt.env()
    # env.create_fact('vagas',{1 , 2, 'a', 4},'gerente')
    # env.extend_fact('vagas',{3, 6},'gerente')
    # env.reduce_fact('vagas','a','gerente')

    # print(env.get_facts('all'))
    
    #drv = driver('driver')
    #drv.recieve_msg('World','achieve',Objective('test_focus'))
    #drv.reasoning()
    
    print("END")

if __name__ == "__main__":
    main()
