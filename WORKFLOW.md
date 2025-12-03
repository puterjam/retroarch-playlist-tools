# RetroArch Toolkit 工作流程

## 优化后的三步工作流程

### 1. Scan - 扫描并匹配

扫描 ROM 目录，自动匹配数据库，生成未识别游戏列表。

```bash
python main.py scan
```

**功能：**
- 扫描指定目录的所有 ROM 文件
- 计算 CRC32 校验和
- 自动匹配 RetroArch 游戏数据库
- 生成 `unknown_games.json` 记录未识别的 ROM

**选项：**
```bash
python main.py scan -p /path/to/roms  # 指定扫描路径
python main.py scan -v                # 详细输出
python main.py scan --no-crc          # 跳过 CRC32 计算
python main.py scan -o results.json   # 导出扫描结果
```

**输出示例：**
```
============================================================
STEP 1: Scanning ROMs
============================================================
[1/150] Found: Super Mario Bros.nes (Nintendo - NES)
[2/150] Found: Zelda.nes (Nintendo - NES)
...

============================================================
STEP 2: Matching ROMs to Database
============================================================
Matching 150 ROMs to database...
Applied 5 manual matches
Matched 142/150 ROMs (94.7%)

📝 Saved 8 unmatched ROMs to: unknown_games.json
   You can manually edit this file to add game information

💡 Use 'match' command to interactively fix 8 unmatched ROM(s)
```

---

### 2. Match - 交互式修复未识别 ROM

使用交互式 shell 修复 `unknown_games.json` 中的未识别 ROM。

```bash
python main.py match
```

**功能：**
- 读取 `unknown_games.json` 中的未识别 ROM
- 提供交互式模糊匹配界面
- 支持自定义搜索
- 保存匹配结果到 `manual_matches.json`

**交互界面：**

```
============================================================
Interactive ROM Matcher
============================================================
Total unmatched ROMs: 8
============================================================
Press Enter to start...

============================================================
[1/8] Super Mario Hack.nes (Nintendo - NES)
CRC32: A1B2C3D4 | Region: USA
============================================================
Similar games:
  🟢 1. Super Mario Bros. | USA | 1985 | 92.3%
  🟡 2. Super Mario Bros. 2 | USA | 1988 | 68.5%
  🔴 3. Mario Bros. | USA | 1983 | 45.2%

Commands: 1-5 (select) | s (search) | n (skip) | q (quit)
Choice: 1

✓ Saved: Super Mario Hack.nes -> Super Mario Bros.
```

**主要特性：**

1. **清屏显示**
   - 每个 ROM 清屏显示，类似 vim 的体验
   - 无多余滚动，界面始终保持清爽
   - 数据库加载消息被自动抑制

2. **交互命令**
   - `1-5` - 选择对应的匹配项
   - `s` - 自定义搜索游戏名
   - `n` 或 `skip` - 跳过当前 ROM
   - `q` 或 `quit` - 退出匹配器

3. **匹配指示器**
   - 🟢 绿色：匹配度 > 80%（高可信度）
   - 🟡 黄色：匹配度 60-80%（中等可信度）
   - 🔴 红色：匹配度 < 60%（低可信度）

4. **紧凑显示**
   - 每次只显示最多 5 个相似游戏
   - 清屏显示，无滚动干扰
   - 单行显示关键信息

5. **自定义搜索**
   ```
   Choice: s
   Search query: mario
   ============================================================
   Search Results: mario
   ============================================================
     1. Super Mario Bros. | USA | 1985
     2. Super Mario Bros. 2 | USA | 1988
     3. Super Mario Bros. 3 | USA | 1990
     ...
     0. Cancel
   ============================================================
   Select [0-10]: 1
   ```

6. **无匹配处理**
   ```
   ⚠️  No similar games found
   Commands: s (search) | n (skip) | q (quit)
   Choice: n
   ```

---

### 3. Playlist - 生成 LPL 文件

根据匹配结果生成 RetroArch playlist 文件。

```bash
python main.py playlist
```

