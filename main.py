import environment as envrmt
import agent as agt

def main():
    env = envrmt.env()
    ag = env.create_agent('ag1')
    ag2 = env.create_agent('ag2')
    
    ag.add_belief(agt.belief('a','b'))
    ag.prepare_msg('ag2','tell',agt.belief('crenc','teste',ag.my_name))
    ag2.prepare_msg('ag1','achieve',agt.plan('print',[1,2],ag2.my_name))
    ag.prepare_msg('ag2','askOne',agt.ask('crenc','',ag.my_name))
    print("END")

if __name__ == "__main__":
    main()
