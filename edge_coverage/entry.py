
class Entry:
    path = ''
    m_time = 0
    bin_no = 0
    size_in_bytes = 0

    def __init__(self, path, m_time, bin_no):
        self.path = path
        self.m_time = m_time
        self.bin_no = bin_no

