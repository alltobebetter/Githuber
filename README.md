# GitHub文件管理器

这是一个基于PyQt6的GitHub文件管理工具，提供图形化界面来管理GitHub仓库文件。

## 功能特点

- GitHub账号认证
- 本地仓库文件管理
- 文件暂存区可视化
- Git命令执行状态显示
- 文件状态实时更新

## 安装要求

1. Python 3.8+
2. PyQt6
3. PyGithub
4. GitPython

## 安装步骤

1. 克隆本仓库到本地
2. 安装依赖包：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行程序：
```bash
python main.py
```

2. 在左侧面板输入GitHub Token和仓库地址
3. 点击"登录"按钮进行认证
4. 选择本地仓库目录
5. 使用中间面板管理文件：
   - 查看文件状态
   - 暂存文件
   - 提交更改
   - 推送到GitHub
6. 在右侧面板查看操作日志

## 注意事项

- 需要有效的GitHub Token才能使用
- 本地目录必须是有效的Git仓库
- 确保有足够的权限访问目标仓库 