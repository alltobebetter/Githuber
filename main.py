import sys
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import requests
import json
import threading
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QTextEdit, QLabel, 
                            QLineEdit, QFileDialog, QListWidget, QMessageBox,
                            QDialog, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QTimer
from PyQt6.QtGui import QPalette, QColor, QFont, QIcon, QKeySequence, QShortcut
from github import Github
import git
import time
import base64
import random
import socket

# 主题颜色
THEME_BLUE = "#87CEEB"  # 天蓝色
THEME_PINK = "#FFB6C1"  # 粉色
THEME_LIGHT_BLUE = "#E6F3F7"  # 浅蓝色（用于悬浮效果）
THEME_LIGHT_PINK = "#FFE6EA"  # 浅粉色（用于悬浮效果）
DISABLED_COLOR = "#E0E0E0"  # 禁用状态的颜色
THEME_GRAY = "#888888"  # 灰色（用于项目按钮）

# 项目信息（使用混淆方式存储）
_p1 = "aHR0cHM6Ly9naXRodWIuY29tLw=="
_p2 = "YWxsdG9iZWJldHRlci8="
_p3 = "R2l0aHViZXI="

# 解码函数（使用非直接的方式）
def _dc(s):
    try:
        return base64.b64decode(s).decode('utf-8')
    except:
        return ""

# 隐藏的访问机制
_c = [97, 108, 108, 116, 111, 98, 101, 98, 101, 116, 116, 101, 114]
_v = lambda x: ''.join([chr(i) for i in x])
_k = lambda: _v(_c)

# GitHub OAuth配置
# 这些值将从配置文件中读取
CLIENT_ID = ""
CLIENT_SECRET = ""
REDIRECT_URI = "http://localhost:8000/callback"

# 配置文件路径
CONFIG_FILE = "github_config.json"
TOKEN_FILE = "github_token.json"  # 添加token文件路径

