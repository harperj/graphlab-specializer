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
        #try:
        self.vertex_src = inspect.getsource(self.VertexData)
        self.vertex_ast = ast.parse(self.vertex_src.lstrip())
        phase2 = graph_data_frontend.GraphDataFrontEnd().visit(self.vertex_ast)
            
        vertex_data = graph_data_frontend.GraphDataTypeExtractor().visit(phase2)

        #except AttributeError:
        #    print "Warning: Nonexistant or erroneous vertex data node. Skipping."

            
        try:
            self.edge_src = inspect.getsource(self.EdgeData)
            self.edge_ast = ast.parse(self.edge_src.lstrip())
            phase2 = graph_data_frontend.GraphDataFrontEnd().visit(self.edge_ast)
            
            edge_data = graph_data_frontend.GraphDataTypeExtractor().visit(phase2)

        except AttributeError:
            print "Warning: Nonexistant or erroneous edge data node.  Skipping."

        #try:
        self.update_src = inspect.getsource(self.update)
        self.update_ast = ast.parse(self.update_src.lstrip())
        #self.explore_ast(self.update_ast, 0)
        phase2 = graph_frontend.GraphFrontEnd().visit(self.update_ast)
        #self.explore_ast(phase2, 0)

        #Collect gather nodes separately from everything else (which will be apply ops)
        #Filter on phase2.body, since top level of phase2 is a ast.Module node
        gather_nodes = filter(lambda x: type(x) == graph_model.GatherNode, phase2.body[0].body)
        apply_nodes = filter(lambda x: type(x) != graph_model.GatherNode and type(x) != graph_model.ScatterNode and type(x) != graph_model.GatherEdges, 
            phase2.body[0].body)
        gather_edges_node = filter(lambda x: type(x) == graph_model.GatherEdges, phase2.body[0].body)
        scatter_nodes = filter(lambda x: type(x) == graph_model.ScatterNode, phase2.body[0].body)
        apply_nodes = ast.Module(body=apply_nodes)

        graph_src = inspect.getsource(self.__class__)
        graph_ast = ast.parse(graph_src.lstrip())
        # @TODO: Add in parsing for declarations which fall in the Python "class variable" scope
        graph_vars = filter(lambda x: type(x) == ast.Assign, graph_ast.body[0].body)
        graph_vars = map(lambda x: graph_data_frontend.GraphDataFrontEnd().visit(x), graph_vars)

        type_decls = []
        reduce_ops = []
        map_ops = []
        for gn in gather_nodes:
            type_decls.append(
                graph_frontend.GatherTypeDeclConvert(vertex_data, edge_data).visit(gn)
            )
            reduce_ops.append(
                graph_frontend.GatherReduceOpConvert().visit(gn)
            )
            map_ops.append(
                graph_frontend.GatherMapOpConvert(vertex_data, edge_data).visit(gn)
            )

        scatter_ops = []
        for sn in scatter_nodes:
            scatter_ops.append(
                graph_frontend.ScatterOpConvert().visit(sn)
            )

        gather_edges_node = graph_frontend.GatherEdgesConvert().visit(gather_edges_node[0])
        #We want to collect the gather_vars to pass to the Apply op conversion object
        #  apply operations must recognize gather vars, and address them in the "sum"
        #  gather_type object.
        gather_vars = reduce(lambda x, y: [x, y],
            map(lambda x: x.total_var.name, gather_nodes) 
            )   

        #self.explore_ast(apply_nodes, 0)
        apply_nodes_converted = graph_frontend.ApplyConvert(gather_vars, vertex_data, edge_data).visit(apply_nodes)

        import asp.codegen.templating.template as template
        gather_type = template.Template(filename="pagerank.mako")
        gather_type = gather_type.render(gather_decls = type_decls, gather_add = reduce_ops, map_body=map_ops, 
            vertex_mods=apply_nodes_converted, scatter_ops=scatter_ops, vertex_data=to_bunch(vertex_data), edge_data=to_bunch(edge_data),
            graph_vars=graph_vars, gather_edges_node=gather_edges_node)
        print gather_type

    class Vertex(object):
        pass

    class Edge(object):
        pass

    def map_reduce(self, map_func, reduce_func, iter):
        return reduce(reduce_func, map(map_func, iter))

    def explore_ast(self, node, depth):
        print ' '*depth, node
        for n in ast.iter_child_nodes(node):
            self.explore_ast(n, depth+1) 

class double(object):
    #Placeholder class for the double datatype
    def __init__(self, value):
        self.value = value

class float(object):
    #placeholder class for the float datatype
    def __init__(self, value):
        self.value = value

class Bunch(dict):
    def __init__(self, d):
        dict.__init__(self, d)
        self.__dict__.update(d)

def to_bunch(d):
    r = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v = to_bunch(v)
        r[k] = v
    return Bunch(r)
