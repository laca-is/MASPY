import environment as envrmt
import agent as agt

def main():
    env = envrmt.env()
    ag = env.create_agent('ag1')
    ag2 = env.create_agent('ag2')
    
    ag.add_belief(agt.belief('a','b'))
    ag.prepare_msg('ag2','tell',agt.belief('crenc','first'))
    ag.prepare_msg('ag2','tell',agt.belief('crenc','second'))
    #ag2.prepare_msg('ag1','achieve',agt.plan('print',[1,2]))
    ag2.print_beliefs()
    ag.prepare_msg('ag2','askAll',agt.belief('crenc','A'))
    print("END")

if __name__ == "__main__":
    main()
