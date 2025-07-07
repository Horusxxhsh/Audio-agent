# -*- coding: gbk -*-
import sqlite3

# 连接到数据库
conn = sqlite3.connect(r'E:\c++\juceproject\juceEffector\supertonal\Builds\VisualStudio2022\music_info.db')
#conn = sqlite3.connect(r'E:\c++\day11\day11\music_info.db')
cursor = conn.cursor()

# 执行查询语句
try:
    cursor.execute("SELECT * FROM music_responses")
    results = cursor.fetchall()
    for row in results:
        print(row)
except sqlite3.Error as e:
    print(f"执行 SQL 语句时出错: {e}")

# 关闭连接
conn.close()