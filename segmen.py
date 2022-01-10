class Segmen:
    FLAG_TYPE = {
        'SYN': 0x2,
        'ACK': 0x10,
        'SYN4ACK': 0x12,
        'FIN4ACK': 0x11,
        'FIN': 0x1,
        'DATA': 0x0
    }

    TYPE_FLAG = {
        0x2: 'SYN',
        0x10: 'ACK',
        0x12: 'SYN4ACK',
        0x11: 'FIN4ACK',
        0x1: 'FIN',
        0x0: 'DATA'
    }

    def __init__(self, seq, ack, flag, checksum=None, data=None, empty=None):
        self.seq = seq
        self.ack = ack
        self.flag = flag
        self.empty = empty if empty else Segmen.ret_empty()
        self.data = data if data else None
        self.checksum = checksum if checksum else self.gen_checksum()
    
    def __str__(self):
        return "flag_type: {}; sequence: {}; checksum: {};" \
            .format(self.flag, self.seq, self.checksum)

    def to_bytesformat(self):
        seq = format(self.seq, '032b')
        ack = format(self.ack, '032b')
        flag = format(self.FLAG_TYPE[self.flag], '08b')
        empty = Segmen.ret_empty()
        checksum = format(self.checksum, '016b')
        rest_1 = int((seq + ack), 2).to_bytes(8, 'big')
        rest_2 = int((flag + empty + checksum), 2).to_bytes(4, 'big')
        segmen = rest_1 + rest_2
        segmen = bytearray(segmen)
        if self.data:
            segmen += self.data
        return segmen
    
    def gen_checksum(self):
        seq = format(self.seq, '032b')
        ack = format(self.ack, '032b')
        flag = format(self.FLAG_TYPE[self.flag], '08b')
        empty = self.empty
        segmen = int((seq + ack + flag + empty), 2).to_bytes(10, 'big')
        # print(segmen) # TEST
        segmen = bytearray(segmen)
        if self.data:
            segmen += self.data
        
        if (len(segmen) % 2) == 1:
            segmen += int(0).to_bytes(1, 'big')

        check_s = 0
        
        for i in range(len(segmen) // 2):
            add_1 = int.from_bytes(segmen[(i*2):(i*2+2)], 'big')
            check_s = Segmen.add16(check_s, add_1)
        
        return (check_s ^ 65535) # One's Complement
    
    def check_checksum(self):
        return (self.gen_checksum() == self.checksum)
    
    @staticmethod
    def add16(bin_1, bin_2):
        MOD = 1 << 16
        result = bin_1 + bin_2
        return result if result < MOD else (result + 1) % MOD

    @staticmethod
    def construct_segmen(data):
        seq = int.from_bytes(data[0:4], 'big')
        ack = int.from_bytes(data[4:8], 'big')
        flag = Segmen.TYPE_FLAG[int.from_bytes(data[8:9], 'big')]
        empty = int.from_bytes(data[9:10], 'big')
        checksum = int.from_bytes(data[10:12], 'big')
        _data = None
        if (flag == "DATA"):
            _data = data[12:] # Bytearray?
        # print(seq, ack, flag, empty, checksum, _data) # TEST
        return Segmen(seq, ack, flag, checksum, _data, empty)
    
    @staticmethod
    def ret_empty():
        return format(0, '08b')
    
if __name__ == "__main__":
    seg = Segmen(1, 1, 'DATA', data=bytes('asdflkjasdflkafsjd', 'utf-8'))
    print(seg.to_bytesformat())

    chk = seg.gen_checksum()
    print(chk)
    print(int(format(chk, '016b'), 2).to_bytes(2, 'big'))
    print(seg.check_checksum())