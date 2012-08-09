import types
import ast
from asp.tree_grammar import *

parse('''
GraphUpdate(body=(GatherNode|ast.Assign|ast.If|GatherEdges|ScatterNode)*)

GatherNode(total_var=Identifier, map=GatherMap, reduce=GatherReduce)

GatherEdges(condition=ast.If)

GatherMap(var=Identifier, body=(Accessor|ast.BinOp))

GatherReduce(var1=Identifier, var2=Identifier, body=ast.BinOp)

ScatterNode(anon_var=Identifier, body=(Accessor|Identifier))

Accessor(values=(Identifier|GraphCall)* )

GraphCall(name, args=(Accessor|Identifier|ast.BinOp)*)

Identifier(name)

Constant(value = (types.IntType | types.LongType | types.FloatType))

''', globals(), checker='GraphModelChecker')
