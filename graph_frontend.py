from graph_model import *
import ast
from asp.util import *
import asp.codegen.ast_tools as ast_tools
import cgen

class GraphFrontEnd(ast_tools.NodeTransformer):
    def visit_FunctionDef(self, node):
        visited_body = []
        for child in node.body:
            new_node = self.visit(child)
            if type(new_node) == list:
                for nn in new_node:
                    visited_body.append(nn)
            else:
                visited_body.append(new_node)

        return GraphUpdate(visited_body)

    def visit_Assign(self, node):
        if type(node.value) == ast.Call \
           and type(node.value.func) == ast.Attribute \
           and node.value.func.attr == 'map_reduce':
            assert type(node.value.args[0]) == ast.Lambda
            assert type(node.value.args[1]) == ast.Lambda
            # node.targets[0].id == lhs name
            #print dir(node.value)
            #print node.value.func.id
            #print node.value.args
            map_func = node.value.args[0]
            reduce_func = node.value.args[1]
            collection = node.value.args[2]
            
            map_var = map_func.args.args[0].id
            map_body = self.visit(map_func.body)
            if type(map_body) == list:
                map_body = map(lambda x: Identifier(x), map_body)
                map_body = Accessor(map_body)
            gather_map = GatherMap(Identifier(map_var), map_body)
            
            reduce_var1 = Identifier(reduce_func.args.args[0].id)
            reduce_var2 = Identifier(reduce_func.args.args[1].id)
            reduce_body = self.visit(reduce_func.body)
            gather_reduce = GatherReduce(reduce_var1, reduce_var2, reduce_body)
            return GatherNode(Identifier(node.targets[0].id), gather_map, gather_reduce)
        else: 
            return self.generic_visit(node)

    def visit_Expr(self, node):
        return self.visit(node.value) 

    def visit_Call(self, node):
        #print "Visited call"
        if type(node.func) == ast.Name \
           and node.func.id == 'map':
            assert len(node.args) == 2
            assert type(node.args[0]) == ast.Lambda
            return ScatterNode(Identifier(node.args[0].args.args[0].id), self.visit(node.args[0].body))
        elif type(node.func) == ast.Name \
             and node.func.id == 'abs':
             node.func.id = 'std::fabs'

        func = self.visit(node.func)
        args = map(self.visit, node.args)
        #print args
        if type(func) == Identifier:
            new_node = GraphCall(func.name, args)
            return Accessor([new_node])
        elif type(func) == Accessor:
            func.values[-1] = GraphCall(func.values[-1].name, args)
            return func

    def visit_If(self, node):
        #Special case: If statement on scatter
        #print "ENCOUNTERED IF"
        #print len(node.body), " ", self.visit(node.body[0].value)
        #print dir(node.body[0])
        if (len(node.body) == 1 
            and type(self.visit(node.body[0].value)) == ScatterNode):
            #Scatter_edges
            return [self.visit(node.body[0]), GatherEdges(node)]
        return self.generic_visit(node)
            
    def visit_Attribute(self, node):
        value = self.visit(node.value)
        #print value
        if type(value) == Identifier:
            return Accessor([value, Identifier(node.attr)])
        elif type(value) == Accessor:
            return Accessor(value.values + [Identifier(node.attr)])

    def visit_Name(self, node):
        return Identifier(node.id)


class GatherTypeDeclConvert(ast_tools.ConvertAST):                      
    def __init__(self, vertex_data, edge_data):
        self.vertex_data = vertex_data
        self.edge_data = edge_data
        super(GatherTypeDeclConvert, self).__init__()

    def visit_GatherNode(self, node):
        return cgen.Value(self.visit(node.map), node.total_var.name)

    def visit_GatherMap(self, node):
        return self.checkType(node.body)

    def checkType(self, acc_node, is_vertex=False):
        #First we'll want to check if this is a vertex or edge member
        if isinstance(acc_node, Accessor) and type(acc_node.values[-1]) != GraphCall:
            if acc_node.values[1].name == "source()" or acc_node.values[1].name == "source":
                return self.vertex_data[acc_node.values[2].name]
            else:
                return self.edge_data[acc_node.values[1].name]

        elif isinstance(acc_node, ast.BinOp):
            res = self.checkType(acc_node.left, is_vertex)
            if res == None:
                return self.checkType(acc_node.right, is_vertex)
            return res
        else:
            return None

