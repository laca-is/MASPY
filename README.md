# MASPY

*MASPY* is a `Python` library which aims to ease the development of a 
Multi-Agent Systems based on the BDI paradigm. In this paradigm, an agent
will contain *Beliefs*, its knowledge, *Desire*, its wants, and
*Intentions*, how it will achieve their wants. 

*MASPY* creates an abstraction layer to model the agents and the environment
where the agents will act. An agent may contain any number of *Beliefs*, 
*Objectives*, *Plans*, these to classes model desires and intentions, 
respectively. The agent can comunicate with others agents, by sending
or requesting any of the previous entitys. This library
uses a Knowledge Query Model Language to model the communication between agents
using acts of speech, or perfomatives, as a base model, in this way an agent can ask, tell,
command or teach anything it needs and knows.

## Install

To install [MASPY](https://pypi.org/project/maspy-ml/) you can use package-management system `pip`: 

        `pip install maspy-ml` 

The minimum version of `Python` guarateed to work is 3.10, altough earlier 
versions may work.

## Using MASPY

### Import

To use the library you need this simple import  ```from maspy import *``` , nothing more or less.

Everything for ``MASPY`` to run correctly in imported this way.

### Creating a new Agent

To create a new agent, you only need to extend `Agent` in your class,
this adds all of the necessary logic to execute an agent. the following
snippet shows how to create an `DummyAgent`. 

To create an instance of any agent, only the Extension is needed.

Technically, this is a MASPY Agent:

#### Dummy Agent

```python
from maspy import *

class DummyAgent(Agent):
    pass

my_agent = DummyAgent()
named_agent = DummyAgent("Ag")
```

When the snippet above is run, this is the printed result:
    
    Starting MASPY Program
    # Admin #> Registering Agent DummyAgent:('DummyAgent', 1)
    Channel:default> Connecting agent DummyAgent:('DummyAgent', 1)
    # Admin #> Registering Agent DummyAgent:('Ag', 1)
    Channel:default> Connecting agent DummyAgent:('Ag', 1)

It will execute indeterminably, while doing nothing.

#### Initial Beliefs and Goals
The agent can start with some inital *Beliefs* or *Goals*.

For most of theses explanations, the code from "examples/ex_parking.py" will be used.

```python
from maspy import *

class Driver(Agent):
    def __init__(self, agent_name=None):
        super().__init__(agent_name)
        self.add(Belief("budget",(rnd.randint(6,10),rnd.randint(12,20)),adds_event=False))
        self.add(Goal("park"))

driver = Driver("Drv")
```

#### Managing Beliefs and Goals
Here are some info about *Beliefs* and *Goals* being created and removed.

- This function adds a *goal* to the agent;
- The first field represents the *goal* key and must always be a string;
- The second field represents arguments of the *goal* and will always be a tuple;
    + Each argument can have any structure, with each position of the tuple representing a different one;
- The third field represents the *goal* source. It is "self" by default, or another agent.
- adding or removing a *goal* always creates an event for agent, which will try to find a applicable plan.

```python
agent = DummyAgent("Ag")
agent.add( Goal(key, args, source) )
agent.rm( Goal(key, args, source) )
        
agent.add( Goal("check_house", {"Area": [50,100], "Rooms": 5}, ("Seller",27) ) )
agent.add( Goal("SendInfo", ("Information",["List","of","Information",42]) ) )
agent.rm( Goal("walk", source=("trainer",2)) )
```

- This function adds a *belief* to the agent;
- The first an second field work exaclty the same way as the *goal*'s
- The third field represents the *belief* source. It is "self" by default, another agent or an environment.
- The fourth field dictates if the adding or removing the belief will generate a new event.
    + By default it does, but sometimes one does not want a group of beliefs to be considerend new events 

```python
agent = DummyAgent("Ag")
agent.add( Belief(Key, Args, Source, Adds_Event) )
agent.rm( Belief(Key, Args, Source, Adds_Event) )

agent.add( Belief("Dirt", (("remaining",3),[(2,2),(3,7),(5,1)])) )
agent.rm( Belief("spot",("A",4,"free"),"Parking",False) )
agent.add( Belief("velocity",57) )
```

#### Defining plans
To define plans it is also really simple, it only needs the `@pl` decoration. 
This decoration must contain the *plan* change *{gain, lose or test}*, the data that changed *{Belief(s) or Goal(s)}* and optionally
a context needed to be true to execute the plan *{Belief(s) or Goal(s)}*.

```python
    change: TypeVar('gain'|'lose'|'test')
    changed_data: Iterable[Belief | Goal] | Belief | Goal
    context: Iterable[Belief | Goal] | Belief | Goal

    @pl(change, changed_data, context)
    def foo(self,src, *changed_data.args, *context.args):
```

Resuming the the driver example, you can implement a plan the following way:

```python
from maspy import *

class Driver(Agent):
    def __init__(self, agent_name=None):
        super().__init__(agent_name)
        self.add(Belief("budget",(rnd.randint(6,10),rnd.randint(12,20)),adds_event=False))
        self.add(Goal("park"))

    # This plan will be executed whenever the agent gains the goal "checkPrice"
    # Every plan needs at least self and src, plus the arguments from the trigger and context
    # for this plan, the context is the belief of a budget with wanted e max prices
    @pl(gain,Goal("checkPrice","Price"),Belief("budget",("WantedPrice","MaxPrice")))
    def check_price(self,src,given_price,want_price,max_price):
        ...

driver = Driver("Drv")
```

### Running the agents
Running the system is simple, given the utilities support we have in place.
The `Admin` module contains a few useful methods to start and manage the 
system.

#### Starting all agents
In case you only need to start all agents, the following snippet is enough.
```python
driver1 = Driver("Drv")
driver2 = Driver("Drv")

Admin().start_system()
```
In this example, both agents have the same name "Drv". 

For communication to not be ambiguous, the Admin names them ("Drv",1) and ("Drv",2).

### Comunication between Agents
After starting the agents they may use the default channel or be connected to private one.

```python
from maspy import *

class Manager(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name,full_log=False,show_cycle=False)
        self.add(Belief("spotPrice",rnd.randint(12,20),adds_event=False))

    @pl(gain,Goal("sendPrice"),Belief("spotPrice","SP"))
    def send_price(self,src,spot_price):
        # The agent manager sends a goal to the manager via the Parking channel
        self.send(src,achieve,Goal("checkPrice",spot_price),"Parking")

class Driver(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name,full_log=False,show_cycle=False)
        self.add(Belief("budget",(rnd.randint(6,10),rnd.randint(12,20)),adds_event=False))
        self.add(Goal("park"))
    
    @pl(gain,Goal("park"))
    def ask_price(self,src):
        # The agent driver sends a goal to the manager via the Parking channel
        self.send("Manager", achieve, Goal("sendPrice"),"Parking")

park_ch = Channel("Parking")
manager = Manager()
driver = Driver("Drv")
Admin().connect_to([manager,driver],park_ch)
```

The following are the different ways to send messages between agents.
If ommited, the default channel is used.

```python 
self.send(target, "tell", Belief, Channel)
self.send(target, "untell", Belief, Channel)
self.send(target, "achieve", Goal, Channel)
self.send(target, "unachieve", Goal, Channel)
self.send(target, "askOne", Belief, Channel)
self.send(target, "askAll", Belief, Channel)
self.send(target, "tellHow", Plan, Channel)
self.send(target, "untellHow", Plan, Channel)
self.send(target, "askHow", Plan, Channel)
```

### Environment
`MASPY` also gives an abstraction to model the environment.

Here's how you create a parking lot for the manager and driver from before:

#### Creating an environment

```python 
from maspy import *

class Park(Environment):
    def __init__(self, env_name=None):
        super().__init__(env_name)
        # This creates in the environment a percept for connected agents to perceive.
        # This specific percept does not create a event when percieved by an agent 
        self.create(Percept("spot",(1,"free"),adds_event=False))

    def park_spot(self, driver, spot_id):
        # The function get gives you percepts from the environment
        # It has various filters to make this search more precise
        spot = self.get(Percept("spot",(spot_id,"free")))
        if spot:
            # This function is used to modify the arguments of an percept.
            self.change(spot,(spot_id,driver))

            # You could also remove the old and create the new
            self.remove(spot)
            self.create(Percept("spot",(spot_id,driver)))

    def leave_spot(self, driver):
        spot = self.get(Percept("spot",("ID",driver)))
        if spot:
            self.change(spot,(spot.args[0],"free"))
```

#### Allowing agents to interact with an environment
```python
from maspy import *

class Park(Environment):
    def __init__(self, env_name=None):
        super().__init__(env_name)
        self.create(Percept("spot",(1,"free"),adds_event=False))

    def park_spot(self, driver, spot_id):
        spot = self.get(Percept("spot",(spot_id,"free")))
        if spot:
            self.change(spot,(spot_id,driver))

class Driver(Agent)
    @pl(gain,Goal("park",("Park_Name","SpotID")))
    def park_on_spot(self,src,park_name,spot_id):
        # This agent functions makes the connection with an environment or channel
        # Just give it Channel(Name) or Envrionment(Name) to add it to the agent 
        self.connect_to(Environment(park_name))

        # After the connection, the agent can make an action with a Park function
        self.action(park_name).park_spot(self.my_name,spot_id)
```

#### Simplest System with Every Class
```python
from maspy import *

class SimpleEnv(Environment):
    def env_act(self, agent1, agent2):
        self.print(f"Contact between {agent1} and {agent2}")

class SimpleAgent(Agent):
    @pl(gain,Goal("say_hello","Agent"))
    def send_hello(self,src,agent):
        self.send(agent,tell,Belief("Hello"),"SimpleChannel")

    @pl(gain,Belief("Hello"))
    def recieve_hello(self,src):
        self.print(f"Hello received from {src}")
        self.action("SimpleEnv").env_act(self.my_name,src)

if __name__ == "__main__":
    Admin().set_logging(full_log=True)
    agent1 = SimpleAgent()
    agent2 = SimpleAgent()
    env = SimpleEnv()
    ch = Channel("SimpleChannel")
    Admin().connect_to([agent1,agent2],[env,ch])
    agent1.add(Goal("say_hello",(agent2.my_name,)))
    Admin().start_system()
```

This code will generate the following prints:

    Starting MASPY Program
    # Admin #> Registering Agent SimpleAgent:('SimpleAgent', 1)
    # Admin #> Registering Channel:default
    Channel:default> Connecting agent SimpleAgent:('SimpleAgent', 1)
    # Admin #> Registering Agent SimpleAgent:('SimpleAgent', 2)
    Channel:default> Connecting agent SimpleAgent:('SimpleAgent', 2)
    # Admin #> Registering Environment SimpleEnv:SimpleEnv
    # Admin #> Registering Channel:SimpleChannel
    Environment:SimpleEnv> Connecting agent SimpleAgent:('SimpleAgent', 1)
    Channel:SimpleChannel> Connecting agent SimpleAgent:('SimpleAgent', 1)
    Environment:SimpleEnv> Connecting agent SimpleAgent:('SimpleAgent', 2)
    Channel:SimpleChannel> Connecting agent SimpleAgent:('SimpleAgent', 2)
    Agent:('SimpleAgent', 1)> Adding Goal('say_hello', ('SimpleAgent', 2), 'self')
    Agent:('SimpleAgent', 1)> New Event: gain:Goal('say_hello', ('SimpleAgent', 2), 'self')
    # Admin #> Starting Agents
    Agent:('SimpleAgent', 1)> Running Plan(Event(change='gain', data=Goal(key='say_hello', _args=('Agent',), source='self'), intention=None), [], 'send_hello')
    Channel:SimpleChannel> ('SimpleAgent', 1) sending tell:Belief('Hello', (), ('SimpleAgent', 1)) to ('SimpleAgent', 2)
    Agent:('SimpleAgent', 2)> Adding Belief('Hello', (), ('SimpleAgent', 1))
    Agent:('SimpleAgent', 2)> New Event: gain:Belief('Hello', (), ('SimpleAgent', 1))
    Agent:('SimpleAgent', 2)> Running Plan(Event(change='gain', data=Belief(key='Hello', _args=(), source='self', adds_event=True), intention=None), [], 'recieve_hello')
    Agent:('SimpleAgent', 2)> Hello received from ('SimpleAgent', 1)
    Environment:SimpleEnv> Contact between ('SimpleAgent', 2) and ('SimpleAgent', 1)
    # Admin #> [Closing System]
    Agent:('SimpleAgent', 1)> Shutting Down...
    Agent:('SimpleAgent', 2)> Shutting Down...
    Ending MASPY Program

This program must be terminated using a *ctrl+c*.
Otherwise the system would continue running indeterminately.

## Rough edges
The project still has some rough edges that should be considered. 

- The framework API will probably have a decent amount of breaking changes
in the future.
- There is no support to run a `MASPY`` system in a distributed setting.
- The system performance still unmeasured, altough running a toy system 
with over thousands of agents was possible.

## Papers published

MASPY: Towards the Creation of BDI Multi-Agent Systems, WESAAC 2023

# Internal Functions


## Agent
```python
___.print_beliefs """  Print all agent's current beliefs-
___.print_goals """  Print all agent's current goals
___.print_plans """  Print all agent's current plans
___.print_events """  Print all agent's current events

"""  print a string using with the agent's name
___.print(*args, **kwargs ) 

"""  connects agent to a Channel or Environment
___.connect_to(target: Channel | Environment | str, target_name: str = None)

"""  disconnects agent from a Channel or Environment
___.disconnect_from(self, target: Channel | Environment)

"""  adds one or more beliefs and(or) goals in agent
___.add(data_type: Belief | Goal | Iterable[Belief | Goal])

"""  removes one or more beliefs and(or) goals from agent
___.rm(data_type: Belief | Goal | Iterable[Belief | Goal])

"""  checks if the agent contains an belief, goal, plan or event
"""  returns True or False
___.has(data_type: Belief | Goal | Plan | Event)

"""  
search agent for a similar belief, goal, plan or event
  optionally, search using info from a belief, goal, plan or event
  optionally, return all similarlly found data
  optional similarity checks:
	ck_chng - plan or event change must be the same
	ck_type - type must be the same
	ck_args - args
	ck_src 
  returns belief, goal, plan, event or Iterable of one
"""  
___.get(data_type: Belief | Goal | Plan | Event,
        search_with:  Belief | Goal | Plan | Event = None,
        all = False, ck_chng=True, ck_type=True, ck_args=True, ck_src=True)

ACTS = 	tell | untell |
		tellHow | untellHow |
		achieve | unachieve |
		askOne | askAll | askHow

MSG = Belief | Ask | Goal | Plan

"""  agent sends message to target agent(s), optionally using a channel
___.send(target: str | tuple | List | "broadcast", act: ACTS, msg: MSG | str, channel: str = DEFAULT_CHANNEL)

"""  find another agent's name also connected in an Environment or Channel
___.find_in(self, agent_name, cls_type=None, cls_name=["env","default"], cls_instance=None

"""  returns connected Environment isntance to make an action
___.action(env_name: str)

"""  ends the agent reasoning cycle
___.stop_cycle()
```

## Environment

```python
___.print_percepts """  print all environment's current percepts

"""  print a string using with the environment's name
___.print(*args, **kwargs ) 

"""  create in environment one or multiple percepts
___.create(percept: Iterable[Percept] | Percept)

"""  search environment for a similar percepts
"""  optionally return all similar percepts
"""  optional similarity checks:
	ck_group -
	ck_args -
"""  return requested information
___.get(percept: Percept, all: Boolean=False,
		ck_group: Boolean=False, ck_args: Boolean=True)

"""  change the args from an old percept
___.change(old_percept: Percept, new_args: Percept.args)

"""  delete from environment one or multiple percepts
___.delete(percept: Iterable[Percept] | Percept)
```

## Admin

```python
"""  starts the reasoning cycle of all created agents
___.start_system()

"""  starts the reasoning cycle of one of multiple agents
___.start_agents(agents: Iterable[Agent] | Agent)

"""  connects any number agents to any number of Channels and Environments
___.connect_to(agents: Iterable[Agent] | Agent, targets: Iterable[Environment | Channel] | Environment | Channel)

"""  Log Settings
""" 
 Optionally set to show
	- execution logs with full_log;
	- reasoning cycle logs with show_cycle;
	- perception of environments with show_prct;
	- selection of plans with show_slct;
 Optionally set what class this effects with set_<class>= True | False
""" 
___.set_logging(full_log: bool, show_cycle: bool=False,
                show_prct: bool=False, show_slct: bool=False, 
                set_admin=True, set_agents=True,
                set_channels=True, set_environments=True)
					
"""  slow all agents reasoning cycles by x seconds
___.slow_cycle_by(self, time: int | float):
```
