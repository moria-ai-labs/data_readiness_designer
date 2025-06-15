import unittest
import json
import os
import tempfile
from dataclasses import asdict

# Adjust import path based on how tests are run.
# If run from root kpi_network_builder with 'python -m unittest discover tests', this should work.
from src.data_models import (
    Schema, KPI, KPIRequiredData, Table, Field, Domain,
    load_schema_from_json, save_kpis_to_json
)

class TestSchemaLoading(unittest.TestCase):
    def setUp(self):
        self.temp_files = []

        # Updated valid schema with new Field attributes
        self.valid_schema_data = [
            {
                "domain_name": "Sales",
                "domain_description": "Sales data",
                "department": "Sales Dept",
                "tables": [
                    {
                        "table_name": "Orders",
                        "table_description": "Order details",
                        "fields": [
                            {
                                "field_name": "order_id", "field_description": "ID", "data_type": "INT",
                                "primary_key": True, "nullable": False
                            },
                            {
                                "field_name": "customer_id", "field_description": "Customer FK", "data_type": "INT",
                                "nullable": False, "foreign_key": True,
                                "foreign_key_table": "Customers", "foreign_key_column": "customer_id"
                            },
                            {
                                "field_name": "amount", "field_description": "Amount", "data_type": "DECIMAL"
                                # This field will use defaults: pk=False, nullable=True, fk=False, fk_table=None, fk_column=None
                            },
                             {
                                "field_name": "notes", "field_description": "Order notes", "data_type": "TEXT",
                                "nullable": True # Explicitly nullable, though it's the default
                            }
                        ]
                    },
                    {
                        "table_name": "Customers", # Referenced by Orders.customer_id
                        "table_description": "Customer details",
                        "fields": [
                             {
                                "field_name": "customer_id", "field_description": "Customer PK", "data_type": "INT",
                                "primary_key": True, "nullable": False
                            }
                        ]
                    }
                ]
            }
        ]
        self.valid_schema_file = self._create_temp_json_file(self.valid_schema_data)

        # Malformed JSON
        self.malformed_json_file = self._create_temp_file("this is not json")

        # Schema with a table missing the 'fields' key entirely
        self.missing_fields_key_data = [
            {
                "domain_name": "TestDomain",
                "domain_description": "Test Desc",
                "department": "Test Dept",
                "tables": [
                    {
                        "table_name": "TestTable1",
                        "table_description": "Table without fields key"
                        # "fields" key is intentionally missing
                    }
                ]
            }
        ]
        self.missing_fields_key_file = self._create_temp_json_file(self.missing_fields_key_data)

    def _create_temp_json_file(self, data):
        # Helper to create a temporary JSON file with given data
        fd, filepath = tempfile.mkstemp(suffix=".json")
        self.temp_files.append(filepath)
        with os.fdopen(fd, 'w') as tmp:
            json.dump(data, tmp)
        return filepath

    def _create_temp_file(self, content_str: str):
        # Helper to create a temporary file with given string content
        fd, filepath = tempfile.mkstemp(suffix=".txt")
        self.temp_files.append(filepath)
        with os.fdopen(fd, 'w') as tmp:
            tmp.write(content_str)
        return filepath

    def test_load_valid_schema_and_field_attributes(self):
        schema = load_schema_from_json(self.valid_schema_file)
        self.assertIsInstance(schema, Schema)
        self.assertEqual(len(schema.domains), 1)

        domain = schema.domains[0]
        self.assertIsInstance(domain, Domain)
        self.assertEqual(domain.domain_name, "Sales")
        self.assertEqual(domain.department, "Sales Dept")
        self.assertEqual(len(domain.tables), 2) # Now two tables: Orders, Customers

        # Test 'Orders' table and its fields
        orders_table = next(t for t in domain.tables if t.table_name == "Orders")
        self.assertIsInstance(orders_table, Table)
        self.assertEqual(orders_table.domain_name, "Sales")
        self.assertEqual(len(orders_table.fields), 4)

        # Field 1: order_id (PK, Not Nullable)
        f_order_id = orders_table.fields[0]
        self.assertEqual(f_order_id.field_name, "order_id")
        self.assertTrue(f_order_id.primary_key)
        self.assertFalse(f_order_id.nullable)
        self.assertFalse(f_order_id.foreign_key)
        self.assertIsNone(f_order_id.foreign_key_table)
        self.assertIsNone(f_order_id.foreign_key_column)

        # Field 2: customer_id (FK, Not Nullable)
        f_customer_id = orders_table.fields[1]
        self.assertEqual(f_customer_id.field_name, "customer_id")
        self.assertFalse(f_customer_id.primary_key)
        self.assertFalse(f_customer_id.nullable)
        self.assertTrue(f_customer_id.foreign_key)
        self.assertEqual(f_customer_id.foreign_key_table, "Customers")
        self.assertEqual(f_customer_id.foreign_key_column, "customer_id")

        # Field 3: amount (Defaults for PK, Nullable, FK)
        f_amount = orders_table.fields[2]
        self.assertEqual(f_amount.field_name, "amount")
        self.assertFalse(f_amount.primary_key) # Default
        self.assertTrue(f_amount.nullable)    # Default
        self.assertFalse(f_amount.foreign_key) # Default
        self.assertIsNone(f_amount.foreign_key_table) # Default
        self.assertIsNone(f_amount.foreign_key_column) # Default

        # Field 4: notes (Explicitly Nullable=True)
        f_notes = orders_table.fields[3]
        self.assertEqual(f_notes.field_name, "notes")
        self.assertFalse(f_notes.primary_key)
        self.assertTrue(f_notes.nullable) # Explicitly set to default, but good to check
        self.assertFalse(f_notes.foreign_key)


        # Test 'Customers' table (minimal fields for FK reference)
        customers_table = next(t for t in domain.tables if t.table_name == "Customers")
        self.assertIsInstance(customers_table, Table)
        self.assertEqual(len(customers_table.fields), 1)
        f_cust_pk = customers_table.fields[0]
        self.assertEqual(f_cust_pk.field_name, "customer_id")
        self.assertTrue(f_cust_pk.primary_key)
        self.assertFalse(f_cust_pk.nullable)


    def test_load_malformed_json(self):
        with self.assertRaises(json.JSONDecodeError):
            load_schema_from_json(self.malformed_json_file)

    def test_load_schema_table_missing_fields_key(self):
        # load_schema_from_json uses table_data.get("fields", [])
        # This means if 'fields' key is absent, it defaults to an empty list.
        schema = load_schema_from_json(self.missing_fields_key_file)
        self.assertIsInstance(schema, Schema)
        self.assertEqual(len(schema.domains), 1)
        domain = schema.domains[0]
        self.assertEqual(len(domain.tables), 1)
        table = domain.tables[0]
        self.assertEqual(table.table_name, "TestTable1")
        self.assertEqual(len(table.fields), 0) # Fields list should be empty

    def tearDown(self):
        for f_path in self.temp_files:
            if os.path.exists(f_path):
                os.remove(f_path)

