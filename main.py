import maspy.communication as cmnct
import maspy.environment as envrmt
from maspy.system_control import Control
from maspy.agent import Belief, Ask, Objective
from driver import driver
import importlib as imp
from crossroads import crossroads


def test_beliefs():
    bel_str = Belief("foo", "abc")
    bel_int = Belief("foo", 1)
    bel_float = Belief("foo", 1.0)
    bel_complex = Belief("foo", 1j)
    bel_lists = Belief("foo", [1, [1, 2]])
    bel_tuples = Belief("foo", (1, 2, 3, [2, 3, {1}], {"a": "a"}))
    bel_dicts = Belief("foo", {1: 1, "a": "foo", (1, 2): "teste"})

    beliefs = set(
        [bel_str, bel_int, bel_float, bel_complex, bel_lists, bel_tuples, bel_dicts]
    )
    bel = Belief("foo", [1, 2])

    d = driver("d", beliefs)
    assert d.search_beliefs(belief=bel_str) == bel_str
    assert d.search_beliefs(belief=bel_complex) == bel_complex
    assert d.search_beliefs(belief=bel_dicts) == bel_dicts
    assert d.search_beliefs(belief=bel_lists) == bel_lists
    assert d.search_beliefs(belief=bel_tuples) == bel_tuples
    assert d.search_beliefs(belief=bel_float) == bel_float
    assert d.search_beliefs(belief=bel_int) == bel_int
    assert d.search_beliefs(belief=bel) == []
    d.add_belief(Belief("a"))
    assert d.search_beliefs(belief=Belief("a")) == Belief("a")

def main():
    env = crossroads("cross_env")
    channel = cmnct.Comms("crossing")
    drv1 = driver("drv1", objectives=[Objective("enter_lane", "South>North")])
    drv2 = driver("drv2")
    channel.add_agents([drv1, drv2])
    drv1.add_focus("crossroads")
    drv2.add_focus("crossroads")
    # comm = cmnct.comms('comm')
    # ctrl = control()
    # b1 = Belief("foo", 1)
    # b2 = Belief("foo", 2)
    # b3 = Belief("foo", [3, 4])
    # drv = driver(
    #     "drv3",
    #     [b1, b2, b3, b1],
    #     [Objective("a")],
    #     plans=("a", lambda agent, src: print("Hello World agent")),
    # )
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

    # drv = driver('driver')
    # drv.recieve_msg('World','achieve',Objective('test_focus'))
    # drv.reasoning()

    # imprt = imp.import_module('maspy.''environment')
    # env = imprt.env()
    # env.create_fact('vagas',{1 , 2, 'a', 4},'gerente')
    # env.extend_fact('vagas',{3, 6},'gerente')
    # env.reduce_fact('vagas','a','gerente')

    # print(env.get_facts('all'))

    # drv = driver('driver')
    # drv.recieve_msg('World','achieve',Objective('test_focus'))
    # drv.reasoning()

    print("END")


if __name__ == "__main__":
    test_beliefs()
