import graph as gl

class PageRankGraph(gl.Graph):
    RESET_PROB = gl.double(0.15)
    TOLERANCE = gl.double(0.01)
    last_change = gl.double(0.0)

    class VertexData(gl.Graph.Vertex):
        def __init__(self):
            self.val = gl.double(3.0)

    class EdgeData(gl.Graph.Edge):
        pass

    def update(self, vertex, neighborhood):
        s = self.map_reduce(lambda x: ((1.0 - RESET_PROB) / x.source().num_out_edges()) * x.source().val, 
                            lambda x, y: x+y, 
                            neighborhood.in_edges())
        last_change = abs(s + RESET_PROB - vertex.val)
        vertex.val = s
        if last_change > TOLERANCE:
            map(lambda x: self.signal(x.target()), neighborhood.out_edges())


PageRankGraph()