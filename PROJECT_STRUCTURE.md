# RetroArch Toolkit 项目结构说明

## 项目概览

RetroArch Toolkit 是一个用于管理 RetroArch ROM 收藏和 Playlist 的 Python 工具。采用模块化设计，核心功能与插件系统分离，易于扩展和维护。

## 目录结构

```
retro-playlist-tools/
│
├── main.py                          # 主程序入口（命令行接口）
├── retroarch-toolkit                # Bash 启动脚本
├── setup.py                         # Python 包安装配置
├── requirements.txt                 # 项目依赖
├── test_basic.py                    # 基础功能测试
├── .gitignore                       # Git 忽略配置
│
├── README.md                        # 项目文档
├── USAGE_EXAMPLES.md               # 使用示例
├── PROJECT_STRUCTURE.md            # 本文档
│
└── retroarch_toolkit/               # 核心包
    │
    ├── __init__.py                 # 包入口，导出主要类
    ├── config.py                   # 配置管理系统
    │
    ├── core/                        # 核心功能模块
    │   ├── __init__.py             # 核心模块入口
    │   ├── utils.py                # 工具函数集
    │   ├── scanner.py              # ROM 扫描器
    │   ├── matcher.py              # 数据库匹配器
    │   ├── playlist.py             # Playlist 生成器
    │   └── fetcher.py              # 插件系统基础架构
    │
    └── plugins/                     # 数据获取插件
        ├── __init__.py             # 插件模块入口
        ├── retroarch_db.py         # RetroArch 官方数据库插件
        ├── libretro_thumbnails.py  # Libretro 缩略图插件
        └── launchbox.py            # LaunchBox 游戏数据库插件
```

## 模块说明

### 主程序层

#### `main.py`
- **作用**：命令行界面入口
- **功能**：
  - 命令解析和路由
  - 用户交互处理
  - 调用核心模块完成任务
- **命令**：init, scan, match, playlist, download-db, download-thumbnails, config

#### `retroarch-toolkit`
- **作用**：便捷的 Bash 启动脚本
- **功能**：包装 Python 调用，提供更简洁的命令行体验

### 核心包层

#### `retroarch_toolkit/__init__.py`
- **导出**：Config, ROMScanner, ROMMatcher, PlaylistGenerator, BaseFetcher
- **作用**：定义包的公共 API

#### `retroarch_toolkit/config.py`
- **类**：Config
- **职责**：
  - 配置文件管理（加载、保存、验证）
  - 系统和核心配置
  - 路径管理
  - 配置项访问（支持点号表示法）
- **配置内容**：
  - RetroArch 路径
  - 核心定义（扩展名、数据库映射）
  - 插件源配置
  - 扫描选项

### 核心功能层

#### `core/utils.py`
- **功能**：工具函数集合
- **主要函数**：
  - `calculate_crc32()` - 计算文件 CRC32 校验和
  - `normalize_rom_name()` - 规范化 ROM 文件名
  - `is_hack_version()` - 检测 Hack/Mod 版本
  - `extract_region_info()` - 提取区域信息
  - `format_file_size()` - 格式化文件大小
  - `sanitize_filename()` - 清理文件名

#### `core/scanner.py`
- **类**：ROMScanner, ROMInfo
- **职责**：
  - 扫描目录查找 ROM 文件
  - 提取 ROM 元数据
  - 计算 CRC32 校验和
  - 支持递归扫描
  - 处理压缩文件（ZIP, 7z）
- **输出**：ROMInfo 对象列表

#### `core/matcher.py`
- **类**：ROMMatcher
- **职责**：
  - ROM 与游戏数据库匹配
  - CRC32 精确匹配
  - 文件名匹配
  - 模糊匹配算法
  - 管理未匹配游戏
- **数据库格式**：支持 JSON 和 RDB

#### `core/playlist.py`
- **类**：PlaylistGenerator
- **职责**：
  - 生成 RetroArch 格式 Playlist
  - 按系统分组
  - 去重和排序
  - Playlist 验证
  - 更新 Playlist 条目

#### `core/fetcher.py`
- **类**：BaseFetcher, FetchPlugin, FetchResult
- **架构**：插件系统基础框架
- **职责**：
  - 定义插件接口（抽象基类）
  - 管理插件生命周期
  - 提供通用功能（文件下载、缓存）
  - 插件注册和调用
- **设计模式**：策略模式 + 工厂模式

