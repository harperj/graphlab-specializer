from graph_model import *
import ast
from asp.util import *
import asp.codegen.ast_tools as ast_tools

class GraphFrontEnd(ast_tools.NodeTransformer):
    def visit_Assign(self, node):
        my_type = node.value.func.attr
        assert node.value.func.value.id == 'np'
        initial_value = ast.literal_eval(node.value.args[0])
        return VarDecl(Identifier(node.targets[0].id), my_type, Constant(initial_value))

    def visit_For(self, node):
        if(type(node.iter) is ast.Call and
           type(node.iter.func) is ast.Attribute):
            print node.iter.func.attr
            print node.target.id
            visited_body = map(self.visit, node.body)
            for subnode in visited_body:
                assert type(subnode) == AccumOp
                

    def visit_AugAssign(self, node):
        print node.op
        print node.target
        print node.value