class GatherReduceOpConvert(ast_tools.ConvertAST):
    def visit_GatherNode(self, node):
        self.total_var = node.total_var
        self.var1 = node.reduce.var1
        self.var2 = node.reduce.var2
        return cgen.Statement(self.visit(node.reduce.body))

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        if isinstance(node.op, ast.Add) and left == self.total_var.name:
                return self.visit(node.left) + "+=" + self.visit(node.right)                
        return "(" + str(self.visit(node.left)) + self.visit(node.op) + str(self.visit(node.right)) + ")"

    def visit_Identifier(self, node):
        if node.name == self.var1.name:
            return self.total_var.name
        elif node.name == self.var2.name:
            return "other." + self.total_var.name
        else:
            return node.name

    def visit_Accessor(self, node):
        return reduce(lambda x, y: Identifier(self.visit(x)+"."+self.visit(y)), node.names)



class GatherMapOpConvert(ast_tools.ConvertAST):
    def __init__(self, vertex_data, edge_data):
        self.vertex_data = vertex_data
        self.edge_data = edge_data
        super(GatherMapOpConvert, self)

    def visit_GatherNode(self, node):
        self.anon_var = node.map.var.name
        return self.visit(node.map.body)

    def visit_Accessor(self, node):
        node.values = map(lambda x: x if self.anon_var != x.name else Identifier('edge'), node.values)
        node_str = reduce(lambda x, y: self.visit(x)+"."+self.visit(y), node.values)
        return node_str

    def visit_Identifier(self, node):
        if node.name in self.vertex_data or node.name in self.edge_data:
            return "data()." + node.name
        return node.name

    def visit_GraphCall(self, node):
        node.name += "("
        if len(node.args) > 0:
            arg_string = reduce(lambda x, y: self.visit(x)+","+self.visit(y), node.args)
            node.name += arg_string
        node.name += ")"
        return node.name

    def visit_str(self, node):
        return node

class GatherEdgesConvert(ast_tools.ConvertAST):
    def visit_GatherEdges(self, node):
        return_decl = cgen.If(self.visit(node.condition.test), cgen.Statement("return graphlab::ALL_EDGES"), 
            cgen.Statement("return graphlab::NO_EDGES"))
        return return_decl

class ApplyConvert(ast_tools.ConvertAST):
    def __init__(self, gather_vars, vertex_data, edge_data):
        self.gather_vars = gather_vars
        self.vertex_data = vertex_data
        self.edge_data = edge_data
        super(ApplyConvert, self).__init__()

    def visit_Module(self, node):
        return map(self.visit, node.body)

    def visit_Assign(self, node):
        return cgen.Statement(self.visit(node.targets[0]) + " = " + self.visit(node.value))

    def visit_BinOp(self, node):
        #print "binop ", node.left, " ", node.op, " ", node.right
        return "(" + str(self.visit(node.left)) + self.visit(node.op) + str(self.visit(node.right)) + ")"


    def visit_Accessor(self, node):
        node_str = ".".join([self.visit(x) for x in node.values])
        return node_str

    def visit_GraphCall(self, node):
        node_name = ""
        if node.name in self.gather_vars:
            node_name = "total." + node.name
        else: 
            node_name = node.name
        node_name += "("
        node_name += ",".join([self.visit(x) for x in node.args])
        node_name += ")"
        return node_name

    def visit_Identifier(self, node):
        if node.name in self.gather_vars:
            return "total." + node.name
        if node.name in self.vertex_data or node.name in self.edge_data:
            return "data()." + node.name
        return node.name

    def visit_str(self, node):
        return node

