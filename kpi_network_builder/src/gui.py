"""
Main graphical user interface for the KPI Network Builder application.

This module defines the main window, views for schema display and network canvas,
custom graphics items for tables and connections, and dialogs for KPI definition.
It uses PyQt6 for all GUI elements.

Key classes:
- `MainWindow`: The main application window, orchestrating all UI components.
- `SchemaView`: A QTreeView that displays the loaded schema (domains and tables).
- `NetworkCanvasView`: A QGraphicsView where users can drag tables and draw connections.
- `TableGraphicsItem`: A QGraphicsRectItem representing a table on the canvas.
- `ConnectionGraphicsItem`: A QGraphicsLineItem representing a connection.
- `KPIDefinitionDialog`: Dialog for users to input KPI metadata and select fields.
- `FieldSelectionWidget`: Helper widget for selecting fields from a table within the KPI dialog.
- `DraggableStandardItemModel`: Custom QStandardItemModel to support dragging tables.
"""
import sys
import pickle
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QGraphicsView, QGraphicsScene,
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFileDialog,
    QGraphicsRectItem, QGraphicsTextItem, QAbstractItemView, QGraphicsItem,
    QGraphicsLineItem, QDialog, QLineEdit, QTextEdit, QDialogButtonBox,
    QMessageBox, QListWidget, QListWidgetItem, QLabel, QScrollArea, QFormLayout,
    QComboBox
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QMimeData, QRectF, QPointF, QLineF

# Assuming .data_models and .graph_logic are resolvable.
# This structure is fine if src/ is in PYTHONPATH or if run as a module 'kpi_network_builder.src.main'
from .data_models import load_schema_from_json, Schema, Table, Domain, Field, KPI, KPIRequiredData, save_kpis_to_json
from .graph_logic import KPINetworkGraph

KPI_TABLE_MIME_TYPE = "application/x-kpi-table" # Custom MIME type for drag-drop operations

class DraggableStandardItemModel(QStandardItemModel):
    """
    Custom QStandardItemModel to enable dragging of table items.

    It defines a custom MIME type (`application/x-kpi-table`) and packages
    the table ID (domain_name, table_name) for drag operations.
    """
    def mimeTypes(self) -> list[str]:
        """Returns a list of supported MIME types, including the custom one."""
        types = super().mimeTypes()
        types.append(KPI_TABLE_MIME_TYPE)
        return types

    def mimeData(self, indexes: list[Qt.QModelIndex]) -> QMimeData | None:
        """
        Packages data from the dragged item into a QMimeData object.

        Only allows table items (children of domain items) to be dragged.
        Serializes the table_id tuple using pickle for reliable transport.

        Args:
            indexes: List of QModelIndex objects for the items being dragged (usually one).

        Returns:
            QMimeData object containing the serialized table ID, or None if drag is not allowed.
        """
        if not indexes: return None
        index = indexes[0]
        item = self.itemFromIndex(index)

        # Ensure the item is a table (must have a parent domain and the specific table_id data)
        if not item or not item.parent():
            return None
        table_id = item.data(Qt.ItemDataRole.UserRole + 2) # UserRole + 2 stores the table_id tuple
        if not table_id or not isinstance(table_id, tuple):
            return None

        mime_data = QMimeData()
        try:
            # Serialize the table_id tuple (domain_name, table_name)
            serialized_table_id = pickle.dumps(table_id)
            mime_data.setData(KPI_TABLE_MIME_TYPE, serialized_table_id)
            mime_data.setText(item.text()) # Also set plain text (table name)
        except Exception as e:
            print(f"Error serializing table_id for drag operation: {e}")
            return None
        return mime_data

