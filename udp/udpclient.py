from socket import *
import datetime as dt
import numpy as np
import time
import math
import sys

#定义全局变量
sendCount = 0 #发送的数据包的数目
recieveCount = 0 #接收到的数据包的数目
lostCount = 0 #放弃传输的包数目
sendTime = np.zeros(12) #一个大小为12的数组用来记录12个数据包的发送时间，初始设置为0
RTT = np.zeros(12)#记录12个数据包的RTT
lostFlag = np.ones(12) #记录12个数据包每个的丢包情况，初始设置为1
allTime = 0 #系统总共响应时间

class MessageForm(object):
    '''
    定义报文类，规定其格式为：
    seqNo：2字节，Ver：1字节，srcPort:2字节，desPort:2字节，len：2字节，
    checkSum:2字节；flag：1字节，time:18字节，data:173字节
    '''
    # 构造函数
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

    def splice(self):#将各个参数拼接为报文
        return (self.seqNo + self.Ver + self.srcPort + self.desPort + self.len + self.checkSum+ self.Flag + self.timeNow + self.data)

    def getFlags(self):#获取该报文的Flag字段
        intFlag = int.from_bytes(self.Flag, "little", signed=True)
        return [getFlagElem(intFlag, 4), getFlagElem(intFlag, 2), getFlagElem(intFlag, 0)]



def decodeMessage( bytes_str):#解封装，返回一个MessageForm对象
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

def matchStr(substr, string, count):
    # substr:子串，str：主串，i：子串在主串中出现的次数，返回的是总匹配的次数
    index = string.find(substr)
    if index == -1 or count == 0:
        return 0
    return index + matchStr(substr, string[index + 1:], count - 1) + 1
    # 递归调用时，会将主串切片从当前子串的下一个位置开始，然后继续寻找下一个匹配位置。递归的结束条件是计数器为 0 或者找不到匹配的子串位置，返回已经累计的匹配位置索引。

def connect():#模拟TCP的连接建立过程：三次握手
    try:
        clientSocket.settimeout(0.1)#设置超时时间为100ms
        # 第一次握手：客户端发送一个带有 SYN=1、ACK=0 的数据包到服务器，表示主动发起连接请求。同时设置序列号（seq_no）为初始值 0。
        first = MessageForm(0,"first hand shake",0,1,0,dt.datetime.now().strftime("%H:%M:%S.%f"))
        clientSocket.sendto(first.splice(),(serverIP, serverPort))
        # 接收第二次握手,客户端通过 clientSocket.recvfrom(2048) 接收服务器返回的数据包，然后解析其中的标志位和序列号等信息。
        serverMessage, serverAddress = clientSocket.recvfrom(2048)
        second = decodeMessage(serverMessage)
        secondSeq= int.from_bytes(second.seqNo,"little",signed=True)
        Flag = second.getFlags()
        if Flag[0] == 1 and Flag[1] == 1 and Flag[2] == 0 and secondSeq== 0:
            # 第二次握手确认：客户端根据接收到的第二次握手数据包，验证其中的标志位和序列号是否符合预期，如果符合则发送第三次握手数据包到服务器。
            # 如果符合预期，则进行第三次握手
            third = MessageForm(secondSeq+1,"third handshake",1,0,0,dt.datetime.now().strftime("%H:%M:%S.%f"))
            clientSocket.sendto(third.splice(),(serverIP,serverPort))
            print("三次握手连接成功！")
    except:
        print("三次握手连接失败!")


def close():#模拟TCP连接释放：四次挥手
    try:
        clientSocket.settimeout(0.1)#超时时间为100ms
        # 第一次挥手,seq no随机赋值16
        firstWaveSeq = 16
        # 构造第一次挥手的数据包（Message），设置 FIN 标志位为 1，表示客户端希望关闭连接。将该数据包发送给服务器。
        firstWave = MessageForm(firstWaveSeq,"第一次挥手",0,0,1,dt.datetime.now().strftime("%H:%M:%S.%f"))
        clientSocket.sendto(firstWave.splice(),(serverIP,serverPort))
        # 接收来自服务器的第二次挥手，检查收到的数据包是否符合预期：ACK 标志位为 1，表示确认收到客户端的 FIN 请求，并且序列号与客户端发送的序列号相匹配。
        serverMessage, serverAddress = clientSocket.recvfrom(2048)
        secondWave = decodeMessage(serverMessage)
        secondWaveSeq= int.from_bytes(secondWave.seqNo,"little",signed=True)
        Flag = secondWave.getFlags()
        if Flag[0] == 1 and Flag[1] == 0 and Flag[2] == 0 and secondWaveSeq== 17:
            # 如果第二次挥手符合预期，则继续接收来自服务器的第三次挥手，检查其是否符合预期：FIN 标志位为 1，表示服务器也希望关闭连接。
            # 接收来自server的第三次挥手
            thirdMessage, thirdAddress = clientSocket.recvfrom(2048)
            thirdWave = decodeMessage(thirdMessage)
            thirdWaveFlag = thirdWave.getFlags()
            thirdWaveSeq = int.from_bytes(thirdWave.seqNo,"little",signed=True)
            if thirdWaveFlag[0] == 0 and thirdWaveFlag[1] == 0 and thirdWaveFlag[2] == 1 and thirdWaveSeq== 18:
                # 如果第三次挥手符合预期，则客户端发送第四次挥手，表示确认服务器的关闭请求，并关闭连接。
                # 第四次挥手
                forthWave = MessageForm(19, "第四次挥手",1,0,0,dt.datetime.now().strftime("%H:%M:%S.%f"))
                clientSocket.sendto(forthWave.splice(),(serverIP,serverPort))
                print("四次挥手完成！Client端关闭！")
    except:
        print("四次挥手失败！")

