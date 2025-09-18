import os
import platform
import sqlite3
import sys

def safe_open_file(relative_path, absolute_dir=None):
    """Try to open file, if relative path fails try using environment variable specified path"""

    
    if absolute_dir is None:
        absolute_dir = os.environ.get('DOCUMENTS_DIR')
        
        if not absolute_dir:
            print("Warning: DOCUMENTS_DIR environment variable not set, using current directory")
            absolute_dir = os.getcwd()  

    try:
        
        with open(relative_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print(f"Successfully opened file from relative path: {relative_path}")
            return content
    except FileNotFoundError:
        try:
            
            absolute_path = os.path.join(absolute_dir, relative_path)
            with open(absolute_path, 'r', encoding='utf-8') as file:
                content = file.read()
                print(f"Successfully opened file from environment variable specified path: {absolute_path}")
                return content
        except FileNotFoundError:
            print(f"Cannot open file {relative_path}, both relative path and environment variable path failed")
            return ""



def save_parameters_to_database():
    try:
        if existing_song:
            
            cursor.execute("""
               UPDATE music_responses 
               SET Preferences = ?, Style = ?, Feature = ?,Parameters = ?
               WHERE SongName = ?
           """, ('reject', result1_str, result2_str, result_str, chat_message))
            print(f"Updated parameters for song {chat_message}")
        else:
            
            cursor.execute("""
                INSERT INTO music_responses (SongName, Parameters, Preferences, Style, Feature)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_message, result_str, 'reject', result1_str, result2_str))
            print(f"Added new song {chat_message} to database")

        
        conn.commit()
        print("Parameters successfully saved to database")
        return True
    except sqlite3.Error as e:
        
        conn.rollback()
        print(f"Database operation failed: {str(e)}")
        return False


result1_str = safe_open_file("result1.txt")


result2_str = safe_open_file("result2.txt")


result_str = safe_open_file("result.txt")

db_dir = os.environ.get('SUPERTONAL_DIR')
if not os.path.exists(db_dir):
    os.makedirs(db_dir) 
db_path = os.path.join(db_dir, "music_info.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

if len(sys.argv) > 1:
    if platform.system() == "Windows":
      
        chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')
    else:
      
        chat_message = sys.argv[1]
else:
    chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')



cursor.execute("SELECT SongName FROM music_responses WHERE SongName =?", (chat_message,))
existing_song = cursor.fetchone()


save_parameters_to_database()

conn.commit()

conn.close()

print(f"Updated song {chat_message} to reject")