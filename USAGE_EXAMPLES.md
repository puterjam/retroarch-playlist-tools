# RetroArch Toolkit 使用示例

本文档提供了一些常见使用场景的详细示例。

## 场景 1：首次整理 ROM 收藏

假设你有一个混乱的 ROM 收藏，需要完整整理。

```bash
# 步骤 1: 初始化配置
python main.py init ~/RetroArch

# 输出：
# RetroArch Toolkit initialized successfully!
# RetroArch path: /home/user/RetroArch
# ROMs path: /home/user/RetroArch/roms
# ...

# 步骤 2: 先扫描看看有什么
python main.py scan -v

# 输出：
# Scanning directory: /home/user/RetroArch/roms
# Found 150 ROM files
# [1/150] Found: Super Mario Bros (USA).nes (Nintendo - Nintendo Entertainment System)
# [2/150] Found: Sonic The Hedgehog (USA).md (Sega - Mega Drive - Genesis)
# ...

# 步骤 3: 下载官方数据库
python main.py download-db

# 输出：
# Downloading 24 database(s)...
# ✓ Nintendo - Nintendo Entertainment System.rdb (downloaded)
# ✓ Sega - Mega Drive - Genesis.rdb (downloaded)
# ...

# 步骤 4: 匹配 ROM 到数据库
python main.py match -v -s

# 输出：
# Scanning ROMs...
# Found 150 ROM files
# Matching 150 ROMs to database...
# Matched 142/150 ROMs (94.7%)
#
# Unmatched ROMs:
#   - Super Mario World Hack - Kaizo Edition.smc (Nintendo - Super Nintendo Entertainment System)
#     Similar games:
#       Super Mario World (USA) (98.50%)
#       Super Mario World (Europe) (95.23%)
#   ...

# 步骤 5: 编辑 unknown_games.json 手动补充信息
# (使用文本编辑器编辑文件)

# 步骤 6: 下载缩略图
python main.py download-thumbnails

# 输出：
# Scanning ROMs...
# Matching ROMs...
#
# Downloading thumbnails for Nintendo - Nintendo Entertainment System...
# [1/85] Super Mario Bros (USA)
#   ✓ Named_Boxarts (downloaded)
#   ✓ Named_Snaps (downloaded)
#   ✓ Named_Titles (downloaded)
# ...

# 步骤 7: 生成 playlist
python main.py playlist

# 输出：
# Scanning ROMs...
# Matching ROMs to database...
# Generating playlists...
# Generated 5 playlist(s):
#   - Nintendo - Nintendo Entertainment System: /home/user/RetroArch/playlists/Nintendo - Nintendo Entertainment System.lpl
#   - Sega - Mega Drive - Genesis: /home/user/RetroArch/playlists/Sega - Mega Drive - Genesis.lpl
#   ...
```

## 场景 2：添加新 ROM 到已有收藏

当你获得新的 ROM 文件时：

```bash
# 1. 将新 ROM 复制到对应系统目录
cp new_game.nes ~/RetroArch/roms/nes/

# 2. 重新扫描和匹配
python main.py match -v

# 3. 下载新游戏的缩略图
python main.py download-thumbnails

# 4. 更新 playlist
python main.py playlist
```

## 场景 3：只处理特定系统

如果你只想处理某个特定系统（如 NES）：

```bash
# 1. 下载特定系统的数据库
python main.py download-db -s "Nintendo Entertainment"

# 2. 扫描特定目录
python main.py scan -p ~/RetroArch/roms/nes -v

# 3. 匹配和生成 playlist
python main.py match
python main.py playlist
```

## 场景 4：处理 ROM Hacks 和自制游戏

对于官方数据库中没有的游戏：

```bash
# 1. 运行匹配命令
python main.py match -v -s

# 输出会显示未匹配的游戏和相似游戏建议

# 2. 编辑 unknown_games.json
# 文件内容示例：
{
  "ABC123DEF": {
    "filename": "Super Mario World - Kaizo Edition.smc",
    "path": "/path/to/rom",
    "system": "Nintendo - Super Nintendo Entertainment System",
    "crc32": "ABC123DEF",
    "normalized_name": "Super Mario World Kaizo Edition",
    "is_hack": true,
    "base_game_name": "Super Mario World",
    "region": "USA",
    "manual_name": "Super Mario World - Kaizo Edition",  # 手动填写
    "manual_year": 2010,  # 手动填写
    "notes": "Popular ROM hack by T. Takemoto"  # 手动填写
  }
}

# 3. 重新生成 playlist 以包含手动信息
python main.py playlist
```

## 场景 5：批量导出和分析

导出 ROM 收藏的详细信息进行分析：

