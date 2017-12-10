import logging
import urllib.request
from bs4 import BeautifulSoup


# 小田急バスのリアルタイム運行状況のURL(サンプルは三鷹市役所前 → 三鷹駅)
BUS_SCHEDULE_URL = 'http://www.odakyubus-navi.com/blsys/loca?VID=lsc&EID=nt&DSMK=46&ASMK=148'


# 小田急バスのリアルタイム運行状況を取得する
def get_bus_schedule(url):
    logging.info("Retrieving URL: {}".format(url))
    content = urllib.request.urlopen(url).read().decode('shift_jisx0213')
    soup = BeautifulSoup(content, "html.parser")

    # エラーメッセージがある時(バスが終了している時も含む)
    errors = soup.select('.errorCntTxt')
    if len(list(errors)) > 0:
        message = errors[0].contents[0]
        logging.warn("Error: ".format(message))
        raise Exception(message)

    # ダイヤをパースする
    result = []
    for bus_info in soup.select('.resultTbl tr')[1:]:
        res = list(map(lambda col: col.string, bus_info.find_all('td')))
        # のりば名が無いパターンの時(のりばが一個しか無い時等)
        if len(res) == 6:
            res = res[:2] + [None] + res[2:]

        info = {
            'scheduled_arrival': res[0],  # 時刻表上の到着時刻(ex 10:00)
            'estimated_arrival': res[1],  # 予想到着時刻(ex 10:02)
            'bus_stop': res[2],  # 乗り場 (ない時はNone)
            'destination': res[3],  # 行き先 (ex 【鷹５４】三鷹駅)
            'type': res[4],  # 車両 (ex ノンステップ)
            'status': res[5],  # 運行状況 (ex 約5分で到着します。, まもなく到着します)
            'destination_arrival': res[6]  # 目的地到着（予測） (ex 10:15)
        }

        result += [info]

    return result


def bus(event, context):
    logging.info(event)

    # もしバス停名を指定したければ使う
    # busStopName = event['request']['intent']['slots']['BusStop']

    # スケジュールを取得してメッセージを組み立てる
    try:
        schedules = get_bus_schedule(BUS_SCHEDULE_URL)
        message = '{}行きのバスは{}'.format(schedules[0]['destination'], schedules[0]['status'])
        if len(schedules) > 1:
            message += '次は{}'.format(schedules[1]['status'])
    except Exception as e:
        message = 'エラー {}'.format(e.message)

    logging.info(message)

    response = {
        'version': '1.0',
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': message,
            }
        }
    }

    return response


# テスト用
if __name__ == '__main__':
    print(bus(None, None))
