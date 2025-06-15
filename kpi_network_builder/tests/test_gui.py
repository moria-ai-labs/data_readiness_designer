import unittest

# Assuming tests are run from the root 'kpi_network_builder' directory
from src.gui import has_common_fields
from src.data_models import Table, Field

class TestHasCommonFields(unittest.TestCase):

    def test_common_fields_exist(self):
        """Test that common fields are detected."""
        table1 = Table(table_name="T1", table_description="Desc1", domain_name="D1", fields=[
            Field(field_name="id", field_description="ID", data_type="INT"),
            Field(field_name="name", field_description="Name", data_type="VARCHAR")
        ])
        table2 = Table(table_name="T2", table_description="Desc2", domain_name="D1", fields=[
            Field(field_name="ref_id", field_description="Ref ID", data_type="INT"),
            Field(field_name="name", field_description="Another Name", data_type="VARCHAR") # Common field name
        ])
        self.assertTrue(has_common_fields(table1, table2))

    def test_no_common_fields(self):
        """Test that no common fields are correctly identified."""
        table1 = Table(table_name="T1", table_description="Desc1", domain_name="D1", fields=[
            Field(field_name="id", field_description="ID", data_type="INT"),
            Field(field_name="value_a", field_description="Value A", data_type="VARCHAR")
        ])
        table2 = Table(table_name="T2", table_description="Desc2", domain_name="D1", fields=[
            Field(field_name="ref_id", field_description="Ref ID", data_type="INT"),
            Field(field_name="value_b", field_description="Value B", data_type="VARCHAR")
        ])
        self.assertFalse(has_common_fields(table1, table2))

    def test_empty_fields_list_one_table(self):
        """Test with one table having an empty fields list."""
        table1 = Table(table_name="T1", table_description="Desc1", domain_name="D1", fields=[
            Field(field_name="id", field_description="ID", data_type="INT")
        ])
        table2 = Table(table_name="T2", table_description="Desc2", domain_name="D1", fields=[]) # Empty fields
        self.assertFalse(has_common_fields(table1, table2))

    def test_empty_fields_list_both_tables(self):
        """Test with both tables having empty fields lists."""
        table1 = Table(table_name="T1", table_description="Desc1", domain_name="D1", fields=[])
        table2 = Table(table_name="T2", table_description="Desc2", domain_name="D1", fields=[])
        self.assertFalse(has_common_fields(table1, table2))

    def test_one_table_is_none(self):
        """Test when one of the table objects is None."""
        table1 = Table(table_name="T1", table_description="Desc1", domain_name="D1", fields=[
            Field(field_name="id", field_description="ID", data_type="INT")
        ])
        self.assertFalse(has_common_fields(table1, None))
        self.assertFalse(has_common_fields(None, table1))

    def test_both_tables_are_none(self):
        """Test when both table objects are None."""
        self.assertFalse(has_common_fields(None, None))

    def test_case_sensitive_field_names(self):
        """Test if field name comparison is case sensitive (it should be)."""
        table1 = Table(table_name="T1", table_description="Desc1", domain_name="D1", fields=[
            Field(field_name="fieldName", field_description="ID", data_type="INT")
        ])
        table2 = Table(table_name="T2", table_description="Desc2", domain_name="D1", fields=[
            Field(field_name="fieldname", field_description="Another ID", data_type="INT")
        ])
        self.assertFalse(has_common_fields(table1, table2), "Field names should be case sensitive.")

        table3 = Table(table_name="T3", table_description="Desc3", domain_name="D1", fields=[
            Field(field_name="CommonName", field_description="ID", data_type="INT")
        ])
        table4 = Table(table_name="T4", table_description="Desc4", domain_name="D1", fields=[
            Field(field_name="CommonName", field_description="Another ID", data_type="INT")
        ])
        self.assertTrue(has_common_fields(table3, table4), "Identical case field names should match.")


if __name__ == '__main__': # pragma: no cover
    unittest.main()
