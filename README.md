# genIcon(Icon Generator )

中文 | [English](README_EN.md)

一个轻量的 Windows 桌面图标生成工具：把任意图片一次性导出为多种尺寸、多种格式的图标，包括正方形 和 圆形两种。

基于 Python + Tkinter + Pillow，单文件实现，也可打包成免安装的 exe 直接使用。

![应用界面截图](docs/screenshot.png)

## 功能特性

- **多格式输入**：PNG、ICO、JPG/JPEG、BMP、GIF、TIFF
- **批量导出**：可选尺寸 16 / 32 / 48 / 64 / 128 / 256，可选格式 PNG / ICO / JPG，任意组合一键生成
- **1:1 裁剪工具**：
  - 正方形、圆形两种形状可选
  - 拖动框体移动，四角 / 四边手柄缩放，点击框外暗区重新拉框
  - 实时显示裁剪区域在原图上的像素尺寸和坐标
- **圆形输出**：圆外区域自动透明（PNG / ICO）；JPG 自动铺白底；圆边经 4 倍超采样，小尺寸下边缘依然平滑
- **JPG 质量可调**：10–100，默认 95；透明背景导出 JPG 时自动铺白底

## 输出命名

```
{原文件名}_{宽}x{高}.{格式}
```

例如加载 `logo.png`、全选尺寸和格式，会生成 `logo_16x16.png`、`logo_32x32.ico` 等 18 个文件，保存到指定的输出目录。

## 使用方法

### 方式一：直接运行 exe

双击 `dist/genicon.exe`，无需安装 Python。

### 方式二：运行源码

依赖：Python 3.8+（自带 tkinter），Pillow。

```bash
pip install pillow
python genicon.py
```

### 基本流程

1. **Browse...** 选择一张图片，右侧显示预览
2. （可选）在 **Crop** 区域选择形状（Square / Circle），点击 **Start Crop** 开启裁剪：
   - 拖动框体调整位置，拖四角 / 四边手柄调整大小
   - 点击框外暗色区域，从该点重新拉一个新框
   - 圆形模式下，点圆内拖动、点角部暗区新建框
   - 再次点击按钮（Cancel Crop）取消裁剪
3. 勾选需要的尺寸和格式，设置 JPG 质量
4. **Choose Folder...** 选择输出目录（不选则默认为图片所在目录）
5. 点击 **Generate Icons** 生成

> 提示：圆形模式下即使不开启裁剪，也会自动取图片居中的最大正方形区域抠圆，避免非正方形图片被拉伸变形。

## 打包 exe

```bash
python -m PyInstaller genicon.spec --noconfirm
```

产物为单文件 `dist/genicon.exe`（无控制台窗口）。如果安装了 UPX 会自动压缩，没有也不影响构建。

## 项目结构

```
genicon/
├── genicon.py       # 主程序（全部逻辑，单文件）
├── genicon.spec     # PyInstaller 打包配置
├── README.md        # 中文说明
├── README_EN.md     # 英文说明
├── docs/
│   └── screenshot.png
├── build/           # PyInstaller 中间产物
└── dist/
    └── genicon.exe  # 可直接使用的独立可执行文件
```