class TestKPISaving(unittest.TestCase):
    def setUp(self):
        self.sample_kpis = [
            KPI(
                kpi_name="Total Revenue",
                department="Sales",
                report_name="Sales Report",
                cadence="Daily",
                description="Total revenue from all sales.",
                data_required=[
                    KPIRequiredData(domain_name="Sales", table_name="Orders", field_name="amount"),
                    KPIRequiredData(domain_name="Sales", table_name="Orders", field_name="order_id")
                ],
                isAvailable=True # Explicitly set for testing
            ),
            KPI(
                kpi_name="New Customers",
                department="Marketing",
                report_name="Marketing Report",
                cadence="Weekly",
                description="Number of new customers acquired.",
                data_required=[
                    KPIRequiredData(domain_name="CRM", table_name="Customers", field_name="customer_id"),
                    KPIRequiredData(domain_name="CRM", table_name="Customers", field_name="signup_date")
                ],
                isAvailable=False # Explicitly set for testing
            ),
            KPI( # Test default isAvailable
                kpi_name="Default Availability KPI",
                department="Operations",
                report_name="Ops Report",
                cadence="Monthly",
                description="KPI with default isAvailable.",
                data_required=[] # No specific data needed for this test focus
                # isAvailable will use default False
            )
        ]

    def test_save_kpis_structure_and_content(self):
        # Use a non-deleted temporary file to ensure it can be read after writing
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmpfile:
            filepath = tmpfile.name

        try:
            save_kpis_to_json(self.sample_kpis, filepath)

            with open(filepath, 'r') as f:
                saved_data = json.load(f)

            self.assertIsInstance(saved_data, list)
            self.assertEqual(len(saved_data), len(self.sample_kpis))

            expected_data = [asdict(kpi) for kpi in self.sample_kpis]

            for i, saved_kpi_dict in enumerate(saved_data):
                expected_kpi_dict = expected_data[i]
                self.assertEqual(saved_kpi_dict['kpi_name'], expected_kpi_dict['kpi_name'])
                self.assertEqual(saved_kpi_dict['department'], expected_kpi_dict['department'])
                self.assertEqual(saved_kpi_dict['report_name'], expected_kpi_dict['report_name'])
                self.assertEqual(saved_kpi_dict['cadence'], expected_kpi_dict['cadence'])
                self.assertEqual(saved_kpi_dict['description'], expected_kpi_dict['description'])

                # Assert the isAvailable field
                # Use .get() for saved_kpi_dict in case 'isAvailable' might be missing (though asdict should include it if default is set)
                # For expected_kpi_dict, direct access is fine as asdict will include fields with default values.
                self.assertEqual(saved_kpi_dict.get('isAvailable'), expected_kpi_dict['isAvailable'])
                # Specifically check the default for the third KPI
                if expected_kpi_dict['kpi_name'] == "Default Availability KPI":
                    self.assertFalse(saved_kpi_dict.get('isAvailable')) # Default is False
                    self.assertFalse(expected_kpi_dict['isAvailable'])


                self.assertIsInstance(saved_kpi_dict['data_required'], list)
                self.assertEqual(len(saved_kpi_dict['data_required']), len(expected_kpi_dict['data_required']))

                for j, saved_req_data_dict in enumerate(saved_kpi_dict['data_required']):
                    expected_req_data_dict = expected_kpi_dict['data_required'][j]
                    self.assertEqual(saved_req_data_dict['domain_name'], expected_req_data_dict['domain_name'])
                    self.assertEqual(saved_req_data_dict['table_name'], expected_req_data_dict['table_name'])
                    self.assertEqual(saved_req_data_dict['field_name'], expected_req_data_dict['field_name'])
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_save_kpis_empty_list(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmpfile:
            filepath = tmpfile.name
        try:
            save_kpis_to_json([], filepath)
            with open(filepath, 'r') as f:
                saved_data = json.load(f)
            self.assertEqual(saved_data, [])
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_save_kpis_io_error(self):
        invalid_filepath = "/hopefully/this/path/does/not/exist/test_kpis.json"
        if os.path.exists(os.path.dirname(invalid_filepath)): # pragma: no cover
             self.skipTest(f"Test path {os.path.dirname(invalid_filepath)} unexpectedly exists.")
        with self.assertRaises(IOError):
            save_kpis_to_json(self.sample_kpis, invalid_filepath)

if __name__ == '__main__': # pragma: no cover
    unittest.main()
