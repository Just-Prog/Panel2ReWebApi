import requests

copyright_dict = {1: "原创", 2: "转载"}
state_dict = {1: "橙色通过", 0: "开放浏览", -1: "待审核", -2: "稿件被退回", -3: "网警锁定",
              -4: "被锁定（撞车）", -9: "等待转码", -10: "延迟审核", -16: "转码失败", -100: "用户删除",
              -30: "修改已提交", -6: "修改已提交"}
live_status_dict = {0: "未开播", 1: "直播中", 2: "轮播中"}


def _is_chinese(word):
    for ch in word:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False


def ArchiveInfo():
    return {
        # bvid
        "bvid": str(),
        # 标题
        "title": '标题',
        # 转载 or 原创
        "copyright": '未知',
        # 简介
        "desc": '',
        # 封面链接
        "cover": None,
        # 发布时间 秒级时间戳
        "ptime": 0,
        # 投稿时间 秒级时间戳
        "ctime": 0,
        # 审核信息
        "state_desc": '',
        # 状态代码
        "state": 0,
        # 转载
        "source": '',
        # 标签
        "tag": '',
        # 以下是api中新增的几项，用于描述特殊拒稿
        # 观察发现所有稿件均有以下项
        # 但无问题的稿件这些项为空字符串
        # 不同于转码失败的拒稿，似乎只有侵权才有这些内容
        "reject_reason": '',
        "modify_advise": '',
        "problem_description": '',
        "problem_description_title": '',
        # 发现该项可以鉴别类型
        # 0-过审核 1-审核中 2-退回 3-撞车或侵权 4-转码问题使用另一接口
        "state_panel": 0
    }


# bvid相关
# BV1 6k 4 y 1 j 7 9k
# BV1 j3 4 1 1 d 7 Rq
# bvid 固定格式：BV1__4_1_7__ (LEN = 12)
def is_bvid_correct(bvid: str):
    if len(bvid) != 12:
        return False
    if bvid[0:2] != 'BV':
        return False
    line = bvid[2] + bvid[5] + bvid[7] + bvid[9]
    if line != '1417':
        return False
    return True


class BiliApis(object):
    def __init__(self, cookies: dict, headers: dict):
        self.cookies = cookies
        self.headers = headers

    def get_member_video_list(self, page: int = 1, size: int = 10, targer_type: str = 'pubed,not_pubed,is_pubing'):
        """
        查询稿件列表
        :param page: 页
        :param size: 页大小
        :param targer_type: 筛选 pubed/not_pubed/is_publing 用','连接
        """
        url = f"https://member.bilibili.com/x/web/archives?status={targer_type}&pn={page}&ps={size}"
        resp = requests.get(url=url, headers=self.headers, cookies=self.cookies)
        if resp.status_code != 200:
            raise Exception(f"调用API时发生错误 HTTP{resp.status_code}")
        got: dict = resp.json().get("data")
        if resp.json().get("code") != 0:
            raise Exception(resp.json().get("message"))
        arc_items = list()
        page_info = got.get('page')
        if got.get("arc_audits") is not None:
            for item in got.get("arc_audits"):
                archive = item['Archive']
                for i, v in enumerate(item['Videos']):
                    if v['reject_reason'] != '':
                        archive['reject_reason']+="\nP{p_num}-{r}".format(p_num=i+1,r=v['reject_reason'])
                arc_items.append(self.read_archive(archive))
        data: dict = {
            "page": page_info,
            "status": got.get('class'),
            "items": arc_items
        }
        return data

    def get_rejection_reason(self, bvid) -> str:
        """
        查询稿件退回原因
        :return: 拼接原因字符串
        """
        if not is_bvid_correct(bvid):
            raise Exception('bvid不合法')
        url = f"https://member.bilibili.com/x/web/archive/failcode?bvid={bvid}"
        resp = requests.get(url=url, headers=self.headers, cookies=self.cookies)
        if resp.status_code != 200:
            raise Exception(f"调用API时发生错误 HTTP{resp.status_code}")
        data = resp.json().get('data').get('videos')
        if data is None:
            return ''
        return ';'.join(i.get('xcode_fail_msg') for i in data)

    @staticmethod
    def read_archive(archive: dict):
        """
        转存稿件信息
        """
        info = ArchiveInfo()
        info['bvid'] = archive.get("bvid")
        info['title'] = archive.get("title")
        info['cover'] = archive.get("cover")
        info['tag'] = archive.get("tag")
        info['copyright'] = copyright_dict[archive.get("copyright")]
        info['desc'] = archive.get("desc")
        info['state'] = archive.get("state")
        info['state_desc'] = archive.get("state_desc")
        info['source'] = archive.get("source")
        info['ctime'] = archive.get("ctime")
        info['ptime'] = archive.get('ptime')
        info['reject_reason'] = archive.get('reject_reason')
        info['modify_advise'] = archive.get('modify_advise')
        info['problem_description'] = archive.get('problem_description')
        info['problem_description_title'] = archive.get('problem_description_title')
        info['state_panel'] = archive.get('state_panel')
        return info

    def get_member_info(self, bvid: str):
        """
        获取单个稿件信息
        :param bvid: BVID
        :return: ArchiveInfo
        """
        if not is_bvid_correct(bvid):
            raise Exception('bvid不合法')
        url = "https://member.bilibili.com/x/client/archive/view?bvid=" + bvid
        resp = requests.get(url=url, headers=self.headers, cookies=self.cookies)
        if resp.status_code != 200:
            raise Exception(f"调用API时发生错误 HTTP{resp.status_code}")
        got: dict = resp.json().get("data")
        if resp.json().get("code") != 0:
            raise Exception(resp.json().get("message"))
        archive: dict = got.get("archive")
        print(archive)
        return self.read_archive(archive)

    def get_liveroom_info(self, room) -> dict:
        """
        获取直播间信息
        :param room: 直播间号
        :return: 从bili获取的源数据，请查文档
        """
        url = "https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room}".format(
            room=room
        )
        resp = requests.get(url=url, headers=self.headers)
        if resp.status_code != 200:
            raise Exception('调用API时发生错误')
        got = resp.json().get("data")
        if resp.json().get("code") != 0:
            raise Exception(resp.json().get("message"))
        return got
