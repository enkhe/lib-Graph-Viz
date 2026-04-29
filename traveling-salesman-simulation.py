import streamlit as st
import random
from graphviz import Digraph
import io
from itertools import permutations
from functools import lru_cache

class Node:
    def __init__(self, name):
        self.name = name

class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}

    def add_node(self, name):
        self.nodes[name] = Node(name)

    def add_edge(self, start, end, weight):
        if start not in self.edges:
            self.edges[start] = {}
        self.edges[start][end] = weight
        if end not in self.edges:
            self.edges[end] = {}
        self.edges[end][start] = weight  # Make the graph undirected

    def get_graphviz(self, bg_color, box_color, node_color, edge_color, path_color, zoom_level, path=None):
        dot = Digraph(comment='Traveling Salesman Problem Visualization')
        dot.attr(engine='neato')
        
        width, height = 22 * zoom_level, 17 * zoom_level
        size = f"{width},{height}"
        dot.attr(rankdir='LR', bgcolor=bg_color, size=size, dpi="60")
        
        with dot.subgraph(name='cluster_bg') as c:
            c.attr(style='filled,rounded', color=box_color, fillcolor=box_color, penwidth='2')
            c.attr(label='', fontcolor="#00000000")

        node_size = max(0.3, 0.8 / zoom_level)
        dot.attr('node', shape='circle', style='filled', fontcolor='black', fontname='Arial', 
                 fontsize=str(max(10, int(20 / zoom_level))), width=str(node_size), height=str(node_size), fixedsize='true')
        
        edge_len = max(1.0, 2.0 * zoom_level)
        dot.attr('edge', fontname='Arial', fontsize=str(max(8, int(16 / zoom_level))), len=str(edge_len))

        for name in self.nodes:
            dot.node(name, name, fillcolor=node_color)

        for start, ends in self.edges.items():
            for end, weight in ends.items():
                if path and start in path and end in path and (path.index(end) == path.index(start) + 1 or path.index(start) == path.index(end) + 1):
                    dot.edge(start, end, label=str(weight), color=path_color, penwidth='3', dir='both')
                else:
                    dot.edge(start, end, label=str(weight), color=edge_color, penwidth='2', dir='both')

        return dot

    def get_mermaid(self, path=None):
        mermaid_code = ["graph LR"]
        for start, ends in self.edges.items():
            for end, weight in ends.items():
                if path and start in path and end in path and (path.index(end) == path.index(start) + 1 or path.index(start) == path.index(end) + 1):
                    mermaid_code.append(f"    {start}-->{end}")
                    mermaid_code.append(f"    style {start} fill:#ff0000")
                    mermaid_code.append(f"    style {end} fill:#ff0000")
                else:
                    mermaid_code.append(f"    {start}--{weight}-->{end}")
        return "\n".join(mermaid_code)

    def nearest_neighbor_tsp(self, start):
        unvisited = set(self.nodes.keys())
        path = [start]
        unvisited.remove(start)
        total_distance = 0

        while unvisited:
            nearest = min(unvisited, key=lambda x: self.edges[path[-1]].get(x, float('inf')))
            path.append(nearest)
            total_distance += self.edges[path[-2]][nearest]
            unvisited.remove(nearest)

        # Return to start
        path.append(start)
        total_distance += self.edges[path[-2]][start]

        return path, total_distance

    def brute_force_tsp(self, start):
        """Optimal TSP via exhaustive search. O(n!)."""
        others = [n for n in self.nodes if n != start]
        best_path, best_dist = None, float('inf')
        for perm in permutations(others):
            route = [start, *perm, start]
            dist = sum(self.edges[route[i]][route[i + 1]] for i in range(len(route) - 1))
            if dist < best_dist:
                best_dist, best_path = dist, route
        return best_path, best_dist

    def held_karp_tsp(self, start):
        """Optimal TSP via Held-Karp dynamic programming. O(n^2 * 2^n)."""
        nodes = list(self.nodes.keys())
        idx = {n: i for i, n in enumerate(nodes)}
        n = len(nodes)
        s = idx[start]
        dist = [[self.edges[nodes[i]].get(nodes[j], float('inf')) for j in range(n)] for i in range(n)]

        # dp[(mask, i)] = (cost, prev) for minimum cost path visiting nodes in mask, ending at i
        dp = {(1 << s, s): (0, None)}
        for mask in range(1 << n):
            if not (mask & (1 << s)):
                continue
            for i in range(n):
                if not (mask & (1 << i)) or (mask, i) not in dp:
                    continue
                cost_i, _ = dp[(mask, i)]
                for j in range(n):
                    if mask & (1 << j):
                        continue
                    new_mask = mask | (1 << j)
                    new_cost = cost_i + dist[i][j]
                    if (new_mask, j) not in dp or new_cost < dp[(new_mask, j)][0]:
                        dp[(new_mask, j)] = (new_cost, i)

        full = (1 << n) - 1
        best_end, best_cost = None, float('inf')
        for i in range(n):
            if i == s or (full, i) not in dp:
                continue
            total = dp[(full, i)][0] + dist[i][s]
            if total < best_cost:
                best_cost, best_end = total, i

        # Reconstruct path
        path_idx = []
        mask, cur = full, best_end
        while cur is not None:
            path_idx.append(cur)
            _, prev = dp[(mask, cur)]
            mask ^= (1 << cur)
            cur = prev
        path_idx.reverse()
        path = [nodes[i] for i in path_idx] + [start]
        return path, best_cost

