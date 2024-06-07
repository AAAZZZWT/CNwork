from socket import *
import queue as q
import select
import time

serverIP = '192.168.41.128'
serverPort = 12000
readableList = []
writableList = []
messageList = {}


class Initialization(object):
    def __init__(self, type, N):
        self.Type = int.to_bytes(type, 2, "little", signed=True)  # Type：2 Bytes
        self.N = int.to_bytes(N, 4, "little", signed=True)  # N：4 Bytes

    def splice(self):
        return self.Type + self.N


class Agreement(object):
    def __init__(self, type):
        self.Type = int.to_bytes(type, 2, "little", signed=True)  # Type：2 Bytes

    def splice(self):
        return self.Type


class ReverseRequest(object):
    def __init__(self, type, Length, Data):
        self.Type = int.to_bytes(type, 2, "little", signed=True)  # Type：2 Bytes
        self.Length = int.to_bytes(Length, 4, "little", signed=True)  # Length：4 Bytes
        self.Data = bytes(Data, encoding="ascii")  # data长度可变

    def splice(self):
        return self.Type + self.Length + self.Data


class ReverseAnswer(object):
    def __init__(self, type, Length, ReverseData):
        self.Type = int.to_bytes(type, 2, "little", signed=True)  # Type：2 Bytes
        self.Length = int.to_bytes(Length, 4, "little", signed=True)  # Length：4 Bytes
        self.ReverseData = bytes(ReverseData, encoding="ascii")  # ReverseData 长度可变

    def splice(self):
        return self.Type + self.Length + self.ReverseData



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
        reverseData =messageString[6:].decode(encoding="ascii")
        return reverseData


def writeMessage(i):
     # 获取消息队列中要发送的消息
    tempSendMessage = messageList.get(i)
    if tempSendMessage:
        clientMessage = DecodeMessage(tempSendMessage.get_nowait())
        if clientMessage == 0:  # 说明接收到的是Initialization类型的报文,则发送agreement报文
            # 发送agreement报文
            agreMessage = Agreement(1)
            i.send(agreMessage.splice())
        # 接收reverseRequest报文
        if isinstance(clientMessage, str):  # 接收到的是一个字符串，说明是ReverseRequest报文
            ansData = ""
            for char in clientMessage:  #对字符串的逆转
                ansData = char + ansData
            ansMessage = ReverseAnswer(3, len(ansData), ansData)  # 把操作后的字符串当做报文中的数据发送到client端
            i.send(ansMessage.splice())


def readMessage(i, serverSocket):
    if i is serverSocket:  # 当有新的客户端连接时，会执行这部分代码，接受新的客户端连接，并将新的客户端加入到 readableList 中，并为其创建一个消息队列。
        clientSocket, clientAddress = serverSocket.accept()
        clientSocket.setblocking(False)
        readableList.append(clientSocket)
        messageList[clientSocket] = q.Queue()
    else:
        tempData = i.recv(2048)
        if tempData:  # 从客户端接收数据，如果接收到数据，则将数据放入消息队列中，并将该客户端加入到输出列表中，以便后续向该客户端发送消息。
            if i not in writableList:
                writableList.append(i)
            tempDecodeData = DecodeMessage(tempData)
            if tempDecodeData != 0:
                print(f'{i.getpeername()}: {tempDecodeData}')  # 注明该消息是从何而来，以便区分多个客户端
            messageList[i].put(tempData)
        # client端断开连接
        else:  # 客户端断开连接
            if (i in readableList):  #移除
                readableList.remove(i)
            if (i in writableList):
                writableList.remove(i)
            i.close()  #关闭
            messageList.pop(i, None)



if __name__ == "__main__":
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind((serverIP, serverPort))
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
        time.sleep(0.5)  #该语句减缓运行时间，可用于测试“同时处理多个client来发数据”

