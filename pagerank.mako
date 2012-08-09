/*
 * Copyright (c) 2009 Carnegie Mellon University.
 *     All rights reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing,
 *  software distributed under the License is distributed on an "AS
 *  IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 *  express or implied.  See the License for the specific language
 *  governing permissions and limitations under the License.
 *
 * For more about this software visit:
 *
 *      http://www.graphlab.ml.cmu.edu
 *
 */

#include <vector>
#include <string>
#include <fstream>

#include <graphlab.hpp>
// #include <graphlab/macros_def.hpp>


struct vertex_data : public graphlab::IS_POD_TYPE {
  %for key in vertex_data.keys():
  ${vertex_data[key]} ${key};
  %endfor
};

%if len(edge_data) > 0:
struct edge_data : public graphlab::IS_POD_TYPE {
  %for key in edge_data.keys():
  ${edge_data[key]} ${key};
  %endfor
};
%else:
typedef graphlab::empty edge_data;
%endif

typedef graphlab::distributed_graph<vertex_data, edge_data> graph_type;

struct gather_type : public graphlab::IS_POD_TYPE {
% for gd in gather_decls:
  ${gd}
%endfor
  gather_type& operator+=(const gather_type& other) {
% for ga in gather_add:
    ${ga}
% endfor
return *this;
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
  }
};

class graph_lab :
  public graphlab::ivertex_program<graph_type, gather_type>,
  public graphlab::IS_POD_TYPE
{
  %for graph_var in graph_vars:
  ${graph_var.type} ${graph_var.name} = ${graph_var.initialValue};
  %endfor
public:
  void init(icontext_type& context, vertex_type& vertex) { 
  }
  gather_type gather(icontext_type& context, const vertex_type& vertex, edge_type& edge) const
  {
    return gather_type(
    %for mb in map_body:
      ${mb}
    %endfor
    );
  }

  void apply(icontext_type& context, vertex_type& vertex, const gather_type& total)
  {
  %for vm in vertex_mods:
    ${vm}
  %endfor
  }

  edge_dir_type scatter_edges(icontext_type& context,
                              const vertex_type& vertex) const {
    ${gather_edges_node}
    //if (last_change > TOLERANCE) return graphlab::OUT_EDGES;
    //else return graphlab::NO_EDGES;
  }

  void scatter(icontext_type& context, const vertex_type& vertex,
               edge_type& edge) const 
  {
  %for so in scatter_ops:
    ${so}
  %endfor
  }
};



/*
 * We want to save the final graph so we define a write which will be
 * used in graph.save("path/prefix", pagerank_writer()) to save the graph.
 */
struct pagerank_writer {
  std::string save_vertex(graph_type::vertex_type v) {
    std::stringstream strm;
    strm << v.id() << "\t";
    %for vertex_datum in vertex_data:
    strm << v.data().${vertex_datum} << "\t";
    %endfor
    strm << "\n";
    return strm.str();
  }
  std::string save_edge(graph_type::edge_type e) {
    std::stringstream strm;
    strm << e.id() << "\t";
    %for edge_datum in edge_data:
    strm << e.data().${edge_datum} << "\t";
    %endfor
    strm << "\n";
    return strm.str();
  }
}; // end of pagerank writer


int main(int argc, char** argv) {
  // Initialize control plain using mpi
  graphlab::mpi_tools::init(argc, argv);
  graphlab::distributed_control dc;
  global_logger().set_log_level(LOG_INFO);

  // Parse command line options -----------------------------------------------
  graphlab::command_line_options clopts("PageRank algorithm.");
  std::string graph_dir;
  std::string format = "adj";
  std::string exec_type = "synchronous";
  clopts.attach_option("graph", graph_dir,
                       "The graph file. Required ");
  clopts.add_positional("graph");
  clopts.attach_option("format", format,
                       "The graph file format");
  clopts.attach_option("engine", exec_type, 
                       "The engine type synchronous or asynchronous");
  //clopts.attach_option("tol", TOLERANCE,
  //                     "The permissible change at convergence.");
  std::string saveprefix;
  clopts.attach_option("saveprefix", saveprefix,
                       "If set, will save the resultant output to a "
                       "sequence of files with prefix saveprefix");

  if(!clopts.parse(argc, argv)) {
    dc.cout() << "Error in parsing command line arguments." << std::endl;
    return EXIT_FAILURE;
  }

  if (graph_dir == "") {
    dc.cout() << "Graph not specified. Cannot continue";
    return EXIT_FAILURE;
  }

  // Build the graph ----------------------------------------------------------
  graph_type graph(dc, clopts);
  dc.cout() << "Loading graph in format: "<< format << std::endl;
  graph.load_format(graph_dir, format);
  // must call finalize before querying the graph
  graph.finalize();
  dc.cout() << "#vertices: " << graph.num_vertices()
            << " #edges:" << graph.num_edges() << std::endl;

  // Initialize the vertex data
  graph.transform_vertices(init_vertex);

  // Running The Engine -------------------------------------------------------
  graphlab::omni_engine<graph_lab> engine(dc, graph, exec_type, clopts);
  engine.signal_all();
  engine.start();
  const float runtime = engine.elapsed_seconds();
  dc.cout() << "Finished Running engine in " << runtime
            << " seconds." << std::endl;

  // Save the final graph -----------------------------------------------------
  if (saveprefix != "") {
    graph.save(saveprefix, pagerank_writer(),
               false,    // do not gzip
               true,     // save vertices
               false);   // do not save edges
  }

  // Tear-down communication layer and quit -----------------------------------
  graphlab::mpi_tools::finalize();
  return EXIT_SUCCESS;
} // End of main