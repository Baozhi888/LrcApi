import time
import base64
import requests
import concurrent.futures
from fake_useragent import UserAgent
from mod import textcompare


ua = UserAgent().chrome


def kugou(title, artist, album):
    headers = {'User-Agent': ua, }
    limit = 10
    # 第一层Json，要求获得Hash值
    response = requests.get(
        f'http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword={title} {artist} {album}&page=1&pagesize=2&showtype=1',
        headers=headers)
    if response.status_code == 200:
        song_info = response.json()["data"]["info"]
        if len(song_info) >= 1:
            ratio_max = 0.2
            for index in range(min(limit, len(song_info))):
                song_item = song_info[index]
                song_name = song_item["songname"]
                singer_name = song_item.get("singername", "")
                song_hash = song_item["hash"]
                album_name = song_item.get("album_name", "")
                title_conform_ratio = textcompare.association(title, song_name)
                artist_conform_ratio = textcompare.assoc_artists(artist, singer_name)
                # 计算两个指标的几何平均值；区间范围(0,1]
                ratio = (title_conform_ratio * artist_conform_ratio) ** 0.5
                ratio_max = max(ratio, ratio_max)
                if ratio >= ratio_max:
                    response2 = requests.get(
                        f"https://krcs.kugou.com/search?ver=1&man=yes&client=mobi&keyword=&duration=&hash={song_hash}&album_audio_id=",
                        headers=headers)
                    lyrics_info = response2.json()
                    lyrics_id = lyrics_info["candidates"][0]["id"]
                    lyrics_key = lyrics_info["candidates"][0]["accesskey"]
                    # 第三层Json，要求获得并解码Base64
                    response3 = requests.get(
                        f"http://lyrics.kugou.com/download?ver=1&client=pc&id={lyrics_id}&accesskey={lyrics_key}&fmt=lrc&charset=utf8",
                        headers=headers)
                    lyrics_data = response3.json()
                    lyrics_encode = lyrics_data["content"]  # 这里是Base64编码的数据
                    lrc_text = base64.b64decode(lyrics_encode).decode('utf-8')  # 这里解码
                    return lrc_text
    time.sleep(10)
    return None


def api_2(title, artist, album):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 LrcAPI/1.1',
    }
    url = f"https://lrc.xms.mx/lyrics?title={title}&artist={artist}&album={album}&path=None&limit=1&api=lrcapi"
    try:
        res = requests.get(url, headers=headers)
        return res.text
    except:
        time.sleep(10)
        return None


api_list = [kugou, api_2]


def main(title, artist, album):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 提交各API函数到线程池中执行
        task_list = []
        for task in api_list:
            task_list.append(executor.submit(task, title, artist, album))
        # 等待任意一个API完成
        done, not_done = concurrent.futures.wait(task_list, return_when=concurrent.futures.FIRST_COMPLETED)
        # 获取已完成线程的返回结果
        lyrics_text = done.pop().result()
    return lyrics_text


def allin(title, artist, album):
    lrc_list = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []

        def request_lrc(task):
            lrc = task(title, artist, album)
            if lrc:
                lrc_list.append(lrc)

        for task in api_list:
            future = executor.submit(request_lrc, task)
            futures.append(future)

        # 等待所有线程完成或超时
        try:
            concurrent.futures.wait(futures, timeout=30)
        except concurrent.futures.TimeoutError:
            pass

        # 取消未完成的任务
        for future in futures:
            future.cancel()

    return lrc_list


if __name__ == "__main__":
    print(main("第二天堂", "林俊杰", "第二天堂"))