```bash
# 导出扫描结果到 JSON
python main.py scan -o my_collection.json

# 文件内容示例：
{
  "total_roms": 150,
  "systems": {
    "Nintendo - Nintendo Entertainment System": {
      "count": 85,
      "total_size": 12345678,
      "matched": 82,
      "hacks": 3
    },
    ...
  },
  "roms": [
    {
      "path": "/path/to/rom.nes",
      "filename": "Super Mario Bros (USA).nes",
      "system": "Nintendo - Nintendo Entertainment System",
      "size": 40960,
      "crc32": "3337EC46",
      "normalized_name": "Super Mario Bros",
      "matched": true,
      "game_name": "Super Mario Bros.",
      "release_year": 1985,
      ...
    },
    ...
  ]
}

# 然后可以用其他工具分析这个 JSON 文件
```

## 场景 6：修改配置

```bash
# 查看当前配置
python main.py config --show

# 修改 ROMs 路径
python main.py config --set roms_path=/new/path/to/roms

# 验证配置
python main.py config --validate
```

## 场景 7：自定义 Fetch 插件

创建自定义插件来从其他数据源获取信息：

```python
# custom_fetcher.py
from retroarch_toolkit.core.fetcher import FetchPlugin, FetchResult
import requests

class MyGameDBFetcher(FetchPlugin):
    PLUGIN_NAME = "mygamedb"

    def get_name(self):
        return self.PLUGIN_NAME

    def search_game(self, query, system=None, **kwargs):
        # 实现搜索逻辑
        try:
            response = requests.get(
                f"https://api.mygamedb.com/search",
                params={"q": query, "platform": system}
            )
            data = response.json()

            return FetchResult(
                success=True,
                data=data,
                source=self.PLUGIN_NAME
            )
        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                source=self.PLUGIN_NAME
            )

    def get_game_info(self, game_id, **kwargs):
        # 实现详细信息获取
        try:
            response = requests.get(f"https://api.mygamedb.com/games/{game_id}")
            data = response.json()

            return FetchResult(
                success=True,
                data=data,
                source=self.PLUGIN_NAME
            )
        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                source=self.PLUGIN_NAME
            )

# 使用自定义插件
from retroarch_toolkit import Config, BaseFetcher
from custom_fetcher import MyGameDBFetcher

config = Config()
fetcher = BaseFetcher(config)

# 注册自定义插件
custom_plugin = MyGameDBFetcher({"enabled": True})
fetcher.register_plugin(custom_plugin)

# 使用插件搜索
result = custom_plugin.search_game("Super Mario Bros", "NES")
if result.success:
    print(result.data)
```

## 场景 8：定期维护脚本

创建一个定期维护脚本：

```bash
#!/bin/bash
# maintain_collection.sh

echo "=== RetroArch Collection Maintenance ==="
echo

echo "Step 1: Scanning ROMs..."
python main.py scan

echo
echo "Step 2: Matching to database..."
python main.py match -v

echo
echo "Step 3: Downloading missing thumbnails..."
python main.py download-thumbnails

echo
echo "Step 4: Regenerating playlists..."
python main.py playlist

echo
echo "Step 5: Validating configuration..."
python main.py config --validate

echo
echo "=== Maintenance Complete ==="
```

使用 cron 定期运行：
```bash
# 每周日凌晨 2 点运行
0 2 * * 0 /path/to/maintain_collection.sh >> /var/log/retroarch_maintenance.log 2>&1
```

## 提示和技巧

### 加速 CRC32 计算

如果你有很多 ROM 文件，CRC32 计算可能很慢：

```bash
# 首次扫描时计算并保存结果
python main.py scan -o roms_cache.json

# 后续操作可以跳过 CRC32 计算
python main.py scan --no-crc
```

### 处理大型 ROM 收藏

对于非常大的收藏（1000+ ROMs）：

```bash
# 分系统处理
for system_dir in ~/RetroArch/roms/*/; do
    echo "Processing $system_dir"
    python main.py scan -p "$system_dir"
    python main.py match
done
```

### 备份配置和数据

```bash
# 备份配置文件
cp ~/.config/retroarch_toolkit/config.json ~/backup/

# 备份 unknown_games.json（包含手动补充的信息）
cp unknown_games.json ~/backup/
```

### 批量重命名 ROM

虽然工具不直接重命名文件，但你可以使用扫描结果：

```python
import json

# 读取扫描结果
with open('my_collection.json', 'r') as f:
    data = json.load(f)

# 根据匹配的标准名称重命名
for rom in data['roms']:
    if rom['matched'] and rom['game_name']:
        old_path = rom['path']
        # 生成新文件名...
        # 重命名文件...
```
