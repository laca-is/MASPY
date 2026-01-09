![MASPY Logo](/docs/imgs/MASPY_LOGO.png)

*MASPY* is a `Python` Framework which aims to ease the development of a 
Multi-Agent Systems based on the BDI paradigm. In this paradigm, an agent
will contain *Beliefs*, its knowledge, *Desire*, its wants, and
*Intentions*, how it will achieve their wants. 

*MASPY* creates an abstraction layer to model the agents and the environment
where the agents will act. An agent may contain any number of *Beliefs*, 
*Objectives*, *Plans*, these to classes model desires and intentions, 
respectively. The agent can communicate with others agents, by sending
or requesting any of the previous entitys. This Framework
uses a Knowledge Query Model Language to model the communication between agents
using acts of speech, or perfomatives, as a base model, in this way an agent can ask, tell,
command or teach anything it needs and knows.

For a more in-detph documentation, see our [WIKI](https://github.com/laca-is/MASPY/wiki)

## Install

To install [MASPY](https://pypi.org/project/maspy-ml/) you can use package-management system `pip`: 

	pip install maspy-ml

To update your already installed version of MASPY to the latest one, you can use:

	pip install maspy-ml -U

**MASPY needs `Python` 3.12+ to run correctly.**

## Using MASPY

### Import

To use the Framework you need this simple import  ```from maspy import *``` , nothing more or less.

Everything for ``MASPY`` to run correctly in imported this way.

Every internal Function is explained in our [WIKI](https://github.com/laca-is/MASPY/wiki)

## Rough edges
The project still has some rough edges that should be considered. 

- The framework API will probably have a decent amount of breaking changes
in the future.
- There is no support to run a ``MASPY`` system in a distributed setting.
- The system performance still unmeasured, altough running a toy system 
with over thousands of agents was possible.

## Papers published

- [MASPY: A Python-Based Framework for Developing BDI Multi-Agent Systems, PAAMS, 2025](https://link.springer.com/chapter/10.1007/978-3-032-07638-0_18) 
- [Towards the Integration of Reinforcement Learning into MASPY, WESAAC 2025](https://doi.org/10.5753/wesaac.2025.37544)
- [MASPY: Towards the Creation of BDI Multi-Agent Systems, WESAAC 2023](https://doi.org/10.5753/wesaac.2023.33440)
