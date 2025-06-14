"""
Defines the core data models for representing data schemas and Key Performance Indicators (KPIs).

This module includes dataclasses for:
- `Field`: Represents a field within a data table.
- `Table`: Represents a data table, including its fields and domain.
- `Domain`: Represents a logical grouping of tables, often related to a business area.
- `Schema`: Represents the overall data schema, composed of multiple domains.
- `KPIRequiredData`: Specifies a single piece of data (a field from a table in a domain) required for a KPI.
- `KPI`: Represents a Key Performance Indicator, including its metadata and a list of required data elements.

It also provides utility functions for:
- Loading a `Schema` object from a JSON file (`load_schema_from_json`).
- Saving a list of `KPI` objects to a JSON file (`save_kpis_to_json`).
"""
import json
from dataclasses import dataclass, field, asdict
from typing import List, Any

@dataclass
class Field:
    """
    Represents a single field (column) in a data table.

    Attributes:
        field_name (str): The name of the field.
        field_description (str): A human-readable description of the field.
        data_type (str): The data type of the field (e.g., INT, VARCHAR, DECIMAL).
        constraints (str): Any constraints applied to the field (e.g., "NOT NULL", "PRIMARY KEY").
    """
    field_name: str
    field_description: str
    data_type: str
    constraints: str

@dataclass
class Table:
    """
    Represents a data table within a specific domain.

    Attributes:
        table_name (str): The name of the table.
        table_description (str): A human-readable description of the table.
        fields (List[Field]): A list of `Field` objects that belong to this table.
        domain_name (str): The name of the domain this table belongs to.
                           This is set during schema loading.
    """
    table_name: str
    table_description: str
    fields: List[Field]
    domain_name: str = "" # Populated during schema loading for context

@dataclass
class Domain:
    """
    Represents a logical domain or subject area within the data schema.

    Attributes:
        domain_name (str): The name of the domain (e.g., "Customer", "Sales").
        domain_description (str): A description of what this domain represents.
        department (str): The business department primarily associated with this domain.
        tables (List[Table]): A list of `Table` objects that fall under this domain.
    """
    domain_name: str
    domain_description: str
    department: str
    tables: List[Table]

@dataclass
class Schema:
    """
    Represents the entire data schema, composed of multiple domains.

    Attributes:
        domains (List[Domain]): A list of `Domain` objects that make up the schema.
    """
    domains: List[Domain]

def load_schema_from_json(filepath: str) -> Schema:
    """
    Loads schema data from a JSON file and constructs a `Schema` object.

    The JSON file is expected to be a list of domain objects, where each domain
    contains a list of table objects, and each table contains a list of field objects.

    Args:
        filepath (str): The path to the JSON file containing the schema definition.

    Returns:
        Schema: A `Schema` object populated with data from the JSON file.

    Raises:
        FileNotFoundError: If the specified filepath does not exist.
        json.JSONDecodeError: If the JSON file is malformed.
        KeyError: If essential keys are missing in the JSON structure (though some
                  missing keys are handled gracefully by using default values or empty lists).
        TypeError: If data types in JSON are not as expected (e.g., a list where a dict is expected).
    """
    with open(filepath, 'r') as f:
        data = json.load(f) # Can raise FileNotFoundError, json.JSONDecodeError

    loaded_domains = []
    for domain_data in data: # Iterates through the top-level list (domains)
        loaded_tables = []
        # Use .get for potentially missing keys to provide default empty lists
        for table_data in domain_data.get("tables", []):
            loaded_fields = []
            for field_data in table_data.get("fields", []):
                # Field creation assumes all necessary keys are present in field_data
                loaded_fields.append(Field(**field_data))

            table_obj = Table(
                table_name=table_data.get("table_name", "UnknownTable"),
                table_description=table_data.get("table_description", ""),
                fields=loaded_fields,
                domain_name=domain_data.get("domain_name", "UnknownDomain") # Set table's domain context
            )
            loaded_tables.append(table_obj)

        loaded_domains.append(Domain(
            domain_name=domain_data.get("domain_name", "UnknownDomain"),
            domain_description=domain_data.get("domain_description", ""),
            department=domain_data.get("department", ""),
            tables=loaded_tables
        ))
    return Schema(domains=loaded_domains)

@dataclass
class KPIRequiredData:
    """
    Specifies a single data field required for a KPI.

    Attributes:
        domain_name (str): The domain name of the table from which the field is required.
        table_name (str): The table name from which the field is required.
        field_name (str): The specific field name required.
    """
    domain_name: str
    table_name: str
    field_name: str

@dataclass
class KPI:
    """
    Represents a Key Performance Indicator (KPI).

    Attributes:
        kpi_name (str): The name of the KPI.
        department (str): The department responsible for or associated with this KPI.
        report_name (str): The name of the report where this KPI is typically found.
        cadence (str): How often the KPI is measured or reported (e.g., "Daily", "Weekly").
        description (str): A detailed description of the KPI.
        data_required (List[KPIRequiredData]): A list of `KPIRequiredData` objects
                                               specifying all data fields needed for this KPI.
    """
    kpi_name: str
    department: str
    report_name: str
    cadence: str
    description: str
    data_required: List[KPIRequiredData]

def save_kpis_to_json(kpis: List[KPI], filepath: str) -> None:
    """
    Saves a list of KPI objects to a JSON file.

    This function serializes the KPI objects (and their nested `KPIRequiredData` objects)
    into a JSON format using `dataclasses.asdict` for accurate conversion.

    Args:
        kpis (List[KPI]): A list of `KPI` objects to be saved.
        filepath (str): The path to the file where the JSON data will be saved.

    Raises:
        IOError: If there is an issue writing to the filepath (e.g., permissions, disk full).
        TypeError: If the `kpis` list contains objects that cannot be serialized by `asdict`
                   (should not happen if only `KPI` instances are provided).
    """
    try:
        kpi_list_of_dicts = [asdict(kpi) for kpi in kpis]
        with open(filepath, 'w') as f:
            json.dump(kpi_list_of_dicts, f, indent=2)
    except (IOError, TypeError) as e:
        # Log or print for server-side debugging, but re-raise for GUI to handle user notification
        print(f"Error during KPI saving in data_models.save_kpis_to_json: {e}")
        raise e
