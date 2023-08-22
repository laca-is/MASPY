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

## Using the library
This project still in its infancy and there isn't a `pip` package to use the 
`MASPY` as a dependecy. Right now to use the project, clone the repository
and manually import as a `Python` module. 

The minimum version of `Python` guarateed to work is 3.10, altough earlier 
versions may work.


## Examples

### Creating a new Agent
To create a new agent, it is only needed to extend an `Agent` base class,
this add all of the necessary logic to execute an agent. the following
snippet shows how to create an `DummyAgent`.

#### Dummy Agent

```python
from maspy.agent import Agent

class DummyAgent(Agent):
    def __init__(self, agent_name):
        super().__init__(agent_name)

if __name__ == "__main__":
    my_agent = DummyAgent("Dummy")

```
#### Initial Beliefs and Objectives
The agent can also start with some inital *Beliefs* or *Objectives*.

```python
from maspy.agent import Agent, Belief, Objective

class AgentWithInitalStates(Agent):
    # the caller will provide beliefs and objectives
    def __init__(self, name, beliefs, objectives):
        super().__init__(name, beliefs, objectives)
        # You may also add some hardcoded beliefs and objectives
        self.add(Objective("some_objective"))
        self.add(Belief("some Belief"))

if __name__ == "__main__":
    # the beliefs/objectives may be any iterable collection or a single
    # entity directly 
    my_agent = AgentWithInitialStates("SomeAgent" [Belief("b")], Objective("o"))
```
#### Defining plans
To define plans it is also really simple, it only needs the `Agent.plan` 
decoration. This decoration must contain the *plan* name, and optionally
a context needed to be true to execute the plan.

```python
from maspy.agent import Agent

class AgentWithPlans(Agent):
    def __init__(self, name):
        super().__init__(name)
    
    @Agent.plan("plan_name")
    # always execute this plan whenever Objective("plan_name") exists
    # every plan needs at least 2 arguments, self and src.
    def some_plan(self, src):
        # do something you would in a ordinary python function
        ...

    @Agent.plan("plan_name2", (Belief("foo")))
    # only execute this plan if the agent has Belief("foo")
    def some_plan(self, src):
        # do something you would in a ordinary python function
        ...
```

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

