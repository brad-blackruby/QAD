# CLAUDE.md - QAD (Quantum Aided Design)

## Project Overview

QAD is a QGIS 3.x plugin that provides AutoCAD-like drawing and editing commands for vector layers. It brings professional CAD tools (line, circle, arc, fillet, trim, extend, dimensioning, etc.) into the QGIS environment.

- **Version**: 3.0.7
- **License**: GNU General Public License v3
- **QGIS Compatibility**: 3.40 – 3.99
- **Language**: Python 3 (PyQt5 via QGIS bindings)
- **Author**: gam17
- **Repository**: https://github.com/gam17/QAD

## Repository Structure

```
QAD/
├── __init__.py              # Plugin entry point (classFactory → Qad)
├── qad.py                   # Main plugin class (Qad) - UI, toolbars, menus, command dispatch
├── qad_commands.py          # Command dispatcher (QadCommandsClass)
├── qad_variables.py         # 60+ CAD-like system variables (QadVariables)
├── qad_utils.py             # General utility functions
├── qad_entity.py            # Entity abstraction for geometric objects
├── qad_layer.py             # Layer operations and status tracking
├── qad_dim.py               # Dimension engine (largest file ~319KB)
├── qad_getpoint.py          # Interactive point selection with snapping
├── qad_maptool.py           # Map tool base class for canvas interaction
├── qad_dynamicinput.py      # Dynamic input interface (real-time coordinate feedback)
├── qad_textwindow.py        # Command-line style text input window
├── qad_snapper.py           # Snap point detection and visualization
├── qad_undoredo.py          # Undo/redo stack management
├── qad_rubberband.py        # Visual feedback for geometry preview
├── qad_grip.py              # Grip/handle visualization for selected objects
├── qad_msg.py               # Message translation and help display
├── qad_shortcuts.py         # Keyboard shortcuts handling
│
├── # Geometry modules
├── qad_line.py              # QadLine class
├── qad_circle.py            # QadCircle class
├── qad_arc.py               # QadArc class
├── qad_ellipse.py           # QadEllipse class
├── qad_polyline.py          # QadPolyline class
├── qad_multi_geom.py        # Multi-geometry support
├── qad_geom_relations.py    # Geometric relationship calculations (~223KB)
├── qad_circle_fun.py        # Circle operation functions
├── qad_offset_fun.py        # Offset operation functions
├── qad_fillet_fun.py        # Fillet/rounding functions
├── qad_extend_trim_fun.py   # Extend/trim functions
├── qad_stretch_fun.py       # Stretch transformation functions
├── qad_array_fun.py         # Array/duplication functions
├── qad_join_fun.py          # Join/merge functions
├── qad_break_fun.py         # Break/split functions
│
├── # Dialog modules
├── qad_options_dlg.py       # Plugin options dialog
├── qad_dsettings_dlg.py     # Drafting settings dialog
├── qad_dimstyle_details_dlg.py  # Dimension style management
├── qad_*_ui.py              # Compiled Qt Designer UI files
├── qad_rc.py                # Compiled Qt resource file (icons)
│
├── cmd/                     # Command implementations (65 files)
│   ├── qad_generic_cmd.py   # Base class QadCommandClass
│   ├── qad_line_cmd.py      # LINE command
│   ├── qad_circle_cmd.py    # CIRCLE command
│   ├── qad_arc_cmd.py       # ARC command
│   ├── qad_*_cmd.py         # Other command implementations
│   └── qad_*_maptool.py     # Map tools paired with commands
│
├── help/                    # Documentation (HTML + PDF)
│   ├── help_en/             # English help files
│   └── help_it/             # Italian help files
│
├── i18n/                    # Translations (7 languages)
│   ├── qad_it.ts/.qm       # Italian
│   ├── qad_es.ts/.qm       # Spanish
│   ├── qad_fi.ts/.qm       # Finnish
│   ├── qad_fr.ts/.qm       # French
│   ├── qad_pt_br.ts/.qm    # Portuguese (Brazil)
│   ├── qad_de.ts            # German
│   └── Qad.pro              # Qt translation project file
│
├── icons/                   # SVG icon files for UI
├── sample_data/             # Sample QGIS project and shapefiles
├── support/                 # Support files (PGP)
│
├── metadata.txt             # QGIS plugin metadata
├── Makefile                 # Resource compilation (pyrcc4)
├── changelog                # Version history
├── LICENSE                  # GPLv3
└── README.md                # Brief project description
```

## Build and Development

### Dependencies

QAD has no external Python dependencies beyond what QGIS provides:
- **QGIS Core/GUI API**: `qgis.core`, `qgis.gui`, `qgis.utils`
- **PyQt5**: accessed via `qgis.PyQt.QtCore`, `qgis.PyQt.QtGui`, `qgis.PyQt.QtWidgets`
- **Python stdlib**: `math`, `os`, `sys`, `configparser`, `re`, `time`, `uuid`, etc.

No `requirements.txt`, `setup.py`, or `pyproject.toml` exists. The plugin relies entirely on the QGIS runtime environment.

### Building Resources

```bash
make              # Compiles .qrc resource files to _rc.py using pyrcc4
make clean        # Removes compiled resource files
```

Windows batch files are also available:
- `compila_risorse.bat` - Compiles resources
- `compila_ui.bat` - Compiles UI files

