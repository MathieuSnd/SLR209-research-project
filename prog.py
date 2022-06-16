from crypt import methods
from dataclasses import dataclass
from json import loads, dumps
from tkinter import S
import pykka
import numpy as np
from time import sleep
from actor import AbstractActor
import time


Height = list[6]


class Actor(AbstractActor):
    peers: dict
    peer_heights: dict
    height: Height
    
    
    
    def __str__(self):
        return self.__repr__()
    def __repr__(self):
        return "Actor {" + f"height={self.height}, peers={list(self.peer_heights.keys())}" + "}" 
    
    def __init__(self):
        super().__init__()
        self.peer_heights = {}
        self.height = []
        
        
    def suicide(self):
        for p in self.peers.values():
            p.tell({"type": "suicide", "id": self.height[-1]})
        self.stop()
        
    
    def getId(self):
        return self.height[-1]
    
    def broadcastUpdate(self):
        print(f"{self.height[-1]} bc to {list(self.peers.keys())}")
        for peer in self.peers.values():
            peer.tell({'type': 'update', 'height': self.height})
    
    def is_sink(self):
        for peer in self.peer_heights.values():
            if peer < self.height:
                return False
        return True
    
    
    def peer_ref_levels(self):
        return [p[1:4] for p in self.peer_heights.values()]
    

            
    def update_message(self, height):
        sink = self.is_sink()
        
        self.peer_heights[height[-1]] = height
        print("update", self.height, self.peer_heights)
        
        
        if height[0] != self.height[0]:
            # When node i receives an Update message 
            # from neighboring node j such that lidj != lidi: 
            
        
            # if lidi > lidj or (oidi = lidj and ri = 1)
            if self.height[0] > height[0] or (self.height[2] == height[2] and self.height[2] == 1):
                self.height = [height[0], 0, 0, 0, height[4]+1, self.height[-1]]
                print(f"adopt {self.height[-1]} -> {height[-1]}")
                
                assert not self.is_sink()
                
                self.broadcastUpdate()
                

        
        # print("sink", sink, " ---> ", self.is_sink())
        
        if sink:
            return
        
        print("becomes sink", self.height)
        
        
        h = self.height  
                
        if self.update_height(height[-1]):
            print("updated height", self.height)
            self.broadcastUpdate()
        else:
            assert h == self.height
        
             
    def suicide_message(self, id):
        del self.peers[id]
        del self.peer_heights[id]
        
        if self.is_sink():
            if self.peers == {}:
                # leader of its own group
                id = self.height[-1]
                self.height = [id, -1, -1, -1, 0, id]
            else:
                print("NEW SINK", self.height)
                id = self.height[-1]
                t = time.time()
                self.height[1:4] = [t, id, 0]
                
            self.broadcastUpdate()
        else:
        
        
        
        
            
    """
        cause: id of the actor that sended the message 
        that caused the update
        returns wether the height changed or not
    """
    def update_height(self, cause: int) -> bool:
        
        
        if not self.is_sink():
            return False
        
        print("SINK", self.height, self.peer_heights)
        
        
        rl = self.peer_ref_levels()
        
        if min(rl) != max(rl):
            # not all peers have the same reference level
            # then i sets its reference level to the largest among
            # all its neighbors and sets its delta to one less than the
            # minimum delta value among all neighbors with the largest
            # reference level (a partial reversal). 
            
            # B
            
            print("B")
            
            ref_level = max(self.peer_ref_levels())
            
            # partial link reversal
            delta = self.height[4]
            for p in self.peer_heights.values():
                if p[1:4] == ref_level:
                    delta = min(delta, p[4] - 1)
            
            self.height[1:4] = ref_level
            self.height[4] = delta
            
        else:
            print("ELSEEEEEEEEEE")
            peers_ref = rl[0]
            if peers_ref[2] == 0: # r == 0
                # unreflected ref level
                # i starts a reflection
                # of this reference level by setting 
                # its reference level to
                # the reflected version of its neighbors' 
                # (with ri = 1) and its delta to 0
                
                print("C - REFLECTIONNNNNNNNNNNNNNNNNNNN")
                self.height[1:4] = [peers_ref[0], peers_ref[1], 1]
                self.height[4] = 0
            elif peers_ref[1] == i: # r == 1, oid == i
                # all of i's neighbors have the same reflected reference
                # level with i as the originator, then i has detected a
                # partition and takes appropriate action. 
                
                # D
                print("NEW LEADER ELECTED")
                id = self.height[-1]
                self.height = [id, -1, -1, -1, 0, id]
            else:
                #all of i's neighbors have the same reflected reference
                #level with an originator other than i, then i starts a
                #new reference level. This situation only happens if a
                #link fails while the system is recovering from an earlier
                #link failure. 
                print("NEW REF LEVEL")
                assert 0
        return True


    def init_message(self, actor_id, peers):
        self.height = [actor_id, -1, -1, -1, 0, actor_id]
        self.peers = peers
    
    
    def start_message(self):
        print("start")
        self.broadcastUpdate()
        
        
    def getself_message(self):
        return self
        
        

# return actor refs and links
def init_actors(N, p):
    actorrefs = {i: Actor().start() for i in range(N)}
    
    links = {i: [] for i in range(N)}
    
    
    # np.random.seed(0)
    
    for i in range(N):
        others = [j for j in range(N)]
        others.remove(i)
        
        
        added_links = list(np.random.choice(others, p, replace=False))
        
        links[i] += added_links
        for j in added_links:
            links[j].append(i)
    
    return actorrefs, links


N = 20; p = 3

actor_refs, links = init_actors(N, p)

actors = [a.ask({"type": "getself"}) for a in actor_refs.values()]

# pring average of number of links per actor
#print(np.mean([len(links[i]) for i in range(N)]))

# print variance of number of links per actor
#print(np.var([len(links[i]) for i in range(N)]))





# send set_id message to all actors
for i in range(len(actors)):
    actor_refs[i].ask({
        "type": "init",
        "actor_id": i,
        "peers": {id: actor_refs[id] for id in links[i]},
    })


"""
    kill the actor with id = i
"""
def kill_actor(i: int):
    # find actor with height[-1] = i
    a = [a for a in actors if a.height[-1] == i][0]

    a.suicide()
    actors.remove(a)
    del actor_refs[i]
    

print(actors)

for a in actor_refs.values():
    a.tell({
        "type": "start",
    })


sleep(1)


print(*actors, sep=",\n")




import matplotlib.pyplot as plt

def draw_graph(actors, links):
    import networkx as nx
    
    G = nx.DiGraph()
    G.add_nodes_from(range(len(actors)))

    
    # add from link list
    for a in actors:
        # heights of neighbors
        
        aid = a.height[-1]
        
        
        outgoing = [h for h in a.peer_heights.values() if h < a.height]
        
        if outgoing == []:
            continue
            
        min_link = min(outgoing)
        
        outgoing.remove(min_link)
        
        G.add_edge(aid, min_link[-1], color="red", weight=2)

        for o in outgoing:
            # grey edge
            G.add_edge(aid, o[-1], color="grey", weight=1)
            
            
    # pos = nx.kamada_kawai_layout(G)

    edges = G.edges()
    colors = [G[u][v]['color'] for u,v in edges]
    weights = [G[u][v]['weight'] for u,v in edges]

    nx.draw(G, edge_color=colors, width=weights, with_labels=True, node_size=800, node_color="black", font_color="white")
    
    
draw_graph(actors, links)

for a in actor_refs.values():
    a.stop()
plt.show()