def create_random_graph(num_nodes, max_weight):
    graph = Graph()
    nodes = [chr(65 + i) for i in range(num_nodes)]
    for node in nodes:
        graph.add_node(node)
    
    for i in range(num_nodes):
        for j in range(i+1, num_nodes):
            weight = random.randint(1, max_weight)
            graph.add_edge(nodes[i], nodes[j], weight)
    
    return graph

def main():
    st.title("Traveling Salesman Problem Simulation")

    st.sidebar.header("Graph Settings")
    num_nodes = st.sidebar.slider("Number of Nodes", 3, 10, 6)
    max_weight = st.sidebar.slider("Maximum Edge Weight", 1, 10, 5)
    zoom_level = st.sidebar.slider("Zoom Level", 0.5, 3.0, 1.0, 0.1)

    st.sidebar.header("Color Settings")
    bg_color = st.sidebar.color_picker("Background Color", "#FFFFFF")
    box_color = st.sidebar.color_picker("Box Color", "#E0E0E0")
    node_color = st.sidebar.color_picker("Node Color", "#e6f3ff")
    edge_color = st.sidebar.color_picker("Edge Color", "#A9A9A9")
    path_color = st.sidebar.color_picker("TSP Path Color", "#FF6347")

    if 'graph' not in st.session_state or st.session_state.num_nodes != num_nodes:
        st.session_state.graph = create_random_graph(num_nodes, max_weight)
        st.session_state.num_nodes = num_nodes

    if st.sidebar.button("Generate New Graph"):
        st.session_state.graph = create_random_graph(num_nodes, max_weight)

    graph = st.session_state.graph
    nodes = list(graph.nodes.keys())

    st.sidebar.header("Traveling Salesman Problem")
    start_node = st.sidebar.selectbox("Starting Node", nodes)
    algorithm = st.sidebar.selectbox(
        "Algorithm",
        ["Nearest Neighbor (heuristic)", "Brute Force (optimal)", "Held-Karp DP (optimal)"],
    )

    if st.sidebar.button("Find TSP Path"):
        if algorithm.startswith("Nearest"):
            path, total_distance = graph.nearest_neighbor_tsp(start_node)
        elif algorithm.startswith("Brute"):
            if num_nodes > 9:
                st.sidebar.warning("Brute force is slow for >9 nodes. Consider Held-Karp.")
            path, total_distance = graph.brute_force_tsp(start_node)
        else:
            path, total_distance = graph.held_karp_tsp(start_node)
        st.session_state.path = path
        st.session_state.total_distance = total_distance
        st.sidebar.success(f"TSP Path: {' -> '.join(path)}")
        st.sidebar.info(f"Total Distance: {total_distance}")
    else:
        st.session_state.path = []
        st.session_state.total_distance = 0

    dot = graph.get_graphviz(bg_color, box_color, node_color, edge_color, path_color, zoom_level, st.session_state.path)

    png_data = dot.pipe(format='png')
    st.image(png_data, caption="Traveling Salesman Problem Graph", width='stretch')

    st.download_button(
        label="Download Graph as PNG",
        data=png_data,
        file_name="tsp_graph.png",
        mime="image/png"
    )

    tab1, tab2 = st.tabs(["Graphviz DOT", "Mermaid"])

    with tab1:
        st.subheader("Graphviz DOT Code")
        st.code(dot.source)

    with tab2:
        st.subheader("Mermaid Graph")
        mermaid_code = graph.get_mermaid(st.session_state.path)
        st.code(mermaid_code, language="mermaid")

if __name__ == "__main__":
    main()
