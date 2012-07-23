struct gather_type : public graphlab::IS_POD_TYPE {
% for gd in gather_decls:
  ${gd}
%endfor
  gather_type& operator+=(gather_type& other) {
% for ga in gather_add:
    ${ga}
% endfor
  }

  gather_type() { }

  gather_type(
%for gd in gather_decls:
    ${gd.typename} ${gd.name}
% if not loop.last:
,
% endif
% endfor
  ) 
  {
%for gd in gather_decls:
    this->${gd.name} = ${gd.name};
%endfor
    return *this;
  }
}

typedef graphlab::distributed_graph<vertex_data_type, edge_data_type> graph_type;

class grab_lab :
  public graphlab::ivertex_program<graph_type, gather_type>,
  public graphlab::IS_POD_TYPE
{
public:
  void init(icontext_type& context, vertex_type& vertex) { }
  gather_type gather(icontext_type& context, const vertex_type& vertex, edge_type& edge) const
  {
    return gather_type(
    %for mb in map_body:
      ${mb}
    %endfor
    )
  }

  void apply(icontext_type& context, vertex_type& vertex, const gather_type& total)
  {
  %for vm in vertex_mods:
    ${vm}
  %endfor
  }
}