### 插件层

#### `plugins/retroarch_db.py`
- **类**：RetroArchDBFetcher
- **功能**：
  - 下载 RetroArch 官方数据库
  - 24+ 系统数据库支持
  - 批量下载
  - 缓存管理

#### `plugins/libretro_thumbnails.py`
- **类**：LibretroThumbnailsFetcher
- **功能**：
  - 下载游戏缩略图
  - 三种类型：封面、截图、标题
  - 多格式支持（PNG, JPG）
  - 批量下载

#### `plugins/launchbox.py`
- **类**：LaunchBoxFetcher
- **功能**：
  - LaunchBox API 集成
  - 游戏信息搜索
  - 平台映射
  - 图片下载

## 数据流

```
用户命令
    ↓
main.py (CLI)
    ↓
Config (配置加载)
    ↓
ROMScanner (扫描)
    ↓
ROMMatcher (匹配)
    ↓
BaseFetcher → Plugins (获取数据)
    ↓
PlaylistGenerator (生成)
    ↓
RetroArch Playlists
```

## 扩展点

### 1. 添加新的插件

创建新插件只需继承 `FetchPlugin` 并实现三个方法：

```python
from retroarch_toolkit.core.fetcher import FetchPlugin, FetchResult

class MyPlugin(FetchPlugin):
    PLUGIN_NAME = "my_plugin"

    def get_name(self):
        return self.PLUGIN_NAME

    def search_game(self, query, system=None, **kwargs):
        # 实现搜索逻辑
        pass

    def get_game_info(self, game_id, **kwargs):
        # 实现详情获取
        pass
```

### 2. 添加新的系统支持

在 `config.py` 的 `DEFAULT_CONFIG` 中添加：

```python
"Your System Name": {
    "core_name": "core_libretro",
    "extensions": [".ext1", ".ext2"],
    "db_name": "System Name.rdb"
}
```

### 3. 自定义匹配算法

在 `ROMMatcher` 中添加新的匹配方法：

```python
def _match_by_custom(self, rom_info, database):
    # 自定义匹配逻辑
    pass
```

## 依赖关系

```
main.py
  └─→ retroarch_toolkit
       ├─→ config
       └─→ core
            ├─→ utils
            ├─→ scanner (依赖 utils)
            ├─→ matcher (依赖 scanner)
            ├─→ playlist (依赖 scanner)
            └─→ fetcher
                 └─→ plugins
                      ├─→ retroarch_db
                      ├─→ libretro_thumbnails
                      └─→ launchbox
```

## 配置文件

### 位置
`~/.config/retroarch_toolkit/config.json`

### 主要配置项

```json
{
  "retroarch_path": "RetroArch 安装路径",
  "roms_path": "ROM 目录",
  "playlists_path": "Playlist 目录",
  "thumbnails_path": "缩略图目录",
  "database_path": "数据库目录",
  "cores": { /* 系统和核心配置 */ },
  "fetch_sources": { /* 插件配置 */ },
  "scan_options": { /* 扫描选项 */ }
}
```

## 数据文件

### `unknown_games.json`
- **位置**：工作目录
- **用途**：记录未匹配的游戏
- **格式**：
```json
{
  "CRC32或文件名": {
    "filename": "原始文件名",
    "manual_name": "手动补充的游戏名",
    "manual_year": 发售年份,
    "notes": "备注"
  }
}
```

## 开发指南

### 运行测试

```bash
python test_basic.py
```

### 调试模式

```bash
python main.py scan -v  # 详细输出
```

### 添加日志

在各模块中使用 `print()` 输出调试信息（未来可以升级为 logging 模块）。

## 性能优化建议

1. **CRC32 计算**：大文件使用分块读取
2. **并发下载**：可以添加异步下载支持
3. **缓存策略**：已实现文件缓存，可扩展到内存缓存
4. **数据库加载**：延迟加载，按需读取

## 未来扩展方向

1. **GUI 界面**：使用 PyQt 或 Tkinter
2. **Web 服务**：提供 REST API
3. **云同步**：支持多设备同步
4. **智能推荐**：基于游戏收藏推荐新游戏
5. **统计分析**：游戏收藏统计和可视化

## 技术栈

- **语言**：Python 3.8+
- **标准库**：argparse, json, pathlib, urllib, zlib, dataclasses
- **可选依赖**：py7zr (7z 支持)
- **架构模式**：分层架构 + 插件系统

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License
