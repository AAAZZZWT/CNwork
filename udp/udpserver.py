from socket import *
import random
import datetime as dt


secondFlag = False #判断第二次握手是否完成
thirdFlag = False #判断第三次握手是否完成
fromClientSeq = 0
class MessageForm(object):
    '''
    定义报文类，规定其格式为：
    seqNo：2字节，Ver：1字节，srcPort:2字节，desPort:2字节，len：2字节，
    checkSum:2字节；flag：1字节，time:18字节，data:173字节
    '''

    # 构造函数，参数分别为：序列号，
    def __init__(self, seqno, data, ACK, SYN, FIN, time):
        self.seqNo = seqno.to_bytes(2, "little", signed=True)  # 序列号 2 bytes
        self.Ver = bytes([2])  # 版本号 1 bytes
        self.srcPort = int.to_bytes(12000, 2, "little", signed=True)  # 源端口 2 bytes
        self.desPort = serverPort.to_bytes(2, "little", signed=True)  # 目的端口 2 bytes
        self.len = int.to_bytes(8, 2, "little", signed=True)  # 长度 2 bytes
        self.checkSum = bytes([0, 0])  # 校验和 2 bytes
        self.flagSet = 0
        self.flagSet = setFlagElem(self.flagSet, 4, ACK)
        self.flagSet = setFlagElem(self.flagSet, 2, SYN)
        self.flagSet = setFlagElem(self.flagSet, 0, FIN)
        self.Flag = int.to_bytes(self.flagSet, 1, "little", signed=True)  # 标志位1位
        self.timeNow = time.encode('utf-8').zfill(18)  # 系统时间 18 bytes
        self.data = data.encode('utf-8').zfill(173)# 数据 173 bytes

    def splice(self):  # 将各个参数拼接为报文
        return ( self.seqNo + self.Ver + self.srcPort + self.desPort + self.len + self.checkSum + self.Flag + self.timeNow + self.data)

    def getFlags(self):  # 获取该报文的Flag字段
        intFlag = int.from_bytes(self.Flag, "little", signed=True)
        return [getFlagElem(intFlag, 4), getFlagElem(intFlag, 2), getFlagElem(intFlag, 0)]



def decodeMessage( bytes_str):#解封装
    seqNo = int.from_bytes(bytes_str[0:2], "little", signed=True)
    Ver = int.from_bytes(bytes_str[2:3], "little", signed=True)
    srcPort = int.from_bytes(bytes_str[3:5], "little", signed=True)
    desPort = int.from_bytes(bytes_str[5:7], "little", signed=True)
    len = int.from_bytes(bytes_str[7:9], "little", signed=True)
    checkSum = int.from_bytes(bytes_str[9:11], "little", signed=True)
    Flag = int.from_bytes(bytes_str[11:12], "little", signed=True)
    timeNow = bytes_str[12:30].decode(encoding="utf-8")
    data = bytes_str[30:203].decode(encoding="utf-8")
    Message = MessageForm(seqNo, data, getFlagElem(Flag, 4), getFlagElem(Flag, 2), getFlagElem(Flag, 0), timeNow)
    return Message


def getFlagElem(flag, i):
    # 得到flag中第i位的值(ACK/SYN/FIN)
    return (flag >> i) & 1
def setFlagElem(flag, i, temp):
    #修改flag中第i位的值为temp
    if temp:
        return flag | (1 << i)
    else:
        return flag & ~(1 << i)

def secondShake():#第二次握手，发送给client相应的报文
    second = MessageForm(0, "第二次握手", 1, 1, 0, dt.datetime.now().strftime("%H:%M:%S.%f"))
    serverSocket.sendto(second.splice(), clientAddress)


def thirdShake():#第三次握手，发送给client相应的报文以及对数据包的回复
    if fromClient.data.decode(encoding="utf-8").find("third handshake") != -1:
        print("成功完成三次握手")
    else:# 根据random来决定收到的报文是回复数据包，以完成对丢包的模拟
        rand = random.randint(1, 20)
        if rand <= 15:  # 丢包率为25%
            toClient = MessageForm(fromClientSeq, ("第" + str(fromClientSeq))+"个数据包", 1, 0, 0,dt.datetime.now().strftime("%H:%M:%S.%f"), )
            # 发送回client，代表该包未丢失
            serverSocket.sendto(toClient.splice(), clientAddress)
            print("已完成第" + str(fromClientSeq)+"个数据包！")
        else:  # 丢包，不回复给Client
            print("第" + str(fromClientSeq)+"个数据包丢包！")
            pass
def allWave():
    secondthirdSeq = 17
    # 第二次挥手，发送给Client
    secondWave = MessageForm(secondthirdSeq, "第二次挥手", 1, 0, 0, dt.datetime.now().strftime("%H-%M-%S.%f"))
    serverSocket.sendto(secondWave.splice(), clientAddress)
    # 第三次挥手，发送给Client
    thirdWave = MessageForm(secondthirdSeq+1, "第三次挥手", 0, 0, 1, dt.datetime.now().strftime("%H-%M-%S.%f"))
    serverSocket.sendto(thirdWave.splice(), clientAddress)


if __name__ == "__main__":
    serverPort = 12000 # 初始化服务器端口号 serverPort 为 12000,创建数据报套接字
    serverSocket = socket(AF_INET, SOCK_DGRAM)
    serverSocket.bind(('', serverPort)) # ''表示绑定到本地所有可用的网络接口
    print("服务器启动完成！")

    while True:
        try:
            # 接收数据并解码
            clientMessage, clientAddress = serverSocket.recvfrom(2048)
            fromClient = decodeMessage(clientMessage)
            fromClientSeq = int.from_bytes(fromClient.seqNo, "little", signed=True)
            # 接收client发送来的数据包
            Flag = fromClient.getFlags()
            if Flag[0] == 0 and Flag[1] == 1 and Flag[2] == 0 and fromClientSeq == 0:
                # 发送第二次握手,seq初始化为0
                secondShake()
                secondFlag = True

            # 完成挥手操作
            elif Flag[0] == 0 and Flag[1] == 0 and Flag[2] == 1 and fromClientSeq != 19:
                allWave()

            elif fromClientSeq == 19:
                print("完成四次挥手！")

            # 接收第三次握手后选择是否回复数据包，模拟丢包现象
            elif (secondFlag and Flag[0] == 1 and Flag[1] == 0 and Flag[2] == 0 and fromClientSeq == 1) or thirdFlag:
                thirdFlag = True #完成了第三次握手
                thirdShake()

        except:
            pass
