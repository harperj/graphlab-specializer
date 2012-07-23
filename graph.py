import inspect
import asp.codegen.python_ast as ast
import asp.codegen.cpp_ast as cpp_ast
import asp.codegen.ast_tools as ast_tools
import cgen
import asp.jit.asp_module as asp_module
import graph_frontend
import graph_data_frontend
import graph_model

class Graph(object):
    def __init__(self):
        vertex_data = { }
        edge_data = { }
        try:
            self.vertex_src = inspect.getsource(self.VertexData)
            self.vertex_ast = ast.parse(self.vertex_src.lstrip())
            phase2 = graph_data_frontend.GraphDataFrontEnd().visit(self.vertex_ast)
            vertex_data = graph_data_frontend.GraphDataTypeExtractor()
            vertex_data.visit(phase2)
            vertex_data = vertex_data.dtypes
        except AttributeError:
            print "Warning: Nonexistant or erroneous vertex data node. Skipping."

            
        try:
            self.edge_src = inspect.getsource(self.EdgeData)
            self.edge_ast = ast.parse(self.edge_src.lstrip())
            phase2 = graph_data_frontend.GraphDataFrontEnd().visit(self.edge_ast)
            edge_data = graph_data_frontend.GraphDataTypeExtractor()
            edge_data.visit(phase2)
            edge_data = edge_data.dtypes

        except AttributeError:
            print "Warning: Nonexistant or erroneous edge data node.  Skipping."

        #try:
        self.update_src = inspect.getsource(self.update)
        self.update_ast = ast.parse(self.update_src.lstrip())
        self.explore_ast(self.update_ast, 0)
        phase2 = graph_frontend.GraphFrontEnd().visit(self.update_ast)
        self.explore_ast(phase2, 0)

        #Collect gather nodes separately from everything else (which will be apply ops)
        #Filter on phase2.body, since top level of phase2 is a ast.Module node
        gather_nodes = filter(lambda x: type(x) == graph_model.GatherNode, phase2.body[0].body)
        apply_nodes = filter(lambda x: type(x) != graph_model.GatherNode, phase2.body[0].body)

        for gn in gather_nodes:
            type_decl = graph_frontend.GatherTypeDeclConvert(vertex_data, edge_data).visit(gn)
            reduce_op = graph_frontend.GatherReduceOpConvert().visit(gn)
            map_op = graph_frontend.GatherMapOpConvert().visit(gn)
            print map_op


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
            self.val = gl.double(3.0)
            self.val2 = gl.string("hello")

    class EdgeData(Graph.Edge):
        def __init__(self):
            self.edge_val = gl.double(1.0)

    def update(self, vertex, neighborhood):
        s = map_reduce(lambda x: (1.0 / x.source().num_out_edges()) * x.source().val, lambda x, y: x+y, neighborhood.in_edges())
        vertex.val = s


TestGraph()