class SchemaView(QWidget):
    """
    A widget that displays the data schema (domains and tables) in a tree view.

    Tables can be dragged from this view onto the NetworkCanvasView.
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.tree_view = QTreeView(self)
        self.model = DraggableStandardItemModel() # Use custom model for drag support
        self.tree_view.setModel(self.model)
        self.model.setHorizontalHeaderLabels(['Schema Elements'])

        # Configure drag-and-drop behavior
        self.tree_view.setDragEnabled(True)
        self.tree_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree_view.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly) # Only dragging from this view

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree_view)
        self.setLayout(layout)

    def load_schema(self, schema_data: Schema):
        """
        Populates the tree view with data from a `Schema` object.

        Domains are top-level items, and tables are children of their respective domains.
        Table items store their full `Table` object and `table_id` tuple for later retrieval.

        Args:
            schema_data: The `Schema` object to display.
        """
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['Schema Elements']) # Reset header
        for domain in schema_data.domains:
            domain_item = QStandardItem(domain.domain_name)
            domain_item.setData(domain, Qt.ItemDataRole.UserRole) # Store Domain object
            domain_item.setFlags(domain_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled) # Domains are not draggable
            self.model.appendRow(domain_item)

            for table_obj in domain.tables: # table_obj is a Table instance from data_models
                table_item = QStandardItem(table_obj.table_name)
                table_item.setData(table_obj, Qt.ItemDataRole.UserRole) # Store full Table object
                # table_obj.domain_name should be set correctly by load_schema_from_json
                table_id = (table_obj.domain_name, table_obj.table_name)
                table_item.setData(table_id, Qt.ItemDataRole.UserRole + 2) # For drag data
                domain_item.appendRow(table_item)

class ConnectionGraphicsItem(QGraphicsLineItem):
    """
    A QGraphicsLineItem subclass representing a visual connection between two TableGraphicsItems.
    Updates its position when connected tables are moved.
    """
    def __init__(self, source_item: 'TableGraphicsItem', target_item: 'TableGraphicsItem', parent: QGraphicsItem | None = None):
        super().__init__(parent)
        self.source_item = source_item
        self.target_item = target_item
        self.setPen(QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.setZValue(-1) # Draw lines behind table items
        self.update_position()

    def source(self) -> 'TableGraphicsItem':
        """Returns the source TableGraphicsItem of the connection."""
        return self.source_item

    def target(self) -> 'TableGraphicsItem':
        """Returns the target TableGraphicsItem of the connection."""
        return self.target_item

    def update_position(self):
        """Recalculates and sets the line's start and end points based on the centers of the connected items."""
        if not self.source_item or not self.target_item: return
        # Calculate center points of items in scene coordinates
        source_center = self.source_item.scenePos() + self.source_item.boundingRect().center()
        target_center = self.target_item.scenePos() + self.target_item.boundingRect().center()
        self.setLine(QLineF(source_center, target_center))

