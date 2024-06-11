from socket import *
import queue as q
import select
import time

serverPort = 12000
readableList = []
writableList = []
messageList = {}


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
        return Type
    elif Type == 1:
        return Type
    elif Type == 2:
        Length = int.from_bytes(messageString[2:6], "little", signed=True)
        Data =messageString[6:].decode(encoding="ascii")
        return Data
    elif Type == 3:
        Length = int.from_bytes(messageString[2:6], "little", signed=True)
        afterData =messageString[6:].decode(encoding="ascii")
        return afterData


def writeMessage(i):
    tempSendMessage = messageList.get(i)  #获取data
    if tempSendMessage:
        clientMessage = DecodeMessage(tempSendMessage.get_nowait())
        if clientMessage == 0:  # 说明接收到的是Initialization类型的报文,则发送agreement报文
            # 发送agreement报文
            agreMessage = Agreement(1)
            i.send(agreMessage.Splice())
        # 接收reverseRequest报文
        else:  # 接收到的是ReverseRequest报文
            ansData = ""
            for char in clientMessage:  #对字符串的逆转
                ansData = char + ansData
            ansMessage = ReverseAnswer(3, len(ansData), ansData)  # 把操作后的字符串当做报文中的数据发送到client端
            i.send(ansMessage.Splice())


def readMessage(i, serverSocket):
    if i is serverSocket:  # 当有新的客户端连接时，会执行这部分代码，接受新的客户端连接，并将新的客户端加入到 readableList 中，并为其创建一个消息队列。
        clientSocket, clientAddress = serverSocket.accept()
        clientSocket.setblocking(False)  # 非阻塞
        messageList[clientSocket] = q.Queue()   # 加入到这个client要发送的消息队列
        readableList.append(clientSocket)
    else:
        tempData = i.recv(2048)
        if tempData:  # 从客户端接收数据，如果接收到数据，则将数据放入消息队列中，并将该客户端加入到输出列表中，以便后续向该客户端发送消息。
            if i not in writableList:
                writableList.append(i)
            tempDecodeData = DecodeMessage(tempData)
            if tempDecodeData != 0:
                print(f'{i.getpeername()}: {tempDecodeData}')  # 注明该消息是从何而来，以便区分多个客户端
            messageList[i].put(tempData)
        else:  # 客户端断开连接
            if (i in readableList):  #移除
                readableList.remove(i)
            if (i in writableList):
                writableList.remove(i)
            i.close()  #关闭
            messageList.pop(i, None)



if __name__ == "__main__":
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('', serverPort))  # ''表示绑定到本地所有可用的网络接口
    serverSocket.setblocking(False)  # 设置为非阻塞
    serverSocket.listen(10)  #最大等待数量为10
    print("server已开启！")
    readableList.append(serverSocket)
    while readableList:
        r, w, ex = select.select(readableList, writableList, readableList)  #用select方式
        for i in r:# 向内有连接时
            try:
                readMessage(i, serverSocket)
            except:
                pass
        for j in w: # 向外发数据时
            try:
                writeMessage(j)
            except:
                pass
        for k in ex:  # 有异常，则关闭s
            if(k in readableList):  # 存在则移除
                readableList.remove(k)
            if(k in writableList):
                writableList.remove(k)
            k.close()
        #time.sleep(0.5)  #该语句减缓运行时间，可用于测试“同时处理多个client来发数据”

