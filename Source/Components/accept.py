import os
import platform
import sqlite3
import sys

def safe_open_file(relative_path, absolute_dir=None):
    """尝试打开文件，如果相对路径失败则尝试使用环境变量指定的路径"""

    # 如果没有提供绝对路径，尝试从环境变量获取
    if absolute_dir is None:
        absolute_dir = os.environ.get('DOCUMENTS_DIR')
        # 如果环境变量也不存在，使用默认值
        if not absolute_dir:
            print("警告: 环境变量 DOCUMENTS_DIR 未设置，使用当前目录")
            absolute_dir = os.getcwd()  # 使用当前工作目录作为备选

    try:
        # 首先尝试相对路径
        with open(relative_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print(f"成功从相对路径打开文件: {relative_path}")
            return content
    except FileNotFoundError:
        try:
            # 如果相对路径失败，尝试环境变量指定的路径
            absolute_path = os.path.join(absolute_dir, relative_path)
            with open(absolute_path, 'r', encoding='utf-8') as file:
                content = file.read()
                print(f"成功从环境变量指定路径打开文件: {absolute_path}")
                return content
        except FileNotFoundError:
            print(f"无法打开文件 {relative_path}，相对路径和环境变量路径都失败")
            return ""


# 数据库操作：存储生成的参数到music_responses表
def save_parameters_to_database():
    try:
        if existing_song:
            # 已存在则更新参数
            cursor.execute("""
               UPDATE music_responses 
               SET Preferences = ?, Style = ?, Feature = ?,Parameters = ?
               WHERE SongName = ?
           """, ('accept', result1_str, result2_str, result_str, chat_message))
            print(f"已更新歌曲 {chat_message} 的参数")
        else:
            # 新增记录（只存储歌曲名、参数和偏好的默认值）
            cursor.execute("""
                INSERT INTO music_responses (SongName, Parameters, Preferences, Style, Feature)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_message, result_str, 'accept', result1_str, result2_str))
            print(f"已添加新歌曲 {chat_message} 到数据库")

        # 提交事务
        conn.commit()
        print("参数已成功保存到数据库")
        return True
    except sqlite3.Error as e:
        # 发生错误时回滚
        conn.rollback()
        print(f"数据库操作失败: {str(e)}")
        return False

# 读取 result1.txt 文件
result1_str = safe_open_file("result1.txt")

# 读取 result2.txt 文件
result2_str = safe_open_file("result2.txt")

# 读取 result.txt 文件
result_str = safe_open_file("result.txt")

db_dir = os.environ.get('SUPERTONAL_DIR')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)  # 创建目录（如果不存在）
db_path = os.path.join(db_dir, "music_info.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

if len(sys.argv) > 1:
    if platform.system() == "Windows":
        # Windows命令行通常使用GBK编码
        chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')
    else:
        # Linux/macOS通常使用UTF-8
        chat_message = sys.argv[1]
else:
    chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')


# 检查 chat_message 是否已经存在于数据库中
cursor.execute("SELECT SongName FROM music_responses WHERE SongName =?", (chat_message,))
existing_song = cursor.fetchone()

# 新增记录
save_parameters_to_database()

conn.commit()
# 关闭数据库连接
conn.close()

print(f"已更新歌曲 {chat_message} 为accept")