**功能：**
- 按系统分组生成 playlist
- 自动应用 `manual_matches.json` 中的手动匹配
- 使用运行时路径（如 Switch 挂载点）
- 关联正确的核心和数据库

**选项：**
```bash
python main.py playlist              # 按系统生成多个 playlist
python main.py playlist --single     # 生成单个 playlist
python main.py playlist --no-match   # 跳过数据库匹配
```

**输出示例：**
```
Scanning ROMs...
Found 150 ROM files

Matching ROMs to database...
Applied 8 manual matches
Matched 150/150 ROMs (100.0%)

Generating playlists...
Generated playlist: Nintendo - NES.lpl (85 items)
Generated playlist: Nintendo - SNES.lpl (45 items)
Generated playlist: Nintendo - Game Boy.lpl (20 items)

Generated 3 playlist(s):
  - Nintendo - NES: /path/to/playlists/Nintendo - NES.lpl
  - Nintendo - SNES: /path/to/playlists/Nintendo - SNES.lpl
  - Nintendo - Game Boy: /path/to/playlists/Nintendo - Game Boy.lpl
```

---

## 完整工作流程示例

```bash
# 1. 初始化配置（首次使用）
python main.py init ~/RetroArch

# 2. 下载游戏数据库（可选，如果数据库不存在）
python main.py download-db

# 3. 扫描并匹配 ROM
python main.py scan

# 4. 交互式修复未识别的 ROM
python main.py match

# 5. 生成 playlist
python main.py playlist

# 6. （可选）下载缩略图
python main.py download-thumbnails
```

---

## 文件说明

### unknown_games.json
存储未识别的 ROM 信息，由 `scan` 命令生成。

```json
{
  "A1B2C3D4": {
    "filename": "Super Mario Hack.nes",
    "path": "/roms/nes/Super Mario Hack.nes",
    "system": "Nintendo - NES",
    "crc32": "A1B2C3D4",
    "normalized_name": "super mario hack",
    "region": "USA",
    "size": 40960,
    "size_formatted": "40.0 KB"
  }
}
```

### manual_matches.json
存储手动匹配结果，由 `match` 命令生成。

```json
{
  "A1B2C3D4": {
    "filename": "Super Mario Hack.nes",
    "path": "/roms/nes/Super Mario Hack.nes",
    "system": "Nintendo - NES",
    "crc32": "A1B2C3D4",
    "matched_name": "Super Mario Bros.",
    "matched_region": "USA",
    "matched_crc": "E1F2A3B4",
    "release_year": "1985",
    "developer": "Nintendo",
    "publisher": "Nintendo"
  }
}
```

---

## 提示与技巧

### 1. 批量处理大量未识别 ROM
```bash
# 使用自动模式快速处理高匹配度的 ROM
python main.py match
# 选择: a (auto)
```

### 2. 精细控制匹配
```bash
# 使用交互模式逐个确认
python main.py match
# 选择: s (select)
```

### 3. 跳过 CRC32 计算（大文件）
```bash
python main.py scan --no-crc
```

### 4. 使用自定义搜索
当模糊匹配不准确时，在交互界面使用 `s` 命令自定义搜索。

### 5. 查看配置
```bash
python main.py config --show
```

---

## 优势

1. **分离的工作流程**
   - 每个步骤独立，便于调试
   - 可以多次运行 `match` 而不需要重新扫描

2. **交互式修复**
   - 使用 Python Prompt Toolkit
   - 无需为每个选择启动新行
   - 支持命令补全和历史记录

3. **灵活的匹配模式**
   - 自动模式：快速处理高匹配度项
   - 交互模式：精确控制每个匹配
   - 可随时切换模式

4. **紧凑的显示**
   - 每次只显示 5 个最相似的游戏
   - 单行显示关键信息
   - 清晰的匹配度指示器

5. **持久化存储**
   - `unknown_games.json` 记录未识别项
   - `manual_matches.json` 保存手动匹配
   - 支持增量修复，不会丢失进度
