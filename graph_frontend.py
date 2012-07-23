from graph_model import *
import ast
from asp.util import *
import asp.codegen.ast_tools as ast_tools
import cgen

class GraphFrontEnd(ast_tools.NodeTransformer):
    def visit_FunctionDef(self, node):
        visited_body = map(self.visit, node.body)
        
        return GraphUpdate(map(self.visit, node.body))
    def visit_Assign(self, node):
        if type(node.value) == ast.Call and node.value.func.id == 'map_reduce':
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

    def visit_Attribute(self, node):
        child = None
        if isinstance(node.value, ast.Name):
            child = Accessor([Identifier(node.value.id)])
        else:
            child = self.visit(node.value)
        child.names.append(Identifier(node.attr))
        print "Visiting attribute ", node.attr
        return child
 
    def visit_Call(self, node):
        child = self.visit(node.func)
        child.names[-1].name += "()"
        #print "Visiting call.  Child ", child[-1].name, "'s call set to: ", child[-1].call
        return child

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
    def visit_GatherNode(self, node):
        self.anon_var = node.map.var.name
        return self.visit(node.map.body)
    def visit_Accessor(self, node):
        node.names = map(lambda x: x if self.anon_var != x.name else Identifier('edge'), node.names)
        node_str = reduce(lambda x, y: Identifier(x.name+"."+y.name), node.names)
        return node_str.name

class ApplyConvert(ast_tools.ConvertAST):
    def __init__(self, gather_vars):
        self.gather_vars = gather_vars
        super(ApplyConvert, self).__init__()



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