class TableGraphicsItem(QGraphicsRectItem):
    """
    A QGraphicsRectItem subclass representing a draggable and selectable table on the canvas.
    Displays the table name and manages its visual connections.
    """
    def __init__(self, x: float, y: float, width: float, height: float,
                 table_id: tuple[str, str], table_name: str, parent: QGraphicsItem | None = None):
        super().__init__(x, y, width, height, parent)
        self.table_id = table_id        # (domain_name, table_name)
        self.table_name = table_name
        self.connections: list[ConnectionGraphicsItem] = [] # Stores associated connections

        # Set flags for interaction
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True) # For updating connections

        # Appearance
        self.setBrush(QBrush(QColor(200, 200, 250, 180))) # Light blue, slightly transparent
        self.setPen(QPen(Qt.GlobalColor.darkBlue, 1.5))

        # Display table name centered in the rectangle
        self.text_item = QGraphicsTextItem(self.table_name, self)
        text_rect = self.text_item.boundingRect()
        rect = self.rect()
        text_x = rect.x() + (rect.width() - text_rect.width()) / 2
        text_y = rect.y() + (rect.height() - text_rect.height()) / 2
        self.text_item.setPos(text_x, text_y)

    def add_connection(self, connection_item: ConnectionGraphicsItem):
        """Adds a connection to this table item's list of managed connections."""
        self.connections.append(connection_item)

    def remove_connection(self, connection_item: ConnectionGraphicsItem):
        """Removes a connection from this table item's list."""
        if connection_item in self.connections:
            self.connections.remove(connection_item)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """
        Called by Qt when an item's state changes. Used here to update
        positions of connected lines when the table item is moved.
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            for conn in self.connections:
                conn.update_position()
        return super().itemChange(change, value)

class NetworkCanvasView(QGraphicsView):
    """
    A QGraphicsView that serves as the canvas for displaying and interacting
    with table graphics items and their connections.

    Handles drag-and-drop of tables from SchemaView, drawing of connections
    between tables, and selection of multiple tables.
    """
    def __init__(self, scene: QGraphicsScene, parent: QWidget | None = None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing) # Smooth rendering
        self.setAcceptDrops(True) # For dropping tables from SchemaView
        self.items_on_canvas: dict[tuple[str,str], TableGraphicsItem] = {} # Tracks items by table_id
        self.kpi_graph_ref: KPINetworkGraph | None = None # Reference to the logical graph

        # State for drawing connections
        self.drawing_connection: bool = False
        self.source_table_item_for_connection: TableGraphicsItem | None = None
        self.temp_line_item: QGraphicsLineItem | None = None

        # Enable rubber-band selection for multiple items
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def set_kpi_graph_ref(self, kpi_graph: KPINetworkGraph):
        """Sets a reference to the KPINetworkGraph for updating connections."""
        self.kpi_graph_ref = kpi_graph

    def clear_canvas_and_connections_state(self):
        """Clears all items from the canvas and resets connection drawing states."""
        self.scene().clear()
        self.items_on_canvas.clear()
        self.drawing_connection = False
        if self.temp_line_item and self.temp_line_item.scene():
            self.scene().removeItem(self.temp_line_item)
        self.temp_line_item = None
        self.source_table_item_for_connection = None

    def dragEnterEvent(self, event: QGraphicsSceneDragDropEvent):
        """Accepts drag events if they contain the custom table MIME type."""
        if event.mimeData().hasFormat(KPI_TABLE_MIME_TYPE): event.acceptProposedAction()
        else: super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QGraphicsSceneDragDropEvent):
        """Accepts drag move events for the custom table MIME type."""
        if event.mimeData().hasFormat(KPI_TABLE_MIME_TYPE): event.acceptProposedAction()
        else: super().dragMoveEvent(event)

    def dropEvent(self, event: QGraphicsSceneDragDropEvent):
        """
        Handles dropping a table item from the SchemaView onto the canvas.
        Creates a TableGraphicsItem for the dropped table if it's not already present.
        """
        if event.mimeData().hasFormat(KPI_TABLE_MIME_TYPE):
            event.acceptProposedAction()
            serialized_table_id = event.mimeData().data(KPI_TABLE_MIME_TYPE)
            try:
                table_id = pickle.loads(serialized_table_id)
            except Exception as e:
                print(f"Error deserializing table_id on drop: {e}"); return

            if not isinstance(table_id, tuple) or len(table_id) != 2:
                print(f"Invalid table_id format on drop: {table_id}"); return

            if table_id in self.items_on_canvas: # Prevent duplicate visual items
                print(f"Table {table_id} is already on the canvas.")
                self.items_on_canvas[table_id].setSelected(True); return

            table_name = table_id[1]
            drop_pos = self.mapToScene(event.pos())
            item_width, item_height = 150, 75

            graphics_item = TableGraphicsItem(
                drop_pos.x() - item_width / 2, drop_pos.y() - item_height / 2, # Center item
                item_width, item_height, table_id, table_name
            )
            self.scene().addItem(graphics_item)
            self.items_on_canvas[table_id] = graphics_item
            print(f"Dropped table: {table_id} at {drop_pos.x()},{drop_pos.y()}")
        else:
            super().dropEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """
        Handles mouse press events on the canvas.
        Initiates connection drawing if a TableGraphicsItem is left-clicked
        and Shift key is not pressed (Shift+Click is often for multi-selection).
        Otherwise, defers to base class for item selection/movement.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            item_at_click = self.itemAt(event.pos())
            # If Shift is pressed or no item is clicked, allow default behavior (selection, rubber-band)
            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier or not item_at_click:
                 super().mousePressEvent(event)
                 return

            if isinstance(item_at_click, TableGraphicsItem):
                # Start drawing a connection line
                self.drawing_connection = True
                self.source_table_item_for_connection = item_at_click

                line_start_pos = item_at_click.scenePos() + item_at_click.boundingRect().center()
                current_mouse_pos = self.mapToScene(event.pos())
                self.temp_line_item = QGraphicsLineItem(QLineF(line_start_pos, current_mouse_pos))
                self.temp_line_item.setPen(QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine))
                self.scene().addItem(self.temp_line_item)
                event.accept()
                return
        super().mousePressEvent(event) # Important for item moving and rubber-band selection

    def mouseMoveEvent(self, event: QMouseEvent):
        """Updates the temporary connection line's end point during a drag if drawing a connection."""
        if self.drawing_connection and self.temp_line_item and self.source_table_item_for_connection:
            line_start_pos = self.source_table_item_for_connection.scenePos() + \
                             self.source_table_item_for_connection.boundingRect().center()
            current_mouse_pos = self.mapToScene(event.pos())
            self.temp_line_item.setLine(QLineF(line_start_pos, current_mouse_pos))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Handles mouse release events on the canvas.
        Finalizes a connection if one was being drawn, creating a ConnectionGraphicsItem
        and updating the underlying KPINetworkGraph.
        """
        if event.button() == Qt.MouseButton.LeftButton and self.drawing_connection:
            self.drawing_connection = False
            if self.temp_line_item:
                self.scene().removeItem(self.temp_line_item)
                self.temp_line_item = None

            target_item = self.itemAt(event.pos())

            if isinstance(target_item, TableGraphicsItem) and \
               self.source_table_item_for_connection and \
               target_item != self.source_table_item_for_connection:

                source_node = self.source_table_item_for_connection
                target_node = target_item

                # Check for existing visual connection (simple check, graph handles logical duplicates)
                for conn in source_node.connections:
                    if conn.target() == target_node: # Assumes directed connection check
                        print(f"Visual connection from {source_node.table_id} to {target_node.table_id} already exists.")
                        self.source_table_item_for_connection = None
                        event.accept()
                        return

                new_connection = ConnectionGraphicsItem(source_node, target_node)
                self.scene().addItem(new_connection)
                source_node.add_connection(new_connection)
                target_node.add_connection(new_connection) # Store on both for updates if either moves

                if self.kpi_graph_ref:
                    self.kpi_graph_ref.add_connection(source_node.table_id, target_node.table_id)
                    print(f"Connection added to KPINetworkGraph: {source_node.table_id} -> {target_node.table_id}")
                event.accept()
            else:
                print("Connection attempt failed: No valid target or target is the source.")

            self.source_table_item_for_connection = None
            return

        # Ensure state is reset if not a connection-drawing release
        self.source_table_item_for_connection = None
        super().mouseReleaseEvent(event)

class FieldSelectionWidget(QWidget):
    """
    A widget used within the KPIDefinitionDialog to display fields of a single table
    and allow the user to select multiple fields.
    """
    def __init__(self, table: Table, parent: QWidget | None = None):
        super().__init__(parent)
        self.table = table # Table object (should have domain_name populated)

        main_layout = QVBoxLayout(self)
        # Display table name and its domain for clarity
        main_layout.addWidget(QLabel(f"<b>Fields for Table: {self.table.table_name}</b> (Domain: {self.table.domain_name})"))

        self.field_list_widget = QListWidget(self)
        self.field_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection) # Standard multi-selection

        for field_obj in self.table.fields: # field_obj is a Field instance
            item = QListWidgetItem(field_obj.field_name)
            item.setData(Qt.ItemDataRole.UserRole, field_obj) # Store the actual Field object
            self.field_list_widget.addItem(item)

        main_layout.addWidget(self.field_list_widget)
        self.setLayout(main_layout)

    def get_selected_fields(self) -> list[Field]:
        """Returns a list of the selected `Field` objects."""
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.field_list_widget.selectedItems()]

class KPIDefinitionDialog(QDialog):
    """
    A dialog for defining a new KPI.

    It allows users to input KPI metadata (name, description, etc.) and select
    required fields from the tables chosen on the NetworkCanvasView.
    """
    def __init__(self, selected_table_graphics_items: list[TableGraphicsItem],
                 kpi_graph: KPINetworkGraph, parent: QWidget | None = None):
        super().__init__(parent)
        self.selected_table_graphics_items = selected_table_graphics_items
        self.kpi_graph = kpi_graph # Used to fetch full Table objects
        self.field_selection_widgets: list[FieldSelectionWidget] = []

        self.setWindowTitle("Define New KPI")
        self.setMinimumWidth(500) # Ensure dialog is reasonably sized

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout() # For structured label-field pairs

        # KPI Metadata Input Fields
        self.kpi_name_edit = QLineEdit(self)
        self.department_edit = QLineEdit(self)
        self.report_name_edit = QLineEdit(self)
        self.cadence_combo = QComboBox(self)
        self.cadence_combo.addItems(["Daily", "Weekly", "Monthly", "Quarterly", "Annually"])
        self.description_edit = QTextEdit(self)
        self.description_edit.setPlaceholderText("Detailed description of the KPI, its purpose, calculation, etc.")

        form_layout.addRow("KPI Name:", self.kpi_name_edit)
        form_layout.addRow("Department:", self.department_edit)
        form_layout.addRow("Report Name:", self.report_name_edit)
        form_layout.addRow("Cadence:", self.cadence_combo)
        form_layout.addRow("Description:", self.description_edit)
        main_layout.addLayout(form_layout)

        # Field Selection Area for each table
        field_selection_area_label = QLabel("<b>Select Required Fields from Tables:</b>")
        main_layout.addWidget(field_selection_area_label)

        # Use a QScrollArea in case many tables/fields are selected
        scroll_content_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_content_widget)

        for t_graphics_item in self.selected_table_graphics_items:
            table_id = t_graphics_item.table_id
            try:
                # Retrieve the full Table object from the KPINetworkGraph node attributes
                table_node_data = self.kpi_graph.graph.nodes[table_id]
                table_obj: Table = table_node_data['table_obj']
                # table_obj.domain_name should be correctly set from load_schema_from_json

                fs_widget = FieldSelectionWidget(table_obj, self)
                self.field_selection_widgets.append(fs_widget)
                scroll_layout.addWidget(fs_widget)
            except KeyError:
                # This should ideally not happen if tables on canvas are always in the graph
                print(f"Error: Table object not found in graph for ID: {table_id} during KPI dialog setup.")
                error_label = QLabel(f"<font color='red'>Could not load fields for table: {table_id[0]}.{table_id[1]}</font>")
                scroll_layout.addWidget(error_label)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content_widget)
        main_layout.addWidget(scroll_area)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def get_kpi_data(self) -> KPI | None:
        """
        Collects data from the dialog fields and constructs a `KPI` object.

        Performs basic validation (KPI name and at least one field selected).

        Returns:
            KPI: The constructed `KPI` object if dialog was accepted and data is valid.
            None: If dialog was cancelled or data is invalid.
        """
        if not self.kpi_name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "KPI Name cannot be empty.")
            return None

        kpi_name = self.kpi_name_edit.text().strip()
        department = self.department_edit.text().strip()
        report_name = self.report_name_edit.text().strip()
        cadence = self.cadence_combo.currentText()
        description = self.description_edit.toPlainText().strip()

        data_required_list: list[KPIRequiredData] = []
        for fs_widget in self.field_selection_widgets:
            # fs_widget.table is the Table object, which has domain_name and table_name
            table_domain = fs_widget.table.domain_name
            table_name = fs_widget.table.table_name
            selected_field_objects = fs_widget.get_selected_fields() # Returns list of Field objects

            for field_obj in selected_field_objects:
                data_required_list.append(KPIRequiredData(
                    domain_name=table_domain,
                    table_name=table_name,
                    field_name=field_obj.field_name
                ))

        if not data_required_list:
             QMessageBox.warning(self, "Validation Error", "At least one field must be selected for the KPI.")
             return None

        return KPI(
            kpi_name=kpi_name, department=department, report_name=report_name,
            cadence=cadence, description=description, data_required=data_required_list
        )

class MainWindow(QMainWindow):
    """
    The main application window.

    Manages the overall layout, menus, actions, and interactions between
    the SchemaView, NetworkCanvasView, and various dialogs.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KPI Network Builder")
        self.setGeometry(100, 100, 1200, 800) # Default window size

        self.kpi_graph = KPINetworkGraph() # Logical graph representation
        self.graphics_scene = QGraphicsScene(self) # Scene for the canvas view

        self.schema_view = SchemaView(self) # Left panel for schema display
        self.network_canvas_view = NetworkCanvasView(self.graphics_scene, self) # Right panel for graph viz
        self.network_canvas_view.set_kpi_graph_ref(self.kpi_graph) # Link canvas to logical graph

        self.defined_kpis: list[KPI] = [] # Stores KPIs defined in the current session

        # Main layout with a splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.schema_view)
        splitter.addWidget(self.network_canvas_view)
        splitter.setSizes([300, 900]) # Initial size ratio for left and right panels
        self.setCentralWidget(splitter)

        self._create_menus()

    def _create_menus(self):
        """Creates the main menu bar and actions."""
        # File Menu
        file_menu = self.menuBar().addMenu("&File")
        open_schema_action = QAction("&Open Schema...", self)
        open_schema_action.triggered.connect(self.load_schema_action)
        file_menu.addAction(open_schema_action)

        save_kpi_action = QAction("&Save KPI Definitions...", self)
        save_kpi_action.triggered.connect(self.save_kpi_action_triggered)
        file_menu.addAction(save_kpi_action)

        file_menu.addSeparator()
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close) # Built-in QMainWindow close
        file_menu.addAction(exit_action)

        # KPI Menu
        kpi_menu = self.menuBar().addMenu("&KPI")
        define_kpi_action = QAction("&Define KPI from Selection", self)
        define_kpi_action.setToolTip("Define a new KPI based on currently selected tables on the canvas.")
        define_kpi_action.triggered.connect(self.define_kpi_action_triggered)
        kpi_menu.addAction(define_kpi_action)

    def load_schema_action(self):
        """
        Handles the 'Open Schema' action.
        Opens a file dialog to select a schema JSON file, loads it,
        populates the SchemaView, and resets the KPINetworkGraph and canvas.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Schema JSON File", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                # data_models.load_schema_from_json now sets table.domain_name
                schema_data = load_schema_from_json(file_path)
                self.schema_view.load_schema(schema_data)

                # Reset current graph, canvas, and KPIs
                self.kpi_graph = KPINetworkGraph()
                self.network_canvas_view.clear_canvas_and_connections_state()
                self.defined_kpis = []

                # Populate the logical graph with tables from the loaded schema
                for domain in schema_data.domains:
                    for table_obj in domain.tables: # table_obj has domain_name set
                        self.kpi_graph.add_table_node(table_obj.domain_name, table_obj.table_name, table_obj)

                self.network_canvas_view.set_kpi_graph_ref(self.kpi_graph) # Update graph reference in canvas
                QMessageBox.information(self, "Schema Loaded", f"Schema successfully loaded from {file_path}.")
                print(f"Schema loaded. Graph populated. Canvas cleared. Defined KPIs reset.")
            except Exception as e:
                QMessageBox.critical(self, "Schema Load Error", f"Failed to load schema from {file_path}: {e}")
                print(f"Error loading schema: {e}")

    def save_kpi_action_triggered(self):
        """
        Handles the 'Save KPI Definitions' action.
        Opens a file dialog to save the currently defined KPIs to a JSON file.
        """
        if not self.defined_kpis:
            QMessageBox.information(self, "No KPIs Defined", "There are no KPIs defined in the current session to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save KPI Definitions", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                # data_models.save_kpis_to_json uses asdict for serialization
                save_kpis_to_json(self.defined_kpis, file_path)
                QMessageBox.information(self, "KPIs Saved", f"Successfully saved {len(self.defined_kpis)} KPI(s) to {file_path}.")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save KPI definitions to {file_path}: {e}")
                print(f"Error saving KPIs: {e}")

    def define_kpi_action_triggered(self):
        """
        Handles the 'Define KPI from Selection' action.
        Gathers selected tables from the canvas, opens the KPIDefinitionDialog,
        and processes the resulting KPI definition.
        """
        selected_graphics_items = [
            item for item in self.network_canvas_view.scene().selectedItems()
            if isinstance(item, TableGraphicsItem)
        ]

        if not selected_graphics_items:
            QMessageBox.warning(self, "No Tables Selected",
                                "Please select one or more tables on the canvas to define a KPI.")
            return

        # Pass the KPINetworkGraph instance which holds the table_obj attributes
        dialog = KPIDefinitionDialog(selected_graphics_items, self.network_canvas_view.kpi_graph_ref, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_kpi = dialog.get_kpi_data()
            if new_kpi:
                self.defined_kpis.append(new_kpi)

                # Perform connectivity check for the tables involved in the new KPI
                table_ids_for_check = list(set([(req.domain_name, req.table_name) for req in new_kpi.data_required]))

                # Verify all tables for the KPI are actually on the canvas (and thus in the graph)
                # This is mostly a sanity check as selection comes from canvas items.
                all_required_tables_on_canvas = all(
                    (dom, tab) in self.network_canvas_view.items_on_canvas for dom, tab in table_ids_for_check
                )

                if not all_required_tables_on_canvas: # Should be rare if selection is from canvas
                    QMessageBox.warning(self, "KPI Definition Issue",
                                        f"KPI '{new_kpi.kpi_name}' defined, but not all its required tables "
                                        "seem to be on the canvas. Connectivity check might be unreliable.")
                    # Proceed with caution or disallow if this state is problematic

                is_connected = self.network_canvas_view.kpi_graph_ref.all_tables_connected(table_ids_for_check)

                msg = (f"KPI '{new_kpi.kpi_name}' defined successfully.\n"
                       f"Number of tables involved: {len(table_ids_for_check)}.\n"
                       f"Tables are connected in the graph: {'Yes' if is_connected else 'No'}.")

                QMessageBox.information(self, "KPI Defined", msg)
                print(f"Defined KPI: {new_kpi.kpi_name}, Connected: {is_connected}, Data: {new_kpi.data_required}")

                # Optionally, clear selection on canvas after defining KPI
                # self.network_canvas_view.scene().clearSelection()
            else:
                # This case occurs if get_kpi_data returned None (e.g., validation error in dialog)
                QMessageBox.warning(self, "KPI Not Defined",
                                    "Failed to define KPI. Please ensure all required information is provided and valid.")

if __name__ == '__main__': # pragma: no cover
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
