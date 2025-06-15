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
from typing import Any # Added import
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QGraphicsView, QGraphicsScene,
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFileDialog,
    QGraphicsRectItem, QGraphicsTextItem, QAbstractItemView, QGraphicsItem,
    QGraphicsLineItem, QDialog, QLineEdit, QTextEdit, QDialogButtonBox,
    QMessageBox, QListWidget, QListWidgetItem, QLabel, QScrollArea, QFormLayout,
    QComboBox
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction, QPainter, QColor, QBrush, QPen
# Ensure QModelIndex is imported directly if used in type hints explicitly after Qt
from PyQt6.QtCore import Qt, QMimeData, QRectF, QPointF, QLineF, QModelIndex

# Assuming .data_models and .graph_logic are resolvable.
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

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData | None: # Corrected type hint for QModelIndex
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

        if not item or not item.parent():
            return None
        # Using Qt.UserRole (from PyQt6.QtCore.Qt)
        table_id = item.data(Qt.ItemDataRole.UserRole + 2)
        if not table_id or not isinstance(table_id, tuple):
            return None

        mime_data = QMimeData()
        try:
            serialized_table_id = pickle.dumps(table_id)
            mime_data.setData(KPI_TABLE_MIME_TYPE, serialized_table_id)
            mime_data.setText(item.text())
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
        self.model = DraggableStandardItemModel()
        self.tree_view.setModel(self.model)
        self.model.setHorizontalHeaderLabels(['Schema Elements'])

        self.tree_view.setDragEnabled(True)
        self.tree_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree_view.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree_view)
        self.setLayout(layout)

    def load_schema(self, schema_data: Schema):
        """
        Populates the tree view with data from a `Schema` object.
        """
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['Schema Elements'])
        for domain in schema_data.domains:
            domain_item = QStandardItem(domain.domain_name)
            # Using Qt.UserRole
            domain_item.setData(domain, Qt.ItemDataRole.UserRole)
            # Using Qt.ItemIsDragEnabled
            domain_item.setFlags(domain_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            self.model.appendRow(domain_item)

            for table_obj in domain.tables:
                table_item = QStandardItem(table_obj.table_name)
                # Using Qt.UserRole
                table_item.setData(table_obj, Qt.ItemDataRole.UserRole)
                table_id = (table_obj.domain_name, table_obj.table_name)
                # Using Qt.UserRole
                table_item.setData(table_id, Qt.ItemDataRole.UserRole + 2)
                domain_item.appendRow(table_item)

class ConnectionGraphicsItem(QGraphicsLineItem):
    """
    A QGraphicsLineItem subclass representing a visual connection between two TableGraphicsItems.
    """
    def __init__(self, source_item: 'TableGraphicsItem', target_item: 'TableGraphicsItem', parent: QGraphicsItem | None = None):
        super().__init__(parent)
        self.source_item = source_item
        self.target_item = target_item
        # Using Qt.GlobalColor, Qt.PenStyle, Qt.PenCapStyle, Qt.PenJoinStyle
        self.setPen(QPen(Qt.GlobalColor.white, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.setZValue(-1)
        self.update_position()

    def source(self) -> 'TableGraphicsItem':
        return self.source_item

    def target(self) -> 'TableGraphicsItem':
        return self.target_item

    def update_position(self):
        if not self.source_item or not self.target_item: return
        source_center = self.source_item.scenePos() + self.source_item.boundingRect().center()
        target_center = self.target_item.scenePos() + self.target_item.boundingRect().center()
        self.setLine(QLineF(source_center, target_center))

class TableGraphicsItem(QGraphicsRectItem):
    """
    A QGraphicsRectItem subclass representing a draggable and selectable table on the canvas.
    """
    def __init__(self, x: float, y: float, width: float, height: float,
                 table_id: tuple[str, str], table_name: str, parent: QGraphicsItem | None = None):
        super().__init__(x, y, width, height, parent)
        self.table_id = table_id
        self.table_name = table_name
        self.connections: list[ConnectionGraphicsItem] = []

        # Using QGraphicsItem.GraphicsItemFlag
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # Using Qt.GlobalColor
        self.setBrush(QBrush(QColor(200, 200, 250, 180)))
        self.setPen(QPen(Qt.GlobalColor.darkBlue, 1.5))

        self.text_item = QGraphicsTextItem(self.table_name, self)
        text_rect = self.text_item.boundingRect()
        rect = self.rect()
        text_x = rect.x() + (rect.width() - text_rect.width()) / 2
        text_y = rect.y() + (rect.height() - text_rect.height()) / 2
        self.text_item.setPos(text_x, text_y)

    def add_connection(self, connection_item: ConnectionGraphicsItem):
        self.connections.append(connection_item)

    def remove_connection(self, connection_item: ConnectionGraphicsItem):
        if connection_item in self.connections:
            self.connections.remove(connection_item)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        # Using QGraphicsItem.GraphicsItemChange
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            for conn in self.connections:
                conn.update_position()
        return super().itemChange(change, value)

class NetworkCanvasView(QGraphicsView):
    """
    A QGraphicsView that serves as the canvas for displaying and interacting
    with table graphics items and their connections.
    """
    def __init__(self, scene: QGraphicsScene, parent: QWidget | None = None):
        super().__init__(scene, parent)
        # Using QPainter.RenderHint
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAcceptDrops(True)
        self.items_on_canvas: dict[tuple[str,str], TableGraphicsItem] = {}
        self.kpi_graph_ref: KPINetworkGraph | None = None

        self.drawing_connection: bool = False
        self.source_table_item_for_connection: TableGraphicsItem | None = None
        self.temp_line_item: QGraphicsLineItem | None = None

        # Using QGraphicsView.DragMode
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def set_kpi_graph_ref(self, kpi_graph: KPINetworkGraph):
        self.kpi_graph_ref = kpi_graph

    def clear_canvas_and_connections_state(self):
        self.scene().clear()
        self.items_on_canvas.clear()
        self.drawing_connection = False
        if self.temp_line_item and self.temp_line_item.scene():
            self.scene().removeItem(self.temp_line_item)
        self.temp_line_item = None
        self.source_table_item_for_connection = None

    def dragEnterEvent(self, event: 'QGraphicsSceneDragDropEvent'): # QGraphicsSceneDragDropEvent from QtWidgets
        if event.mimeData().hasFormat(KPI_TABLE_MIME_TYPE): event.acceptProposedAction()
        else: super().dragEnterEvent(event)

    def dragMoveEvent(self, event: 'QGraphicsSceneDragDropEvent'):
        if event.mimeData().hasFormat(KPI_TABLE_MIME_TYPE): event.acceptProposedAction()
        else: super().dragMoveEvent(event)

    def dropEvent(self, event: 'QGraphicsSceneDragDropEvent'):
        if event.mimeData().hasFormat(KPI_TABLE_MIME_TYPE):
            event.acceptProposedAction()
            serialized_table_id = event.mimeData().data(KPI_TABLE_MIME_TYPE)
            try:
                table_id = pickle.loads(serialized_table_id)
            except Exception as e:
                print(f"Error deserializing table_id on drop: {e}"); return

            if not isinstance(table_id, tuple) or len(table_id) != 2:
                print(f"Invalid table_id format on drop: {table_id}"); return

            if table_id in self.items_on_canvas:
                print(f"Table {table_id} is already on the canvas.")
                self.items_on_canvas[table_id].setSelected(True); return

            table_name = table_id[1]
            # QDropEvent.position() returns QPointF. mapToScene expects QPoint.
            # Explicitly convert QPointF to QPoint using .toPoint()
            drop_pos = self.mapToScene(event.position().toPoint())
            item_width, item_height = 150, 75

            graphics_item = TableGraphicsItem(
                drop_pos.x() - item_width / 2, drop_pos.y() - item_height / 2,
                item_width, item_height, table_id, table_name
            )
            self.scene().addItem(graphics_item)
            self.items_on_canvas[table_id] = graphics_item
            print(f"Dropped table: {table_id} at {drop_pos.x()},{drop_pos.y()}")
        else:
            super().dropEvent(event)

    def mousePressEvent(self, event: 'QMouseEvent'): # QMouseEvent from QtGui
        # Using Qt.MouseButton and Qt.KeyboardModifier
        if event.button() == Qt.MouseButton.LeftButton:
            item_at_click = self.itemAt(event.pos())
            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier or not item_at_click:
                 super().mousePressEvent(event)
                 return

            if isinstance(item_at_click, TableGraphicsItem):
                self.drawing_connection = True
                self.source_table_item_for_connection = item_at_click

                line_start_pos = item_at_click.scenePos() + item_at_click.boundingRect().center()
                current_mouse_pos = self.mapToScene(event.pos())
                self.temp_line_item = QGraphicsLineItem(QLineF(line_start_pos, current_mouse_pos))
                # Using Qt.GlobalColor and Qt.PenStyle
                self.temp_line_item.setPen(QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine))
                self.scene().addItem(self.temp_line_item)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: 'QMouseEvent'):
        if self.drawing_connection and self.temp_line_item and self.source_table_item_for_connection:
            line_start_pos = self.source_table_item_for_connection.scenePos() + \
                             self.source_table_item_for_connection.boundingRect().center()
            current_mouse_pos = self.mapToScene(event.pos())
            self.temp_line_item.setLine(QLineF(line_start_pos, current_mouse_pos))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: 'QMouseEvent'):
        # Using Qt.MouseButton
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

                for conn in source_node.connections:
                    if conn.target() == target_node:
                        print(f"Visual connection from {source_node.table_id} to {target_node.table_id} already exists.")
                        self.source_table_item_for_connection = None
                        event.accept()
                        return

                new_connection = ConnectionGraphicsItem(source_node, target_node)
                self.scene().addItem(new_connection)
                source_node.add_connection(new_connection)
                target_node.add_connection(new_connection)

                if self.kpi_graph_ref:
                    self.kpi_graph_ref.add_connection(source_node.table_id, target_node.table_id)
                    print(f"Connection added to KPINetworkGraph: {source_node.table_id} -> {target_node.table_id}")
                event.accept()
            else:
                print("Connection attempt failed: No valid target or target is the source.")

            self.source_table_item_for_connection = None
            return

        self.source_table_item_for_connection = None
        super().mouseReleaseEvent(event)

