import inspect
import asp.codegen.python_ast as ast
import asp.codegen.cpp_ast as cpp_ast
import asp.codegen.ast_tools as ast_tools
import cgen
import asp.jit.asp_module as asp_module
import graph_frontend
import graph_data_frontend

class Graph(object):
    def __init__(self):
        try:
            self.vertex_src = inspect.getsource(self.VertexData)
            self.vertex_ast = ast.parse(self.vertex_src.lstrip())
            phase2 = graph_data_frontend.GraphDataFrontEnd().visit(self.vertex_ast)
        except AttributeError:
            print "Warning: Nonexistant or erroneous vertex data node. Skipping."


            
        try:
            self.edge_src = inspect.getsource(self.EdgeData)
            self.edge_ast = ast.parse(self.edge_src.lstrip())
            phase2 = graph_data_frontend.GraphDataFrontEnd().visit(self.edge_ast)
        except AttributeError:
            print "Warning: Nonexistant or erroneous edge data node.  Skipping."

        #try:
        self.update_src = inspect.getsource(self.update)
        self.update_ast = ast.parse(self.update_src.lstrip())
        self.explore_ast(self.update_ast, 0)
        phase2 = graph_frontend.GraphFrontEnd().visit(self.update_ast)
        #except AttributeError:
        #    print "Warning: Nonexistant or erroneous update function.  Skipping."

    class Vertex(object):
        pass

    class Edge(object):
        pass


    def explore_ast(self, node, depth):
        print ' '*depth, node
        for n in ast.iter_child_nodes(node):
            self.explore_ast(n, depth+1) 

class TestGraph(Graph):
    class VertexData(Graph.Vertex):
        def __init__(self):
            self.val = np.double(3.0)
            self.val2 = np.string("hello")

    class EdgeData(Graph.Edge):
        def __init__(self):
            self.edge_val = np.double(1.0)

    def update(self, vertex, neighborhood):
        accum = np.double(0.0)
        for edge in neighborhood.in_edges():
            accum += (edge.source.val - 1) / 3


TestGraph()
