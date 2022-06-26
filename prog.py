from crypt import methods
from dataclasses import dataclass
from json import loads, dumps
from tkinter import S
import pykka
import numpy as np
from time import sleep
from actor import AbstractActor


Height = list[6]


class Actor(AbstractActor):
    peers: dict
    heights: dict # dict(int, Height)
    pid: int
    peer_pids: dict # node id -> partition id
    peer_heights: dict # node id -> {partition id -> Height}
    
    def __str__(self):
        return self.__repr__()
    def __repr__(self):
        return "Actor {" + f"height={self.heights}, peers={list(self.peer_heights.keys())}" + "}" 
    
    def __init__(self):
        super().__init__()
        self.peer_heights = {}
        self.peer_pids = {}
        self.heights = {}
        
    
    def getId(self):
        return self.heights[self.pid][-1]
    
    def broadcastUpdate(self):
        print(f"{self.heights[self.pid][-1]} bc to {list(self.peers.keys())}")
        for peer in self.peers.values():
            peer.tell({
                'type': 'update', 
                'heights': self.heights,
                'id': self.heights[self.pid][-1],
                'pid': self.pid
            })
    
    def is_sink(self):
        pid = self.pid
        
        for id in self.peer_heights.keys():
            if self.peer_pids[id] != pid:
                continue
            
            if self.peer_heights[id][pid] < self.heights[pid]:
                return False
        return True
    
    # ref levels of peers in our partition
    def peer_ref_levels(self):
        rl = []
        
        pid = self.pid
        
        for i in self.peers.keys():
            if self.peer_pids == self.pid:
                rl.append(self.peer_heights[i][pid][1:4])
        return rl    

            
    def update_message(self, id, heights, pid):
        sink = self.is_sink()
        
        heights = heights.copy()
        
        self.peer_heights[id] = heights
        self.peer_pids[id] = pid
        
        need_broadcast = False
        
        if pid != self.pid:
            updated = False
            for p in heights.keys():
                h = heights[p]
                if isinstance(h, list):
                    h = 0
                    
                if p == self.pid: 
                    continue
                    
                if p in self.heights.keys() and self.heights[pid] <= h + 1:
                    continue
                
                updated = True
                print(self.heights[self.pid][-1], "learn about", p)
                self.heights[p] = h + 1
                    
                
            if updated:
                self.broadcastUpdate()
            return        
        else:
            # pj knows some partitions, let us learn how to contact them
            for p in heights.keys():
                if p != self.pid:
                    if not p in self.heights.keys() or self.heights[p] > heights[p] + 1:
                        self.heights[p] = heights[p] + 1
                        need_broadcast = True

        if heights[pid][0] != self.heights[pid][0]:
            # When node i receives an Update message 
            # from neighboring node j such that lidj != lidi: 
            # if lidi > lidj or (oidi = lidj and ri = 1)
            if (self.heights[pid][0] > heights[pid][0] or 
               (self.heights[pid][2] == heights[pid][2] and self.heights[pid][2] == 1)):
                self.heights[pid] = [heights[pid][0], 0, 0, 0, heights[pid][4]+1, self.heights[pid][-1]]
                need_broadcast = True
            if not sink:
                h = self.heights[pid]  
                if self.update_height(heights[pid][-1]):
                    need_broadcast = True
                else:
                    assert h == self.heights[self.pid]
        
        if need_broadcast:
            self.broadcastUpdate()

             
        
    """
        cause: id of the actor that sended the message 
        that caused the update
        returns wether the height changed or not
    """
    def update_height(self, cause: int) -> bool:
        if not self.is_sink():
            return False
        
        
        rl = self.peer_ref_levels()
        
        if min(rl) != max(rl):
            # not all peers have the same reference level
            # then i sets its reference level to the largest among
            # all its neighbors and sets its delta to one less than the
            # minimum delta value among all neighbors with the largest
            # reference level (a partial reversal). 
            
            ref_level = max(self.peer_ref_levels())
            
            # partial link reversal
            delta = self.heights[self.pid][4]
            for p in self.peer_heights.values():
                if p[1:4] == ref_level:
                    delta = min(delta, p[4] - 1)
            
            self.heights[self.pid][1:4] = ref_level
            self.heights[self.pid][4] = delta
            
        else:
            peers_ref = rl[0]
            if peers_ref[2] == 0: # r == 0
                # unreflected ref level
                # i starts a reflection
                # of this reference level by setting 
                # its reference level to
                # the reflected version of its neighbors' 
                # (with ri = 1) and its delta to 0
                
                self.heights[self.pid][1:4] = [peers_ref[0], peers_ref[1], 1]
                self.heights[self.pid][4] = 0
            elif peers_ref[1] == i: # r == 1, oid == i
                # all of i's neighbors have the same reflected reference
                # level with i as the originator, then i has detected a
                # partition and takes appropriate action. 
                id = self.heights[self.pid][-1]
                self.heights[self.pid] = [id, -1, -1, -1, 0, id]
            else:
                #all of i's neighbors have the same reflected reference
                #level with an originator other than i, then i starts a
                #new reference level. This situation only happens if a
                #link fails while the system is recovering from an earlier
                #link failure. 
                assert 0
        return True


    def init_message(self, actor_id, peers, pid):
        self.heights = {pid: [actor_id, -1, -1, -1, 0, actor_id]}
        self.peers = peers
        self.pid = pid
        
    
    
    def start_message(self):
        print("start")
        self.broadcastUpdate()
        
        
    def getself_message(self):
        return self
        
        