class FieldSelectionWidget(QWidget):
    """
    A widget used within the KPIDefinitionDialog to display fields of a single table
    and allow the user to select multiple fields.
    """
    def __init__(self, table: Table, parent: QWidget | None = None):
        super().__init__(parent)
        self.table = table

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(QLabel(f"<b>Fields for Table: {self.table.table_name}</b> (Domain: {self.table.domain_name})"))

        self.field_list_widget = QListWidget(self)
        # Using QAbstractItemView.SelectionMode
        self.field_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        for field_obj in self.table.fields:
            item = QListWidgetItem(field_obj.field_name)
            # Using Qt.UserRole
            item.setData(Qt.ItemDataRole.UserRole, field_obj)
            self.field_list_widget.addItem(item)

        main_layout.addWidget(self.field_list_widget)
        self.setLayout(main_layout)

    def get_selected_fields(self) -> list[Field]:
        # Using Qt.UserRole
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.field_list_widget.selectedItems()]

class KPIDefinitionDialog(QDialog):
    """
    A dialog for defining a new KPI.
    """
    def __init__(self, selected_table_graphics_items: list[TableGraphicsItem],
                 kpi_graph: KPINetworkGraph, parent: QWidget | None = None):
        super().__init__(parent)
        self.selected_table_graphics_items = selected_table_graphics_items
        self.kpi_graph = kpi_graph
        self.field_selection_widgets: list[FieldSelectionWidget] = []

        self.setWindowTitle("Define New KPI")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

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

        field_selection_area_label = QLabel("<b>Select Required Fields from Tables:</b>")
        main_layout.addWidget(field_selection_area_label)

        scroll_content_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_content_widget)

        for t_graphics_item in self.selected_table_graphics_items:
            table_id = t_graphics_item.table_id
            try:
                table_node_data = self.kpi_graph.graph.nodes[table_id]
                table_obj: Table = table_node_data['table_obj']

                fs_widget = FieldSelectionWidget(table_obj, self)
                self.field_selection_widgets.append(fs_widget)
                scroll_layout.addWidget(fs_widget)
            except KeyError:
                print(f"Error: Table object not found in graph for ID: {table_id} during KPI dialog setup.")
                error_label = QLabel(f"<font color='red'>Could not load fields for table: {table_id[0]}.{table_id[1]}</font>")
                scroll_layout.addWidget(error_label)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content_widget)
        main_layout.addWidget(scroll_area)

        # Using QDialogButtonBox.StandardButton
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def get_kpi_data(self) -> KPI | None:
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
            table_domain = fs_widget.table.domain_name
            table_name = fs_widget.table.table_name
            selected_field_objects = fs_widget.get_selected_fields()

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
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KPI Network Builder")
        self.setGeometry(100, 100, 1200, 800)

        self.kpi_graph = KPINetworkGraph()
        self.graphics_scene = QGraphicsScene(self)

        self.schema_view = SchemaView(self)
        self.network_canvas_view = NetworkCanvasView(self.graphics_scene, self)
        self.network_canvas_view.set_kpi_graph_ref(self.kpi_graph)

        self.defined_kpis: list[KPI] = []

        # Using Qt.Orientation
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.schema_view)
        splitter.addWidget(self.network_canvas_view)
        splitter.setSizes([300, 900])
        self.setCentralWidget(splitter)

        self._create_menus()

    def _create_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        open_schema_action = QAction("&Open Schema...", self)
        open_schema_action.triggered.connect(self.load_schema_action)
        file_menu.addAction(open_schema_action)

        save_kpi_action = QAction("&Save KPI Definitions...", self)
        save_kpi_action.triggered.connect(self.save_kpi_action_triggered)
        file_menu.addAction(save_kpi_action)

        file_menu.addSeparator()
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        kpi_menu = self.menuBar().addMenu("&KPI")
        define_kpi_action = QAction("&Define KPI from Selection", self)
        define_kpi_action.setToolTip("Define a new KPI based on currently selected tables on the canvas.")
        define_kpi_action.triggered.connect(self.define_kpi_action_triggered)
        kpi_menu.addAction(define_kpi_action)

    def load_schema_action(self):
        # Using QFileDialog.getOpenFileName
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Schema JSON File", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                schema_data = load_schema_from_json(file_path)
                self.schema_view.load_schema(schema_data)

                self.kpi_graph = KPINetworkGraph()
                self.network_canvas_view.clear_canvas_and_connections_state()
                self.defined_kpis = []

                for domain in schema_data.domains:
                    for table_obj in domain.tables:
                        self.kpi_graph.add_table_node(table_obj.domain_name, table_obj.table_name, table_obj)

                self.network_canvas_view.set_kpi_graph_ref(self.kpi_graph)
                QMessageBox.information(self, "Schema Loaded", f"Schema successfully loaded from {file_path}.")
                print(f"Schema loaded. Graph populated. Canvas cleared. Defined KPIs reset.")
            except Exception as e:
                QMessageBox.critical(self, "Schema Load Error", f"Failed to load schema from {file_path}: {e}")
                print(f"Error loading schema: {e}")

    def save_kpi_action_triggered(self):
        if not self.defined_kpis:
            QMessageBox.information(self, "No KPIs Defined", "There are no KPIs defined in the current session to save.")
            return

        # Using QFileDialog.getSaveFileName
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save KPI Definitions", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                save_kpis_to_json(self.defined_kpis, file_path)
                QMessageBox.information(self, "KPIs Saved", f"Successfully saved {len(self.defined_kpis)} KPI(s) to {file_path}.")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save KPI definitions to {file_path}: {e}")
                print(f"Error saving KPIs: {e}")

    def define_kpi_action_triggered(self):
        selected_graphics_items = [
            item for item in self.network_canvas_view.scene().selectedItems()
            if isinstance(item, TableGraphicsItem)
        ]

        if not selected_graphics_items:
            QMessageBox.warning(self, "No Tables Selected",
                                "Please select one or more tables on the canvas to define a KPI.")
            return

        dialog = KPIDefinitionDialog(selected_graphics_items, self.network_canvas_view.kpi_graph_ref, self)

        # Using QDialog.DialogCode
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_kpi = dialog.get_kpi_data()
            if new_kpi:
                self.defined_kpis.append(new_kpi)

                table_ids_for_check = list(set([(req.domain_name, req.table_name) for req in new_kpi.data_required]))

                all_required_tables_on_canvas = all(
                    (dom, tab) in self.network_canvas_view.items_on_canvas for dom, tab in table_ids_for_check
                )

                if not all_required_tables_on_canvas:
                    QMessageBox.warning(self, "KPI Definition Issue",
                                        f"KPI '{new_kpi.kpi_name}' defined, but not all its required tables "
                                        "seem to be on the canvas. Connectivity check might be unreliable.")

                is_connected = self.network_canvas_view.kpi_graph_ref.all_tables_connected(table_ids_for_check)

                msg = (f"KPI '{new_kpi.kpi_name}' defined successfully.\n"
                       f"Number of tables involved: {len(table_ids_for_check)}.\n"
                       f"Tables are connected in the graph: {'Yes' if is_connected else 'No'}.")

                QMessageBox.information(self, "KPI Defined", msg)
                print(f"Defined KPI: {new_kpi.kpi_name}, Connected: {is_connected}, Data: {new_kpi.data_required}")

            else:
                QMessageBox.warning(self, "KPI Not Defined",
                                    "Failed to define KPI. Please ensure all required information is provided and valid.")

if __name__ == '__main__': # pragma: no cover
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

[end of kpi_network_builder/src/gui.py]

[end of kpi_network_builder/src/gui.py]
