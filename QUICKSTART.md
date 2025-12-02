# RetroArch Toolkit 快速入门

## 5 分钟快速开始

### 1. 准备工作

```bash
# 确保安装了 Python 3.8+
python --version

# 克隆项目
git clone <repository-url>
cd retro-playlist-tools

# 使脚本可执行
chmod +x retroarch-toolkit main.py

# 可选：安装 7z 支持
pip install py7zr
```

### 2. 初始化配置

```bash
# 方式 1：直接指定路径
./retroarch-toolkit init ~/RetroArch

# 方式 2：交互式输入
./retroarch-toolkit init
# 然后按提示输入 RetroArch 路径
```

配置会保存在 `~/.config/retroarch_toolkit/config.json`

### 3. 扫描 ROM

```bash
# 扫描配置中的 ROMs 目录
./retroarch-toolkit scan

# 扫描特定目录
./retroarch-toolkit scan -p ~/Games/ROMs

# 显示详细信息
./retroarch-toolkit scan -v
```

### 4. 匹配游戏

```bash
# 先下载官方数据库（仅需一次）
./retroarch-toolkit download-db

# 匹配 ROM 到数据库
./retroarch-toolkit match

# 查看未匹配的游戏和相似推荐
./retroarch-toolkit match -v -s
```

### 5. 生成 Playlist

```bash
# 按系统生成多个 playlist
./retroarch-toolkit playlist

# 生成单个包含所有游戏的 playlist
./retroarch-toolkit playlist --single
```

### 6. 下载缩略图

```bash
# 为所有匹配的游戏下载缩略图
./retroarch-toolkit download-thumbnails
```

## 完整工作流程

```bash
# 1. 初始化
./retroarch-toolkit init ~/RetroArch

# 2. 下载数据库
./retroarch-toolkit download-db

# 3. 扫描和匹配
./retroarch-toolkit match -v -s

# 4. 编辑未匹配游戏（可选）
# 编辑 unknown_games.json 文件，手动补充游戏信息

# 5. 下载缩略图
./retroarch-toolkit download-thumbnails

# 6. 生成 playlist
./retroarch-toolkit playlist

# 7. 完成！在 RetroArch 中查看你的游戏收藏
```

## 常用命令

### 查看配置

```bash
./retroarch-toolkit config --show
```

### 修改配置

```bash
# 修改 ROM 路径
./retroarch-toolkit config --set roms_path=/new/path

# 验证配置
./retroarch-toolkit config --validate
```

### 导出扫描结果

```bash
./retroarch-toolkit scan -o my_collection.json
```

### 查看帮助

```bash
./retroarch-toolkit --help
./retroarch-toolkit scan --help
```

## 项目结构速览

```
./main.py                    # 主程序
./retroarch-toolkit          # 启动脚本
./retroarch_toolkit/         # 核心包
  ├── config.py             # 配置管理
  ├── core/                 # 核心功能
  │   ├── utils.py         # 工具函数
  │   ├── scanner.py       # ROM 扫描
  │   ├── matcher.py       # 数据库匹配
  │   ├── playlist.py      # Playlist 生成
  │   └── fetcher.py       # 插件系统
  └── plugins/              # 数据获取插件
      ├── retroarch_db.py
      ├── libretro_thumbnails.py
      └── launchbox.py
```

## 支持的系统

- Nintendo Entertainment System (NES)
- Super Nintendo Entertainment System (SNES)
- Game Boy / Game Boy Color / Game Boy Advance
- Sega Genesis / Mega Drive
- Sony PlayStation
- Arcade (MAME)
- 更多系统可通过配置添加

## 故障排除

### ROM 未被识别

检查文件扩展名是否在配置中支持：
```bash
./retroarch-toolkit config --show
```

### 缩略图下载失败

确保游戏名称与数据库匹配。先运行 `match` 命令。

### 数据库下载慢

使用国内镜像或者手动下载数据库文件。

### 配置文件损坏

删除配置重新初始化：
```bash
rm ~/.config/retroarch_toolkit/config.json
./retroarch-toolkit init
```

## 高级用法

### 自定义插件

创建 `my_plugin.py`：
```python
from retroarch_toolkit.core.fetcher import FetchPlugin, FetchResult

class MyPlugin(FetchPlugin):
    PLUGIN_NAME = "my_plugin"

    def get_name(self):
        return self.PLUGIN_NAME

    def search_game(self, query, system=None, **kwargs):
        # 实现搜索
        return FetchResult(success=True, data={})

    def get_game_info(self, game_id, **kwargs):
        # 实现获取详情
        return FetchResult(success=True, data={})
```

注册插件：
```python
from retroarch_toolkit import Config, BaseFetcher
from my_plugin import MyPlugin

config = Config()
fetcher = BaseFetcher(config)
fetcher.register_plugin(MyPlugin({}))
```

### 批处理脚本

创建 `update_collection.sh`：
```bash
#!/bin/bash
./retroarch-toolkit scan
./retroarch-toolkit match
./retroarch-toolkit download-thumbnails
./retroarch-toolkit playlist
echo "Collection updated!"
```

### Python API 使用

```python
from retroarch_toolkit import Config, ROMScanner, ROMMatcher, PlaylistGenerator

# 初始化
config = Config()

# 扫描
scanner = ROMScanner(config)
roms = scanner.scan()
scanner.print_summary()

# 匹配
matcher = ROMMatcher(config)
matcher.match_all_roms(roms)

# 生成 playlist
generator = PlaylistGenerator(config)
playlists = generator.generate_playlists(roms)
```

## 下一步

- 阅读 [README.md](README.md) 了解详细功能
- 查看 [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) 学习更多使用场景
- 阅读 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) 了解项目架构

## 获取帮助

- 查看文档：README.md
- 报告问题：GitHub Issues
- 贡献代码：Pull Requests

祝你使用愉快！🎮
