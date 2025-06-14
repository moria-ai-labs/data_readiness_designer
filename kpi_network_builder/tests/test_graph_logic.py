import unittest
import networkx # For NetworkXNoPath, NodeNotFound

# Adjust import path
from src.graph_logic import KPINetworkGraph
from src.data_models import Table, Field, Domain

class TestKPINetworkGraph(unittest.TestCase):
    def setUp(self):
        self.graph = KPINetworkGraph()

        # Sample Table objects
        # Fields for T1
        self.f1_t1 = Field(field_name="id", field_description="Primary Key", data_type="INT", constraints="PK")
        self.f2_t1 = Field(field_name="value1", field_description="Value 1", data_type="VARCHAR", constraints="")
        self.f_common_t1_t3 = Field(field_name="common_key_t1_t3", field_description="FK to T3", data_type="INT", constraints="")

        # Fields for T2
        self.f1_t2 = Field(field_name="id", field_description="Primary Key", data_type="INT", constraints="PK")
        self.f2_t2 = Field(field_name="value2", field_description="Value 2", data_type="VARCHAR", constraints="")
        self.f_common_t2_t3 = Field(field_name="common_key_t2_t3", field_description="FK to T3", data_type="INT", constraints="")

        # Fields for T3 (potential bridge)
        self.f1_t3 = Field(field_name="id", field_description="Primary Key", data_type="INT", constraints="PK")
        self.f_common_t1_t3_ref = Field(field_name="common_key_t1_t3", field_description="Ref T1", data_type="INT", constraints="")
        self.f_common_t2_t3_ref = Field(field_name="common_key_t2_t3", field_description="Ref T2", data_type="INT", constraints="")

        # Fields for T4 (isolated or different common fields)
        self.f1_t4 = Field(field_name="id", field_description="Primary Key", data_type="INT", constraints="PK")
        self.f_other = Field(field_name="other_key", field_description="Other value", data_type="VARCHAR", constraints="")


        self.T1_obj = Table(domain_name="D1", table_name="T1", table_description="Table 1", fields=[self.f1_t1, self.f2_t1, self.f_common_t1_t3])
        self.T2_obj = Table(domain_name="D1", table_name="T2", table_description="Table 2", fields=[self.f1_t2, self.f2_t2, self.f_common_t2_t3])
        self.T3_obj = Table(domain_name="D1", table_name="T3", table_description="Table 3 (Bridge)", fields=[self.f1_t3, self.f_common_t1_t3_ref, self.f_common_t2_t3_ref])
        self.T4_obj = Table(domain_name="D2", table_name="T4", table_description="Table 4 (Isolated)", fields=[self.f1_t4, self.f_other])

        # Node IDs
        self.t1_id = ("D1", "T1")
        self.t2_id = ("D1", "T2")
        self.t3_id = ("D1", "T3")
        self.t4_id = ("D2", "T4")
        self.invalid_id = ("DX", "TX")

        # Add nodes
        self.graph.add_table_node(self.T1_obj.domain_name, self.T1_obj.table_name, self.T1_obj)
        self.graph.add_table_node(self.T2_obj.domain_name, self.T2_obj.table_name, self.T2_obj)
        self.graph.add_table_node(self.T3_obj.domain_name, self.T3_obj.table_name, self.T3_obj)
        self.graph.add_table_node(self.T4_obj.domain_name, self.T4_obj.table_name, self.T4_obj)


    def test_add_table_node(self):
        self.assertTrue(self.t1_id in self.graph.graph.nodes)
        self.assertEqual(self.graph.graph.nodes[self.t1_id]['table_obj'], self.T1_obj)
        self.assertTrue(self.t4_id in self.graph.graph.nodes)
        self.assertEqual(self.graph.graph.nodes[self.t4_id]['table_obj'], self.T4_obj)

    def test_add_connection(self):
        self.graph.add_connection(self.t1_id, self.t2_id, type="FK_Join")
        self.assertTrue(self.graph.graph.has_edge(self.t1_id, self.t2_id))
        self.assertEqual(self.graph.graph.edges[self.t1_id, self.t2_id]['type'], "FK_Join")

        # Test adding edge with non-existent node (NetworkX behavior: adds node)
        # KPINetworkGraph.add_connection doesn't prevent this, relies on NetworkX
        # self.graph.add_connection(self.t1_id, self.invalid_id)
        # self.assertTrue(self.graph.graph.has_edge(self.t1_id, self.invalid_id))
        # self.assertTrue(self.invalid_id in self.graph.graph.nodes) # NetworkX adds nodes if not present

    def test_path_exists(self):
        self.graph.add_connection(self.t1_id, self.t2_id)
        self.graph.add_connection(self.t2_id, self.t3_id)

        self.assertTrue(self.graph.path_exists(self.t1_id, self.t3_id))
        self.assertFalse(self.graph.path_exists(self.t3_id, self.t1_id)) # Directed graph
        self.assertFalse(self.graph.path_exists(self.t1_id, self.t4_id))

        # Test with invalid node ID (NetworkX raises NodeNotFound)
        with self.assertRaises(networkx.NodeNotFound):
            self.graph.path_exists(self.t1_id, self.invalid_id)
        with self.assertRaises(networkx.NodeNotFound):
            self.graph.path_exists(self.invalid_id, self.t1_id)

        # Test path to self (should be true if node exists, path of length 0)
        self.assertTrue(self.graph.path_exists(self.t1_id, self.t1_id))


    def test_all_tables_connected(self):
        self.graph.add_connection(self.t1_id, self.t2_id)
        self.graph.add_connection(self.t2_id, self.t3_id)

        self.assertTrue(self.graph.all_tables_connected([self.t1_id, self.t2_id, self.t3_id]))
        self.assertTrue(self.graph.all_tables_connected([self.t3_id, self.t1_id])) # Weakly connected

        self.assertFalse(self.graph.all_tables_connected([self.t1_id, self.t4_id]))
        self.assertTrue(self.graph.all_tables_connected([self.t1_id])) # Single table
        self.assertTrue(self.graph.all_tables_connected([])) # Empty list

        # Test with some nodes not in graph - should be handled by all_tables_connected
        # based on current implementation it filters to valid_table_ids.
        self.assertFalse(self.graph.all_tables_connected([self.t1_id, self.invalid_id]))
        self.assertTrue(self.graph.all_tables_connected([self.t1_id, self.t1_id, self.invalid_id]))


    def test_get_shortest_path(self):
        self.graph.add_connection(self.t1_id, self.t2_id)
        self.graph.add_connection(self.t2_id, self.t3_id)

        path = self.graph.get_shortest_path(self.t1_id, self.t3_id)
        self.assertEqual(path, [self.t1_id, self.t2_id, self.t3_id])

        self.assertIsNone(self.graph.get_shortest_path(self.t3_id, self.t1_id)) # No path in this direction
        self.assertIsNone(self.graph.get_shortest_path(self.t1_id, self.t4_id))

        # Test with invalid node ID
        self.assertIsNone(self.graph.get_shortest_path(self.t1_id, self.invalid_id))
        self.assertIsNone(self.graph.get_shortest_path(self.invalid_id, self.t1_id))

    def test_suggest_missing_links_simple(self):
        # T1 has 'common_key_t1_t3', T2 has 'common_key_t2_t3'
        # T3 has 'common_key_t1_t3' and 'common_key_t2_t3'
        # So, T3 shares a field name with T1, and T3 shares a field name with T2.
        # No direct connection T1-T2 in graph initially.

        required_ids = [self.t1_id, self.t2_id]

        domain1 = Domain(domain_name="D1", domain_description="Desc D1", department="Dept X",
                         tables=[self.T1_obj, self.T2_obj, self.T3_obj])
        domain2 = Domain(domain_name="D2", domain_description="Desc D2", department="Dept Y",
                         tables=[self.T4_obj])
        all_schema_domains = [domain1, domain2]

        suggestions = self.graph.suggest_missing_links(required_ids, all_schema_domains)

        # Expected: T3 can bridge T1 and T2 because:
        # T1 fields: {id, value1, common_key_t1_t3}
        # T2 fields: {id, value2, common_key_t2_t3}
        # T3 fields: {id, common_key_t1_t3, common_key_t2_t3}
        # T3 shares 'common_key_t1_t3' with T1.
        # T3 shares 'common_key_t2_t3' with T2.
        # So, T3 is a potential bridge.

        # The key for suggestions dict is ((t1_id, t2_id),) or ((t2_id, t1_id),)
        # We need to check for either order if the graph is undirected for this pair.
        # The current logic iterates pairs (i, j) where i < j, so key should be ((t1_id, t2_id),)
        pair_key = (self.t1_id, self.t2_id)

        self.assertIn(pair_key, suggestions)
        self.assertIsInstance(suggestions[pair_key], list)
        self.assertIn(self.t3_id, suggestions[pair_key])

    def test_suggest_missing_links_no_bridge(self):
        # Scenario: T1 and T4. T1 in D1, T4 in D2.
        # T1 fields: {id, value1, common_key_t1_t3}
        # T4 fields: {id, other_key}
        # T3 fields: {id, common_key_t1_t3, common_key_t2_t3}
        # T3 connects to T1 (common_key_t1_t3) but not to T4 based on shared field names.

        required_ids = [self.t1_id, self.t4_id]

        domain1 = Domain(domain_name="D1", domain_description="Desc D1", department="Dept X",
                         tables=[self.T1_obj, self.T2_obj, self.T3_obj]) # T3 is available
        domain2 = Domain(domain_name="D2", domain_description="Desc D2", department="Dept Y",
                         tables=[self.T4_obj])
        all_schema_domains = [domain1, domain2]

        suggestions = self.graph.suggest_missing_links(required_ids, all_schema_domains)
        pair_key = (self.t1_id, self.t4_id)

        # T3 can link to T1 (via 'common_key_t1_t3')
        # T3 cannot link to T4 (no common field names between T3 and T4)
        # Therefore, T3 should not be suggested as a bridge for T1 and T4.
        if pair_key in suggestions: # pragma: no cover
            self.assertNotIn(self.t3_id, suggestions[pair_key],
                             "T3 should not be suggested as it doesn't connect to T4 by field name")
        # A more precise assertion is that the pair_key might not even be in suggestions if no bridge is found,
        # or if it is, the list of bridges should be empty.
        # The current implementation adds to suggestions only if potential_bridges is not empty.
        self.assertNotIn(pair_key, suggestions, "No bridge should be found between T1 and T4 via T3 based on field names.")


    def test_suggest_missing_links_already_connected(self):
        self.graph.add_connection(self.t1_id, self.t2_id) # T1 and T2 are now connected

        required_ids = [self.t1_id, self.t2_id]
        domain1 = Domain(domain_name="D1", tables=[self.T1_obj, self.T2_obj, self.T3_obj])
        all_schema_domains = [domain1]

        # The suggest_missing_links uses a subgraph of *required_ids*.
        # If t1 and t2 are connected directly in this subgraph, it won't suggest.
        suggestions = self.graph.suggest_missing_links(required_ids, all_schema_domains)

        # Since T1 and T2 are directly connected in the subgraph of required_ids,
        # the pair (T1,T2) should not be a key in the suggestions dict.
        pair_key = (self.t1_id, self.t2_id)
        self.assertNotIn(pair_key, suggestions, "Should not suggest links for already connected tables in selection.")

if __name__ == '__main__': # pragma: no cover
    unittest.main()
