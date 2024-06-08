from socket import *
import sys
import random as rd

N = 0 #用于记录分割后数组的大小
beforeData = []  # 逆转之前的字符串集合，用来分块
afterData = []  # 逆转之后的字符串集合，用来打印
beforePath = r'before.txt'  # 存放要逆转字符串的文件的路径
afterPath = r'after.txt'   # 存放逆转后字符串的文件的路径
class Initialization(object):
    # Initialization类
    def __init__(self, type, N):
        self.Type = type.to_bytes(2, "little", signed=True)  # Type:2 Bytes
        self.N = N.to_bytes(4, "little", signed=True)  # N:4 Bytes

    def Splice(self):  # 把Initialization类对象的各个参数(Type和N)拼接在一起
        return self.Type + self.N


class Agreement(object):
    #Agreement类
    def __init__(self, type):
        self.Type = type.to_bytes(2, "little", signed=True)  # Type:2 Bytes

    def Splice(self):  # 把Agreement类对象的各个参数(只有Type)拼接在一起
        return self.Type


class ReverseRequest(object):
    # ReverseRequest类
    def __init__(self, type, len , beforedata):
        self.Type = type.to_bytes(2, "little", signed=True)  # Type:2 Bytes
        self.Length = len.to_bytes(4, "little", signed=True)  # Length:4 Bytes
        self.beforeData = bytes(beforedata, encoding="ascii")  # Data:长度未设定

    def Splice(self):  # 把ReverseRequest类对象的各个参数(Type,Length,Data)拼接在一起
        return self.Type + self.Length + self.beforeData


class ReverseAnswer(object):
    # ReverseAnswer类
    def __init__(self, type, len, afterdata):
        self.Type = type.to_bytes(2, "little", signed=True)  # Type:2 Bytes
        self.Length = len.to_bytes( 4, "little", signed=True)  # Length:4 Bytes
        self.afterData = bytes(afterdata, encoding="ascii")

    def Splice(self):  # 把ReverseAnswer类对象的各个参数(Type,Length,beforeData)拼接在一起
        return self.Type + self.Length + self.afterData



def DecodeMessage(messageString):
    Type = int.from_bytes(messageString[0:2], "little", signed=True)
    if Type == 0:
        N = int.from_bytes(messageString[2:6], "little", signed=True)
        return [Type, N]
    if Type == 1:
        return [Type,]
    if Type == 2:
        Length = int.from_bytes(messageString[2:6], "little", signed=True)
        Data =messageString[6:].decode(encoding="ascii")
        return [Type,Length,Data]
    if Type == 3:
        Length = int.from_bytes(messageString[2:6], "little", signed=True)
        afterData =messageString[6:].decode(encoding="ascii")
        return [Type,Length,afterData]

def start():
    try:
        # 向server发送initialization报文
        iniMessage = Initialization(0, N)
        clientSocket.send(iniMessage.Splice())
        # 接收从server发来的agreement报文
        agreMessage = clientSocket.recv(2048)
        decodeAgreement = DecodeMessage(agreMessage)
        if decodeAgreement[0] == 1:  # 判断收到agreement的报文是否正确
            # 将beforeData的内容发出去
            for i in range(N):
                tempLen = len(afterData[i])
                revMessage = ReverseRequest(2, tempLen, afterData[i])
                clientSocket.send(revMessage.Splice())
                # 接收reverseAnswer
                try:
                    ansMessage = clientSocket.recv(2048)
                    ans = DecodeMessage(ansMessage)
                    beforeData.append(ans[2])
                    print(i + 1, "：", ans[2])
                except:
                    print("接收逆转报文失败！")
        else:
            print("接收agreement报文失败！")
    except:
        print("收发错误！")

if __name__ == "__main__":
    # 命令行输入server的IP、端口号、Lmin和Lmax
    serverIP = sys.argv[1]
    serverPort = int(sys.argv[2])
    Lmin = int(sys.argv[3])
    Lmax = int(sys.argv[4])
    # 创建TCP连接
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverIP, serverPort))
    try:
        # 读取文件内容并分块
        file = open(beforePath, 'r')
        content = file.read()
        while len(content) >= Lmin:
            contentLen = len(content)
            lenOfData = rd.randint(Lmin, min(Lmax, contentLen))  # 随机生成长度
            tempData = content[:lenOfData]  #切割
            afterData.append(tempData)  # 放到数组中
            tempContent = content[lenOfData:]
            content = tempContent  # 更新数据
        if content:
            afterData.append(content)
        N = len(afterData)  # 分割后的原数据大小
        file.close()
        start()
    except:
        print("分割reverse错误！")
    finally:
        beforeData = beforeData[::-1]  # 不仅每个分割块内部要倒转，所有的分割块也要倒转
        with open(afterPath, 'w') as afterFile:
            for i in beforeData:
                afterFile.write(i)
        afterFile.close()
        clientSocket.close()


