import os
from sniffapp.settings import *

file_dir = 'uploaded_files/'
file_dir = os.path.join(BASE_DIR, file_dir)
query_packets_file = 'SELECT * FROM packets'
query_transfer_file = 'SELECT * FROM transfer'