# return actor refs and links
def init_actors(N, p, P, k):
    actorrefs = {i: Actor().start() for i in range(N * k)}
    
    links = {i: [] for i in range(N * k)}
    
    np.random.seed(5)
    
    
    # partitions
    if N > 1:
        for j in range(k):    
            for i in range(N):
                begin = N * j
                others = [l for l in range(begin, begin + N)]
                others.remove(begin + i)
                
                
                added_links = list(np.random.choice(others, p, replace=False))
                
                links[begin + i] += added_links
                for o in added_links:
                    links[o].append(begin + i)
                
    # links between partitions
    if k > 1:
        for pi in range(k):
            part = [i for i in range(N * pi, N * (pi + 1))]
            
            others = [l for l in range(k * N) if l not in part]
            print(others, k, N)
            
            for i in range(P):
                host = np.random.choice(part)
                foreigner = np.random.choice(others)
                
                links[host]      += [foreigner]
                links[foreigner] += [host]
        
            
    
    return actorrefs, links

# N: nodes per partition
# p: conectivity parameter in a partition
# P: conectivity parameter between partitions
# k: number of partitions
N = 4; p = 1; P = 1; k = 3

actor_refs, links = init_actors(N, p, P, k)

# print variance of the number of links per node
print("links per node:", np.var([len(links[i]) for i in range(N * k)]))


actors = [a.ask({"type": "getself"}) for a in actor_refs.values()]



# send set_id message to all actors
for i in range(len(actors)):
    pid = i // N
    
    actor_refs[i].ask({
        "type": "init",
        "actor_id": i,
        "peers": {id: actor_refs[id] for id in links[i]},
        "pid": pid
    })


print(actors)

for a in actor_refs.values():
    a.tell({
        "type": "start",
    })


sleep(2)


for a in actor_refs.values():
    a.stop()


for i in range(len(actors)):
    a = actors[i]
    print(i, a)


import networkx as nx
import matplotlib.pyplot as plt



def draw_graph(actors, links):
    
    G = nx.DiGraph()
    partitions_colors = {
        0: "yellow", 
        1: "cyan",
        2: "lightgreen",
        3: "lightblue",
        4: "red",
        5: "pink",
        6: "yellow",
        6: "cyan",
        7: "lightgreen",
        8: "grey",
        9: "red",
    }
    node_tuples = [0 for _ in range(N * k)]
    
    for (i, a) in enumerate(actors):
        node_tuples[i] = (i, {'color': partitions_colors[a.pid]})
    
    G.add_nodes_from(node_tuples)
    

    
    # add from link list
    for a in actors:
        # heights of neighbors
        
        aid = a.heights[a.pid][-1]
        outgoing = []
        
        inter_part_links = []
        inter_part_h0 = []
        
        draw_parti = 0
        
        
        for i in a.peer_heights.keys():
            pidi = a.peer_pids[i]
            h = a.peer_heights[i][pidi]
            
            if draw_parti in a.peer_heights[i]:
                if pidi == draw_parti:
                    inter_part_h0.append(0)
                else:
                    inter_part_h0.append(a.peer_heights[i][draw_parti])
                
                inter_part_links.append(h[-1])
                
            if pidi == a.pid:
                if h < a.heights[a.pid]:
                    outgoing.append(h)
            else:
                G.add_edge(aid, h[-1], color="blue", weight=1, style="arc3")
                G.add_edge(h[-1], aid, color="blue", weight=1, style="arc3")
                
        
        
        
        if outgoing != []:
            min_link = min(outgoing)
            
            outgoing.remove(min_link)
            
            G.add_edge(aid, min_link[-1], color="red", weight=2, style="arc3")

            for o in outgoing:
                # grey edge
                G.add_edge(aid, o[-1], color="grey", weight=1, style="arc3")
            
        if a.pid != draw_parti and inter_part_links != []:
            #continue
            link = inter_part_links[np.argmin(inter_part_h0)]
            print("LINK", aid, link)
            G.add_edge(aid, link, color="green", weight=3, style="arc3")
            
            
    # pos = nx.kamada_kawai_layout(G)

    edges = G.edges()
    edge_colors = [G[u][v]['color'] for u,v in edges]
    weights = [G[u][v]['weight'] for u,v in edges]
    connectionstyle = [G[u][v]['style'] for u,v in edges]
    
    node_colors = [G.nodes[i]['color'] for i in G.nodes()]
    
    
    
    pos = nx.kamada_kawai_layout(G)
    
    nx.draw(G,
            pos=pos,
            connectionstyle='arc3, rad=0.',
            edge_color=edge_colors, 
            width=weights, 
            with_labels=True, 
            node_size=800, 
            node_color=node_colors, 
            font_color="black"
    )
    
    
    
    
draw_graph(actors, links)

    

plt.show()

