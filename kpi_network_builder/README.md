# KPI Network Builder

## Project Description
The KPI Network Builder is a desktop application designed to help users visualize their data schema and define Key Performance Indicators (KPIs) based on this schema. Users can load a data schema from a JSON file, drag-and-drop tables onto a canvas, draw connections between them to represent relationships, and then define KPIs by selecting relevant tables and fields. The defined KPIs can be exported to a JSON file for further use.

## Features
-   **Schema Loading**: Load data schema definitions from a JSON file.
-   **Visual Network Building**: Drag tables onto a canvas and draw connections to visualize relationships.
-   **KPI Definition**: Define KPIs by selecting tables from the canvas, providing metadata (name, department, description, etc.), and choosing specific fields required for each KPI.
-   **Connectivity Check**: Automatically checks if the tables selected for a KPI are connected in the visualized graph.
-   **JSON Export**: Save defined KPI specifications to a JSON file.
-   **Graphical User Interface**: Built with PyQt6 for a user-friendly experience.

## Setup Instructions

### Prerequisites
-   Python 3.8+ is recommended.

### Environment Setup
1.  **Clone the repository** (if applicable).
2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    ```
3.  **Activate the virtual environment**:
    -   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```
    -   On Windows:
        ```bash
        venv\Scripts\activate
        ```

### Install Dependencies
Once the virtual environment is activated, install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application
To run the KPI Network Builder, execute the following command from the root directory of the project (`kpi_network_builder/`):
```bash
python -m src.main
```
Note: Using `python -m src.main` allows Python to correctly recognize `src` as a package, enabling relative imports within the project (like `from .gui import MainWindow`) to work as expected when `main.py` is executed. Running `python src/main.py` directly can lead to `ImportError`s for such relative imports because Python does not add the `src` directory to its path in the same way.

## Running Tests
To run the unit tests, execute the following command from the root directory of the project (`kpi_network_builder/`):
```bash
python -m unittest discover tests
```

## Basic Usage Guide
1.  **Load Schema**:
    -   Go to `File > Open Schema...`.
    -   Select your schema JSON file. The tables will appear in the "Schema Elements" panel on the left.
2.  **Visualize Tables**:
    -   Drag tables from the "Schema Elements" panel onto the main canvas area on the right.
3.  **Draw Connections**:
    -   Click on one table item on the canvas.
    -   Drag the mouse to another table item. A temporary line will appear.
    -   Release the mouse button on the target table to create a visual connection (representing a relationship like a foreign key).
4.  **Select Tables for KPI**:
    -   Select one or more tables on the canvas that are relevant to the KPI you want to define.
    -   You can select multiple tables by:
        -   Holding `Ctrl` (or `Cmd` on Mac) and clicking on individual tables.
        -   Clicking and dragging on an empty part of the canvas to draw a selection box (rubber-band selection) around the tables.
5.  **Define KPI**:
    -   Go to `KPI > Define KPI from Selection...`.
    -   A dialog will appear. Fill in the KPI metadata:
        -   KPI Name, Department, Report Name, Cadence, Description.
    -   For each table involved, select the specific fields required for the KPI from the lists provided.
    -   Click "OK".
    -   A message will confirm if the KPI was defined and whether the selected tables are connected in your visualized graph.
6.  **Save KPIs**:
    -   Go to `File > Save KPI Definitions...`.
    -   Choose a location and filename to save your defined KPIs as a JSON file.

This workflow allows you to map out your data relationships and clearly define the data requirements for your KPIs.
