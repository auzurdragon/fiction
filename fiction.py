# -*- coding:utf-8 -*-
"""
    小说
"""
import requests,json,os,logging,threading,sys
from bs4 import BeautifulSoup as bs
from time import localtime,strftime,time
from queue import PriorityQueue


# 定义父类
class fiction(object):
    def __init__(self, name=''):
        self.save_dir = 'fiction'
        self.fiction = {
            'name':name if name else '',
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
    def get_url(self, url):
        req = requests.get(url)
        if req.ok:
            soup = bs(req.content, features='html5lib')
            return soup
        else:
            return False
    def save(self):
        """ 保存到文件 """
        # 修改文件顶部信息
        if '%s.txt' % self.fiction['name'] in os.listdir(self.save_dir):
            with open(u'%s/%s.txt' % (self.save_dir, self.fiction['name']), 'r', encoding='utf8') as f:
                tmp = f.readlines()
            tmp[0] = json.dumps(self.fiction) + '\n'
        else:
            tmp = [json.dumps(self.fiction) + '\n',]
        with open(u'%s/%s.txt' % (self.save_dir, self.fiction['name']), 'w', encoding='utf8') as f:
            f.writelines(tmp)
        # 写入章节
        with open(u'%s/%s.txt' % (self.save_dir, self.fiction['name']), 'a+', encoding='utf-8') as f:
            while not self.content.empty():
                ind, name, content = self.content.get()
                f.write('\n\n' + name + '\n')
                f.write('\n' + content + '\n')
    def do_fiction(self, name=''):
        if name:self.__init__(name)
        self.get_source()
        self.get_catalog()
        self.get_chapter_all()
        self.save()
        print('do_fiction %s over' % self.fiction['name'])
    def load(self, name):
        """ 读取文件信息 """
        info = False
        if f'{name}.txt' in os.listdir(self.save_dir):
            with open(u'%s/%s.txt' % (self.save_dir, name), 'r', encoding='utf8') as f:
                info = json.loads(f.readlines()[0])
        else:
            logging.info('%s not in dirv' % name)
        return info
    def find_local(self, name=''):
        """ 打印文件列表 """
        if name:
            if self.load(name):
                self.fiction = self.load(name)
                print(self.fiction)
        else:
            file_list = [i[:-4] for i in os.listdir(self.save_dir)]
            for name in file_list:
                try:
                    info = self.load(name)
                    print(file_list.index(name), info['name'], info['author'], info['num'], info['last_chapter'], sep='\t')
                    print('\t', info['desc'])
                except Exception as Err:
                    logging.info(name, Err)
    def get_source(self, name=''):
        """ 找到主页 """
        pass
    def get_catalog(self):
        """ 提取目录地址 """
        pass
    def get_chapter(self):
        """ 抓取单一章节 """
        pass
    def get_chapter_all(self):
        """ 抓取所有章节 """
        while self.content.qsize() < len(self.catalog):
            get_list = []
            for i in self.catalog:
                get_list.append(threading.Thread(target=self.get_chapter, args=(i,)))
            for i in get_list:
                i.start()
            for i in get_list:
                i.join()
        # self.fiction['num'] += len(self.catalog)
        # self.fiction['last_chapter'] = self.catalog[-1]['name']
        self.fiction['update'] = str(int(time()))
        logging.info('get_chapter_all %s complete, get %d chapters' % (self.fiction['name'], len(self.catalog)))
    def check_catalog(self):
        """ 将抓取到的目录与本地文件的最后一章对比，返回需要抓取的目录 """
        chapter_name_list = [i['name'] for i in self.catalog]
        local_info = self.load(self.fiction['name'])
        ind = chapter_name_list.index(local_info['last_chapter'])+1 if local_info else 0
        self.catalog = self.catalog[ind:]

class bqg(fiction):
    def get_source(self, name=''):
        if name:
            self.__init__(name)
        url = 'https://www.xbiquge6.com/search.php?keyword=%s' % self.fiction['name']
        soup = self.get_url(url)
        if not soup:return False
        soup = soup.find('div', class_='result-list').find_all('div', class_='result-item result-game-item')
        if not soup:return False
        flist = []
        for i in soup:
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
        ind = 0
        if len(flist) > 1:
            for i in flist:
                print('%d , 名称:%s , 作者:%s , 末尾:%s , 简介:%s' % (flist.index(i), i['name'], i['author'], i['last_chapter'], i['desc']))
            ind = int(input('Please select fiction id :'))
        self.fiction = dict(self.fiction, **flist[ind])
    def get_catalog(self):
        soup = self.get_url(self.fiction['source'])
        if not soup:return False
        soup = soup.find('div', id='list').find_all('a')
        if not soup:return False
        self.catalog = [{'ind':soup.index(i), 'name':i.text, 'status':False, 'url':'https://www.xbiquge6.com%s' % i.get('href')} for i in soup]
        self.check_catalog()
        logging.info('get_catalog, %s, last chapter %s, %d chapter waiting for get' % (self.fiction['name'], self.fiction['last_chapter'], len(self.catalog)))
        return True
    def get_chapter(self, chapter):
        """ 抓取单一章节, 抓取结果保存入队列 """
        soup = self.get_url(chapter['url'])
        if not soup:return False
        chapter['content'] = soup.find('div', id='content').text.replace(u'\xa0\xa0\xa0\xa0', '\n')
        chapter['status'] = True
        self.content.put((chapter['ind'], chapter['name'], chapter['content']))
        return True

class x23(fiction):
    """ https://www.x23us.com/ """
    def get_source(self, name=''):
        if name:self.__init__(name)
        url = 'https://www.x23us.com/modules/article/search.php?searchtype=keywords&searchkey=%s' % self.fiction['name']
        url = requests.utils.quote(url, safe=':/?&=', encoding='gbk')
        soup = self.get_url(url)
        pass

if __name__ == '__main__':
    if len(sys.argv) == 1:
        name = input('请输入小说名称:')
        t = bqg(name)
        t.do_fiction()
    else:
        flist = sys.argv[1:]
        for name in flist:
            print(name)
            t = bqg(name)
            t.do_fiction()