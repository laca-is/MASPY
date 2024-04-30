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

To create an instance of any agent, only their name is needed.

#### Dummy Agent

```python
from maspy import *

class DummyAgent(Agent):
    def __init__(self, agent_name):
        super().__init__(agent_name)

my_agent = DummyAgent("Dummy")
```

#### Initial Beliefs and Objectives
The agent can also start with some inital *Beliefs* or *Goals*.

```python
from maspy import *

class DummyAgent(Agent):
    def __init__(self, agent_name, beliefs, goals):
        super().__init__(agent_name, beliefs, goals)
        # You may also add some hardcoded beliefs and goals
        self.add(Belief("Box",(5,10)))

# the beliefs/goals may be any iterable collection or a single entity 
agent_1 = DummyAgent("Dummy_1", [Belief("my_pos",(0,0)),Belief("target_pos",(7,7))], Goal("move_boxes"))
agent_2 = DummyAgent("Dummy_2", [Belief("my_pos",(3,3)),Belief("target_pos",(3,3))], Goal("move_boxes"))

```
#### Defining plans
To define plans it is also really simple, it only needs the `@pl` decoration. 
This decoration must contain the *plan* change, the information that changed and optionally
a context needed to be true to execute the plan.

```python
from maspy import *

class DummyAgent(Agent):
    def __init__(self, agent_name, beliefs, goals):
        super().__init__(agent_name, beliefs, goals)
        self.add(Belief("Box",(5,10)))

    # always execute this plan whenever the agent aquires the goal to "move_boxes".
    # this plan also needs the agent to believe a "Box" is at some coordinate (X,Y)
    # every plan needs at least self and src, plus the arguments from the chosen context
    @pl(gain,Goal("move_boxes"),Belief("Box",('X','Y'))
    def some_plan(self, src, X, Y):
        ...

agent_1 = DummyAgent("Dummy_1", [Belief("my_pos",(0,0)),Belief("target_pos",(7,7))], Goal("move_boxes"))
agent_2 = DummyAgent("Dummy_2", [Belief("my_pos",(3,3)),Belief("target_pos",(3,3))], Goal("move_boxes"))
```

#### Simplest Possible Agent w/ a Plan
```python
from maspy import *

class HelloAgent(Agent):
    @pl(gain,Belief("hello"))
    def func(self,src):
        print("Hello World")

agent = HelloAgent()
agent.add(Belief("hello"))
agent.start()
```

This code will generate the following prints:

    Starting MASPY Program
    # Admin #> Registering Agent HelloAgent:('HelloAgent', 1)
    Channel:default> Connecting agent HelloAgent:('HelloAgent', 1)
    # Admin #> Starting Agents
    Agent:('HelloAgent', 1)> Hello World

### Running the agents
Running the system is simple, given the utilities support we have in place.
The `Handler` module contains a few usefull methods to start and manage the 
system.

#### Starting all agents
In case you only need to start all agents, the following snippet is enough.
```python
ag1 = DummyAgent("foo")
ag2 = DummyAgent("bar")

Handler().start_all_agents()
```

#### Starting some agents
This snippet shows how to start agents in a arbitrary order.

```python
ag1 = DummyAgent()
ag2 = DummyAgent()

Handler().start_agent(ag2)
# do other things
Handler().start_agent(ag1)
```
### Comunication between Agents
After starting the agents they may be connected to a channel.

```python
ag1 = DummyAgent("ag1")
ag2 = DummyAgent("ag2")
ag3 = DummyAgent("ag3")

# connect ag1 and ag2 to channel "c"
Handler().connect_to([ag1, ag2], [Channel("c")])
# connect ag3 to channel "c"

Handler().start_all_agents()
# ag1 is send a belief to ag3 by the default channel
ag1.send(ag3.my_name, "tell", Belief("foo"))

#ag2 is sending an Objective to ag1 using a specific channel called "c"
ag2.send(ag1.my_name, "achieve", Objective("bar"), Channel("c"))
```
### Environment
`MASPY` also gives an abstraction to model the environment

#### Creating an environment

```python 
from maspy.environment import Environment

class MyEnv(Environment):
    def __init__(self, env_name="my_env"):
        super().__init__(env_name)

    def env_action(self):
        # do something to change the environment state
        ...
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

## Rough edges
The project still has some rough edges that should be considered. 

- The framework API will probably have a decent amount of breaking changes
in the future.
- There is no support to run a `MASPY`` system in a distributed setting.
- The system performance still unmeasured, altough running a toy system 
with over thousands of agents was possible.


## Papers published

MASPY: Towards the Creation of BDI Multi-Agent Systems, WESAAC 2023