if __name__ == "__main__":
    # 命令行输入
    serverIP = sys.argv[1]
    serverPort = int(sys.argv[2])
    # 创建UDP套接字
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    # 设置超时时间为100ms
    clientSocket.settimeout(0.1)
    try:
        # 模拟TCP连接建立，三次握手
        connect()
        #连接成功之后，发送12个数据包
        for i in range(12):
            # 标记是否丢包
            retransCount = 0
            for j in range(3):  #一共发三次，第一次是正常发出，后两次是重传
                try:
                    clientSocket.settimeout(0.1)  # 设置超时时间为100ms
                    Message = MessageForm((i + 1), "第" + str(i + 1) + "个数据包", 1, 0, 0,
                                        dt.datetime.now().strftime("%H:%M:%S.%f"))
                    clientSocket.sendto(Message.splice(), (serverIP, serverPort))
                    sendCount = sendCount + 1  # 发送出的数目加一
                    sendTime[i] = time.time()  # 发送的时间，计入数组
                    serverMessage, serverAddress = clientSocket.recvfrom(2048)
                    recieveCount = recieveCount + 1  # 接收到的数目+1
                    receiveMessage = decodeMessage(serverMessage)
                    receiveTime = receiveMessage.timeNow.decode(encoding="utf-8")#server发来回复的时间
                    if recieveCount == 1:
                        iniReceiveTime = receiveTime
                    # 整体响应时间
                    allTime = (float)((int(receiveTime[receiveTime.find(".") + 1:]) - int(
                        iniReceiveTime[iniReceiveTime.find(".") + 1:])) / 1000)
                    if allTime < 0:#丢包时
                        allTime = allTime +  (int(receiveTime[matchStr(":", receiveTime, 2) + 1:receiveTime.find(".")]) - int(
                            iniReceiveTime[matchStr(":", iniReceiveTime, 2) + 1:iniReceiveTime.find(".")]))*1000  # 使单位变为ms
                    RTT[i] = (time.time() - sendTime[i]) * 1000  # 记录该数据包的RTT
                    # 打印接收到的报文的信息
                    receiveSeq = int.from_bytes(receiveMessage.seqNo, "little", signed=True)
                    print("sequence no:", receiveSeq, "、serverIP:", serverIP, "、serverPort:", serverPort, "、RTT:",
                          RTT[i], "(ms)")
                    break #正常收到了server的相应则会执行到该语句，跳出本次循环

                except:
                    # 超时，打印出该数据包超时的信息
                    print("sequence no:", i + 1, "request time out")
                    retransCount = retransCount + 1
            if retransCount == 3:  # 重传了三次则丢包
                lostFlag[i] = 0  # 丢包标记
                lostCount = lostCount + 1


        # 模拟TCP连接释放四次挥手
        close()
        clientSocket.close()
    except:
        pass
    finally:
        #计算结果
        lostRate = 1.0 - (float)(recieveCount / sendCount)
        sumRTT=sum(RTT)
        avgRTT = (float)(sumRTT / (recieveCount - lostCount))
        varRTT = 0.0
        for i in range(recieveCount):
            if RTT[i] != 0 or lostFlag[i] != 0:
                varRTT = varRTT + (RTT[i] - avgRTT) ** 2
            else:
                continue
        staRTT = math.sqrt(varRTT / (recieveCount - lostCount))
        print("汇总信息:")  # 打印结果
        print("发送输出的upd Messages数目为：", sendCount, "，接收到的udp Messages数目为：", recieveCount, "，丢包率为：",
              '%.2f' % (lostRate * 100), "%")
        print("最大RTT为：", '%.2f' % max(RTT), "，最小RTT为：", '%.2f' % min(RTT), "，平均RTT为：", '%.2f' % avgRTT,
              "，RTT的标准差为：", '%.2f' % staRTT, "，server的整体相应时间为：", '%.1f' % allTime, "ms")