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

## 主要命令

```
usage: ./rap [-h] {init,scan,match,playlist,download-db,download-thumbnails,config} ...

RetroArch Playlist Creator - Manage playlists and ROM collections by PuterJam

positional arguments:
  {init,scan,match,build,get,config}
                        Available commands
    init                Initialize RetroArch configuration
    scan                Scan ROM directory and match against database
    match               Interactively match unmatched ROMs from unknown_games.json
    build               Generate RetroArch playlists
    get                 Download resources (db, thumbnails)
    config              Manage configuration

options:
  -h, --help            show this help message and exit
```

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

## 许可证

MIT License

## 相关资源

- [RetroArch](https://www.retroarch.com/)
- [Libretro Database](https://github.com/libretro/libretro-database)
- [Libretro Thumbnails](http://thumbnails.libretro.com/)
- [LaunchBox Games Database](https://gamesdb.launchbox-app.com/)
- [ROMhacking.net](https://www.romhacking.net/)
