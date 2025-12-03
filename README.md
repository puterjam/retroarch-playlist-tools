# retroarch playlist creator (mac only)

一个强大的 Python 工具，用于规范化和美化 RetroArch 本地 ROM 资源和 playlist。

## 功能特性

### 核心功能

1. **ROM 扫描工具**
   - 自动扫描 RetroArch ROMs 目录
   - 支持递归扫描子目录
   - 计算 ROM 文件的 CRC32 校验和
   - 支持压缩文件（ZIP, 7z）

2. **智能文件名规范化**
   - 自动识别公版和 Hack 版本
   - 规范化 ROM 文件名
   - 提取区域信息（USA, Japan, Europe 等）
   - 识别游戏修改版本

3. **数据库匹配**
   - 从 RetroArch 官方数据库匹配游戏
   - CRC32 精确匹配
   - 文件名模糊匹配
   - 支持 www.romhacking.net 等游戏数据库

4. **缩略图下载**
   - 从 thumbnails.libretro.com 下载游戏封面
   - 从 gamesdb.launchbox-app.com 获取游戏信息
   - 支持多种缩略图类型（封面、截图、标题画面）
   - 批量下载功能

5. **Playlist 生成**
   - 按系统自动生成 RetroArch playlist
   - 支持自定义 playlist
   - 自动关联对应的核心
   - 验证和清理 playlist

6. **可扩展的 Fetch 插件系统**
   - 模块化设计，易于扩展
   - 支持多个游戏数据库源
   - 自定义插件开发接口

## 项目结构

```
retro-playlist-tools/
├── main.py                     # 命令行主程序入口
├── setup.py                    # 安装脚本
├── requirements.txt            # 依赖声明
├── README.md                   # 使用说明
├── USAGE_EXAMPLES.md           # 使用示例
└── retroarch_toolkit/          # 核心包
    ├── __init__.py
    ├── config.py               # 配置管理模块
    ├── core/                   # 核心功能模块
    │   ├── __init__.py
    │   ├── utils.py           # 工具函数（CRC32、文件名处理等）
    │   ├── scanner.py         # ROM 扫描器
    │   ├── matcher.py         # 数据库匹配器
    │   ├── playlist.py        # Playlist 生成器
    │   └── fetcher.py         # 插件系统基类
    └── plugins/                # 数据获取插件
        ├── __init__.py
        ├── retroarch_db.py    # RetroArch 官方数据库插件
        ├── libretro_thumbnails.py # Libretro 缩略图插件
        └── launchbox.py       # LaunchBox 游戏数据库插件
```

## 安装

### 依赖要求

- Python 3.8 或更高版本
- 可选：`py7zr` 用于支持 7z 压缩文件

### 安装步骤

```bash
# 克隆仓库
git clone <repository-url>
cd retro-playlist-tools

# 安装可选依赖（支持 7z 文件）
pip install py7zr

# 使脚本可执行
chmod +x retroarch-toolkit main.py
```

## 使用指南

工具提供三种运行方式：

```bash
# 方式 1: 使用启动脚本（推荐）
./retroarch-toolkit <command>

# 方式 2: 直接运行 Python
python main.py <command>

# 方式 3: 安装后使用（需要先 pip install）
retroarch-toolkit <command>
```

### 1. 初始化配置

首次使用需要初始化 RetroArch 路径：

```bash
# 使用任意一种方式
./retroarch-toolkit init /path/to/retroarch
# 或
python main.py init /path/to/retroarch
```

或者交互式输入：

```bash
python main.py init
```

配置文件将保存在 `~/.config/retroarch_toolkit/config.json`

### 2. 扫描 ROM 文件

扫描 ROM 目录并计算 CRC32：

```bash
# 使用配置中的路径
python main.py scan

# 扫描指定路径
python main.py scan -p /path/to/roms

# 详细输出
python main.py scan -v

# 导出扫描结果
python main.py scan -o scan_results.json
```

### 3. 匹配游戏数据库

将 ROM 与游戏数据库匹配：

```bash
# 基本匹配
python main.py match

# 显示未匹配的 ROM
python main.py match -v

# 显示相似游戏建议
python main.py match -v -s
```

未匹配的游戏会保存到 `unknown_games.json`，你可以手动编辑此文件补充信息。

### 4. 生成 Playlist

生成 RetroArch playlist 文件：

```bash
# 按系统生成多个 playlist
python main.py playlist

# 生成单个 playlist
python main.py playlist --single

# 跳过数据库匹配
python main.py playlist --no-match
```

### 5. 下载数据库

下载 RetroArch 官方游戏数据库（带进度显示和文件大小）：