class ScatterOpConvert(ast_tools.ConvertAST):
    def visit_ScatterNode(self, node):
        self.anon_var = node.anon_var
        return cgen.Statement(self.visit(node.body))

    def visit_Accessor(self, node):
        #node_str = reduce(lambda x, y: self.visit(x)+"."+self.visit(y), node.values, self.visit(node.values[0]))
        node_str = ".".join([self.visit(x) for x in node.values])
        return node_str

    def visit_GraphCall(self, node):
        node_name = node.name
        node_name += "("
        if len(node.args) > 1:
            #arg_string = reduce(lambda x, y: self.visit(x)+","+self.visit(y), node.args)
            arg_string = ",".join([self.visit(x) for x in node.args])
            node_name += arg_string
        elif len(node.args) == 1:
            node_name += self.visit(node.args[0])
        node_name += ")"
        return node_name

    def visit_Identifier(self, node):
        if node.name == self.anon_var.name:
            return "edge"
        elif node.name == "self":
            return "context"
        return node.name

    def visit_str(self, node):
        return node

class GraphConvert(ast_tools.ConvertAST):
    def __init__(self, vertex_data, edge_data):
        self.vertex_data = vertex_data
        self.edge_data = edge_data
        super(GraphConvert, self).__init__()

    def visit_GraphUpdate(self, node):
        #Generate gather_type
        gather_nodes = filter(lambda x: type(x) == GatherNode, node.body)
        vertex_mods = filter(lambda x: type(x) != GatherNode, node.body)
        gather_decls = []

        #First generate type declarations
        for gn in gather_nodes:
            #map will operate on edges, unless edge.source() is called
            my_type = self.checkType(gn.map.body)
            gather_decls.append(cgen.Value(my_type, gn.total_var.name))

        gather_add = []
        #Next generate operator+= content
        for gn in gather_nodes:
            self.curr_gather = gn
            self.is_reduce = True
            gather_add.append(cgen.Statement(self.visit(gn.reduce.body)))

        #Now generate gather() code from map
        map_stmts = []
        for gn in gather_nodes:
            self.curr_gather = gn
            self.is_reduce = False
            my_map = self.visit(gn.map.body)
            map_stmts.append(my_map)

        vertex_mod_strings = []
        for vm in vertex_mods:
            vertex_mod_strings.append(cgen.Statement(self.visit(vm)))

        import asp.codegen.templating.template as template
        gather_type = template.Template(filename="pagerank.mako")
        gather_type = gather_type.render(gather_decls = gather_decls, gather_add = gather_add, map_body=map_stmts, vertex_mods=vertex_mod_strings)
        print gather_type

    def visit_Assign(self, node):
        return self.visit(node.targets[0]) + "=" + self.visit(node.value)



    def visit_BinOp(self, node):
        left = self.visit(node.left)
        if self.is_reduce and isinstance(node.op, ast.Add) and left == self.curr_gather.total_var.name:
                return self.visit(node.left) + "+=" + self.visit(node.right)                
        return "(" + str(self.visit(node.left)) + self.visit(node.op) + str(self.visit(node.right)) + ")"


    def visit_Num(self, node):
        return str(node.n)

    def visit_Identifier(self, node):
        if node.name == self.curr_gather.reduce.var1.name:
            return self.curr_gather.total_var.name
        elif node.name == self.curr_gather.reduce.var2.name:
            return "other." + self.curr_gather.total_var.name
        else:
            return node.name


    def visit_Accessor(self, node):
        if not self.is_reduce:
                node.names = map(lambda x: x if self.curr_gather.map.var.name != x.name else Identifier('edge'), node.names)
        node_str = reduce(lambda x, y: Identifier(x.name+"."+y.name), node.names)
        return node_str.name


    def checkType(self, acc_node):
        #First we'll want to check if this is a vertex or edge member
        if isinstance(acc_node, Accessor) and acc_node.names[-1].name[-2:] != "()":
            if acc_node.names[1].name == "source()" or acc_node.names[1].name == "source":
                return self.vertex_data[acc_node.names[2].name]
            else:
                return self.edge_data[acc_node.names[1].name]
        elif isinstance(acc_node, ast.BinOp):
            res = self.checkType(acc_node.left)
            if res == None:
                return self.checkType(acc_node.right)
            return res
        else:
            return None
