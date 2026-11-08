# Together Level Manager

> 面向 **A Dance of Fire and Ice（ADOFAI，冰与火之舞）** 的 TGT（Together）模组关卡批量管理工具：
> 把一堆 `.zip / .rar / .7z` 关卡包变成一张能排序、能筛选信息、能一键分类归档的表格。

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![GUI](https://img.shields.io/badge/GUI-ttkbootstrap-6c5ce7)
![License](https://img.shields.io/badge/License-Apache--2.0-green)

---

## 这个工具解决什么问题

社群下载的 ADOFAI 关卡通常是压缩包，一个包几百个，逐个解压再按曲名重命名非常痛苦。
TLM 做的事情是：

1. 扫描你指定的**压缩包文件夹**；
2. 用 Together 模组自带的 `7z.exe` 把包里的 `.adofai` 谱面与 `.ogg / .wav` 音频解到**缓存文件夹**；
3. 解析谱面元数据（曲名 / 艺术家 / 作者 / 谱面日期 / 轨道长度），列成表格；
4. 勾选你要的关卡，按**类型**（例如 `Init / Hard / Collab`）解压完整压缩包到
   `保存路径/<类型>/<曲名_艺术家_作者>/`；
5. 支持列头排序、清理缓存、类型管理、启动自动加载。

## 功能一览

| 功能 | 说明 |
| --- | --- |
| 关卡解析 | 支持新旧两种谱面格式：`pathData`（方向字符）自动换算成 `angleData` |
| 容错修复 | 谱面 JSON 被手改坏（多余逗号 / 被截断 / BOM）时尽力修复后再读 |
| 表格展示 | 歌曲 / 艺术家 / 作者 / 日期 四列，点击列头切换升/降序，箭头指示当前排序列 |
| 批量导出 | 多选后按类型导出，导出时解压**完整**压缩包（含贴图、特效、音频） |
| 缓存管理 | 一键清空解压缓存；已处理过的包自动跳过，不重复解压 |
| 7z 自动探测 | 依次探测 Together 新旧目录布局与系统 `7z`，也可手动指定路径 |
| 设置持久化 | 设置在程序目录下的 `tlm_settings.json`，升级不丢配置（旧版设置自动迁移） |
| 多线程 | 解压与扫描走线程池，进度条实时反馈，界面不卡死 |

## 环境要求

- Windows 10 / 11（用到了 `subprocess.CREATE_NO_WINDOW` 与 Together 的目录约定）
- Python **3.12+**
- `ttkbootstrap==1.10.1`、`colorama==0.4.6`
- 一个可用的 `7z.exe`：优先用 Together 模组自带的；没有就装 7-Zip，或在设置里指定

## 安装与运行

```bash
git clone https://github.com/ThisisYLaaa/ADOFAI-TLM.git
cd ADOFAI-TLM
pip install -r requirements.txt

python main.py          # 推荐入口
# 或
python -m tlm           # 等价
python UI.py            # 旧入口，仍可用（等同 main.py，会提示已废弃）
```

也可以当作包安装（获得 `tlm` 命令）：

```bash
pip install -e .
tlm
```

## 首次配置

点工具栏「**设置**」，填三个目录（都可以用「浏览」选）：

| 设置项 | 含义 | 建议 |
| --- | --- | --- |
| 压缩包文件夹 | 存放待处理关卡压缩包的目录 | 只放压缩包，不要嵌套太深 |
| 保存路径 | 导出后按类型归档的根目录 | 例如 `D:\Adofai Songs` |
| 缓存文件夹 | 解压中间的 `.adofai` + 音频落地位置 | 单独一个目录，方便一键清理 |
| 7z 路径 | 留空 = 自动探测 | 探测失败时手动指向 `7z.exe` |
| 启动时自动加载 | 打开程序就扫描一遍 | 关卡多时建议关掉 |

「缓存文件夹」会被程序写入和清空，**不要指向有重要文件的目录**。

## 使用流程

1. **刷新**：扫描压缩包 → 解到缓存 → 解析元数据 → 填表。
   首次会慢（要解压），之后已处理过的包会被跳过。
2. **看表**：点列头排序；日期取的是压缩包修改时间，方便按新旧筛。
3. **导出**：选中若干行 → 「**保存**」→ 选类型 → 确认。导出到
   `保存路径/<类型>/<曲名_艺术家_作者>/`，文件名里的非法字符会被剔除。
4. **类型管理**：类型就是导出时的二级目录名，可增删。
5. **清理缓存**：切换压缩包批次前清一次，避免结果混在一起。

## 目录结构

```
ADOFAI-TLM/
├── main.py                 # 启动入口（python main.py）
├── UI.py                   # 旧入口兼容壳（转发到 main.py）
├── pyproject.toml          # 打包 / 依赖 / pytest 配置
├── requirements.txt
├── tlm/                    # 程序包（不含 GUI 依赖，可单独 import）
│   ├── __main__.py         # python -m tlm
│   ├── constants.py        # 版本号、主题、默认设置、扩展名
│   ├── paths.py            # 设置文件位置 / Together 目录 / 7z 探测
│   ├── log.py              # 彩色日志（colorama 可选）
│   ├── parser.py           # .adofai 解析与 JSON 容错修复
│   ├── models.py           # Level 关卡模型
│   ├── utils.py            # 7z 解压、文件名清洗、HTML 清洗
│   ├── settings.py         # 设置单例（迁移旧配置）
│   ├── service.py          # 线程池扫描 / 解压（纯逻辑，无 Tk 依赖）
│   └── ui/
│       ├── bridge.py       # worker 线程 → 主线程 的安全队列桥
│       ├── treeview.py     # 表格与排序
│       ├── dialogs.py      # 设置 / 类型管理 / 导出 对话框
│       └── main_window.py  # 主窗口
└── tests/                  # pytest：解析、模型、设置、扫描逻辑、UI 冒烟
```

## 配置文件

位置：程序目录下的 `tlm_settings.json`（打包成 exe 时在 exe 同目录）。
可用环境变量 `TLM_HOME` 指定其它目录。旧版的 `tl_settings_<版本>.json` 会被自动迁移。

```jsonc
{
  "zip_folder": "",            // 压缩包目录
  "save_folder": "",           // 导出根目录
  "unzip_cache_folder": "",    // 解压缓存目录
  "auto_load": false,          // 启动时自动刷新
  "types": ["Init"],           // 导出类型（二级目录名）
  "seven_zip_path": ""         // 7z.exe 路径；留空 = 自动探测
}
```

相关环境变量：

| 变量 | 作用 |
| --- | --- |
| `TLM_HOME` | 设置文件所在目录 |
| `TLM_7Z` | 直接指定 `7z.exe` |
| `TLM_TOGETHER_DIR` | 手动指定 Together 模组安装目录（目录改版时用） |

## 开发与测试

```bash
pip install -r requirements.txt pytest
python -m pytest -q
```

测试覆盖：谱面解析与坏 JSON 修复、`Level` 元数据回退、文件名/HTML 清洗、
设置的读写与旧配置迁移、扫描与进度回调、GUI 模块导入冒烟。
`tlm.service`、`tlm.parser`、`tlm.models` 均不依赖 Tkinter，可在无显示环境下测试。

## 常见问题

**提示「未找到 7z 可执行文件」**
程序按 `设置 → 7z 路径`、`TLM_7Z`、Together 的
`%LOCALAPPDATA%\Together\Resources\7z\7z.exe` / `%LOCALAPPDATA%\Together\7z\7z.exe`，
再到系统 `PATH` 的顺序找。Together 目录改版过，若都没命中就到设置里手动选一个。
点设置窗口里的「**自动探测**」会告诉你每个候选路径是否命中。

**关卡列表是空的**
先确认「缓存文件夹」里确实有 `<压缩包名>/xxx.adofai`。压缩包里的谱面如果在深层子目录，
程序会递归取第一个 `.adofai`；包里没有谱面时会静默跳过。

**某个关卡日期显示 unknown**
日期来自压缩包的修改时间。缓存目录里没有压缩包（例如被手动删掉）时就没有日期可读，
这不影响导出，只是排序会落到后面。

**导出的文件夹名很奇怪**
导出目录名是 `曲名_艺术家_作者` 去掉 `<>:"/\|?*` 之后的拼接；谱面里没写元数据时会显示 `unknown`。

**控制台报 `Incorrect padding` / 谱面解析失败**
说明谱面 JSON 损坏严重，程序会把该关卡记为解析失败并跳过，不影响其它关卡。

## 版本记录

- **v1.1.0**（当前）
  - 重构为 `tlm` 包：`parser / models / utils / settings / service / ui` 分层，逻辑层不再依赖 GUI
  - 修复：关卡目录里没有压缩包时 `Level.date` 未赋值导致的 `AttributeError` 崩溃
  - 修复：worker 线程直接操作 Tkinter 控件（进度条 / 状态栏）导致的卡死风险，改为队列桥
  - 修复：设置里的 `"/" -> "\"` 全局替换把路径写坏；日志 formatter 破坏 `record.msg`
  - 改进：设置文件不再依赖当前工作目录，旧版 `tl_settings_*.json` 自动迁移
  - 改进：7z 探测支持 Together 新旧目录布局与系统安装，可在设置里手动指定
  - 新增：`pyproject.toml`、pytest 测试套件（38+ 用例）
- **v1.0.0** 初版：解包 → 解析 → 表格 → 按类型导出

## 协议

[Apache License 2.0](LICENSE)

## 联系

- B 站：[Leaked翼龙](https://space.bilibili.com/616045770)
- QQ 群：132292540
