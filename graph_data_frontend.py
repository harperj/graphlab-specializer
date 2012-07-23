from graph_data_model import *
import ast
from asp.util import *
import asp.codegen.ast_tools as ast_tools

class GraphDataFrontEnd(ast_tools.NodeTransformer):
    def visit_ClassDef(self, node):
        body = map(self.visit, node.body)
        if node.name == "VertexData":
            return VertexType(body[0])

        if node.name == "EdgeData":
            return EdgeType(body[0])

    def visit_FunctionDef(self, node):
        if node.name == '__init__':
            return map(self.visit, node.body)
        else:
            return None

    def visit_Assign(self, node):
        my_type = node.value.func.attr
        assert node.value.func.value.id == 'gl'
        initial_value = ast.literal_eval(node.value.args[0])
        return TypeDecl(node.targets[0].attr, my_type, Value(initial_value))

    def visit_Module(self, node):
        #Body length should only be 1, since this is just a ClassDef
        assert len(node.body) == 1

        return self.visit(node.body[0])


class GraphDataTypeExtractor(ast_tools.NodeVisitor):
    def visit_TypeDecl(self, node):
        if hasattr(self, 'dtypes'):
            self.dtypes[node.name] = node.type
        else:
            self.dtypes = { node.name: node.type } 
    