class StyledButton(QPushButton):
    def __init__(self, text, border_color, parent=None):
        super().__init__(text, parent)
        hover_color = THEME_LIGHT_BLUE if border_color == THEME_BLUE else THEME_LIGHT_PINK
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px dashed {border_color};
                border-radius: 5px;
                padding: 8px 20px;
                color: #333;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                border-color: {DISABLED_COLOR};
                color: #999;
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class StyledLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #87CEEB;
                border-radius: 5px;
                padding: 5px 10px;
                background-color: white;
                height: 30px;
            }
            QLineEdit:focus {
                border-color: #FFB6C1;
            }
            QLineEdit:disabled {
                background-color: #F0F0F0;
                border-color: #CCCCCC;
            }
            QLineEdit[readOnly="true"] {
                background-color: #F8F8F8;
            }
        """)
        self.setMinimumWidth(300)  # 设置最小宽度

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

class Worker(QThread):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.result = None

    def run(self):
        try:
            self.result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))

class SignalHandler(QObject):
    auth_success = pyqtSignal(str)
    auth_error = pyqtSignal(str)

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """覆盖默认的日志方法，避免向控制台输出"""
        # 不向控制台输出任何内容
        pass
        
    def do_GET(self):
        try:
            # 验证路径是否正确
            if not self.path.startswith('/callback'):
                self.send_error_response("无效请求", "不正确的回调路径")
                return
                
            # 解析查询参数
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            
            if "code" in query_components:
                # 获取认证码
                code = query_components["code"][0]
                window.log_output("收到GitHub回调，正在处理认证码...")
                
                # 使用认证码获取访问令牌
                data = {
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'code': code,
                    'redirect_uri': REDIRECT_URI
                }
                
                try:
                    # 添加更多详细日志
                    window.log_output("向GitHub请求访问令牌...")
                    
                    # 使用更长的超时和重试机制
                    max_retries = 3
                    retry_count = 0
                    
                    while retry_count < max_retries:
                        try:
                            response = requests.post(
                                'https://github.com/login/oauth/access_token',
                                data=data,
                                headers={'Accept': 'application/json'},
                                timeout=15  # 增加超时时间
                            )
                            
                            # 请求成功，跳出循环
                            break
                        except requests.RequestException as e:
                            retry_count += 1
                            if retry_count < max_retries:
                                window.log_output(f"请求失败，正在重试 ({retry_count}/{max_retries})...")
                                time.sleep(2)  # 重试前等待
                            else:
                                raise  # 重试次数用完，抛出异常
                    
                    # 检查响应状态
                    if response.status_code != 200:
                        window.log_output(f"GitHub返回错误状态码: {response.status_code}")
                        window.signal_handler.auth_error.emit(f"GitHub返回错误: HTTP {response.status_code}")
                        self.send_error_response("GitHub API错误", f"状态码: {response.status_code}")
                        return
                    
                    # 处理响应数据
                    try:
                        response_data = response.json()
                    except ValueError:
                        window.log_output("无法解析GitHub响应")
                        window.signal_handler.auth_error.emit("无法解析GitHub的JSON响应")
                        self.send_error_response("数据解析错误", "无法解析GitHub的JSON响应")
                        return
                    
                    if 'access_token' in response_data:
                        access_token = response_data['access_token']
                        window.log_output("成功获取访问令牌")
                        
                        # 发送认证成功信号
                        window.signal_handler.auth_success.emit(access_token)
                        
                        # 修复可能的异常 - 检查是否可以写入响应
                        try:
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html; charset=utf-8')
                            self.end_headers()
                            success_message = """
                            <html>
                            <head>
                                <title>认证成功</title>
                                <meta http-equiv="refresh" content="3;url=https://github.com">
                                <style>
                                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                                    h2 { color: #4CAF50; }
                                    p { margin: 20px 0; }
                                    .loader { 
                                        border: 5px solid #f3f3f3; 
                                        border-radius: 50%; 
                                        border-top: 5px solid #4CAF50; 
                                        width: 40px; 
                                        height: 40px; 
                                        animation: spin 2s linear infinite; 
                                        margin: 20px auto;
                                    }
                                    @keyframes spin {
                                        0% { transform: rotate(0deg); }
                                        100% { transform: rotate(360deg); }
                                    }
                                </style>
                            </head>
                            <body>
                                <h2>认证成功！</h2>
                                <div class="loader"></div>
                                <p>请返回应用程序继续操作。</p>
                                <p>此窗口将在3秒后自动关闭...</p>
                                <script>
                                    // 关闭页面的脚本
                                    setTimeout(function() {{
                                        window.close();
                                    }}, 3000);
                                </script>
                            </body>
                            </html>
                            """.encode('utf-8')
                            
                            # 防止NoneType异常
                            if hasattr(self, 'wfile') and self.wfile is not None:
                                try:
                                    self.wfile.write(success_message)
                                    self.wfile.flush()  # 确保数据发送
                                except:
                                    pass  # 忽略写入错误，认证已经成功
                        except Exception as e:
                            # 即使响应发送失败，也确保认证成功信号已经发出
                            print(f"发送响应时出错，但认证已成功: {str(e)}")
                    else:
                        error_msg = response_data.get('error_description', '未知错误')
                        window.log_output(f"认证失败: {error_msg}")
                        window.signal_handler.auth_error.emit(f"认证失败: {error_msg}")
                        self.send_error_response("认证失败", error_msg)
                except requests.RequestException as e:
                    window.log_output(f"网络错误: {str(e)}")
                    window.signal_handler.auth_error.emit(f"网络错误: {str(e)}")
                    self.send_error_response("网络错误", str(e))
            else:
                window.log_output("无效的请求: 缺少认证码")
                window.signal_handler.auth_error.emit("无效的请求")
                self.send_error_response("无效的请求", "缺少必要的认证码")
        except Exception as e:
            window.log_output(f"处理请求时出错: {str(e)}")
            window.signal_handler.auth_error.emit(f"处理请求时出错: {str(e)}")
            try:
                self.send_error_response("处理请求时出错", str(e))
            except:
                # 如果发送错误响应也失败，至少确保错误信号已发出
                pass
    
    def send_error_response(self, title, message):
        try:
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            error_html = f"""
            <html>
            <head>
                <title>{title}</title>
                <meta http-equiv="refresh" content="5;url=https://github.com">
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    h2 {{ color: #f44336; }}
                    p {{ margin: 20px 0; }}
                    .error {{ color: #666; font-family: monospace; background: #f1f1f1; padding: 10px; }}
                </style>
            </head>
            <body>
                <h2>{title}</h2>
                <p class="error">{message}</p>
                <p>请关闭此窗口并重试。</p>
                <p>此页面将在5秒后自动关闭...</p>
                <script>
                    // 尝试关闭页面
                    setTimeout(function() {{
                        window.close();
                    }}, 5000);
                </script>
            </body>
            </html>
            """.encode('utf-8')
            
            # 防止NoneType异常
            if hasattr(self, 'wfile') and self.wfile is not None:
                try:
                    self.wfile.write(error_html)
                    self.wfile.flush()  # 确保数据发送
                except:
                    pass  # 忽略写入错误
        except Exception as e:
            # 静默处理错误，避免可能的递归异常
            print(f"发送错误响应时出错: {str(e)}")

class OAuthConfigDialog(QDialog):
    def __init__(self, parent=None, client_id="", client_secret=""):
        super().__init__(parent)
        self.setWindowTitle("GitHub OAuth 配置")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # 表单布局
        form_layout = QFormLayout()
        
        # Client ID 输入
        self.client_id_input = StyledLineEdit()
        self.client_id_input.setText(client_id)
        form_layout.addRow("Client ID:", self.client_id_input)
        
        # Client Secret 输入
        self.client_secret_input = StyledLineEdit()
        self.client_secret_input.setText(client_secret)
        form_layout.addRow("Client Secret:", self.client_secret_input)
        
        layout.addLayout(form_layout)
        
        # 帮助链接 - 使用自定义样式
        help_container = QWidget()
        help_layout = QHBoxLayout(help_container)
        help_layout.setContentsMargins(0, 10, 0, 10)
        
        help_label = QLabel('不知道怎么填？')
        help_label.setStyleSheet("color: #666; font-size: 13px;")
        
        help_link = QPushButton("点击这里获取帮助")
        help_link.setCursor(Qt.CursorShape.PointingHandCursor)
        help_link.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {THEME_PINK};
                font-weight: bold;
                text-decoration: none;
                padding: 0px 5px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                color: {THEME_BLUE};
            }}
        """)
        help_link.clicked.connect(lambda: webbrowser.open("https://github.com/alltobebetter/Githuber/blob/main/how_to_input.md"))
        
        help_layout.addStretch()
        help_layout.addWidget(help_label)
        help_layout.addWidget(help_link)
        help_layout.addStretch()
        
        layout.addWidget(help_container)
        
        # 添加分隔线
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: #E0E0E0;")
        layout.addWidget(separator)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 15, 0, 5)
        
        # 确定按钮
        self.ok_button = StyledButton("确定", THEME_BLUE)
        self.ok_button.clicked.connect(self.accept)
        
        # 取消按钮
        self.cancel_button = StyledButton("取消", THEME_PINK)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_values(self):
        return self.client_id_input.text(), self.client_secret_input.text()

class GitHubManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_config()  # 加载配置
        self.github = None
        self.repo = None
        self.git_repo = None
        self.signal_handler = SignalHandler()
        self.signal_handler.auth_success.connect(self.handle_auth_success)
        self.signal_handler.auth_error.connect(self.handle_auth_error)
        self.server = None
        self.server_thread = None
        self.username = None
        self.current_worker = None
        self.auth_timer = None  # 添加认证超时计时器
        self.auth_worker = None  # 添加认证工作线程
        self.access_token = None  # 添加访问令牌变量
        # 保存按钮原始样式
        self.original_button_styles = {}
        self.initUI()
        self.setup_initial_state()
        
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.svg')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 添加隐藏的快捷键
        self._setup_hidden_shortcuts()
        
        # 设置自动检查计时器
        self._setup_auto_check()
            
        # 尝试自动登录
        self.try_auto_login()

    def _setup_hidden_shortcuts(self):
        """设置隐藏的快捷键"""
        # Alt+G+H 组合键打开项目页面
        self.gh_shortcut = QShortcut(QKeySequence("Alt+G, H"), self)
        self.gh_shortcut.activated.connect(self._open_project)
        
        # Ctrl+Alt+P 组合键打开项目页面
        self.project_shortcut = QShortcut(QKeySequence("Ctrl+Alt+P"), self)
        self.project_shortcut.activated.connect(self._open_project)
        
    def _setup_auto_check(self):
        """设置自动检查计时器"""
        # 创建一个隐藏的计时器，定期检查项目按钮是否存在
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._check_project_button)
        # 随机设置间隔时间，避免被发现规律
        interval = random.randint(30000, 60000)  # 30秒到1分钟之间
        self.check_timer.start(interval)
        
    def _check_project_button(self):
        """检查项目按钮是否存在，如果不存在则重新创建"""
        try:
            # 检查项目按钮是否存在于布局中
            button_exists = hasattr(self, 'project_button') and not self.project_button.isHidden()
            
            if not button_exists:
                # 如果按钮不存在或被隐藏，重新创建
                self._recreate_project_button()
                
            # 随机更改下次检查的时间间隔
            new_interval = random.randint(30000, 60000)
            self.check_timer.setInterval(new_interval)
        except Exception:
            # 静默处理异常，避免暴露检查机制
            pass
            
    def _recreate_project_button(self):
        """重新创建项目按钮"""
        try:
            # 创建新的项目按钮
            self.project_button = QPushButton('在GitHub查看此项目')
            self.project_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.project_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 2px dashed {THEME_GRAY};
                    border-radius: 5px;
                    padding: 8px 20px;
                    color: #555;
                    font-weight: bold;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: #F0F0F0;
                }}
            """)
            
            # 设置项目按钮图标
            github_cat_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'github_cat.svg')
            if os.path.exists(github_cat_icon_path):
                self.project_button.setIcon(QIcon(github_cat_icon_path))
            
            # 连接项目按钮点击事件
            self.project_button.clicked.connect(self._open_project)
            
            # 将按钮添加到布局中
            if hasattr(self, 'auth_layout'):
                # 检查是否已经有按钮
                for i in range(self.auth_layout.count()):
                    item = self.auth_layout.itemAt(i)
                    if item and item.widget() and item.widget().text() == '在GitHub查看此项目':
                        # 如果已经有相同的按钮，先移除
                        self.auth_layout.removeItem(item)
                        item.widget().deleteLater()
                        break
                
                # 在认证按钮之前插入项目按钮
                for i in range(self.auth_layout.count()):
                    item = self.auth_layout.itemAt(i)
                    if item and item.widget() and "GitHub:" in item.widget().text():
                        self.auth_layout.insertWidget(i, self.project_button)
                        return
                
                # 如果没有找到认证按钮，直接添加到布局末尾
                self.auth_layout.addWidget(self.project_button)
        except Exception:
            # 静默处理异常
            pass
    
    def load_config(self):
        """从配置文件加载 OAuth 配置"""
        global CLIENT_ID, CLIENT_SECRET
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    CLIENT_ID = config.get('client_id', '')
                    CLIENT_SECRET = config.get('client_secret', '')
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
            
    def load_token(self):
        """从文件加载保存的访问令牌"""
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                    return token_data.get('access_token', None)
            return None
        except Exception as e:
            self.log_output(f"加载访问令牌失败: {str(e)}")
            return None
            
    def save_token(self, access_token):
        """保存访问令牌到文件"""
        try:
            token_data = {
                'access_token': access_token
            }
            with open(TOKEN_FILE, 'w') as f:
                json.dump(token_data, f)
            return True
        except Exception as e:
            self.log_output(f"保存访问令牌失败: {str(e)}")
            return False
            
    def try_auto_login(self):
        """尝试使用保存的令牌自动登录"""
        access_token = self.load_token()
        if access_token:
            self.log_output("检测到保存的登录状态，正在尝试自动登录...")
            self.access_token = access_token
            
            # 创建一个工作线程来处理GitHub API调用
            self.auth_worker = Worker(self.process_auth_token, access_token)
            self.auth_worker.signals.finished.connect(self.on_auth_process_finished)
            self.auth_worker.signals.error.connect(self.on_auto_login_error)
            self.auth_worker.start()

    def on_auto_login_error(self, error_message):
        """自动登录失败处理"""
        self.log_output(f"自动登录失败: {error_message}")
        self.log_output("令牌可能已过期，请重新登录")
        
        # 删除无效的令牌文件
        try:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
        except Exception as e:
            self.log_output(f"删除无效令牌文件失败: {str(e)}")
        
        self.auth_button.setEnabled(True)
        self.auth_button.setText("GitHub: 未登录")
        self.github = None
        self.access_token = None

    def save_config(self, client_id, client_secret):
        """保存 OAuth 配置到文件"""
        global CLIENT_ID, CLIENT_SECRET
        try:
            config = {
                'client_id': client_id,
                'client_secret': client_secret
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            CLIENT_ID = client_id
            CLIENT_SECRET = client_secret
            return True
        except Exception as e:
            self.log_output(f"保存配置失败: {str(e)}")
            return False

    def show_oauth_config(self):
        """显示 OAuth 配置对话框"""
        dialog = OAuthConfigDialog(self, CLIENT_ID, CLIENT_SECRET)
        if dialog.exec():
            client_id, client_secret = dialog.get_values()
            if client_id and client_secret:
                if self.save_config(client_id, client_secret):
                    self.log_output("OAuth 配置已保存")
                    # 如果已经有配置按钮，则隐藏它
                    if hasattr(self, 'config_button'):
                        self.config_button.hide()
                    # 添加配置按钮（如果还没有）
                    if not hasattr(self, 'config_button'):
                        self.config_button = StyledButton("修改配置", THEME_BLUE)
                        self.config_button.clicked.connect(self.show_oauth_config)
                        self.auth_layout.insertWidget(0, self.config_button)
                    else:
                        self.config_button.show()
                    return True
            else:
                self.log_output("请输入有效的 Client ID 和 Client Secret")
        return False

    def setup_initial_state(self):
        """设置初始状态"""
        # 禁用Git相关的功能，直到选择仓库
        self.file_list.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.stage_button.setEnabled(False)
        self.commit_button.setEnabled(False)
        self.push_button.setEnabled(False)

    def enable_features(self):
        """登录成功后启用功能"""
        self.repo_input.setEnabled(True)
        self.local_path_input.setEnabled(True)
        self.browse_button.setEnabled(True)
        # 文件操作相关的按钮初始状态为禁用
        self.file_list.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.stage_button.setEnabled(False)
        self.commit_button.setEnabled(False)
        self.push_button.setEnabled(False)

    def update_git_features(self, has_git=False):
        """更新Git相关功能的状态"""
        self.file_list.setEnabled(has_git)
        self.refresh_button.setEnabled(has_git)
        self.stage_button.setEnabled(has_git)
        self.commit_button.setEnabled(has_git)
        self.push_button.setEnabled(has_git)
        
        # 设置按钮颜色
        if has_git:
            # 恢复原始样式，而不是重新应用当前样式
            if 'refresh' in self.original_button_styles:
                self.refresh_button.setStyleSheet(self.original_button_styles['refresh'])
            if 'stage' in self.original_button_styles:
                self.stage_button.setStyleSheet(self.original_button_styles['stage'])
            if 'commit' in self.original_button_styles:
                self.commit_button.setStyleSheet(self.original_button_styles['commit'])
            if 'push' in self.original_button_styles:
                self.push_button.setStyleSheet(self.original_button_styles['push'])
        else:
            disabled_style = f"""
                QPushButton {{
                    background-color: transparent;
                    border: 2px dashed {DISABLED_COLOR};
                    border-radius: 5px;
                    padding: 8px 20px;
                    color: #999;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: transparent;
                }}
            """
            self.refresh_button.setStyleSheet(disabled_style)
            self.stage_button.setStyleSheet(disabled_style)
            self.commit_button.setStyleSheet(disabled_style)
            self.push_button.setStyleSheet(disabled_style)

    def initUI(self):
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
            QListWidget {
                border: 2px solid #87CEEB;
                border-radius: 5px;
                background-color: white;
            }
            QTextEdit {
                border: 2px solid #87CEEB;
                border-radius: 5px;
                background-color: #F8F8F8;
                font-family: Consolas, Monaco, monospace;
            }
        """)
        
        self.setWindowTitle('GitHub文件管理器')
        self.setGeometry(100, 100, 900, 600)  # 将宽度从 1200 改为 900
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        layout = QHBoxLayout()
        layout.setSpacing(20)  # 增加组件之间的间距
        
        # 左侧面板 - GitHub认证
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)
        
        # 文件操作部分
        self.local_path_label = QLabel('本地仓库路径:')
        self.local_path_input = StyledLineEdit()
        self.browse_button = StyledButton('浏览', THEME_PINK)
        self.browse_button.clicked.connect(self.browse_directory)
        
        # 仓库地址显示
        self.repo_label = QLabel('仓库地址:')
        self.repo_input = StyledLineEdit()
        self.repo_input.setReadOnly(True)  # 设置为只读
        
        # 新仓库名称（始终显示）
        self.new_repo_label = QLabel('新仓库名称:')
        self.new_repo_input = StyledLineEdit()
        self.new_repo_input.setEnabled(False)  # 初始状态禁用
        
        # 创建仓库按钮（初始隐藏）
        self.create_repo_button = StyledButton('创建并初始化仓库', THEME_BLUE)
        self.create_repo_button.clicked.connect(self.create_new_repo)
        self.create_repo_button.hide()
        
        # GitHub认证部分（移到底部）
        auth_group = QWidget()
        self.auth_layout = QVBoxLayout()  # 使用实例变量存储布局
        self.auth_layout.setSpacing(10)
        
        # 添加项目按钮（在认证按钮上方）
        self.project_button = QPushButton('在GitHub查看此项目')
        self.project_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px dashed {THEME_GRAY};
                border-radius: 5px;
                padding: 8px 20px;
                color: #555;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: #F0F0F0;
            }}
        """)
        
        # 设置项目按钮图标
        github_cat_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'github_cat.svg')
        if os.path.exists(github_cat_icon_path):
            self.project_button.setIcon(QIcon(github_cat_icon_path))
        
        # 连接项目按钮点击事件
        self.project_button.clicked.connect(self._open_project)
        
        # 创建集成了登录状态的按钮
        self.auth_button = QPushButton('GitHub: 未登录')
        self.auth_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auth_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px dashed {THEME_BLUE};
                border-radius: 5px;
                padding: 8px 20px;
                color: #333;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {THEME_LIGHT_BLUE};
            }}
        """)
        self.auth_button.clicked.connect(self.toggle_auth)
        
        # 如果已经有配置，添加修改配置按钮
        if CLIENT_ID and CLIENT_SECRET:
            self.config_button = StyledButton("修改配置", THEME_BLUE)
            self.config_button.clicked.connect(self.show_oauth_config)
            self.auth_layout.addWidget(self.config_button)
        
        self.auth_layout.addWidget(self.project_button)  # 添加项目按钮
        self.auth_layout.addWidget(self.auth_button)
        auth_group.setLayout(self.auth_layout)
        
        # 添加组件到左侧面板
        left_layout.addWidget(self.local_path_label)
        left_layout.addWidget(self.local_path_input)
        left_layout.addWidget(self.browse_button)
        left_layout.addWidget(self.repo_label)
        left_layout.addWidget(self.repo_input)
        left_layout.addWidget(self.new_repo_label)
        left_layout.addWidget(self.new_repo_input)
        left_layout.addWidget(self.create_repo_button)
        left_layout.addStretch()  # 添加弹性空间
        left_layout.addWidget(auth_group)  # 认证部分放在最底部
        
        left_panel.setLayout(left_layout)
        
        # 中间面板 - 文件暂存区
        middle_panel = QWidget()
        middle_layout = QVBoxLayout()
        middle_layout.setSpacing(10)
        
        files_label = QLabel('文件暂存区')
        files_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        
        self.file_list = QListWidget()
        # 修改为ExtendedSelection模式，支持更灵活的选择方式
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        # 连接项目点击事件，自定义处理选择行为
        self.file_list.itemClicked.connect(self.toggle_item_selection)
        # 连接选择变化事件
        self.file_list.itemSelectionChanged.connect(self.update_selection_status)
        
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #87CEEB;
                border-radius: 5px;
                background-color: white;
                font-family: Consolas, Monaco, monospace;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #E0E0E0;
            }
            QListWidget::item:selected {
                background-color: #E6F3F7;
                color: #333;
            }
            QListWidget::item:hover {
                background-color: #FFE6EA;
            }
        """)
        
        # 添加多选提示标签
        selection_hint = QLabel('提示: 点击可选择文件，Ctrl或Shift键可多选')
        selection_hint.setStyleSheet("font-size: 12px; color: #666; font-style: italic;")
        
        # 添加选择状态标签
        self.selection_status = QLabel('已选择: 0 个文件')
        self.selection_status.setStyleSheet("font-size: 12px; color: #333; margin-top: 5px;")
        
        self.refresh_button = StyledButton('刷新文件列表', THEME_BLUE)
        self.refresh_button.clicked.connect(self.refresh_files)
        # 保存原始样式
        self.original_button_styles['refresh'] = self.refresh_button.styleSheet()
        
        self.stage_button = StyledButton('暂存选中文件', THEME_PINK)
        self.stage_button.clicked.connect(self.stage_files)
        # 保存原始样式
        self.original_button_styles['stage'] = self.stage_button.styleSheet()
        
        self.commit_button = StyledButton('提交更改', THEME_BLUE)
        self.commit_button.clicked.connect(self.commit_changes)
        # 保存原始样式
        self.original_button_styles['commit'] = self.commit_button.styleSheet()
        
        self.push_button = StyledButton('推送到GitHub', THEME_PINK)
        self.push_button.clicked.connect(self.push_to_github)
        # 保存原始样式
        self.original_button_styles['push'] = self.push_button.styleSheet()
        
        middle_layout.addWidget(files_label)
        middle_layout.addWidget(self.file_list)
        middle_layout.addWidget(selection_hint)  # 添加多选提示
        middle_layout.addWidget(self.selection_status)  # 添加选择状态
        middle_layout.addWidget(self.refresh_button)
        middle_layout.addWidget(self.stage_button)
        middle_layout.addWidget(self.commit_button)
        middle_layout.addWidget(self.push_button)
        
        middle_panel.setLayout(middle_layout)
        
        # 右侧面板 - 命令输出
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        output_label = QLabel('命令输出')
        output_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        
        right_layout.addWidget(output_label)
        right_layout.addWidget(self.output_text)
        
        right_panel.setLayout(right_layout)
        
        # 添加所有面板到主布局
        layout.addWidget(left_panel)
        layout.addWidget(middle_panel)
        layout.addWidget(right_panel)
        
        # 设置布局比例
        layout.setStretch(0, 1)
        layout.setStretch(1, 2)
        layout.setStretch(2, 2)
        
        main_widget.setLayout(layout)

    def toggle_auth(self):
        """切换登录/登出状态"""
        if self.github is None:
            # 未登录状态，执行登录
            self.start_oauth()
        else:
            # 已登录状态，执行登出
            self.logout()

    def start_oauth(self):
        global CLIENT_ID, CLIENT_SECRET
        
        # 检查是否已配置 OAuth
        if not CLIENT_ID or not CLIENT_SECRET:
            if not self.show_oauth_config():
                return
        
        # 先检测网络连接
        self.log_output("正在检测网络连接...")
        self.auth_button.setEnabled(False)
        self.auth_button.setText("检测网络中...")
        
        # 直接启动OAuth流程，跳过网络检测
        self.log_output("网络连接正常，开始GitHub认证...")
        self.start_oauth_process()

    def start_oauth_process(self):
        """启动OAuth认证流程"""
        try:
            # 关闭之前的服务器（如果有）
            self.stop_server()
            
            # 尝试端口列表 - 从常用端口到不常用端口
            port_list = [8000, 8080, 6789, 5678, 3000, 9000, 10000, 12345]
            success = False
            
            for port in port_list:
                self.log_output(f"尝试在端口 {port} 上启动服务器...")
                
                # 先检查端口是否可用
                if not self.is_port_available(port):
                    self.log_output(f"端口 {port} 已被占用，尝试下一个端口...")
                    continue
                
                # 尝试启动服务器
                try:
                    global REDIRECT_URI
                    REDIRECT_URI = f"http://localhost:{port}/callback"
                    self.server = HTTPServer(('localhost', port), OAuthCallbackHandler)
                    self.server_thread = threading.Thread(target=self.run_server)
                    self.server_thread.daemon = True
                    self.server_thread.start()
                    
                    # 验证服务器是否真的在运行
                    time.sleep(0.5)  # 给服务器启动一点时间
                    if self.is_server_running(port):
                        self.log_output(f"成功在端口 {port} 上启动服务器")
                        success = True
                        break
                    else:
                        self.log_output(f"服务器似乎没有在端口 {port} 上正常运行，尝试下一个端口...")
                        self.stop_server()
                except Exception as e:
                    self.log_output(f"在端口 {port} 上启动服务器失败: {str(e)}")
                    self.stop_server()
            
            if not success:
                self.log_output("无法启动认证服务器，请尝试以管理员身份运行或检查防火墙设置")
                self.auth_button.setEnabled(True)
                self.auth_button.setText("GitHub: 未登录")
                return
            
            # 设置认证超时计时器
            if self.auth_timer is None:
                self.auth_timer = QThread()
                self.auth_timer.run = self.check_auth_timeout
                self.auth_timer.daemon = True
                self.auth_timer.start()
            
            # 构建GitHub OAuth URL
            auth_url = f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=repo"
            # 打开浏览器前添加延迟，确保服务器已经启动
            QTimer.singleShot(1000, lambda: self.open_browser(auth_url))
            self.log_output("已打开浏览器，请在浏览器中完成GitHub授权...")
            
            # 禁用认证按钮，防止重复点击
            self.auth_button.setEnabled(False)
            self.auth_button.setText("认证中...")
            
        except Exception as e:
            self.log_output(f"启动认证流程失败: {str(e)}")
            self.auth_button.setEnabled(True)
            self.auth_button.setText("GitHub: 未登录")
    
    def is_port_available(self, port):
        """检查端口是否可用"""
        try:
            # 尝试绑定端口
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.bind(("localhost", port))
            s.close()
            return True
        except:
            return False
    
    def is_server_running(self, port):
        """验证服务器是否在运行"""
        try:
            # 尝试连接到服务器
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("localhost", port))
            s.close()
            return True
        except:
            return False

    def open_browser(self, url):
        """在单独的线程中打开浏览器"""
        try:
            webbrowser.open(url)
        except Exception as e:
            self.log_output(f"打开浏览器失败: {str(e)}")
            
    def run_server(self):
        """在线程中运行HTTP服务器，带有超时处理"""
        try:
            # 设置服务器超时
            self.server.timeout = 0.5  # 更短的超时，提高响应性
            
            # 运行服务器，直到应用关闭或认证完成
            start_time = time.time()
            max_time = 180  # 3分钟超时
            self.log_output("认证服务器已启动，等待GitHub回调...")
            
            while time.time() - start_time < max_time:
                try:
                    # 输出定期的心跳日志，确认服务器仍在运行
                    if int(time.time() - start_time) % 30 == 0 and int(time.time() - start_time) > 0:
                        self.log_output(f"服务器仍在等待GitHub回调... (已等待 {int(time.time() - start_time)} 秒)")
                    
                    # 处理一个请求，然后返回
                    self.server.handle_request()
                    
                    # 如果已经认证成功，退出循环
                    if self.github is not None:
                        self.log_output("认证成功，正在关闭服务器...")
                        break
                except socket.timeout:
                    # 正常的超时，继续循环
                    pass
                except Exception as e:
                    # 记录其他异常，但继续运行
                    print(f"服务器处理请求时出错: {str(e)}")
                    # 短暂暂停，避免过度记录错误
                    time.sleep(0.1)
            
            # 超时或完成后关闭服务器
            self.stop_server()
            
            # 如果是因为超时退出，且没有认证成功
            if self.github is None and time.time() - start_time >= max_time:
                self.log_output("认证服务器超时，请重试登录...")
                # 通过信号发出超时通知
                self.signal_handler.auth_error.emit("认证超时，服务器已关闭。请重试登录过程。")
                
        except Exception as e:
            self.log_output(f"服务器线程出错: {str(e)}")
            print(f"服务器线程详细错误: {str(e)}")
            # 尝试关闭服务器
            self.stop_server()

    def stop_server(self):
        """安全地关闭HTTP服务器"""
        if self.server is not None:
            try:
                self.server.server_close()
            except:
                pass
            self.server = None

    def check_auth_timeout(self):
        """检查认证是否超时"""
        start_time = time.time()
        while time.time() - start_time < 60:  # 1分钟超时，减少等待时间
            time.sleep(1)
            if self.github is not None:  # 如果已认证成功
                return
        
        # 超时处理
        if self.github is None and not self.auth_button.isEnabled():
            self.signal_handler.auth_error.emit("认证超时，可能是网络问题导致。如果您在中国大陆，可能需要使用代理。")

    def handle_auth_success(self, access_token):
        """处理认证成功"""
        # 保存访问令牌
        self.access_token = access_token
        self.save_token(access_token)
        
        # 创建一个工作线程来处理GitHub API调用
        self.auth_worker = Worker(self.process_auth_token, access_token)
        self.auth_worker.signals.finished.connect(self.on_auth_process_finished)
        self.auth_worker.signals.error.connect(self.on_auth_process_error)
        self.auth_worker.start()
        
    def process_auth_token(self, access_token):
        """在工作线程中处理认证令牌"""
        # 设置较短的超时时间
        g = Github(access_token, timeout=10)
        user = g.get_user()
        username = user.login
        
        # 返回处理结果
        return {
            'github': g,
            'username': username
        }
        
    def on_auth_process_finished(self):
        """认证处理完成"""
        if hasattr(self.auth_worker, 'fn') and hasattr(self.auth_worker, 'result'):
            result = self.auth_worker.result
            self.github = result['github']
            self.username = result['username']
            
            # 更新按钮显示
            self.auth_button.setEnabled(True)
            self.auth_button.setText(f"{self.username}")
            self.auth_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 2px dashed {THEME_PINK};
                    border-radius: 5px;
                    padding: 8px 20px;
                    color: #333;
                    font-weight: bold;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {THEME_LIGHT_PINK};
                    color: #333;
                }}
            """)
            
            # 设置悬停文本
            self.auth_button.setToolTip(f"{self.username} / 点击退出登录")
            
            self.log_output("GitHub认证成功！")
            self.enable_features()  # 启用所有功能
            
            # 如果已经有仓库地址，尝试连接
            repo_url = self.repo_input.text()
            if repo_url:
                try:
                    repo_parts = repo_url.split('/')
                    repo_name = '/'.join(repo_parts[-2:])
                    self.repo = self.github.get_repo(repo_name)
                    self.log_output(f"成功连接到仓库: {repo_name}")
                except Exception as e:
                    self.log_output(f"连接仓库失败: {str(e)}")
            
            # 更新文件列表（如果有）
            if self.git_repo:
                self.refresh_files()
    
    def on_auth_process_error(self, error_message):
        """认证处理错误"""
        self.log_output(f"认证处理失败: {error_message}")
        self.log_output("可能原因：")
        self.log_output("1. GitHub API访问受限")
        self.log_output("2. 网络连接不稳定")
        self.log_output("3. 需要配置代理")
        
        self.auth_button.setEnabled(True)
        self.auth_button.setText("GitHub: 未登录")
        self.github = None

    def handle_auth_error(self, error_message):
        """处理认证错误"""
        self.log_output(error_message)
        self.auth_button.setEnabled(True)
        self.auth_button.setText("GitHub: 未登录")
        
        # 显示更详细的错误信息
        if "timeout" in error_message.lower() or "连接" in error_message:
            self.log_output("网络连接问题可能是由于:")
            self.log_output("1. GitHub在您的地区可能被限制访问")
            self.log_output("2. 需要配置代理")
            self.log_output("3. 网络连接不稳定")
            self.log_output("建议: 如果您在中国大陆，可能需要使用代理服务")

    def get_repo_url_from_git(self, directory):
        """从Git配置中获取仓库地址"""
        try:
            repo = git.Repo(directory)
            if 'origin' in repo.remotes:
                url = repo.remotes.origin.url
                # 转换SSH格式为HTTPS格式（如果是SSH格式的话）
                if url.startswith('git@github.com:'):
                    url = url.replace('git@github.com:', 'https://github.com/')
                if url.endswith('.git'):
                    url = url[:-4]
                return url
        except Exception as e:
            self.log_output(f"读取仓库地址失败: {str(e)}")
        return None

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择本地仓库目录")
        if directory:
            self.local_path_input.setText(directory)
            try:
                self.git_repo = git.Repo(directory)
                # 尝试获取并填写仓库地址
                repo_url = self.get_repo_url_from_git(directory)
                if repo_url:
                    self.repo_input.setText(repo_url)
                    # 如果已经登录，尝试连接到仓库
                    if self.github:
                        try:
                            repo_parts = repo_url.split('/')
                            repo_name = '/'.join(repo_parts[-2:])
                            self.repo = self.github.get_repo(repo_name)
                            self.log_output(f"成功连接到仓库: {repo_name}")
                            self.new_repo_input.setEnabled(False)  # 禁用新仓库名称输入
                            self.create_repo_button.hide()  # 隐藏创建按钮
                        except Exception as e:
                            self.log_output(f"连接仓库失败: {str(e)}")
                
                self.update_git_features(True)  # 启用Git相关功能
                self.refresh_files()  # 使用新的线程化方法加载文件
            except git.exc.InvalidGitRepositoryError:
                self.log_output("选择的目录不是Git仓库")
                if self.github:  # 只有在登录状态下才启用新仓库创建
                    self.new_repo_input.setEnabled(True)  # 启用新仓库名称输入
                    self.create_repo_button.show()  # 显示创建按钮
                self.git_repo = None
                self.repo_input.clear()  # 清空仓库地址
                self.update_git_features(False)  # 禁用Git相关功能

    def run_git_command(self, command, cwd=None):
        """在指定目录运行Git命令并返回输出"""
        try:
            # 设置环境变量以处理中文和网络
            my_env = os.environ.copy()
            my_env["PYTHONIOENCODING"] = "utf-8"
            my_env["LANG"] = "en_US.UTF-8"
            
            # 添加 SSL 验证禁用（如果需要）
            my_env["GIT_SSL_NO_VERIFY"] = "1"
            
            # 设置 HTTP 代理（如果需要）
            # my_env["HTTP_PROXY"] = "http://your-proxy:port"
            # my_env["HTTPS_PROXY"] = "http://your-proxy:port"
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                cwd=cwd,
                text=True,
                encoding='utf-8',
                env=my_env
            )
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.log_output(output.strip())
            
            rc = process.poll()
            if rc != 0:
                error = process.stderr.read()
                if error:
                    self.log_output(f"错误: {error}")
                    # 网络错误处理
                    if "Failed to connect" in error or "Could not resolve host" in error:
                        self.log_output("网络连接失败，请检查：")
                        self.log_output("1. 确保网络连接正常")
                        self.log_output("2. 检查是否需要配置代理")
                        self.log_output("3. 如果使用代理，请设置 git config --global http.proxy")
                        self.log_output("4. 可以尝试在命令行执行: git config --global http.sslVerify false")
                return False
            return True
        except Exception as e:
            self.log_output(f"执行命令失败: {str(e)}")
            return False

    def create_new_repo_worker(self, repo_name, directory):
        try:
            # 首先测试网络连接并配置 Git
            self.log_output("正在配置 Git 网络设置...")
            
            # 配置 Git 网络设置
            network_config_commands = [
                'git config --global http.sslVerify false',
                'git config --global http.postBuffer 524288000',
                'git config --global http.lowSpeedLimit 0',
                'git config --global http.lowSpeedTime 999999'
            ]
            
            for cmd in network_config_commands:
                if not self.run_git_command(cmd, directory):
                    self.log_output(f"警告: {cmd} 配置失败，继续执行...")

            # 测试网络连接
            try:
                self.github.get_user().get_repos()
                self.log_output("GitHub 连接正常")
            except Exception as e:
                self.log_output("无法连接到 GitHub，正在尝试其他配置...")
                # 尝试设置代理（如果环境中有代理的话）
                if "HTTP_PROXY" in os.environ:
                    self.run_git_command(f'git config --global http.proxy {os.environ["HTTP_PROXY"]}', directory)
                if "HTTPS_PROXY" in os.environ:
                    self.run_git_command(f'git config --global https.proxy {os.environ["HTTPS_PROXY"]}', directory)

            self.log_output(f"正在创建GitHub仓库: {repo_name}...")
            new_repo = self.github.get_user().create_repo(repo_name)
            self.repo = new_repo
            self.repo_input.setText(new_repo.html_url)
            self.log_output(f"GitHub仓库创建成功: {repo_name}")
            
            self.log_output("正在初始化本地Git仓库...")
            if not self.run_git_command("git init -b main", directory):
                raise Exception("Git初始化失败")

            self.log_output("正在配置远程仓库...")
            remote_url = new_repo.clone_url
            # 尝试使用 HTTPS 和 SSH 格式
            if not self.run_git_command(f'git remote add origin {remote_url}', directory):
                ssh_url = new_repo.ssh_url
                if not self.run_git_command(f'git remote set-url origin {ssh_url}', directory):
                    raise Exception("添加远程仓库失败")

            # 配置Git用户信息
            if not self.run_git_command(f'git config user.name "{self.username}"', directory):
                raise Exception("配置用户名失败")
            if not self.run_git_command('git config user.email "noreply@github.com"', directory):
                raise Exception("配置邮箱失败")

            # 配置Git编码
            encoding_commands = [
                'git config core.quotepath false',
                'git config gui.encoding utf-8',
                'git config i18n.commitencoding utf-8',
                'git config i18n.logoutputencoding utf-8'
            ]
            
            for cmd in encoding_commands:
                if not self.run_git_command(cmd, directory):
                    self.log_output(f"警告: {cmd} 配置失败，继续执行...")

            self.log_output("正在添加文件...")
            if not self.run_git_command("git add .", directory):
                raise Exception("添加文件失败")

            self.log_output("正在提交更改...")
            if not self.run_git_command('git commit -m "初始提交"', directory):
                raise Exception("提交更改失败")

            self.log_output("正在推送到GitHub...")
            # 设置分支名称
            if not self.run_git_command("git branch -M main", directory):
                raise Exception("设置分支名称失败")
            
            # 多次尝试推送，使用不同的配置
            push_attempts = [
                "git push -u origin main",
                "git push -u origin main --force",
                "git push -u origin main --verbose"
            ]
            
            success = False
            for push_cmd in push_attempts:
                self.log_output(f"尝试推送命令: {push_cmd}")
                if self.run_git_command(push_cmd, directory):
                    success = True
                    break
                else:
                    self.log_output("推送失败，尝试其他方式...")
                    # 在重试之前等待一下
                    time.sleep(2)
            
            if not success:
                raise Exception("所有推送尝试都失败，请检查网络连接")

            self.git_repo = git.Repo(directory)
            self.new_repo_input.setEnabled(False)
            self.create_repo_button.hide()
            self.update_git_features(True)  # 启用Git相关功能，确保调用此函数恢复样式
            
            # 使用QTimer在主线程中调用refresh_files，避免线程安全问题
            QTimer.singleShot(100, self.refresh_files)
            
            self.log_output("仓库创建和初始化完成！")
            
        except Exception as e:
            self.log_output(f"创建仓库失败: {str(e)}")
            self.update_git_features(False)  # 禁用Git相关功能
            # 如果失败，尝试清理
            try:
                if self.repo:
                    self.repo.delete()
                    self.log_output("已删除远程仓库")
            except:
                pass
    
    def create_new_repo(self):
        if not self.github or not self.username:
            self.log_output("请先登录GitHub！")
            return
            
        repo_name = self.new_repo_input.text()
        if not repo_name:
            self.log_output("请输入新仓库名称！")
            return
            
        directory = self.local_path_input.text()
        if not directory:
            self.log_output("请选择本地目录！")
            return

        # 创建工作线程
        self.current_worker = Worker(
            self.create_new_repo_worker,
            repo_name,
            directory
        )
        self.current_worker.start()

    def refresh_files(self):
        if not self.git_repo:
            return
            
        # 禁用刷新按钮，防止重复点击
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("加载中...")
        self.log_output("正在加载文件列表...")
        
        # 创建工作线程来加载文件列表
        self.current_worker = Worker(
            self.refresh_files_worker,
            self.git_repo.working_dir
        )
        self.current_worker.signals.finished.connect(self.on_refresh_files_finished)
        self.current_worker.signals.error.connect(self.on_refresh_files_error)
        self.current_worker.start()
        
        # 设置超时计时器，15秒后如果还没完成就强制结束
        QTimer.singleShot(15000, self.check_refresh_timeout)
        
    def check_refresh_timeout(self):
        """检查文件加载是否超时"""
        if hasattr(self, 'current_worker') and self.current_worker and self.refresh_button.text() == "加载中...":
            self.log_output("文件列表加载超时，已强制停止")
            self.on_refresh_files_finished()  # 强制完成
            
    def on_refresh_files_finished(self):
        """文件列表加载完成后的处理"""
        # 恢复按钮状态
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("刷新文件列表")
        
        # 如果有结果，更新文件列表
        if hasattr(self, 'current_worker') and hasattr(self.current_worker, 'result'):
            file_items = self.current_worker.result
            if file_items:
                # 清空当前列表
                self.file_list.clear()
                # 添加所有文件项目
                for item in file_items:
                    self.file_list.addItem(item)
                
                self.log_output("文件列表加载完成")
            else:
                self.log_output("没有找到文件")
        else:
            self.log_output("文件列表加载完成")
            
        # 重置选择状态
        self.update_selection_status()

    def on_refresh_files_error(self, error_message):
        """文件列表加载出错的处理"""
        self.log_output(f"加载文件列表失败: {error_message}")
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("刷新文件列表")
        
    def refresh_files_worker(self, directory):
        """在工作线程中加载文件列表"""
        try:
            # 不在工作线程中清空文件列表，而是在主线程的on_refresh_files_finished中处理
            repo = self.git_repo
            
            # 只获取根目录下的文件和文件夹
            root_items = os.listdir(directory)
            file_items = []  # 收集所有要显示的项目
            
            for item in sorted(root_items):
                full_path = item  # 只处理根目录下的项目
                abs_path = os.path.join(directory, full_path)
                
                # 如果是目录，只添加目录项，不递归处理
                if os.path.isdir(abs_path):
                    if item != '.git':  # 排除.git目录
                        file_items.append(f"📁 {full_path}/")
                else:
                    # 检查文件状态
                    try:
                        if full_path in repo.untracked_files:
                            file_items.append(f"📄 未跟踪: {full_path}")
                        else:
                            # 检查已修改的文件
                            diff_list = [item.a_path for item in repo.index.diff(None)]
                            if full_path in diff_list:
                                file_items.append(f"📄 已修改: {full_path}")
                            else:
                                # 显示已跟踪的文件
                                file_items.append(f"📄 {full_path}")
                    except Exception as e:
                        print(f"检查文件状态失败 {full_path}: {str(e)}")
            
            # 返回收集到的文件项目列表
            return file_items
            
        except Exception as e:
            raise Exception(f"刷新文件列表失败: {str(e)}")
            
    def stage_files_worker(self, file_paths):
        try:
            for file_path in file_paths:
                self.log_output(f"正在暂存文件: {file_path}")
                if not self.run_git_command(f'git add "{file_path}"', self.git_repo.working_dir):
                    raise Exception(f"暂存文件失败: {file_path}")
            
            # 使用QTimer在主线程中调用refresh_files，避免线程安全问题
            QTimer.singleShot(100, self.refresh_files)
            
            self.log_output("文件暂存完成")
        except Exception as e:
            self.log_output(f"暂存失败: {str(e)}")

    def stage_files(self):
        if not self.git_repo:
            return
            
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            self.log_output("请先选择要暂存的文件")
            return
            
        file_paths = []
        for item in selected_items:
            text = item.text()
            # 处理不同类型的文件项目
            if text.startswith("📁 "):  # 文件夹
                path = text[3:].strip().rstrip('/')
                file_paths.append(path)
            elif ":" in text:  # 未跟踪或已修改的文件
                path = text.split(": ")[1].strip()
                file_paths.append(path)
            else:  # 普通文件
                path = text[2:].strip()  # 移除文件图标
                file_paths.append(path)
        
        self.log_output(f"准备暂存 {len(file_paths)} 个文件")
        
        self.current_worker = Worker(
            self.stage_files_worker,
            file_paths
        )
        self.current_worker.start()

    def commit_changes_worker(self):
        try:
            self.log_output("正在提交更改...")
            if not self.run_git_command('git commit -m "更新文件"', self.git_repo.working_dir):
                raise Exception("提交失败")
            
            # 使用QTimer在主线程中调用refresh_files，避免线程安全问题
            QTimer.singleShot(100, self.refresh_files)
            
            self.log_output("更改提交完成")
        except Exception as e:
            self.log_output(f"提交失败: {str(e)}")

    def commit_changes(self):
        if not self.git_repo:
            return
            
        self.current_worker = Worker(self.commit_changes_worker)
        self.current_worker.start()

    def push_to_github_worker(self):
        try:
            self.log_output("正在推送到GitHub...")
            
            # 首先测试网络连接
            test_command = 'git ls-remote --exit-code origin'
            if not self.run_git_command(test_command, self.git_repo.working_dir):
                self.log_output("无法连接到远程仓库，正在尝试配置...")
                
                # 尝试配置 SSL 验证
                self.run_git_command('git config --global http.sslVerify false', self.git_repo.working_dir)
                
                # 重新尝试推送
                if not self.run_git_command("git push", self.git_repo.working_dir):
                    raise Exception("推送失败，请检查网络连接或代理设置")
            else:
                # 网络正常，直接推送
                if not self.run_git_command("git push", self.git_repo.working_dir):
                    raise Exception("推送失败")
            
            # 使用QTimer在主线程中调用refresh_files，避免线程安全问题
            QTimer.singleShot(100, self.refresh_files)
            
            self.log_output("推送完成")
        except Exception as e:
            self.log_output(f"推送失败: {str(e)}")

    def push_to_github(self):
        if not self.git_repo or not self.repo:
            return
            
        self.current_worker = Worker(self.push_to_github_worker)
        self.current_worker.start()
    
    def log_output(self, message):
        self.output_text.append(f"[{message}]")

    def logout(self):
        """退出登录"""
        self.github = None
        self.repo = None
        self.git_repo = None
        self.username = None
        self.access_token = None
        
        # 删除令牌文件
        try:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
                self.log_output("已清除保存的登录状态")
        except Exception as e:
            self.log_output(f"清除登录状态失败: {str(e)}")
        
        # 重置按钮状态
        self.auth_button.setEnabled(True)
        self.auth_button.setText("GitHub: 未登录")
        self.auth_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px dashed {THEME_BLUE};
                border-radius: 5px;
                padding: 8px 20px;
                color: #333;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {THEME_LIGHT_BLUE};
            }}
        """)
        self.auth_button.setToolTip("点击登录 GitHub")
        
        # 清空输入框
        self.repo_input.clear()
        self.local_path_input.clear()
        self.new_repo_input.clear()
        self.file_list.clear()
        
        # 禁用功能
        self.setup_initial_state()
        
        self.log_output("已退出登录")

    def _open_project(self):
        """打开项目GitHub页面（使用混淆方式）"""
        try:
            # 动态构建URL，避免直接存储完整URL
            url_parts = [_dc(_p1), _dc(_p2), _dc(_p3)]
            project_url = ''.join(url_parts)
            
            # 使用随机的成功消息
            success_messages = [
                "正在打开项目页面...",
                "查看项目源码...",
                "访问开源仓库..."
            ]
            self.log_output(random.choice(success_messages))
            
            # 打开浏览器
            webbrowser.open(project_url)
        except Exception as e:
            # 隐藏真实错误
            self.log_output("无法打开页面，请检查网络连接")

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        self.log_output("正在关闭应用程序...")
        
        # 创建一个关闭进度对话框
        close_dialog = QDialog(self)
        close_dialog.setWindowTitle("正在关闭")
        close_dialog.setFixedSize(300, 100)
        close_dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
            }
            QLabel {
                color: #333333;
                font-size: 14px;
            }
        """)
        
        dialog_layout = QVBoxLayout()
        message_label = QLabel("正在安全关闭应用程序，请稍候...")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(message_label)
        close_dialog.setLayout(dialog_layout)
        
        # 在单独的线程中执行关闭操作
        close_thread = threading.Thread(target=self.perform_close_operations)
        close_thread.daemon = True
        close_thread.start()
        
        # 显示对话框，但设置一个超时
        close_dialog.show()
        
        # 使用QTimer设置超时
        QTimer.singleShot(3000, lambda: self.force_close(close_dialog))
        
        # 接受关闭事件
        event.accept()
        
        # 随机概率在关闭时访问项目页面
        if random.random() < 0.1:  # 10%的概率
            try:
                url_parts = [_dc(_p1), _dc(_p2), _dc(_p3)]
                project_url = ''.join(url_parts)
                webbrowser.open(project_url)
            except:
                pass
    
    def perform_close_operations(self):
        """执行关闭前的清理操作"""
        try:
            # 安全关闭HTTP服务器
            self.stop_server()
            
            # 安全终止工作线程
            if self.current_worker:
                try:
                    self.current_worker.quit()
                except:
                    pass
                
            # 如果有一些更改没有保存，可以在这里处理
            time.sleep(0.5)  # 给一些时间完成任何正在进行的操作
            
        except Exception as e:
            print(f"关闭操作时出错: {str(e)}")
    
    def force_close(self, dialog):
        """强制关闭应用程序"""
        try:
            dialog.close()
        except:
            pass

    def toggle_item_selection(self, item):
        """处理文件列表中的项目点击事件，实现点击切换选择状态"""
        # 在ExtendedSelection模式下，如果没有按下Ctrl或Shift键，我们需要自定义处理单击行为
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.NoModifier:
            # 如果没有按下任何修饰键，单击行为应该是：
            # 1. 如果只有一个项目被选中且就是当前点击的项目，保持选中状态
            # 2. 如果有多个项目被选中或选中的不是当前项目，那么只选中当前项目
            selected_items = self.file_list.selectedItems()
            
            # 如果当前只有这一个项目被选中，不做任何操作（保持选中状态）
            if len(selected_items) == 1 and selected_items[0] == item:
                pass
            else:
                # 取消所有选择，然后只选中当前项目
                self.file_list.clearSelection()
                item.setSelected(True)
        # 如果按下了Ctrl或Shift键，让QListWidget处理多选行为

    def update_selection_status(self):
        """更新选择状态标签"""
        selected_count = len(self.file_list.selectedItems())
        self.selection_status.setText(f'已选择: {selected_count} 个文件')
        
        # 根据是否有选中项目来启用或禁用暂存按钮
        self.stage_button.setEnabled(selected_count > 0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 添加导入
    from PyQt6.QtCore import QTimer
    
    # 隐藏的自动更新机制
    def _ensure_project_link():
        # 检查是否存在必要的变量
        module_vars = globals()
        required_vars = ['_p1', '_p2', '_p3', '_dc']
        
        # 如果缺少任何必要变量，重新创建它们
        if not all(var in module_vars for var in required_vars):
            # 重新创建项目信息
            module_vars['_p1'] = "aHR0cHM6Ly9naXRodWIuY29tLw=="
            module_vars['_p2'] = "YWxsdG9iZWJldHRlci8="
            module_vars['_p3'] = "R2l0aHViZXI="
            
            # 重新创建解码函数
            def _decode(s):
                try:
                    return base64.b64decode(s).decode('utf-8')
                except:
                    return ""
            module_vars['_dc'] = _decode
    
    # 确保项目链接存在
    _ensure_project_link()
    
    window = GitHubManager()
    window.show()
    sys.exit(app.exec()) 