```bash
# 列出可用数据库
python main.py download-db -l

# 下载所有数据库（显示实时进度）
python main.py download-db

# 输出示例（带转圈动画和实时进度）：
# ======================================================================
# Downloading 24 database(s)
# ======================================================================
#
# [1/24] Nintendo - Nintendo Entertainment System.rdb
#   ⠹ ( 45.2%) 556.03 KB/1.23 MB    ← 实时更新，转圈动画
#   ✓ (100.0%) 1.23 MB/1.23 MB      ← 下载完成
#
# [2/24] Nintendo - Game Boy.rdb
#   ✓ Cached 856.32 KB                ← 已缓存文件
#
# [3/24] Sega - Mega Drive - Genesis.rdb
#   ⠼ ( 72.8%) 1.45 MB/1.99 MB      ← 下载中
#   ✓ (100.0%) 1.99 MB/1.99 MB      ← 完成
# ...
#
# ======================================================================
# Download Summary:
#   Total databases: 24
#   Downloaded: 18
#   Cached: 6
#   Total size: 45.67 MB
# ======================================================================

# 下载特定系统
python main.py download-db -s "Nintendo" "Sega"

# 指定输出目录
python main.py download-db -o /path/to/databases
```

### 6. 下载缩略图

下载游戏缩略图：

```bash
python main.py download-thumbnails
```

此命令会：
1. 扫描 ROM 文件
2. 匹配到数据库获取正确的游戏名
3. 下载缩略图到 RetroArch thumbnails 目录

### 7. 配置管理

查看和修改配置：

```bash
# 显示当前配置
python main.py config --show

# 设置配置项
python main.py config --set roms_path=/new/path

# 验证配置
python main.py config --validate
```

## 配置文件说明

配置文件位于 `~/.config/retroarch_toolkit/config.json`：

```json
{
  "retroarch_path": "/path/to/retroarch",
  "roms_path": "/path/to/retroarch/roms",
  "playlists_path": "/path/to/retroarch/playlists",
  "thumbnails_path": "/path/to/retroarch/thumbnails",
  "database_path": "/path/to/retroarch/database/rdb",
  "cores": {
    "Nintendo - Nintendo Entertainment System": {
      "core_name": "nestopia_libretro",
      "extensions": [".nes", ".fds", ".unf", ".unif"],
      "db_name": "Nintendo - Nintendo Entertainment System.rdb"
    }
    // ... 更多系统配置
  },
  "fetch_sources": {
    "retroarch_db": {
      "enabled": true,
      "base_url": "https://github.com/libretro/libretro-database/raw/master/rdb"
    },
    "libretro_thumbnails": {
      "enabled": true,
      "base_url": "http://thumbnails.libretro.com"
    },
    "launchbox": {
      "enabled": true,
      "base_url": "https://gamesdb.launchbox-app.com",
      "api_key": ""
    }
  }
}
```

## 扩展开发

### 创建自定义 Fetch 插件

你可以创建自定义插件来获取其他数据源的游戏信息：

```python
from retroarch_toolkit.core.fetcher import FetchPlugin, FetchResult

class CustomFetcher(FetchPlugin):
    PLUGIN_NAME = "custom_source"

    def get_name(self) -> str:
        return self.PLUGIN_NAME

    def search_game(self, query: str, system=None, **kwargs) -> FetchResult:
        # 实现游戏搜索逻辑
        pass

    def get_game_info(self, game_id: str, **kwargs) -> FetchResult:
        # 实现游戏信息获取逻辑
        pass
```

然后在代码中注册插件：

```python
from retroarch_toolkit.core import BaseFetcher

fetcher = BaseFetcher(config)
fetcher.register_plugin(CustomFetcher(config))
```

## 工作流程示例

完整的 ROM 整理流程：

```bash
# 1. 初始化配置
python main.py init ~/RetroArch

# 2. 下载游戏数据库
python main.py download-db

# 3. 扫描并匹配 ROM
python main.py match -v -s

# 4. 手动编辑 unknown_games.json 补充未匹配的游戏信息

# 5. 下载缩略图
python main.py download-thumbnails

# 6. 生成 playlist
python main.py playlist

# 7. 验证配置
python main.py config --validate
```

## 注意事项

1. **RDB 文件格式**：RetroArch 使用自定义的 RDB 二进制格式。如需完整支持，建议使用 libretro 的 `rdb2dat` 工具将 RDB 转换为 JSON 格式。

2. **CRC32 计算**：对于大文件，CRC32 计算可能需要一些时间。使用 `--no-crc` 选项可以跳过计算。

3. **压缩文件**：支持 ZIP 文件的 CRC32 读取。7z 文件需要安装 `py7zr` 包。

4. **缩略图下载**：游戏名称必须与数据库中的名称完全匹配才能下载到缩略图。

5. **未匹配游戏**：对于数据库中找不到的 ROM（如 hack 版本、自制游戏），工具会记录到 `unknown_games.json`，你可以手动补充信息。

## 支持的系统

目前支持以下游戏系统：

- Nintendo Entertainment System (NES)
- Super Nintendo Entertainment System (SNES)
- Game Boy / Game Boy Color
- Game Boy Advance
- Sega Genesis / Mega Drive
- Sony PlayStation
- Arcade (MAME)

更多系统可以通过修改配置文件添加。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 相关资源

- [RetroArch](https://www.retroarch.com/)
- [Libretro Database](https://github.com/libretro/libretro-database)
- [Libretro Thumbnails](http://thumbnails.libretro.com/)
- [LaunchBox Games Database](https://gamesdb.launchbox-app.com/)
- [ROMhacking.net](https://www.romhacking.net/)