### Installation for Development

1. Symlink or copy the `QAD/` directory into your QGIS plugins folder:
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Restart QGIS and enable QAD in the Plugin Manager.

### Testing

There is no automated test suite (no pytest, unittest, or CI/CD pipeline). Testing is done manually within QGIS using sample data in `sample_data/`.

## Architecture and Key Patterns

### Plugin Entry Point

`__init__.py` defines `classFactory(iface)` which returns a `Qad` instance. The `Qad` class in `qad.py` is the main plugin class managing the entire lifecycle: toolbars, menus, map tools, text window, and command execution.

### Command Pattern

All CAD commands inherit from `QadCommandClass` (in `cmd/qad_generic_cmd.py`). Commands are stateful objects that:
- Are registered in `qad_commands.py` via `QadCommandsClass`
- Manage their own step-by-step lifecycle (prompts, input, execution)
- Can have associated `MapTool` classes for canvas interaction

The naming convention for command files:
- `cmd/qad_<name>_cmd.py` - Command implementation
- `cmd/qad_<name>_maptool.py` - Associated map tool (if interactive)

### Geometry System

QAD defines its own geometry classes that wrap/extend QGIS geometry:
- `QadLine`, `QadCircle`, `QadArc`, `QadEllipse`, `QadPolyline`
- Heavy computation in `qad_geom_relations.py` (intersections, distances, projections)
- Function modules (`*_fun.py`) contain stateless geometric operations

### Map Tools and User Input

- `QadGetPoint` (`qad_getpoint.py`) handles interactive point selection with snapping
- `QadMapTool` (`qad_maptool.py`) is the base class for canvas interaction
- `QadDynamicInput` (`qad_dynamicinput.py`) provides real-time coordinate tooltips
- `QadSnapper` (`qad_snapper.py`) implements snap modes (endpoint, midpoint, center, tangent, intersection, etc.)

### System Variables

`qad_variables.py` manages 60+ CAD-like system variables (types: STRING, COLOR, INT, FLOAT, BOOL). These control snap modes, colors, sizes, tracking behavior, and more. Configuration is persisted to `qad.ini`.

### Internationalization

- Translations use `QadMsg.translate(context, text)`
- Source `.ts` files and compiled `.qm` files in `i18n/`
- Supported languages: English (default), Italian, Spanish, Finnish, French, Portuguese-BR, German

## Code Conventions

### Naming

- **Classes**: PascalCase, often with `Class` suffix (e.g., `QadCommandClass`, `QadEntitySet`)
- **Enums**: PascalCase with `Enum` suffix (e.g., `QadSnapTypeEnum`, `QadInputModeEnum`)
- **Functions/Methods**: mixed camelCase and snake_case (legacy codebase)
- **Constants**: UPPER_CASE within enum classes
- **Module files**: `qad_<feature>.py` or `qad_<feature>_<type>.py`
- **All module files** use the `qad_` prefix

### Code Style

- UTF-8 encoding with `# -*- coding: utf-8 -*-` header on all files
- Comments appear in both Italian and English throughout the codebase
- No linter or formatter configuration (no flake8, pylint, black, etc.)
- Double underscore (`self.__name`) for private attributes, single underscore (`self._name`) for protected
- GPL license header at the top of every source file

### Import Style

- QGIS/PyQt imports use `from qgis.PyQt.QtCore import ...` (not direct PyQt5 imports)
- Relative imports within the plugin package (e.g., `from .qad_utils import ...`)
- Commands use parent-relative imports (e.g., `from ..qad_msg import QadMsg`)

## Key Files by Size (Complexity Indicators)

| File | Size | Description |
|------|------|-------------|
| `qad_dim.py` | ~319KB | Full dimensioning engine (most complex) |
| `qad_geom_relations.py` | ~223KB | Geometric relationship calculations |
| `qad_dynamicinput.py` | ~185KB | Dynamic input interface |
| `qad_variables.py` | ~105KB | System variables management |
| `qad.py` | ~101KB | Main plugin class |
| `qad_utils.py` | ~97KB | General utilities |
| `qad_fillet_fun.py` | ~75KB | Fillet operations |
| `qad_offset_fun.py` | ~74KB | Offset operations |
| `qad_snapper.py` | ~73KB | Snap detection |
| `qad_getpoint.py` | ~73KB | Point selection |

## Common Tasks

### Adding a New Command

1. Create `cmd/qad_<name>_cmd.py` with a class inheriting from `QadCommandClass`
2. If the command needs canvas interaction, create `cmd/qad_<name>_maptool.py`
3. Register the command in `qad_commands.py`
4. Add toolbar/menu entries in `qad.py` if needed
5. Add icon SVG to `icons/` if a toolbar button is required
6. Add translations to `.ts` files in `i18n/`

### Adding a Translation

1. Add string entries using `QadMsg.translate(context, text)` in code
2. Run `lupdate` (via `i18n/lupdate.bat` or manually) to extract strings to `.ts` files
3. Translate strings in the `.ts` file for the target language
4. Compile with `lrelease` (via `i18n/lrelease.bat`) to produce `.qm` files

### Modifying Geometry Operations

- Core geometry classes are in root-level `qad_<shape>.py` files
- Stateless operations go in `qad_<feature>_fun.py` function modules
- Relationship calculations (intersections, distances) go in `qad_geom_relations.py`
