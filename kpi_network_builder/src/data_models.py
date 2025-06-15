"""
Defines the core data models for representing data schemas and Key Performance Indicators (KPIs).

This module includes dataclasses for:
- `Field`: Represents a field within a data table, including constraint information.
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
from typing import List, Any, Optional # Optional is needed for type hints like Optional[str]

@dataclass
class Field:
    """
    Represents a single field (column) in a data table.

    Attributes:
        field_name (str): The name of the field.
        field_description (str): A human-readable description of the field.
        data_type (str): The data type of the field (e.g., INT, VARCHAR, DECIMAL).
        primary_key (bool): True if the field is part of the primary key. Defaults to False.
        nullable (bool): True if the field can contain NULL values. Defaults to True.
        foreign_key (bool): True if the field is a foreign key. Defaults to False.
        foreign_key_table (Optional[str]): The table referenced by the foreign key, if applicable.
        foreign_key_column (Optional[str]): The column in the referenced table, if applicable.
    """
    field_name: str
    field_description: str
    data_type: str
    primary_key: bool = False
    nullable: bool = True  # Defaulting to True as 'nullable: false' is explicit in some schemas
    foreign_key: bool = False
    foreign_key_table: Optional[str] = None
    foreign_key_column: Optional[str] = None

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
    The field definitions are parsed to populate the new attributes of the `Field` dataclass.

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
        data = json.load(f)

    loaded_domains = []
    for domain_data in data:
        loaded_tables = []
        for table_data in domain_data.get("tables", []):
            loaded_fields = []
            for field_data in table_data.get("fields", []):
                # Create Field object with new attributes
                field_obj = Field(
                    field_name=field_data.get("field_name", "UnknownField"),
                    field_description=field_data.get("field_description", ""),
                    data_type=field_data.get("data_type", "UNKNOWN"),
                    primary_key=field_data.get("primary_key", False),
                    nullable=field_data.get("nullable", True), # Default to True
                    foreign_key=field_data.get("foreign_key", False),
                    foreign_key_table=field_data.get("foreign_key_table"), # Will be None if key missing
                    foreign_key_column=field_data.get("foreign_key_column") # Will be None if key missing
                )
                loaded_fields.append(field_obj)

            table_obj = Table(
                table_name=table_data.get("table_name", "UnknownTable"),
                table_description=table_data.get("table_description", ""),
                fields=loaded_fields,
                domain_name=domain_data.get("domain_name", "UnknownDomain")
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
    isAvailable: bool = False # New field to indicate if the KPI data is available

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
        print(f"Error during KPI saving in data_models.save_kpis_to_json: {e}")
        raise e
