"""
Manages the graph representation of tables and their connections using NetworkX.

This module provides the `KPINetworkGraph` class, which encapsulates a
NetworkX directed graph (`DiGraph`). It offers methods to:
- Add tables as nodes, storing `Table` objects as node attributes.
- Add directed connections (edges) between tables.
- Query for path existence, shortest paths, and overall connectivity of table sets.
- Suggest potential intermediate tables to bridge gaps between unconnected tables based on shared field names.
"""
import networkx
from ..src.data_models import Table, Domain # Adjusted import path

class KPINetworkGraph:
    """
    A graph manager for representing and analyzing relationships between data tables.

    This class uses a NetworkX DiGraph to store tables as nodes and
    user-defined connections as directed edges. Table metadata (as `Table` objects)
    is stored as attributes of the nodes.
    """
    def __init__(self):
        """
        Initializes the KPINetworkGraph with an empty directed graph.
        """
        self.graph = networkx.DiGraph()

    def add_table_node(self, domain_name: str, table_name: str, table_data: Table):
        """
        Adds a table as a node to the graph.

        The node ID is a tuple `(domain_name, table_name)`. The full `Table` object,
        which includes field information and descriptions, is stored as an attribute
        of the node, accessible via `self.graph.nodes[node_id]['table_obj']`.

        Args:
            domain_name (str): The domain name of the table.
            table_name (str): The name of the table.
            table_data (Table): The `Table` object containing metadata for this table.
        """
        node_id = (domain_name, table_name)
        self.graph.add_node(node_id, table_obj=table_data)

    def add_connection(self, source_table_id: tuple[str, str], target_table_id: tuple[str, str], **attrs):
        """
        Adds a directed connection (edge) between two table nodes in the graph.

        Additional attributes for the connection (e.g., type of join, specific fields involved)
        can be passed as keyword arguments.

        Args:
            source_table_id (tuple[str, str]): The ID `(domain_name, table_name)` of the source table.
            target_table_id (tuple[str, str]): The ID `(domain_name, table_name)` of the target table.
            **attrs: Arbitrary keyword arguments to store as attributes of the edge.
        """
        self.graph.add_edge(source_table_id, target_table_id, **attrs)

    def path_exists(self, source_table_id: tuple[str, str], target_table_id: tuple[str, str]) -> bool:
        """
        Checks if a directed path exists from a source table to a target table.

        Args:
            source_table_id (tuple[str, str]): The ID of the source table.
            target_table_id (tuple[str, str]): The ID of the target table.

        Returns:
            bool: `True` if a path exists, `False` otherwise.

        Raises:
            networkx.NodeNotFound: If either `source_table_id` or `target_table_id`
                                   is not present in the graph.
        """
        return networkx.has_path(self.graph, source_table_id, target_table_id)

    def all_tables_connected(self, table_ids: list[tuple[str, str]]) -> bool:
        """
        Checks if all specified tables are part of the same connected component in the graph.

        This method considers the graph as undirected for this check (weakly connected),
        meaning a path can exist in either direction between any two tables in the component.
        Tables not present in the graph are ignored after a warning.

        Args:
            table_ids (list[tuple[str, str]]): A list of table IDs to check for connectivity.

        Returns:
            bool: `True` if all valid tables in `table_ids` form a single weakly connected
                  component (or if there are fewer than 2 valid tables), `False` otherwise.
        """
        if len(table_ids) < 2:
            return True

        valid_table_ids = [tid for tid in table_ids if tid in self.graph]
        if len(valid_table_ids) < len(table_ids):
            # Log a warning if some tables provided are not in the graph.
            # This might indicate an issue upstream or simply that not all desired tables are visualized.
            print(f"Warning: Some table IDs for connectivity check do not exist in the graph: {set(table_ids) - set(valid_table_ids)}")

        if len(valid_table_ids) < 2: # After filtering, if < 2 valid tables, they are "connected".
             return True

        # Create a subgraph containing only the valid tables to check their connectivity among themselves.
        subgraph = self.graph.subgraph(valid_table_ids)
        return networkx.is_weakly_connected(subgraph)

    def get_shortest_path(self, source_table_id: tuple[str, str], target_table_id: tuple[str, str]) -> list | None:
        """
        Finds the shortest directed path from a source table to a target table.

        Args:
            source_table_id (tuple[str, str]): The ID of the source table.
            target_table_id (tuple[str, str]): The ID of the target table.

        Returns:
            list | None: A list of table IDs representing the shortest path from source
                         to target, or `None` if no path exists or if either node is not found.
        """
        try:
            return networkx.shortest_path(self.graph, source_table_id, target_table_id)
        except networkx.NetworkXNoPath:
            return None
        except networkx.NodeNotFound:
            # Log or handle cases where nodes are not found.
            print(f"Warning: Node not found in get_shortest_path. Source: {source_table_id}, Target: {target_table_id}")
            return None

    def suggest_missing_links(
        self,
        required_table_ids: list[tuple[str, str]],
        all_schema_domains: list[Domain]
    ) -> dict:
        """
        Suggests potential intermediate tables to connect pairs of tables within
        `required_table_ids` that are not currently connected in the subgraph of these tables.

        The suggestion heuristic is based on finding tables (not in `required_table_ids`)
        from `all_schema_domains` that share common field names with both tables in an
        unconnected pair. This implies these tables *might* serve as intermediaries.

        Args:
            required_table_ids (list[tuple[str, str]]): A list of table IDs that are part of a KPI.
            all_schema_domains (list[Domain]): A list of all `Domain` objects in the entire schema,
                                              used to search for potential bridge tables.

        Returns:
            dict: A dictionary where keys are tuples `((t1_id, t2_id),)` representing an
                  unconnected pair from `required_table_ids`. Values are lists of
                  potential bridge table IDs `(domain_name, table_name)` that could link them.
                  Example: `{ (('D1', 'T1'), ('D1', 'T2')) : [('D1', 'T3')] }`
        """
        suggestions = {}

        valid_required_table_ids = [tid for tid in required_table_ids if tid in self.graph]
        if len(valid_required_table_ids) < 2: # Need at least two tables to find a pair.
            return suggestions

        # Subgraph of only the tables required for the KPI.
        # This is used to determine if pairs are ALREADY connected *within this selection*.
        subgraph_of_required = self.graph.subgraph(valid_required_table_ids)

        for i in range(len(valid_required_table_ids)):
            for j in range(i + 1, len(valid_required_table_ids)):
                t1_id = valid_required_table_ids[i]
                t2_id = valid_required_table_ids[j]

                # Check if path exists in either direction *within the subgraph of required tables*.
                # If they are connected (possibly via other tables in required_table_ids),
                # we don't need to suggest external bridges for this specific pair.
                if not networkx.has_path(subgraph_of_required, t1_id, t2_id) and \
                   not networkx.has_path(subgraph_of_required, t2_id, t1_id):

                    potential_bridges = []

                    # Retrieve Table objects for t1 and t2 to access their field names.
                    # These must exist as they are from valid_required_table_ids.
                    t1_obj: Table = self.graph.nodes[t1_id]['table_obj']
                    t2_obj: Table = self.graph.nodes[t2_id]['table_obj']

                    t1_field_names = {f.field_name for f in t1_obj.fields}
                    t2_field_names = {f.field_name for f in t2_obj.fields}

                    # Iterate through all tables in the entire schema to find potential bridges.
                    for domain in all_schema_domains:
                        for table_in_domain in domain.tables:
                            schema_table_id = (domain.domain_name, table_in_domain.table_name)

                            # Don't suggest a table that is already one of the required tables.
                            if schema_table_id in valid_required_table_ids:
                                continue

                            schema_table_obj: Table = table_in_domain # For clarity
                            schema_table_field_names = {f.field_name for f in schema_table_obj.fields}

                            # Heuristic: Does this schema_table share any field name with t1?
                            links_to_t1 = bool(t1_field_names.intersection(schema_table_field_names))
                            # Heuristic: Does this schema_table share any field name with t2?
                            links_to_t2 = bool(t2_field_names.intersection(schema_table_field_names))

                            if links_to_t1 and links_to_t2:
                                # This table shares field names with both t1 and t2,
                                # making it a candidate for bridging the connection.
                                potential_bridges.append(schema_table_id)

                    if potential_bridges:
                        # Store suggestions, ensuring no duplicate bridge tables for a given pair.
                        suggestions[((t1_id, t2_id))] = list(set(potential_bridges))
        return suggestions
