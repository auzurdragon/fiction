# -*- coding:utf8 -*-
"""
    抓取和管理小说, 以.txt文件保存
    来源网站：
    1、新笔趣阁 https://www.xbiquge6.com
"""
import requests,threading,logging,os,json,sys
from bs4 import BeautifulSoup as bs
from time import localtime,strftime,time,sleep
from queue import Queue,PriorityQueue

logging.basicConfig(level=logging.DEBUG)

url_list = [
    {'name':'新笔趣阁', 'url':'https://www.xbiquge6.com'},
]

class fiction(object):
    def __init__(self, name):
        self.save_dir = 'fiction'
        self.fiction = {
            'name':name,
            'author':'',
            'source':'',
            'num':0,
            'last_chapter':'',
            'update':int(0),
            'desc':''
        }
        self.catalog = []
        self.content = PriorityQueue()
        if self.save_dir not in os.listdir():
            logging.info('no save_dir, mkdir')
            os.mkdir(self.save_dir)
    def save(self):
        """
            保存到文本文件
        """
        with open(u'%s/%s.txt' % (self.save_dir, self.fiction['name']), 'w+', encoding='utf8') as f:
            f.writelines([json.dumps(self.fiction)])
        with open(u'%s/%s.txt' % (self.save_dir, self.fiction['name']), 'a+', encoding='utf-8') as f:
            while not self.content.empty():
                ind, name, content = self.content.get()
                f.write('\n\n' + name)
                f.write('\n' + content)
    def check_dir(self):
        """
            检查小说是否已经抓取过, 并获得历史信息
        """
        if '%s.txt' % self.fiction['name'] in os.listdir(self.save_dir):
            with open(u'%s/%s.txt' % (self.save_dir,self.fiction['name']), 'r', encoding='utf8') as r:
                tmp = json.loads(r.readlines()[0].strip())
            self.fiction = dict(self.fiction, **tmp)
            return True
        else:
            logging.info('%s not in save_dir' % self.fiction['name'])
            return False
    def find_source(self):
        """
            在网站上查找目录页面地址
        """
        url = 'https://www.xbiquge6.com/search.php?keyword=%s' % self.fiction['name']
        try:
            tmp = requests.get(url)
            if tmp.ok:
                tmp = bs(tmp.content, features='html5lib')
                tmp = tmp.body.find('div', class_='result-list').find_all('div', class_='result-item result-game-item')
                if tmp:
                    flist = []
                    for i in tmp:
                        name = i.find('a', class_='result-game-item-title-link')
                        desc = ''.join(i.find('p', class_='result-game-item-desc').text.split())
                        info = i.find_all('p', class_='result-game-item-info-tag')
                        flist.append({
                            'name':name['title'],
                            'source':name['href'].replace('http://', 'https://'),
                            'author':info[0].find_all('span')[1].text.strip(),
                            'last_chapter':info[-1].find('a').text.strip(),
                            'desc':desc,
                        })
                    if len(flist) == 1:
                        ind = 0
                    else:
                        for i in flist:
                            print('%d , 名称:%s , 作者:%s , 末尾:%s , 简介:%s' % (flist.index(i), i['name'], i['author'], i['last_chapter'], i['desc']))
                        ind = int(input('Please select fiction id :'))
                    self.fiction = dict(self.fiction, **flist[ind])
                    for i in self.fiction.keys():
                        print('%s:%s' % (i, self.fiction[i]))
                else:
                    logging.warning('get_source, pd.body.find_all failed')
            else:
                logging.warning('get_source, requests.get.ok is False')
        except Exception as E:
            logging.error('get_source, requests.get, %s' % E)
            return False
    def get_source(self):
        """
            查找目录链接
        """
        if self.check_dir():
            pass
        else:
            self.find_source()
    def get_catalog(self):
        if self.fiction['source'] == '':
            logging.info('get_catagory : source url is null')
            return False
        try:
            tmp = requests.get(self.fiction['source'])
            tmp = bs(tmp.content, features='html5lib').find_all('div', class_='box_con')[1]
            tmp = tmp.find_all('a')
            self.catalog = [{'ind':tmp.index(i), 'name':i.text, 'url':'https://www.xbiquge6.com%s' % i.get('href')} for i in tmp]
            if self.check_dir():
                ind = len(self.catalog)-1
                while ind >=0 :
                    if self.catalog[ind]['name'] == self.fiction['last_chatper']:
                        self.catalog = self.catalog[ind:]
                        break
                    ind -= 1
            logging.info('get_catalog, %s, last chapter %s, %d chapter waiting for get' % (self.fiction['name'], self.fiction['last_chapter'], len(self.catalog)))
            return True
        except Exception as E:
            logging.error('get_catalog failed, %s' % E)
            return False
    def get_chapter(self, chapter):
        """
            抓取单章节，保存入队列
        """
        try:
            tmp = requests.get(chapter['url'])
            tmp = bs(tmp.content, features='html5lib')
            chapter['content'] = tmp.body.find('div', id='content').text.replace(u'\xa0\xa0\xa0\xa0', '\n')
            self.content.put((chapter['ind'], chapter['name'], chapter['content']))
            return True
        except Exception as E:
            logging.error('get_chapter failed, %s' % E)
            return False
    def get_chapter_all(self):
        """
            获取 self.catalog 中的所有链接
        """
        while self.content.qsize() < len(self.catalog):
            get_list = []
            for i in self.catalog:
                get_list.append(threading.Thread(target=self.get_chapter, args=(i,)))
            for i in get_list:
                i.start()
            for i in get_list:
                i.join()
        self.fiction['num'] += len(self.catalog)
        self.fiction['last_chapter'] = self.catalog[-1]['name']
        self.fiction['update'] = str(int(time()))
        logging.info('get_chapter_all %s complete' % self.fiction['name'])
    def get_fiction(self):
        try:
            self.get_source()
            self.get_catalog()
            self.get_chapter_all()
            self.save()
        except Exception as E:
            logging.error(E)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        name = input('请输入小说名称:')
        t = fiction(name)
        t.get_fiction()
    else:
        flist = sys.argv[1:]
        for name in flist:
            print(name)
            t = fiction(name)
            t.get_fiction()
    