# _*_ coding:utf-8 _*_


import requests
# 线程库
import threading
# 解析库
from lxml import etree
# 队列
from queue import Queue
import time
import json

# 采集线程退出标志
GATHER_EXIT = False
# 解析线程退出标志
PARSE_EXIT = False


class ThreadGather(threading.Thread):
    """数据采集类"""

    def __init__(self, threadName, pageQueue, dataQueue):
        super(ThreadGather, self).__init__()
        # 线程名
        self.threadName = threadName
        # 页码队列
        self.pageQueue = pageQueue
        # 数据队列
        self.dataQueue = dataQueue
        # 请求报头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'}

    def run(self):
        print(self.threadName + '启动')
        while not GATHER_EXIT:
            try:
                # get参数为false时，如果队列为空，就弹出一个Queue.empty()的异常
                # get参数为true时，如果队列为空，不会结束，会进入阻塞状态，直到队列有新的数据
                page = self.pageQueue.get(False)
                url = 'http://www.qiushibaike.com/text/page/' + str(page) + '/'
                content = requests.get(url, headers=self.headers).text

                self.dataQueue.put(content)
                print(len(content))
            except:
                pass
        print(self.threadName + '结束')


class ThreadParse(threading.Thread):
    """数据解析类"""

    def __init__(self, threadName, dataQueue, fileName, lock):
        super(ThreadParse, self).__init__()
        # 线程名
        self.threadName = threadName
        # 保存解析后数据的文件名
        self.fileName = fileName
        # 数据队列
        self.dataQueue = dataQueue
        # 锁
        self.lock = lock

    def run(self):
        print(self.threadName + '启动')
        while not PARSE_EXIT:
            try:
                html = self.dataQueue.get(False)
                self.parse(html)
            except Exception as e:
                pass
        print(self.threadName + '结束')

    def parse(self, html):
        # 解析为HTML DOM
        html = etree.HTML(html)
        # 段子node列表集合
        node_list = html.xpath("//div[contains(@id,'qiushi_tag')]")

        for node in node_list:
            # 取出每个节点的用户名
            username = node.xpath('./div/a/h2')[0].text
            # 段子内容
            content = node.xpath(".//div[@class='content']/span")[0].text
            # 点赞数量
            praise = node.xpath('.//i')[0].text
            # 评论数量
            comments = node.xpath('.//i')[1].text

            items = {
                'username': username.replace('\n', ''),
                'content': content.replace('\n', ''),
                'praise': praise.replace('\n', ''),
                'comments': comments.replace('\n', '')
            }

            # 获取锁，处理完内容后,释放锁
            with self.lock:
                print(items)
                self.fileName.write(json.dumps(items, ensure_ascii=False).encode('utf-8'))


def main():
    # 页码的队列 队列的大小为20
    pageQueue = Queue(20)
    # 放入1-20的页面数字，先进先出
    for i in range(1, 21):
        pageQueue.put(i)

    # 采集结果（每页的HTML源码）的数据队列，参数为空表示不限制
    dataQueue = Queue()

    # a 表示往文件里面追加内容
    filename = open('duanzi.json', 'ab')
    # 创建锁
    lock = threading.Lock()

    # 采集线程的名字
    gatherList = ['采集线程1', '采集线程2', '采集线程3']
    # 存储采集线程的列表集合
    threadGather = []
    for threadName in gatherList:
        thread = ThreadGather(threadName, pageQueue, dataQueue)
        thread.start()
        threadGather.append(thread)

    # 解析线程的名字
    parseList = ['解析线程1', '解析线程2', '解析线程3']
    # 解析采集线程的列表集合
    threadParse = []
    for threadName in parseList:
        thread = ThreadParse(threadName, dataQueue, filename, lock)
        thread.start()
        threadParse.append(thread)

    # 等待pageQueue为空
    while not pageQueue.empty():
        pass

    # 如果pageQueue为空，采集线程退出循环
    global GATHER_EXIT
    GATHER_EXIT = True

    print('pageQueue为空')

    for thread in threadGather:
        thread.join()
        print('1')

    while not dataQueue.empty():
        pass

    print('dataQueue为空')
    # 如果dataQueue为空，解析线程退出循环
    global PARSE_EXIT
    PARSE_EXIT = True

    for thread in threadParse:
        thread.join()
        print('2')

    # 数据解析并写入文件完成后，获取锁，关闭文件
    with lock:
        filename.close()
    print('爬虫结束')


if __name__ == '__main__':
    main()
