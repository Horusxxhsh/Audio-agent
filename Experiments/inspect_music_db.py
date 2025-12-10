import sqlite3

conn = sqlite3.connect('music_info.db')
c = conn.cursor()
c.execute("SELECT Parameters FROM music_responses LIMIT 1")
row = c.fetchone()
print("RAW PARAMETERS:", row[0])
conn.close()
