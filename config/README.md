# Configuration Files

This directory contains external configuration files for the RetroArch Toolkit.

## Files

### databases.json
List of available RetroArch databases to download.

**Structure:**
```json
{
  "available_databases": [
    "System Name.rdb",
    ...
  ]
}
```

**Usage:**
- Used by `retroarch_db.py` plugin to determine which databases are available for download
- Add new database names here to support additional systems

### systems.json
System and core configurations including extensions, database mappings, and fetch sources.

**Structure:**
```json
{
  "cores": {
    "System Name": {
      "core_name": "core_libretro",
      "extensions": [".ext1", ".ext2"],
      "db_name": "System Name.rdb"
    }
  },
  "fetch_sources": {
    "source_name": {
      "enabled": true,
      "base_url": "https://..."
    }
  },
  "scan_options": {
    "recursive": true,
    "calculate_crc32": true,
    ...
  }
}
```

**Usage:**
- Used by `config.py` to load default system configurations
- Add new systems, cores, or fetch sources here
- Modify scan options to change default behavior

## Adding New Systems

To add support for a new gaming system:

1. **Add database to `databases.json`:**
   ```json
   "Manufacturer - System Name.rdb"
   ```

2. **Add system configuration to `systems.json`:**
   ```json
   "Manufacturer - System Name": {
     "core_name": "emulator_libretro",
     "extensions": [".ext1", ".ext2"],
     "db_name": "Manufacturer - System Name.rdb"
   }
   ```

3. **Test the configuration:**
   ```bash
   python main.py download-db -l
   ```

## Configuration Loading

The toolkit loads configurations in this order:

1. **External config files** (this directory)
   - `config/databases.json`
   - `config/systems.json`

2. **User config file** (`~/.config/retroarch_toolkit/config.json`)
   - User-specific paths and settings
   - Overrides system defaults

3. **Fallback defaults** (hardcoded in source)
   - Used if external config files cannot be loaded

## Benefits

- **Easy Updates**: Add new systems without modifying source code
- **Maintainability**: Separate configuration from logic
- **Extensibility**: Users can customize systems by editing JSON files
- **Version Control**: Track configuration changes separately from code
