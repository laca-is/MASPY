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
ag = DummyAgent("dummy")
env = MyEnv()
# connect the agent to the environment
ag.connect_to(env)

Handler().start_all_agents()
# execute environment action
ag.execute_in("my_env").env_action(ag)
```

#### Simplest Possible Agent w/ a Plan
```python
from maspy import *

class HelloAgent(Agent):
    @pl(gain,Belief("hello"))
    def func(self,src):
        self.print("Hello World")
        self.stop_cycle()

agent = HelloAgent()
agent.add(Belief("hello"))
Admin().start_system()
```

This code will generate the following prints:

    Starting MASPY Program
    # Admin #> Registering Agent HelloAgent:('HelloAgent', 1)
    Channel:default> Connecting agent HelloAgent:('HelloAgent', 1)
    # Admin #> Starting Agents
    Agent:('HelloAgent', 1)> Hello World
    Agent:('HelloAgent', 1)> Shutting Down...
    Ending MASPY Program

Notice that the agent is manually stoped with ```self.stop_cycle()```. 
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

