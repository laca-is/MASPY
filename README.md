# MASPY

*MASPY* is a `Python` library which aims to ease the development of a 
Multi-Agent Systems based on the BDI paradigm. In this paradigm, an agent
will contain *Beliefs*, its knowledge, *Desire*, its wants, and
*Intentions*, how it will achieve their wants. 

*MASPY* creates an abstraction layer to model the agents and the environment
where the agents will act. An agent may contain any number of *Beliefs*, 
*Objectives*, *Plans*, these to classes model desires and intentions, 
respectively. The agent can communicate with others agents, by sending
or requesting any of the previous entitys. This library
uses a Knowledge Query Model Language to model the communication between agents
using acts of speech, or perfomatives, as a base model, in this way an agent can ask, tell,
command or teach anything it needs and knows.

Table of Contents
- [`Managing Beliefs and Goals`](#Managing-Beliefs-and-Goals): Creating, removing and using Beliefs and Goals
- [`Defining plans`](#Defining-plans): Proprieties for the definition of Plans
- [`Communication between Agents`](#Communication-between-Agents): How to send messages between Agents
- [`Managing the Environment`](#Environment): How to create Environments and its Percepts
- [`Internal Functions`](#Internal-Functions): All available MASPY functions.

## Install

To install [MASPY](https://pypi.org/project/maspy-ml/) you can use package-management system `pip`: 

	pip install maspy-ml

To update your already installed version of MASPY to the latest one, you can use:

	pip install maspy-ml -U

The minimum version of `Python` guarateed to work is 3.10, altough earlier 
versions may work.

## Latest changes
	maspy-v0.2.1:
	- New internal function to perceive environments during plans
	- Fixed problem of overwriting perceived beliefs of the environment
	- Better error explanations for debugging
	- More concise system logging
 
	maspy-v0.2.0:
	- Better typing for library functions
	- Fixed perception speed
	- Fixed ending multiple agents problem
	- Better agent finder

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
    # for this plan, the context is the belief of a budget with wanted and max prices
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

### Communication between Agents
After starting the agents they may use the default channel or be connected to private one.

```python
from maspy import *

class Manager(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name,show_exec=False,show_cycle=False)
        self.add(Belief("spotPrice",rnd.randint(12,20),adds_event=False))

    @pl(gain,Goal("sendPrice"),Belief("spotPrice","SP"))
    def send_price(self,src,spot_price):
        # The agent manager sends a goal to the manager via the Parking channel
        self.send(src,achieve,Goal("checkPrice",spot_price),"Parking")

class Driver(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name,show_exec=False,show_cycle=False)
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
    Admin().set_logging(show_exec=True)
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

___ : Represents either an object instance outside its class, or self inside its class.

Iterable : Represents any data structuture that can be iterated.

## Agent
```python
___.print_beliefs #  Print all agent's current beliefs-
___.print_goals #  Print all agent's current goals
___.print_plans #  Print all agent's current plans
___.print_events #  Print all agent's current events

"""
Prints the given arguments with the agent's name as a prefix.
Args:
    *args: The arguments to be printed.
    **kwargs: The keyword arguments to be printed.
Returns:
    None
"""
___.print(*args, **kwargs) 

"""
Connects agent to a target
Args: 
    target - Channel, Environment or str
	when target is str it searches for a file with str for its name
Returns: 
    Connected Channel, Environment or None
"""
___.connect_to(target: Environment | Channel | str)

"""
Disconnects agent from a target
Args: 
    target - Channel or Environment
Returns: 
    None
"""
___.disconnect_from(target: Channel | Environment)

"""
Adds one or more beliefs and(or) goals in agent
Args: 
    data_type - Belief, Goal, Beliefs and(or) Goals
Returns: 
    None
"""
___.add(data_type: Belief | Goal | Iterable[Belief | Goal])

"""
Removes one or more beliefs and(or) goals from agent
Args: 
    data_type - Belief, Goal, Beliefs and(or) Goals
Returns: 
    None
"""
___.rm(data_type: Belief | Goal | Iterable[Belief | Goal])

"""
Checks if the agent has an belief, goal, plan or event
Args:
    data_type - Belief, Goal, Plan or Event
Returns:
    bool: True if has, False if not
"""
___.has(data_type: Belief | Goal | Plan | Event)

"""  
Retrieves a specific data from the agent's knowledge on the given data_type and search parameters
Args:
    data_type - Belief, Goal, Plan or Event: The type of data to retrieve.
    search_with - Belief, Goal, Plan or Event: The info to search with. Defaults to None.
    all - bool: Whether to return all matching data or just the first match. Defaults to False.
    ck_chng - bool: Whether to check the changes argument in the data. Defaults to True.
    ck_type - bool: Whether to check the type of the data. Defaults to True.
    ck_args - bool: Whether to check the arguments of the data. Defaults to True.
    ck_src - bool: Whether to check the source of the data. Defaults to True.
Returns:
    List[data] | data: The retrieved data of the specified type.
    If no matches are found, returns None.
"""  
___.get(data_type: Belief | Goal | Plan | Event,
        search_with:  Belief | Goal | Plan | Event = None,
        all = False, ck_chng=True, ck_type=True, ck_args=True, ck_src=True)
"""
ACTS = 	tell | untell |
	tellHow | untellHow |
	achieve | unachieve |
	askOne | askAll | askHow

MSG = Belief | Ask | Goal | Plan

Sends a message to target agent or agents, optionally through a channel
Args:
    target - str, tuple or list: The target agent or agents to send the message to.
    act - ACTS: The directive of the message.
    msg - MSG, str: The message to send.
    channel - str: The channel to send the message through. Defaults to DEFAULT_CHANNEL.
Returns:
    None
"""
___.send(target: str | tuple | list, act: ACTS, msg: MSG | str, channel: str = DEFAULT_CHANNEL)

"""
Finds another agent's name also connected in an Environment or Channel
Args:
    agent_name - str or list[str]: The class agent or list containing the class name and instance name.
    cls_type - str or None: The type of class to search in. Defaults to "channel".	
    cls_name - str or None: The name of the class to search in. Defaults to "default".
    cls_instance Environment, Channel or None - An specific instance of the class to search in. Defaults to None.
Returns:
    dict[str, set[tuple]], set[tuple] or None: A dictionary, set of tuples, or None based on the agent name provided.
	str -> Agent Class
	tuple -> (Agent Name, ID)
"""
___.find_in(agent_name: str | list[str],
  	    cls_type: str = "channel",
  	    cls_name: str = "default", 
            cls_instance: Environment | Channel | None = None)

"""
Perceives the specified environment(s) and updates the agent's beliefs.
Args:
    env_name str or list[str]: The name of the environment or a list of environment names to perceive.
        env_name can also accepts "all" to perceive all connected environments.
Returns:
    None:
"""
___.perceive(env_name: str | list[str])

"""
Retrieves the environment instance with the given name to make an action
Args:
    env_name - str: The name of the environment to retrieve.
Returns:
    Environment or None: The retrieved environment or None found.
"""
___.action(env_name: str)

"""
Stop the cycle of the agent.
    
This method stops the cycle of the agent by setting the `stop_flag` event to True,
indicating that the cycle should be stopped. It also sets the `paused_agent` flag
to True, indicating that the agent has been paused.Finally, it sets the `running`
flag to False, indicating that the agent is no longer running.

Args:
    None
Returns:
    None
"""
___.stop_cycle()
```

## Environment

```python
___.print_percepts # prints all environment's current percepts

"""
Prints the given arguments with the environment's name as a prefix.
Args:
    *args: The arguments to be printed.
    **kwargs: The keyword arguments to be printed.
Returns:
    None
"""
___.print(*args, **kwargs ) 

"""
Creates in environment one or multiple percepts
Args:
    percept - list[Percept] | Percept: The one or multiple Percept to be created.
Returns:
    None
"""
___.create(percept: list[Percept] | Percept)

"""
Retrieves from environment one or multiple percepts that match the given percept
Args:
    percept - Percept: The percept to search for.
    all - bool: If True, returns all matching percepts. Defaults to False.
    ck_group - bool: Whether to check the group of the percept. Defaults to False.
    ck_args - bool: Whether to check the arguments of the percept. Defaults to True.
Returns:
    List[Percept] or Percept: The retrieved percept(s).
    If no matches are found, returns None.
"""
___.get(percept: Percept, all: bool=False, ck_group: bool=False, ck_args: bool=True)

"""
Changes the arguments of a percept
Args:
    old_percept - Percept: The percept to be changed.
    new_args - Percept.args: The new arguments for the percept.
Returns:
    None
"""
___.change(old_percept: Percept, new_args: Percept.args)

"""
Deletes from environment one or multiple percepts
Args:
    percept - Iterable[Percept] | Percept: The one or multiple Percept to be deleted.
Returns:
    None
"""
___.delete(percept: list[Percept] | Percept)
```

## Admin

```python
"""
Starts the reasoning cycle of all created agents
Args:
    None
Returns:
    None
"""
Admin().start_system()

"""
Starts the reasoning cycle of one of multiple agents
Args:
    agents: list[Agent] or Agent: The agent(s) to start their reasoning cycle
Returns:
    None
"""
Admin().start_agents(agents: Union[list[Agent], Agent])

"""
Connects any number agents to any number of Channels and Environments
Args:
    agents: Iterable[Agent] or Agent: The agent(s) to connect
    targets: Iterable[Environment or Channel], Environment or Channel: The target(s) to connect to
Returns:
    None
"""
Admin().connect_to(agents: Iterable | Agent,
		   targets: Iterable[Environment | Channel] | Environment | Channel)

"""
Sets the logging configuration for the whole system
Args:
    show_exec: bool: Whether to show execution logs
    show_cycle: bool: Whether to show reasoning cycle logs
    show_prct: bool: Whether to show perception logs
    show_slct: bool: Whether to show selection of plans logs
    set_<class>: bool: Whether to affect the class to True | False
Returns:
    None
""" 
Admin().set_logging(show_exec: bool, show_cycle: bool=False,
                show_prct: bool=False, show_slct: bool=False, 
                set_admin=True, set_agents=True,
                set_channels=True, set_environments=True)
					
"""
Slows all agents reasoning cycles by x seconds
Args:
    time: int | float: The time to sleep in seconds
Returns:
    None
"""
Admin().slow_cycle_by(time: int | float):
```
