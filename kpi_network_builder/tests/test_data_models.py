import unittest
import json
import os
import tempfile
from dataclasses import asdict

# Adjust import path based on how tests are run.
# If run from root kpi_network_builder with 'python -m unittest discover tests', this should work.
from kpi_network_builder.src.data_models import (
    Schema, KPI, KPIRequiredData, Table, Field, Domain,
    load_schema_from_json, save_kpis_to_json
)

class TestSchemaLoading(unittest.TestCase):
    def setUp(self):
        self.temp_files = []

        # Valid schema
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
                            {"field_name": "order_id", "field_description": "ID", "data_type": "INT", "constraints": "PK"},
                            {"field_name": "amount", "field_description": "Amount", "data_type": "DECIMAL", "constraints": ""}
                        ]
                    }
                ]
            }
        ]
        self.valid_schema_file = self._create_temp_json_file(self.valid_schema_data)

        # Malformed JSON
        self.malformed_json_file = self._create_temp_file("this is not json")

        # Missing keys (e.g., missing 'fields' in a table)
        self.missing_keys_schema_data = [
            {
                "domain_name": "Sales",
                "tables": [{"table_name": "Customers"}] # Missing 'fields', 'domain_description', 'department'
            }
        ]
        # load_schema_from_json is somewhat tolerant to missing optional keys like table_description
        # but will fail if essential structural keys for creating objects are missing or if types are wrong.
        # The current load_schema_from_json uses .get() for many things, making it resilient to some missing keys.
        # Let's test a case where 'fields' is missing, which is crucial for Table.
        self.missing_fields_data = [
            {
                "domain_name": "TestDomain",
                "domain_description": "Test Desc",
                "department": "Test Dept",
                "tables": [
                    {
                        "table_name": "TestTable1",
                        "table_description": "Table without fields key"
                        # "fields" key is missing
                    }
                ]
            }
        ]
        self.missing_fields_file = self._create_temp_json_file(self.missing_fields_data)


    def _create_temp_json_file(self, data):
        fd, filepath = tempfile.mkstemp(suffix=".json")
        self.temp_files.append(filepath)
        with os.fdopen(fd, 'w') as tmp:
            json.dump(data, tmp)
        return filepath

    def _create_temp_file(self, content_str):
        fd, filepath = tempfile.mkstemp(suffix=".txt")
        self.temp_files.append(filepath)
        with os.fdopen(fd, 'w') as tmp:
            tmp.write(content_str)
        return filepath

    def test_load_valid_schema(self):
        schema = load_schema_from_json(self.valid_schema_file)
        self.assertIsInstance(schema, Schema)
        self.assertEqual(len(schema.domains), 1)
        domain = schema.domains[0]
        self.assertIsInstance(domain, Domain)
        self.assertEqual(domain.domain_name, "Sales")
        self.assertEqual(domain.department, "Sales Dept")
        self.assertEqual(len(domain.tables), 1)
        table = domain.tables[0]
        self.assertIsInstance(table, Table)
        self.assertEqual(table.table_name, "Orders")
        self.assertEqual(table.domain_name, "Sales") # Check domain_name propagation
        self.assertEqual(len(table.fields), 2)
        field1 = table.fields[0]
        self.assertIsInstance(field1, Field)
        self.assertEqual(field1.field_name, "order_id")

    def test_load_malformed_json(self):
        with self.assertRaises(json.JSONDecodeError):
            load_schema_from_json(self.malformed_json_file)

    def test_load_schema_missing_fields_key(self):
        # load_schema_from_json uses table_data.get("fields", [])
        # so it will not raise KeyError, but fields list will be empty.
        schema = load_schema_from_json(self.missing_fields_file)
        self.assertIsInstance(schema, Schema)
        self.assertEqual(len(schema.domains), 1)
        domain = schema.domains[0]
        self.assertEqual(len(domain.tables), 1)
        table = domain.tables[0]
        self.assertEqual(table.table_name, "TestTable1")
        self.assertEqual(len(table.fields), 0) # Fields list should be empty

    def tearDown(self):
        for f in self.temp_files:
            os.remove(f)

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
                ]
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
                ]
            )
        ]

    def test_save_kpis_structure_and_content(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmpfile:
            filepath = tmpfile.name

        try:
            save_kpis_to_json(self.sample_kpis, filepath)

            with open(filepath, 'r') as f:
                saved_data = json.load(f)

            self.assertIsInstance(saved_data, list)
            self.assertEqual(len(saved_data), len(self.sample_kpis))

            # Compare with asdict representation
            expected_data = [asdict(kpi) for kpi in self.sample_kpis]

            # Check structure and content of each KPI
            for i, saved_kpi_dict in enumerate(saved_data):
                expected_kpi_dict = expected_data[i]
                self.assertEqual(saved_kpi_dict['kpi_name'], expected_kpi_dict['kpi_name'])
                self.assertEqual(saved_kpi_dict['department'], expected_kpi_dict['department'])
                self.assertEqual(saved_kpi_dict['report_name'], expected_kpi_dict['report_name'])
                self.assertEqual(saved_kpi_dict['cadence'], expected_kpi_dict['cadence'])
                self.assertEqual(saved_kpi_dict['description'], expected_kpi_dict['description'])

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
        # Attempt to save to a non-existent directory (or read-only file, more complex to set up reliably)
        # For simplicity, using a path that's likely not writable for a standard user in a temp env.
        # This test is a bit platform-dependent or environment-dependent.
        # A more robust way might involve patching `open` to raise an IOError.
        invalid_filepath = "/hopefully/this/path/does/not/exist/test_kpis.json"
        if os.path.exists(os.path.dirname(invalid_filepath)): # pragma: no cover
             self.skipTest(f"Test path {os.path.dirname(invalid_filepath)} unexpectedly exists, cannot test IO Error reliably.")

        with self.assertRaises(IOError): # Or FileNotFoundError which is a subclass of IOError
            save_kpis_to_json(self.sample_kpis, invalid_filepath)


if __name__ == '__main__': # pragma: no cover
    unittest.main()
