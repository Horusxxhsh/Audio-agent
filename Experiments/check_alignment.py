import sqlite3
import json

def normalize(obj):
    if isinstance(obj, str):
        try:
             obj = json.loads(obj)
        except: pass
    if isinstance(obj, dict):
        return json.dumps(obj, sort_keys=True)
    return str(obj)

# Load Music
conn_m = sqlite3.connect('music_info.db')
c_m = conn_m.cursor()
c_m.execute("SELECT Parameters FROM music_responses ORDER BY rowid")
music_rows = c_m.fetchall()
conn_m.close()

# Load Audio
conn_a = sqlite3.connect('audio_info.db')
c_a = conn_a.cursor()
c_a.execute("SELECT Parameters FROM audio_vector ORDER BY rowid")
audio_rows = c_a.fetchall()
conn_a.close()

print(f"Music Count: {len(music_rows)}")
print(f"Audio Count: {len(audio_rows)}")

# Check alignment
# Hypothesis: Music[0] == Audio[11] (Assuming 11 pre-existing records)
offset = 11
if len(audio_rows) >= offset + 1:
    m_p = normalize(music_rows[0][0])
    a_p = normalize(audio_rows[offset][0]) # Use offset 11 (12th item)? Or 11 items means 0..10. So 11 is next.
    
    print(f"\nComparing Music[0] with Audio[{offset}]:")
    print(f"Match? {m_p == a_p}")
    # print(f"Music: {m_p[:100]}...")
    # print(f"Audio: {a_p[:100]}...")
    
    # Calculate distance/similarity just in case of float diffs
    # (Reuse simple dict comp logic if needed, but string equality is good first test)
    
    if m_p != a_p:
       print("Mismatch details:")
       # Try finding ANY match for Music[0] in Audio
       found = -1
       for i, row in enumerate(audio_rows):
           if normalize(row[0]) == m_p:
               found = i
               break
       if found != -1:
           print(f"Found Music[0] in Audio at index {found}!")
       else:
           print("Music[0] not found in Audio DB.")

else:
    print("Audio DB too small.")
